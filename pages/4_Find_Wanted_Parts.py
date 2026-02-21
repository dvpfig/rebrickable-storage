import streamlit as st
import pandas as pd
from pathlib import Path
import hashlib

from ui.layout import short_key
from ui.summary import render_summary_table
from core.paths import init_paths
from core.mapping import load_ba_mapping, build_rb_to_similar_parts_mapping, load_ba_part_names
from core.preprocess import load_wanted_files, load_collection_files, merge_wanted_collection
from core.images import precompute_location_images, fetch_wanted_part_images, save_user_uploaded_image
from core.colors import load_colors, build_color_lookup, render_color_cell
from core.color_similarity import build_color_similarity_matrix, find_alternative_colors_for_parts
from core.security import validate_csv_file
import os
from dotenv import load_dotenv
from typing import List, Tuple, Dict
from core.sets import SetsManager
from pages.find_wanted_parts_helpers import get_unfound_parts, merge_set_results, render_missing_parts_by_set

# Page configuration
st.title("🔍 Find Wanted Parts")
st.sidebar.header("🔍 Find Wanted Parts")

# Load environment variables
load_dotenv()


def render_set_search_section(merged_df: pd.DataFrame, sets_manager: SetsManager, color_lookup: Dict) -> None:
    """
    Render set search interface for parts not found or insufficient.
    
    This function displays a UI section that allows users to search for wanted parts
    within their owned LEGO sets. It only appears when there are parts that are not
    found or have insufficient quantities in the loose parts collection.
    
    The interface includes:
    - "Include Owned Sets" button to trigger the set selection interface
    - Set selection checkboxes grouped by source CSV
    - "Search Selected Sets" button to execute the search
    - Results display with set-based locations
    
    Args:
        merged_df: Merged dataframe containing wanted parts and collection matches
        sets_manager: SetsManager instance for accessing set data
        color_lookup: Dictionary mapping color IDs to color info (for ID->name conversion)
        
    Requirements: 7.2, 7.3, 7.4, 7.5
    """
    # Get unfound parts (with color names for API compatibility)
    unfound_parts = get_unfound_parts(merged_df, color_lookup)
    
    # Only show this section if there are unfound parts
    if not unfound_parts:
        return
    
    st.markdown("---")
    st.markdown("### 📦 Search in Owned Sets")
    
    # Check if user has any sets with fetched inventories
    # Use session state if available, otherwise load from disk
    if st.session_state.get("sets_data_loaded", False) and st.session_state.get("sets_metadata") is not None:
        all_sets = st.session_state["sets_metadata"]
        # Group by source
        sets_by_source = {}
        for set_data in all_sets:
            source = set_data["source_csv"]
            if source not in sets_by_source:
                sets_by_source[source] = []
            sets_by_source[source].append(set_data)
    else:
        sets_by_source = sets_manager.get_sets_by_source()
    
    available_sets = []
    for source, sets_list in sets_by_source.items():
        for set_data in sets_list:
            if set_data.get("inventory_fetched", False):
                available_sets.append(set_data)
    
    if not available_sets:
        st.info("📭 No set inventories available. Add sets and retrieve inventories on the 'My Collection - Sets' page.")
        return
    
    # Display info about unfound parts
    st.markdown(f"**{len(unfound_parts)} part(s)** not found or insufficient in your loose parts collection.")
    
    # Initialize session state for set search UI
    if "show_set_selection" not in st.session_state:
        st.session_state["show_set_selection"] = False
    
    # "Include Owned Sets" button
    if not st.session_state["show_set_selection"]:
        if st.button("🔍 Include Owned Sets", key="include_owned_sets_btn", help="Search for these parts in your LEGO sets"):
            st.session_state["show_set_selection"] = True
            st.rerun()
        return
    
    # Set selection interface
    st.markdown("#### Select Sets to Search")
    st.markdown("Choose which sets to search for the missing parts:")
    
    # Initialize selected sets in session state
    if "selected_sets_for_search" not in st.session_state:
        st.session_state["selected_sets_for_search"] = set()
    
    # Group sets by source CSV and display with checkboxes
    for source_name, sets_list in sorted(sets_by_source.items()):
        # Filter to only sets with fetched inventories
        fetched_sets = [s for s in sets_list if s.get("inventory_fetched", False)]
        
        if not fetched_sets:
            continue
        
        with st.expander(f"📁 {source_name} ({len(fetched_sets)} set(s))", expanded=True):
            # "Select All" / "Deselect All" for this source
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button(f"Select All", key=f"select_all_{source_name}"):
                    # Add all sets from this source to selected sets
                    for set_data in fetched_sets:
                        st.session_state["selected_sets_for_search"].add(set_data["set_number"])
                    st.rerun()
            with col2:
                if st.button(f"Deselect All", key=f"deselect_all_{source_name}"):
                    # Remove all sets from this source from selected sets
                    for set_data in fetched_sets:
                        st.session_state["selected_sets_for_search"].discard(set_data["set_number"])
                    st.rerun()
            
            # Display checkboxes for each set
            for set_data in fetched_sets:
                set_number = set_data["set_number"]
                set_name = set_data.get("set_name", set_number)
                part_count = set_data.get("part_count", 0)
                
                # Check if this set is selected (read from session state)
                is_selected = set_number in st.session_state["selected_sets_for_search"]
                checkbox_label = f"{set_number} - {set_name} ({part_count} parts)"
                
                # Use on_change callback to update session state
                def toggle_set(set_num=set_number):
                    if set_num in st.session_state["selected_sets_for_search"]:
                        st.session_state["selected_sets_for_search"].discard(set_num)
                    else:
                        st.session_state["selected_sets_for_search"].add(set_num)
                
                st.checkbox(
                    checkbox_label, 
                    value=is_selected, 
                    key=f"set_checkbox_{set_number}",
                    on_change=toggle_set,
                    args=(set_number,)
                )
    
    # Action buttons
    st.markdown("---")
    col1, col2 = st.columns([1, 1])
    
    with col1:
        # "Search Selected Sets" button
        selected_count = len(st.session_state["selected_sets_for_search"])
        if selected_count == 0:
            st.button("🔍 Search Selected Sets", key="search_sets_btn", disabled=True, help="Select at least one set to search")
        else:
            if st.button(f"🔍 Search Selected Sets ({selected_count})", key="search_sets_btn", help="Search for parts in selected sets"):
                with st.spinner(f"Searching {selected_count} set(s)..."):
                    # Get cached inventories from session state
                    inventories_cache = st.session_state.get("sets_inventories_cache", {})
                    
                    # Search in selected sets with part/color combinations
                    selected_sets_list = list(st.session_state["selected_sets_for_search"])
                    set_results = sets_manager.search_parts(
                        unfound_parts,  # Pass the full list of (part_num, color) tuples
                        selected_sets=selected_sets_list,
                        inventories_cache=inventories_cache
                    )
                    
                    # Store results separately (don't merge into merged_df)
                    if set_results:
                        st.session_state["set_search_results"] = set_results
                        st.success(f"✅ Found parts in {len(set_results)} part/color combination(s)!")
                        st.rerun()
                    else:
                        st.session_state["set_search_results"] = {}
                        st.warning("No matching parts found in selected sets.")
    
    with col2:
        # "Cancel" button
        if st.button("❌ Cancel", key="cancel_set_search_btn", help="Close set selection"):
            st.session_state["show_set_selection"] = False
            st.session_state["selected_sets_for_search"] = set()
            st.rerun()

# Check authentication
if not st.session_state.get("authentication_status"):
    st.warning("⚠️ Please login on the first page to access this feature.")
    if st.button("🔐 Go to Login Page"):
        st.switch_page("pages/1_Rebrickable_Storage.py")
    st.stop()


# Get paths and user info
paths = init_paths()
username = st.session_state.get("username")
user_collection_dir = paths.user_data_dir / username / "collection"
user_uploaded_images_dir = paths.get_user_uploaded_images_dir(username)

# Save/Load Progress buttons in sidebar
with st.sidebar:
   
    # Save progress
    if st.button("💾 Save Progress", use_container_width=True):
        session_data = {
            "found_counts": st.session_state.get("found_counts", {}),
            "locations_index": st.session_state.get("locations_index", {})
        }
        if st.session_state.get("auth_manager"):
            st.session_state.auth_manager.save_user_session(username, session_data, paths.user_data_dir)
            st.success("Progress saved!")
        else:
            st.error("❌ Authentication manager not available.")

    # Load progress
    if st.button("📂 Load Progress", use_container_width=True):
        if st.session_state.get("auth_manager"):
            saved_data = st.session_state.auth_manager.load_user_session(username, paths.user_data_dir)
            if saved_data:
                st.session_state["found_counts"] = saved_data.get("found_counts", {})
                st.session_state["locations_index"] = saved_data.get("locations_index", {})
                st.success("Progress loaded!")
                st.rerun()
            else:
                st.info("No saved progress found.")
        else:
            st.error("❌ Authentication manager not available.")

# Load mapping and color data
ba_mapping = load_ba_mapping(paths.mapping_path)
rb_to_similar = build_rb_to_similar_parts_mapping(paths.mapping_path)
ba_part_names = load_ba_part_names(paths.mapping_path)
colors_df = load_colors(paths.colors_path)
color_lookup = build_color_lookup(colors_df)
color_similarity_matrix = build_color_similarity_matrix(colors_df)

# Get max file size from environment
max_file_size_mb = float(os.getenv('MAX_FILE_SIZE_MB', '1.0'))

st.markdown("---")

# ---------------------------------------------------------------------
# --- File Upload Section
# ---------------------------------------------------------------------
col1, col2 = st.columns(2)

with col1:
    st.markdown("### 🗂️ Wanted parts: Upload")
    wanted_files_raw = st.file_uploader(
        "Upload Wanted CSVs", 
        type=["csv"], 
        accept_multiple_files=True, 
        key="wanted_uploader"
    )
    
    # Validate wanted files
    wanted_files = []
    if wanted_files_raw:
        for file in wanted_files_raw:
            is_valid, error_msg = validate_csv_file(file, max_size_mb=max_file_size_mb)
            if is_valid:
                wanted_files.append(file)
            else:
                st.error(f"❌ {file.name}: {error_msg}")

with col2:
    st.markdown("### 🗂️ Collection: Select Files")
    default_collection_files = sorted(user_collection_dir.glob("*.csv"))
    selected_files = []
    
    if default_collection_files:
        for csv_file in default_collection_files:
            include = st.checkbox(f"Include {csv_file.name}", value=True, key=f"inc_{csv_file.name}")
            if include:
                selected_files.append(csv_file)
    else:
        st.info("📭 No collection files found. Add files in 'My Collection - Parts' page.")
    
    uploaded_collection_files_raw = st.file_uploader(
        "Upload Collection CSVs", 
        type=["csv"], 
        accept_multiple_files=True, 
        key="collection_uploader"
    )
    
    # Validate uploaded collection files
    uploaded_collection_files = []
    if uploaded_collection_files_raw:
        for file in uploaded_collection_files_raw:
            is_valid, error_msg = validate_csv_file(file, max_size_mb=max_file_size_mb)
            if is_valid:
                uploaded_collection_files.append(file)
                # Log file upload
                if st.session_state.get("auth_manager") and st.session_state.auth_manager.audit_logger:
                    st.session_state.auth_manager.audit_logger.log_file_upload(
                        username, file.name, "csv", file.size
                    )
            else:
                st.error(f"❌ {file.name}: {error_msg}")

# Combine selected and uploaded files
collection_files_stream = []
collection_file_paths = []

# Add selected files from default collection
for f in selected_files:
    collection_file_paths.append(f)
    file_handle = open(f, "rb")
    collection_files_stream.append(file_handle)

# Add uploaded files
if uploaded_collection_files:
    collection_files_stream.extend(uploaded_collection_files)
    for uploaded_file in uploaded_collection_files:
        collection_file_paths.append(uploaded_file)

st.markdown("---")

# ---------------------------------------------------------------------
# --- Find Wanted Parts Section
# ---------------------------------------------------------------------
if collection_files_stream:
    st.markdown("### ▶️ Find wanted parts in collection")
    st.markdown("Process the wanted parts and collection lists, create a table with wanted parts per location in collection.")
    
    # Calculate hash of collection files to detect changes
    collection_hash = hashlib.md5()
    for f in collection_file_paths:
        if isinstance(f, Path):
            collection_hash.update(str(f).encode())
            collection_hash.update(str(f.stat().st_mtime).encode())
        else:
            collection_hash.update(f.name.encode())
            collection_hash.update(str(f.size).encode())
    current_collection_hash = collection_hash.hexdigest()
    
    # Check if collection files have changed
    if st.session_state.get("collection_hash") != current_collection_hash:
        st.session_state["collection_hash"] = current_collection_hash
        st.session_state["precompute_done"] = False
    
    # Precompute collection images button
    precompute_done = st.session_state.get("precompute_done", False)
    
    if not precompute_done:
        if st.button("🔄 Precompute collection images", key="precompute_button"):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Progress callback function
            def update_progress(current, total, item, status):
                progress = current / total if total > 0 else 0
                progress_bar.progress(progress)
                status_text.text(f"Processing {current}/{total}: {item} - {status}")
            
            try:
                with st.spinner("Precomputing collection images..."):
                    # Load collection files
                    collection = load_collection_files(collection_files_stream)
                    collection_bytes = collection.to_csv(index=False).encode('utf-8')
                    
                    # Precompute location images
                    images_index, part_images_map = precompute_location_images(
                        collection_bytes, 
                        ba_mapping, 
                        paths.cache_images,
                        user_uploaded_dir=user_uploaded_images_dir,
                        progress_callback=update_progress
                    )
                    
                    # Save to session state
                    st.session_state["locations_index"] = images_index
                    st.session_state["part_images_map"] = part_images_map
                    st.session_state["collection_df"] = collection
                    st.session_state["collection_bytes"] = collection_bytes
                    st.session_state["precompute_done"] = True
                    
                    st.success("✅ Collection images precomputed successfully!")
                    st.rerun()
            except Exception as e:
                st.error(f"❌ Error precomputing images: {e}")
            finally:
                # Clear progress indicators
                progress_bar.empty()
                status_text.empty()
    else:
        st.button("✅ Collection images precomputed", key="precompute_button_done", disabled=True)
    
    # Generate pickup list button
    can_generate = wanted_files and precompute_done
    
    if not can_generate:
        st.info("📤 Upload at least one Wanted file and Precompute collection to generate pickup list")
        st.button("🚀 Generate pickup list", key="generate_button", disabled=True)
        st.session_state["start_processing"] = False
    else:
        if st.button("🚀 Generate pickup list", key="generate_button"):
            st.session_state["start_processing"] = True
else:
    st.info("📤 Upload at least one Collection file to begin.")
    st.session_state["start_processing"] = False

st.markdown("---")

# ---------------------------------------------------------------------
# --- MAIN WANTED PARTS PROCESSING LOGIC
# ---------------------------------------------------------------------
if st.session_state.get("start_processing"):

    # Processing Wanted files and merging with precomputed collection
    with st.spinner("Processing wanted parts and generating pickup list..."):       
        try:
            # Load wanted files
            wanted = load_wanted_files(wanted_files)
            
            # Get precomputed collection data from session state
            collection = st.session_state.get("collection_df")
            if collection is None:
                st.error("❌ Collection data not found. Please precompute collection images first.")
                st.stop()            
        except Exception as e:
            st.error(f"Error parsing uploaded files: {e}")
            st.stop()

        def _df_bytes(df):
            return df.to_csv(index=False).encode('utf-8')
        
        # Merge wanted and collection data
        merged_source_hash = hashlib.md5(_df_bytes(collection) + _df_bytes(wanted)).hexdigest()
        if st.session_state.get("merged_df") is None or st.session_state.get("merged_source_hash") != merged_source_hash:
            merged = merge_wanted_collection(wanted, collection, rb_to_similar)
            
            # Add BA part names to merged dataframe
            merged["BA_part_name"] = merged["Part"].astype(str).map(ba_part_names).fillna("")
            
            st.session_state["merged_df"] = merged
            st.session_state["merged_source_hash"] = merged_source_hash

        merged = st.session_state["merged_df"]
        
        # Fetch images for all wanted parts (including "Not Found" parts)
        merged_bytes = _df_bytes(merged)
        wanted_images_map = fetch_wanted_part_images(
            merged_bytes, 
            ba_mapping, 
            paths.cache_images,
            user_uploaded_dir=user_uploaded_images_dir
        )
        
        # Merge with precomputed collection images
        precomputed_images = st.session_state.get("part_images_map", {})
        combined_images_map = {**precomputed_images, **wanted_images_map}
        st.session_state["part_images_map"] = combined_images_map
        st.write("Status: Generated pickup list with part locations and images.")
    
    st.markdown("### 🧩 Parts Grouped by Location")

    loc_summary = merged.groupby("Location").agg(parts_count=("Part", "count"), total_wanted=("Quantity_wanted", "sum")).reset_index()
    loc_summary = loc_summary.sort_values("Location")

    # Display Parts By Location
    st.markdown('<hr class="location-separator">', unsafe_allow_html=True)    
    for _, loc_row in loc_summary.iterrows():
        location = loc_row["Location"]
        parts_count = loc_row["parts_count"]
        total_wanted = loc_row["total_wanted"]

        # Check if all parts in this location are marked as found
        loc_group = merged.loc[merged["Location"] == location]
        all_found = True
        for _, row in loc_group.iterrows():
            key = (str(row["Part"]), str(row["Color"]), str(row["Location"]))
            found = st.session_state.get("found_counts", {}).get(key, 0)
            qty_wanted = int(row["Quantity_wanted"])
            if found < qty_wanted:
                all_found = False
                break

        # Location Header
        st.markdown('<div class="location-card">', unsafe_allow_html=True)

        st.markdown(f"""
        <div class="location-header">
            <div class="location-title">📦 {location}</div>
        """, unsafe_allow_html=True)
        
        if all_found:
            st.markdown("✅ **All parts found in this location**", unsafe_allow_html=True)
        
        st.markdown('<div class="loc-btn-row">', unsafe_allow_html=True)

        # Open/Close buttons
        colA, colB = st.columns([0.1, 0.7])
        with colA:
            if st.button("Open ▼", key=short_key("open", location), help="Show this location", use_container_width=False):
                st.session_state["expanded_loc"] = location
        with colB:
            if st.button("Close ▶", key=short_key("close", location), help="Hide this location", use_container_width=False):
                if st.session_state.get("expanded_loc") == location:
                    st.session_state["expanded_loc"] = None
            
        st.markdown("</div></div>", unsafe_allow_html=True)

        # Collapsed display
        if st.session_state.get("expanded_loc") != location:
            imgs = st.session_state.get("locations_index", {}).get(location, [])
            if imgs:
                st.image(imgs[:10], width=25)
            st.markdown('<hr class="location-separator">', unsafe_allow_html=True)
            continue
        
        # Expanded display
        st.markdown(f"#### Details for {location}")

        imgs = st.session_state.get("locations_index", {}).get(location, [])
        if imgs:
            st.markdown("**Stored here (sample images):**")
            st.image(imgs[:50], width=60)
            st.markdown("---")
        
        # Check for insufficient parts
        loc_parts_df = merged.loc[merged["Location"] == location].copy()
        has_insufficient_parts = False
        for _, row in loc_parts_df.iterrows():
            qty_wanted = int(row["Quantity_wanted"])
            qty_have = int(row.get("Quantity_have", 0))
            available = row.get("Available", False)
            if not available or qty_have < qty_wanted:
                has_insufficient_parts = True
                break
        
        # Color similarity slider
        alternative_colors = {}
        if has_insufficient_parts:
            st.markdown("**🎨 Color Similarity Settings**")
            color_distance_key = f"color_distance_{location}"
            if color_distance_key not in st.session_state:
                st.session_state[color_distance_key] = 30.0
            
            color_distance = st.slider(
                "Adjust color similarity threshold (lower = closer colors only)",
                min_value=0.0,
                max_value=100.0,
                value=st.session_state[color_distance_key],
                step=5.0,
                key=f"slider_{color_distance_key}",
                help="0 = exact match only, 30 = similar colors, 60 = broader range"
            )
            st.session_state[color_distance_key] = color_distance
            
            if color_distance > 0:
                alternative_colors = find_alternative_colors_for_parts(
                    loc_parts_df,
                    st.session_state.get("collection_df"),
                    color_similarity_matrix,
                    max_distance=color_distance
                )
            
            st.markdown("---")

        # List parts in this location
        loc_group = merged.loc[merged["Location"] == location]
        for part_num, part_group in loc_group.groupby("Part"):
            img_url = st.session_state.get("part_images_map", {}).get(str(part_num), "")
            ba_name = part_group["BA_part_name"].iloc[0] if "BA_part_name" in part_group.columns else ""
            
            left, right = st.columns([1, 4])
            with left:
                st.markdown(f"##### **{part_num}**")
                st.markdown(f"{ba_name}")
                replacement_parts = part_group["Replacement_parts"].iloc[0] if "Replacement_parts" in part_group.columns else ""
                if replacement_parts:
                    st.markdown(f"(replace with {replacement_parts})")

                if img_url:
                    st.image(img_url, width=100)
                else:
                    st.text("🚫 No image")
                    upload_key = f"upload_{part_num}_{location}"
                    uploaded_file = st.file_uploader(
                        "Upload image",
                        type=["png", "jpg", "jpeg"],
                        key=upload_key,
                        label_visibility="collapsed",
                        help=f"Upload a custom image for part {part_num}"
                    )
                    if uploaded_file is not None:
                        if save_user_uploaded_image(uploaded_file, str(part_num), user_uploaded_images_dir):
                            st.success("✅ Image saved!")
                            precompute_location_images.clear()
                            fetch_wanted_part_images.clear()
                            st.rerun()
                        else:
                            st.error("❌ Failed to save image")
            
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
                    found = st.session_state.get("found_counts", {}).get(key, 0)

                    cols = st.columns([2.5, 1, 1, 2])
                    cols[0].markdown(color_html, unsafe_allow_html=True)
                    cols[1].markdown(f"{qty_wanted}")
                    
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
                        if "found_counts" not in st.session_state:
                            st.session_state["found_counts"] = {}
                        st.session_state["found_counts"][key] = int(new_found)

                    complete = st.session_state.get("found_counts", {}).get(key, 0) >= qty_wanted
                    cols[3].markdown(
                        f"✅ Found all ({st.session_state.get('found_counts', {}).get(key, 0)}/{qty_wanted})"
                        if complete 
                        else f"**Found:** {st.session_state.get('found_counts', {}).get(key, 0)}/{qty_wanted}"
                    )
                    
                    # Show alternative colors
                    alt_key = (str(row["Part"]), int(row["Color"]), str(row["Location"]))
                    if alt_key in alternative_colors and (not row["Available"] or qty_have < qty_wanted):
                        alternatives = alternative_colors[alt_key]
                        if alternatives:
                            with st.expander(f"🎨 {len(alternatives)} alternative color(s) available", expanded=False):
                                st.markdown("**Alternative colors in this location:**")
                                for alt_color_id, alt_color_name, alt_qty, distance in alternatives[:5]:
                                    alt_color_html = render_color_cell(alt_color_id, color_lookup)
                                    alt_cols = st.columns([2.5, 1, 1])
                                    alt_cols[0].markdown(alt_color_html, unsafe_allow_html=True)
                                    alt_cols[1].markdown(f"Qty: **{alt_qty}**")
                                    if distance < 15:
                                        similarity = "Very similar"
                                    elif distance < 30:
                                        similarity = "Similar"
                                    elif distance < 50:
                                        similarity = "Somewhat similar"
                                    else:
                                        similarity = "Different"
                                    alt_cols[2].markdown(f"*{similarity}*")

        # Mark all / Clear all buttons
        st.markdown('<div class="loc-btn-row">', unsafe_allow_html=True)
        colM, colC = st.columns([0.1, 0.7])
        with colM:
            if st.button("Mark all found ✔", key=short_key("markall", location), help="Fill all items for this location", use_container_width=False):
                if "found_counts" not in st.session_state:
                    st.session_state["found_counts"] = {}
                for _, r in loc_group.iterrows():
                    k = (str(r["Part"]), str(r["Color"]), str(r["Location"]))
                    st.session_state["found_counts"][k] = int(r["Quantity_wanted"])
                if st.session_state.get("expanded_loc") == location:
                    st.session_state["expanded_loc"] = None
        with colC:
            if st.button("Clear found ✖", key=short_key("clearall", location), help="Clear found counts for this location", use_container_width=False):
                for _, r in loc_group.iterrows():
                    k = (str(r["Part"]), str(r["Color"]), str(r["Location"]))
                    st.session_state.get("found_counts", {}).pop(k, None)

        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown('<hr class="location-separator">', unsafe_allow_html=True)

    # Update merged dataframe with found counts
    found_map = st.session_state.get("found_counts", {})
    keys_tuples = list(zip(merged["Part"].astype(str), merged["Color"].astype(str), merged["Location"].astype(str)))
    merged["Found"] = [found_map.get(k, 0) for k in keys_tuples]
    merged["Complete"] = merged["Found"] >= merged["Quantity_wanted"]

    # Render summary table
    render_summary_table(merged)

    # Download button
    csv = merged.to_csv(index=False).encode("utf-8")
    st.download_button("💾 Download merged CSV", csv, "lego_wanted_with_location.csv")

    # ---------------------------------------------------------------------
    # --- Set Search Section (Requirements 7.2, 7.3, 7.4, 7.5)
    # ---------------------------------------------------------------------
    # Initialize SetsManager for set search functionality
    try:
        sets_manager = SetsManager(paths.user_data_dir / username)
        render_set_search_section(merged, sets_manager, color_lookup)
        
        # Display set search results in a separate section (Requirement 8.3)
        set_search_results = st.session_state.get("set_search_results", {})
        if set_search_results:
            render_missing_parts_by_set(
                set_search_results,
                merged,
                st.session_state.get("part_images_map", {}),
                ba_part_names,
                color_lookup
            )
    except Exception as e:
        # If there's an error initializing sets manager, just skip this section
        # This ensures the main functionality continues to work
        pass
