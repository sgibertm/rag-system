import streamlit as st


def render_chat():
    """Header, conversation history and chat input. Filled in later."""
    st.title("LSDatasheet")
    st.caption("Chat with your datasheets")

    if st.session_state.doc is None:
        st.info("Upload a PDF in the sidebar to start.")