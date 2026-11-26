import html

import streamlit as st

from backend.api import DEFAULT_SETTINGS, STYLES, prepare_document
from frontend.state import reset_conversation


LANGUAGES = ["Auto", "English", "Spanish", "Catalan", "French"]
SEARCH_MODES = ["hybrid", "vector", "bm25"]


def section(title):
    st.markdown(f'<div class="lsd-section">{title}</div>', unsafe_allow_html=True)


# Brand
def render_brand():
    st.markdown("""
        <div class="lsd-brand">
            <div class="lsd-brand-icon">📘</div>
            <div>
                <div class="lsd-brand-name">LSDatasheet</div>
                <div class="lsd-brand-tag">Your datasheet assistant</div>
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
            st.session_state.messages = []
        return

    # A new file: process it (only once, not on every rerun)
    file_key = f"{uploaded.name}-{uploaded.size}"
    if file_key != st.session_state.doc_key:
        with st.spinner("Reading and indexing the PDF..."):
            try:
                st.session_state.doc = prepare_document(uploaded.getvalue(), uploaded.name)
            except ValueError as error:
                st.session_state.doc = None
                st.error(str(error))
                return
        st.session_state.doc_key = file_key
        reset_conversation()

    render_doc_card(st.session_state.doc)


def render_doc_card(doc):
    name = html.escape(doc["name"])
    st.markdown(f"""
        <div class="lsd-doc-card">
            <div class="lsd-doc-name">📄 {name}</div>
            <div class="lsd-doc-stats">
                <span class="lsd-chip">{doc["n_pages"]} pages</span>
                <span class="lsd-chip">{doc["n_chunks"]} chunks</span>
            </div>
        </div>
    """, unsafe_allow_html=True)


# Settings
def render_settings():
    section("Answer")
    language = st.selectbox("Language", LANGUAGES, help="Auto = same language as the question")
    style = st.selectbox("Style", list(STYLES))
    temperature = st.slider("Temperature", 0.0, 1.0, DEFAULT_SETTINGS["temperature"], 0.05,
                            help="Low = precise, high = creative")

    section("Search")
    k = st.slider("Chunks used", 1, 10, DEFAULT_SETTINGS["k"])
    mode = st.selectbox("Search mode", SEARCH_MODES, index=SEARCH_MODES.index(DEFAULT_SETTINGS["mode"]))
    rerank = st.toggle("Re-ranking", value=DEFAULT_SETTINGS["rerank"],
                       help="Reorders the chunks with a cross-encoder: more precise, a bit slower")

    st.session_state.settings = {
        "language": language,
        "style": style,
        "temperature": temperature,
        "k": k,
        "mode": mode,
        "rerank": rerank,
    }


# Sidebar
def render_sidebar():
    with st.sidebar:
        render_brand()
        render_upload()
        render_settings()

        st.write("")
        if st.button("Clear conversation", use_container_width=True, disabled=st.session_state.doc is None):
            reset_conversation()
            st.rerun()