"""
retriever.py: finds the chunks that answer the question.

3 modes (we compare them in eval_retrieval.py):
- "vector": embeddings (finds chunks with the same MEANING, works across languages)
- "bm25":   keywords (finds exact words like "TMR0", "VDD", "74LS157",
            which embeddings sometimes miss)
- "hybrid": both, combined with Reciprocal Rank Fusion (RRF)

RRF: each chunk gets 1 / (RRF_K + position) from each list, and we add them.
A chunk that is high in both lists wins. We use positions and not scores
because the BM25 score and the cosine distance are in different scales.
"""
import re
from rank_bm25 import BM25Okapi
from backend.embeddings import embed_query

RRF_K = 60          # standard value from the RRF paper
CANDIDATES = 20     # how many chunks we take from each method before combining


def tokenize(text):
    # "VDD = 5.0V (p. 3)" -> ["vdd", "5", "0v", "p", "3"]
    return re.findall(r"\w+", text.lower())


class Retriever:
    def __init__(self, store):
        self.store = store
        self._bm25 = {}   # doc_id -> (BM25 index, chunks), built once per document

    def _get_bm25(self, doc_id):
        if doc_id not in self._bm25:
            chunks = self.store.get_chunks(doc_id)
            index = BM25Okapi([tokenize(c.text) for c in chunks]) if chunks else None
            self._bm25[doc_id] = (index, chunks)
        return self._bm25[doc_id]

    def vector_search(self, question, doc_id, k):
        results = self.store.search(embed_query(question), doc_id, k=k)
        return [chunk for chunk, dist in results]

    def bm25_search(self, question, doc_id, k):
        index, chunks = self._get_bm25(doc_id)
        if index is None:
            return []
        scores = index.get_scores(tokenize(question))
        # positions of the chunks sorted from best to worst score
        best = sorted(range(len(chunks)), key=lambda i: scores[i], reverse=True)[:k]
        # score 0 = no word in common, so it's not useful
        return [chunks[i] for i in best if scores[i] > 0]

    def retrieve(self, question, doc_id, k=5, mode="hybrid"):
        # returns a list of k Chunk, the best first
        if mode == "vector":
            return self.vector_search(question, doc_id, k)
        if mode == "bm25":
            return self.bm25_search(question, doc_id, k)
        if mode != "hybrid":
            raise ValueError(f"Unknown mode: {mode}. Use 'vector', 'bm25' or 'hybrid'")

        rrf_scores = {}
        chunk_by_id = {}
        for results in (self.vector_search(question, doc_id, CANDIDATES),
                        self.bm25_search(question, doc_id, CANDIDATES)):
            for position, chunk in enumerate(results):
                rrf_scores[chunk.chunk_id] = rrf_scores.get(chunk.chunk_id, 0) + 1 / (RRF_K + position + 1)
                chunk_by_id[chunk.chunk_id] = chunk

        best_ids = sorted(rrf_scores, key=rrf_scores.get, reverse=True)[:k]
        return [chunk_by_id[cid] for cid in best_ids]

    def forget(self, doc_id):
        # call this if the document is deleted or loaded again
        self._bm25.pop(doc_id, None)


if __name__ == "__main__":
    # Test of the whole critical path (pdf_loader -> chunking -> embeddings -> vector_store -> retriever):
    # python -m backend.retriever data/pdfs/74LS157.pdf "What is the propagation delay?"
    import sys
    import time
    from backend.pdf_loader import load_pdf
    from backend.chunking import chunk_document
    from backend.embeddings import embed_chunks
    from backend.vector_store import VectorStore

    path = sys.argv[1]
    question = sys.argv[2] if len(sys.argv) > 2 else "What is the supply voltage?"

    store = VectorStore()
    doc_id, pages = load_pdf(path)
    if not store.has_doc(doc_id):
        start = time.perf_counter()
        chunks = chunk_document(pages, doc_id)
        store.add(chunks, embed_chunks([c.text for c in chunks]))
        print(f"Ingested {len(chunks)} chunks in {time.perf_counter() - start:.1f} s")

    retriever = Retriever(store)
    print("Question:", question)
    for mode in ("vector", "bm25", "hybrid"):
        start = time.perf_counter()
        results = retriever.retrieve(question, doc_id, k=3, mode=mode)
        seconds = time.perf_counter() - start
        print(f"\n=== {mode} ({seconds:.2f} s) -> pages {[c.page for c in results]}")
        for c in results:
            print(f"  [p. {c.page}] {c.text[:120]!r}")
