# chunking.py: splits every page into small pieces (chunks).
# The LLM can't read a whole datasheet and the embedding model only reads ~512 tokens,
# so each page is cut into chunks of CHUNK_SIZE characters.
# A chunk never mixes two pages (one page to cite), it is cut between lines,
# and consecutive chunks share OVERLAP characters so no sentence is lost.

from backend import config
from backend.schemas import Chunk


# Page Chunking
def split_long_line(line, size):
    # A line longer than the chunk size is cut in pieces (rare, but it happens)
    pieces = []
    for start in range(0, len(line), size):
        pieces.append(line[start:start + size])
    return pieces


def chunk_page(text, chunk_size=config.CHUNK_SIZE, overlap=config.OVERLAP):
    # Returns the chunks (strings) of ONE page
    lines = []
    for line in text.splitlines():
        if len(line) > chunk_size:
            lines.extend(split_long_line(line, chunk_size))
        else:
            lines.append(line)

    chunks = []
    current = []      # lines of the chunk being built
    current_len = 0

    for line in lines:
        # +1 for the "\n" that joins the lines
        if current_len + len(line) + 1 > chunk_size and current:
            chunks.append("\n".join(current))

            # Overlap: the new chunk starts with the last lines of the previous one
            kept = []
            kept_len = 0
            for old_line in reversed(current):
                if kept_len + len(old_line) + 1 > overlap:
                    break
                kept.insert(0, old_line)
                kept_len += len(old_line) + 1
            current = kept
            current_len = kept_len

        current.append(line)
        current_len += len(line) + 1

    if current:
        chunks.append("\n".join(current))

    # Almost empty chunks (page numbers, headers...) are thrown away
    result = []
    for chunk in chunks:
        if len(chunk.strip()) >= config.MIN_CHUNK:
            result.append(chunk.strip())
    return result


# Document Chunking
def chunk_document(pages, doc_id, chunk_size=config.CHUNK_SIZE, overlap=config.OVERLAP):
    # pages = list of Page from pdf_loader, returns a list of Chunk
    all_chunks = []
    for page in pages:
        for i, piece in enumerate(chunk_page(page.text, chunk_size, overlap)):
            all_chunks.append(Chunk(
                text=piece,
                page=page.page,
                chunk_id=f"{doc_id}_p{page.page}_c{i}",
                doc_id=doc_id,
            ))
    return all_chunks


# Quick Test: python -m backend.chunking data/pdfs/74LS157.pdf
if __name__ == "__main__":
    import sys
    from backend.pdf_loader import load_pdf

    doc_id, pages = load_pdf(sys.argv[1])
    chunks = chunk_document(pages, doc_id)

    lengths = []
    for chunk in chunks:
        lengths.append(len(chunk.text))

    print(len(pages), "pages =====>", len(chunks), "chunks")
    print("Chunk length: min", min(lengths), "| max", max(lengths),
          "| mean", round(sum(lengths) / len(lengths)))

    print("\n--- First chunk:", chunks[0].chunk_id, "(page", chunks[0].page, ") ---")
    print(chunks[0].text)