def prepare_document(data: bytes, name: str) -> dict: ...
    # returns {"doc_id", "name", "n_pages", "n_chunks"}
    # raises an error if it's not a PDF or has no text

def summarize(doc_id) -> Iterator[str]: ...   # streams the welcome text

def answer(question, history, doc_id, settings) -> tuple[list[dict], Iterator[str]]: ...
    # returns (sources, token_stream); each source = {"page", "text"}