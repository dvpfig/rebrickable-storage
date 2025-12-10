# core/images.py
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

@cache_data(show_spinner=False)
def precompute_location_images(collection_df_serialized: bytes, ba_mapping: dict, cache_images_dir):
    df = pd.read_csv(BytesIO(collection_df_serialized))
    
    # Filter out rows with missing Location or Part
    df_clean = df[df["Location"].notna() & df["Part"].notna()].copy()
    
    if df_clean.empty:
        return {}
    
    # Vectorized regex cleaning: remove "pr\d+" suffix and strip whitespace
    df_clean["Part_cleaned"] = df_clean["Part"].astype(str).str.strip().str.replace(
        r"pr\d+$", "", regex=True, case=False
    )
    
    # Vectorized mapping using ba_mapping
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
    
    # Batch fetch all images in parallel
    image_cache = get_cached_images_batch(list(all_unique_ids), cache_images_dir)
    
    # Build output dictionary with sorted image paths per location
    out = {}
    for location, part_ids in location_parts.items():
        imgs = []
        for pid in sorted(part_ids):
            img_path = image_cache.get(pid)
            if img_path:
                imgs.append(img_path)
        out[location] = imgs
    
    return out
    
@cache_data(show_spinner=False)
def fetch_image_bytes(url: str, _session: Optional[requests.Session] = None):
    """Fetch image bytes from URL, optionally using a session for connection reuse."""
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
    Fetch a single image (thread-safe worker function).
    Returns (identifier, image_path) tuple, or (identifier, "") if not found.
    """
    # Check PNG cache first
    local_png = cache_dir / f"{identifier}.png"
    if local_png.exists():
        return (identifier, str(local_png))
    
    # Try to fetch PNG from URL
    url = f"https://brickarchitect.com/content/parts-large/{identifier}.png"
    data = fetch_image_bytes(url, session)
    if data:
        try:
            with open(local_png, "wb") as f:
                f.write(data)
            return (identifier, str(local_png))
        except Exception:
            pass
    
    # Check JPG cache as fallback
    local_jpg = cache_dir / f"{identifier}.jpg"
    if local_jpg.exists():
        return (identifier, str(local_jpg))
    
    return (identifier, "")

def get_cached_images_batch(part_ids: List[str], cache_dir: Path, max_workers: int = MAX_WORKERS) -> Dict[str, str]:
    """
    Batch fetch images for multiple part IDs in parallel.
    Returns a dictionary mapping part_id -> image_path (or empty string if not found).
    """
    if not part_ids:
        return {}
    
    # Pre-check file existence for all parts (batch file I/O check)
    file_cache: Dict[str, Optional[str]] = {}
    png_paths = {pid: cache_dir / f"{pid}.png" for pid in part_ids}
    jpg_paths = {pid: cache_dir / f"{pid}.jpg" for pid in part_ids}
    
    # Batch check PNG files
    for pid, png_path in png_paths.items():
        if png_path.exists():
            file_cache[pid] = str(png_path)
    
    # Check JPG files only for parts without PNG
    for pid in part_ids:
        if pid not in file_cache:
            jpg_path = jpg_paths[pid]
            if jpg_path.exists():
                file_cache[pid] = str(jpg_path)
    
    # Separate cached and uncached parts
    cached_results = {pid: path for pid, path in file_cache.items() if path}
    uncached_parts = [pid for pid in part_ids if pid not in cached_results]
    
    if not uncached_parts:
        return cached_results
    
    # Fetch uncached images in parallel
    # Create a session for connection reuse across requests
    session = requests.Session()
    results = cached_results.copy()
    
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
    finally:
        session.close()
    
    return results

@cache_data(show_spinner=False)
def get_cached_image(identifier: str, cache_dir: Path) -> str:
    """
    Legacy single-image fetch function (kept for backward compatibility).
    For batch operations, use get_cached_images_batch() instead.
    """
    result = get_cached_images_batch([identifier], cache_dir, max_workers=1)
    return result.get(identifier, "")

#@cache_data(show_spinner=False)
def resolve_part_image(part_num: str, ba_mapping: dict, cache_dir: Path) -> str:
    cleaned = re.sub(r"pr\d+$", "", part_num, flags=re.IGNORECASE)
    return get_cached_image(ba_mapping.get(cleaned), cache_dir)
