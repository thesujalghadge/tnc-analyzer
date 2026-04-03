import html
import re
import tempfile
from urllib.parse import urlparse

import requests
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


def is_valid_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def html_to_text(raw_html: str) -> str:
    raw_html = re.sub(r"<script[\s\S]*?</script>", " ", raw_html, flags=re.IGNORECASE)
    raw_html = re.sub(r"<style[\s\S]*?</style>", " ", raw_html, flags=re.IGNORECASE)
    raw_html = re.sub(r"<[^>]+>", " ", raw_html)
    raw_html = html.unescape(raw_html)
    return clean_text(raw_html)


def extract_pages_from_url(url: str):
    if not is_valid_url(url):
        raise ValueError("Please enter a valid URL starting with http:// or https://")

    try:
        response = requests.get(url, timeout=20)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise ValueError("Could not fetch the link. Please check the URL and try again.") from exc

    content_type = response.headers.get("content-type", "").lower()

    if "pdf" in content_type or url.lower().endswith(".pdf"):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(response.content)
            temp_path = tmp.name

        try:
            return extract_pages(temp_path)
        finally:
            try:
                import os
                os.unlink(temp_path)
            except OSError:
                pass

    if "text/html" in content_type or "<html" in response.text.lower():
        text = html_to_text(response.text)
        if not text:
            raise ValueError("The page was fetched, but no readable text could be extracted.")
        return [{"page_number": 1, "text": text}]

    if "text/plain" in content_type:
        text = clean_text(response.text)
        if not text:
            raise ValueError("The link does not contain readable text.")
        return [{"page_number": 1, "text": text}]

    raise ValueError("This link type is not supported yet. Please use a PDF or webpage URL.")


def extract_pages_from_text(raw_text: str):
    cleaned_text = clean_text(raw_text)
    if not cleaned_text:
        raise ValueError("No readable text could be extracted from the provided content.")

    split_pages = re.split(r"\[page\s+\d+\]", cleaned_text, flags=re.IGNORECASE)
    page_blocks = [block.strip() for block in split_pages if block.strip()]

    if len(page_blocks) <= 1:
        return [{"page_number": 1, "text": cleaned_text}]

    return [
        {"page_number": index, "text": block}
        for index, block in enumerate(page_blocks, start=1)
    ]
