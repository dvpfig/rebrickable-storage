import streamlit as st
import pandas as pd
import requests
from pathlib import Path
from io import BytesIO
import re
import json
import hashlib

# ---------------------------------------------------------------------
# --- Local Libraries
# ---------------------------------------------------------------------
from ui.theme import apply_dark_theme, apply_light_theme
from ui.layout import ensure_session_state_keys, short_key
from ui.summary import render_summary_table
from core.paths import init_paths, save_uploadedfiles, manage_default_collection
from core.mapping import load_ba_mapping, count_parts_in_mapping
from core.preprocess import load_wanted_files, load_collection_files, merge_wanted_collection, get_collection_parts_tuple, get_collection_parts_set
from core.images import precompute_location_images
from core.colors import load_colors, build_color_lookup, render_color_cell
from core.auth import AuthManager
from core.labels import organize_labels_by_location, generate_collection_labels_zip
from core.download_helpers import create_download_callbacks
from resources.ba_part_labels import download_ba_labels
from resources.ba_part_images import download_ba_images
from resources.ba_part_mappings import fetch_all_ba_parts, fetch_rebrickable_mappings, find_latest_mapping_file

# ---------------------------------------------------------------------
# --- Page setup
# ---------------------------------------------------------------------
st.set_page_config(page_title="Rebrickable Storage - Parts Finder", layout="wide")
st.title("🧱 Rebrickable Storage - Parts Finder")

# ---------------------------------------------------------------------
# --- Theme Toggle (at the top, visible to all users)
# ---------------------------------------------------------------------
# Initialize theme in session state (default to dark)
if "theme" not in st.session_state:
    st.session_state["theme"] = "dark"

# Theme toggle switch at the top
col_theme_left, col_theme_right = st.columns([10, 1])
with col_theme_right:
    theme_icon = "🌙" if st.session_state["theme"] == "dark" else "☀️"
    theme_label = "Dark" if st.session_state["theme"] == "dark" else "Light"
    if st.button(f"{theme_icon} {theme_label}", key="theme_toggle", help="Toggle between dark and light theme"):
        st.session_state["theme"] = "light" if st.session_state["theme"] == "dark" else "dark"
        st.rerun()

# Apply theme based on session state (applies to entire app including login)
if st.session_state["theme"] == "dark":
    apply_dark_theme()
else:
    apply_light_theme()

# ---------------------------------------------------------------------
# --- Path Resolution & Global Setup (before authentication)
# ---------------------------------------------------------------------
paths = init_paths()

# Base path constants
CACHE_IMAGES_DIR = paths.cache_images
CACHE_LABELS_DIR = paths.cache_labels
RESOURCES_DIR = paths.resources_dir
DEFAULT_COLLECTION_DIR = paths.default_collection_dir
MAPPING_PATH = paths.mapping_path
COLORS_PATH = paths.colors_path

# Session-state initialization
ensure_session_state_keys()

# Load mapping and color data (cached, so only loads once)
ba_mapping = load_ba_mapping(MAPPING_PATH)
colors_df = load_colors(COLORS_PATH)
color_lookup = build_color_lookup(colors_df)

# ---------------------------------------------------------------------
# --- Authentication Setup
# ---------------------------------------------------------------------
auth_config_path = paths.resources_dir / "auth_config.yaml"

# Initialize AuthManager once
if "auth_manager" not in st.session_state:
    st.session_state.auth_manager = AuthManager(auth_config_path)

auth_manager = st.session_state.auth_manager

# Attempt silent cookie login BEFORE any UI
auth_manager.authenticator.login(
    location="unrendered",
    max_login_attempts=0   # suppress login form → cookie-only check
)

# Read authentication state
auth_status = st.session_state.get("authentication_status", None)
name = st.session_state.get("name", None)
username = st.session_state.get("username", None)

# Evaluate authentication result
if auth_status is True:
    # Authenticated via cookie or fresh login
    pass
elif auth_status is False:
    # Wrong credentials
    st.error("❌ Incorrect username or password.")
    st.stop()
else:
    # No cookie → Show Login + Registration UI
    st.markdown("### Welcome! Please login or register to continue.")

    tab1, tab2 = st.tabs(["Login", "Register"])
    with tab1:
        # Render login form (no return value needed)
        auth_manager.authenticator.login(location="main")
    with tab2:
        auth_manager.register_user()

    st.stop()

# -------------------------------------------------
# 5) Authenticated area
# -------------------------------------------------
if auth_status is True:
    # Define user collection directory for use throughout the app
    user_collection_dir = paths.user_data_dir / username / "collection"
    user_collection_dir.mkdir(parents=True, exist_ok=True)
    
    with st.sidebar:
        display_name = st.session_state.get("name", username)
        st.write(f"👤 Welcome, **{display_name}**!")

        # Logout button
        auth_manager.logout()

        # Save progress
        if st.button("💾 Save Progress"):
            session_data = {
                "found_counts": st.session_state.get("found_counts", {}),
                "locations_index": st.session_state.get("locations_index", {})
            }
            auth_manager.save_user_session(username, session_data, paths.user_data_dir)
            st.success("Progress saved!")

        # Load progress
        if st.button("📂 Load Progress"):
            saved_data = auth_manager.load_user_session(username, paths.user_data_dir)
            if saved_data:
                st.session_state["found_counts"] = saved_data.get("found_counts", {})
                st.session_state["locations_index"] = saved_data.get("locations_index", {})
                st.success("Progress loaded!")
                st.rerun()
            else:
                st.info("No saved progress found.")

        # Change password
        with st.expander("🔐 Change Password"):
            auth_manager.reset_password()

        # Collection default folder
        with st.expander("🗂️ Collection default"):
            # Will only execute if authenticated → username not None
            uploaded_files_list = st.file_uploader(
                "Upload Collection CSVs",
                type=["csv"],
                accept_multiple_files=True
            )
            save_uploadedfiles(uploaded_files_list, user_collection_dir)
            st.write("Current default collection files:")
            manage_default_collection(user_collection_dir)

        # Sync latest Labels from BrickArchitect
        with st.expander("🔄 Get latest Labels from BrickArchitect"):
            st.markdown("Download the latest label files (.lbx) from BrickArchitect based on the part mapping database.")
            st.markdown("Labels cached locally - only new labels will be downloaded.")
            
            # Calculate part counts for preview
            try:
                # Get collection parts as tuple (for caching)
                collection_parts_tuple = get_collection_parts_tuple(user_collection_dir)
                
                # Use helper function to count parts
                total_parts_with_labels, collection_parts_with_labels = count_parts_in_mapping(str(MAPPING_PATH), collection_parts_tuple, "labels")
                
                # Filter mode selector with counts
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
                # Fallback to simple selector
                labels_filter_mode = st.radio(
                    "Download mode:",
                    options=["collection", "all"],
                    format_func=lambda x: "Only parts in my collection" if x == "collection" else "All available parts",
                    index=0,
                    key="labels_filter_mode",
                    horizontal=True
                )
            
            # Initialize stop flag in session state
            if "ba_labels_stop_flag" not in st.session_state:
                st.session_state.ba_labels_stop_flag = False
            
            # Show start button if not downloading
            if not st.session_state.get("ba_labels_downloading", False):
                if st.button("📥 Get latest BA labels", key="download_ba_labels"):
                    st.session_state.ba_labels_downloading = True
                    st.session_state.ba_labels_stop_flag = False
                    st.rerun()
            else:
                # Show stop button while downloading
                if st.button("⏹️ Stop Download", key="stop_ba_labels", type="secondary"):
                    st.session_state.ba_labels_stop_flag = True
            
            # Perform download if flag is set
            if st.session_state.get("ba_labels_downloading", False):
                # Create download callbacks
                progress_callback, stop_flag_callback, stats_callback = create_download_callbacks(
                    stop_flag_key="ba_labels_stop_flag",
                    show_stats=False
                )
                
                try:
                    # Get collection parts if filter mode is "collection"
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
                    # Reset download state
                    st.session_state.ba_labels_downloading = False
                    st.session_state.ba_labels_stop_flag = False
        
        # Sync latest Images from BrickArchitect
        with st.expander("🔄 Get latest Images from BrickArchitect"):
            st.markdown("Download the latest part images from BrickArchitect based on the part mapping database.")
            st.markdown("Images cached locally - only new images will be downloaded.")
            
            # Calculate part counts for preview
            try:
                # Get collection parts as tuple (for caching)
                collection_parts_tuple = get_collection_parts_tuple(user_collection_dir)
                
                # Use helper function to count parts
                total_parts_with_images, collection_parts_with_images = count_parts_in_mapping(str(MAPPING_PATH), collection_parts_tuple, "images")
                
                # Filter mode selector with counts
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
                # Fallback to simple selector
                images_filter_mode = st.radio(
                    "Download mode:",
                    options=["collection", "all"],
                    format_func=lambda x: "Only parts in my collection" if x == "collection" else "All available parts",
                    index=0,
                    key="images_filter_mode",
                    horizontal=True
                )
            
            # Initialize stop flag in session state
            if "ba_images_stop_flag" not in st.session_state:
                st.session_state.ba_images_stop_flag = False
            
            # Show start button if not downloading
            if not st.session_state.get("ba_images_downloading", False):
                if st.button("📥 Get latest BA images", key="download_ba_images"):
                    st.session_state.ba_images_downloading = True
                    st.session_state.ba_images_stop_flag = False
                    st.rerun()
            else:
                # Show stop button while downloading
                if st.button("⏹️ Stop Download", key="stop_ba_images", type="secondary"):
                    st.session_state.ba_images_stop_flag = True
            
            # Perform download if flag is set
            if st.session_state.get("ba_images_downloading", False):
                # Create download callbacks
                progress_callback_images, stop_flag_callback_images, stats_callback_images = create_download_callbacks(
                    stop_flag_key="ba_images_stop_flag",
                    show_stats=False
                )
                
                try:
                    # Get collection parts if filter mode is "collection"
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
                    # Reset download state
                    st.session_state.ba_images_downloading = False
                    st.session_state.ba_images_stop_flag = False
            
        # Sync latest updates from BrickArchitect
        with st.expander("🔄 Sync latest Parts from BrickArchitect"):
            
            # BA Mappings Update Section
            st.markdown("**Update part number mapping database** between BrickArchitect and Rebrickable.")
            
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
                def format_parts_stats(stats):
                    return (f"📋 Pages processed: {stats.get('pages_processed', 0)}, "
                            f"Parts added: {stats.get('parts_added', 0)}")
                
                progress_callback_parts, stop_flag_callback_parts, stats_callback_parts = create_download_callbacks(
                    stop_flag_key="ba_parts_stop_flag",
                    show_stats=True,
                    stats_formatter=format_parts_stats
                )
                
                try:
                    from datetime import datetime
                    from resources.ba_part_mappings import fetch_all_ba_parts
                    
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
                def format_mappings_stats(stats):
                    return f"🔗 Processed {stats.get('processed', 0)}/{stats.get('total', 0)} parts"
                
                progress_callback_mappings, stop_flag_callback_mappings, stats_callback_mappings = create_download_callbacks(
                    stop_flag_key="ba_mappings_stop_flag",
                    show_stats=True,
                    stats_formatter=format_mappings_stats
                )
                
                try:
                    from resources.ba_part_mappings import fetch_rebrickable_mappings, find_latest_mapping_file
                    
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

st.write("Status: Set up app completed. Loaded mappings of parts and colors!")

# ---------------------------------------------------------------------
# --- File upload section
# ---------------------------------------------------------------------
col1, col2 = st.columns(2)
with col1:
    st.markdown("### 🗂️ Wanted parts: Upload")
    wanted_files = st.file_uploader("Upload Wanted CSVs", type=["csv"], accept_multiple_files=True)

with col2:
    st.markdown("### 🗂️ Collection: Pre-selected Files")
    default_collection_files = sorted(user_collection_dir.glob("*.csv"))
    selected_files = []
    if default_collection_files:
        for csv_file in default_collection_files:
            include = st.checkbox(f"Include {csv_file.name}", value=True, key=f"inc_{csv_file.name}")
            if include:
                selected_files.append(csv_file)
    uploaded_collection_files = st.file_uploader("Upload Collection CSVs", type=["csv"], accept_multiple_files=True)

collection_files_stream = []
collection_file_paths = []

# Add selected files from default collection
for f in selected_files:
    collection_file_paths.append(f)
    # Open file handle for streamlit processing
    file_handle = open(f, "rb")
    collection_files_stream.append(file_handle)

# Add uploaded files
if uploaded_collection_files:
    collection_files_stream.extend(uploaded_collection_files)
    # Store paths for uploaded files (they're in memory, so we'll handle differently)
    for uploaded_file in uploaded_collection_files:
        collection_file_paths.append(uploaded_file)

st.markdown("---")

# ---------------------------------------------------------------------
# --- ACTIONS Section
# ---------------------------------------------------------------------
col1, col2 = st.columns(2)
with col1:
    # ---------------------------------------------------------------------
    # --- Start Wanted Parts Processing Button
    if wanted_files and collection_files_stream:
        st.markdown("### ▶️ Find wanted parts in collection")
        st.markdown("Process the wanted parts and collection lists, create a table with wanted parts per location in collection.")
        if st.button("🚀 Start generating pickup list"):
            st.session_state["start_processing"] = True
    else:
        st.info("📤 Upload at least one Wanted and one Collection file to begin.")
        st.session_state["start_processing"] = False

with col2:
    # ---------------------------------------------------------------------
    # --- Labels Organization Section
    if collection_files_stream:
        st.markdown("### 🏷️ Generate Labels by Location")
        st.markdown("Create a downloadable zip file with label images organized by location from your collection files.")
        
        # Output mode selection
        output_mode = st.radio(
            "Output mode:",
            options=["both", "merged_only"],
            format_func=lambda x: "Both individual and merged files" if x == "both" else "Merged files only (one file per location)",
            index=0,
            key="labels_output_mode",
            horizontal=True
        )
        
        if st.button("📦 Generate Labels Zip File", key="generate_labels"):
            generate_collection_labels_zip(collection_files_stream, ba_mapping, CACHE_LABELS_DIR, output_mode)
        # Display download button if zip file is ready
        if st.session_state.get("labels_zip_bytes"):
            st.download_button(
                "⬇️ Download Labels Zip File",
                st.session_state["labels_zip_bytes"],
                st.session_state.get("labels_zip_filename", "labels_by_location.zip"),
                mime="application/zip",
                key="download_labels_zip"
            )
            if st.button("🗑️ Clear Labels Zip", key="clear_labels_zip"):
                st.session_state.pop("labels_zip_bytes", None)
                st.session_state.pop("labels_zip_filename", None)
                st.rerun()
    else:
        st.info("📤 Upload at least one Collection file to begin.")


# ---------------------------------------------------------------------
# --- MAIN WANTED PARTS PROCESSING LOGIC
# ---------------------------------------------------------------------
if st.session_state.get("start_processing"):

    # ---------------------------------------------------------------------
    # --- Processing Uploaded files (short processing time)
    with st.spinner("Processing Collection & Wanted parts..."):       
        try:
            wanted = load_wanted_files(wanted_files)
            collection = load_collection_files(collection_files_stream)
        except Exception as e:
            st.error(f"Error parsing uploaded files: {e}")
            st.stop()

        st.session_state["collection_df"] = collection
        st.write("Status: Loaded collection and wanted parts.")

        def _df_bytes(df):
            return df.to_csv(index=False).encode('utf-8')
        
        merged_source_hash = hashlib.md5(_df_bytes(collection) + _df_bytes(wanted)).hexdigest()
        if st.session_state.get("merged_df") is None or st.session_state.get("merged_source_hash") != merged_source_hash:
            merged = merge_wanted_collection(wanted, collection)
            st.session_state["merged_df"] = merged
            st.session_state["merged_source_hash"] = merged_source_hash

        merged = st.session_state["merged_df"]
        
        collection_bytes = _df_bytes(collection)
        
    # ---------------------------------------------------------------------
    # --- Processing Image locations (longer processing time)
    with st.spinner("Computing image locations..."):
        images_index, part_images_map = precompute_location_images(collection_bytes, ba_mapping, CACHE_IMAGES_DIR)
        st.session_state["locations_index"] = images_index
        st.session_state["part_images_map"] = part_images_map
        st.write("Status: Loaded image locations for parts.")
        
    st.markdown("### 🧩 Parts Grouped by Location")

    loc_summary = merged.groupby("Location").agg(parts_count=("Part", "count"), total_wanted=("Quantity_wanted", "sum")).reset_index()
    loc_summary = loc_summary.sort_values("Location")

    # ---------------------------------------------------------------------
    # --- Display Parts By Location
    for _, loc_row in loc_summary.iterrows():
        location = loc_row["Location"]
        parts_count = loc_row["parts_count"]
        total_wanted = loc_row["total_wanted"]

        # Check if all parts in this location are marked as found (for display in header)
        loc_group = merged.loc[merged["Location"] == location]
        all_found = True
        for _, row in loc_group.iterrows():
            key = (str(row["Part"]), str(row["Color"]), str(row["Location"]))
            found = st.session_state["found_counts"].get(key, 0)
            qty_wanted = int(row["Quantity_wanted"])
            if found < qty_wanted:
                all_found = False
                break

        # CARD START - Location Header
        st.markdown('<div class="location-card">', unsafe_allow_html=True)

        st.markdown(f"""
        <div class="location-header">
            <div class="location-title">📦 {location}</div>
        """, unsafe_allow_html=True)
        
        # Display green tick if all parts are found (right below title)
        if all_found:
            st.markdown("✅ **All parts found in this location**", unsafe_allow_html=True)
        
        st.markdown('<div class="loc-btn-row">', unsafe_allow_html=True)

        # Buttons Open/Close (expand/collapse) - left-aligned and close together
        colA, colB = st.columns([0.1, 0.7])
        with colA:
            if st.button("Open ▼", key=short_key("open", location), help="Show this location", use_container_width=False):
                st.session_state["expanded_loc"] = location
        with colB:
            if st.button("Close ▶", key=short_key("close", location), help="Hide this location", use_container_width=False):
                if st.session_state.get("expanded_loc") == location:
                    st.session_state["expanded_loc"] = None
            
        st.markdown("</div></div>", unsafe_allow_html=True)  # end header
        # CARD END

        # Collapsed display of location
        if st.session_state.get("expanded_loc") != location:
            
            imgs = st.session_state["locations_index"].get(location, [])
            if imgs:
                st.image(imgs[:10], width=25)
            #st.markdown("---")
            continue
        
        # Expanded display of location (larger images to identify location
        st.markdown(f"#### Details for {location}")

        imgs = st.session_state["locations_index"].get(location, [])
        if imgs:
            st.markdown("**Stored here (sample images):**")
            st.image(imgs[:50], width=60)
            st.markdown("---")

        # List of parts found in this location
        loc_group = merged.loc[merged["Location"] == location]
        for part_num, part_group in loc_group.groupby("Part"):
            # Use precomputed image map
            img_url = st.session_state.get("part_images_map", {}).get(str(part_num), "")
            
            left, right = st.columns([1, 4])
            with left:
                if img_url:
                    st.image(img_url, width=100)
                else:
                    st.text("🚫 No image")
                st.markdown(f"### **{part_num}**")
            with right:
                header = st.columns([2.5, 1, 1, 2])
                header[0].markdown("**Color**")
                header[1].markdown("**Wanted**")
                header[2].markdown("**Available**")
                header[3].markdown("**Found**")

                for _, row in part_group.iterrows():
                    color_html = render_color_cell(row["Color"], color_lookup)
                    qty_wanted = int(row["Quantity_wanted"])
                    qty_have = int(row["Quantity_have"])
                    key = (str(row["Part"]), str(row["Color"]), str(row["Location"]))
                    found = st.session_state["found_counts"].get(key, 0)

                    cols = st.columns([2.5, 1, 1, 2])
                    cols[0].markdown(color_html, unsafe_allow_html=True)
                    cols[1].markdown(f"{qty_wanted}")
                    # Three states for Available column:
                    # - Red cross (0 ❌) when not available
                    # - Orange warning (⚠️) when available but not enough
                    # - Green tick (✅) when enough available
                    if not row["Available"] or qty_have == 0:
                        available_display = "0 ❌"
                    elif qty_have >= qty_wanted:
                        available_display = f"✅ {qty_have}"
                    else:
                        available_display = f"⚠️ {qty_have}"
                    cols[2].markdown(available_display)

                    widget_key = short_key("found_input", row["Part"], row["Color"], row["Location"])
                    new_found = cols[3].number_input(
                        " ", min_value=0, max_value=qty_wanted, value=int(found), step=1,
                        key=widget_key, label_visibility="collapsed"
                    )
                    if int(new_found) != int(found):
                        st.session_state["found_counts"][key] = int(new_found)

                    complete = st.session_state["found_counts"].get(key, 0) >= qty_wanted
                    cols[3].markdown(
                        f"✅ Found all ({st.session_state['found_counts'].get(key, 0)}/{qty_wanted})"
                        if complete 
                        else f"**Found:** {st.session_state['found_counts'].get(key, 0)}/{qty_wanted}"
                    )

            st.markdown("---")

        # Buttons Mark all / Clear all - left-aligned and close together
        # CARD START - Buttons "Found all" / "Clear all"            
        st.markdown('<div class="loc-btn-row">', unsafe_allow_html=True)
        colM, colC = st.columns([0.1, 0.7])
        with colM:
            if st.button("Mark all found ✔", key=short_key("markall", location), help="Fill all items for this location", use_container_width=False):
                for _, r in loc_group.iterrows():
                    k = (str(r["Part"]), str(r["Color"]), str(r["Location"]))
                    st.session_state["found_counts"][k] = int(r["Quantity_wanted"])
                # Collapse the location card after marking all as found
                if st.session_state.get("expanded_loc") == location:
                    st.session_state["expanded_loc"] = None
        with colC:
            if st.button("Clear found ✖", key=short_key("clearall", location), help="Clear found counts for this location", use_container_width=False):
                for _, r in loc_group.iterrows():
                    k = (str(r["Part"]), str(r["Color"]), str(r["Location"]))
                    st.session_state["found_counts"].pop(k, None)

        st.markdown("</div>", unsafe_allow_html=True)
        # CARD END
        
        #st.markdown("---")

    found_map = st.session_state.get("found_counts", {})
    keys_tuples = list(zip(merged["Part"].astype(str), merged["Color"].astype(str), merged["Location"].astype(str)))
    merged["Found"] = [found_map.get(k, 0) for k in keys_tuples]
    merged["Complete"] = merged["Found"] >= merged["Quantity_wanted"]

    # Render summary table
    render_summary_table(merged)

    # Download button
    csv = merged.to_csv(index=False).encode("utf-8")
    st.download_button("💾 Download merged CSV", csv, "lego_wanted_with_location.csv")

st.caption("Powered by BrickArchitect & Rebrickable • Made with ❤️ and Streamlit")
