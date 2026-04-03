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


def is_risk_summary_question(question: str):
    question_lower = question.lower()
    patterns = [
        "is this risky",
        "is this tnc risky",
        "what is risky",
        "what should i worry",
        "should i be worried",
        "summarize the risks",
        "main risks",
        "biggest risks",
        "what are the risks",
    ]
    return any(pattern in question_lower for pattern in patterns)


def retrieve_risk_clauses(question, clauses, top_k=3):
    query_embedding = np.array(get_embeddings([question])[0], dtype="float32")
    clause_embeddings = get_embeddings([clause["clause"] for clause in clauses])
    scored_results = []

    for clause, embedding in zip(clauses, clause_embeddings):
        semantic_score = _cosine_similarity(query_embedding, np.array(embedding, dtype="float32"))
        risk_weight = clause["risk_score"] / 10.0
        combined_score = round((semantic_score * 0.45) + (risk_weight * 0.55), 4)
        scored_results.append({
            "chunk_id": clause["chunk_id"],
            "page_number": clause["page_number"],
            "text": clause["clause"],
            "relevance_score": combined_score,
            "risk_score": clause["risk_score"],
            "risk": clause["risk"],
            "reason": clause["reason"],
        })

    scored_results.sort(
        key=lambda item: (item["risk_score"], item["relevance_score"]),
        reverse=True,
    )
    return scored_results[:top_k]


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


def fallback_risk_answer(citations):
    if not citations:
        return {
            "answer": "I could not find enough grounded evidence to judge the document risk clearly.",
            "grounded": False,
        }

    highest = citations[0]
    if highest["risk_score"] >= 7:
        answer = "Yes. This document has at least one clearly risky clause, especially around how the lender can change terms or act without directly informing the borrower."
    elif highest["risk_score"] >= 4:
        answer = "This document has some meaningful risks, mostly around payment changes, fees, or lender-favorable conditions, but it does not look extreme overall."
    else:
        answer = "This document looks relatively standard from the retrieved clauses, though there are still some user obligations to review."

    return {
        "answer": answer,
        "grounded": True,
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


def generate_risk_answer(question, context, citations):
    from app.services.llm_service import USE_GEMINI

    if USE_GEMINI:
        try:
            from app.services.llm_service import gemini_model

            prompt = f"""
You are analyzing legal clauses from a user document.

Question:
{question}

Retrieved risk-focused clauses:
{context}

Instructions:
- Answer in plain language for a normal user
- Focus on whether the document has meaningful user risks
- Mention the most important 1-2 risks only
- Use only the given clauses
- Return strict JSON only with this shape:
  {{"answer":"...","grounded":true}}
"""

            response = gemini_model.generate_content(prompt)

            if hasattr(response, "text") and response.text:
                response_text = response.text.strip()
                response_text = response_text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
                payload = json.loads(response_text)
                return {
                    "answer": payload.get("answer", "").strip() or "I could not summarize the risks clearly from the retrieved clauses.",
                    "grounded": bool(payload.get("grounded", False)),
                }
        except Exception as e:
            print("❌ Gemini Risk QA Error:", e)

    return fallback_risk_answer(citations)


def calculate_confidence(citations, grounded, risk_mode=False):
    if not citations:
        return 0.0

    average_score = sum(chunk["relevance_score"] for chunk in citations) / len(citations)
    if risk_mode:
        top_risk = max(chunk.get("risk_score", 0.0) for chunk in citations) / 10.0
        average_score = max(average_score, (average_score * 0.55) + (top_risk * 0.45))
    if not grounded:
        average_score *= 0.6

    return round(min(max(average_score, 0.0), 1.0), 2)


# =========================================================
# 🔹 MAIN FUNCTION
# =========================================================

def answer_question(question, index, chunks, clauses):
    risk_mode = is_risk_summary_question(question)

    if risk_mode:
        top_chunks = retrieve_risk_clauses(question, clauses)
    else:
        top_chunks = retrieve_chunks(question, index, chunks)

    # 2. build context
    context = build_context(top_chunks)

    # 3. generate answer
    if risk_mode:
        answer_payload = generate_risk_answer(question, context, top_chunks)
    else:
        answer_payload = generate_answer(question, context)
    confidence = calculate_confidence(top_chunks, answer_payload["grounded"], risk_mode=risk_mode)

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
