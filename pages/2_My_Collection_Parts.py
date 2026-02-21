import streamlit as st
import pandas as pd
from pathlib import Path
import hashlib

from core.paths import init_paths, save_uploadedfiles, manage_default_collection
from core.mapping import load_ba_mapping, count_parts_in_mapping, get_mapping_deviation_rules
from core.labels import generate_collection_labels_zip
from core.preprocess import load_collection_files, get_collection_parts_tuple, get_collection_parts_set
from core.images import precompute_location_images, create_custom_images_zip, count_custom_images, upload_custom_images, delete_all_custom_images
from core.security import validate_csv_file
from core.download_helpers import create_download_callbacks
from resources.ba_part_labels import download_ba_labels
from resources.ba_part_images import download_ba_images
from resources.ba_part_mappings import fetch_all_ba_parts, fetch_rebrickable_mappings, find_latest_mapping_file, display_mapping_files_info
import os
from dotenv import load_dotenv

# Page configuration
st.title("🏷️ My Collection - Parts")
st.sidebar.header("🏷️ My Collection - Parts")

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
user_collection_dir = paths.user_data_dir / username / "collection"
user_uploaded_images_dir = paths.get_user_uploaded_images_dir(username)

# Sidebar sections for collection management
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
    
    st.markdown("---")
    
    # Custom Images Management
    with st.expander("🖼️ Custom Images"):
        st.markdown("Manage your custom part images uploaded when no official image was available.")
        
        # Count custom images
        custom_image_count = count_custom_images(user_uploaded_images_dir)
        
        if custom_image_count > 0:
            st.info(f"📊 You have **{custom_image_count}** custom image(s) uploaded.")
            
            # Download button
            if st.button("📥 Download all custom images", key="download_custom_images"):
                try:
                    zip_buffer = create_custom_images_zip(user_uploaded_images_dir)
                    
                    if zip_buffer.getbuffer().nbytes > 0:
                        st.download_button(
                            label="💾 Download ZIP file",
                            data=zip_buffer,
                            file_name=f"{username}_custom_images.zip",
                            mime="application/zip",
                            key="download_custom_images_zip"
                        )
                    else:
                        st.warning("⚠️ No images to download.")
                except Exception as e:
                    st.error(f"❌ Error creating ZIP: {e}")
        else:
            st.info("📭 No custom images uploaded yet.")
        
        st.markdown("---")
        
        # Upload multiple custom images
        st.markdown("**Upload Custom Images**")
        uploaded_custom_images = st.file_uploader(
            "Upload custom part images (PNG or JPG)",
            type=["png", "jpg", "jpeg"],
            accept_multiple_files=True,
            key="upload_custom_images"
        )
        
        if uploaded_custom_images:
            if st.button("📤 Upload Images", key="upload_custom_images_button"):
                try:
                    stats = upload_custom_images(uploaded_custom_images, user_uploaded_images_dir)
                    
                    if stats["total"] > 0:
                        st.success(
                            f"✅ Uploaded **{stats['total']}** image(s): "
                            f"**{stats['new']}** new, **{stats['overwritten']}** overwritten"
                        )
                        st.rerun()
                    else:
                        st.warning("⚠️ No images were uploaded.")
                except Exception as e:
                    st.error(f"❌ Error uploading images: {e}")
        
        st.markdown("---")
        
        # Delete all custom images
        st.markdown("**Reset Custom Images**")
        if custom_image_count > 0:
            if st.button("🗑️ Delete all custom images", key="delete_custom_images", type="secondary"):
                try:
                    deleted_count = delete_all_custom_images(user_uploaded_images_dir)
                    if deleted_count > 0:
                        st.success(f"✅ Deleted **{deleted_count}** custom image(s).")
                        st.rerun()
                    else:
                        st.warning("⚠️ No images were deleted.")
                except Exception as e:
                    st.error(f"❌ Error deleting images: {e}")
        else:
            st.button("🗑️ Delete all custom images", key="delete_custom_images_disabled", disabled=True)
    
    

# Load mapping
ba_mapping = load_ba_mapping(paths.mapping_path)

# Get max file size from environment
max_file_size_mb = float(os.getenv('MAX_FILE_SIZE_MB', '1.0'))

st.markdown("---")

# ---------------------------------------------------------------------
# --- Mapping Deviation Rules Display
# ---------------------------------------------------------------------
st.markdown("### 🔄 Part Number Mapping Rules")
st.markdown("""
The application uses a two-tier mapping system to convert Rebrickable (RB) part numbers to BrickArchitect (BA) part numbers:

1. **Excel File Mapping** (Primary): Explicit mappings from `part number - BA vs RB - {date}.xlsx`
2. **Generalized Pattern Rules** (Fallback): Automatic pattern-based conversions for common cases
""")

with st.expander("📋 View Generalized Mapping Rules", expanded=False):
    st.markdown("These rules automatically handle common RB part number patterns not explicitly listed in the Excel file:")
    
    rules = get_mapping_deviation_rules()
    
    # Create a dataframe for better display
    rules_df = pd.DataFrame(rules, columns=["Description", "Example RB", "Example BA", "Pattern Rule"])
    
    # Display as a table
    st.dataframe(
        rules_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Description": st.column_config.TextColumn("Rule Description", width="medium"),
            "Example RB": st.column_config.TextColumn("Example RB Part", width="small"),
            "Example BA": st.column_config.TextColumn("Maps to BA Part", width="small"),
            "Pattern Rule": st.column_config.TextColumn("Pattern", width="medium"),
        }
    )
    
    st.info("💡 **Priority**: Excel file mappings are checked first. If no match is found, these generalized rules are applied automatically.")

st.markdown("---")

# ---------------------------------------------------------------------
# --- Collection Default Section
# ---------------------------------------------------------------------
st.markdown("### 🗂️ Collection default")

uploaded_files_list = st.file_uploader(
    "Upload Collection CSVs",
    type=["csv"],
    accept_multiple_files=True,
    key="main_collection_uploader"
)

# Validate and save uploaded files
if uploaded_files_list:
    validated_files = []
    for file in uploaded_files_list:
        is_valid, error_msg = validate_csv_file(file, max_size_mb=max_file_size_mb)
        if is_valid:
            validated_files.append(file)
            # Log file upload
            if st.session_state.get("auth_manager") and st.session_state.auth_manager.audit_logger:
                st.session_state.auth_manager.audit_logger.log_file_upload(
                    username, file.name, "csv", file.size
                )
        else:
            st.error(f"❌ {file.name}: {error_msg}")
    
    if validated_files:
        save_uploadedfiles(validated_files, user_collection_dir)

st.write("Current default collection files:")
manage_default_collection(user_collection_dir)

# Prepare collection files for label generation
default_collection_files = sorted(user_collection_dir.glob("*.csv"))
collection_files_stream = []
collection_file_paths = []

if default_collection_files:
    for csv_file in default_collection_files:
        collection_file_paths.append(csv_file)
        file_handle = open(csv_file, "rb")
        collection_files_stream.append(file_handle)

# ---------------------------------------------------------------------
# --- Precompute Collection Images Section
# ---------------------------------------------------------------------
if collection_files_stream:
    st.markdown("---")
    st.markdown("### 🖼️ Precompute Collection Images")
    st.markdown("Download and cache images for all parts in your collection files.")
    
    precompute_done = st.session_state.get("precompute_collection_done", False)
    
    if not precompute_done:
        if st.button("🔄 Precompute collection images", key="precompute_collection_button"):
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
                    
                    # Find parts without images
                    collection_clean = collection[collection["Part"].notna()].copy()
                    all_parts = set(collection_clean["Part"].astype(str).str.strip().unique())
                    parts_with_images = set(part_images_map.keys())
                    missing_images = sorted(all_parts - parts_with_images)
                    
                    # Save to session state
                    st.session_state["precompute_collection_done"] = True
                    st.session_state["precompute_missing_images"] = missing_images
                    
                    st.success(f"✅ Collection images precomputed successfully! Found {len(parts_with_images)} images.")
                    
                    if missing_images:
                        st.warning(f"⚠️ {len(missing_images)} part(s) have no cached or downloadable images.")
                    
                    st.rerun()
            except Exception as e:
                st.error(f"❌ Error precomputing images: {e}")
            finally:
                # Clear progress indicators
                progress_bar.empty()
                status_text.empty()
    else:
        st.success("✅ Collection images precomputed")
        
        # Show missing images if any
        missing_images = st.session_state.get("precompute_missing_images", [])
        if missing_images:
            with st.expander(f"⚠️ Parts without images ({len(missing_images)})", expanded=False):
                st.markdown("The following parts could not find cached images or download from BrickArchitect:")
                
                # Display in columns for better readability
                cols_per_row = 5
                for i in range(0, len(missing_images), cols_per_row):
                    cols = st.columns(cols_per_row)
                    for j, col in enumerate(cols):
                        if i + j < len(missing_images):
                            col.text(missing_images[i + j])
        
        if st.button("🔄 Recompute images", key="recompute_collection_button"):
            st.session_state["precompute_collection_done"] = False
            st.session_state.pop("precompute_missing_images", None)
            st.rerun()

st.markdown("---")

# ---------------------------------------------------------------------
# --- Labels Generation Section
# ---------------------------------------------------------------------
if collection_files_stream:
    st.markdown("### 🏷️ Generate Labels by Location")
    st.markdown("Create a downloadable zip file with label images organized by location from your collection files.")
    st.info("ℹ️ Labels are generated for **loose parts only**. Parts from LEGO sets are excluded from label generation.")
    
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
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Progress callback function
        def update_progress(current, total, location, status):
            progress = current / total if total > 0 else 0
            progress_bar.progress(progress)
            status_text.text(f"Processing {current}/{total}: {location} - {status}")
        
        try:
            generate_collection_labels_zip(collection_files_stream, ba_mapping, paths.cache_labels, output_mode, progress_callback=update_progress)
        finally:
            # Clear progress indicators
            progress_bar.empty()
            status_text.empty()
    
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
    st.info("📤 Upload at least one Collection file to generate labels.")

st.markdown("---")