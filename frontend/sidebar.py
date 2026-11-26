import streamlit as st


def render_sidebar():
    """Uploader, document info and settings. Filled in later."""
    with st.sidebar:
        st.header("Document")
        st.caption("PDF uploader goes here")

        st.divider()

        st.header("Settings")
        st.caption("Temperature, language, style go here")