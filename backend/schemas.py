# schemas.py: data structures shared by all the backend files.

from dataclasses import dataclass, field

@dataclass
class Page:
    page: int    # page number, starting at 1
    text: str    # cleaned text of the page

@dataclass
class Chunk:
    text: str
    page: int    # page of the chunk, used to cite sources
    chunk_id: str
    doc_id: str

@dataclass
class Answer:
    text: str
    pages: list = field(default_factory=list)    # pages cited in the answer
    chunks: list = field(default_factory=list)   # chunks given to the LLM
    latency_s: float = 0.0                       # response time in seconds
    abstained: bool = False                      # True if the LLM said it couldn't find it