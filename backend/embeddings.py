"""
embeddings.py: converts text into vectors (embeddings).

We use a MULTILINGUAL model because the datasheets are in English but
the user can ask in Spanish or Catalan. With a multilingual model,
"¿Cuánta memoria Flash tiene?" and "Flash program memory" get close vectors.

The e5 models need a prefix: "query: " for questions and "passage: " for
chunks. If we change to a model without prefixes, we put USE_PREFIX = False.
"""
from sentence_transformers import SentenceTransformer

MODEL_NAME = "intfloat/multilingual-e5-small"   # ~470 MB, works on CPU
USE_PREFIX = True   # only for e5 models

# The model is loaded only once (loading takes some seconds),
# and then all the calls use the same one
_model = None


def get_model():
    global _model
    if _model is None:
        print(f"Loading embedding model {MODEL_NAME} (only the first time)...")
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def embed_chunks(texts, batch_size=32):
    # texts = list of strings (the chunks) -> list of vectors (list of floats)
    if USE_PREFIX:
        texts = ["passage: " + t for t in texts]
    vectors = get_model().encode(
        texts,
        batch_size=batch_size,
        normalize_embeddings=True,     # length 1, so cosine similarity = dot product
        show_progress_bar=len(texts) > 100,
    )
    return vectors.tolist()


def embed_query(question):
    # one question -> one vector
    if USE_PREFIX:
        question = "query: " + question
    vector = get_model().encode(question, normalize_embeddings=True)
    return vector.tolist()


if __name__ == "__main__":
    # Test: python -m backend.embeddings
    # The question in Spanish should be closer to the Flash chunk than to the Timer chunk
    chunks = [
        "The PIC18F4321 has 8 Kbytes of Flash program memory and 512 bytes of RAM.",
        "Timer0 can be configured as an 8-bit or 16-bit timer/counter.",
    ]
    chunk_vectors = embed_chunks(chunks)
    query_vector = embed_query("¿Cuánta memoria Flash tiene?")

    print("Vector size:", len(query_vector))
    for text, vec in zip(chunks, chunk_vectors):
        # vectors are normalized, so the dot product is the cosine similarity
        similarity = sum(a * b for a, b in zip(query_vector, vec))
        print(round(similarity, 3), "->", text)
