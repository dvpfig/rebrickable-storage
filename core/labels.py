# core/labels.py
import streamlit as st
import os
import shutil
import pandas as pd
import re
import tempfile
import zipfile
from pathlib import Path
from typing import Tuple, Literal
from io import BytesIO

from core.preprocess import load_collection_files
from core.lbx_merger import LbxMerger

def organize_labels_by_location(
    collection_df: pd.DataFrame,
    ba_mapping: dict,
    labels_source_dir: Path,
    output_mode: Literal["both", "merged_only"] = "both"
) -> Tuple[bytes, dict]:
    """
    Organize label files (.lbx) by location based on collection CSV data.
    
    Args:
        collection_df: DataFrame with columns 'Part' (RB part number) and 'Location'
        ba_mapping: Dictionary mapping RB part numbers to BA part numbers
        labels_source_dir: Directory containing label files (.lbx)
        output_mode: "both" for individual + merged files, "merged_only" for merged files only
    
    Returns:
        Tuple of (zip_file_bytes, stats_dict) where stats_dict contains:
        - total_parts_processed: int
        - files_copied_count: int
        - locations_count: int
        - missing_labels_count: int
        - missing_labels_list: list of missing label filenames
        - merged_files_count: int
        - merge_failures_count: int
    """
    # Column names
    LOC_PART_COL = 'Part'
    LOC_LOCATION_COL = 'Location'
    
    # Build location-to-BA-parts mapping
    location_to_ba_parts = {}
    missing_labels = set()
    total_parts_processed = 0
    files_copied_count = 0
    merged_files_count = 0
    merge_failures_count = 0
    
    for _, row in collection_df.iterrows():
        location = str(row[LOC_LOCATION_COL]).strip()
        rb_part = str(row[LOC_PART_COL]).strip()
        
        if not location or pd.isna(location) or location == 'nan':
            continue
        
        # Filter out set-based locations (format: "Set {set_number} - {set_name}")
        if location.startswith("Set "):
            continue
        
        # Map RB part to BA part
        ba_part = ba_mapping.get(rb_part)
        
        if ba_part:
            if location not in location_to_ba_parts:
                location_to_ba_parts[location] = set()
            location_to_ba_parts[location].add(ba_part)
    
    # Create temporary directory for organizing files
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        output_base_dir = temp_path / 'locations'
        output_base_dir.mkdir(exist_ok=True)
        
        # Initialize merger with 0mm spacing and no length limit
        merger = LbxMerger(max_length_mm=9999, spacing_mm=0)
        
        # Create folders and copy files
        for location, ba_parts_set in location_to_ba_parts.items():
            # Sanitize location name for use as a directory name
            sanitized_location_name = re.sub(r'[\\/|:*?"<>]', '_', location)
            location_dir = output_base_dir / sanitized_location_name
            location_dir.mkdir(parents=True, exist_ok=True)
            
            # Collect label files for this location
            location_label_files = []
            
            for ba_part in ba_parts_set:
                total_parts_processed += 1
                label_filename = f"{ba_part}.lbx"
                source_file_path = labels_source_dir / label_filename
                
                if source_file_path.exists():
                    # Copy individual files only if mode is "both"
                    if output_mode == "both":
                        dest_file_path = location_dir / label_filename
                        try:
                            shutil.copy2(source_file_path, dest_file_path)
                            files_copied_count += 1
                        except Exception as e:
                            # Log error but continue
                            pass
                    
                    # Collect for merging
                    location_label_files.append(source_file_path)
                else:
                    missing_labels.add(label_filename)
            
            # Create merged file for this location
            if location_label_files:
                # Sort files alphabetically for consistent ordering
                location_label_files.sort(key=lambda p: p.name)
                
                merged_filename = f"{sanitized_location_name}.lbx"
                merged_file_path = location_dir / merged_filename
                
                try:
                    success = merger.merge_labels(location_label_files, merged_file_path)
                    if success:
                        merged_files_count += 1
                    else:
                        merge_failures_count += 1
                except Exception as e:
                    # Log error but continue
                    merge_failures_count += 1
        
        # Create zip file
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(output_base_dir):
                for file in files:
                    file_path = Path(root) / file
                    # Create relative path within zip
                    arcname = file_path.relative_to(output_base_dir.parent)
                    zipf.write(file_path, arcname)
        
        zip_buffer.seek(0)
        zip_bytes = zip_buffer.read()
        
        stats = {
            'total_parts_processed': total_parts_processed,
            'files_copied_count': files_copied_count,
            'locations_count': len(location_to_ba_parts),
            'missing_labels_count': len(missing_labels),
            'missing_labels_list': list(missing_labels)[:20],  # First 20 for display
            'merged_files_count': merged_files_count,
            'merge_failures_count': merge_failures_count,
            'output_mode': output_mode
        }
        
        return zip_bytes, stats


def generate_collection_labels_zip(
    collection_files_stream,
    ba_mapping: dict,
    labels_source_dir: Path,
    output_mode: Literal["both", "merged_only"] = "both"
):

    with st.spinner("Organizing labels by location..."):
        try:
            # Prepare collection files for labels generation
            # Reset file handles to beginning if they're file objects
            labels_collection_stream = []
            for f in collection_files_stream:
                if hasattr(f, 'seek'):
                    f.seek(0)
                labels_collection_stream.append(f)
            
            # Load collection files for labels generation
            collection_for_labels = load_collection_files(labels_collection_stream)
            
            # Generate labels zip
            zip_bytes, stats = organize_labels_by_location(
                collection_for_labels,
                ba_mapping,
                labels_source_dir,
                output_mode
            )
            
            if zip_bytes and stats['locations_count'] > 0:
                st.success(f"✅ Successfully generated labels zip file!")
                
                # Build statistics message based on output mode
                mode_display = "Both individual and merged files" if stats['output_mode'] == "both" else "Merged files only"
                stats_msg = (
                    f"**Statistics:**\n"
                    f"- Output mode: {mode_display}\n"
                    f"- Locations: {stats['locations_count']}\n"
                    f"- Parts processed: {stats['total_parts_processed']}\n"
                )
                
                if stats['output_mode'] == "both":
                    stats_msg += f"- Individual labels copied: {stats['files_copied_count']}\n"
                
                stats_msg += (
                    f"- Merged files created: {stats['merged_files_count']}\n"
                    f"- Missing labels: {stats['missing_labels_count']}"
                )
                
                if stats['merge_failures_count'] > 0:
                    stats_msg += f"\n- ⚠️ Merge failures: {stats['merge_failures_count']}"
                
                st.info(stats_msg)
                
                if stats['missing_labels_count'] > 0:
                    with st.expander("⚠️ View missing labels"):
                        missing_list = stats['missing_labels_list']
                        st.text("\n".join(missing_list))
                        if stats['missing_labels_count'] > 20:
                            st.text(f"... and {stats['missing_labels_count'] - 20} more")
                
                # Store zip bytes in session state for download
                st.session_state["labels_zip_bytes"] = zip_bytes
                st.session_state["labels_zip_filename"] = f"labels_by_location_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.zip"
                
                st.rerun()
            else:
                if stats['locations_count'] == 0:
                    st.warning("No locations found in collection files. Please ensure your collection files contain 'Location' column with valid location names.")
                else:
                    st.error("Failed to generate zip file. Please check that collection files contain valid data.")
        except Exception as e:
            st.error(f"Error generating labels: {e}")
            import traceback
            st.code(traceback.format_exc())

