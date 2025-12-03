# core/images.py
import re
import pandas as pd
import requests
from io import BytesIO
from pathlib import Path
from streamlit import cache_data
#import streamlit as st

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
        #Debug
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
    local_png = cache_dir / f"{identifier}.png"
    if local_png.exists():
        return str(local_png)
    
    local_jpg = cache_dir / f"{identifier}.jpg"
    if local_jpg.exists():
        return str(local_jpg)

    return ""

#@cache_data(show_spinner=False)
def resolve_part_image(part_num: str, ba_mapping: dict, cache_dir: Path) -> str:
    cleaned = re.sub(r"pr\d+$", "", part_num, flags=re.IGNORECASE)
    return get_cached_image(ba_mapping.get(cleaned), cache_dir)
