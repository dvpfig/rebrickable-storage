# core/colors.py
import pandas as pd
from streamlit import cache_data

@cache_data(show_spinner=False)
def load_colors(colors_path):
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
