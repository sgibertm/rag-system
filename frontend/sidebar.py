import base64
import html
import time
from pathlib import Path

import streamlit as st

from backend import config
from backend.api import DEFAULT_SETTINGS, STYLES, prepare_document
from frontend.state import reset_conversation


LOGO_PATH = Path(__file__).parent.parent / "assets" / "rag-logo-white.png"

# Value sent to the backend -> short label shown in the UI
LANGUAGES = {"Auto": "Auto", "English": "EN", "Spanish": "ES", "Catalan": "CA", "French": "FR"}
STYLE_LABELS = {"Concise": "Concise", "Descriptive": "Detailed", "Practical examples": "Examples"}
SEARCH_MODES = {"hybrid": "Hybrid", "vector": "Vector", "bm25": "Keyword"}

# Small line icons (Lucide style). They use currentColor, so CSS decides their color.
ICON_FILE = """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"
stroke-linecap="round" stroke-linejoin="round"><path d="M14 3v4a1 1 0 0 0 1 1h4"/>
<path d="M17 21H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h7l5 5v11a2 2 0 0 1-2 2z"/>
<path d="M9 13h6M9 17h4"/></svg>"""
ICON_CPU = """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"
stroke-linecap="round" stroke-linejoin="round"><rect x="6" y="6" width="12" height="12" rx="2"/>
<path d="M9 2v4M15 2v4M9 18v4M15 18v4M2 9h4M2 15h4M18 9h4M18 15h4"/></svg>"""


def section(title, meta=""):
    # Section label; meta = optional text aligned to the right
    meta_html = f'<span class="lsd-section-meta">{meta}</span>' if meta else ""
    st.markdown(f'<div class="lsd-section"><span>{title}</span>{meta_html}</div>',
                unsafe_allow_html=True)


# Brand
@st.cache_data
def logo_base64():
    # Read once: the logo goes inside HTML, so it needs to be base64 text
    return base64.b64encode(LOGO_PATH.read_bytes()).decode()


def render_brand():
    st.markdown(f"""
        <div class="lsd-brand">
            <img class="lsd-brand-logo" src="data:image/png;base64,{logo_base64()}">
            <div class="lsd-brand-text">
                <div class="lsd-brand-name">LSDatasheet</div>
                <div class="lsd-brand-tag">Datasheet assistant</div>
            </div>
        </div>
    """, unsafe_allow_html=True)


# Document Upload
def render_upload():
    section("Document")
    uploaded = st.file_uploader("Upload a PDF", type=["pdf"], label_visibility="collapsed")

    # The file was removed from the uploader
    if uploaded is None:
        if st.session_state.doc is not None:
            st.session_state.doc = None
            st.session_state.doc_key = None
            st.session_state.pdf_bytes = None
            st.session_state.messages = []
        return

    # A new file: process it (only once, not on every rerun)
    file_key = f"{uploaded.name}-{uploaded.size}"
    if file_key != st.session_state.doc_key:
        data = uploaded.getvalue()
        start = time.perf_counter()
        with st.spinner("Reading and indexing the PDF..."):
            try:
                doc = prepare_document(data, uploaded.name)
            except ValueError as error:
                st.session_state.doc = None
                st.session_state.pdf_bytes = None
                st.error(str(error))
                return
        doc["index_seconds"] = time.perf_counter() - start   # shown in the card (latency metric)
        st.session_state.doc = doc
        st.session_state.doc_key = file_key
        st.session_state.pdf_bytes = data      # the viewer needs the original file
        st.session_state.viewer_page = 1
        reset_conversation()

    render_doc_card(st.session_state.doc)


def render_doc_card(doc):
    name = html.escape(doc["name"])
    seconds = doc.get("index_seconds")
    indexed = f" · indexed in {seconds:.1f}s" if seconds else ""
    st.markdown(f"""
        <div class="lsd-doc">
            <div class="lsd-doc-icon">{ICON_FILE}</div>
            <div class="lsd-doc-body">
                <div class="lsd-doc-name" title="{name}">{name}</div>
                <div class="lsd-doc-meta">{doc["n_pages"]:,} pages · {doc["n_chunks"]:,} chunks</div>
            </div>
        </div>
        <div class="lsd-doc-foot"><span class="lsd-live"></span>Ready{indexed}</div>
    """, unsafe_allow_html=True)


# Settings
def render_answer_settings():
    section("Response")

    style = st.segmented_control("Style", list(STYLE_LABELS), format_func=STYLE_LABELS.get,
                                 default="Concise", key="style", width="stretch")
    language = st.pills("Language", list(LANGUAGES), format_func=LANGUAGES.get,
                        default="Auto", key="language", width="stretch",
                        help="Auto = same language as the question")
    temperature = st.slider("Temperature", 0.0, 1.0, DEFAULT_SETTINGS["temperature"], 0.05,
                            help="Low = precise, high = creative")

    # segmented_control and pills return None if the user clicks the selected option again
    return {
        "style": style or "Concise",
        "language": language or "Auto",
        "temperature": temperature,
    }


def render_search_settings():
    section("Retrieval")
    mode = st.segmented_control("Search mode", list(SEARCH_MODES), format_func=SEARCH_MODES.get,
                                default=DEFAULT_SETTINGS["mode"], key="mode", width="stretch")
    k = st.slider("Chunks used", 1, 10, DEFAULT_SETTINGS["k"])
    rerank = st.toggle("Re-ranking", value=DEFAULT_SETTINGS["rerank"],
                       help="Reorders the chunks with a cross-encoder: more precise, a bit slower")
    mode = mode or DEFAULT_SETTINGS["mode"]   # None if the selected option is clicked again
    return {"k": k, "mode": mode, "rerank": rerank}


# Footer
def render_footer():
    if st.button("Clear conversation", icon=":material/restart_alt:", use_container_width=True,
                 disabled=st.session_state.doc is None, type="tertiary"):
        reset_conversation()
        st.rerun()

    # Only reads the model names from config.py, nothing in the backend changes
    llm = html.escape(config.LLM_MODEL)
    embeddings = html.escape(config.EMBEDDING_MODEL.split("/")[-1])
    st.markdown(f"""
        <div class="lsd-workspace">
            <div class="lsd-workspace-icon">{ICON_CPU}</div>
            <div class="lsd-workspace-body">
                <div class="lsd-workspace-name">Local workspace<span class="lsd-live"></span></div>
                <div class="lsd-workspace-meta">{llm} · {embeddings}</div>
            </div>
        </div>
    """, unsafe_allow_html=True)


# Sidebar
def render_sidebar():
    with st.sidebar:
        render_brand()
        render_upload()
        settings = render_answer_settings()
        settings.update(render_search_settings())
        st.session_state.settings = settings
        render_footer()
