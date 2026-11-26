# api.py: the contract between the UI (frontend/) and the backend.
# The app only imports this file. Everything else (chunks, Chroma, Ollama...)
# is hidden inside RAGPipeline, so the UI doesn't need to know it.
# We create ONE pipeline for the whole app: Streamlit runs app.py again on every
# click, but this module is imported only once, so the embedding model and the
# database are not loaded again each time.

from backend.llm import LLMError
from backend.pipeline import DEFAULT_SETTINGS, RAGPipeline
from backend.prompts import STYLES, clean_answer, is_abstention


pipeline = RAGPipeline()


# Functions Used by the App
def prepare_document(data, name):
    # Returns {"doc_id", "name", "n_pages", "n_chunks"}, raises ValueError if the PDF is not valid
    return pipeline.ingest(data, name=name)


def summarize(doc_id, language="English"):
    # Returns the welcome text
    return pipeline.summarize(doc_id, language=language)


def answer(question, history, doc_id, settings):
    # Returns (sources, token_stream)
    # settings keys: "model", "temperature", "language", "style", "k", "mode", "rerank"
    return pipeline.answer_stream(question, doc_id, history, settings)


def finish_answer(full_text):
    # When the stream ends it goes to (clean_text, abstained)
    return clean_answer(full_text), is_abstention(full_text)