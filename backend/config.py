# PDF Loading
MIN_CHARS_PER_PAGE = 20           # a page with fewer characters counts as empty
MIN_TEXT_PAGE_RATIO = 0.1         # at least 10% of the pages must have text
REPEATED_LINE_RATIO = 0.5         # a line on 50% of the pages is a header/footer
MIN_PAGES_FOR_HEADER_REMOVAL = 4  # shorter documents are not cleaned
EDGE_LINES = 4                    # lines checked at the top and bottom of each page

# Chunking
CHUNK_SIZE = 1000   # max characters per chunk
OVERLAP = 200       # characters repeated between consecutive chunks
MIN_CHUNK = 50      # shorter chunks are thrown away

# Embeddings
EMBEDDING_MODEL = "intfloat/multilingual-e5-small"  # multilingual
USE_PREFIX = True        # e5 models need "query: " / "passage: "
EMBEDDING_BATCH = 32     # chunks embedded at the same time

# Vector Database (ChromaDB)
DB_PATH = "data/chroma"  # folder of the database
CHROMA_BATCH = 1000      # max chunks saved in one call
# One collection per embedding model: if EMBEDDING_MODEL changes, the PDFs are
# embedded again instead of reusing vectors made by the old model
COLLECTION = "chunks_" + EMBEDDING_MODEL.replace("/", "_")

# Retrieval
TOP_K = 5                # chunks given to the LLM
SEARCH_MODE = "hybrid"   # "vector", "bm25" or "hybrid"
CANDIDATES = 20          # chunks taken from each search before combining them
RRF_K = 60               # standard value from the RRF paper

# LLM (Ollama)
LLM_MODEL = "qwen2.5:3b"   # local open-weight model
TEMPERATURE = 0.1          # low = more precise, high = more creative

# Welcome Summary
MAX_GROUPS = 10            # the document is split in at most 10 groups of pages
CHARS_PER_GROUP = 2500     # characters of each group sent to the LLM
SHORT_DOC_CHARS = 6000     # shorter documents are sent all at once (no groups)
SUMMARY_TEMPERATURE = 0.3  # a bit higher than TEMPERATURE so the welcome sounds natural

# Conversation Memory
MAX_HISTORY = 5   # previous messages of the chat given to the LLM

# Re-ranking
RERANK = False   # default, the app can turn it on from the sidebar
RERANK_MODEL = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"  # open-source, multilingual
RERANK_CANDIDATES = 20   # chunks retrieved first, then reordered by the cross-encoder