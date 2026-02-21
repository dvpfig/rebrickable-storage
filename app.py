import streamlit as st
import pandas as pd
from pathlib import Path
from io import BytesIO

# ---------------------------------------------------------------------
# --- Local Libraries
# ---------------------------------------------------------------------
from ui.theme import apply_custom_styles
from ui.layout import ensure_session_state_keys
from ui.shared_content import render_about_info_content, render_new_user_content, render_app_features_content
from core.paths import init_paths
from core.auth import AuthManager
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ---------------------------------------------------------------------
# --- Page setup
# ---------------------------------------------------------------------
st.set_page_config(
    page_title="Rebrickable Storage", 
    layout="wide", 
    page_icon="🧩",
    initial_sidebar_state="collapsed"
)
st.title("🧩 Welcome to Rebrickable Storage")

# Apply custom styles (works with both light and dark Streamlit themes)
apply_custom_styles()

# ---------------------------------------------------------------------
# --- Path Resolution & Global Setup (before authentication)
# ---------------------------------------------------------------------
paths = init_paths()

# Session-state initialization
ensure_session_state_keys()

# ---------------------------------------------------------------------
# --- Initialize Authentication Manager (but don't show login UI here)
# ---------------------------------------------------------------------
auth_config_path = paths.resources_dir / "auth_config.yaml"
audit_log_dir = paths.user_data_dir / "_audit_logs"

# Initialize AuthManager once with audit logging
if "auth_manager" not in st.session_state:
    st.session_state.auth_manager = AuthManager(auth_config_path, audit_log_dir)

auth_manager = st.session_state.auth_manager

# Attempt silent cookie login BEFORE any UI
auth_manager.authenticator.login(
    location="unrendered",
    max_login_attempts=0   # suppress login form → cookie-only check
)

# Read authentication state
auth_status = st.session_state.get("authentication_status", None)
username = st.session_state.get("username", None)

# Check session timeout if authenticated
if auth_status is True and username:
    if not auth_manager.check_session_timeout(username):
        st.error("⏱️ Your session has expired due to inactivity. Please login again.")
        auth_manager.logout()
        st.rerun()
else:
    # Unauthenticated - Show login prompt in sidebar
    with st.sidebar:
        st.warning("⚠️ Please login on the first page to access all features.")

# ---------------------------------------------------------------------
# --- Authenticated Area (Sidebar Content) 
# ---------------------------------------------------------------------

# Add authenticated sidebar content BEFORE navigation
if auth_status is True:
    # Load sets data into session state on first access
    if not st.session_state.get("sets_data_loaded", False):
        from core.sets import SetsManager
        user_data_dir = paths.user_data_dir / username
        sets_manager = SetsManager(user_data_dir, paths.cache_set_inventories)
        sets_manager.load_into_session_state(st.session_state)
    
    with st.sidebar:
        display_name = st.session_state.get("name", username)
        st.write(f"👤 Welcome, **{display_name}**!")
        
        # Logout button
        auth_manager.logout()

# ---------------------------------------------------------------------
# --- Configure Multi-page Navigation
# ---------------------------------------------------------------------

pg = st.navigation([
    "pages/1_Rebrickable_Storage.py",
    "pages/2_My_Collection_Parts.py",
    "pages/3_My_Collection_Sets.py",
    "pages/4_Find_Wanted_Parts.py"
], position="top")
pg.run()

st.caption("Powered by [BrickArchitect Lego Parts Guide](https://brickarchitect.com/parts/) & [Rebrickable Lego Collection Lists](https://rebrickable.com/) • Made with ❤️ and Streamlit")
