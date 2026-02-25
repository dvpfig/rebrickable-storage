import streamlit as st
import pandas as pd
from pathlib import Path
import hashlib

from core.infrastructure.session import short_key
from core.state.progress import render_summary_table
from core.infrastructure.paths import init_paths
from core.parts.mapping import load_ba_mapping, build_rb_to_similar_parts_mapping, load_ba_part_names
from core.data.preprocess import load_wanted_files, load_collection_files, merge_wanted_collection
from core.parts.images import precompute_location_images, fetch_wanted_part_images, save_user_uploaded_image
from core.data.colors import load_colors, build_color_lookup, render_color_cell
from core.data.color_similarity import build_color_similarity_matrix, find_alternative_colors_for_parts
from core.auth.security import validate_csv_file
import os
from dotenv import load_dotenv
from typing import List, Tuple, Dict
from core.data.sets import SetsManager
from core.state.find_wanted_parts import get_unfound_parts, merge_set_results, render_missing_parts_by_set, render_set_search_section

# Page configuration
st.title("🔍 Find Wanted Parts")
st.markdown("Search for wanted parts in your collection. Upload wanted parts lists, match them against your inventory, and track your progress by location.")
st.sidebar.header("🔍 Find Wanted Parts")

# Load environment variables
load_dotenv()

# Check authentication
if not st.session_state.get("authentication_status"):
    st.warning("⚠️ Please login on the first page to access this feature.")
    if st.button("🔐 Go to Login Page"):
        st.switch_page("pages/1_Rebrickable_Storage.py")
    st.stop()


# Get paths and user info
paths = init_paths()
username = st.session_state.get("username")
user_collection_dir = paths.get_user_collection_parts_dir(username)
user_uploaded_images_dir = paths.get_user_uploaded_images_dir(username)

# Save/Load Progress buttons in sidebar
with st.sidebar:
    st.markdown("---")
    # Save progress
    if st.button("💾 Save Progress", width='stretch', type="primary"):
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
    if st.button("📂 Load Progress", width='stretch', type="primary"):
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
custom_mapping_path = paths.resources_dir / "custom_rb_ba_mapping.csv"
ba_mapping = load_ba_mapping(paths.mapping_path, custom_mapping_path)
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
        st.session_state.pop("precompute_stats_page4", None)  # Clear stats when collection changes
    
    # Precompute collection images button
    precompute_done = st.session_state.get("precompute_done", False)
    
    if not precompute_done:
        if st.button("🔄 Precompute collection images", key="precompute_button", type="primary"):
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
                    
                    # Load API key for Rebrickable fallback
                    from core.auth.api_keys import load_api_key
                    user_data_dir = paths.user_data_dir / username
                    api_key = load_api_key(user_data_dir)
                    
                    # Precompute location images
                    images_index, part_images_map, stats = precompute_location_images(
                        collection_bytes, 
                        ba_mapping, 
                        paths.cache_images,
                        user_uploaded_dir=user_uploaded_images_dir,
                        progress_callback=update_progress,
                        cache_rb_dir=paths.cache_images_rb,
                        api_key=api_key,
                        user_data_dir=user_data_dir
                    )
                    
                    # Save to session state (including stats for display after rerun)
                    st.session_state["locations_index"] = images_index
                    st.session_state["part_images_map"] = part_images_map
                    st.session_state["collection_df"] = collection
                    st.session_state["collection_bytes"] = collection_bytes
                    st.session_state["precompute_done"] = True
                    st.session_state["precompute_stats_page4"] = stats
                    
                    st.rerun()
            except Exception as e:
                st.error(f"❌ Error precomputing images: {e}")
            finally:
                # Clear progress indicators
                progress_bar.empty()
                status_text.empty()
    else:
        st.button("✅ Collection images precomputed", key="precompute_button_done", disabled=True)
        
        # Show download statistics if available
        stats = st.session_state.get("precompute_stats_page4")
        if stats:
            if stats["ba_downloaded"] > 0:
                st.info(f"📥 Downloaded {stats['ba_downloaded']} image(s) from BrickArchitect")
            if stats["rb_downloaded"] > 0:
                st.success(f"🎉 Downloaded {stats['rb_downloaded']} image(s) from Rebrickable API")
            if stats["rb_rate_limit_errors"] > 0:
                st.warning(
                    f"⚠️ {stats['rb_rate_limit_errors']} Rebrickable API rate limit error(s) (HTTP 429). "
                    f"Re-run precompute to retry and fetch more images."
                )
            if stats["rb_other_errors"] > 0:
                st.info(f"ℹ️ {stats['rb_other_errors']} temporary API error(s) (network/server issues)")
    
    # Generate pickup list button
    can_generate = wanted_files and precompute_done
    
    if not can_generate:
        st.info("📤 Upload at least one Wanted file and Precompute collection to generate pickup list")
        st.button("🚀 Generate pickup list", key="generate_button", disabled=True)
        st.session_state["start_processing"] = False
    else:
        if st.button("🚀 Generate pickup list", key="generate_button", type="primary"):
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
        
        # Load API key for Rebrickable fallback
        from core.auth.api_keys import load_api_key
        user_data_dir = paths.user_data_dir / username
        api_key = load_api_key(user_data_dir)
        
        # Fetch images for all wanted parts (including "Not Found" parts)
        merged_bytes = _df_bytes(merged)
        wanted_images_map, wanted_stats = fetch_wanted_part_images(
            merged_bytes, 
            ba_mapping, 
            paths.cache_images,
            user_uploaded_dir=user_uploaded_images_dir,
            cache_rb_dir=paths.cache_images_rb,
            api_key=api_key
        )
        
        # Show download statistics for wanted parts
        if wanted_stats["ba_downloaded"] > 0 or wanted_stats["rb_downloaded"] > 0 or wanted_stats["rb_rate_limit_errors"] > 0 or wanted_stats["rb_other_errors"] > 0:
            if wanted_stats["ba_downloaded"] > 0:
                st.info(f"📥 Downloaded {wanted_stats['ba_downloaded']} wanted part image(s) from BrickArchitect")
            if wanted_stats["rb_downloaded"] > 0:
                st.success(f"🎉 Downloaded {wanted_stats['rb_downloaded']} wanted part image(s) from Rebrickable API")
            if wanted_stats["rb_rate_limit_errors"] > 0:
                st.warning(
                    f"⚠️ {wanted_stats['rb_rate_limit_errors']} Rebrickable API rate limit error(s) (HTTP 429) for wanted parts. "
                    f"Refresh the page to retry."
                )
            if wanted_stats["rb_other_errors"] > 0:
                st.info(f"ℹ️ {wanted_stats['rb_other_errors']} temporary API error(s) for wanted parts")
        
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
    
    # Initialize expanded locations tracking in session state
    if "expanded_locations" not in st.session_state:
        st.session_state["expanded_locations"] = set()
    
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

        # Location Header with preview images
        imgs = st.session_state.get("locations_index", {}).get(location, [])
        
        # Build expander label with status indicator
        status_indicator = "✅ All parts found" if all_found else f"{parts_count} part(s), {int(total_wanted)} total wanted"
        
        # Check if this location is currently expanded
        is_expanded = location in st.session_state["expanded_locations"]
        
        # Create toggle button that looks like an expander (discrete styling like other buttons)
        button_icon = "▼" if is_expanded else "▶"
        button_label = f"{button_icon} 📦 {location} — {status_indicator}"
        
        if st.button(button_label, key=f"toggle_{location}", width='stretch', type="secondary"):
            if is_expanded:
                st.session_state["expanded_locations"].discard(location)
            else:
                st.session_state["expanded_locations"].add(location)
            st.rerun()
        
        # Only render content if expanded (performance optimization)
        if is_expanded:
            # Show preview images at the top
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

                    for row_idx, row in part_group.iterrows():
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

                        widget_key = short_key("found_input", row["Part"], row["Color"], row["Location"], row_idx)
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
            st.markdown("---")
            colM, colC = st.columns([1, 1])
            with colM:
                if st.button("Mark all found ✔", key=short_key("markall", location), help="Fill all items for this location", width='stretch'):
                    if "found_counts" not in st.session_state:
                        st.session_state["found_counts"] = {}
                    for _, r in loc_group.iterrows():
                        k = (str(r["Part"]), str(r["Color"]), str(r["Location"]))
                        st.session_state["found_counts"][k] = int(r["Quantity_wanted"])
            with colC:
                if st.button("Clear found ✖", key=short_key("clearall", location), help="Clear found counts for this location", width='stretch'):
                    for _, r in loc_group.iterrows():
                        k = (str(r["Part"]), str(r["Color"]), str(r["Location"]))
                        st.session_state.get("found_counts", {}).pop(k, None)
        
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
    st.download_button("💾 Download merged CSV", csv, "lego_wanted_with_location.csv", type="primary")
    
    # Export missing parts button
    not_found_parts = merged[merged["Location"] == "❌ Not Found"].copy()
    if not not_found_parts.empty:
        st.markdown("---")
        st.markdown("### ❌ Not Available")
        st.markdown(f"**{len(not_found_parts)} part(s)** not found in your collection.")
        
        # Create Rebrickable format CSV (Part, Color, Quantity)
        export_df = not_found_parts[["Part", "Color", "Quantity_wanted"]].copy()
        export_df.columns = ["Part", "Color", "Quantity"]
        export_csv = export_df.to_csv(index=False).encode("utf-8")
        
        st.download_button("📥 Export Missing Parts (Rebrickable Format)",
            export_csv, "missing_parts_rebrickable.csv", type="primary")

    # ---------------------------------------------------------------------
    # --- Set Search Section
    # ---------------------------------------------------------------------
    # Initialize SetsManager for set search functionality
    try:
        sets_manager = SetsManager(paths.user_data_dir / username, paths.cache_set_inventories)
        render_set_search_section(merged, sets_manager, color_lookup)
        
        # Display set search results in a separate section
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
