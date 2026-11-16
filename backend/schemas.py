# Structure shared between all backend modules
from dataclasses import dataclass, field

@dataclass
class Page:
    page: int        # page number (starting at 1)
    text: str        # cleaned text of the page (output of pdf_loader)

@dataclass
class Chunk:
    text: str
    page: int        # page number (starting at 1), for citing sources
    chunk_id: str
    doc_id: str

@dataclass
class Answer:
    text: str                                    # LLM answer
    pages: list[int] = field(default_factory=list)       # Cited pages
    chunks: list[Chunk] = field(default_factory=list)    # Used chunks
    latency_s: float = 0.0                       # Response time in seconds