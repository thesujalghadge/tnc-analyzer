import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.db.database import get_connection


def _utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def compute_file_checksum(file_path: str):
    digest = hashlib.sha256()
    with open(file_path, "rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def compute_text_checksum(text: str):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def persist_analysis(
    *,
    document_id: str,
    source_type: str,
    page_count: int,
    summary: str,
    formatted_output: str,
    risk_overview: dict,
    clauses,
    chunks,
    user_id: str | None = None,
    original_name: str | None = None,
    source_url: str | None = None,
    stored_path: str | None = None,
    file_size: int | None = None,
    mime_type: str | None = None,
    checksum: str | None = None,
    extra_metadata: dict | None = None,
    model_used: str = "gemini_or_fallback",
):
    analysis_id = str(uuid4())
    created_at = _utc_now()

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO documents (
                id, user_id, source_type, original_name, source_url, stored_path,
                file_size, page_count, mime_type, checksum, extra_metadata, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                document_id,
                user_id,
                source_type,
                original_name,
                source_url,
                stored_path,
                file_size,
                page_count,
                mime_type,
                checksum,
                json.dumps(extra_metadata or {}, ensure_ascii=True),
                created_at,
            ),
        )

        connection.execute(
            """
            INSERT INTO analyses (
                id, document_id, summary, formatted_output,
                risk_overview_json, model_used, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                analysis_id,
                document_id,
                summary,
                formatted_output,
                json.dumps(risk_overview, ensure_ascii=True),
                model_used,
                created_at,
            ),
        )

        connection.executemany(
            """
            INSERT INTO document_chunks (document_id, chunk_id, page_number, text)
            VALUES (?, ?, ?, ?)
            """,
            [
                (
                    document_id,
                    chunk["chunk_id"],
                    chunk["page_number"],
                    chunk["text"],
                )
                for chunk in chunks
            ],
        )

        connection.executemany(
            """
            INSERT INTO analysis_clauses (
                analysis_id, chunk_id, page_number, clause_text, category,
                category_confidence, risk, risk_score, confidence, reason, highlighted_terms_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    analysis_id,
                    clause.chunk_id,
                    clause.page_number,
                    clause.clause,
                    clause.category,
                    clause.category_confidence,
                    clause.risk,
                    clause.risk_score,
                    clause.confidence,
                    clause.reason,
                    json.dumps(clause.highlighted_terms, ensure_ascii=True),
                )
                for clause in clauses
            ],
        )

    return {
        "analysis_id": analysis_id,
        "document_id": document_id,
        "created_at": created_at,
        "page_count": page_count,
        "checksum": checksum,
        "stored_path": stored_path,
        "file_size": file_size,
        "mime_type": mime_type,
        "original_name": original_name,
        "source_type": source_type,
        "source_url": source_url,
    }


def persist_chat_exchange(document_id: str, question: str, answer_payload):
    chat_id = str(uuid4())

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO chat_history (
                id, document_id, question, answer, grounded,
                confidence, citations_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                chat_id,
                document_id,
                question,
                answer_payload.answer,
                int(answer_payload.grounded),
                answer_payload.confidence,
                json.dumps(
                    [citation.model_dump() for citation in answer_payload.citations],
                    ensure_ascii=True,
                ),
                _utc_now(),
            ),
        )

    return chat_id


def fetch_document_bundle(document_id: str):
    with get_connection() as connection:
        document = connection.execute(
            "SELECT * FROM documents WHERE id = ?",
            (document_id,),
        ).fetchone()

        if document is None:
            return None

        analysis = connection.execute(
            "SELECT * FROM analyses WHERE document_id = ?",
            (document_id,),
        ).fetchone()

        chunks = connection.execute(
            """
            SELECT chunk_id, page_number, text
            FROM document_chunks
            WHERE document_id = ?
            ORDER BY chunk_id
            """,
            (document_id,),
        ).fetchall()

        clauses = connection.execute(
            """
            SELECT chunk_id, page_number, clause_text, category, category_confidence,
                   risk, risk_score, confidence, reason, highlighted_terms_json
            FROM analysis_clauses
            WHERE analysis_id = ?
            ORDER BY risk_score DESC, id ASC
            """,
            (analysis["id"],),
        ).fetchall() if analysis else []

        chats = connection.execute(
            """
            SELECT question, answer, grounded, confidence, citations_json, created_at
            FROM chat_history
            WHERE document_id = ?
            ORDER BY created_at DESC
            """,
            (document_id,),
        ).fetchall()

    return {
        "document": dict(document),
        "analysis": dict(analysis) if analysis else None,
        "chunks": [dict(chunk) for chunk in chunks],
        "clauses": [
            {
                **dict(clause),
                "highlighted_terms": json.loads(clause["highlighted_terms_json"]),
            }
            for clause in clauses
        ],
        "chat_history": [
            {
                **dict(chat),
                "citations": json.loads(chat["citations_json"]),
            }
            for chat in chats
        ],
    }


def ensure_storage_path(path: str):
    Path(path).mkdir(parents=True, exist_ok=True)
