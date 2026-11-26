"""
api.py: the contract between the UI (frontend/) and the backend.

The app only imports these 3 functions. Everything else (chunks, Chroma,
Ollama...) is hidden inside RAGPipeline, so the UI doesn't need to know it.

We create ONE pipeline for the whole app: Streamlit runs app.py again on every
click, but this module is imported only once, so the embedding model and the
database are not loaded again each time.
"""
from collections.abc import Iterator

from backend.pipeline import RAGPipeline

_pipeline = None


def get_pipeline():
    global _pipeline
    if _pipeline is None:
        _pipeline = RAGPipeline()
    return _pipeline


def prepare_document(data: bytes, name: str) -> dict:
    # returns {"doc_id", "name", "n_pages", "n_chunks"}
    # raises an error if it's not a PDF or has no text
    # (InvalidPDFError / NoTextError, both are ValueError: the UI can catch ValueError
    # and show str(error), the message is already written for the user)
    return get_pipeline().ingest(data, name=name)


def summarize(doc_id, language="English") -> Iterator[str]:
    # streams the welcome text
    # (the summary needs several LLM calls first, so the text arrives all together;
    # the second time it's instant because it's saved)
    yield get_pipeline().summarize(doc_id, language=language)


def answer(question, history, doc_id, settings) -> tuple[list[dict], Iterator[str]]:
    # returns (sources, token_stream); each source = {"page", "text"}
    # history = st.session_state.messages WITHOUT the current question
    # settings = dict, keys used: "model", "temperature", "language", "k", "mode"
    #            (other keys are ignored)
    # the LLM may answer prompts.NOT_FOUND: when the stream ends, the UI can check
    # prompts.is_abstention(full_text) to hide the sources
    return get_pipeline().answer_stream(question, doc_id, history, settings)
