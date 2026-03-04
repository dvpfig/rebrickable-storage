# core/colors.py
import pandas as pd
import requests
import zipfile
import io
from pathlib import Path
from streamlit import cache_data


def download_colors_csv(colors_path: Path) -> bool:
    """
    Download colors.csv from Rebrickable and save to the specified path.

    Fetches the zipped CSV from https://cdn.rebrickable.com/media/downloads/colors.csv.zip,
    extracts it, and saves as colors.csv.

    Args:
        colors_path: Path where colors.csv should be saved

    Returns:
        bool: True if download was successful, False otherwise
    """
    url = "https://cdn.rebrickable.com/media/downloads/colors.csv.zip"
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
            # Find the CSV file inside the zip
            csv_files = [f for f in zf.namelist() if f.endswith('.csv')]
            if not csv_files:
                return False

            # Extract the first CSV file
            colors_path.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(csv_files[0]) as src, open(colors_path, 'wb') as dst:
                dst.write(src.read())

        return True
    except Exception:
        return False


def ensure_colors_csv(colors_path: Path) -> bool:
    """
    Ensure colors.csv exists. If not found, download from Rebrickable.

    Args:
        colors_path: Path where colors.csv should exist

    Returns:
        bool: True if file exists (or was downloaded), False if unavailable
    """
    if colors_path.exists():
        return True
    return download_colors_csv(colors_path)


@cache_data(show_spinner=False)
def load_colors(colors_path):
    """
    Load and parse LEGO color data from CSV file.
    
    Args:
        colors_path: Path to the colors CSV file
        
    Returns:
        pd.DataFrame: DataFrame with columns id, name, rgb, is_trans
    """
    try:
        colors = pd.read_csv(colors_path)
        if "name" in colors.columns:
            colors["name"] = colors["name"].astype(str).str.strip()
        if "rgb" in colors.columns:
            colors["rgb"] = colors["rgb"].astype(str).str.strip()
        if "is_trans" in colors.columns:
            colors["is_trans"] = colors["is_trans"].astype(str).str.lower().isin(["true", "1", "yes"])
        if "id" in colors.columns:
            colors["id"] = pd.to_numeric(colors["id"], errors="coerce").fillna(-1).astype(int)
        return colors
    except Exception:
        return pd.DataFrame(columns=["id", "name", "rgb", "is_trans"])

@cache_data(show_spinner=False)
def build_color_lookup(colors_df):
    """
    Build a lookup dictionary for fast color information retrieval.
    
    Args:
        colors_df: DataFrame with color data (id, name, rgb, is_trans)
        
    Returns:
        dict: {color_id: {'name': str, 'rgb': str, 'is_trans': bool}}
    """
    lookup = {}
    for _, r in colors_df.iterrows():
        try:
            cid = int(r.get("id", -1))
        except Exception:
            continue
        lookup[cid] = {
            "name": r.get("name", "Unknown"),
            "rgb": r.get("rgb", "000000"),
            "is_trans": bool(r.get("is_trans", False)),
        }
    return lookup

@cache_data(show_spinner=False)
def render_color_cell(color_id, color_lookup):
    """
    Render an HTML color cell with color swatch and name.
    
    Args:
        color_id: LEGO color ID (integer)
        color_lookup: Dictionary mapping color IDs to color info
        
    Returns:
        str: HTML string with color swatch and label
    """
    try:
        cid = int(color_id)
    except Exception:
        return "[Unknown color]"
    color_info = color_lookup.get(cid)
    if not color_info:
        return f"[Unknown ID: {cid}]"
    rgb = color_info["rgb"].lstrip('#')
    trans = color_info["is_trans"]
    name = color_info["name"]
    label = "Transparent" if trans else "Solid"
    return (
        f"<div style='display:flex;align-items:center;gap:8px;'>"
        f"<div style='width:24px;height:24px;border-radius:4px;border:1px solid #999; background-color:#{rgb};'></div>"
        f"<div><b>{name}</b><br><span style='font-size:0.8em;color:#666'>{label}</span></div>"
        f"</div>"
    )
