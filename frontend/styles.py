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
    max-width: 1400px;
    padding-top: 2.5rem;
    padding-bottom: 2rem;
}

/* Top bar of Streamlit: transparent so the background shows */
[data-testid="stHeader"] { background: transparent; }

/* ===================== Sidebar =====================
   Colors of the native widgets come from [theme.sidebar] in .streamlit/config.toml.
   Palette: one surface (white 3.5%), one border (white 7%), three text greys, one blue. */
[data-testid="stSidebar"] {
    --sb-surface: rgba(255, 255, 255, 0.035);
    --sb-surface-hover: rgba(255, 255, 255, 0.06);
    --sb-border: rgba(255, 255, 255, 0.07);
    --sb-text: #e7eaf0;
    --sb-text-2: #9aa3b2;
    --sb-text-3: #6b7486;
    --sb-accent: #4f8cff;
    --sb-radius: 10px;
    width: 320px !important;
    min-width: 320px !important;
    border-right: 1px solid var(--sb-border);
    font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

/* Less empty space above the brand (the collapse button area) */
[data-testid="stSidebarHeader"] { height: 2.25rem; padding-bottom: 0; }
[data-testid="stSidebarUserContent"] { padding: 0 1.25rem 1.5rem; }
[data-testid="stSidebarUserContent"] [data-testid="stVerticalBlock"] { gap: 0.75rem; }

/* Labels of the native widgets */
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {
    font-size: 0.8rem;
    font-weight: 500;
    color: var(--sb-text-2);
}

/* Brand */
.lsd-brand {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 0 0 1.25rem;
    margin-bottom: 0.25rem;
    border-bottom: 1px solid var(--sb-border);
}
.lsd-brand-logo { width: 84px; height: 84px; object-fit: contain; flex-shrink: 0; }
.lsd-brand-name {
    font-size: 1.3rem;
    font-weight: 650;
    letter-spacing: -0.025em;
    color: #ffffff;
    line-height: 1.15;
}
.lsd-brand-tag { font-size: 0.8rem; color: var(--sb-text-3); margin-top: 3px; }

/* Section labels */
.lsd-section {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    margin: 1.1rem 0 0.1rem;
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.07em;
    text-transform: uppercase;
    color: var(--sb-text-3);
}
.lsd-section-meta {
    font-size: 0.72rem;
    font-weight: 500;
    letter-spacing: 0;
    text-transform: none;
    color: var(--sb-text-2);
    font-variant-numeric: tabular-nums;
}

/* File uploader: compact drop zone */
[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] {
    background: transparent;
    border: 1px dashed rgba(255, 255, 255, 0.14);
    border-radius: var(--sb-radius);
    padding: 0.7rem 0.8rem;
    transition: border-color 0.15s, background 0.15s;
}
[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"]:hover {
    border-color: var(--sb-accent);
    background: rgba(79, 140, 255, 0.06);
}
[data-testid="stSidebar"] [data-testid="stFileUploaderDropzoneInstructions"] span,
[data-testid="stSidebar"] [data-testid="stFileUploaderDropzoneInstructions"] small {
    font-size: 0.75rem;
    color: var(--sb-text-3);
}
[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] button {
    font-size: 0.8rem;
    padding: 0.25rem 0.75rem;
    min-height: 0;
    border-radius: 8px;
}

/* Document card */
.lsd-doc {
    display: flex;
    align-items: center;
    gap: 11px;
    padding: 10px 12px;
    background: var(--sb-surface);
    border: 1px solid var(--sb-border);
    border-radius: var(--sb-radius) var(--sb-radius) 0 0;
}
.lsd-doc-icon {
    width: 32px;
    height: 32px;
    border-radius: 8px;
    background: rgba(79, 140, 255, 0.12);
    color: var(--sb-accent);
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
}
.lsd-doc-icon svg { width: 17px; height: 17px; }
.lsd-doc-body { flex: 1; min-width: 0; }
.lsd-doc-name {
    font-size: 0.83rem;
    font-weight: 500;
    color: var(--sb-text);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.lsd-doc-meta { font-size: 0.72rem; color: var(--sb-text-3); margin-top: 1px; white-space: nowrap; font-variant-numeric: tabular-nums; }
.lsd-doc-foot {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 0.7rem;
    color: var(--sb-text-3);
    padding: 5px 12px;
    border: 1px solid var(--sb-border);
    border-top: none;
    border-radius: 0 0 var(--sb-radius) var(--sb-radius);
    margin-top: -1px;
}

/* Segmented control and pills */
[data-testid="stSidebar"] button[data-variant="segmented_control"],
[data-testid="stSidebar"] button[data-variant="pills"] {
    font-size: 0.78rem;
    min-height: 30px;
    padding: 0 0.7rem;
    border-color: var(--sb-border);
    background: transparent;
    color: var(--sb-text-2);
    transition: background 0.15s, color 0.15s;
}
[data-testid="stSidebar"] button[data-variant="segmented_control"] p,
[data-testid="stSidebar"] button[data-variant="pills"] p { font-size: 0.78rem; }
[data-testid="stSidebar"] button[data-variant="segmented_control"]:hover,
[data-testid="stSidebar"] button[data-variant="pills"]:hover {
    background: var(--sb-surface-hover);
    color: var(--sb-text);
}
[data-testid="stSidebar"] button[data-variant="segmented_control"][aria-checked="true"],
[data-testid="stSidebar"] button[data-variant="pills"][aria-checked="true"] {
    background: rgba(79, 140, 255, 0.14);
    border-color: rgba(79, 140, 255, 0.45);
    color: #ffffff;
}
[data-testid="stSidebar"] [data-testid="stButtonGroup"] [role="radiogroup"] { flex-wrap: nowrap; }
[data-testid="stSidebar"] button[data-variant="segmented_control"] { flex: 1; padding: 0 0.4rem; }
[data-testid="stSidebar"] button[data-variant="pills"] { flex: 1; padding: 0 0.3rem; min-width: 0; }

/* Footer: clear button + local workspace */
[data-testid="stSidebar"] [data-testid="stButton"] button {
    justify-content: flex-start;
    font-size: 0.8rem;
    color: var(--sb-text-2);
    padding: 0.45rem 0.6rem;
    border-radius: 8px;
    border: 1px solid var(--sb-border);
}
[data-testid="stSidebar"] [data-testid="stButton"] button p { font-size: 0.8rem; }
[data-testid="stSidebar"] [data-testid="stButton"] button:hover:not(:disabled) {
    background: var(--sb-surface-hover);
    color: var(--sb-text);
}

/* Push the footer (clear button + workspace) to the bottom of the sidebar */
[data-testid="stSidebarUserContent"] > div > [data-testid="stVerticalBlock"] { min-height: calc(100vh - 5.25rem); }
[data-testid="stSidebarUserContent"] [data-testid="stElementContainer"]:has([data-testid="stButton"]) { margin-top: auto; padding-top: 1rem; }

.lsd-workspace {
    display: flex;
    align-items: center;
    gap: 11px;
    padding: 10px 12px;
    background: var(--sb-surface);
    border: 1px solid var(--sb-border);
    border-radius: var(--sb-radius);
}
.lsd-workspace-icon {
    width: 30px;
    height: 30px;
    border-radius: 8px;
    background: rgba(255, 255, 255, 0.06);
    color: var(--sb-text-2);
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
}
.lsd-workspace-icon svg { width: 16px; height: 16px; }
.lsd-workspace-body { min-width: 0; }
.lsd-workspace-name {
    font-size: 0.8rem;
    font-weight: 500;
    color: var(--sb-text);
    display: flex;
    align-items: center;
    gap: 7px;
}
.lsd-workspace-meta {
    font-size: 0.7rem;
    color: var(--sb-text-3);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.lsd-live { width: 6px; height: 6px; border-radius: 50%; background: #4ade80; box-shadow: 0 0 0 3px rgba(74, 222, 128, 0.15); }

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

/* PDF Viewer */
.lsd-viewer-counter {
    text-align: center;
    font-size: 0.85rem;
    color: #475569;
}

</style>
"""


def apply_styles():
    st.markdown(CSS, unsafe_allow_html=True)