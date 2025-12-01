# ui/theme.py
import streamlit as st

def apply_dark_theme():
    st.markdown(r"""
    <style>
    /* ---- Global Colors ---- */
    body, .stApp {
        background-color: #121212 !important;
        color: #E6E6E6 !important;
        font-family: "Inter", "Roboto", sans-serif;
    }

    /* ---- Main Containers ---- */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }

    /* Panel / Widget backgrounds */
    .stMarkdown, .stText, .stColumn, div[data-testid="column"] {
        color: #E6E6E6 !important;
    }

    /* ---- Cards (dataframes, expanders, info boxes) ---- */
    .stDataFrame, div[data-testid="stDataFrame"], .st-cq {
        background-color: #1A1A1A !important;
        border-radius: 10px !important;
        border: 1px solid #2E2E2E !important;
        color: #E6E6E6 !important;
    }

    /* Improve dataframe text contrast */
    table, td, th {
        color: #E6E6E6 !important;
        border-color: #333333 !important;
    }

    /* ---- Buttons ---- */
    .stButton>button {
        background-color: #2B7FFF !important; /* LEGO blue */
        color: #FFFFFF !important;
        border-radius: 10px !important;
        border: none !important;
        padding: 0.55rem 1.2rem !important;
        font-weight: 600 !important;
        transition: 0.15s ease-in-out;
    }
    .stButton>button:hover {
        background-color: #1F5FCC !important;
        transform: translateY(-2px);
        box-shadow: 0 4px 10px rgba(0,0,0,0.4);
    }

    /* ---- Toggle label ---- */
    label[data-testid="stWidgetLabel"] {
        color: #E6E6E6 !important;
        font-weight: 600 !important;
    }

    /* ---- Number inputs, text boxes ---- */
    input, textarea, select, .stTextInput>div>div>input {
        background-color: #1C1C1C !important;
        color: #F1F1F1 !important;
        border-radius: 8px !important;
        border: 1px solid #333333 !important;
    }

    /* Fix for component icons */
    svg {
        filter: brightness(0.85) !important;
    }

    /* ---- Progress bars ---- */
    .stProgress > div > div > div > div {
        background-color: #2B7FFF !important;
    }

    /* ---- Expander ---- */
    details {
        background-color: #1A1A1A !important;
        color: #E6E6E6 !important;
        border-radius: 10px !important;
        border: 1px solid #2E2E2E !important;
        padding: 0.6rem;
        margin-bottom: 1rem;
    }

    /* ---- Separator lines ---- */
    hr {
        border: 0;
        border-top: 1px solid #333333 !important;
    }

    /* ---- Small previews / images ---- */
    img {
        border-radius: 6px !important;
        background-color: #1A1A1A;
    }

    /* ---- Tooltips ---- */
    div[data-testid="stTooltip"] {
        background-color: #2E2E2E !important;
        color: #FFFFFF !important;
        border: 1px solid #444444 !important;
    }

    /* ---- ENHANCEMENTS FOR LOCATION LISTS ---- */
    
    /* Location block container */
    .location-card {
        background-color: rgb(38, 39, 48);
        padding: 0.5rem;
        border-radius: 12px;
        margin-bottom: 0.5rem;
    }

    /* Row with title and action buttons */
    .location-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 0.6rem;
    }

    /* Title text */
    .location-title {
        font-size: 1.35rem;
        font-weight: 700;
        margin: 0;
    }

    /* Small inline buttons */
    .loc-btn-small > button {
        padding: 0.25rem 0.55rem !important;
        font-size: 0.75rem !important;
        border-radius: 6px !important;
        margin-left: 4px !important;
    }

    .loc-btn-row {
        display: flex;
        gap: 6px;
        margin-bottom: 0.6rem;
    }

    /* Ultra-subtle thin separator */
    .location-separator {
        height: 1px !important;
        width: 100% !important;
        background-color: var(--divider-color, #C7CBD1);
        margin: 4px 0 10px 0 !important;
        opacity: 0.35 !important;
        padding: 0 !important;
    }

    </style>
    """, unsafe_allow_html=True)
