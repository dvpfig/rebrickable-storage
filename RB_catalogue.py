# FULL UPDATED SCRIPT WITH THEME TOGGLE + START BUTTON

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
# THEME TOGGLE (DARK / LIGHT modes)
# ---------------------------------------------------------------------
st.session_state["theme"] = "dark-enhanced"

if st.session_state["theme"] == "dark-enhanced":
    st.markdown("""
        <style>

        /* ---- Global Colors ---- */
        body, .stApp {
            background-color: #121212 !important;
            color: #E6E6E6 !important;
            font-family: "Inter", "Roboto", sans-serif;
        }

        /* ---- Main Containers ---- */
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        
        /* Panel / Widget backgrounds */
        .stMarkdown, .stText, .stColumn, div[data-testid="column"] {
            color: #E6E6E6 !important;
        }

        /* ---- Cards (dataframes, expanders, info boxes) ---- */
        .stDataFrame, div[data-testid="stDataFrame"], .st-cq {
            background-color: #1A1A1A !important;
            border-radius: 10px !important;
            border: 1px solid #2E2E2E !important;
            color: #E6E6E6 !important;
        }

        /* Improve dataframe text contrast */
        table, td, th {
            color: #E6E6E6 !important;
            border-color: #333333 !important;
        }

        /* ---- Buttons ---- */
        .stButton>button {
            background-color: #2B7FFF !important; /* LEGO blue */
            color: #FFFFFF !important;
            border-radius: 10px !important;
            border: none !important;
            padding: 0.55rem 1.2rem !important;
            font-weight: 600 !important;
            transition: 0.15s ease-in-out;
        }
        .stButton>button:hover {
            background-color: #1F5FCC !important;
            transform: translateY(-2px);
            box-shadow: 0 4px 10px rgba(0,0,0,0.4);
        }

        /* ---- Toggle label ---- */
        label[data-testid="stWidgetLabel"] {
            color: #E6E6E6 !important;
            font-weight: 600 !important;
        }

        /* ---- Number inputs, text boxes ---- */
        input, textarea, select, .stTextInput>div>div>input {
            background-color: #1C1C1C !important;
            color: #F1F1F1 !important;
            border-radius: 8px !important;
            border: 1px solid #333333 !important;
        }

        /* Fix for component icons */
        svg {
            filter: brightness(0.85) !important;
        }

        /* ---- Progress bars ---- */
        .stProgress > div > div > div > div {
            background-color: #2B7FFF !important;
        }

        /* ---- Expander ---- */
        details {
            background-color: #1A1A1A !important;
            color: #E6E6E6 !important;
            border-radius: 10px !important;
            border: 1px solid #2E2E2E !important;
            padding: 0.6rem;
            margin-bottom: 1rem;
        }

        /* ---- Separator lines ---- */
        hr {
            border: 0;
            border-top: 1px solid #333333 !important;
        }

        /* ---- Small previews / images ---- */
        img {
            border-radius: 6px !important;
            background-color: #1A1A1A;
        }

        /* ---- Tooltips ---- */
        div[data-testid="stTooltip"] {
            background-color: #2E2E2E !important;
            color: #FFFFFF !important;
            border: 1px solid #444444 !important;
        }

        </style>
    """, unsafe_allow_html=True)

# ---- UNIVERSAL UI ENHANCEMENTS FOR LOCATION LISTS ----
st.markdown("""
<style>

    /* Location block container */
    .location-card {
        background-color: rgb(38, 39, 48);
        padding: 0.5rem;
        border-radius: 12px;
        margin-bottom: 0.5rem;
    }

    /* Row with title and action buttons */
    .location-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 0.6rem;
    }

    /* Title text */
    .location-title {
        font-size: 1.35rem;
        font-weight: 700;
        margin: 0;
    }

    /* Small inline buttons */
    .loc-btn-small > button {
        padding: 0.25rem 0.55rem !important;
        font-size: 0.75rem !important;
        border-radius: 6px !important;
        margin-left: 4px !important;
    }

    .loc-btn-row {
        display: flex;
        gap: 6px;
        margin-bottom: 0.6rem;
    }

    /* Ultra-subtle thin separator */
    .location-separator {
        height: 1px !important;
        width: 100% !important;
        background-color: var(--divider-color, #C7CBD1);
        margin: 4px 0 10px 0 !important;
        opacity: 0.35 !important;
        padding: 0 !important;
    }

    
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------
# --- Base path resolution (cross-platform)
# ---------------------------------------------------------------------
try:
    ROOT_DIR = Path(__file__).resolve().parent
except NameError:
    ROOT_DIR = Path(os.getcwd()).resolve()

GLOBAL_CACHE_DIR = ROOT_DIR / "cache"
CACHE_IMAGES_DIR = GLOBAL_CACHE_DIR / "images"
RESOURCES_DIR = ROOT_DIR / "resources"
DEFAULT_COLLECTION_DIR = ROOT_DIR / "collection"

MAPPING_PATH = RESOURCES_DIR / "part number - BA vs RB - filled.xlsx"
COLORS_PATH = RESOURCES_DIR / "colors.csv"

for d in [GLOBAL_CACHE_DIR, CACHE_IMAGES_DIR, RESOURCES_DIR, DEFAULT_COLLECTION_DIR]:
    d.mkdir(parents=True, exist_ok=True)

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
    st.session_state["found_counts"] = {}
if "locations_index" not in st.session_state:
    st.session_state["locations_index"] = {}
if "ba_mapping" not in st.session_state:
    st.session_state["ba_mapping"] = None
if "mapping_warnings" not in st.session_state:
    st.session_state["mapping_warnings"] = {"missing_mappings": set(), "missing_images": set()}
if "expanded_loc" not in st.session_state:
    st.session_state["expanded_loc"] = None
if "merged_df" not in st.session_state:
    st.session_state["merged_df"] = None
if "merged_source_hash" not in st.session_state:
    st.session_state["merged_source_hash"] = None
if "start_processing" not in st.session_state:
    st.session_state["start_processing"] = False

# ---------------------------------------------------------------------
# --- Helpers
# ---------------------------------------------------------------------
def short_key(*args) -> str:
    return hashlib.md5("::".join(map(str, args)).encode("utf-8")).hexdigest()

@st.cache_data(show_spinner=False)
def read_ba_mapping_from_excel_bytes(excel_bytes: bytes) -> dict:
    try:
        df = pd.read_excel(BytesIO(excel_bytes))
    except Exception:
        return {}
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

# Load mapping file
if st.session_state["ba_mapping"] is None:
    if MAPPING_PATH.exists():
        with open(MAPPING_PATH, "rb") as f:
            st.session_state["ba_mapping"] = read_ba_mapping_from_excel_bytes(f.read())
    else:
        st.session_state["ba_mapping"] = {}

@st.cache_data(show_spinner=False)
def fetch_image_bytes(url: str) -> bytes | None:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
        "Referer": url.rsplit('/', 1)[0],
    }
    try:
        r = requests.get(url, headers=headers, timeout=6)
        if r.status_code == 200 and r.content:
            return r.content
    except:
        return None
    return None

@st.cache_data(show_spinner=False)
def get_part_image_cached(identifier: str) -> str:
    if not identifier:
        return ""
    local_png = CACHE_IMAGES_DIR / f"{identifier}.png"
    if local_png.exists():
        return str(local_png)
    local_jpg = CACHE_IMAGES_DIR / f"{identifier}.jpg"
    if local_jpg.exists():
        return str(local_jpg)
    url = f"https://brickarchitect.com/content/parts-large/{identifier}.png"
    data = fetch_image_bytes(url)
    if data:
        with open(local_png, "wb") as f:
            f.write(data)
        return str(local_png)
    return ""

def get_part_image(part_num: str, ba_mapping: dict) -> str:
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
            st.session_state["mapping_warnings"]["missing_mappings"].add(cleaned)
    candidates.append(cleaned)
    for cid in candidates:
        p = get_part_image_cached(cid)
        if p:
            return p
    st.session_state["mapping_warnings"]["missing_images"].add(part_original)
    return ""

@st.cache_data(show_spinner=False)
def precompute_all_location_images(collection_df_serialized: bytes, ba_mapping: dict) -> dict:
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

# Load colors
@st.cache_data(show_spinner=False)
def load_colors():
    try:
        colors = pd.read_csv(COLORS_PATH)
        colors["name"] = colors["name"].str.strip()
        colors["rgb"] = colors["rgb"].str.strip()
        colors["is_trans"] = colors["is_trans"].astype(str).str.lower().isin(["true", "1", "yes"])
        colors["id"] = colors["id"].astype(int)
        return colors
    except:
        return pd.DataFrame(columns=["id", "name", "rgb", "is_trans"])

colors_df = load_colors()
color_lookup = {
    int(cid): {"name": name, "rgb": rgb, "is_trans": trans}
    for cid, name, rgb, trans in zip(colors_df.get("id", []), colors_df.get("name", []), colors_df.get("rgb", []), colors_df.get("is_trans", []))
}

def render_color_cell(color_id) -> str:
    try:
        cid = int(color_id)
    except:
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
        f"<div style='width:24px;height:24px;border-radius:4px;border:1px solid #999; background-color:#{rgb};'></div>"
        f"<div><b>{name}</b><br><span style='font-size:0.8em;color:#666'>{label}</span></div>"
        f"</div>"
    )

# ---------------------------------------------------------------------
# --- File upload section
# ---------------------------------------------------------------------
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("### 🗂️ Wanted parts: Upload")
    wanted_files = st.file_uploader("Upload Wanted CSVs", type=["csv"], accept_multiple_files=True)

with col2:
    st.markdown("### 🗂️ Collection: Pre-selected Files")
    default_collection_files = sorted(DEFAULT_COLLECTION_DIR.glob("*.csv"))
    selected_files = []
    if default_collection_files:
        for csv_file in default_collection_files:
            include = st.checkbox(f"Include {csv_file.name}", value=True, key=f"inc_{csv_file.name}")
            if include:
                selected_files.append(csv_file)
    uploaded_collection_files = st.file_uploader("Upload Collection CSVs", type=["csv"], accept_multiple_files=True)

collection_files_stream = []
for f in selected_files:
    collection_files_stream.append(open(f, "rb"))
if uploaded_collection_files:
    collection_files_stream.extend(uploaded_collection_files)

## TEMPORARY SKIP PROGRESS RESTORE
#with col3:
#    st.markdown("### 🗂️ Restore previous found progress")
#    uploaded_locations_json = st.file_uploader("Upload locations_index.json", type=["json"], key="upload_locations_json")
#    if uploaded_locations_json:
#        try:
#            loaded = json.load(uploaded_locations_json)
#            if isinstance(loaded, dict):
#                st.session_state["locations_index"] = loaded
#                st.success("locations_index restored.")
#        except Exception as e:
#            st.error(f"Could not read JSON: {e}")

# ---------------------------------------------------------------------
# --- Start Processing Button
# ---------------------------------------------------------------------
if wanted_files and collection_files_stream:
    st.markdown("### ▶️ Ready to process")
    if st.button("🚀 Start generating pickup list"):
        st.session_state["start_processing"] = True
else:
    st.info("📤 Upload at least one Wanted and one Collection file to begin.")
    st.session_state["start_processing"] = False

# ---------------------------------------------------------------------
# --- MAIN PROCESSING LOGIC
# ---------------------------------------------------------------------
if st.session_state.get("start_processing"):

    def sanitize_and_validate(df, required, label):
        df.columns = df.columns.str.strip().str.title()
        missing = [c for c in required if c not in df.columns]
        if missing:
            st.error(f"❌ File {label} missing required columns: {', '.join(missing)}")
            st.stop()
        return df

    # Load wanted
    wanted_dfs = []
    for file in wanted_files:
        df = pd.read_csv(file)
        df = sanitize_and_validate(df, ["Part", "Color", "Quantity"], file.name)
        df = df.rename(columns={"Quantity": "Quantity_wanted"})
        wanted_dfs.append(df)
    wanted = pd.concat(wanted_dfs, ignore_index=True)

    # Load collection
    collection_dfs = []
    for file in collection_files_stream:
        if hasattr(file, "read"):
            df = pd.read_csv(file)
            label = getattr(file, "name", "uploaded")
        else:
            df = pd.read_csv(file)
            label = str(file)
        df = sanitize_and_validate(df, ["Part", "Color", "Quantity", "Location"], label)
        collection_dfs.append(df)
    collection = pd.concat(collection_dfs, ignore_index=True)

    st.session_state["collection_df"] = collection

    def _df_bytes(df):
        return df.to_csv(index=False).encode('utf-8')

    merged_source_hash = hashlib.md5(_df_bytes(collection) + _df_bytes(wanted)).hexdigest()
    if st.session_state.get("merged_df") is None or st.session_state.get("merged_source_hash") != merged_source_hash:
        merged = pd.merge(
            wanted,
            collection[["Part", "Color", "Location", "Quantity"]],
            on=["Part", "Color"],
            how="left",
            suffixes=("_wanted", "_have")
        )
        merged["Available"] = merged["Location"].notna()
        merged["Location"] = merged["Location"].fillna("❌ Not Found")
        merged["Quantity_have"] = merged.get("Quantity_have", merged.get("Quantity", 0)).fillna(0).astype(int)
        merged = merged.sort_values(by=["Location", "Part"])
        st.session_state["merged_df"] = merged
        st.session_state["merged_source_hash"] = merged_source_hash

    merged = st.session_state["merged_df"]

    collection_bytes = _df_bytes(collection)
    images_index = precompute_all_location_images(collection_bytes, st.session_state.get("ba_mapping", {}))
    st.session_state["locations_index"] = images_index

    st.markdown("### 🧩 Parts Grouped by Location")

    loc_summary = merged.groupby("Location").agg(parts_count=("Part", "count"), total_wanted=("Quantity_wanted", "sum")).reset_index()
    loc_summary = loc_summary.sort_values("Location")

    for _, loc_row in loc_summary.iterrows():
        location = loc_row["Location"]
        parts_count = loc_row["parts_count"]
        total_wanted = loc_row["total_wanted"]

        # CARD START - Location Header
        st.markdown('<div class="location-card">', unsafe_allow_html=True)

        st.markdown(f"""
        <div class="location-header">
            <div class="location-title">📦 {location}</div>
            <div class="loc-btn-row">
        """, unsafe_allow_html=True)

        colA, colB = st.columns([1, 1])

        with colA:
            if st.button("Open ▼", key=short_key("open", location), help="Show this location", use_container_width=False):
                st.session_state["expanded_loc"] = location

        with colB:
            if st.button("Close ▶", key=short_key("close", location), help="Hide this location", use_container_width=False):
                if st.session_state.get("expanded_loc") == location:
                    st.session_state["expanded_loc"] = None

        st.markdown("</div></div>", unsafe_allow_html=True)  # end header
        # CARD END

        if st.session_state.get("expanded_loc") != location:
            imgs = st.session_state["locations_index"].get(location, [])
            if imgs:
                st.image(imgs[:10], width=30)
            #st.markdown("---")
            continue

        st.markdown(f"#### Details for {location}")

        imgs = st.session_state["locations_index"].get(location, [])
        if imgs:
            st.markdown("**Stored here (sample images):**")
            st.image(imgs[:50], width=60)
            st.markdown("---")

        loc_group = merged.loc[merged["Location"] == location]

        for part_num, part_group in loc_group.groupby("Part"):
            img_url = get_part_image(part_num, st.session_state.get("ba_mapping", {}))
            left, right = st.columns([1, 4])
            with left:
                if img_url:
                    st.image(img_url, width=100)
                else:
                    st.text("🚫 No image")
                st.markdown(f"### **{part_num}**")
            with right:
                header = st.columns([2.5, 1, 1, 2])
                header[0].markdown("**Color**")
                header[1].markdown("**Wanted**")
                header[2].markdown("**Available**")
                header[3].markdown("**Found**")

                for _, row in part_group.iterrows():
                    color_html = render_color_cell(row["Color"])
                    qty_wanted = int(row["Quantity_wanted"])
                    qty_have = int(row["Quantity_have"])
                    key = (str(row["Part"]), str(row["Color"]), str(row["Location"]))
                    found = st.session_state["found_counts"].get(key, 0)

                    cols = st.columns([2.5, 1, 1, 2])
                    cols[0].markdown(color_html, unsafe_allow_html=True)
                    cols[1].markdown(f"{qty_wanted}")
                    cols[2].markdown(f"✅ {qty_have}" if row["Available"] else "❌")

                    widget_key = short_key("found_input", row["Part"], row["Color"], row["Location"])
                    new_found = cols[3].number_input(
                        " ", min_value=0, max_value=qty_wanted, value=int(found), step=1,
                        key=widget_key, label_visibility="collapsed"
                    )
                    if int(new_found) != int(found):
                        st.session_state["found_counts"][key] = int(new_found)

                    complete = st.session_state["found_counts"].get(key, 0) >= qty_wanted
                    cols[3].markdown(
                        f"✅ Found all ({st.session_state['found_counts'].get(key, 0)}/{qty_wanted})"
                        if complete 
                        else f"**Found:** {st.session_state['found_counts'].get(key, 0)}/{qty_wanted}"
                    )

            st.markdown("---")

        # CARD START - Buttons "Found all" / "Clear all"            
        st.markdown('<div class="loc-btn-row">', unsafe_allow_html=True)
        colM, colC = st.columns([1, 1])
        with colM:
            if st.button("Mark all found ✔", key=short_key("markall", location), help="Fill all items for this location"):
                for _, r in loc_group.iterrows():
                    k = (str(r["Part"]), str(r["Color"]), str(r["Location"]))
                    st.session_state["found_counts"][k] = int(r["Quantity_wanted"])
        with colC:
            if st.button("Clear found ✖", key=short_key("clearall", location), help="Clear found counts for this location"):
                for _, r in loc_group.iterrows():
                    k = (str(r["Part"]), str(r["Color"]), str(r["Location"]))
                    st.session_state["found_counts"].pop(k, None)

        st.markdown("</div>", unsafe_allow_html=True)
        # CARD END
        
        #st.markdown("---")

    found_map = st.session_state.get("found_counts", {})
    keys_tuples = list(zip(merged["Part"].astype(str), merged["Color"].astype(str), merged["Location"].astype(str)))
    merged["Found"] = [found_map.get(k, 0) for k in keys_tuples]
    merged["Complete"] = merged["Found"] >= merged["Quantity_wanted"]

    summary = merged.groupby("Location").agg(
        parts_count=("Part", "count"),
        found_parts=("Found", "sum"),
        total_wanted=("Quantity_wanted", "sum"),
    ).reset_index()
    summary["completion_%"] = (100 * summary["found_parts"] / summary["total_wanted"]).round(1).fillna(0)

    st.markdown("### 📈 Summary & Progress by Location")
    st.data_editor(
        summary,
        column_config={
            "completion_%": st.column_config.ProgressColumn(
                "completion_%", format="%d%%", min_value=0, max_value=100
            )
        },
        hide_index=True,
        width='stretch'
    )

    csv = merged.to_csv(index=False).encode("utf-8")
    st.download_button("💾 Download merged CSV", csv, "lego_wanted_with_location.csv")

## TEMPORARY SKIP PROGRESS RESTORE
#    if st.button("Download locations_index as JSON"):
#        st.download_button(
#            "Click to download locations_index.json",
#            json.dumps(st.session_state.get("locations_index", {}), indent=2),
#            "locations_index.json",
#            key="download_locations_json"
#        )

    if st.session_state["mapping_warnings"]["missing_mappings"]:
        st.warning(f"Missing BA mapping for {len(st.session_state['mapping_warnings']['missing_mappings'])} parts.")
    if st.session_state["mapping_warnings"]["missing_images"]:
        st.info(f"No BrickArchitect image found for {len(st.session_state['mapping_warnings']['missing_images'])} parts.")

st.caption("Powered by BrickArchitect & Rebrickable • Made with ❤️ and Streamlit")
