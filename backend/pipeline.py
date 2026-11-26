# pipeline.py: RAG orchestrator, joins the two halves of the project:
#   SEARCH: pdf_loader -> chunking -> embeddings -> vector_store -> retriever
#   ANSWER: prompts -> llm
# It doesn't use Streamlit (requirement of the assignment), so the evaluation
# scripts can use it directly. The app uses it through backend/api.py.
# Two ways to get an answer:
# - ask():           waits for the whole answer and returns an Answer (evaluation)
# - answer_stream(): returns the sources + the answer token by token (app)

import re
import time

from backend import config
from backend.pdf_loader import load_pdf
from backend.chunking import chunk_document
from backend.embeddings import embed_chunks
from backend.vector_store import VectorStore
from backend.retriever import Retriever
from backend.prompts import build_rag_messages, clean_answer, is_abstention
from backend.llm import generate, generate_stream
from backend.summarizer import summarize_document
from backend.schemas import Answer, Page


# Settings
DEFAULT_SETTINGS = {
    "model": config.LLM_MODEL,
    "temperature": config.TEMPERATURE,
    "language": None,              # None = same language as the question
    "style": None,                 # None = default rules, or a key of prompts.STYLES
    "k": config.TOP_K,
    "mode": config.SEARCH_MODE,
    "rerank": config.RERANK,
}


def make_settings(settings=None):
    # Defaults + what the app sends (unknown keys are ignored)
    final = dict(DEFAULT_SETTINGS)
    if settings:
        for key, value in settings.items():
            if key in final:
                final[key] = value

    # The app may send "Auto" for the language
    if final["language"] in ("", "Auto", "auto"):
        final["language"] = None
    return final


def cited_pages(text):
    # "... 512 bytes (p. 3) and (p. 12)" to [3, 12]
    pages = set()
    for number in re.findall(r"p\.\s*(\d+)", text):
        pages.add(int(number))
    return sorted(pages)


class RAGPipeline:

    # Setup
    def __init__(self, db_path=config.DB_PATH):
        self.store = VectorStore(path=db_path)
        self.retriever = Retriever(self.store)
        self.docs = {}        # doc_id to {"doc_id", "name", "n_pages", "n_chunks"}
        self.pages = {}       # doc_id to list of Page (needed for the summary)
        self.summaries = {}   # (doc_id, language) to welcome text (made only once)

    # Search Half
    def ingest(self, source, name="document.pdf"):
        # source = path or bytes, returns {"doc_id", "name", "n_pages", "n_chunks"}
        # Raises InvalidPDFError / NoTextError (from pdf_loader) if the PDF is not valid
        doc_id, pages = load_pdf(source)

        if self.store.has_doc(doc_id):
            # Already processed before (even in another session): not done again
            n_chunks = len(self.store.get_chunks(doc_id))
        else:
            chunks = chunk_document(pages, doc_id)
            texts = []
            for chunk in chunks:
                texts.append(chunk.text)
            self.store.add(chunks, embed_chunks(texts))
            self.retriever.forget(doc_id)   # the BM25 index has to be built again
            n_chunks = len(chunks)

        self.pages[doc_id] = pages
        self.docs[doc_id] = {"doc_id": doc_id, "name": name, "n_pages": len(pages), "n_chunks": n_chunks}
        return self.docs[doc_id]

    def retrieve(self, question, doc_id, k=config.TOP_K, mode=config.SEARCH_MODE, rerank=config.RERANK):
        # The k most relevant Chunk of the document
        return self.retriever.retrieve(question, doc_id, k=k, mode=mode, rerank=rerank)

    # Answer Half
    def summarize(self, doc_id, model=config.LLM_MODEL, language="English"):
        # Welcome message, made only once per document and language
        key = (doc_id, language)
        if key not in self.summaries:
            # summarizer.py works with (page_number, text), not with Page objects
            pages = []
            for page in self.get_pages(doc_id):
                pages.append((page.page, page.text))
            self.summaries[key] = summarize_document(pages, model, language)
        return self.summaries[key]

    def build_messages(self, question, chunks, history, language, style):
        # System + last MAX_HISTORY messages of the chat + question with the context
        messages = build_rag_messages(question, chunks, language, style)
        if history:
            recent = []
            for message in history[-config.MAX_HISTORY:]:
                recent.append({"role": message["role"], "content": message["content"]})
            messages = [messages[0]] + recent + [messages[1]]
        return messages

    def ask(self, question, doc_id, history=None, settings=None):
        # Complete answer at once (for the evaluation)
        s = make_settings(settings)
        start = time.perf_counter()

        chunks = self.retrieve(question, doc_id, k=s["k"], mode=s["mode"], rerank=s["rerank"])
        messages = self.build_messages(question, chunks, history, s["language"], s["style"])
        raw, seconds = generate(messages, model=s["model"], temperature=s["temperature"])
        text = clean_answer(raw)

        return Answer(
            text=text,
            pages=cited_pages(text),
            chunks=chunks,
            latency_s=time.perf_counter() - start,
            abstained=is_abstention(raw),
        )

    def answer_stream(self, question, doc_id, history=None, settings=None):
        # For the app: returns (sources, token_stream)
        # sources = [{"page", "text"}] so the app can show them while the answer is written
        s = make_settings(settings)
        chunks = self.retrieve(question, doc_id, k=s["k"], mode=s["mode"], rerank=s["rerank"])
        messages = self.build_messages(question, chunks, history, s["language"], s["style"])

        sources = []
        for chunk in chunks:
            sources.append({"page": chunk.page, "text": chunk.text})

        stream = generate_stream(messages, model=s["model"], temperature=s["temperature"])
        return sources, stream

    # Helpers
    def get_pages(self, doc_id):
        if doc_id in self.pages:
            return self.pages[doc_id]

        # The app was restarted: the chunks are in the database but the pages are not
        # in memory, so we rebuild them from the chunks (enough for the summary)
        by_page = {}
        for chunk in self.store.get_chunks(doc_id):
            if chunk.page not in by_page:
                by_page[chunk.page] = []
            by_page[chunk.page].append(chunk.text)

        if not by_page:
            raise KeyError(f"Document {doc_id} is not loaded. Call ingest() first.")

        pages = []
        for number in sorted(by_page):
            pages.append(Page(page=number, text="\n".join(by_page[number])))
        return pages


# Quick Test of the WHOLE system (needs Ollama open):
# python -m backend.pipeline data/pdfs/74LS157.pdf
if __name__ == "__main__":
    import sys

    pipeline = RAGPipeline()
    info = pipeline.ingest(sys.argv[1], name=sys.argv[1])
    print("Loaded:", info)

    print("\n--- Summary ---")
    print(pipeline.summarize(info["doc_id"]))

    questions = [
        "What is the propagation delay from data to output?",   # answerable, p. 3
        "¿Qué hace la entrada Enable?",                        # in Spanish, p. 2
        "What is the price of this chip?",                     # not in the PDF it prints NOT_FOUND
    ]
    for question in questions:
        answer = pipeline.ask(question, info["doc_id"])
        retrieved = []
        for chunk in answer.chunks:
            retrieved.append(chunk.page)
        print(f"\nQ: {question}\nA: {answer.text}")
        print(f"   cited pages {answer.pages} | retrieved pages {retrieved}"
              f" | abstained {answer.abstained} | {answer.latency_s:.1f} s")

    print("\n--- Streaming ---")
    sources, stream = pipeline.answer_stream("What is the supply voltage?", info["doc_id"])
    source_pages = []
    for source in sources:
        source_pages.append(source["page"])
    print("sources:", source_pages)
    for token in stream:
        print(token, end="", flush=True)
    print()