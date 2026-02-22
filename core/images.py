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
import logging

# Configuration
MAX_WORKERS = 10  # Thread pool size for parallel image fetching
TIMEOUT = 4  # HTTP request timeout in seconds

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def _get_unavailable_images_file(user_data_dir: Optional[Path] = None) -> Path:
    """
    Get the path to the unavailable images file.
    If user_data_dir is provided, use user-specific file, otherwise use global cache.
    
    Args:
        user_data_dir: Optional user-specific data directory
        
    Returns:
        Path to the unavailable images JSON file
    """
    if user_data_dir:
        return user_data_dir / "unavailable_images.json"
    else:
        # Fallback to cache directory for global unavailable images
        from pathlib import Path
        cache_dir = Path("cache")
        cache_dir.mkdir(exist_ok=True)
        return cache_dir / "unavailable_images.json"

def _load_unavailable_images(user_data_dir: Optional[Path] = None) -> Set[str]:
    """
    Load the set of unavailable images from file.
    
    Args:
        user_data_dir: Optional user-specific data directory
        
    Returns:
        Set of part numbers marked as unavailable
    """
    import json
    
    file_path = _get_unavailable_images_file(user_data_dir)
    
    if file_path.exists():
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                return set(data.get("unavailable_parts", []))
        except Exception as e:
            logger.warning(f"Failed to load unavailable images from {file_path}: {e}")
            return set()
    
    return set()

def _save_unavailable_images(unavailable_images: Set[str], user_data_dir: Optional[Path] = None):
    """
    Save the set of unavailable images to file.
    
    Args:
        unavailable_images: Set of part numbers marked as unavailable
        user_data_dir: Optional user-specific data directory
    """
    import json
    
    file_path = _get_unavailable_images_file(user_data_dir)
    
    try:
        # Ensure directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save as JSON
        with open(file_path, 'w') as f:
            json.dump({
                "unavailable_parts": sorted(list(unavailable_images)),
                "last_updated": str(pd.Timestamp.now())
            }, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save unavailable images to {file_path}: {e}")

def precompute_location_images(collection_df_serialized: bytes, ba_mapping: dict, cache_images_dir, user_uploaded_dir=None, progress_callback=None, cache_rb_dir=None, api_key=None, user_data_dir=None):
    df = pd.read_csv(BytesIO(collection_df_serialized))
    
    # Filter out rows with missing Location or Part
    df_clean = df[df["Location"].notna() & df["Part"].notna()].copy()
    
    if df_clean.empty:
        return {}, {}, {"ba_downloaded": 0, "rb_downloaded": 0, "rb_rate_limit_errors": 0, "rb_other_errors": 0}
    
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

    # Batch fetch all images in parallel (including user-uploaded and Rebrickable fallback)
    image_cache, stats = get_cached_images_batch(
        list(all_unique_ids), 
        cache_images_dir, 
        user_uploaded_dir=user_uploaded_dir,
        progress_callback=progress_callback,
        cache_rb_dir=cache_rb_dir,
        api_key=api_key,
        user_data_dir=user_data_dir
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
    
    return out, part_image_map, stats
    
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

def _fetch_single_image(identifier: str, cache_dir: Path, session: Optional[requests.Session] = None, cache_rb_dir: Optional[Path] = None, api_key: Optional[str] = None, unavailable_images: Optional[Set[str]] = None) -> tuple[str, str, str]:
    """
    Fetch a single image from URL and save to cache (thread-safe worker function).
    This function assumes the cache has already been checked.
    Returns (identifier, image_path, source) tuple.
    - source can be: "ba" (BrickArchitect), "rb" (Rebrickable), "rb_rate_limit", "rb_other_error", or "" (not found)
    
    Args:
        identifier: Part number identifier
        cache_dir: Path to BrickArchitect cache directory
        session: Optional requests session for connection reuse
        cache_rb_dir: Optional path to Rebrickable cache directory
        api_key: Optional Rebrickable API key for fallback
        unavailable_images: Optional set to track unavailable images (passed from main thread)
    """
    # Check if this part is already marked as unavailable
    if unavailable_images is None:
        unavailable_images = set()
    
    if identifier in unavailable_images:
        return (identifier, "", "")
    
    local_png = cache_dir / f"{identifier}.png"
    
    # Try to fetch PNG from BrickArchitect URL
    url = f"https://brickarchitect.com/content/parts/{identifier}.png"
    data = fetch_image_bytes(url, session)
    if data:
        try:
            with open(local_png, "wb") as f:
                f.write(data)
            return (identifier, str(local_png), "ba")
        except Exception:
            pass
    
    # Fallback to Rebrickable API if BrickArchitect failed
    if cache_rb_dir and api_key:
        try:
            from core.rebrickable_api import RebrickableAPI, APIError, RateLimitError
            
            # Initialize API client
            api_client = RebrickableAPI(api_key)
            
            # Log attempt to fetch from Rebrickable
            logger.info(f"Attempting to fetch part {identifier} from Rebrickable API")
            
            # Get part info including image URL
            part_info = api_client.get_part_info(identifier)
            
            # Part doesn't exist in Rebrickable (404) - mark as unavailable
            if part_info is None:
                logger.info(f"Part {identifier} not found in Rebrickable (404) - marking as unavailable")
                unavailable_images.add(identifier)
                return (identifier, "", "")
            
            if part_info.get("part_img_url"):
                img_url = part_info["part_img_url"]
                logger.info(f"Part {identifier} found in Rebrickable, image URL: {img_url}")
                
                # Fetch image from Rebrickable
                rb_data = fetch_image_bytes(img_url, session)
                if rb_data:
                    # Save to Rebrickable cache
                    rb_png = cache_rb_dir / f"{identifier}.png"
                    try:
                        cache_rb_dir.mkdir(parents=True, exist_ok=True)
                        with open(rb_png, "wb") as f:
                            f.write(rb_data)
                        logger.info(f"Successfully downloaded and cached part {identifier} from Rebrickable")
                        return (identifier, str(rb_png), "rb")
                    except Exception as e:
                        logger.error(f"Failed to save Rebrickable image for part {identifier}: {e}")
                        pass
                else:
                    logger.warning(f"Failed to download image from Rebrickable URL for part {identifier}")
            else:
                # Part exists but has no image URL - mark as unavailable
                logger.info(f"Part {identifier} exists in Rebrickable but has no image URL - marking as unavailable")
                unavailable_images.add(identifier)
                return (identifier, "", "")
                
        except RateLimitError as e:
            # Rate limit error (429) - don't mark as unavailable, can retry
            logger.warning(f"Rate limit error (429) for part {identifier}: {e}")
            return (identifier, "", "rb_rate_limit")
        except APIError as e:
            # Other API errors (network, server errors) - can retry
            logger.warning(f"API error for part {identifier}: {e}")
            return (identifier, "", "rb_other_error")
        except Exception as e:
            # Unexpected error - mark as unavailable
            logger.error(f"Unexpected error fetching part {identifier} from Rebrickable: {e}")
            unavailable_images.add(identifier)
            return (identifier, "", "")
    
    # No API key or all attempts failed - mark as unavailable
    unavailable_images.add(identifier)
    return (identifier, "", "")

def get_cached_images_batch(part_ids: List[str], cache_dir: Path, max_workers: int = MAX_WORKERS, user_uploaded_dir: Optional[Path] = None, progress_callback=None, cache_rb_dir: Optional[Path] = None, api_key: Optional[str] = None, user_data_dir: Optional[Path] = None) -> tuple[Dict[str, str], Dict[str, int]]:
    """
    Batch fetch images for multiple part IDs in parallel.
    Returns a tuple of (image_dict, stats_dict).
    
    image_dict: mapping part_id -> image_path
    stats_dict: statistics with keys:
        - ba_downloaded: Count of images downloaded from BrickArchitect
        - rb_downloaded: Count of images downloaded from Rebrickable API
        - rb_rate_limit_errors: Count of Rebrickable API rate limit errors (429)
        - rb_other_errors: Count of other Rebrickable API errors (network, server, etc.)
    
    Priority order:
    1. BrickArchitect cache (cache/images/)
    2. Rebrickable cache (cache/images_rb/)
    3. User-uploaded images (user_data/{username}/images_uploaded/)
    4. Download from BrickArchitect
    5. Download from Rebrickable API (if API key available)
    
    Args:
        part_ids: List of part identifiers to fetch images for
        cache_dir: Path to BrickArchitect image cache directory
        max_workers: Number of parallel workers for fetching
        user_uploaded_dir: Optional path to user-uploaded images directory
        progress_callback: Optional callback function(current, total, item, status) for progress reporting
        cache_rb_dir: Optional path to Rebrickable image cache directory
        api_key: Optional Rebrickable API key for fallback
        user_data_dir: Optional user-specific data directory for unavailable images tracking
    """
    if not part_ids:
        return {}, {"ba_downloaded": 0, "rb_downloaded": 0, "rb_rate_limit_errors": 0, "rb_other_errors": 0}
    
    # Load unavailable images from file
    unavailable_images = _load_unavailable_images(user_data_dir)
    
    
    # Initialize statistics
    stats = {
        "ba_downloaded": 0,
        "rb_downloaded": 0,
        "rb_rate_limit_errors": 0,
        "rb_other_errors": 0
    }
    
    total_parts = len(part_ids)
    
    # Pre-check file existence for all parts (batch file I/O check)
    if progress_callback:
        progress_callback(0, total_parts, "Checking cache", "Starting")
    
    file_cache: Dict[str, Optional[str]] = {}
    png_paths = {pid: cache_dir / f"{pid}.png" for pid in part_ids}
    
    # Also check Rebrickable cache if available
    rb_png_paths = {}
    if cache_rb_dir:
        rb_png_paths = {pid: cache_rb_dir / f"{pid}.png" for pid in part_ids}
    
    # Also check user-uploaded images if available
    user_png_paths = {}
    user_jpg_paths = {}
    if user_uploaded_dir and user_uploaded_dir.exists():
        user_png_paths = {pid: user_uploaded_dir / f"{pid}.png" for pid in part_ids}
        user_jpg_paths = {pid: user_uploaded_dir / f"{pid}.jpg" for pid in part_ids}
    
    # Batch check files in priority order
    for idx, pid in enumerate(part_ids):
        # Skip if already marked as unavailable
        if pid in unavailable_images:
            continue
            
        # Priority 1: Check BrickArchitect cache
        if png_paths[pid].exists():
            file_cache[pid] = str(png_paths[pid])
        # Priority 2: Check Rebrickable cache
        elif pid in rb_png_paths and rb_png_paths[pid].exists():
            file_cache[pid] = str(rb_png_paths[pid])
        # Priority 3: Check user-uploaded images (PNG)
        elif pid in user_png_paths and user_png_paths[pid].exists():
            file_cache[pid] = str(user_png_paths[pid])
        # Priority 3: Check user-uploaded images (JPG)
        elif pid in user_jpg_paths and user_jpg_paths[pid].exists():
            file_cache[pid] = str(user_jpg_paths[pid])
            
        if progress_callback and (idx + 1) % 100 == 0:
            progress_callback(idx + 1, total_parts, f"Checked {idx + 1} files", "Checking cache")
    
    # Separate cached and uncached parts (excluding unavailable)
    cached_results = {pid: path for pid, path in file_cache.items() if path}
    uncached_parts = [pid for pid in part_ids if pid not in cached_results and pid not in unavailable_images]
    
    if progress_callback:
        unavailable_count = len([pid for pid in part_ids if pid in unavailable_images])
        status_msg = f"Found {len(cached_results)} cached"
        if unavailable_count > 0:
            status_msg += f", {unavailable_count} unavailable"
        progress_callback(len(cached_results), total_parts, status_msg, "Cache check complete")
    
    if not uncached_parts:
        return cached_results, stats
    
    # Fetch uncached images in parallel (Priority 4 & 5: Download from BA or RB)
    if progress_callback:
        progress_callback(len(cached_results), total_parts, f"Fetching {len(uncached_parts)} images", "Downloading")
    
    # Create a session for connection reuse across requests
    session = requests.Session()
    results = cached_results.copy()
    completed_count = len(cached_results)
    
    try:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all fetch tasks, passing unavailable_images set to avoid session_state access in threads
            future_to_pid = {
                executor.submit(_fetch_single_image, pid, cache_dir, session, cache_rb_dir, api_key, unavailable_images): pid
                for pid in uncached_parts
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_pid):
                pid, img_path, source = future.result()
                if img_path:
                    results[pid] = img_path
                    # Track download source
                    if source == "ba":
                        stats["ba_downloaded"] += 1
                    elif source == "rb":
                        stats["rb_downloaded"] += 1
                elif source == "rb_rate_limit":
                    stats["rb_rate_limit_errors"] += 1
                elif source == "rb_other_error":
                    stats["rb_other_errors"] += 1
                    
                completed_count += 1
                
                # Report progress every 10 images or at the end
                if progress_callback and (completed_count % 10 == 0 or completed_count == total_parts):
                    progress_callback(completed_count, total_parts, f"Downloaded {completed_count - len(cached_results)}", "Downloading")
    finally:
        session.close()
        # Save updated unavailable images to file
        _save_unavailable_images(unavailable_images, user_data_dir)
    
    return results, stats

@cache_data(show_spinner=False)
def fetch_wanted_part_images(merged_df_serialized: bytes, ba_mapping: dict, cache_images_dir, user_uploaded_dir=None, cache_rb_dir=None, api_key=None, user_data_dir=None):
    """
    Fetch images for all wanted parts (including those not in collection).
    This complements precompute_location_images by handling "Not Found" parts.

    Args:
        merged_df_serialized: Serialized merged dataframe with wanted parts
        ba_mapping: Dictionary mapping RB part numbers to BA part numbers
        cache_images_dir: Path to image cache directory
        user_uploaded_dir: Optional path to user-uploaded images directory
        cache_rb_dir: Optional path to Rebrickable image cache directory
        api_key: Optional Rebrickable API key for fallback
        user_data_dir: Optional user-specific data directory for unavailable images tracking

    Returns:
        Tuple of (image_dict, stats_dict)
        - image_dict: Dict mapping part_num -> image_path for all wanted parts
        - stats_dict: Statistics about downloads
    """
    df = pd.read_csv(BytesIO(merged_df_serialized))

    if df.empty or "Part" not in df.columns:
        return {}, {"ba_downloaded": 0, "rb_downloaded": 0, "rb_rate_limit_errors": 0, "rb_other_errors": 0}

    # Get all unique wanted parts
    wanted_parts = df["Part"].dropna().unique()

    # Clean and map part numbers (generalized rules applied via ba_mapping)
    part_mapping = {}
    for part in wanted_parts:
        part_str = str(part).strip()
        # Map to BA part number (includes generalized rules)
        part_mapped = ba_mapping.get(part_str, part_str)
        part_mapping[part_str] = part_mapped

    # Batch fetch all images (including user-uploaded and Rebrickable fallback)
    unique_mapped_parts = list(set(part_mapping.values()))
    image_cache, stats = get_cached_images_batch(
        unique_mapped_parts, 
        cache_images_dir, 
        user_uploaded_dir=user_uploaded_dir,
        cache_rb_dir=cache_rb_dir,
        api_key=api_key,
        user_data_dir=user_data_dir
    )

    # Build final mapping from original part numbers to image paths
    result = {}
    for original_part, mapped_part in part_mapping.items():
        if mapped_part in image_cache:
            result[original_part] = image_cache[mapped_part]

    return result, stats



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


def clear_unavailable_images_cache(user_data_dir: Optional[Path] = None) -> int:
    """
    Clear the cache of parts marked as having unavailable images.
    This allows the system to retry fetching images for these parts.
    
    Args:
        user_data_dir: Optional user-specific data directory
    
    Returns:
        Number of parts cleared from the unavailable cache
    """
    unavailable_images = _load_unavailable_images(user_data_dir)
    count = len(unavailable_images)
    
    # Delete the file
    file_path = _get_unavailable_images_file(user_data_dir)
    if file_path.exists():
        try:
            file_path.unlink()
        except Exception as e:
            logger.error(f"Failed to delete unavailable images file {file_path}: {e}")
    
    return count


def get_unavailable_images_count(user_data_dir: Optional[Path] = None) -> int:
    """
    Get the count of parts currently marked as having unavailable images.
    
    Args:
        user_data_dir: Optional user-specific data directory
    
    Returns:
        Number of parts in the unavailable cache
    """
    unavailable_images = _load_unavailable_images(user_data_dir)
    return len(unavailable_images)

