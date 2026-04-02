# -------------------------------
# IMPORTS
# -------------------------------
import json

import numpy as np

from app.models.schemas import AskResponse, SourceChunk
from app.services.embedding import get_embeddings


# =========================================================
# 🔹 RETRIEVE RELEVANT CHUNKS
# =========================================================

def _cosine_similarity(vector_a, vector_b):
    denominator = np.linalg.norm(vector_a) * np.linalg.norm(vector_b)
    if denominator == 0:
        return 0.0
    return float(np.dot(vector_a, vector_b) / denominator)


def retrieve_chunks(query, index, chunks, top_k=3, candidate_pool=6):
    query_embedding = np.array(get_embeddings([query])[0], dtype="float32")
    distances, indices = index.search(np.array([query_embedding]), candidate_pool)

    candidates = []
    for i in indices[0]:
        if 0 <= i < len(chunks):
            candidates.append(chunks[i])

    if not candidates:
        return []

    candidate_embeddings = get_embeddings([chunk["text"] for chunk in candidates])
    reranked_results = []

    for chunk, candidate_embedding in zip(candidates, candidate_embeddings):
        score = _cosine_similarity(query_embedding, np.array(candidate_embedding, dtype="float32"))
        reranked_results.append({
            "chunk_id": chunk["chunk_id"],
            "page_number": chunk["page_number"],
            "text": chunk["text"],
            "relevance_score": round(score, 4),
        })

    reranked_results.sort(key=lambda item: item["relevance_score"], reverse=True)
    return reranked_results[:top_k]


# =========================================================
# 🔹 BUILD CONTEXT
# =========================================================

def build_context(chunks):
    context = ""
    for chunk in chunks:
        context += f"[Clause {chunk['chunk_id'] + 1} | Page {chunk['page_number']}]\n{chunk['text']}\n\n"
    return context


# =========================================================
# 🔹 FALLBACK ANSWER (VERY IMPORTANT)
# =========================================================

def fallback_answer(question, context):
    q = question.lower()
    ctx = context.lower()

    # EMI related
    if "emi" in q:
        if "increase the emi" in ctx or "increase emi" in ctx:
            return {
                "answer": "Yes. The bank can increase your EMI if interest rate changes.",
                "grounded": True,
            }

    # charges / fees
    if "charge" in q or "fee" in q:
        if "fee" in ctx or "charge" in ctx or "penalty" in ctx:
            return {
                "answer": "Yes. The document mentions additional fees and charges.",
                "grounded": True,
            }

    # interest rate
    if "interest" in q:
        if "interest rate" in ctx and "change" in ctx:
            return {
                "answer": "Yes. The interest rate can change over time.",
                "grounded": True,
            }

    return {
        "answer": "Answer not clearly found in document.",
        "grounded": False,
    }


# =========================================================
# 🔹 GENERATE ANSWER (GEMINI + FALLBACK)
# =========================================================

def generate_answer(question, context):
    from app.services.llm_service import USE_GEMINI

    if USE_GEMINI:
        try:
            from app.services.llm_service import gemini_model

            prompt = f"""
You are analyzing a legal document.

Answer the question using the given clauses.

Question:
{question}

Clauses:
{context}

Instructions:
- Use only the given clauses
- If the answer is supported, say so clearly and briefly
- If support is weak, say that clearly
- Return strict JSON only with this shape:
  {{"answer":"...","grounded":true}}
"""

            response = gemini_model.generate_content(prompt)

            if hasattr(response, "text") and response.text:
                response_text = response.text.strip()
                response_text = response_text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
                payload = json.loads(response_text)
                return {
                    "answer": payload.get("answer", "").strip() or "Answer not clearly found in document.",
                    "grounded": bool(payload.get("grounded", False)),
                }

        except Exception as e:
            print("❌ Gemini QA Error:", e)

    # 🔥 fallback if Gemini fails or disabled
    return fallback_answer(question, context)


def calculate_confidence(citations, grounded):
    if not citations:
        return 0.0

    average_score = sum(chunk["relevance_score"] for chunk in citations) / len(citations)
    if not grounded:
        average_score *= 0.6

    return round(min(max(average_score, 0.0), 1.0), 2)


# =========================================================
# 🔹 MAIN FUNCTION
# =========================================================

def answer_question(question, index, chunks):
    # 1. retrieve relevant chunks
    top_chunks = retrieve_chunks(question, index, chunks)

    # 2. build context
    context = build_context(top_chunks)

    # 3. generate answer
    answer_payload = generate_answer(question, context)
    confidence = calculate_confidence(top_chunks, answer_payload["grounded"])

    # 4. return with evidence
    return AskResponse(
        answer=answer_payload["answer"],
        grounded=answer_payload["grounded"],
        confidence=confidence,
        citations=[
            SourceChunk(
                chunk_id=chunk["chunk_id"],
                page_number=chunk["page_number"],
                text=chunk["text"],
                relevance_score=chunk["relevance_score"],
            )
            for chunk in top_chunks
        ],
    )
