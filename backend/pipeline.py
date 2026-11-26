"""
pipeline.py: RAG orchestrator. Joins the two halves of the project:

    SEARCH:   pdf_loader -> chunking -> embeddings -> vector_store -> retriever
    ANSWER:   prompts -> llm

It doesn't use Streamlit (requirement of the assignment), so the evaluation
scripts can use it directly. The app uses it through backend/api.py.

Two ways to get an answer:
- ask()          -> waits for the whole answer and returns an Answer (for eval_llm.py)
- answer_stream()-> returns the sources + the answer token by token (for the app)
"""
import re
import time

from backend.pdf_loader import load_pdf
from backend.chunking import chunk_document
from backend.embeddings import embed_chunks
from backend.vector_store import VectorStore
from backend.retriever import Retriever
from backend.prompts import build_rag_messages, clean_answer, is_abstention
from backend.llm import generate, generate_stream
from backend.summarizer import summarize_document
from backend.schemas import Answer, Page

# Default settings. The app can change any of them (sidebar), the rest stay like this.
DEFAULT_SETTINGS = {
    "model": "qwen2.5:3b",   # Ollama model (Experiment 3: change it here)
    "temperature": 0.1,
    "language": None,        # None = same language as the question
    "k": 5,                  # chunks given to the LLM
    "mode": "hybrid",        # "vector", "bm25" or "hybrid" (Experiment 2)
}
HISTORY_MESSAGES = 4   # last messages of the chat we give to the LLM (2 questions + 2 answers)


def make_settings(settings=None):
    # mix the defaults with what the app sends (unknown keys like "style" are ignored)
    final = dict(DEFAULT_SETTINGS)
    for key, value in (settings or {}).items():
        if key in final:
            final[key] = value
    # the app may send "Auto" for the language
    if final["language"] in ("", "Auto", "auto"):
        final["language"] = None
    return final


def cited_pages(text):
    # "... 512 bytes (p. 3) and (p. 12)" -> [3, 12]
    pages = [int(n) for n in re.findall(r"p\.\s*(\d+)", text)]
    return sorted(set(pages))


class RAGPipeline:
    def __init__(self, db_path="data/chroma"):
        self.store = VectorStore(path=db_path)
        self.retriever = Retriever(self.store)
        self.docs = {}        # doc_id -> {"doc_id", "name", "n_pages", "n_chunks"}
        self.pages = {}       # doc_id -> list of Page (needed for the summary)
        self.summaries = {}   # doc_id -> welcome text (so we only make it once)

    # ---------------------------------------------------------------- SEARCH half

    def ingest(self, source, name="document.pdf"):
        # source = path of the PDF or its bytes (Streamlit's uploaded_file.getvalue())
        # returns {"doc_id", "name", "n_pages", "n_chunks"}
        # raises InvalidPDFError / NoTextError (from pdf_loader) if the PDF is not valid
        doc_id, pages = load_pdf(source)

        if self.store.has_doc(doc_id):
            # already processed before (even in another session): we don't do it again
            n_chunks = len(self.store.get_chunks(doc_id))
        else:
            chunks = chunk_document(pages, doc_id)
            self.store.add(chunks, embed_chunks([c.text for c in chunks]))
            self.retriever.forget(doc_id)   # the BM25 index has to be built again
            n_chunks = len(chunks)

        self.pages[doc_id] = pages
        self.docs[doc_id] = {"doc_id": doc_id, "name": name,
                             "n_pages": len(pages), "n_chunks": n_chunks}
        return self.docs[doc_id]

    def retrieve(self, question, doc_id, k=5, mode="hybrid"):
        # returns the k most relevant Chunk of the document
        return self.retriever.retrieve(question, doc_id, k=k, mode=mode)

    # ---------------------------------------------------------------- ANSWER half

    def summarize(self, doc_id, model=DEFAULT_SETTINGS["model"], language="English"):
        # welcome message of the document (made only once per document)
        if doc_id not in self.summaries:
            pages = self._get_pages(doc_id)
            # summarizer.py works with (page_number, text), not with Page objects
            pages = [(p.page, p.text) for p in pages]
            self.summaries[doc_id] = summarize_document(pages, model, language)
        return self.summaries[doc_id]

    def _build_messages(self, question, chunks, history, language):
        # system + last messages of the chat + question with the context
        messages = build_rag_messages(question, chunks, language)
        if history:
            recent = [{"role": m["role"], "content": m["content"]}
                      for m in history[-HISTORY_MESSAGES:]]
            messages = [messages[0]] + recent + [messages[1]]
        return messages

    def ask(self, question, doc_id, history=None, settings=None):
        # complete answer at once (for the evaluation)
        s = make_settings(settings)
        start = time.perf_counter()
        chunks = self.retrieve(question, doc_id, k=s["k"], mode=s["mode"])
        messages = self._build_messages(question, chunks, history, s["language"])
        raw, _ = generate(messages, model=s["model"], temperature=s["temperature"])
        text = clean_answer(raw)
        return Answer(
            text=text,
            pages=cited_pages(text),
            chunks=chunks,
            latency_s=time.perf_counter() - start,
            abstained=is_abstention(raw),
        )

    def answer_stream(self, question, doc_id, history=None, settings=None):
        # for the app: returns (sources, token_stream)
        # sources = [{"page", "text"}] so the app can show them while the answer is written
        s = make_settings(settings)
        chunks = self.retrieve(question, doc_id, k=s["k"], mode=s["mode"])
        messages = self._build_messages(question, chunks, history, s["language"])
        sources = [{"page": c.page, "text": c.text} for c in chunks]
        stream = generate_stream(messages, model=s["model"], temperature=s["temperature"])
        return sources, stream

    # ---------------------------------------------------------------- helpers

    def _get_pages(self, doc_id):
        if doc_id in self.pages:
            return self.pages[doc_id]
        # the app was restarted: the chunks are in the database but the pages are not
        # in memory, so we rebuild them from the chunks (enough for the summary)
        by_page = {}
        for c in self.store.get_chunks(doc_id):
            by_page.setdefault(c.page, []).append(c.text)
        if not by_page:
            raise KeyError(f"Document {doc_id} is not loaded. Call ingest() first.")
        return [Page(page=n, text="\n".join(texts)) for n, texts in sorted(by_page.items())]


if __name__ == "__main__":
    # Test of the WHOLE system (needs Ollama open with qwen2.5:3b):
    # python -m backend.pipeline data/pdfs/74LS157.pdf
    import sys

    pipeline = RAGPipeline()
    info = pipeline.ingest(sys.argv[1], name=sys.argv[1])
    print("Loaded:", info)

    print("\n--- Summary ---")
    print(pipeline.summarize(info["doc_id"]))

    questions = [
        "What is the propagation delay from data to output?",   # answerable, p. 3
        "¿Qué hace la entrada Enable?",                        # in Spanish, p. 2
        "What is the price of this chip?",                     # not in the PDF -> NOT_FOUND
    ]
    for q in questions:
        answer = pipeline.ask(q, info["doc_id"])
        print(f"\nQ: {q}\nA: {answer.text}")
        print(f"   cited pages {answer.pages} | retrieved pages {[c.page for c in answer.chunks]}"
              f" | abstained {answer.abstained} | {answer.latency_s:.1f} s")

    print("\n--- Streaming ---")
    sources, stream = pipeline.answer_stream("What is the supply voltage?", info["doc_id"])
    print("sources:", [s["page"] for s in sources])
    for token in stream:
        print(token, end="", flush=True)
    print()
