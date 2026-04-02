from app.db.vector_store import VectorStore
from app.models.schemas import AnalyzeResponse, ClauseAnalysis, RiskOverview
from app.services.analyzer import analyze_clauses
from app.services.chunking import chunk_pages
from app.services.embedding import get_embeddings
from app.services.llm_service import generate_summary
from app.services.output_formatter import format_output
from app.services.parser import extract_pages


def _build_clause_models(chunk_records, analysis):
    clauses = []

    for chunk_record, item in zip(chunk_records, analysis):
        clauses.append(
            ClauseAnalysis(
                chunk_id=chunk_record["chunk_id"],
                page_number=chunk_record["page_number"],
                clause=item["clause"],
                category=item["category"],
                category_confidence=item["category_confidence"],
                risk=item["risk"],
                risk_score=item["risk_score"],
                confidence=item["confidence"],
                reason=item["reason"],
                highlighted_terms=item["highlighted_terms"],
            )
        )

    return clauses


def _build_risk_overview(analysis) -> RiskOverview:
    risk_count = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}

    for item in analysis:
        risk_count[item["risk"]] += 1

    return RiskOverview(
        high=risk_count["HIGH"],
        medium=risk_count["MEDIUM"],
        low=risk_count["LOW"],
    )


def analyze_document(file_path: str):
    pages = extract_pages(file_path)
    chunks = chunk_pages(pages)

    if not chunks:
        raise ValueError("No text could be extracted from the uploaded document.")

    chunk_texts = [chunk["text"] for chunk in chunks]
    embeddings = get_embeddings(chunk_texts)

    vector_store = VectorStore(dimension=len(embeddings[0]))
    vector_store.add(embeddings, chunk_texts)

    analysis = analyze_clauses(chunk_texts)
    summary = generate_summary(chunk_texts)
    formatted_output = format_output(summary, analysis)

    response = AnalyzeResponse(
        document_id="",
        summary=summary,
        risk_overview=_build_risk_overview(analysis),
        clauses=_build_clause_models(chunks, analysis),
        formatted_output=formatted_output,
    )

    return response, vector_store, chunks
