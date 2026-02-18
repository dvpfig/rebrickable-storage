import streamlit as st
from ui.shared_content import render_about_info_content, render_app_features_content

st.sidebar.header("🧩 Rebrickable Storage")

st.markdown("---")

# Read authentication state
auth_status = st.session_state.get("authentication_status", None)
name = st.session_state.get("name", None)
username = st.session_state.get("username", None)

# Check authentication
if not st.session_state.get("authentication_status"):
    st.warning("⚠️ Please login first")
    st.stop()

with st.sidebar:
    # Change password
    with st.expander("🔐 Change Password"):
        if st.session_state.get("auth_manager"):
            st.session_state.auth_manager.reset_password()
        else:
            st.error("❌ Authentication manager not available.")

    st.markdown("---")

    # Theme selector note
    st.info("💡 **Theme:** Use the ⋮ menu (top-right) → Settings to switch between light and dark theme.")

display_name = st.session_state.get("name", username)
st.write(f"👤 Welcome, **{display_name}**!")

st.markdown("## 🚀 Getting Started - Choose a Function")

st.info("Use the topbar menu to navigate between pages")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### 🏷️ My Collection")
    st.markdown("""
    Manage your LEGO parts collection:
    - View and select collection files
    - Upload new collection CSVs
    - Generate printable labels by location
    """)
    if st.button("📂 Go to My Collection", use_container_width=True):
        st.switch_page("pages/2_My_Collection.py")

with col2:
    st.markdown("### 🔍 Find Wanted Parts")
    st.markdown("""
    Find parts you need for new builds:
    - Upload wanted parts lists
    - Match against your collection
    - Get pickup lists by location
    """)
    if st.button("🔎 Go to Find Wanted Parts", use_container_width=True):
        st.switch_page("pages/3_Find_Wanted_Parts.py")

st.markdown("---")

# Render the About/Info content (app brief info)
render_about_info_content()

st.markdown("---")

# Render the App features content
render_app_features_content()