import os
import shutil
import base64

from fastapi import FastAPI, File, HTTPException, UploadFile

from app.models.schemas import AnalyzeResponse, AnalyzeUrlRequest, AskRequest, AskResponse
from app.services.analysis_service import (
    analyze_document as run_document_analysis,
    analyze_image_text,
    analyze_url as run_url_analysis,
)
from app.services.document_store import InMemoryDocumentStore
from app.services.llm_service import extract_text_from_images
from app.services.qa_service import answer_question

app = FastAPI()

UPLOAD_FOLDER = "data/uploads"
document_store = InMemoryDocumentStore()


# =========================================================
# 🔹 ANALYZE ENDPOINT
# =========================================================

@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze_document(file: UploadFile = File(...)):
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        response, vector_store, chunks, analysis = run_document_analysis(file_path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    session = document_store.create(chunks=chunks, clauses=analysis, vector_index=vector_store.index)
    response.document_id = session.document_id
    return response


@app.post("/analyze-url", response_model=AnalyzeResponse)
async def analyze_document_url(request: AnalyzeUrlRequest):
    try:
        response, vector_store, chunks, analysis = run_url_analysis(request.url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    session = document_store.create(chunks=chunks, clauses=analysis, vector_index=vector_store.index)
    response.document_id = session.document_id
    return response


@app.post("/analyze-images", response_model=AnalyzeResponse)
async def analyze_document_images(files: list[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail="Please upload at least one document image.")

    image_payloads = []
    for file in files:
        if not file.content_type or not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="Only image files are supported for photo analysis.")

        content = await file.read()
        image_payloads.append({
            "mime_type": file.content_type,
            "data": base64.b64encode(content).decode("utf-8"),
        })

    try:
        raw_text = extract_text_from_images(image_payloads)
        response, vector_store, chunks, analysis = analyze_image_text(raw_text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    session = document_store.create(chunks=chunks, clauses=analysis, vector_index=vector_store.index)
    response.document_id = session.document_id
    return response


# =========================================================
# 🔹 Q&A ENDPOINT
# =========================================================

@app.post("/ask", response_model=AskResponse)
async def ask_question(request: AskRequest):
    session = document_store.get(request.document_id)

    if session is None:
        raise HTTPException(status_code=404, detail="Document not found. Please analyze a document first.")

    return answer_question(
        request.question,
        session.vector_index,
        session.chunks,
        session.clauses,
    )
