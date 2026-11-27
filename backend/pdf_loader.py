# pdf_loader.py: validates the PDF and extracts the text page by page.
# Output: a doc_id + a list of Page(page, text). Page numbers start at 1,
# so the chunker can keep them on every Chunk and the app can cite sources.

import hashlib
import re
from collections import Counter
from pathlib import Path

import pymupdf

from backend import config
from backend.schemas import Page


# Errors (both are ValueError, the app shows str(error) to the user)
class InvalidPDFError(ValueError):
    pass


class NoTextError(ValueError):
    pass


# Ligatures: some fonts write two or three letters as one character
LIGATURES = {"ﬀ": "ff", "ﬁ": "fi", "ﬂ": "fl", "ﬃ": "ffi", "ﬄ": "ffl", "ﬅ": "ft", "ﬆ": "st"}


# Main Function
def load_pdf(source):
    # source = path or bytes (uploaded_file.getvalue()), returns (doc_id, pages)
    data = read_bytes(source)
    doc = open_pdf(data)

    try:
        pages = []
        for i, pdf_page in enumerate(doc):
            text = clean_text(pdf_page.get_text("text"))
            pages.append(Page(page=i + 1, text=text))
    finally:
        doc.close()

    check_has_text(pages)
    pages = remove_repeated_lines(pages)
    return compute_doc_id(data), pages


def compute_doc_id(data):
    # Same PDF = same id, so it is never processed twice
    return hashlib.sha256(data).hexdigest()[:16]


# Validation
def read_bytes(source):
    if isinstance(source, (bytes, bytearray)):
        return bytes(source)

    path = Path(source)
    if not path.is_file():
        raise InvalidPDFError(f"File not found: {path}")
    return path.read_bytes()


def open_pdf(data):
    # Every PDF starts with "%PDF-", so a renamed .txt is rejected here
    if not data[:1024].lstrip().startswith(b"%PDF-"):
        raise InvalidPDFError("The file is not a PDF.")

    try:
        doc = pymupdf.open(stream=data, filetype="pdf")
    except Exception as e:
        raise InvalidPDFError(f"The PDF is corrupted or cannot be read ({e}).") from e

    if doc.needs_pass:
        doc.close()
        raise InvalidPDFError("The PDF is password-protected.")

    if doc.page_count == 0:
        doc.close()
        raise InvalidPDFError("The PDF has no pages.")

    return doc


def check_has_text(pages):
    pages_with_text = 0
    for page in pages:
        if len(page.text) >= config.MIN_CHARS_PER_PAGE:
            pages_with_text += 1

    # Too few pages with text = scanned PDF
    if pages_with_text / len(pages) < config.MIN_TEXT_PAGE_RATIO:
        raise NoTextError(
            "This PDF has no extractable text (it is probably a scanned, "
            "image-only document). OCR is not supported."
        )


# Text Cleaning
def clean_text(text):
    for ligature, letters in LIGATURES.items():
        text = text.replace(ligature, letters)

    # Soft hyphens and control chars: "ob\u0002jects" to "objects"
    text = re.sub(r"[\u00ad\u0002]\n?", "", text)

    # Split words: "recog-\nnising" to "recognising" (but "VREF-\nCVREF" stays)
    text = re.sub(r"(?<=[a-z])-\n(?=[a-z])", "", text)

    # Tabs and repeated spaces (also non-breaking \u00a0) to one space
    text = text.replace("\t", " ")
    text = re.sub(r"[ \u00a0]{2,}", " ", text)

    lines = []
    for line in text.splitlines():
        lines.append(line.strip())
    text = "\n".join(lines)

    # Max one empty line in a row
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# Header and Footer Removal
def line_key(line):
    # Digits to "#", so "Page 5 of 10" and "Page 6 of 10" are the same line
    return re.sub(r"\d+", "#", line.strip().lower())


def edge_positions(n_lines):
    # First and last EDGE_LINES lines of a page (10 lines to {0,1,2,3,6,7,8,9})
    top = set(range(min(config.EDGE_LINES, n_lines)))
    bottom = set(range(max(0, n_lines - config.EDGE_LINES), n_lines))
    return top | bottom


def remove_repeated_lines(pages):
    if len(pages) < config.MIN_PAGES_FOR_HEADER_REMOVAL:
        return pages

    page_lines = []
    for page in pages:
        lines = []
        for line in page.text.splitlines():
            if line.strip():
                lines.append(line)
        page_lines.append(lines)

    # On how many pages each edge line appears (once per page)
    counts = Counter()
    for lines in page_lines:
        edge_keys = set()
        for i in edge_positions(len(lines)):
            edge_keys.add(line_key(lines[i]))
        counts.update(edge_keys)

    threshold = config.REPEATED_LINE_RATIO * len(pages)
    repeated = set()
    for key, n_pages in counts.items():
        if n_pages >= threshold:
            repeated.add(key)

    # A number alone at the top/bottom is a page number (numbers inside tables are kept)
    repeated.add("#")

    cleaned = []
    for page, lines in zip(pages, page_lines):
        edges = edge_positions(len(lines))
        kept = []
        for i, line in enumerate(lines):
            if not (i in edges and line_key(line) in repeated):
                kept.append(line)
        cleaned.append(Page(page=page.page, text="\n".join(kept)))
    return cleaned


# Quick Test: python -m backend.pdf_loader data/pdfs/74LS157.pdf
if __name__ == "__main__":
    import sys

    doc_id, pages = load_pdf(sys.argv[1])
    total = 0
    empty = []
    for page in pages:
        total += len(page.text)
        if not page.text:
            empty.append(page.page)

    print(f"doc_id: {doc_id} | pages: {len(pages)} | chars: {total}")
    if empty:
        print(f"pages without text: {empty}")

    # First page with text
    for page in pages:
        if page.text:
            print(f"\n--- page {page.page} ---\n{page.text[:800]}")
            break