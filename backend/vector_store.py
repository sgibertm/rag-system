"""
vector_store.py: saves the chunks and their embeddings in ChromaDB.

ChromaDB saves everything in a folder (data/chroma), so if we close the
app and open it again, we don't have to process the PDF again.
data/ is in .gitignore, so the database is not uploaded to GitHub.

We calculate the embeddings ourselves (embeddings.py) and give them to
Chroma, so we control which model is used.
"""
import chromadb
from backend.schemas import Chunk

DB_PATH = "data/chroma"
COLLECTION = "chunks"
BATCH = 1000   # Chroma doesn't accept too many chunks in one call


class VectorStore:
    def __init__(self, path=DB_PATH, collection=COLLECTION):
        self.client = chromadb.PersistentClient(path=path)
        # cosine distance: 0 = same meaning, 2 = opposite
        self.collection = self.client.get_or_create_collection(
            name=collection, metadata={"hnsw:space": "cosine"}
        )

    def add(self, chunks, embeddings):
        # chunks = list of Chunk, embeddings = list of vectors (same order)
        for i in range(0, len(chunks), BATCH):
            batch = chunks[i:i + BATCH]
            # upsert = add, or replace if the ID already exists (no duplicates)
            self.collection.upsert(
                ids=[c.chunk_id for c in batch],
                documents=[c.text for c in batch],
                embeddings=embeddings[i:i + BATCH],
                metadatas=[{"page": c.page, "doc_id": c.doc_id} for c in batch],
            )

    def has_doc(self, doc_id):
        # True if this PDF is already in the database
        result = self.collection.get(where={"doc_id": doc_id}, limit=1)
        return len(result["ids"]) > 0

    def search(self, query_embedding, doc_id, k=5):
        # returns the k most similar chunks of ONE document: list of (Chunk, distance)
        result = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
            where={"doc_id": doc_id},
        )
        found = []
        # [0] because we sent only one question
        for cid, text, meta, dist in zip(result["ids"][0], result["documents"][0],
                                         result["metadatas"][0], result["distances"][0]):
            found.append((Chunk(text=text, page=meta["page"], chunk_id=cid, doc_id=meta["doc_id"]), dist))
        return found

    def get_chunks(self, doc_id):
        # all the chunks of a document (the BM25 part of the retriever needs them)
        result = self.collection.get(where={"doc_id": doc_id})
        chunks = []
        for cid, text, meta in zip(result["ids"], result["documents"], result["metadatas"]):
            chunks.append(Chunk(text=text, page=meta["page"], chunk_id=cid, doc_id=meta["doc_id"]))
        # Chroma doesn't keep the order, so we sort by page
        chunks.sort(key=lambda c: c.page)
        return chunks

    def delete_doc(self, doc_id):
        self.collection.delete(where={"doc_id": doc_id})


if __name__ == "__main__":
    # Test: python -m backend.vector_store data/pdfs/74LS157.pdf
    import sys
    from backend.pdf_loader import load_pdf
    from backend.chunking import chunk_document
    from backend.embeddings import embed_chunks, embed_query

    doc_id, pages = load_pdf(sys.argv[1])
    store = VectorStore()

    if store.has_doc(doc_id):
        print("Already in the database, not processing again")
    else:
        chunks = chunk_document(pages, doc_id)
        store.add(chunks, embed_chunks([c.text for c in chunks]))
        print("Saved", len(chunks), "chunks")

    print("Chunks of this document in the database:", len(store.get_chunks(doc_id)))

    question = "What is the propagation delay?"
    print("\nQuestion:", question)
    for chunk, dist in store.search(embed_query(question), doc_id, k=3):
        print(f"\n[p. {chunk.page}] distance {dist:.3f}")
        print(chunk.text[:200])
