import streamlit as st
from ui.shared_content import render_about_info_content, render_app_features_content, render_new_user_content
from core.infrastructure.paths import init_paths

# ---------------------------------------------------------------------
# --- Page configuration
# ---------------------------------------------------------------------
st.sidebar.header("🧩 Welcome")

# Theme settings note for new users
st.sidebar.markdown("---")
st.sidebar.markdown("""
<div style="padding: 10px; border-radius: 5px; background-color: rgba(128, 128, 128, 0.1);">
    <div style="display: flex; align-items: center; gap: 10px;">
        <div style="flex: 1; font-size: 0.85em;">
            <strong>💡 Tip:</strong> Change theme (light/dark) via the menu in the top-right corner
        </div>
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="12" cy="6" r="1.5" fill="currentColor"/>
            <circle cx="12" cy="12" r="1.5" fill="currentColor"/>
            <circle cx="12" cy="18" r="1.5" fill="currentColor"/>
        </svg>
    </div>
</div>
""", unsafe_allow_html=True)
st.sidebar.markdown("---")

st.markdown("---")

# Read authentication state
auth_status = st.session_state.get("authentication_status", None)
name = st.session_state.get("name", None)
username = st.session_state.get("username", None)

# ---------------------------------------------------------------------
# --- Authentication Handling
# ---------------------------------------------------------------------
if not auth_status:
    # Not authenticated - Show Login + Registration UI
    col1, col2 = st.columns(2)

    with col1:
        # Render the About/Info content (app brief info)
        render_about_info_content()
    with col2:
        # Render new users login info content
        render_new_user_content()

        auth_manager = st.session_state.get("auth_manager")
        if auth_manager:
            tab1, tab2 = st.tabs(["Login", "Register"])
            with tab1:
                # Show error message if authentication failed
                if auth_status is False:
                    attempted_username = st.session_state.get("username", "unknown")
                    
                    # Check if account is locked
                    is_allowed, error_msg = auth_manager._check_rate_limit(attempted_username)
                    if not is_allowed:
                        st.error(f"🔒 {error_msg}")
                    else:
                        # Record the failed attempt
                        auth_manager._record_login_attempt(attempted_username, False)
                        st.error("❌ Incorrect username or password.")
                
                # Render login form (no return value needed)
                auth_manager.authenticator.login(location="main")
                
                # Record successful login if authentication just succeeded
                if st.session_state.get("authentication_status") is True:
                    auth_manager._record_login_attempt(st.session_state.get("username"), True)
                    
            with tab2:
                auth_manager.register_user()
        else:
            st.error("❌ Authentication manager not available.")

    st.markdown("---")
    
    # Render the App features content
    render_app_features_content()
    st.stop()

# ---------------------------------------------------------------------
# --- Authenticated User Content
# ---------------------------------------------------------------------

# Main content welcome message
display_name = st.session_state.get("name", username)
st.write(f"👤 Welcome, **{display_name}**!")

st.markdown("## 🚀 Getting Started - Choose a Function")

# Show warning if no mapping file exists yet
paths = init_paths()
if not paths.has_mapping:
    st.warning(
        "⚠️ **No BA vs RB mapping file found.** Some features (labels, images, part matching) "
        "won't work until you create one. Go to **My Collection - Parts** → "
        "**'🔄 Sync latest Parts from BrickArchitect'** → **'Get full list of BA parts'** to set it up."
    )

st.info("Use the topbar menu to navigate between pages")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### 🏷️ My Collection - Parts")
    st.markdown("""
    Manage your LEGO parts collection:
    - View and select collection files
    - Upload new collection CSVs
    - Generate printable labels by location
    """)
    if st.button("📂 Go to My Collection - Parts", width='stretch'):
        st.switch_page("pages/3_My_Collection_Parts.py")

with col2:
    st.markdown("### 📦 My Collection - Sets")
    st.markdown("""
    Manage your LEGO sets collection:
    - Upload sets CSV or add manually
    - Retrieve set inventories via API
    - View your complete set collection
    """)
    if st.button("📦 Go to My Collection - Sets", width='stretch'):
        st.switch_page("pages/4_My_Collection_Sets.py")

with col3:
    st.markdown("### 🔍 Find Wanted Parts")
    st.markdown("""
    Find parts you need for new builds:
    - Upload wanted parts lists
    - Match against collection or sets
    - Get pickup lists by location, export as pdf
    """)
    if st.button("🔎 Go to Find Wanted Parts", width='stretch'):
        st.switch_page("pages/5_Find_Wanted_Parts.py")

st.markdown("---")

# Render the About/Info content (app brief info)
render_about_info_content()

st.markdown("---")

# Render the App features content
render_app_features_content()
