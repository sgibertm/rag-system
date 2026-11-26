import streamlit as st

CSS = """
<style>

/* Page */
.stApp {
    background: radial-gradient(circle at 10% 0%, #dbeafe 0%, transparent 40%),
                radial-gradient(circle at 90% 10%, #e0e7ff 0%, transparent 35%),
                #f8fafc;
}

.block-container {
    max-width: 900px;
    padding-top: 2.5rem;
    padding-bottom: 6rem;
}

/* Top bar of Streamlit: transparent so the background shows */
[data-testid="stHeader"] { background: transparent; }

/* Sidebar */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #dbeafe 0%, #eef2ff 100%);
    border-right: 1px solid #c7d2fe;
}

.lsd-brand {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 0.5rem;
}

.lsd-brand-icon {
    width: 40px;
    height: 40px;
    border-radius: 12px;
    background: linear-gradient(135deg, #1d4ed8, #6366f1);
    color: white;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.3rem;
    box-shadow: 0 4px 12px rgba(29, 78, 216, 0.35);
}

.lsd-brand-name { font-weight: 800; font-size: 1.15rem; color: #1e3a8a; }
.lsd-brand-tag  { font-size: 0.75rem; color: #64748b; }

.lsd-section {
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #475569;
    margin: 1.2rem 0 0.4rem;
}

/* Document Card */
.lsd-doc-card {
    background: white;
    border: 1px solid #c7d2fe;
    border-radius: 14px;
    padding: 12px 14px;
    margin-top: 0.6rem;
    box-shadow: 0 2px 8px rgba(30, 58, 138, 0.08);
}

.lsd-doc-name {
    font-weight: 700;
    color: #0f172a;
    word-break: break-word;
}

.lsd-doc-stats { margin-top: 6px; }

.lsd-chip {
    display: inline-block;
    background: #eef2ff;
    color: #3730a3;
    border-radius: 999px;
    padding: 2px 10px;
    margin: 2px 4px 2px 0;
    font-size: 0.75rem;
    font-weight: 600;
}

/* Header */
.lsd-header { margin-bottom: 1.5rem; }

.lsd-title {
    font-size: 2.4rem;
    font-weight: 800;
    letter-spacing: -0.03em;
    background: linear-gradient(90deg, #1d4ed8, #6366f1);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin: 0;
}

.lsd-subtitle { color: #64748b; margin-top: 0.2rem; }

.lsd-badge {
    display: inline-block;
    margin-top: 0.6rem;
    background: white;
    border: 1px solid #c7d2fe;
    color: #1d4ed8;
    border-radius: 999px;
    padding: 2px 12px;
    font-size: 0.75rem;
    font-weight: 600;
}

/* Empty State */
.lsd-empty {
    background: white;
    border: 1px solid #e2e8f0;
    border-radius: 20px;
    padding: 2rem;
    box-shadow: 0 10px 30px rgba(30, 58, 138, 0.08);
}

.lsd-empty h3 { margin-top: 0; color: #1e3a8a; }

.lsd-steps {
    display: flex;
    gap: 12px;
    margin-top: 1.2rem;
}

.lsd-step {
    flex: 1;
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    padding: 14px;
}

.lsd-step-number {
    width: 28px;
    height: 28px;
    border-radius: 50%;
    background: #1d4ed8;
    color: white;
    font-weight: 700;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 8px;
}

.lsd-step-title { font-weight: 700; color: #0f172a; }
.lsd-step-text  { font-size: 0.85rem; color: #64748b; }

/* Chat Bubbles */
[data-testid="stChatMessage"] {
    background: white;
    border: 1px solid #e2e8f0;
    border-radius: 18px;
    border-bottom-left-radius: 4px;
    padding: 14px 18px;
    margin-bottom: 12px;
    max-width: 85%;
    box-shadow: 0 2px 10px rgba(15, 23, 42, 0.06);
    animation: lsd-fade-in 0.3s ease-out;
}

/* User messages contain a hidden .lsd-user marker */
[data-testid="stChatMessage"]:has(.lsd-user) {
    background: linear-gradient(135deg, #1d4ed8, #4f46e5);
    border: none;
    margin-left: auto;
    flex-direction: row-reverse;
    border-bottom-left-radius: 18px;
    border-bottom-right-radius: 4px;
}

[data-testid="stChatMessage"]:has(.lsd-user) p { color: white; }

/* "I don't know" answers contain a hidden .lsd-abstain marker */
[data-testid="stChatMessage"]:has(.lsd-abstain) {
    background: #fffbeb;
    border: 1px solid #fde68a;
}

.lsd-user, .lsd-abstain { display: none; }

@keyframes lsd-fade-in {
    from { opacity: 0; transform: translateY(6px); }
    to   { opacity: 1; transform: translateY(0); }
}

/* Sources */
.lsd-pages { margin-top: 10px; font-size: 0.8rem; color: #64748b; }

.lsd-page-pill {
    display: inline-block;
    background: #eef2ff;
    color: #1d4ed8;
    border: 1px solid #c7d2fe;
    border-radius: 999px;
    padding: 1px 10px;
    margin: 0 4px 4px 0;
    font-weight: 600;
}

.lsd-chunk {
    border-left: 3px solid #818cf8;
    background: #f8fafc;
    border-radius: 0 8px 8px 0;
    padding: 10px 14px;
    margin-bottom: 12px;
    font-size: 0.85rem;
    color: #334155;
    white-space: pre-wrap;
}

.lsd-chunk-page { font-size: 0.75rem; font-weight: 700; color: #4f46e5; margin-bottom: 4px; }

/* Chat Input */
[data-testid="stChatInput"] {
    border-radius: 16px;
    box-shadow: 0 8px 24px rgba(30, 58, 138, 0.12);
}

/* Footer */
.lsd-footer { text-align: center; color: #94a3b8; font-size: 0.8rem; margin-top: 2rem; }

</style>
"""


def apply_styles():
    st.markdown(CSS, unsafe_allow_html=True)