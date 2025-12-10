# ui/theme.py
import streamlit as st

def apply_dark_theme():
    st.markdown(r"""
    <style>
    /* ---- Global Colors ---- */
    body, .stApp, [data-testid="stAppViewContainer"] {
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
    .stMarkdown, .stText, .stColumn, div[data-testid="column"], 
    [data-testid="stMarkdownContainer"], p, h1, h2, h3, h4, h5, h6 {
        color: #E6E6E6 !important;
    }

    /* ---- Sidebar ---- */
    [data-testid="stSidebar"], [data-testid="stSidebar"] > div {
        background-color: #1A1A1A !important;
        color: #E6E6E6 !important;
    }
    [data-testid="stSidebar"] .stMarkdown, [data-testid="stSidebar"] p {
        color: #E6E6E6 !important;
    }
    
    /* Sidebar icon arrows - ensure high contrast */
    [data-testid="stSidebar"] [data-testid="stIconMaterial"],
    [data-testid="stSidebar"] button[data-testid="stIconMaterial"],
    button[data-testid="stIconMaterial"],
    [data-testid="stIconMaterial"] svg,
    [data-testid="stSidebar"] svg,
    button[data-testid="baseButton-header"] svg,
    [data-testid="baseButton-header"] svg {
        color: #E6E6E6 !important;
        fill: #E6E6E6 !important;
        stroke: #E6E6E6 !important;
        filter: brightness(1.2) !important;
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
    label[data-testid="stWidgetLabel"], .stCheckbox label, .stRadio label {
        color: #E6E6E6 !important;
        font-weight: 600 !important;
    }

    /* ---- Number inputs, text boxes, selectboxes ---- */
    input, textarea, select, .stTextInput>div>div>input,
    [data-testid="stNumberInput"] input, [data-testid="stSelectbox"] select {
        background-color: #1C1C1C !important;
        color: #F1F1F1 !important;
        border-radius: 8px !important;
        border: 1px solid #333333 !important;
    }
    
    /* ---- Secondary buttons ---- */
    [data-testid="baseButton-secondary"],
    button[data-testid="baseButton-secondary"],
    button.kind-secondary,
    button[data-kind="secondary"],
    .stDownloadButton > button,
    [data-testid="stDownloadButton"] > button,
    button[class*="secondary"],
    [class*="baseButton-secondary"] button,
    [class*="stBaseButton-secondary"] button {
        background-color: #2A2A2A !important;
        color: #E6E6E6 !important;
        border: 1px solid #333333 !important;
        border-radius: 8px !important;
    }
    [data-testid="baseButton-secondary"]:hover,
    button[data-testid="baseButton-secondary"]:hover,
    button.kind-secondary:hover,
    button[data-kind="secondary"]:hover,
    .stDownloadButton > button:hover,
    [data-testid="stDownloadButton"] > button:hover,
    button[class*="secondary"]:hover,
    [class*="baseButton-secondary"] button:hover,
    [class*="stBaseButton-secondary"] button:hover {
        background-color: #2A2A2A !important;
        border-color: #444444 !important;
        color: #E6E6E6 !important;
    }
    /* Ensure text color in secondary buttons */
    [data-testid="baseButton-secondary"] *,
    button[data-testid="baseButton-secondary"] *,
    button.kind-secondary *,
    button[data-kind="secondary"] * {
        color: #E6E6E6 !important;
    }

    /* Checkbox styling */
    [data-testid="stCheckbox"] {
        color: #E6E6E6 !important;
    }

    /* File uploader */
    [data-testid="stFileUploader"] {
        background-color: #1A1A1A !important;
        border: 1px solid #2E2E2E !important;
        border-radius: 8px !important;
    }
    
    /* File uploader dropzone */
    [data-testid="stFileUploaderDropzone"], 
    [data-testid="stFileUploaderDropzone"] > div {
        background-color: #1A1A1A !important;
        border: 2px dashed #2E2E2E !important;
        border-radius: 8px !important;
        color: #E6E6E6 !important;
    }
    [data-testid="stFileUploaderDropzone"]:hover {
        border-color: #2B7FFF !important;
        background-color: #1F1F1F !important;
    }

    /* Info, success, warning, error boxes */
    [data-testid="stAlert"], .stAlert {
        background-color: #1A1A1A !important;
        border: 1px solid #2E2E2E !important;
        color: #E6E6E6 !important;
    }

    /* Fix for component icons */
    svg {
        filter: brightness(0.85) !important;
    }
    /* Exception for sidebar icons - keep them bright */
    [data-testid="stSidebar"] svg,
    button[data-testid="baseButton-header"] svg,
    [data-testid="baseButton-header"] svg {
        filter: brightness(1.2) !important;
    }

    /* ---- Progress bars ---- */
    .stProgress > div > div > div > div {
        background-color: #2B7FFF !important;
    }

    /* ---- Expander ---- */
    details, [data-testid="stExpander"] {
        background-color: #1A1A1A !important;
        color: #E6E6E6 !important;
        border-radius: 10px !important;
        border: 1px solid #2E2E2E !important;
        padding: 0.6rem;
        margin-bottom: 1rem;
    }
    [data-testid="stExpander"] summary {
        color: #E6E6E6 !important;
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

    /* ---- Tabs ---- */
    [data-testid="stTabs"] {
        background-color: #1A1A1A !important;
    }
    [data-testid="stTabs"] button {
        color: #E6E6E6 !important;
    }

    /* ---- ENHANCEMENTS FOR LOCATION LISTS ---- */
    
    /* Location block container */
    .location-card {
        background-color: rgb(38, 39, 48) !important;
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
        color: #E6E6E6 !important;
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
        background-color: #333333 !important;
        margin: 4px 0 10px 0 !important;
        opacity: 0.35 !important;
        padding: 0 !important;
    }

    /* Caption text */
    .stCaption {
        color: #B0B0B0 !important;
    }
    
    /* ---- App Header ---- */
    [data-testid="stHeader"],
    header[data-testid="stHeader"],
    .stApp > header {
        background-color: #121212 !important; 
    }
    [data-testid="stHeader"] * {
        color: #E6E6E6 !important;
    }

    </style>
    """, unsafe_allow_html=True)
    # Set data-theme attribute
    st.markdown("""
    <script>
    document.documentElement.setAttribute('data-theme', 'dark');
    </script>
    """, unsafe_allow_html=True)


def apply_light_theme():
    st.markdown(r"""
    <style>
    /* ---- Global Colors ---- */
    body, .stApp, [data-testid="stAppViewContainer"] {
        background-color: #FFFFFF !important;
        color: #262730 !important;
        font-family: "Inter", "Roboto", sans-serif;
    }

    /* ---- Main Containers ---- */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }

    /* Panel / Widget backgrounds */
    .stMarkdown, .stText, .stColumn, div[data-testid="column"],
    [data-testid="stMarkdownContainer"], p, h1, h2, h3, h4, h5, h6 {
        color: #262730 !important;
    }

    /* ---- Sidebar ---- */
    [data-testid="stSidebar"], [data-testid="stSidebar"] > div {
        background-color: #F0F2F6 !important;
        color: #262730 !important;
    }
    [data-testid="stSidebar"] .stMarkdown, [data-testid="stSidebar"] p {
        color: #262730 !important;
    }
    
    /* Sidebar icon arrows - ensure high contrast */
    [data-testid="stSidebar"] [data-testid="stIconMaterial"],
    [data-testid="stSidebar"] button[data-testid="stIconMaterial"],
    button[data-testid="stIconMaterial"],
    [data-testid="stIconMaterial"] svg,
    [data-testid="stSidebar"] svg,
    button[data-testid="baseButton-header"] svg,
    [data-testid="baseButton-header"] svg {
        color: #262730 !important;
        fill: #262730 !important;
        stroke: #262730 !important;
    }

    /* ---- Cards (dataframes, expanders, info boxes) ---- */
    .stDataFrame, div[data-testid="stDataFrame"], .st-cq {
        background-color: #FFFFFF !important;
        border-radius: 10px !important;
        border: 1px solid #E0E0E0 !important;
        color: #262730 !important;
    }

    /* Improve dataframe text contrast */
    table, td, th {
        color: #262730 !important;
        border-color: #E0E0E0 !important;
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
        box-shadow: 0 4px 10px rgba(43, 127, 255, 0.3);
    }

    /* ---- Toggle label ---- */
    label[data-testid="stWidgetLabel"], .stCheckbox label, .stRadio label {
        color: #262730 !important;
        font-weight: 600 !important;
    }

    /* ---- Number inputs, text boxes, selectboxes ---- */
    input, textarea, select, .stTextInput>div>div>input,
    [data-testid="stNumberInput"] input, [data-testid="stSelectbox"] select {
        background-color: #FFFFFF !important;
        color: #262730 !important;
        border-radius: 8px !important;
        border: 1px solid #E0E0E0 !important;
    }
    
    /* ---- Secondary buttons ---- */
    [data-testid="baseButton-secondary"],
    button[data-testid="baseButton-secondary"],
    button.kind-secondary,
    button[data-kind="secondary"],
    .stDownloadButton > button,
    [data-testid="stDownloadButton"] > button,
    button[class*="secondary"],
    [class*="baseButton-secondary"] button,
    [class*="stBaseButton-secondary"] button {
        background-color: #F8F9FA !important;
        color: #262730 !important;
        border: 1px solid #E0E0E0 !important;
        border-radius: 8px !important;
    }
    [data-testid="baseButton-secondary"]:hover,
    button[data-testid="baseButton-secondary"]:hover,
    button.kind-secondary:hover,
    button[data-kind="secondary"]:hover,
    .stDownloadButton > button:hover,
    [data-testid="stDownloadButton"] > button:hover,
    button[class*="secondary"]:hover,
    [class*="baseButton-secondary"] button:hover,
    [class*="stBaseButton-secondary"] button:hover {
        background-color: #E8E8E8 !important;
        border-color: #C0C0C0 !important;
        color: #262730 !important;
    }
    /* Ensure text color in secondary buttons */
    [data-testid="baseButton-secondary"] *,
    button[data-testid="baseButton-secondary"] *,
    button.kind-secondary *,
    button[data-kind="secondary"] * {
        color: #262730 !important;
    }

    /* Checkbox styling */
    [data-testid="stCheckbox"] {
        color: #262730 !important;
    }

    /* File uploader */
    [data-testid="stFileUploader"] {
        background-color: #F8F9FA !important;
        border: 1px solid #E0E0E0 !important;
        border-radius: 8px !important;
    }
    
    /* File uploader dropzone */
    [data-testid="stFileUploaderDropzone"],
    [data-testid="stFileUploaderDropzone"] > div {
        background-color: #F8F9FA !important;
        border: 2px dashed #E0E0E0 !important;
        border-radius: 8px !important;
        color: #262730 !important;
    }
    [data-testid="stFileUploaderDropzone"]:hover {
        border-color: #2B7FFF !important;
        background-color: #F0F4FF !important;
    }

    /* Info, success, warning, error boxes */
    [data-testid="stAlert"], .stAlert {
        background-color: #F8F9FA !important;
        border: 1px solid #E0E0E0 !important;
        color: #262730 !important;
    }

    /* Fix for component icons */
    svg {
        filter: brightness(1) !important;
    }
    /* Sidebar icons - ensure visibility */
    [data-testid="stSidebar"] svg,
    button[data-testid="baseButton-header"] svg,
    [data-testid="baseButton-header"] svg {
        filter: brightness(1) !important;
    }

    /* ---- Progress bars ---- */
    .stProgress > div > div > div > div {
        background-color: #2B7FFF !important;
    }

    /* ---- Expander ---- */
    details, [data-testid="stExpander"] {
        background-color: #FFFFFF !important;
        color: #262730 !important;
        border-radius: 10px !important;
        border: 1px solid #E0E0E0 !important;
        padding: 0.6rem;
        margin-bottom: 1rem;
    }
    [data-testid="stExpander"] summary {
        color: #262730 !important;
    }

    /* ---- Separator lines ---- */
    hr {
        border: 0;
        border-top: 1px solid #E0E0E0 !important;
    }

    /* ---- Small previews / images ---- */
    img {
        border-radius: 6px !important;
        background-color: #F8F9FA;
    }

    /* ---- Tooltips ---- */
    div[data-testid="stTooltip"] {
        background-color: #262730 !important;
        color: #FFFFFF !important;
        border: 1px solid #E0E0E0 !important;
    }

    /* ---- Tabs ---- */
    [data-testid="stTabs"] {
        background-color: #FFFFFF !important;
    }
    [data-testid="stTabs"] button {
        color: #262730 !important;
    }

    /* ---- ENHANCEMENTS FOR LOCATION LISTS ---- */
    
    /* Location block container */
    .location-card {
        background-color: #F8F9FA !important;
        padding: 0.5rem;
        border-radius: 12px;
        margin-bottom: 0.5rem;
        border: 1px solid #E0E0E0 !important;
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
        color: #262730 !important;
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
        background-color: #E0E0E0 !important;
        margin: 4px 0 10px 0 !important;
        opacity: 0.5 !important;
        padding: 0 !important;
    }

    /* Caption text */
    .stCaption {
        color: #6B6B6B !important;
    }
    
    /* ---- App Header ---- */
    [data-testid="stHeader"],
    header[data-testid="stHeader"],
    .stApp > header {
        background-color: #FFFFFF !important;
    }
    [data-testid="stHeader"] * {
        color: #262730 !important;
    }

    </style>
    """, unsafe_allow_html=True)
    # Set data-theme attribute
    st.markdown("""
    <script>
    document.documentElement.setAttribute('data-theme', 'light');
    </script>
    """, unsafe_allow_html=True)
