"""
chunking.py: splits the pages into small pieces (chunks).

Why: the LLM can't read 400 pages at once, and the embedding model only
reads ~512 tokens. So we cut each page into chunks of ~CHUNK_SIZE characters.

Rules:
- A chunk never mixes two pages, so each chunk has ONE page to cite.
- We cut between lines (not in the middle of a word or a table row).
- Consecutive chunks share OVERLAP characters, so if an important
  sentence is cut, it appears complete in one of the two chunks.
"""
from backend.schemas import Chunk

CHUNK_SIZE = 1000   # max characters per chunk (Experiment: try 500 / 1000 / 1500)
OVERLAP = 200       # characters repeated between consecutive chunks
MIN_CHUNK = 50      # chunks shorter than this are thrown away (page numbers, headers...)


def split_long_line(line, size):
    # a line longer than the chunk size is cut in pieces (rare, but it happens)
    return [line[i:i + size] for i in range(0, len(line), size)]


def chunk_page(text, chunk_size=CHUNK_SIZE, overlap=OVERLAP):
    # returns a list of strings (the chunks of ONE page)
    lines = []
    for line in text.splitlines():
        if len(line) > chunk_size:
            lines.extend(split_long_line(line, chunk_size))
        else:
            lines.append(line)

    chunks = []
    current = []        # lines of the chunk we are building
    current_len = 0

    for line in lines:
        # +1 because of the "\n" that joins the lines
        if current_len + len(line) + 1 > chunk_size and current:
            chunks.append("\n".join(current))

            # overlap: the new chunk starts with the last lines of the previous one
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

    # remove chunks that are almost empty
    return [c.strip() for c in chunks if len(c.strip()) >= MIN_CHUNK]


def chunk_document(pages, doc_id, chunk_size=CHUNK_SIZE, overlap=OVERLAP):
    # pages = list of Page(page, text) from pdf_loader.load_pdf
    # returns a list of Chunk (see schemas.py)
    all_chunks = []
    for p in pages:
        for i, piece in enumerate(chunk_page(p.text, chunk_size, overlap)):
            all_chunks.append(Chunk(
                text=piece,
                page=p.page,
                chunk_id=f"{doc_id}_p{p.page}_c{i}",   # unique ID, e.g. "a1b2c3_p12_c0"
                doc_id=doc_id,
            ))
    return all_chunks


if __name__ == "__main__":
    # Test: python -m backend.chunking data/pdfs/74LS157.pdf
    import sys
    from backend.pdf_loader import load_pdf

    doc_id, pages = load_pdf(sys.argv[1])
    chunks = chunk_document(pages, doc_id)

    lengths = [len(c.text) for c in chunks]
    print(len(pages), "pages ->", len(chunks), "chunks")
    print("Chunk length: min", min(lengths), "| max", max(lengths),
          "| mean", round(sum(lengths) / len(lengths)))
    print("\n--- First chunk:", chunks[0].chunk_id, "(page", chunks[0].page, ") ---")
    print(chunks[0].text)
