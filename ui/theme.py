# ui/theme.py
import streamlit as st

def apply_custom_styles():
    """Apply minimal custom CSS that works with both light and dark Streamlit themes"""
    st.markdown(r"""
    <style>

    /* ---- Primary Action Buttons - Blue color for type="primary" ---- */
    div[data-testid="stButton"] > button[kind="primary"],
    div[data-testid="stDownloadButton"] > button[kind="primary"] {
        background-color: #4A90E2 !important;
        border: #4A90E2 !important;
        color: #FFFFFF !important;
    }
    div[data-testid="stButton"] > button[kind="primary"]:hover,
    div[data-testid="stDownloadButton"] > button[kind="primary"]:hover {
        background-color: #357ABD !important;
    }

    /* ---- Location Cards ---- */
    .location-card {
        background-color: var(--secondary-background-color);
        padding: 0.5rem;
        border-radius: 12px;
        margin-bottom: 0.5rem;
        border: 1px solid var(--border-color);
    }

    .location-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 0.6rem;
    }

    .location-title {
        font-size: 1.35rem;
        font-weight: 700;
        margin: 0;
    }

    .loc-btn-row {
        display: flex;
        gap: 6px;
        margin-bottom: 0.6rem;
    }

    /* ---- Location Card Separator ---- */
    .location-separator {
        height: 4px !important;
        background: linear-gradient(90deg, 
            transparent 0%, 
            #888888 10%, 
            #888888 90%, 
            transparent 100%) !important;
        border: none !important;
        margin: 1rem 0 !important;
        border-radius: 2px !important;
    }

    </style>
    """, unsafe_allow_html=True)
