# embeddings.py: converts text into vectors (embeddings).
# We use a MULTILINGUAL model because the datasheets are in English but the
# user can ask in Spanish or Catalan: "¿Cuánta memoria Flash tiene?" and
# "Flash program memory" get close vectors.
# The e5 models need a prefix: "query: " for questions and "passage: " for chunks.

from sentence_transformers import SentenceTransformer
from backend import config


# Model Loading (once, when this file is imported)
print(f"Loading embedding model {config.EMBEDDING_MODEL}...")
model = SentenceTransformer(config.EMBEDDING_MODEL)


# Embedding
def embed_chunks(texts, batch_size=config.EMBEDDING_BATCH):
    # texts = list of chunk texts to list of vectors (list of floats)
    if config.USE_PREFIX:
        prefixed = []
        for text in texts:
            prefixed.append("passage: " + text)
        texts = prefixed

    vectors = model.encode(
        texts,
        batch_size=batch_size,
        normalize_embeddings=True,          # length 1, so cosine similarity = dot product
        show_progress_bar=len(texts) > 100,
    )
    return vectors.tolist()


def embed_query(question):
    # One question to one vector
    if config.USE_PREFIX:
        question = "query: " + question

    vector = model.encode(question, normalize_embeddings=True)
    return vector.tolist()


# Quick Test: python -m backend.embeddings
# The Spanish question should be closer to the Flash chunk than to the Timer chunk
if __name__ == "__main__":
    chunks = [
        "The PIC18F4321 has 8 Kbytes of Flash program memory and 512 bytes of RAM.",
        "Timer0 can be configured as an 8-bit or 16-bit timer/counter.",
    ]
    chunk_vectors = embed_chunks(chunks)
    query_vector = embed_query("¿Cuánta memoria Flash tiene?")

    print("Vector size:", len(query_vector))
    for text, vector in zip(chunks, chunk_vectors):
        # Vectors are normalized, so the dot product is the cosine similarity
        similarity = 0
        for a, b in zip(query_vector, vector):
            similarity += a * b
        print(round(similarity, 3), "->", text)