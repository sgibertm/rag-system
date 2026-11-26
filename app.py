import streamlit as st

from frontend.styles import apply_styles
from frontend.state import init_state
from frontend.sidebar import render_sidebar
from frontend.chat import render_chat

st.set_page_config(page_title="LSDatasheet", page_icon="📘", layout="centered")

apply_styles()
init_state()
render_sidebar()
render_chat()