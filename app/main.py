import os
import shutil

from fastapi import FastAPI, File, HTTPException, UploadFile

from app.models.schemas import AnalyzeResponse, AskRequest, AskResponse
from app.services.analysis_service import analyze_document as run_document_analysis
from app.services.document_store import InMemoryDocumentStore
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
