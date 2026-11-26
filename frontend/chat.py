import html

import streamlit as st

from backend.api import LLMError, answer, finish_answer, summarize
from frontend.state import add_message


USER_AVATAR = "🧑‍🎓"
ASSISTANT_AVATAR = "📘"


# Header
def render_header():
    st.markdown("""
        <div class="lsd-header">
            <div class="lsd-title">LSDatasheet</div>
            <div class="lsd-subtitle">Chat with your datasheets: answers with page references.</div>
            <span class="lsd-badge">● Runs locally</span>
        </div>
    """, unsafe_allow_html=True)


# Empty State (before any PDF is uploaded)
def render_empty_state():
    st.markdown("""
        <div class="lsd-empty">
            <h3>Start by uploading a datasheet</h3>
            Upload a PDF in the sidebar and ask anything about it.
            <div class="lsd-steps">
                <div class="lsd-step">
                    <div class="lsd-step-number">1</div>
                    <div class="lsd-step-title">Upload</div>
                    <div class="lsd-step-text">A datasheet, manual or exam in PDF.</div>
                </div>
                <div class="lsd-step">
                    <div class="lsd-step-number">2</div>
                    <div class="lsd-step-title">Read</div>
                    <div class="lsd-step-text">It is split, embedded and summarized.</div>
                </div>
                <div class="lsd-step">
                    <div class="lsd-step-number">3</div>
                    <div class="lsd-step-title">Ask</div>
                    <div class="lsd-step-text">Get answers with the pages they come from.</div>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)


# Sources
def render_sources(sources):
    pages = []
    for source in sources:
        if source["page"] not in pages:
            pages.append(source["page"])
    pages.sort()

    pills = ""
    for page in pages:
        pills += f'<span class="lsd-page-pill">p. {page}</span>'
    st.markdown(f'<div class="lsd-pages">Sources: {pills}</div>', unsafe_allow_html=True)

    with st.expander(f"See the text used ({len(sources)} passages)"):
        for source in sources:
            text = html.escape(source["text"])
            # One line: the chunk box keeps line breaks (pre-wrap), so no extra spaces here
            chunk_html = f'<div class="lsd-chunk"><div class="lsd-chunk-page">PAGE {source["page"]}</div>{text}</div>'
            st.markdown(chunk_html, unsafe_allow_html=True)


# Messages
def render_message(message):
    if message["role"] == "user":
        with st.chat_message("user", avatar=USER_AVATAR):
            # The hidden marker makes the CSS paint this bubble as the user's
            text = html.escape(message["content"])
            st.markdown(f'<span class="lsd-user"></span>{text}', unsafe_allow_html=True)
        return

    with st.chat_message("assistant", avatar=ASSISTANT_AVATAR):
        if message["abstained"]:
            st.markdown(f'<span class="lsd-abstain"></span>{message["content"]}', unsafe_allow_html=True)
        else:
            st.markdown(message["content"])
            if message["sources"]:
                render_sources(message["sources"])


# Welcome Summary
def write_welcome():
    st.session_state.need_summary = False
    settings = st.session_state.settings

    language = settings["language"]
    if language == "Auto":
        language = "English"

    with st.spinner("Reading the whole document to summarize it..."):
        try:
            welcome = summarize(st.session_state.doc["doc_id"], language)
        except LLMError as error:
            st.error(str(error))
            return
    add_message("assistant", welcome)


# Questions
def answer_question(question):
    history = list(st.session_state.messages)   # previous messages, without this question
    add_message("user", question)
    render_message(st.session_state.messages[-1])

    with st.chat_message("assistant", avatar=ASSISTANT_AVATAR):
        try:
            with st.spinner("Searching the document..."):
                sources, stream = answer(question, history, st.session_state.doc["doc_id"],
                                         st.session_state.settings)
            full_text = st.write_stream(stream)
        except LLMError as error:
            st.error(str(error))
            return

    text, abstained = finish_answer(full_text)
    if abstained:
        sources = None
    add_message("assistant", text, sources, abstained)
    st.rerun()   # draw it again from the history, with its sources and colours


# Chat Page
def render_chat():
    render_header()

    if st.session_state.doc is None:
        render_empty_state()
        st.chat_input("Upload a PDF to start", disabled=True)
        return

    if st.session_state.need_summary:
        write_welcome()

    for message in st.session_state.messages:
        render_message(message)

    question = st.chat_input("Ask something about the document...")
    if question:
        answer_question(question)