import re

from pypdf import PdfReader


def clean_text(text: str) -> str:
    # Remove extra newlines
    text = re.sub(r'\n+', '\n', text)

    # Join broken lines
    text = re.sub(r'(?<!\n)\n(?!\n)', ' ', text)

    # Remove multiple spaces
    text = re.sub(r'\s+', ' ', text)

    return text.strip()


def extract_pages(file_path: str):
    reader = PdfReader(file_path)
    pages = []

    for page_number, page in enumerate(reader.pages, start=1):
        raw_text = page.extract_text() or ""
        cleaned_text = clean_text(raw_text)

        if cleaned_text:
            pages.append({
                "page_number": page_number,
                "text": cleaned_text,
            })

    return pages


def extract_text(file_path: str) -> str:
    pages = extract_pages(file_path)
    return " ".join(page["text"] for page in pages).strip()
