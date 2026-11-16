# RAG Orchestrator: combines ingestion, chunking, embeddings, retrieval, and LLM
# Must work without Streamlit (requirement from the assignment)
from backend.schemas import Chunk, Answer


class RAGPipeline:
    def ingest(self, pdf_path: str) -> str:
        # Loads a PDF and returns a document ID
        raise NotImplementedError  # TODO

    def summarize(self, doc_id: str) -> str:
        # Summarizes the entire document
        raise NotImplementedError  # TODO

    def retrieve(self, question: str, k: int = 5) -> list[Chunk]:
        # Returns the k most relevant chunks
        raise NotImplementedError  # TODO

    def ask(self, question: str, history: list | None = None) -> Answer:
        # Recupera chunks y genera la respuesta con páginas citadas
        raise NotImplementedError  # TODO
    