# -------------------------------
# IMPORTS
# -------------------------------
from sentence_transformers import SentenceTransformer

from app.models.schemas import AskResponse, SourceChunk

# embedding model
embed_model = SentenceTransformer("all-MiniLM-L6-v2")


# =========================================================
# 🔹 RETRIEVE RELEVANT CHUNKS
# =========================================================

def retrieve_chunks(query, index, chunks, top_k=3):
    query_embedding = embed_model.encode([query])

    distances, indices = index.search(query_embedding, top_k)

    results = []
    for i in indices[0]:
        if 0 <= i < len(chunks):
            results.append({
                "chunk_id": chunks[i]["chunk_id"],
                "page_number": chunks[i]["page_number"],
                "text": chunks[i]["text"],
            })

    return results


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
            return "Yes. The bank can increase your EMI if interest rate changes."

    # charges / fees
    if "charge" in q or "fee" in q:
        if "fee" in ctx or "charge" in ctx or "penalty" in ctx:
            return "Yes. The document mentions additional fees and charges."

    # interest rate
    if "interest" in q:
        if "interest rate" in ctx and "change" in ctx:
            return "Yes. The interest rate can change over time."

    return "Answer not clearly found in document"


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
- Answer clearly in 1-2 sentences
- If answer is present, say YES or NO first
- Then explain briefly
- Use only the given clauses
- Do NOT say "not found" if answer is implied

Example:
Question: Can bank increase EMI?
Answer: Yes. The bank can increase EMI if interest rate changes.

Now answer:
"""

            response = gemini_model.generate_content(prompt)

            if hasattr(response, "text") and response.text:
                return response.text.strip()

        except Exception as e:
            print("❌ Gemini QA Error:", e)

    # 🔥 fallback if Gemini fails or disabled
    return fallback_answer(question, context)


# =========================================================
# 🔹 MAIN FUNCTION
# =========================================================

def answer_question(question, index, chunks):
    # 1. retrieve relevant chunks
    top_chunks = retrieve_chunks(question, index, chunks)

    # 2. build context
    context = build_context(top_chunks)

    # 3. generate answer
    answer = generate_answer(question, context)

    # 4. return with evidence
    return AskResponse(
        answer=answer,
        evidence=[
            SourceChunk(
                chunk_id=chunk["chunk_id"],
                page_number=chunk["page_number"],
                text=chunk["text"],
            )
            for chunk in top_chunks
        ],
    )
