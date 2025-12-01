# core/images.py
import re
import pandas as pd
import requests
from io import BytesIO
from pathlib import Path
from streamlit import cache_data

@cache_data(show_spinner=False)
def precompute_location_images(collection_df_serialized: bytes, ba_mapping: dict, cache_images_dir):
    df = pd.read_csv(BytesIO(collection_df_serialized))
    out = {}
    for location in df["Location"].dropna().unique():
        parts = df.loc[df["Location"] == location, "Part"].dropna().unique()
        cleaned = [re.sub(r"pr\\d+$", "", str(p).strip(), flags=re.IGNORECASE) for p in parts]
        mapped = [ba_mapping.get(c, c) for c in cleaned]
        unique_ids = sorted(set(mapped))
        imgs = []
        for pid in unique_ids:
            p = get_cached_image(pid, cache_images_dir)
            if p:
                imgs.append(p)
        out[location] = imgs
        # Debug
        #st.write(imgs)
    return out
    
@cache_data(show_spinner=False)
def fetch_image_bytes(url: str):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
    }
    try:
        r = requests.get(url, headers=headers, timeout=6)
        if r.status_code == 200 and r.content:
            return r.content
    except Exception:
        return None
    return None

@cache_data(show_spinner=False)
def get_cached_image(identifier: str, cache_dir: Path) -> str:
    if not identifier:
        return ""
    local_png = cache_dir / f"{identifier}.png"
    local_jpg = cache_dir / f"{identifier}.jpg"
    if local_png.exists():
        return str(local_png)
    if local_jpg.exists():
        return str(local_jpg)
    url = f"https://brickarchitect.com/content/parts-large/{identifier}.png"
    data = fetch_image_bytes(url)
    if data:
        try:
            with open(local_png, "wb") as f:
                f.write(data)
            return str(local_png)
        except Exception:
            return ""
    return ""

def resolve_part_image(part_num: str, ba_mapping: dict, cache_dir: Path) -> str:
    if not part_num or str(part_num).strip().lower() in ["nan", "none", ""]:
        return ""
    part_original = str(part_num).strip()
    cleaned = re.sub(r"pr\d+$", "", part_original, flags=re.IGNORECASE)
    candidates = []
    if ba_mapping:
        mapped = ba_mapping.get(cleaned)
        if mapped:
            candidates.append(mapped)
    candidates.append(cleaned)
    for cid in candidates:
        p = get_cached_image(cid, cache_dir)
        if p:
            return p
    return ""
