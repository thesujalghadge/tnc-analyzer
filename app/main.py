import base64
import json
import re
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

from fastapi import FastAPI, File, Header, HTTPException, Response, UploadFile

from app.db.database import init_db
from app.db.vector_store import VectorStore
from app.models.schemas import (
    AnalyzeResponse,
    AnalyzeUrlRequest,
    AskRequest,
    AskResponse,
    AuthLoginRequest,
    AuthRegisterRequest,
    AuthResponse,
    DocumentMetadata,
    HistoryItem,
    UserResponse,
)
from app.services.analysis_service import (
    analyze_document as run_document_analysis,
    analyze_image_text,
    analyze_url as run_url_analysis,
)
from app.services.auth_service import (
    authenticate_user,
    create_session,
    get_user_from_token,
    register_user,
    revoke_session,
)
from app.services.document_store import InMemoryDocumentStore
from app.services.embedding import get_embeddings
from app.services.llm_service import extract_text_from_images
from app.services.persistence_service import (
    build_analysis_payload,
    compute_file_checksum,
    compute_text_checksum,
    ensure_storage_path,
    fetch_document_bundle,
    list_user_history,
    persist_analysis,
    persist_chat_exchange,
)
from app.services.qa_service import answer_question
from app.services.report_service import build_analysis_report_pdf, build_report_filename

app = FastAPI()

UPLOAD_FOLDER = "data/uploads"
document_store = InMemoryDocumentStore()
ensure_storage_path(UPLOAD_FOLDER)


@app.on_event("startup")
def startup():
    init_db()


def _sanitize_filename(filename: str | None, fallback: str):
    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", filename or fallback).strip("._")
    return safe_name or fallback


async def _persist_uploaded_file(file: UploadFile, default_name: str):
    file_bytes = await file.read()
    safe_name = _sanitize_filename(file.filename, default_name)
    stored_name = f"{uuid4().hex}_{safe_name}"
    file_path = Path(UPLOAD_FOLDER) / stored_name
    file_path.write_bytes(file_bytes)

    return {
        "path": str(file_path),
        "original_name": safe_name,
        "file_size": len(file_bytes),
        "mime_type": file.content_type,
        "checksum": compute_file_checksum(str(file_path)),
    }


async def _persist_uploaded_images(files: list[UploadFile]):
    stored_paths = []
    original_names = []
    mime_types = set()
    total_size = 0
    image_payloads = []

    for file in files:
        content = await file.read()
        safe_name = _sanitize_filename(file.filename, "document_image")
        stored_name = f"{uuid4().hex}_{safe_name}"
        file_path = Path(UPLOAD_FOLDER) / stored_name
        file_path.write_bytes(content)

        stored_paths.append(str(file_path))
        original_names.append(safe_name)
        total_size += len(content)
        if file.content_type:
            mime_types.add(file.content_type)

        image_payloads.append({
            "mime_type": file.content_type,
            "data": base64.b64encode(content).decode("utf-8"),
        })

    return {
        "stored_paths": stored_paths,
        "original_name": ", ".join(original_names[:3]) + (f" (+{len(original_names) - 3} more)" if len(original_names) > 3 else ""),
        "file_size": total_size,
        "mime_type": ", ".join(sorted(mime_types)) if mime_types else None,
        "checksum": compute_text_checksum("|".join(stored_paths)),
        "image_payloads": image_payloads,
        "extra_metadata": {
            "file_names": original_names,
            "file_count": len(original_names),
        },
    }


def _page_count_from_chunks(chunks):
    return len({chunk["page_number"] for chunk in chunks}) if chunks else 0


def _structured_clauses(response: AnalyzeResponse):
    return [clause.model_dump() for clause in response.clauses]


def _extract_bearer_token(authorization: str | None):
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid authorization header.")
    return parts[1].strip()


def _current_user(authorization: str | None, *, required: bool = False):
    token = _extract_bearer_token(authorization)
    if not token:
        if required:
            raise HTTPException(status_code=401, detail="Authentication required.")
        return None

    user = get_user_from_token(token)
    if user is None:
        raise HTTPException(status_code=401, detail="Your session is invalid or expired. Please sign in again.")
    return user


def _restore_document_session(document_id: str, *, user_id: str | None = None):
    payload = build_analysis_payload(document_id, user_id=user_id)
    bundle = fetch_document_bundle(document_id)

    if payload is None or bundle is None:
        return None, None

    chunks = bundle["chunks"]
    chunk_texts = [chunk["text"] for chunk in chunks]
    if not chunk_texts:
        return payload, None

    embeddings = get_embeddings(chunk_texts)
    vector_store = VectorStore(dimension=len(embeddings[0]))
    vector_store.add(embeddings, chunk_texts)

    session = document_store.create(
        chunks=chunks,
        clauses=payload["clauses"],
        vector_index=vector_store.index,
        document_id=document_id,
    )
    return payload, session


# =========================================================
# 🔹 AUTH ENDPOINTS
# =========================================================

@app.post("/auth/register", response_model=AuthResponse)
async def register(request: AuthRegisterRequest):
    if len(request.password.strip()) < 8:
        raise HTTPException(status_code=400, detail="Password should be at least 8 characters long.")

    try:
        user = register_user(request.name, request.email, request.password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return AuthResponse(
        access_token=create_session(user["id"]),
        user=UserResponse(**user),
    )


@app.post("/auth/login", response_model=AuthResponse)
async def login(request: AuthLoginRequest):
    try:
        user = authenticate_user(request.email, request.password)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    return AuthResponse(
        access_token=create_session(user["id"]),
        user=UserResponse(**user),
    )


@app.post("/auth/logout")
async def logout(authorization: str | None = Header(default=None)):
    token = _extract_bearer_token(authorization)
    if token:
        revoke_session(token)
    return {"ok": True}


# =========================================================
# 🔹 ANALYZE ENDPOINT
# =========================================================

@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze_document(file: UploadFile = File(...), authorization: str | None = Header(default=None)):
    user = _current_user(authorization, required=False)
    stored_file = await _persist_uploaded_file(file, "uploaded_document.pdf")

    try:
        response, vector_store, chunks, analysis = run_document_analysis(stored_file["path"])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    document_id = str(uuid4())
    metadata = persist_analysis(
        document_id=document_id,
        source_type="pdf",
        user_id=user["id"] if user else None,
        original_name=stored_file["original_name"],
        stored_path=stored_file["path"],
        file_size=stored_file["file_size"],
        mime_type=stored_file["mime_type"],
        checksum=stored_file["checksum"],
        page_count=_page_count_from_chunks(chunks),
        summary=response.summary,
        formatted_output=response.formatted_output,
        risk_overview=response.risk_overview.model_dump(),
        clauses=response.clauses,
        chunks=chunks,
        extra_metadata={"upload_name": stored_file["original_name"]},
    )

    session = document_store.create(
        chunks=chunks,
        clauses=_structured_clauses(response),
        vector_index=vector_store.index,
        document_id=document_id,
    )
    response.document_id = session.document_id
    response.metadata = DocumentMetadata(**metadata)
    return response


@app.post("/analyze-url", response_model=AnalyzeResponse)
async def analyze_document_url(request: AnalyzeUrlRequest, authorization: str | None = Header(default=None)):
    user = _current_user(authorization, required=False)
    try:
        response, vector_store, chunks, analysis = run_url_analysis(request.url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    checksum = compute_text_checksum("\n".join(chunk["text"] for chunk in chunks))
    document_id = str(uuid4())
    metadata = persist_analysis(
        document_id=document_id,
        source_type="url",
        user_id=user["id"] if user else None,
        original_name=_sanitize_filename(Path(urlparse(request.url).path).name or "web_document", "web_document"),
        source_url=request.url,
        checksum=checksum,
        page_count=_page_count_from_chunks(chunks),
        summary=response.summary,
        formatted_output=response.formatted_output,
        risk_overview=response.risk_overview.model_dump(),
        clauses=response.clauses,
        chunks=chunks,
        extra_metadata={"source_host": urlparse(request.url).netloc},
    )

    session = document_store.create(
        chunks=chunks,
        clauses=_structured_clauses(response),
        vector_index=vector_store.index,
        document_id=document_id,
    )
    response.document_id = session.document_id
    response.metadata = DocumentMetadata(**metadata)
    return response


@app.post("/analyze-images", response_model=AnalyzeResponse)
async def analyze_document_images(files: list[UploadFile] = File(...), authorization: str | None = Header(default=None)):
    user = _current_user(authorization, required=False)
    if not files:
        raise HTTPException(status_code=400, detail="Please upload at least one document image.")

    image_payloads = []
    for file in files:
        if not file.content_type or not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="Only image files are supported for photo analysis.")

    stored_images = await _persist_uploaded_images(files)
    image_payloads = stored_images["image_payloads"]

    try:
        raw_text = extract_text_from_images(image_payloads)
        response, vector_store, chunks, analysis = analyze_image_text(raw_text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    checksum = compute_text_checksum(raw_text)
    document_id = str(uuid4())
    metadata = persist_analysis(
        document_id=document_id,
        source_type="image",
        user_id=user["id"] if user else None,
        original_name=stored_images["original_name"],
        stored_path=json.dumps(stored_images["stored_paths"], ensure_ascii=True),
        file_size=stored_images["file_size"],
        mime_type=stored_images["mime_type"],
        checksum=checksum,
        page_count=_page_count_from_chunks(chunks),
        summary=response.summary,
        formatted_output=response.formatted_output,
        risk_overview=response.risk_overview.model_dump(),
        clauses=response.clauses,
        chunks=chunks,
        extra_metadata=stored_images["extra_metadata"],
    )

    session = document_store.create(
        chunks=chunks,
        clauses=_structured_clauses(response),
        vector_index=vector_store.index,
        document_id=document_id,
    )
    response.document_id = session.document_id
    response.metadata = DocumentMetadata(**metadata)
    return response


# =========================================================
# 🔹 Q&A ENDPOINT
# =========================================================

@app.post("/ask", response_model=AskResponse)
async def ask_question(request: AskRequest):
    session = document_store.get(request.document_id)

    if session is None:
        raise HTTPException(status_code=404, detail="Document not found. Please analyze a document first.")

    answer = answer_question(
        request.question,
        session.vector_index,
        session.chunks,
        session.clauses,
    )
    persist_chat_exchange(request.document_id, request.question, answer)
    return answer


@app.get("/report/{document_id}")
async def download_report(document_id: str, authorization: str | None = Header(default=None)):
    bundle = fetch_document_bundle(document_id)
    if bundle is None or bundle.get("analysis") is None:
        raise HTTPException(status_code=404, detail="Stored analysis not found for this document.")

    owner_id = bundle["document"].get("user_id")
    if owner_id:
        user = _current_user(authorization, required=True)
        if user["id"] != owner_id:
            raise HTTPException(status_code=403, detail="You do not have access to this report.")

    report_bytes = build_analysis_report_pdf(bundle)
    filename = build_report_filename(bundle)
    return Response(
        content=report_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/history", response_model=list[HistoryItem])
async def get_history(authorization: str | None = Header(default=None)):
    user = _current_user(authorization, required=True)
    items = list_user_history(user["id"])
    return [HistoryItem(**item) for item in items]


@app.get("/analysis/{document_id}", response_model=AnalyzeResponse)
async def load_stored_analysis(document_id: str, authorization: str | None = Header(default=None)):
    user = _current_user(authorization, required=True)
    payload, session = _restore_document_session(document_id, user_id=user["id"])

    if payload is None or session is None:
        raise HTTPException(status_code=404, detail="Stored analysis not found for this user.")

    response = AnalyzeResponse(**payload)
    response.document_id = session.document_id
    return response
