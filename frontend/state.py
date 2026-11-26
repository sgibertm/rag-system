import copy

import streamlit as st


# Session State Keys (everything the app needs to remember between reruns)
DEFAULTS = {
    "messages": [],         # chat history: {"role", "content", "sources", "abstained"}
    "doc": None,            # loaded PDF: {"doc_id", "name", "n_pages", "n_chunks"}
    "doc_key": None,        # name + size of the uploaded file, to detect a new upload
    "need_summary": False,  # True right after a PDF is loaded: write the welcome message
    "settings": {},         # filled by the sidebar on every run
}


# Initialization
def init_state():
    for key, value in DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = copy.deepcopy(value)


# Helpers
def reset_conversation():
    # Empty chat; if a PDF is loaded, the welcome message is written again
    st.session_state.messages = []
    if st.session_state.doc is not None:
        st.session_state.need_summary = True


def add_message(role, content, sources=None, abstained=False):
    st.session_state.messages.append({
        "role": role,
        "content": content,
        "sources": sources,
        "abstained": abstained,
    })