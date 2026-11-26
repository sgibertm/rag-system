# retriever.py: finds the chunks that answer the question.
# 3 modes (we compare them in eval_retrieval.py):
# - "vector": embeddings, finds chunks with the same MEANING (works across languages)
# - "bm25":   keywords, finds exact words like "TMR0", "VDD" or "74LS157",
#             which embeddings sometimes miss
# - "hybrid": both, combined with Reciprocal Rank Fusion (RRF)
# RRF: each chunk gets 1 / (RRF_K + position) from each list, and we add them up.
# A chunk that is high in both lists wins. We use positions and not scores
# because the BM25 score and the cosine distance have different scales.
# Re-ranking: we retrieve RERANK_CANDIDATES chunks and a cross-encoder
# reads each one together with the question to reorder them. It's slower than
# embeddings but more precise, because it compares the question and the chunk directly.

import re

from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder

from backend import config
from backend.embeddings import embed_query


def tokenize(text):
    # "VDD = 5.0V (p. 3)" to ["vdd", "5", "0v", "p", "3"]
    return re.findall(r"\w+", text.lower())


class Retriever:

    # Setup
    def __init__(self, store):
        self.store = store
        self.bm25_indexes = {}   # doc_id to (BM25 index, chunks), built once per document
        self.reranker = None     # cross-encoder, loaded the first time re-ranking is used

    def get_bm25(self, doc_id):
        if doc_id not in self.bm25_indexes:
            chunks = self.store.get_chunks(doc_id)
            index = None
            if chunks:
                tokenized = []
                for chunk in chunks:
                    tokenized.append(tokenize(chunk.text))
                index = BM25Okapi(tokenized)
            self.bm25_indexes[doc_id] = (index, chunks)
        return self.bm25_indexes[doc_id]

    def forget(self, doc_id):
        # Call this if the document is deleted or loaded again
        self.bm25_indexes.pop(doc_id, None)

    # Search Methods
    def vector_search(self, question, doc_id, k):
        results = self.store.search(embed_query(question), doc_id, k=k)
        chunks = []
        for chunk, distance in results:
            chunks.append(chunk)
        return chunks

    def bm25_search(self, question, doc_id, k):
        index, chunks = self.get_bm25(doc_id)
        if index is None:
            return []

        scores = index.get_scores(tokenize(question))
        # Positions of the chunks, from best to worst score
        positions = sorted(range(len(chunks)), key=lambda i: scores[i], reverse=True)[:k]

        best = []
        for i in positions:
            # Score 0 = no word in common, so it's not useful
            if scores[i] > 0:
                best.append(chunks[i])
        return best

    # Re-ranking
    def rerank(self, question, chunks, k):
        if self.reranker is None:
            print(f"Loading re-ranking model {config.RERANK_MODEL}...")
            self.reranker = CrossEncoder(config.RERANK_MODEL)

        pairs = []
        for chunk in chunks:
            pairs.append((question, chunk.text))
        scores = self.reranker.predict(pairs)

        # Positions of the chunks, from best to worst score
        positions = sorted(range(len(chunks)), key=lambda i: scores[i], reverse=True)[:k]
        best = []
        for i in positions:
            best.append(chunks[i])
        return best

    # Main Function
    def retrieve(self, question, doc_id, k=config.TOP_K, mode=config.SEARCH_MODE, rerank=config.RERANK):
        # Returns a list of k Chunk, the best first
        if not rerank:
            return self.search(question, doc_id, k, mode)

        candidates = self.search(question, doc_id, config.RERANK_CANDIDATES, mode)
        if not candidates:
            return []
        return self.rerank(question, candidates, k)

    def search(self, question, doc_id, k, mode):
        if mode == "vector":
            return self.vector_search(question, doc_id, k)
        if mode == "bm25":
            return self.bm25_search(question, doc_id, k)
        if mode != "hybrid":
            raise ValueError(f"This is an unknown mode: {mode}. Use 'vector', 'bm25' or 'hybrid'")

        vector_results = self.vector_search(question, doc_id, config.CANDIDATES)
        bm25_results = self.bm25_search(question, doc_id, config.CANDIDATES)

        # RRF: add 1 / (RRF_K + position) from each list
        rrf_scores = {}
        chunk_by_id = {}
        for results in (vector_results, bm25_results):
            for position, chunk in enumerate(results):
                score = 1 / (config.RRF_K + position + 1)
                rrf_scores[chunk.chunk_id] = rrf_scores.get(chunk.chunk_id, 0) + score
                chunk_by_id[chunk.chunk_id] = chunk

        best_ids = sorted(rrf_scores, key=rrf_scores.get, reverse=True)[:k]
        best = []
        for chunk_id in best_ids:
            best.append(chunk_by_id[chunk_id])
        return best


# Quick Test (whole search path: pdf_loader, chunking, embeddings, vector_store, retriever):
# python -m backend.retriever data/pdfs/74LS157.pdf "What is the propagation delay?"
if __name__ == "__main__":
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
        texts = []
        for chunk in chunks:
            texts.append(chunk.text)
        store.add(chunks, embed_chunks(texts))
        print(f"Ingested {len(chunks)} chunks in {time.perf_counter() - start:.1f} s")

    retriever = Retriever(store)
    print("Question:", question)
    for mode, rerank in (("vector", False), ("bm25", False), ("hybrid", False), ("hybrid", True)):
        start = time.perf_counter()
        results = retriever.retrieve(question, doc_id, k=3, mode=mode, rerank=rerank)
        seconds = time.perf_counter() - start

        pages_found = []
        for chunk in results:
            pages_found.append(chunk.page)
        name = mode
        if rerank:
            name = mode + " + rerank"
        print(f"\n=== {name} ({seconds:.2f} s) to pages {pages_found}")
        for chunk in results:
            print(f"  [p. {chunk.page}] {chunk.text[:120]!r}")