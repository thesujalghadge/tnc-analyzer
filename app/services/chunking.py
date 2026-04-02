import re


def _split_sentences(text: str):
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [part.strip() for part in parts if part.strip()]


def chunk_text(text: str, chunk_size: int = 700, overlap_sentences: int = 1):
    sentences = _split_sentences(text)

    chunks = []
    current_sentences = []
    current_length = 0

    for sentence in sentences:
        sentence_length = len(sentence) + 1

        if current_sentences and current_length + sentence_length > chunk_size:
            chunks.append(" ".join(current_sentences).strip())

            if overlap_sentences > 0:
                current_sentences = current_sentences[-overlap_sentences:]
                current_length = sum(len(item) + 1 for item in current_sentences)
            else:
                current_sentences = []
                current_length = 0

        current_sentences.append(sentence)
        current_length += sentence_length

    if current_sentences:
        chunks.append(" ".join(current_sentences).strip())

    return chunks


def chunk_pages(pages, chunk_size: int = 700, overlap_sentences: int = 1):
    chunks = []

    for page in pages:
        page_chunks = chunk_text(
            page["text"],
            chunk_size=chunk_size,
            overlap_sentences=overlap_sentences,
        )

        for chunk_text_value in page_chunks:
            chunks.append({
                "chunk_id": len(chunks),
                "page_number": page["page_number"],
                "text": chunk_text_value,
            })

    return chunks
