import streamlit as st

CSS = """
<style>
.stApp {
    background: linear-gradient(135deg, #f8fafc 0%, #eef2ff 100%);
}

[data-testid="stSidebar"] {
    background-color: #d3e4ff;
}

[data-testid="stChatMessage"] {
    border-radius: 20px;
    padding: 15px;
    margin-bottom: 10px;
    max-width: 80%;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
    background-color: #d3e4ff;
    margin-left: auto;
    flex-direction: row-reverse;
    border-bottom-right-radius: 2px;
    color: #000000;
}
</style>
"""


def apply_styles():
    """Inject the global CSS into the page."""
    st.markdown(CSS, unsafe_allow_html=True)