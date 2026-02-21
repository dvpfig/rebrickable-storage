import streamlit as st
from ui.shared_content import render_about_info_content, render_app_features_content, render_new_user_content
from core.paths import init_paths
from core.mapping import count_parts_in_mapping
from core.preprocess import get_collection_parts_tuple, get_collection_parts_set
from core.download_helpers import create_download_callbacks
from resources.ba_part_labels import download_ba_labels
from resources.ba_part_images import download_ba_images
from resources.ba_part_mappings import fetch_all_ba_parts, fetch_rebrickable_mappings, find_latest_mapping_file, display_mapping_files_info

# ---------------------------------------------------------------------
# --- Page configuration
# ---------------------------------------------------------------------
st.sidebar.header("🧩 Rebrickable Storage")

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
    if st.button("📂 Go to My Collection - Parts", use_container_width=True):
        st.switch_page("pages/2_My_Collection_Parts.py")

with col2:
    st.markdown("### 📦 My Collection - Sets")
    st.markdown("""
    Manage your LEGO sets collection:
    - Upload sets CSV or add manually
    - Retrieve set inventories via API
    - View your complete set collection
    """)
    if st.button("📦 Go to My Collection - Sets", use_container_width=True):
        st.switch_page("pages/3_My_Collection_Sets.py")

with col3:
    st.markdown("### 🔍 Find Wanted Parts")
    st.markdown("""
    Find parts you need for new builds:
    - Upload wanted parts lists
    - Match against collection or sets
    - Get pickup lists by location
    """)
    if st.button("🔎 Go to Find Wanted Parts", use_container_width=True):
        st.switch_page("pages/4_Find_Wanted_Parts.py")

st.markdown("---")

# Render the About/Info content (app brief info)
render_about_info_content()

st.markdown("---")

# Render the App features content
render_app_features_content()

# ---------------------------------------------------------------------
# --- Sidebar Content (for authenticated users)
# ---------------------------------------------------------------------
if st.session_state.get("authentication_status"):
    paths = init_paths()
    username = st.session_state.get("username")
    user_collection_dir = paths.get_user_collection_parts_dir(username)
    
    with st.sidebar:
        st.markdown("---")
        
        # Sync latest Labels/Images from BrickArchitect
        with st.expander("🔄 Get latest Labels/Images"):
            st.markdown("Download the latest labels (.lbx) or images (.png) from BrickArchitect based on the part mapping database. Files cached locally - only new files will be downloaded.")
            
            # Display cache statistics
            try:
                labels_count = len(list(paths.cache_labels.glob("*.lbx")))
                images_count = len(list(paths.cache_images.glob("*.png")))
                st.info(f"📊 Cache: **{labels_count}** labels, **{images_count}** images")
            except Exception as e:
                st.warning(f"⚠️ Could not count cache files: {e}")
            
            st.markdown("---")
            st.markdown("**Labels (.lbx files)**")
            
            # Calculate part counts for labels
            try:
                collection_parts_tuple = get_collection_parts_tuple(user_collection_dir)
                total_parts_with_labels, collection_parts_with_labels = count_parts_in_mapping(str(paths.mapping_path), collection_parts_tuple, "labels")
                
                labels_filter_mode = st.radio(
                    "Download mode:",
                    options=["collection", "all"],
                    format_func=lambda x: f"Only parts in my collection ({collection_parts_with_labels} parts)" if x == "collection" else f"All available parts ({total_parts_with_labels} parts)",
                    index=0,
                    key="labels_filter_mode",
                    horizontal=True
                )
            except Exception as e:
                st.warning(f"⚠️ Could not calculate part counts: {e}")
                labels_filter_mode = st.radio(
                    "Download mode:",
                    options=["collection", "all"],
                    format_func=lambda x: "Only parts in my collection" if x == "collection" else "All available parts",
                    index=0,
                    key="labels_filter_mode",
                    horizontal=True
                )
            
            if "ba_labels_stop_flag" not in st.session_state:
                st.session_state.ba_labels_stop_flag = False
            
            if not st.session_state.get("ba_labels_downloading", False):
                if st.button("📥 Get latest BA labels", key="download_ba_labels"):
                    st.session_state.ba_labels_downloading = True
                    st.session_state.ba_labels_stop_flag = False
                    st.rerun()
            else:
                if st.button("⏹️ Stop Download", key="stop_ba_labels", type="secondary"):
                    st.session_state.ba_labels_stop_flag = True
            
            if st.session_state.get("ba_labels_downloading", False):
                progress_callback, stop_flag_callback, stats_callback = create_download_callbacks(
                    stop_flag_key="ba_labels_stop_flag",
                    show_stats=False
                )
                
                try:
                    collection_parts_set = None
                    if labels_filter_mode == "collection":
                        collection_parts_set = get_collection_parts_set(user_collection_dir)
                        if not collection_parts_set:
                            st.warning("⚠️ No collection files found. Downloading all parts instead.")
                            labels_filter_mode = "all"
                    
                    with st.spinner("Downloading BA labels..."):
                        stats = download_ba_labels(
                            mapping_path=paths.mapping_path,
                            cache_labels_dir=paths.cache_labels,
                            timeout=10,
                            progress_callback=progress_callback,
                            stop_flag_callback=stop_flag_callback,
                            stats_callback=stats_callback,
                            filter_mode=labels_filter_mode,
                            collection_parts=collection_parts_set
                        )
                    
                except Exception as e:
                    st.error(f"❌ Error during download: {e}")
                finally:
                    st.session_state.ba_labels_downloading = False
                    st.session_state.ba_labels_stop_flag = False
            
            st.markdown("---")
            st.markdown("**Images (.png files)**")
            
            # Calculate part counts for images
            try:
                collection_parts_tuple = get_collection_parts_tuple(user_collection_dir)
                total_parts_with_images, collection_parts_with_images = count_parts_in_mapping(str(paths.mapping_path), collection_parts_tuple, "images")
                
                images_filter_mode = st.radio(
                    "Download mode:",
                    options=["collection", "all"],
                    format_func=lambda x: f"Only parts in my collection ({collection_parts_with_images} parts)" if x == "collection" else f"All available parts ({total_parts_with_images} parts)",
                    index=0,
                    key="images_filter_mode",
                    horizontal=True
                )
            except Exception as e:
                st.warning(f"⚠️ Could not calculate part counts: {e}")
                images_filter_mode = st.radio(
                    "Download mode:",
                    options=["collection", "all"],
                    format_func=lambda x: "Only parts in my collection" if x == "collection" else "All available parts",
                    index=0,
                    key="images_filter_mode",
                    horizontal=True
                )
            
            if "ba_images_stop_flag" not in st.session_state:
                st.session_state.ba_images_stop_flag = False
            
            if not st.session_state.get("ba_images_downloading", False):
                if st.button("📥 Get latest BA images", key="download_ba_images"):
                    st.session_state.ba_images_downloading = True
                    st.session_state.ba_images_stop_flag = False
                    st.rerun()
            else:
                if st.button("⏹️ Stop Download", key="stop_ba_images", type="secondary"):
                    st.session_state.ba_images_stop_flag = True
            
            if st.session_state.get("ba_images_downloading", False):
                progress_callback_images, stop_flag_callback_images, stats_callback_images = create_download_callbacks(
                    stop_flag_key="ba_images_stop_flag",
                    show_stats=False
                )
                
                try:
                    collection_parts_set = None
                    if images_filter_mode == "collection":
                        collection_parts_set = get_collection_parts_set(user_collection_dir)
                        if not collection_parts_set:
                            st.warning("⚠️ No collection files found. Downloading all parts instead.")
                            images_filter_mode = "all"
                    
                    with st.spinner("Downloading BA images..."):
                        stats = download_ba_images(
                            mapping_path=paths.mapping_path,
                            cache_images_dir=paths.cache_images,
                            timeout=10,
                            progress_callback=progress_callback_images,
                            stop_flag_callback=stop_flag_callback_images,
                            stats_callback=stats_callback_images,
                            filter_mode=images_filter_mode,
                            collection_parts=collection_parts_set
                        )
                    
                except Exception as e:
                    st.error(f"❌ Error during download: {e}")
                finally:
                    st.session_state.ba_images_downloading = False
                    st.session_state.ba_images_stop_flag = False
        
        # Sync latest updates from BrickArchitect
        with st.expander("🔄 Sync latest Parts from BrickArchitect"):
            
            # BA Mappings Update Section
            st.markdown("**Update part number mapping database** between BrickArchitect and Rebrickable.")
            
            # Display available mapping files with part counts
            st.info("📋 **Available Mapping Files:**")
            
            # Create callback for counting parts
            count_parts_wrapper = lambda file_path_str: count_parts_in_mapping(file_path_str, None, "images")
            
            # Display mapping files with part counts
            display_mapping_files_info(paths.resources_dir, count_parts_wrapper)
            
            st.markdown("---")
            
            # Phase 1: Get full list of BA parts
            st.markdown("**Step 1:** Fetch all BA parts from BrickArchitect (creates new Excel file)")
            
            # Initialize stop flag for phase 1
            if "ba_parts_stop_flag" not in st.session_state:
                st.session_state.ba_parts_stop_flag = False
            
            # Show start button if not fetching
            if not st.session_state.get("ba_parts_fetching", False):
                if st.button("📋 Get full list of BA parts", key="fetch_ba_parts"):
                    st.session_state.ba_parts_fetching = True
                    st.session_state.ba_parts_stop_flag = False
                    st.rerun()
            else:
                # Show stop button while fetching
                if st.button("⏹️ Stop Fetch", key="stop_ba_parts", type="secondary"):
                    st.session_state.ba_parts_stop_flag = True
            
            # Perform fetch if flag is set
            if st.session_state.get("ba_parts_fetching", False):
                # Create download callbacks with custom stats formatter
                format_parts_stats = lambda stats: (f"📋 Pages processed: {stats.get('pages_processed', 0)}, "
                            f"Parts added: {stats.get('parts_added', 0)}")
                
                progress_callback_parts, stop_flag_callback_parts, stats_callback_parts = create_download_callbacks(
                    stop_flag_key="ba_parts_stop_flag",
                    show_stats=True,
                    stats_formatter=format_parts_stats
                )
                
                try:
                    from datetime import datetime
                    
                    timestamp = datetime.now().strftime("%Y-%m-%d")
                    output_file = paths.resources_dir / f"part number - BA vs RB - {timestamp}.xlsx"
                    
                    with st.spinner("Fetching BA parts..."):
                        stats = fetch_all_ba_parts(
                            output_file=output_file,
                            start_page=1,
                            log_callback=progress_callback_parts,
                            stop_flag_callback=stop_flag_callback_parts,
                            stats_callback=stats_callback_parts
                        )
                    
                except Exception as e:
                    st.error(f"❌ Error during fetch: {e}")
                finally:
                    # Reset fetch state
                    st.session_state.ba_parts_fetching = False
                    st.session_state.ba_parts_stop_flag = False
            
            st.markdown("---")
            
            # Phase 2: Get BA mappings for parts
            st.markdown("**Step 2:** Fetch Rebrickable mappings for BA parts (updates latest Excel file)")
            
            # Initialize stop flag for phase 2
            if "ba_mappings_stop_flag" not in st.session_state:
                st.session_state.ba_mappings_stop_flag = False
            
            # Show start button if not updating
            if not st.session_state.get("ba_mappings_updating", False):
                if st.button("🔗 Get BA mappings for parts", key="update_ba_mappings"):
                    st.session_state.ba_mappings_updating = True
                    st.session_state.ba_mappings_stop_flag = False
                    st.rerun()
            else:
                # Show stop button while updating
                if st.button("⏹️ Stop Update", key="stop_ba_mappings", type="secondary"):
                    st.session_state.ba_mappings_stop_flag = True
            
            # Perform update if flag is set
            if st.session_state.get("ba_mappings_updating", False):
                # Create download callbacks with custom stats formatter
                format_mappings_stats = lambda stats: f"🔗 Processed {stats.get('processed', 0)}/{stats.get('total', 0)} parts"
                
                progress_callback_mappings, stop_flag_callback_mappings, stats_callback_mappings = create_download_callbacks(
                    stop_flag_key="ba_mappings_stop_flag",
                    show_stats=True,
                    stats_formatter=format_mappings_stats
                )
                
                try:
                    
                    # Find the latest mapping file
                    latest_file = find_latest_mapping_file(paths.resources_dir)
                    
                    if not latest_file:
                        st.error("❌ No mapping file found. Please run 'Get full list of BA parts' first.")
                    else:
                        st.info(f"📂 Updating file: {latest_file.name}")
                        
                        with st.spinner("Fetching Rebrickable mappings..."):
                            stats = fetch_rebrickable_mappings(
                                output_file=latest_file,
                                checkpoint_interval=50,
                                log_callback=progress_callback_mappings,
                                stop_flag_callback=stop_flag_callback_mappings,
                                stats_callback=stats_callback_mappings
                            )
                    
                except Exception as e:
                    st.error(f"❌ Error during update: {e}")
                finally:
                    # Reset update state
                    st.session_state.ba_mappings_updating = False
                    st.session_state.ba_mappings_stop_flag = False