# vector_store.py: saves the chunks and their embeddings in ChromaDB.
# ChromaDB keeps everything in a folder (DB_PATH), so if we close the app and
# open it again, we don't have to process the PDF again.
# We compute the embeddings ourselves (embeddings.py) and give them to Chroma,
# so we control which model is used.

import chromadb

from backend import config
from backend.schemas import Chunk


class VectorStore:

    # Setup
    def __init__(self, path=config.DB_PATH, collection=config.COLLECTION):
        self.client = chromadb.PersistentClient(path=path)
        # Cosine distance: 0 = same meaning, 2 = opposite
        self.collection = self.client.get_or_create_collection(
            name=collection, metadata={"hnsw:space": "cosine"}
        )

    # Saving
    def add(self, chunks, embeddings):
        # chunks = list of Chunk, embeddings = list of vectors (same order)
        for start in range(0, len(chunks), config.CHROMA_BATCH):
            end = start + config.CHROMA_BATCH
            batch = chunks[start:end]

            ids = []
            documents = []
            metadatas = []
            for chunk in batch:
                ids.append(chunk.chunk_id)
                documents.append(chunk.text)
                metadatas.append({"page": chunk.page, "doc_id": chunk.doc_id})

            # upsert = add, or replace if the id already exists (no duplicates)
            self.collection.upsert(
                ids=ids,
                documents=documents,
                embeddings=embeddings[start:end],
                metadatas=metadatas,
            )

    def delete_doc(self, doc_id):
        self.collection.delete(where={"doc_id": doc_id})

    # Reading
    def has_doc(self, doc_id):
        # True if this PDF is already in the database
        result = self.collection.get(where={"doc_id": doc_id}, limit=1)
        return len(result["ids"]) > 0

    def search(self, query_embedding, doc_id, k=5):
        # The k most similar chunks of ONE document to list of (Chunk, distance)
        result = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
            where={"doc_id": doc_id},
        )

        # [0] because we sent only one question
        ids = result["ids"][0]
        texts = result["documents"][0]
        metas = result["metadatas"][0]
        distances = result["distances"][0]

        found = []
        for chunk_id, text, meta, distance in zip(ids, texts, metas, distances):
            chunk = Chunk(text=text, page=meta["page"], chunk_id=chunk_id, doc_id=meta["doc_id"])
            found.append((chunk, distance))
        return found

    def get_chunks(self, doc_id):
        # All the chunks of a document (the BM25 search needs them)
        result = self.collection.get(where={"doc_id": doc_id})

        chunks = []
        for chunk_id, text, meta in zip(result["ids"], result["documents"], result["metadatas"]):
            chunks.append(Chunk(text=text, page=meta["page"], chunk_id=chunk_id, doc_id=meta["doc_id"]))

        # Chroma doesn't keep the order, so we sort by page
        chunks.sort(key=lambda chunk: chunk.page)
        return chunks


# Quick Test: python -m backend.vector_store data/pdfs/74LS157.pdf
if __name__ == "__main__":
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
        texts = []
        for chunk in chunks:
            texts.append(chunk.text)
        store.add(chunks, embed_chunks(texts))
        print("Saved", len(chunks), "chunks")

    print("Chunks of this document in the database:", len(store.get_chunks(doc_id)))

    question = "What is the propagation delay?"
    print("\nQuestion:", question)
    for chunk, distance in store.search(embed_query(question), doc_id, k=3):
        print(f"\n[p. {chunk.page}] distance {distance:.3f}")
        print(chunk.text[:200])