# core/labels.py
import os
import shutil
import pandas as pd
import re
import tempfile
import zipfile
from pathlib import Path
from typing import Tuple
from io import BytesIO

def organize_labels_by_location(
    collection_df: pd.DataFrame,
    ba_mapping: dict,
    labels_source_dir: Path
) -> Tuple[bytes, dict]:
    """
    Organize label files (.lbx) by location based on collection CSV data.
    
    Args:
        collection_df: DataFrame with columns 'Part' (RB part number) and 'Location'
        ba_mapping: Dictionary mapping RB part numbers to BA part numbers
        labels_source_dir: Directory containing label files (.lbx)
    
    Returns:
        Tuple of (zip_file_bytes, stats_dict) where stats_dict contains:
        - total_parts_processed: int
        - files_copied_count: int
        - locations_count: int
        - missing_labels_count: int
        - missing_labels_list: list of missing label filenames
    """
    # Column names
    LOC_PART_COL = 'Part'
    LOC_LOCATION_COL = 'Location'
    
    # Build location-to-BA-parts mapping
    location_to_ba_parts = {}
    missing_labels = set()
    total_parts_processed = 0
    files_copied_count = 0
    
    for _, row in collection_df.iterrows():
        location = str(row[LOC_LOCATION_COL]).strip()
        rb_part = str(row[LOC_PART_COL]).strip()
        
        if not location or pd.isna(location) or location == 'nan':
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
        
        # Create folders and copy files
        for location, ba_parts_set in location_to_ba_parts.items():
            # Sanitize location name for use as a directory name
            sanitized_location_name = re.sub(r'[\\/|:*?"<>]', '_', location)
            location_dir = output_base_dir / sanitized_location_name
            location_dir.mkdir(parents=True, exist_ok=True)
            
            for ba_part in ba_parts_set:
                total_parts_processed += 1
                label_filename = f"{ba_part}.lbx"
                source_file_path = labels_source_dir / label_filename
                dest_file_path = location_dir / label_filename
                
                if source_file_path.exists():
                    try:
                        shutil.copy2(source_file_path, dest_file_path)
                        files_copied_count += 1
                    except Exception as e:
                        # Log error but continue
                        pass
                else:
                    missing_labels.add(label_filename)
        
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
            'missing_labels_list': list(missing_labels)[:20]  # First 20 for display
        }
        
        return zip_bytes, stats

