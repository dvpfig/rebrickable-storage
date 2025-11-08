import streamlit as st
import pandas as pd
import requests
from pathlib import Path
from io import BytesIO
import re
import json
import hashlib
import time
import os
import sys

# ---------------------------------------------------------------------
# --- Page setup
# ---------------------------------------------------------------------
st.set_page_config(page_title="Rebrickable Collection - Parts Finder", layout="wide")
st.title("🧱 Rebrickable Collection - Parts Finder")

# ---------------------------------------------------------------------
# --- Base path resolution (cross-platform)
# ---------------------------------------------------------------------
# Resolve root directory of the script
try:
    ROOT_DIR = Path(__file__).resolve().parent
except NameError:
    # Fallback if running interactively (e.g., streamlit run)
    ROOT_DIR = Path(os.getcwd()).resolve()

# Define main folders relative to the script
GLOBAL_CACHE_DIR = ROOT_DIR / "cache"
CACHE_IMAGES_DIR = GLOBAL_CACHE_DIR / "images"
RESOURCES_DIR = ROOT_DIR / "resources"
DEFAULT_COLLECTION_DIR = ROOT_DIR / "collection"

# Define main resource files
MAPPING_PATH = RESOURCES_DIR / "part number - BA vs RB - filled.xlsx"
COLORS_PATH = RESOURCES_DIR / "colors.csv"

# Ensure directories exist
for d in [GLOBAL_CACHE_DIR, CACHE_IMAGES_DIR, RESOURCES_DIR, DEFAULT_COLLECTION_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Print environment info in logs (useful when deployed)
print(f"Running on platform: {sys.platform}")
print(f"Root dir: {ROOT_DIR}")
print(f"Cache dir: {GLOBAL_CACHE_DIR}")
print(f"Resources dir: {RESOURCES_DIR}")

# ---------------------------------------------------------------------
# --- Session-state initialization
# ---------------------------------------------------------------------
if "collection_df" not in st.session_state:
    st.session_state["collection_df"] = None

if "found_counts" not in st.session_state:
    st.session_state["found_counts"] = {}  # {(part, color, location): found_count}

if "locations_index" not in st.session_state:
    # maps location -> list of local image paths
    st.session_state["locations_index"] = {}

if "ba_mapping" not in st.session_state:
    st.session_state["ba_mapping"] = None

if "mapping_warnings" not in st.session_state:
    st.session_state["mapping_warnings"] = {"missing_mappings": set(), "missing_images": set()}

# track which location UI is currently expanded (only that location renders widgets)
if "expanded_loc" not in st.session_state:
    st.session_state["expanded_loc"] = None

# store merged df to avoid re-merging on every widget interaction
if "merged_df" not in st.session_state:
    st.session_state["merged_df"] = None
if "merged_source_hash" not in st.session_state:
    st.session_state["merged_source_hash"] = None

# ---------------------------------------------------------------------
# --- Helpers: short deterministic widget key (MD5)
# ---------------------------------------------------------------------
def short_key(*args) -> str:
    s = "::".join(map(str, args))
    return hashlib.md5(s.encode("utf-8")).hexdigest()

# ---------------------------------------------------------------------
# --- Load BA mapping from provided Excel (cached via st.cache_data)
# ---------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def read_ba_mapping_from_excel_bytes(excel_bytes: bytes) -> dict:
    try:
        df = pd.read_excel(BytesIO(excel_bytes))
    except Exception:
        return {}
    # normalize
    cols = {c: c.strip() for c in df.columns}
    df = df.rename(columns=cols)
    ba_cols = [c for c in df.columns if c.lower().startswith("ba")]
    rb_cols = [c for c in df.columns if c.lower().startswith("rb")]
    mapping = {}
    if not ba_cols:
        return mapping
    for _, r in df.iterrows():
        ba_val = str(r.get(ba_cols[0], "")).strip()
        if not ba_val or ba_val.lower() in ["nan", "none"]:
            continue
        for rc in rb_cols:
            rv = r.get(rc)
            if pd.isna(rv):
                continue
            rv_str = str(rv).strip()
            if not rv_str:
                continue
            mapping[rv_str] = ba_val
    return mapping

# Preload mapping file if exists
if st.session_state["ba_mapping"] is None:
    if MAPPING_PATH.exists():
        try:
            with open(MAPPING_PATH, "rb") as f:
                st.session_state["ba_mapping"] = read_ba_mapping_from_excel_bytes(f.read())
            #st.info(f"Loaded BA mapping from {MAPPING_PATH.name}")
        except Exception:
            st.session_state["ba_mapping"] = {}
            st.warning("Could not load BA mapping from resources.")
    else:
        st.session_state["ba_mapping"] = {}
        st.info("No BA mapping file found in resources; continuing without it.")

# ---------------------------------------------------------------------
# --- Image fetching & caching helpers
# ---------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def fetch_image_bytes(url: str) -> bytes | None:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/126.0.0.0 Safari/537.36"
        ),
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
        "Referer": url.rsplit('/', 1)[0],
    }
    try:
        r = requests.get(url, headers=headers, timeout=6)
        if r.status_code == 200 and r.content:
            return r.content
    except requests.exceptions.RequestException:
        return None
    return None

@st.cache_data(show_spinner=False)
def get_part_image_cached(identifier: str) -> str:
    """Return local path for identifier image; download once and cache on disk."""
    if not identifier:
        return ""
    # check if png image with BA part nr exists
    local_png = CACHE_IMAGES_DIR / f"{identifier}.png"
    if local_png.exists():
        return str(local_png)
    # fallback try jpg
    local_jpg = CACHE_IMAGES_DIR / f"{identifier}.jpg"
    if local_jpg.exists():
        return str(local_jpg)
        
    # attempt to fetch image online, first png then jpg
    url = f"https://brickarchitect.com/content/parts-large/{identifier}.png"
    data = fetch_image_bytes(url)
    if data:
        with open(local_png, "wb") as f:
            f.write(data)
        return str(local_png)
    
    url_jpg = f"https://brickarchitect.com/content/parts-large/{identifier}.jpg"
    data = fetch_image_bytes(url_jpg)
    if data:
        with open(local_jpg, "wb") as f:
            f.write(data)
        return str(local_jpg)
    return ""

def get_part_image(part_num: str, ba_mapping: dict) -> str:
    """Try BA mapped image first, then fallback to cleaned RB id. Records missing mapping/images once."""
    if not part_num or str(part_num).strip().lower() in ["nan", "none", ""]:
        return ""
    part_original = str(part_num).strip()
    cleaned = re.sub(r"pr\d+$", "", part_original, flags=re.IGNORECASE)
    candidates = []
    if ba_mapping:
        mapped = ba_mapping.get(cleaned)
        if mapped:
            candidates.append(mapped)
        else:
            if cleaned not in st.session_state["mapping_warnings"]["missing_mappings"]:
                st.session_state["mapping_warnings"]["missing_mappings"].add(cleaned)
    candidates.append(cleaned)
    for cid in candidates:
        if not cid:
            continue
        p = get_part_image_cached(cid)
        if p:
            return p
    if part_original not in st.session_state["mapping_warnings"]["missing_images"]:
        st.session_state["mapping_warnings"]["missing_images"].add(part_original)
    return ""

# Precompute images for all locations once
@st.cache_data(show_spinner=False)
def precompute_all_location_images(collection_df_serialized: bytes, ba_mapping: dict) -> dict:
    """
    Accept a serialized (csv bytes) to make the cache key depend on the collection content.
    Returns dict: location -> [local image paths...]
    """
    # read the collection copy
    df = pd.read_csv(BytesIO(collection_df_serialized))
    out = {}
    for location in df["Location"].dropna().unique():
        parts = df.loc[df["Location"] == location, "Part"].dropna().unique()
        cleaned = [re.sub(r"pr\d+$", "", str(p).strip(), flags=re.IGNORECASE) for p in parts]
        mapped = [ba_mapping.get(c, c) for c in cleaned]
        unique_ids = sorted(set(mapped))
        imgs = []
        for pid in unique_ids:
            p = get_part_image_cached(pid)
            if p:
                imgs.append(p)
        out[location] = imgs
    return out

# ---------------------------------------------------------------------
# --- Load colors.csv (cached)
# ---------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def load_colors():
    try:
        colors = pd.read_csv(COLORS_PATH)
        colors["name"] = colors["name"].str.strip()
        colors["rgb"] = colors["rgb"].str.strip()
        colors["is_trans"] = colors["is_trans"].astype(str).str.lower().isin(["true", "1", "yes"])
        colors["id"] = colors["id"].astype(int)
        return colors
    except Exception:
        return pd.DataFrame(columns=["id", "name", "rgb", "is_trans"])

colors_df = load_colors()
color_lookup = {
    int(cid): {"name": name, "rgb": rgb, "is_trans": trans}
    for cid, name, rgb, trans in zip(colors_df.get("id", []), colors_df.get("name", []), colors_df.get("rgb", []), colors_df.get("is_trans", []))
}

def render_color_cell(color_id) -> str:
    try:
        cid = int(color_id)
    except (ValueError, TypeError):
        return "[Unknown color]"
    color_info = color_lookup.get(cid)
    if not color_info:
        return f"[Unknown ID: {cid}]"
    rgb = color_info["rgb"]
    trans = color_info["is_trans"]
    name = color_info["name"]
    label = "Transparent" if trans else "Solid"
    return (
        f"<div style='display:flex;align-items:center;gap:8px;'>"
        f"<div style='width:24px;height:24px;border-radius:4px;border:1px solid #999;"
        f"background-color:#{rgb};'></div>"
        f"<div><b>{name}</b><br><span style='font-size:0.8em;color:#666'>{label}</span></div>"
        f"</div>"
    )

# ---------------------------------------------------------------------
# --- File upload UI (same as before)
# ---------------------------------------------------------------------
#st.markdown("## 📂 WANTED & COLLECTION Lists")

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("### 🗂️ Wanted parts: Upload")
    wanted_files = st.file_uploader("Upload one or more Wanted Parts CSVs", type=["csv"], accept_multiple_files=True)

with col2:
    st.markdown("### 🗂️ Collection: Pre-selected Collection Files Found")
    default_collection_files = sorted(DEFAULT_COLLECTION_DIR.glob("*.csv"))
    selected_files = []
    if default_collection_files:
        for csv_file in default_collection_files:
            include = st.checkbox(f"Include {csv_file.name}", value=True, key=f"inc_{csv_file.name}")
            if include:
                selected_files.append(csv_file)
    else:
        st.info("No CSV files found in 'collection' folder.")
    uploaded_collection_files = st.file_uploader("Upload one or more Collection CSVs (with Location)", type=["csv"], accept_multiple_files=True)

# Combine
collection_files_stream = []
for f in selected_files:
    collection_files_stream.append(open(f, "rb"))
if uploaded_collection_files:
    collection_files_stream.extend(uploaded_collection_files)

with col3:
    st.markdown("### 🗂️ Restore previous Found progress (optional)")
    uploaded_locations_json = st.file_uploader("Upload locations_index.json to restore cache (optional)", type=["json"], key="upload_locations_json")
    if uploaded_locations_json:
        try:
            loaded = json.load(uploaded_locations_json)
            if isinstance(loaded, dict):
                st.session_state["locations_index"] = loaded
                st.success("locations_index restored into session_state.")
            else:
                st.error("Uploaded JSON is not a dict mapping.")
        except Exception as e:
            st.error(f"Could not read uploaded JSON: {e}")

# ---------------------------------------------------------------------
# --- Helper: sanitize CSVs
# ---------------------------------------------------------------------
def sanitize_and_validate(df, required_columns, file_label):
    df.columns = df.columns.str.strip().str.title()
    missing = [c for c in required_columns if c not in df.columns]
    if missing:
        st.error(f"❌ The file **{file_label}** is missing required columns: {', '.join(missing)}")
        st.stop()
    return df

# ---------------------------------------------------------------------
# --- Merge helper (no longer cached by streamlit only; stored in session_state)
# ---------------------------------------------------------------------
def merge_wanted_and_collection(wanted_df: pd.DataFrame, collection_df: pd.DataFrame) -> pd.DataFrame:
    merged = pd.merge(
        wanted_df,
        collection_df[["Part", "Color", "Location", "Quantity"]],
        on=["Part", "Color"],
        how="left",
        suffixes=("_wanted", "_have")
    )
    merged["Available"] = merged["Location"].notna()
    merged["Location"] = merged["Location"].fillna("❌ Not Found")
    if "Quantity_have" in merged.columns:
        merged["Quantity_have"] = merged["Quantity_have"].fillna(0).astype(int)
    elif "Quantity" in merged.columns:
        merged = merged.rename(columns={"Quantity": "Quantity_have"})
        merged["Quantity_have"] = merged["Quantity_have"].fillna(0).astype(int)
    else:
        merged["Quantity_have"] = 0
    merged = merged.sort_values(by=["Location", "Part"], ascending=[True, True])
    return merged

# ---------------------------------------------------------------------
# --- Main logic when files present ---
# ---------------------------------------------------------------------
if wanted_files and collection_files_stream:
    # Load wanted
    wanted_dfs = []
    for file in wanted_files:
        try:
            df = pd.read_csv(file)
            df = sanitize_and_validate(df, ["Part", "Color", "Quantity"], f"Wanted ({getattr(file, 'name', 'uploaded')})")
            df = df.rename(columns={"Quantity": "Quantity_wanted"})
            wanted_dfs.append(df)
        except Exception as e:
            st.error(f"Could not read wanted file: {e}")
            st.stop()
    wanted = pd.concat(wanted_dfs, ignore_index=True)

    # Load collection
    collection_dfs = []
    for file in collection_files_stream:
        try:
            if hasattr(file, "read"):
                df = pd.read_csv(file)
                label = getattr(file, "name", "uploaded_collection")
            else:
                df = pd.read_csv(file)
                label = str(file)
            df = sanitize_and_validate(df, ["Part", "Color", "Quantity", "Location"], f"Collection ({label})")
            collection_dfs.append(df)
        except Exception as e:
            st.error(f"Could not read collection file {label}: {e}")
            st.stop()
    collection = pd.concat(collection_dfs, ignore_index=True)
    st.session_state["collection_df"] = collection

    # --- Precompute & cache merged DF (store in session_state) ---
    # We create a simple hash based on the bytes of the uploaded collection(s) & wanted to detect changes
    # Serialize small canonical bytes for cache-keying
    def _df_bytes(df: pd.DataFrame) -> bytes:
        return df.to_csv(index=False).encode("utf-8")

    merged_source_hash = hashlib.md5(_df_bytes(collection) + _df_bytes(wanted)).hexdigest()
    if st.session_state.get("merged_df") is None or st.session_state.get("merged_source_hash") != merged_source_hash:
        st.session_state["merged_df"] = merge_wanted_and_collection(wanted, collection)
        st.session_state["merged_source_hash"] = merged_source_hash

    merged = st.session_state["merged_df"]

    # --- Precompute images for all locations (if not yet done for this collection) ---
    collection_bytes = _df_bytes(collection)
    # we use cached precompute_all_location_images keyed by the bytes + mapping presence
    images_index = precompute_all_location_images(collection_bytes, st.session_state.get("ba_mapping", {}))
    # store in session state for direct reuse (and to allow download)
    st.session_state["locations_index"] = images_index

    # --- UI: show collapsed locations and allow opening one at a time ---
    st.markdown("### 🧩 Parts Grouped by Location (click Open to render a location)")
    # compute basic summary per location (fast)
    loc_summary = merged.groupby("Location").agg(
        parts_count=("Part", "count"),
        total_wanted=("Quantity_wanted", "sum")
    ).reset_index().sort_values(by="Location")

    for _, loc_row in loc_summary.iterrows():
        location = loc_row["Location"]
        parts_count = loc_row["parts_count"]
        total_wanted = loc_row["total_wanted"]

        # compact header with Open / Close buttons
        header_cols = st.columns([4, 1, 1])
        header_cols[0].markdown(f"**📦 {location}**")
        # Detect whether this location is currently expanded
        is_open = st.session_state.get("expanded_loc") == location

        if header_cols[1].button("▼ Open", key=short_key("open", location)):
            st.session_state["expanded_loc"] = location
        if header_cols[2].button("▶ Close", key=short_key("close", location)):
            # only clear if we are closing the currently open one
            if st.session_state.get("expanded_loc") == location:
                st.session_state["expanded_loc"] = None

        # render only if this location is expanded
        if st.session_state.get("expanded_loc") != location:
            # show a small preview of stored images (if we have them) but do not create heavy widgets
            imgs = st.session_state["locations_index"].get(location, [])
            if imgs:
                # show up to 10 small images to give context
                st.image(imgs[:10], width=30)
            st.markdown("---")
            continue  # skip heavy rendering for collapsed locations

        # --- expanded: render full location UI (only one location at a time) ---
        st.markdown(f"#### Details for {location} — wanted {parts_count} parts")
        # Show stored images for this location
        imgs = st.session_state["locations_index"].get(location, [])
        if imgs:
            st.markdown("**Stored here (sample images):**")
            st.image(imgs[:50], width=60, caption=None)  # limited to avoid overloading UI
            st.markdown("---")

        # iterate parts in this location and render per-part number inputs (only for this location)
        loc_group = merged.loc[merged["Location"] == location]
        # group by Part (keeps same layout)
        for part_num, part_group in loc_group.groupby("Part"):
            img_url = get_part_image(part_num, st.session_state.get("ba_mapping", {}))

            left_col, right_col = st.columns([1, 4])
            with left_col:
                if img_url:
                    st.image(img_url, width=100)
                else:
                    st.text("🚫 No image")
                st.markdown(f"### **{part_num}**")

            with right_col:
                header_cols = st.columns([2.5, 1, 1, 2])
                header_cols[0].markdown("**Color**")
                header_cols[1].markdown("**Wanted**")
                header_cols[2].markdown("**Available**")
                header_cols[3].markdown("**Found**")

                for _, row in part_group.iterrows():
                    color_html = render_color_cell(row["Color"])
                    qty_wanted = int(row["Quantity_wanted"])
                    qty_have = int(row["Quantity_have"])
                    key = (str(row["Part"]), str(row["Color"]), str(row["Location"]))
                    found = st.session_state["found_counts"].get(key, 0)

                    cols = st.columns([2.5, 1, 1, 2])
                    with cols[0]:
                        st.markdown(color_html, unsafe_allow_html=True)
                    with cols[1]:
                        st.markdown(f"{qty_wanted}")
                    with cols[2]:
                        have_display = f"✅ {qty_have}" if row["Available"] else "❌"
                        st.markdown(have_display)
                    with cols[3]:
                        widget_key = short_key("found_input", row["Part"], row["Color"], row["Location"])
                        new_found = st.number_input(
                            f"Found ({row['Part']}-{row['Color']}-{location})",
                            min_value=0,
                            max_value=qty_wanted,
                            value=int(found),
                            step=1,
                            key=widget_key,
                            label_visibility="collapsed"
                        )
                        if int(new_found) != int(found):
                            st.session_state["found_counts"][key] = int(new_found)
                        complete = int(st.session_state["found_counts"].get(key, 0)) >= qty_wanted
                        found_display = (
                            f"✅ Found all ({st.session_state['found_counts'].get(key, 0)}/{qty_wanted})"
                            if complete else f"**Found:** {st.session_state['found_counts'].get(key, 0)}/{qty_wanted}"
                        )
                        st.markdown(found_display)

            st.markdown("---")

        # small utility row for this expanded location
        util_cols = st.columns([3, 1, 1])
        util_cols[0].markdown("Tip: Close this location to speed up further interactions.")
        
        if util_cols[1].button("Mark all as found (location)", key=short_key("markall", location)):
            # mark all items in this location complete (set found = wanted)
            for _, r in loc_group.iterrows():
                k = (str(r["Part"]), str(r["Color"]), str(r["Location"]))
                st.session_state["found_counts"][k] = int(r["Quantity_wanted"])
            # force a UI rerun to refresh number inputs and tick marks
            #st.rerun()
    
        if util_cols[2].button("Clear found (location)", key=short_key("clearall", location)):
            for _, r in loc_group.iterrows():
                k = (str(r["Part"]), str(r["Color"]), str(r["Location"]))
                if k in st.session_state["found_counts"]:
                    del st.session_state["found_counts"][k]
            # force a UI rerun to refresh number inputs and tick marks
            #st.rerun()
    
        st.markdown("---")

    # --- end for each location

    # Append found counts to merged for summaries (fast list lookup)
    found_map = st.session_state.get("found_counts", {})
    keys_tuples = list(zip(merged["Part"].astype(str), merged["Color"].astype(str), merged["Location"].astype(str)))
    merged["Found"] = [found_map.get(k, 0) for k in keys_tuples]
    merged["Complete"] = merged["Found"] >= merged["Quantity_wanted"]

    # Summary by location
    group_summary = (
        merged.groupby("Location")
        .agg(
            parts_count=("Part", "count"),
            found_parts=("Found", "sum"),
            total_wanted=("Quantity_wanted", "sum"),
        )
        .reset_index()
    )
    group_summary["completion_%"] = (
        (100 * group_summary["found_parts"] / group_summary["total_wanted"]).round(1)
    ).fillna(0)

    st.markdown("### 📈 Summary & Progress by Location")
    st.data_editor(
        group_summary,
        column_config={
            "completion_%": st.column_config.ProgressColumn(
                "completion_%",
                help="Percentage of parts found vs wanted",
                format="%d%%",
                min_value=0,
                max_value=100,
            ),
        },
        width='stretch',
        hide_index=True,
    )

    # Export merged csv
    csv = merged.to_csv(index=False).encode("utf-8")
    st.download_button("💾 Download merged CSV (with Found parts)", csv, "lego_wanted_with_location.csv")

    # Allow download of locations index
    st.markdown("### 🔁 Found parts progress (session state)")
    if st.button("Download locations_index as JSON"):
        st.download_button(
            "Click to download locations_index.json",
            data=json.dumps(st.session_state.get("locations_index", {}), indent=2),
            file_name="locations_index.json",
            key="download_locations_json"
        )

    # non-spammy warnings
    if st.session_state["mapping_warnings"]["missing_mappings"]:
        st.warning(f"Missing BA mapping for {len(st.session_state['mapping_warnings']['missing_mappings'])} RB parts (logged).")
    if st.session_state["mapping_warnings"]["missing_images"]:
        st.info(f"No BrickArchitect image found for {len(st.session_state['mapping_warnings']['missing_images'])} parts (logged).")

else:
    st.info("📤 Upload at least one Wanted list and one Collection list to begin.")


st.caption("Powered by BrickArchitect & Rebrickable • Made with ❤️ and Streamlit")
