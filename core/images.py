# core/images.py
import streamlit as st
import re
import pandas as pd
import requests
from io import BytesIO
from pathlib import Path
from streamlit import cache_data
import streamlit as st
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Set, Optional

# Configuration
MAX_WORKERS = 10  # Thread pool size for parallel image fetching
TIMEOUT = 6  # HTTP request timeout in seconds

def precompute_location_images(collection_df_serialized: bytes, ba_mapping: dict, cache_images_dir, user_uploaded_dir=None, progress_callback=None):
    df = pd.read_csv(BytesIO(collection_df_serialized))
    
    # Filter out rows with missing Location or Part
    df_clean = df[df["Location"].notna() & df["Part"].notna()].copy()
    
    if df_clean.empty:
        return {}, {}
    
    # Vectorized regex cleaning: remove "pr\d+" suffix and strip whitespace
    # Note: The "pr\d+" pattern is handled by generalized rules in the mapping
    df_clean["Part_cleaned"] = df_clean["Part"].astype(str).str.strip()
    
    # Vectorized mapping using ba_mapping (includes generalized rules)
    df_clean["Part_mapped"] = df_clean["Part_cleaned"].map(
        lambda x: ba_mapping.get(x, x)
    )
    
    # Group by Location and collect unique mapped part IDs per location
    location_parts: Dict[str, Set[str]] = {}
    for location, group in df_clean.groupby("Location"):
        unique_ids = set(group["Part_mapped"].dropna().unique())
        if unique_ids:
            location_parts[location] = unique_ids
    
    # Collect all unique part IDs across all locations for batch processing
    all_unique_ids = set()
    for part_ids in location_parts.values():
        all_unique_ids.update(part_ids)

    # Batch fetch all images in parallel (including user-uploaded)
    image_cache = get_cached_images_batch(
        list(all_unique_ids), 
        cache_images_dir, 
        user_uploaded_dir=user_uploaded_dir,
        progress_callback=progress_callback
    )
    
    # Build part_num -> image_path mapping for quick lookup
    # Map original part numbers (before cleaning/mapping) to their image paths
    part_image_map: Dict[str, str] = {}
    total_parts = len(df_clean)
    current_part = 0
    
    for _, row in df_clean.iterrows():
        current_part += 1
        if progress_callback and current_part % 100 == 0:
            progress_callback(current_part, total_parts, f"Mapping part {current_part}", "Processing")
        
        original_part = str(row["Part"])
        mapped_part = row["Part_mapped"]
        if mapped_part in image_cache:
            part_image_map[original_part] = image_cache[mapped_part]
    
    # Build output dictionary with sorted image paths per location
    out = {}
    total_locations = len(location_parts)
    current_location = 0
    
    for location, part_ids in location_parts.items():
        current_location += 1
        if progress_callback:
            progress_callback(current_location, total_locations, location, "Building index")
        
        imgs = []
        for pid in sorted(part_ids):
            img_path = image_cache.get(pid)
            if img_path:
                imgs.append(img_path)
        out[location] = imgs
    
    return out, part_image_map
    
@cache_data(show_spinner=False)
def fetch_image_bytes(url: str, _session: Optional[requests.Session] = None):
    """
    Fetch image bytes from URL, optionally using a session for connection reuse.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
    }
    try:
        if _session:
            r = _session.get(url, headers=headers, timeout=TIMEOUT)
        else:
            r = requests.get(url, headers=headers, timeout=TIMEOUT)
        if r.status_code == 200 and r.content:
            return r.content
    except Exception:
        return None
    return None

def _fetch_single_image(identifier: str, cache_dir: Path, session: Optional[requests.Session] = None) -> tuple[str, str]:
    """
    Fetch a single image from URL and save to cache (thread-safe worker function).
    This function assumes the cache has already been checked.
    Returns (identifier, image_path) tuple, or (identifier, "") if not found.
    """
    local_png = cache_dir / f"{identifier}.png"
    
    # Try to fetch PNG from URL
    url = f"https://brickarchitect.com/content/parts/{identifier}.png"
    data = fetch_image_bytes(url, session)
    if data:
        try:
            with open(local_png, "wb") as f:
                f.write(data)
            return (identifier, str(local_png))
        except Exception:
            pass
    
    return (identifier, "")

def get_cached_images_batch(part_ids: List[str], cache_dir: Path, max_workers: int = MAX_WORKERS, user_uploaded_dir: Optional[Path] = None, progress_callback=None) -> Dict[str, str]:
    """
    Batch fetch images for multiple part IDs in parallel.
    Returns a dictionary mapping part_id -> image_path (or empty string if not found).
    
    Args:
        part_ids: List of part identifiers to fetch images for
        cache_dir: Path to global image cache directory
        max_workers: Number of parallel workers for fetching
        user_uploaded_dir: Optional path to user-uploaded images directory
        progress_callback: Optional callback function(current, total, item, status) for progress reporting
    """
    if not part_ids:
        return {}
    
    total_parts = len(part_ids)
    
    # Pre-check file existence for all parts (batch file I/O check)
    if progress_callback:
        progress_callback(0, total_parts, "Checking cache", "Starting")
    
    file_cache: Dict[str, Optional[str]] = {}
    png_paths = {pid: cache_dir / f"{pid}.png" for pid in part_ids}
    
    # Batch check PNG files
    for idx, (pid, png_path) in enumerate(png_paths.items()):
        if png_path.exists():
            file_cache[pid] = str(png_path)
        if progress_callback and (idx + 1) % 100 == 0:
            progress_callback(idx + 1, total_parts, f"Checked {idx + 1} files", "Checking cache")
    
    # Separate cached and uncached parts
    cached_results = {pid: path for pid, path in file_cache.items() if path}
    uncached_parts = [pid for pid in part_ids if pid not in cached_results]
    
    if progress_callback:
        progress_callback(len(cached_results), total_parts, f"Found {len(cached_results)} cached", "Cache check complete")
    
    if not uncached_parts:
        return cached_results
    
    # Fetch uncached images in parallel
    if progress_callback:
        progress_callback(len(cached_results), total_parts, f"Fetching {len(uncached_parts)} images", "Downloading")
    
    # Create a session for connection reuse across requests
    session = requests.Session()
    results = cached_results.copy()
    completed_count = len(cached_results)
    
    try:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all fetch tasks
            future_to_pid = {
                executor.submit(_fetch_single_image, pid, cache_dir, session): pid
                for pid in uncached_parts
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_pid):
                pid, img_path = future.result()
                if img_path:
                    results[pid] = img_path
                completed_count += 1
                
                # Report progress every 10 images or at the end
                if progress_callback and (completed_count % 10 == 0 or completed_count == total_parts):
                    progress_callback(completed_count, total_parts, f"Downloaded {completed_count - len(cached_results)}", "Downloading")
    finally:
        session.close()
    
    # Check user-uploaded images for any remaining parts without images
    if user_uploaded_dir and user_uploaded_dir.exists():
        still_missing = [pid for pid in part_ids if pid not in results]
        if still_missing and progress_callback:
            progress_callback(completed_count, total_parts, "Checking user uploads", "Finalizing")
        
        for pid in still_missing:
            user_png = user_uploaded_dir / f"{pid}.png"
            user_jpg = user_uploaded_dir / f"{pid}.jpg"
            if user_png.exists():
                results[pid] = str(user_png)
            elif user_jpg.exists():
                results[pid] = str(user_jpg)
    
    return results

@cache_data(show_spinner=False)
def fetch_wanted_part_images(merged_df_serialized: bytes, ba_mapping: dict, cache_images_dir, user_uploaded_dir=None):
    """
    Fetch images for all wanted parts (including those not in collection).
    This complements precompute_location_images by handling "Not Found" parts.

    Args:
        merged_df_serialized: Serialized merged dataframe with wanted parts
        ba_mapping: Dictionary mapping RB part numbers to BA part numbers
        cache_images_dir: Path to image cache directory
        user_uploaded_dir: Optional path to user-uploaded images directory

    Returns:
        Dict mapping part_num -> image_path for all wanted parts
    """
    df = pd.read_csv(BytesIO(merged_df_serialized))

    if df.empty or "Part" not in df.columns:
        return {}

    # Get all unique wanted parts
    wanted_parts = df["Part"].dropna().unique()

    # Clean and map part numbers (generalized rules applied via ba_mapping)
    part_mapping = {}
    for part in wanted_parts:
        part_str = str(part).strip()
        # Map to BA part number (includes generalized rules)
        part_mapped = ba_mapping.get(part_str, part_str)
        part_mapping[part_str] = part_mapped

    # Batch fetch all images (including user-uploaded)
    unique_mapped_parts = list(set(part_mapping.values()))
    image_cache = get_cached_images_batch(unique_mapped_parts, cache_images_dir, user_uploaded_dir=user_uploaded_dir)

    # Build final mapping from original part numbers to image paths
    result = {}
    for original_part, mapped_part in part_mapping.items():
        if mapped_part in image_cache:
            result[original_part] = image_cache[mapped_part]

    return result



def save_user_uploaded_image(uploaded_file, part_num: str, user_uploaded_dir: Path) -> bool:
    """
    Save a user-uploaded image for a specific part number with security validation.
    
    Args:
        uploaded_file: Streamlit UploadedFile object
        part_num: Part number identifier
        user_uploaded_dir: Directory to save user-uploaded images
        
    Returns:
        True if saved successfully, False otherwise
    """
    try:
        from core.security import validate_image_file
        
        # Validate image file (size and content)
        is_valid, error_msg = validate_image_file(uploaded_file, max_size_mb=1.0)
        if not is_valid:
            st.error(f"❌ {error_msg}")
            return False
        
        # Create directory if it doesn't exist
        user_uploaded_dir.mkdir(parents=True, exist_ok=True)
        
        # Determine file extension from uploaded file
        file_ext = uploaded_file.name.split('.')[-1].lower()
        
        # Normalize extension (jpeg -> jpg)
        if file_ext == 'jpeg':
            file_ext = 'jpg'
        
        # Save file with part number as filename
        save_path = user_uploaded_dir / f"{part_num}.{file_ext}"
        with open(save_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        return True
    except Exception as e:
        st.error(f"❌ Error saving image: {e}")
        return False


def create_custom_images_zip(user_uploaded_dir: Path) -> BytesIO:
    """
    Create a ZIP file containing all user-uploaded custom images.
    
    Args:
        user_uploaded_dir: Directory containing user-uploaded images
        
    Returns:
        BytesIO object containing the ZIP file
    """
    import zipfile
    
    zip_buffer = BytesIO()
    
    if not user_uploaded_dir.exists():
        return zip_buffer
    
    # Get all image files
    image_files = list(user_uploaded_dir.glob("*.png")) + list(user_uploaded_dir.glob("*.jpg"))
    
    if not image_files:
        return zip_buffer
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for img_path in sorted(image_files):
            # Add file to zip with just the filename (no path)
            zip_file.write(img_path, arcname=img_path.name)
    
    zip_buffer.seek(0)
    return zip_buffer


def count_custom_images(user_uploaded_dir: Path) -> int:
    """
    Count the number of custom images uploaded by the user.
    
    Args:
        user_uploaded_dir: Directory containing user-uploaded images
        
    Returns:
        Number of custom images
    """
    if not user_uploaded_dir.exists():
        return 0
    
    png_files = list(user_uploaded_dir.glob("*.png"))
    jpg_files = list(user_uploaded_dir.glob("*.jpg"))
    
    return len(png_files) + len(jpg_files)
def upload_custom_images(uploaded_files, user_uploaded_dir: Path) -> dict:
    """
    Upload multiple custom images to user-specific directory with security validation.
    Overwrites existing images with the same name.

    Args:
        uploaded_files: List of uploaded file objects from Streamlit
        user_uploaded_dir: Directory to save uploaded images

    Returns:
        Dictionary with upload statistics:
        - total: Total number of images uploaded
        - new: Number of new images
        - overwritten: Number of overwritten images
        - failed: Number of failed uploads
    """
    if not uploaded_files:
        return {"total": 0, "new": 0, "overwritten": 0, "failed": 0}

    from core.security import validate_image_file
    
    # Ensure directory exists
    user_uploaded_dir.mkdir(parents=True, exist_ok=True)

    stats = {"total": 0, "new": 0, "overwritten": 0, "failed": 0}

    for uploaded_file in uploaded_files:
        # Validate image file
        is_valid, error_msg = validate_image_file(uploaded_file, max_size_mb=1.0)
        if not is_valid:
            st.warning(f"⚠️ Skipped {uploaded_file.name}: {error_msg}")
            stats["failed"] += 1
            continue
        
        # Check if file already exists
        target_path = user_uploaded_dir / uploaded_file.name
        is_overwrite = target_path.exists()

        try:
            # Save the file
            with open(target_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            stats["total"] += 1
            if is_overwrite:
                stats["overwritten"] += 1
            else:
                stats["new"] += 1
        except Exception as e:
            st.warning(f"⚠️ Failed to save {uploaded_file.name}: {e}")
            stats["failed"] += 1

    return stats


def delete_all_custom_images(user_uploaded_dir: Path) -> int:
    """
    Delete all custom images from user-specific directory.

    Args:
        user_uploaded_dir: Directory containing user-uploaded images

    Returns:
        Number of images deleted
    """
    if not user_uploaded_dir.exists():
        return 0

    deleted_count = 0

    # Delete all PNG and JPG files
    for img_path in list(user_uploaded_dir.glob("*.png")) + list(user_uploaded_dir.glob("*.jpg")):
        try:
            img_path.unlink()
            deleted_count += 1
        except Exception:
            pass

    return deleted_count

