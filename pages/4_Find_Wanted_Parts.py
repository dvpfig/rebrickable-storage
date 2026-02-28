import streamlit as st
import pandas as pd
from pathlib import Path
import hashlib

from core.state.progress import render_summary_table
from core.infrastructure.paths import init_paths
from core.parts.mapping import load_ba_mapping, build_rb_to_similar_parts_mapping, load_ba_part_names
from core.data.preprocess import load_wanted_files, load_collection_files, merge_wanted_collection
from core.parts.images import precompute_location_images, fetch_wanted_part_images
from core.data.colors import load_colors, build_color_lookup
from core.data.color_similarity import build_color_similarity_matrix, render_color_similarity_slider
from core.auth.security import validate_csv_file
import os
from dotenv import load_dotenv
from core.data.sets import SetsManager
from core.state.find_wanted_parts import (
    render_missing_parts_by_set, render_set_search_section,
    render_second_location_parts, render_part_detail, render_location_actions, render_missing_parts_export,
    get_unfound_parts, render_direct_set_search_section
)

# Page configuration
st.title("🔍 Find Wanted Parts")
st.markdown("Search for wanted parts in your collection (parts and/or sets). Upload wanted parts lists, match them against your inventory, and track your progress by location.")
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
            "locations_index": st.session_state.get("locations_index", {}),
            "set_found_counts": st.session_state.get("set_found_counts", {})
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
                st.session_state["set_found_counts"] = saved_data.get("set_found_counts", {})
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
    st.markdown("""
    Upload CSV files with the parts you need. Expected format (Rebrickable CSV export):
    - **Part**: Part number (e.g., "3001")
    - **Color**: Color ID (e.g., "4" for Red)
    - **Quantity**: Number of parts needed
    """)
    wanted_files_raw = st.file_uploader(
        "Upload CSV file(s) with Wanted Parts", 
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
    st.markdown("### 🗂️ Collection (Parts): Select Files")
    default_collection_files = sorted(user_collection_dir.glob("*.csv"))
    selected_files = []
    
    with st.expander(f"📁 Available files ({len(default_collection_files)})", expanded=False):
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
# --- Search Alternative Selection
# ---------------------------------------------------------------------
st.markdown("### ▶️ Select How to Find Wanted Parts")
st.markdown("#### How do you want to search for wanted parts?")
search_alternative = st.radio(
    "How do you want to search for wanted parts?",
    options=["***A: Parts collection first, then sets***", "***B: Search in owned sets only***"],
    captions=["Search for wanted parts in your collection of parts (first) and then in your owned sets.","Search for wanted parts directly in your owned set inventories."],
    index=0,
    key="search_alternative",
    horizontal=True,
    label_visibility="collapsed",
)

st.markdown("---")

# =====================================================================
# === ALTERNATIVE A: Find Wanted Parts (Parts -> Sets)
# =====================================================================
if search_alternative.startswith("***A"):
    if not collection_files_stream:
        st.info("📤 Upload at least one Collection file to begin.")
        st.session_state["start_processing"] = False
    else:
        st.markdown("### ▶️ Find wanted parts in collection (Parts → Sets)")
        st.markdown("Search for wanted parts in your collection of parts (first) and then in your owned sets.")
        st.markdown("1. Precompute the images for wanted and collection parts; 2. Show list of location with wanted parts; 3. (Optional) Search missing parts in owned sets.")
        
        if wanted_files:
            _wanted_preview = load_wanted_files(wanted_files)
            _unique_count = len(_wanted_preview[["Part", "Color"]].drop_duplicates())
            st.markdown(f"**{_unique_count} wanted part/color combination(s)** to search for.")
        
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
            st.session_state.pop("precompute_stats_page4", None)
        
        # Precompute collection images button
        precompute_done = st.session_state.get("precompute_done", False)
        
        if not precompute_done:
            if st.button("🔄 Precompute collection images", key="precompute_button", type="primary"):
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                def update_progress(current, total, item, status):
                    progress = current / total if total > 0 else 0
                    progress_bar.progress(progress)
                    status_text.text(f"Processing {current}/{total}: {item} - {status}")
                
                try:
                    with st.spinner("Precomputing collection images..."):
                        collection = load_collection_files(collection_files_stream)
                        collection_bytes = collection.to_csv(index=False).encode('utf-8')
                        
                        from core.auth.api_keys import load_api_key
                        user_data_dir = paths.user_data_dir / username
                        api_key = load_api_key(user_data_dir)
                        
                        images_index, part_images_map, stats = precompute_location_images(
                            collection_bytes, ba_mapping, paths.cache_images,
                            user_uploaded_dir=user_uploaded_images_dir,
                            progress_callback=update_progress,
                            cache_rb_dir=paths.cache_images_rb,
                            api_key=api_key, user_data_dir=user_data_dir
                        )
                        
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
                    progress_bar.empty()
                    status_text.empty()
        else:
            st.button("✅ Collection images precomputed", key="precompute_button_done", disabled=True)
            
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

    st.markdown("---")

    # -----------------------------------------------------------------
    # --- MAIN WANTED PARTS PROCESSING LOGIC (Alternative A)
    # -----------------------------------------------------------------
    if st.session_state.get("start_processing"):
        # Processing Wanted files and merging with precomputed collection
        try:
            wanted = load_wanted_files(wanted_files)
            collection = st.session_state.get("collection_df")
            if collection is None:
                st.error("❌ Collection data not found. Please precompute collection images first.")
                st.stop()
        except Exception as e:
            st.error(f"Error parsing uploaded files: {e}")
            st.stop()

        # Merge wanted and collection data
        _wanted_hash = hashlib.md5(pd.util.hash_pandas_object(wanted).values.tobytes()).hexdigest()
        _collection_hash = hashlib.md5(pd.util.hash_pandas_object(collection).values.tobytes()).hexdigest()
        merged_source_hash = hashlib.md5((_collection_hash + _wanted_hash).encode()).hexdigest()
        
        if st.session_state.get("merged_df") is None or st.session_state.get("merged_source_hash") != merged_source_hash:
            with st.spinner("Processing wanted parts and generating pickup list..."):
                merged = merge_wanted_collection(wanted, collection, rb_to_similar)
                merged["BA_part_name"] = merged["Part"].astype(str).map(ba_part_names).fillna("")
                st.session_state["merged_df"] = merged
                st.session_state["merged_source_hash"] = merged_source_hash

        merged = st.session_state["merged_df"]
        
        # Fetch images for all wanted parts
        if "merged_bytes" not in st.session_state or st.session_state.get("merged_bytes_hash") != merged_source_hash:
            st.session_state["merged_bytes"] = merged.to_csv(index=False).encode('utf-8')
            st.session_state["merged_bytes_hash"] = merged_source_hash
        
        merged_bytes = st.session_state["merged_bytes"]
        
        user_data_dir = paths.user_data_dir / username
        from core.auth.api_keys import load_api_key
        api_key = load_api_key(user_data_dir)
        
        wanted_images_map, wanted_stats = fetch_wanted_part_images(
            merged_bytes, ba_mapping, paths.cache_images,
            user_uploaded_dir=user_uploaded_images_dir,
            cache_rb_dir=paths.cache_images_rb, api_key=api_key,
            user_data_dir=user_data_dir
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

        # Build second-location lookup
        second_loc_parts = merged[merged["Second_location"].astype(str).str.strip() != ""].copy()
        second_loc_by_location = {}
        for _, row in second_loc_parts.iterrows():
            sl = str(row["Second_location"]).strip()
            if sl:
                second_loc_by_location.setdefault(sl, []).append(row)

        loc_summary = merged.groupby("Location").agg(parts_count=("Part", "count"), total_wanted=("Quantity_wanted", "sum")).reset_index()

        # Add location groups for second locations that don't exist as primary locations
        existing_locations = set(loc_summary["Location"].values)
        for sl_location in second_loc_by_location:
            if sl_location not in existing_locations:
                new_row = pd.DataFrame([{"Location": sl_location, "parts_count": 0, "total_wanted": 0}])
                loc_summary = pd.concat([loc_summary, new_row], ignore_index=True)

        loc_summary = loc_summary.sort_values("Location")

        # Display Parts By Location
        st.markdown('<hr class="location-separator">', unsafe_allow_html=True)
        
        if "expanded_locations" not in st.session_state:
            st.session_state["expanded_locations"] = set()
        
        for _, loc_row in loc_summary.iterrows():
            location = loc_row["Location"]
            parts_count = loc_row["parts_count"]
            total_wanted = loc_row["total_wanted"]

            loc_group = merged.loc[merged["Location"] == location]
            all_found = True
            for _, row in loc_group.iterrows():
                key = (str(row["Part"]), str(row["Color"]), str(row["Location"]))
                found = st.session_state.get("found_counts", {}).get(key, 0)
                qty_wanted = int(row["Quantity_wanted"])
                if found < qty_wanted:
                    all_found = False
                    break

            imgs = st.session_state.get("locations_index", {}).get(location, [])
            
            second_loc_count = len(second_loc_by_location.get(location, []))
            if parts_count == 0 and second_loc_count > 0:
                status_indicator = f"📌 {second_loc_count} part(s) from other locations"
            elif all_found:
                status_indicator = "✅ All parts found"
            else:
                status_indicator = f"{parts_count} part(s), {int(total_wanted)} total wanted"
            
            is_expanded = location in st.session_state["expanded_locations"]
            button_icon = "▼" if is_expanded else "▶"
            button_label = f"{button_icon} 📦 {location} — {status_indicator}"
            
            if st.button(button_label, key=f"toggle_{location}", width='stretch', type="secondary"):
                if is_expanded:
                    st.session_state["expanded_locations"].discard(location)
                else:
                    st.session_state["expanded_locations"].add(location)
                st.rerun()
            
            if is_expanded:
                if imgs:
                    st.markdown("**Stored here (sample images):**")
                    st.image(imgs[:50], width=60)
                    st.markdown("---")
                
                loc_parts_df = merged.loc[merged["Location"] == location].copy()
                alternative_colors = render_color_similarity_slider(
                    location, loc_parts_df,
                    st.session_state.get("collection_df"),
                    color_similarity_matrix
                )

                loc_group = merged.loc[merged["Location"] == location]
                for part_num, part_group in loc_group.groupby("Part"):
                    render_part_detail(
                        part_num, part_group, location, alternative_colors,
                        color_lookup, user_uploaded_images_dir
                    )

                second_loc_rows = second_loc_by_location.get(location, [])
                render_second_location_parts(location, second_loc_rows, color_lookup)
                render_location_actions(location, loc_group)
            
            st.markdown('<hr class="location-separator">', unsafe_allow_html=True)

        # Update merged dataframe with found counts
        found_map = st.session_state.get("found_counts", {})
        keys_tuples = list(zip(merged["Part"].astype(str), merged["Color"].astype(str), merged["Location"].astype(str)))
        merged["Found"] = [found_map.get(k, 0) for k in keys_tuples]
        merged["Complete"] = merged["Found"] >= merged["Quantity_wanted"]

        # Download button
        csv = merged.to_csv(index=False).encode("utf-8")
        st.download_button("💾 Download merged CSV", csv, "lego_wanted_with_location.csv", type="primary")
        
        # Export missing parts
        render_missing_parts_export(merged)

        # -----------------------------------------------------------------
        # --- Set Search Section (Alternative A)
        # -----------------------------------------------------------------
        set_search_results = {}
        try:
            sets_manager = SetsManager(paths.user_data_dir / username, paths.cache_set_inventories)
            render_set_search_section(merged, sets_manager, color_lookup)
            
            set_search_results = st.session_state.get("set_search_results", {})
            if set_search_results:
                render_missing_parts_by_set(
                    set_search_results, merged,
                    st.session_state.get("part_images_map", {}),
                    ba_part_names, color_lookup
                )
        except Exception as e:
            pass

        # -----------------------------------------------------------------
        # --- Summary & Progress (Alternative A)
        # -----------------------------------------------------------------
        set_found_counts = st.session_state.get("set_found_counts", {})
        render_summary_table(merged, set_search_results, set_found_counts, color_lookup)


# =====================================================================
# === ALTERNATIVE B: Search in Owned Sets Only
# =====================================================================
elif search_alternative.startswith("***B"):
    if not wanted_files:
        st.info("📤 Upload at least one Wanted file to search in your owned sets.")
    else:
        st.markdown("### ▶️ Find wanted parts in owned sets")
        st.markdown("Search for wanted parts directly in your owned set inventories.")

        try:
            sets_manager = SetsManager(paths.user_data_dir / username, paths.cache_set_inventories)

            # Load wanted parts and convert to (part_num, color_name) pairs
            wanted = load_wanted_files(wanted_files)
            wanted["BA_part_name"] = wanted["Part"].astype(str).map(ba_part_names).fillna("")

            # Build list of all wanted (part, color_name) tuples for set search
            wanted_parts_for_search = []
            for _, row in wanted.iterrows():
                part_num = str(row["Part"])
                color_id = row["Color"]
                try:
                    color_id_int = int(color_id)
                    color_info = color_lookup.get(color_id_int, {})
                    color_name = color_info.get("name", str(color_id))
                except (ValueError, TypeError):
                    color_name = str(color_id)
                wanted_parts_for_search.append((part_num, color_name))

            # Remove duplicates
            seen = set()
            unique_wanted = []
            for pair in wanted_parts_for_search:
                if pair not in seen:
                    seen.add(pair)
                    unique_wanted.append(pair)

            st.markdown(f"**{len(unique_wanted)} wanted part/color combination(s)** to search for.")

            # Render the direct set search UI
            render_direct_set_search_section(unique_wanted, sets_manager)

            # Display set search results
            set_search_results_b = st.session_state.get("set_search_results_b", {})
            if set_search_results_b:
                # Fetch images for wanted parts
                wanted_bytes = wanted.to_csv(index=False).encode('utf-8')
                user_data_dir = paths.user_data_dir / username
                from core.auth.api_keys import load_api_key
                api_key = load_api_key(user_data_dir)

                wanted_images_map, _ = fetch_wanted_part_images(
                    wanted_bytes, ba_mapping, paths.cache_images,
                    user_uploaded_dir=user_uploaded_images_dir,
                    cache_rb_dir=paths.cache_images_rb, api_key=api_key,
                    user_data_dir=user_data_dir
                )
                st.session_state["part_images_map"] = wanted_images_map

                # Build a minimal merged-like DataFrame for display and export
                # All parts are "not found in collection" since we skip collection
                merged_b = wanted.copy()
                merged_b["Location"] = "❌ Not Found"
                merged_b["Quantity_have"] = 0
                merged_b["Quantity_similar"] = 0
                merged_b["Available"] = False
                merged_b["Found"] = 0
                merged_b["Complete"] = False
                merged_b["Second_location"] = ""
                if "Quantity" in merged_b.columns and "Quantity_wanted" not in merged_b.columns:
                    merged_b = merged_b.rename(columns={"Quantity": "Quantity_wanted"})

                render_missing_parts_by_set(
                    set_search_results_b, merged_b,
                    st.session_state.get("part_images_map", {}),
                    ba_part_names, color_lookup
                )

                # Not-found parts: wanted parts that were NOT found in any set
                found_in_sets = set(set_search_results_b.keys())
                not_found_rows = []
                for _, row in wanted.iterrows():
                    part_num = str(row["Part"])
                    color_id = row["Color"]
                    try:
                        color_id_int = int(color_id)
                        color_info = color_lookup.get(color_id_int, {})
                        color_name = color_info.get("name", str(color_id))
                    except (ValueError, TypeError):
                        color_name = str(color_id)
                    if (part_num, color_name) not in found_in_sets:
                        not_found_rows.append(row)

                if not_found_rows:
                    not_found_df = pd.DataFrame(not_found_rows)
                    if "Quantity" in not_found_df.columns and "Quantity_wanted" not in not_found_df.columns:
                        not_found_df = not_found_df.rename(columns={"Quantity": "Quantity_wanted"})
                    with st.expander(f"❌ Not found in any set ({len(not_found_df)} part(s))", expanded=False):
                        from core.data.colors import render_color_cell

                        for _, row in not_found_df.iterrows():
                            part_num = str(row["Part"])
                            color_id = row["Color"]
                            qty_wanted = int(row.get("Quantity_wanted", 0))

                            try:
                                color_id_int = int(color_id)
                                color_info = color_lookup.get(color_id_int, {})
                                color_name = color_info.get("name", str(color_id))
                            except (ValueError, TypeError):
                                color_id_int = None
                                color_name = str(color_id)

                            img_url = wanted_images_map.get(str(part_num), "")
                            ba_name = ba_part_names.get(str(part_num), "")

                            left, right = st.columns([1, 4])

                            with left:
                                st.markdown(f"##### **{part_num}**")
                                if ba_name:
                                    st.markdown(f"{ba_name}")
                                if img_url:
                                    st.image(img_url, width=100)
                                else:
                                    st.text("🚫 No image")

                            with right:
                                header = st.columns([2.5, 1, 1, 1, 1])
                                header[0].markdown("**Color**")
                                header[1].markdown("**Wanted**")
                                header[2].markdown("**Missing**")
                                header[3].markdown("**Available**")
                                header[4].markdown("**Found**")

                                if color_id_int is not None:
                                    color_html = render_color_cell(color_id_int, color_lookup)
                                else:
                                    color_html = f"<span>{color_name}</span>"

                                cols = st.columns([2.5, 1, 1, 1, 1])
                                cols[0].markdown(color_html, unsafe_allow_html=True)
                                cols[1].markdown(f"{qty_wanted}")
                                cols[2].markdown(f"{qty_wanted}")
                                cols[3].markdown("❌ 0")
                                cols[4].markdown("0")

                            st.markdown("---")

                    # Export missing parts button
                    export_df = not_found_df[["Part", "Color", "Quantity_wanted"]].copy()
                    export_df.columns = ["Part", "Color", "Quantity"]
                    export_csv = export_df.to_csv(index=False).encode("utf-8")
                    st.download_button(
                        "📥 Export Missing Parts (Rebrickable Format)",
                        export_csv, "missing_parts_rebrickable.csv", type="primary"
                    )

                # Summary table for Alternative B
                set_found_counts = st.session_state.get("set_found_counts", {})
                render_summary_table(merged_b, set_search_results_b, set_found_counts, color_lookup)

        except Exception as e:
            st.error(f"❌ Error: {e}")
