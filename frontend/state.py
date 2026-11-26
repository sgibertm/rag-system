import copy

import streamlit as st

# Every session_state key the app uses, with its starting value.
DEFAULTS = {
    "messages": [],   # chat history: [{"role": "user"/"assistant", "content": "..."}]
    "doc": None,      # info about the loaded PDF, or None if nothing uploaded yet
}


def init_state():
    """Create any missing session_state keys. Safe to call on every rerun."""
    for key, value in DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = copy.deepcopy(value)