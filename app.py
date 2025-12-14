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
from core.mapping import load_ba_mapping
from core.preprocess import load_wanted_files, load_collection_files, merge_wanted_collection
from core.images import precompute_location_images, resolve_part_image
from core.colors import load_colors, build_color_lookup, render_color_cell
from core.auth import AuthManager
from core.labels import organize_labels_by_location, generate_collection_labels_zip

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
# --- Authentication Setup
# ---------------------------------------------------------------------
paths = init_paths()
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

# --- Base path resolution (cross-platform)
CACHE_IMAGES_DIR = paths.cache_images
CACHE_LABELS_DIR = paths.cache_labels
RESOURCES_DIR = paths.resources_dir
DEFAULT_COLLECTION_DIR = paths.default_collection_dir  # Common collection directory
MAPPING_PATH = paths.mapping_path
COLORS_PATH = paths.colors_path

# --- Session-state initialization
ensure_session_state_keys()

# --- Mapping file
ba_mapping = load_ba_mapping(MAPPING_PATH)

# --- Color Lookup
colors_df = load_colors(COLORS_PATH)
color_lookup = build_color_lookup(colors_df)

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
        
        if st.button("📦 Generate Labels Zip File", key="generate_labels"):
            generate_collection_labels_zip(collection_files_stream, ba_mapping, CACHE_LABELS_DIR)
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
        images_index = precompute_location_images(collection_bytes, ba_mapping, CACHE_IMAGES_DIR)
        st.session_state["locations_index"] = images_index
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

        # CARD START - Location Header
        st.markdown('<div class="location-card">', unsafe_allow_html=True)

        st.markdown(f"""
        <div class="location-header">
            <div class="location-title">📦 {location}</div>
            <div class="loc-btn-row">
        """, unsafe_allow_html=True)

        # Buttons Open/Close (expand/collapse)
        colA, colB = st.columns([1, 1])
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
                st.image(imgs[:10], width=30)
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
            img_url = resolve_part_image(part_num, ba_mapping, CACHE_IMAGES_DIR)
            
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
                    cols[2].markdown(f"✅ {qty_have}" if row["Available"] else "❌")

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

        # Buttons Mark all / Clear all
        # CARD START - Buttons "Found all" / "Clear all"            
        st.markdown('<div class="loc-btn-row">', unsafe_allow_html=True)
        colM, colC = st.columns([1, 1])
        with colM:
            if st.button("Mark all found ✔", key=short_key("markall", location), help="Fill all items for this location"):
                for _, r in loc_group.iterrows():
                    k = (str(r["Part"]), str(r["Color"]), str(r["Location"]))
                    st.session_state["found_counts"][k] = int(r["Quantity_wanted"])
        with colC:
            if st.button("Clear found ✖", key=short_key("clearall", location), help="Clear found counts for this location"):
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
