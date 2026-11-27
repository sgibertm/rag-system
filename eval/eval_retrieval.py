"""
eval_retrieval.py: Experiments 1 and 2 (embedding models and chunking).
A hit means that at least one of the top-k chunks comes from a page listed in "pages" of questions.json.
Only the answerable questions with pages are used for Hit@3 and Hit@5.

Run from the repo root, with the PDFs in data/ (same names as in eval/questions.json):
  python -m eval.eval_retrieval embeddings   -> Experiment 1: compare embedding models (chunking fixed)
  python -m eval.eval_retrieval chunking     -> Experiment 2: compare chunking configs (best embedding)
  python -m eval.eval_retrieval save         -> saves eval/retrieved.json for eval_llm.py (Experiment 3)
"""
import csv
import json
import os
import platform
import sys
import time
from dataclasses import asdict

import numpy as np
from sentence_transformers import SentenceTransformer

from backend.pdf_loader import load_pdf
from backend.schemas import Chunk

DATA_DIR = "data"
QUESTIONS = "eval/questions.json"
RESULTS = "eval/results_retrieval.csv"
RETRIEVED = "eval/retrieved.json"

# Embedding models: name -> (prefix for the question, prefix for the chunks)
# e5 needs "query: " / "passage: "; bge recommends an instruction for the question
EMBEDDING_MODELS = {
    "sentence-transformers/all-MiniLM-L6-v2": ("", ""),
    "BAAI/bge-small-en-v1.5": ("Represent this sentence for searching relevant passages: ", ""),
    "intfloat/multilingual-e5-small": ("query: ", "passage: "),
}
FIXED_CHUNKING = (800, 150)  # (chunk_size, overlap) in characters, used in Experiment 1
CHUNK_CONFIGS = [(400, 80), (800, 150), (1500, 300)]  # Experiment 2

# Fill these after running Experiments 1 and 2 (they are used by "chunking" and "save")
BEST_EMBEDDING = "intfloat/multilingual-e5-small"
BEST_CHUNKING = (800, 150)

TOP_K = 5
MIN_CHUNK_CHARS = 30

questions = json.load(open(QUESTIONS, encoding="utf-8"))
documents = sorted({q["document"] for q in questions})

missing = [d for d in documents if not os.path.exists(os.path.join(DATA_DIR, d))]
if missing:
    print("Missing PDFs in", DATA_DIR + "/:", missing)
    sys.exit(1)

# The PDFs are read only once, the loader gives the doc_id and the pages with their number (starting at 1)
loaded = {d: load_pdf(os.path.join(DATA_DIR, d)) for d in documents}


def evaluate(model_name, chunk_size, overlap):
    # Builds one index per PDF, asks every question and returns the metrics
    model = SentenceTransformer(model_name)
    q_prefix, p_prefix = EMBEDDING_MODELS[model_name]
    # The first call is slow, so we do not time it
    model.encode(["warm up"])

    # Prepare the documents: chunks never cross a page, so every chunk keeps its page number
    index = {}
    start_time = time.perf_counter()
    for doc in documents:
        doc_id, pages = loaded[doc]
        chunks = []
        for page in pages:
            start = 0
            while start < len(page.text):
                piece = page.text[start:start + chunk_size].strip()
                if len(piece) >= MIN_CHUNK_CHARS:
                    chunks.append(Chunk(text=piece, page=page.page, chunk_id=f"{doc_id}-{len(chunks)}", doc_id=doc_id))
                start += chunk_size - overlap
        vectors = model.encode([p_prefix + c.text for c in chunks], normalize_embeddings=True, batch_size=32, show_progress_bar=False)
        index[doc] = (chunks, vectors)
    prep_seconds = time.perf_counter() - start_time

    # Ask the questions
    hits3 = hits5 = counted = 0
    query_seconds = 0
    retrieved = {}
    for q in questions:
        chunks, vectors = index[q["document"]]
        t = time.perf_counter()
        query_vector = model.encode([q_prefix + q["question"]], normalize_embeddings=True)[0]
        # Cosine similarity (vectors are normalized)
        top = np.argsort(-(vectors @ query_vector))[:TOP_K]
        query_seconds += time.perf_counter() - t
        retrieved[str(q["id"])] = [asdict(chunks[i]) for i in top]
        if q["answerable"] and q["pages"]:
            counted += 1
            hits3 += any(chunks[i].page in q["pages"] for i in top[:3])
            hits5 += any(chunks[i].page in q["pages"] for i in top[:5])

    return {
        "hit3": hits3 / counted, "hit5": hits5 / counted, "questions": counted,
        "prep_seconds": prep_seconds, "avg_query_ms": query_seconds / len(questions) * 1000,
        "chunks": sum(len(c) for c, _ in index.values()), "retrieved": retrieved,
    }


mode = sys.argv[1] if len(sys.argv) > 1 else ""
if mode == "embeddings":
    experiments = [(m, FIXED_CHUNKING) for m in EMBEDDING_MODELS]
elif mode == "chunking":
    experiments = [(BEST_EMBEDDING, c) for c in CHUNK_CONFIGS]
elif mode == "save":
    experiments = [(BEST_EMBEDDING, BEST_CHUNKING)]
else:
    print("Usage: python -m eval.eval_retrieval embeddings | chunking | save")
    sys.exit(1)

# The assignment asks to always note down the hardware
print("Hardware:", platform.platform(), "|", platform.processor(), "| CPUs:", os.cpu_count())

new_file = not os.path.exists(RESULTS)
with open(RESULTS, "a", newline="", encoding="utf-8-sig") as f:
    writer = csv.writer(f, delimiter=";")
    if new_file:
        writer.writerow(["experiment", "embedding_model", "chunk_size", "overlap", "questions", "hit@3", "hit@5", "prep_seconds", "avg_query_ms", "chunks"])
    for model_name, (size, overlap) in experiments:
        r = evaluate(model_name, size, overlap)
        print(f"{model_name} | chunks {size}/{overlap} | Hit@3 {r['hit3']:.3f} | Hit@5 {r['hit5']:.3f} | "
              f"prep {r['prep_seconds']:.1f} s | query {r['avg_query_ms']:.1f} ms | {r['chunks']} chunks")
        writer.writerow([mode, model_name, size, overlap, r["questions"], round(r["hit3"], 3), round(r["hit5"], 3), round(r["prep_seconds"], 1), round(r["avg_query_ms"], 1), r["chunks"]])
        if mode == "save":
            json.dump(r["retrieved"], open(RETRIEVED, "w", encoding="utf-8"), ensure_ascii=False)
            print("Saved", RETRIEVED, "for eval_llm.py")
