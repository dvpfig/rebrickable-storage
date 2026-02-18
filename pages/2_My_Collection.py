import streamlit as st
import pandas as pd
from pathlib import Path
import hashlib

from core.paths import init_paths, save_uploadedfiles, manage_default_collection
from core.mapping import load_ba_mapping
from core.labels import generate_collection_labels_zip
from core.preprocess import load_collection_files
from core.images import precompute_location_images, create_custom_images_zip, count_custom_images, upload_custom_images, delete_all_custom_images
from core.security import validate_csv_file
import os
from dotenv import load_dotenv

#st.set_page_config(page_title="My Collection", page_icon="📈")

st.title("🏷️ My Collection")
st.sidebar.header("🏷️ My Collection")

# Load environment variables
load_dotenv()

# Check authentication
if not st.session_state.get("authentication_status"):
    st.warning("⚠️ Please login first")
    st.stop()

# Get paths and user info
paths = init_paths()
username = st.session_state.get("username")
user_collection_dir = paths.user_data_dir / username / "collection"
user_uploaded_images_dir = paths.get_user_uploaded_images_dir(username)

# Sidebar sections for collection management
with st.sidebar:
    st.markdown("---")
    
    # Collection default folder
    with st.expander("🗂️ Collection default"):
        uploaded_files_list = st.file_uploader(
            "Upload Collection CSVs",
            type=["csv"],
            accept_multiple_files=True,
            key="sidebar_collection_uploader"
        )
        save_uploadedfiles(uploaded_files_list, user_collection_dir)
        st.write("Current default collection files:")
        manage_default_collection(user_collection_dir)
    
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
    
    st.markdown("---")

# Load mapping
ba_mapping = load_ba_mapping(paths.mapping_path)

# Get max file size from environment
max_file_size_mb = float(os.getenv('MAX_FILE_SIZE_MB', '1.0'))

st.markdown("---")

# ---------------------------------------------------------------------
# --- Collection Files Section
# ---------------------------------------------------------------------
st.markdown("### 🗂️ Collection: Pre-selected Files")

default_collection_files = sorted(user_collection_dir.glob("*.csv"))
selected_files = []

if default_collection_files:
    for csv_file in default_collection_files:
        include = st.checkbox(f"Include {csv_file.name}", value=True, key=f"inc_{csv_file.name}")
        if include:
            selected_files.append(csv_file)
else:
    st.info("📭 No pre-selected collection files found. Upload files using the sidebar or below.")

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
# --- Labels Generation Section
# ---------------------------------------------------------------------
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
        generate_collection_labels_zip(collection_files_stream, ba_mapping, paths.cache_labels, output_mode)
    
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