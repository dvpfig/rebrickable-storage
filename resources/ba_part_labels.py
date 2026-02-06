"""
BrickArchitect Label Downloader

This module downloads label files (.lbx) from BrickArchitect based on the
part mapping Excel file. Labels are cached locally to avoid re-downloading.
"""

import os
import requests
from pathlib import Path
import openpyxl
from urllib.parse import urlparse


def download_ba_labels(mapping_path: Path, cache_labels_dir: Path, timeout: int = 10, progress_callback=None, stop_flag_callback=None, stats_callback=None):
    """
    Download BrickArchitect label files based on the mapping Excel file.
    
    Args:
        mapping_path: Path to the Excel file containing BA part mappings
        cache_labels_dir: Directory to cache downloaded label files
        timeout: Request timeout in seconds
        progress_callback: Optional callback function(message, status) for progress updates
            status can be: 'info', 'success', 'warning', 'error'
        stop_flag_callback: Optional callback function() that returns True if download should stop
        stats_callback: Optional callback function(stats) to update stats in real-time
    
    Returns:
        dict: Statistics about the download process
            - total: Total number of label URLs found
            - skipped: Number of files already cached
            - downloaded: Number of files successfully downloaded
            - failed: Number of failed downloads
            - stopped: Whether the download was stopped by user
    """
    stats = {"total": 0, "skipped": 0, "downloaded": 0, "failed": 0, "stopped": False}
    
    def log(message, status="info"):
        if progress_callback:
            progress_callback(message, status)
        else:
            print(message)
    
    def should_stop():
        """Check if user requested to stop"""
        if stop_flag_callback and stop_flag_callback():
            return True
        return False
    
    def update_stats():
        """Update stats via callback if provided"""
        if stats_callback:
            stats_callback(stats.copy())
    
    # Setup
    os.makedirs(cache_labels_dir, exist_ok=True)
    
    # Load workbook
    try:
        wb = openpyxl.load_workbook(mapping_path)
        ws = wb.active
    except Exception as e:
        log(f"❌ Error loading Excel file: {e}", "error")
        raise
    
    # Identify columns
    header_row = [cell.value for cell in ws[1]]
    try:
        partnum_col = header_row.index("BA partnum") + 1
        labelurl_col = header_row.index("BA label URL") + 1
    except ValueError as e:
        log("❌ Could not find required columns 'BA partnum' or 'BA label URL'", "error")
        raise ValueError("Could not find required columns 'BA partnum' or 'BA label URL'") from e
    
    # Download each label file
    for row in ws.iter_rows(min_row=2):
        # Check if user wants to stop
        if should_stop():
            log("⏹️ Download stopped by user", "warning")
            stats["stopped"] = True
            update_stats()
            break
        
        partnum = row[partnum_col - 1].value
        label_url = row[labelurl_col - 1].value
        
        if not label_url or "No label available" in str(label_url):
            continue
        
        stats["total"] += 1
        update_stats()
        
        # Extract filename from URL
        parsed = urlparse(label_url)
        filename = os.path.basename(parsed.path)
        
        if not filename.lower().endswith(".lbx"):
            continue
        
        save_path = os.path.join(cache_labels_dir, filename)
        
        # Skip if already downloaded
        if os.path.exists(save_path):
            log(f"✅ Skipping (already exists): {filename}", "info")
            stats["skipped"] += 1
            update_stats()
            continue
        
        # Check again before downloading (user might have clicked stop)
        if should_stop():
            log("⏹️ Download stopped by user", "warning")
            stats["stopped"] = True
            update_stats()
            break
        
        # Download file
        try:
            log(f"⬇️ Downloading {filename}...", "info")
            response = requests.get(label_url, timeout=timeout)
            if response.status_code == 200 and response.content:
                with open(save_path, "wb") as f:
                    f.write(response.content)
                log(f"✅ Saved: {filename}", "success")
                stats["downloaded"] += 1
                update_stats()
            else:
                log(f"⚠️ Failed to download {filename} (status: {response.status_code})", "warning")
                stats["failed"] += 1
                update_stats()
        except Exception as e:
            log(f"❌ Error downloading {filename}: {e}", "error")
            stats["failed"] += 1
            update_stats()
    
    # Summary
    if stats["stopped"]:
        log(f"⏹️ Download stopped!", "warning")
    else:
        log(f"🎉 Download complete!", "success")
    
    return stats


# Command-line execution
if __name__ == "__main__":
    SCRIPT_DIR = Path(__file__).parent
    INPUT_FILE = SCRIPT_DIR / "part number - BA vs RB - 2025-11-11.xlsx"
    GLOBAL_CACHE_DIR = SCRIPT_DIR.parent / "cache"
    CACHE_LABELS_DIR = GLOBAL_CACHE_DIR / "labels"
    
    download_ba_labels(INPUT_FILE, CACHE_LABELS_DIR)
