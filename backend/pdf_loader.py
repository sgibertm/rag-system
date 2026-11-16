# PDF loading: validates the file and extracts the text page by page.
#
# Output: a doc_id + a list of Page(page, text). Page numbers start at 1 so the
# chunker can keep them on every Chunk and the app can cite sources.
#
# Design decisions:
# - PyMuPDF (pymupdf): fast and handles big datasheets (hundreds of pages) in
#   a few seconds. We keep the PDF's own text order (no sort=True): sorting by
#   position mixes the two columns of papers (tested with the YOLO paper).
# - doc_id = hash of the file bytes: the same PDF always gets the same id, so
#   the vector store can skip re-ingesting a document it already has.
# - Datasheets repeat a header/footer on every page ("PIC18F4321 FAMILY",
#   "© 2006 Microchip ... DS39689B-page 364"). That text adds noise to every
#   chunk and its embedding, so lines repeated on most pages are removed.
# - No OCR: if the PDF has (almost) no extractable text we raise NoTextError
#   so the app can tell the user (required by the assignment).

from __future__ import annotations

import hashlib
import re
from collections import Counter
from pathlib import Path

import pymupdf

from backend.schemas import Page


class InvalidPDFError(ValueError):
    """The file is not a valid / readable PDF."""


class NoTextError(ValueError):
    """The PDF has no extractable text (e.g. scanned, image-only)."""


# A PDF is considered "without text" below these thresholds
MIN_CHARS_PER_PAGE = 20      # a page with fewer chars counts as empty
MIN_TEXT_PAGE_RATIO = 0.1    # at least 10% of pages must have text

# A line is a header/footer if it appears on at least this fraction of pages
REPEATED_LINE_RATIO = 0.5
MIN_PAGES_FOR_HEADER_REMOVAL = 4
EDGE_LINES = 4              # lines checked at the top and bottom of each page

_LIGATURES = {"ﬀ": "ff", "ﬁ": "fi", "ﬂ": "fl", "ﬃ": "ffi", "ﬄ": "ffl", "ﬅ": "ft", "ﬆ": "st"}


# ---------------------------------------------------------------- public API

def load_pdf(source: str | Path | bytes) -> tuple[str, list[Page]]:
    """Validates the PDF and returns (doc_id, pages).

    `source` can be a path or the raw bytes (what Streamlit's file_uploader
    gives you with uploaded_file.getvalue()).

    Raises InvalidPDFError or NoTextError with a message ready to show the user.
    """
    data = _read_bytes(source)
    doc = _open_pdf(data)
    try:
        pages = [Page(page=i + 1, text=_clean_text(p.get_text("text")))
                 for i, p in enumerate(doc)]
    finally:
        doc.close()

    _check_has_text(pages)
    pages = _remove_repeated_lines(pages)
    return compute_doc_id(data), pages


def compute_doc_id(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:16]


# ---------------------------------------------------------------- validation

def _read_bytes(source: str | Path | bytes) -> bytes:
    if isinstance(source, (bytes, bytearray)):
        return bytes(source)
    path = Path(source)
    if not path.is_file():
        raise InvalidPDFError(f"File not found: {path}")
    return path.read_bytes()


def _open_pdf(data: bytes) -> pymupdf.Document:
    # Check the magic bytes first: a .txt renamed to .pdf must be rejected
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


def _check_has_text(pages: list[Page]) -> None:
    with_text = sum(len(p.text) >= MIN_CHARS_PER_PAGE for p in pages)
    if with_text / len(pages) < MIN_TEXT_PAGE_RATIO:
        raise NoTextError(
            "This PDF has no extractable text (it is probably a scanned, "
            "image-only document). OCR is not supported."
        )


# ---------------------------------------------------------------- cleaning

def _clean_text(text: str) -> str:
    for lig, rep in _LIGATURES.items():
        text = text.replace(lig, rep)
    # Soft hyphens / control chars some PDFs use for hyphenation ("ob\x02jects")
    text = re.sub(r"[­\u0002]\n?", "", text)
    # Re-join words split across lines: "recog-\nnising" -> "recognising".
    # Only between lowercase letters, so "VREF-\nCVREF" or "-40°C" are untouched.
    text = re.sub(r"(?<=[a-z])-\n(?=[a-z])", "", text)
    text = text.replace("\t", " ")
    text = re.sub(r"[  ]{2,}", " ", text)
    text = "\n".join(line.strip() for line in text.splitlines())
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _line_key(line: str) -> str:
    # Page numbers change on every page ("DS39689B-page 364", "Page 5 of 10"),
    # so digits are ignored when comparing lines
    return re.sub(r"\d+", "#", line.strip().lower())


def _edge_indices(n_lines: int) -> set[int]:
    # Headers/footers only live at the top or bottom of the page
    return set(range(min(EDGE_LINES, n_lines))) | set(range(max(0, n_lines - EDGE_LINES), n_lines))


def _remove_repeated_lines(pages: list[Page]) -> list[Page]:
    if len(pages) < MIN_PAGES_FOR_HEADER_REMOVAL:
        return pages

    # Count on how many pages each edge line appears (once per page)
    page_lines = [[l for l in p.text.splitlines() if l.strip()] for p in pages]
    counts = Counter()
    for lines in page_lines:
        counts.update({_line_key(lines[i]) for i in _edge_indices(len(lines))})

    threshold = REPEATED_LINE_RATIO * len(pages)
    repeated = {k for k, c in counts.items() if c >= threshold}
    # A line that is only a number at the top/bottom is a page number.
    # Numbers inside the page are kept: in datasheet tables they are data.
    repeated.add("#")

    cleaned = []
    for p, lines in zip(pages, page_lines):
        edges = _edge_indices(len(lines))
        kept = [l for i, l in enumerate(lines)
                if not (i in edges and _line_key(l) in repeated)]
        cleaned.append(Page(page=p.page, text="\n".join(kept)))
    return cleaned


# ---------------------------------------------------------------- quick test
# python -m backend.pdf_loader data/some.pdf

if __name__ == "__main__":
    import sys

    doc_id, pages = load_pdf(sys.argv[1])
    total = sum(len(p.text) for p in pages)
    empty = [p.page for p in pages if not p.text]
    print(f"doc_id: {doc_id} | pages: {len(pages)} | chars: {total}")
    if empty:
        print(f"pages without text: {empty}")
    first = next(p for p in pages if p.text)
    print(f"\n--- page {first.page} (first 800 chars) ---\n{first.text[:800]}")
