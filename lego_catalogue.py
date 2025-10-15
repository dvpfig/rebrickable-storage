import streamlit as st
import pandas as pd
import requests
import hashlib
import os
from pathlib import Path
from io import BytesIO
from PIL import Image
import re
import json

st.set_page_config(page_title="LEGO Parts Finder", layout="wide")
st.title("🧱 LEGO Parts Finder with Location Highlights")

# ---------------------------------------------------------------------
# --- Persistent configuration (last used directories)
# ---------------------------------------------------------------------
CONFIG_FILE = Path("lego_finder_config.json")

def load_config():
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_config(config):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        st.warning(f"⚠️ Could not save config: {e}")

config = load_config()

# ---------------------------------------------------------------------
# --- Sidebar: Ask user for directories
# ---------------------------------------------------------------------
st.sidebar.markdown("## 📁 Directory Settings")

# Helper function for directory selection
def choose_directory(label, default_path, config_key):
    #placeholder = st.sidebar.empty()
    if config_key not in st.session_state:
        st.session_state[config_key] = default_path

    #if placeholder.button(f"📂 Select {label}", key=f"btn_{config_key}"):
    with st.sidebar.expander(f"Select {label} folder", expanded=True):
        new_path = st.text_input(f"Enter or paste path for {label}:", value=st.session_state[config_key])
        col_ok, col_cancel = st.columns(2)
        with col_ok:
            if st.button("✅ Confirm", key=f"ok_{config_key}"):
                st.session_state[config_key] = new_path
                st.rerun()
        with col_cancel:
            if st.button("❌ Cancel", key=f"cancel_{config_key}"):
                st.rerun()

    return Path(st.session_state[config_key]).expanduser()

# Choose folders with intuitive expand
DEFAULT_COLLECTION_DIR = choose_directory(
    "Collection folder", config.get("collection_dir", "collection"), "collection_dir"
)

# Create folders
DEFAULT_COLLECTION_DIR.mkdir(parents=True, exist_ok=True)

st.sidebar.success(f"Collection folder: {DEFAULT_COLLECTION_DIR.resolve()}")

# Choose folders with intuitive expand
BASE_CACHE_DIR = choose_directory(
    "Base cache folder (images + progress)", config.get("base_cache_dir", "cache"), "base_cache_dir"
)

# Create folders
BASE_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Inside base cache: subfolders for separation
CACHE_IMAGES_DIR = BASE_CACHE_DIR / "images"
CACHE_PROGRESS_DIR = BASE_CACHE_DIR / "progress"
CACHE_IMAGES_DIR.mkdir(exist_ok=True)
CACHE_PROGRESS_DIR.mkdir(exist_ok=True)

st.sidebar.success(f"Cache folder: {BASE_CACHE_DIR.resolve()}")

# Save config if changed
if (
    config.get("collection_dir") != str(DEFAULT_COLLECTION_DIR)
    or config.get("base_cache_dir") != str(BASE_CACHE_DIR)
):
    config["collection_dir"] = str(DEFAULT_COLLECTION_DIR)
    config["base_cache_dir"] = str(BASE_CACHE_DIR)
    save_config(config)

# ---------------------------------------------------------------------
# --- Progress persistence: Load & Save found parts CSV ---
# ---------------------------------------------------------------------
progress_file = CACHE_PROGRESS_DIR / "found_progress.csv"

def load_progress():
    if progress_file.exists():
        try:
            df = pd.read_csv(progress_file)
            return {
                (str(r["Part"]), str(r["Color"]), str(r["Location"])): int(r["Found"])
                for _, r in df.iterrows()
            }
        except Exception as e:
            st.warning(f"⚠️ Could not load found parts progress: {e}")
    return {}

def save_progress(found_counts_dict):
    try:
        rows = [
            {"Part": part, "Color": color, "Location": location, "Found": found}
            for (part, color, location), found in found_counts_dict.items()
        ]
        pd.DataFrame(rows).to_csv(progress_file, index=False)
    except Exception as e:
        st.warning(f"⚠️ Could not save progress: {e}")

# Load persisted progress into session state
if "found_counts" not in st.session_state:
    st.session_state["found_counts"] = load_progress()

# Helper to update progress and persist
def update_progress(key, delta, max_value):
    found_counts = st.session_state["found_counts"]
    found = found_counts.get(key, 0)
    found = max(0, min(found + delta, max_value))
    found_counts[key] = found
    st.session_state["found_counts"] = found_counts
    save_progress(found_counts)

# ---------------------------------------------------------------------
# --- Directories for resources (colors.csv etc.)
# ---------------------------------------------------------------------
RESOURCES_DIR = Path("resources")

# ---------------------------------------------------------------------
# --- File uploads ---
# ---------------------------------------------------------------------
st.markdown("## 📂 WANTED & COLLECTION Lists")

# --- Search for CSV files in the directory ---
default_collection_files = sorted(DEFAULT_COLLECTION_DIR.glob("*.csv"))

col1, col2 = st.columns(2)

with col1:
    wanted_files = st.file_uploader(
        "Upload one or more Wanted Parts CSVs",
        type=["csv"],
        accept_multiple_files=True
    )

with col2:
    st.markdown("### 🗂️ Pre-selected Collection Files Found")
    selected_files = []
    if default_collection_files:
        for csv_file in default_collection_files:
            # Checkbox to let user include/exclude each file
            include = st.checkbox(f"Include {csv_file.name}", value=True)
            if include:
                selected_files.append(csv_file)
    else:
        st.info("No CSV files found in 'collections' folder.")

    st.markdown("### 📤 Or Upload Additional Collection CSVs")
    uploaded_collection_files = st.file_uploader(
        "Upload one or more Collection CSVs (with Location)",
        type=["csv"],
        accept_multiple_files=True
    )

# Combine pre-selected and uploaded files into one list for processing
collection_files = []
for f in selected_files:
    # Open as a file-like object to keep compatibility with uploaded files
    collection_files.append(open(f, "rb"))

if uploaded_collection_files:
    collection_files.extend(uploaded_collection_files)
    
# ---------------------------------------------------------------------
# --- Load colors.csv from Resources folder ---
# ---------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def load_colors():
    colors_path = RESOURCES_DIR / f"colors.csv"
    try:
        colors = pd.read_csv(colors_path)
        colors["name"] = colors["name"].str.strip()
        colors["rgb"] = colors["rgb"].str.strip()
        colors["is_trans"] = colors["is_trans"].astype(str).str.lower().isin(["true", "1", "yes"])
        colors["id"] = colors["id"].astype(int)
        return colors
    except Exception as e:
        st.warning(f"⚠️ Could not load colors.csv: {e}")
        return pd.DataFrame(columns=["id", "name", "rgb", "is_trans"])

colors_df = load_colors()

# Create color lookup dictionary
color_lookup = {
    int(cid): {"name": name, "rgb": rgb, "is_trans": trans}
    for cid, name, rgb, trans in zip(colors_df["id"], colors_df["name"], colors_df["rgb"], colors_df["is_trans"])
}

# ---------------------------------------------------------------------
# --- Get Part Images ---
# ---------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def get_part_image(part_num: str) -> str:
    """Return local path to cached image for a given part number.
    Downloads from BrickArchitect if not cached yet."""
    if pd.isna(part_num):
        return ""

    # Extract only the numeric prefix from part number (e.g. '32123a' -> '32123')
    match = re.match(r"(\d+)", str(part_num).strip())
    if not match:
        return ""
    part_str = match.group(1)
    
    local_path = CACHE_IMAGES_DIR / f"{part_str}.png"

    # Check if image is already cached
    if local_path.exists():
        return str(local_path)

    # Otherwise, download it
    url = f"https://brickarchitect.com/content/parts-large/{part_str}.png"
    try:
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            with open(local_path, "wb") as f:
                f.write(r.content)
            return str(local_path)
    except Exception:
        pass

    return ""  # fallback: no image

# ---------------------------------------------------------------------
# --- Helpers ---
# ---------------------------------------------------------------------

def color_for_location(location):
    if location in ["❌ Not Found", ""]:
        return "#fdd"
    h = int(hashlib.sha1(location.encode()).hexdigest(), 16) % 360
    return f"hsl({h}, 70%, 80%)"

def sanitize_and_validate(df, required_columns, file_label):
    df.columns = df.columns.str.strip().str.title()
    missing = [c for c in required_columns if c not in df.columns]
    if missing:
        st.error(f"❌ The file **{file_label}** is missing required columns: {', '.join(missing)}")
        st.stop()
    return df

def render_color_cell(color_id) -> str:
    """Return HTML representation for the color cell using color ID."""
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
# --- Main logic ---
# ---------------------------------------------------------------------
if wanted_files and collection_files:
    # Combine multiple wanted lists
    wanted_dfs = []
    for file in wanted_files:
        df = pd.read_csv(file)
        df = sanitize_and_validate(df, ["Part", "Color", "Quantity"], f"Wanted ({file.name})")
        wanted_dfs.append(df)
    wanted = pd.concat(wanted_dfs, ignore_index=True)

    # Combine multiple collection lists
    collection_dfs = []
    for file in collection_files:
        df = pd.read_csv(file)
        df = sanitize_and_validate(df, ["Part", "Color", "Quantity", "Location"], f"Collection ({file.name})")
        collection_dfs.append(df)
    collection = pd.concat(collection_dfs, ignore_index=True)

    # --- Expandable previews ---
    with st.expander("🔍 Preview Wanted Parts (merged)"):
        st.dataframe(wanted.head(30), use_container_width=True)
    with st.expander("🔍 Preview Collection Parts (merged)"):
        st.dataframe(collection.head(30), use_container_width=True)

    # --- Merge by Part + Color ---
    merged = pd.merge(
        wanted,
        collection[["Part", "Color", "Location", "Quantity"]],
        on=["Part", "Color"],
        how="left",
        suffixes=("_wanted", "_have")
    )

    merged["Available"] = merged["Location"].notna()
    merged["Location"] = merged["Location"].fillna("❌ Not Found")
    merged["Quantity_have"] = merged["Quantity_have"].fillna(0).astype(int)

    # --- Sort by Location then Part ---
    merged = merged.sort_values(by=["Location", "Part"], ascending=[True, True])

    # --- Search bar ---
    query = st.text_input("🔍 Search by part or location")
    if query:
        q = query.lower()
        merged = merged[
            merged.apply(lambda r: q in str(r["Part"]).lower()
                                  or q in str(r["Location"]).lower(), axis=1)
        ]

    # -----------------------------------------------------------------
    # --- Visual grouped display with collapsible sections (clean Streamlit style) ---
    # -----------------------------------------------------------------
    st.markdown("### 🧩 Parts Grouped by Location")

    if "found_counts" not in st.session_state:
        st.session_state["found_counts"] = {}

    for location, loc_group in merged.groupby("Location"):
        with st.expander(f"📦 {location}", expanded=False):

            for part_num, part_group in loc_group.groupby("Part"):
                img_url = get_part_image(part_num)

                # Layout: left = image + part ID, right = table of color variants
                left_col, right_col = st.columns([1, 4])

                with left_col:
                    if img_url:
                        st.image(img_url, width=100)
                    else:
                        st.markdown("🚫 No image")
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

                        if key not in st.session_state["found_counts"]:
                            st.session_state["found_counts"][key] = 0
                        found = st.session_state["found_counts"][key]
                        complete = found >= qty_wanted
                        check = "✅" if complete else ""

                        have_display = f"✅ {qty_have}" if row["Available"] else "❌"
                        found_display = f"✅ Found all ({found}/{qty_wanted})" if complete else f"**Found:** {found}/{qty_wanted}"

                        cols = st.columns([2.5, 1, 1, 2])
                        with cols[0]:
                            st.markdown(color_html, unsafe_allow_html=True)
                        with cols[1]:
                            st.markdown(f"{qty_wanted}")
                        with cols[2]:
                            st.markdown(have_display)
                        with cols[3]:
                            
                            st.markdown(found_display, help="Found so far")
                            bcols = st.columns([1, 1, 4])
                            with bcols[0]:
                                if st.button("➖", key=f"minus_btn_{location}_{part_num}_{row['Color']}", use_container_width=True):
                                    update_progress(key, -1, qty_wanted)
                                    st.rerun()
                            with bcols[1]:
                                if st.button("➕", key=f"plus_btn_{location}_{part_num}_{row['Color']}", use_container_width=True):
                                    update_progress(key, +1, qty_wanted)
                                    st.rerun()

                st.markdown("---")

    # -----------------------------------------------------------------
    # --- Append found counts to merged DataFrame ---
    # -----------------------------------------------------------------
    def get_found_value(row):
        key = (str(row["Part"]), str(row["Color"]), str(row["Location"]))
        return st.session_state["found_counts"].get(key, 0)

    merged["Found"] = merged.apply(get_found_value, axis=1)
    merged["Complete"] = merged["Found"] >= merged["Quantity_wanted"]

    # -----------------------------------------------------------------
    # --- Summary by location including found ---
    # -----------------------------------------------------------------
    group_summary = (
        merged.groupby("Location")
        .agg(
            parts_count=("Part", "count"),
            found_parts=("Found", "sum"),
            total_wanted=("Quantity_wanted", "sum")
        )
        .reset_index()
    )

    group_summary["completion_%"] = (
        100 * group_summary["found_parts"] / group_summary["total_wanted"]
    ).round(1)

    # -----------------------------------------------------------------
    # --- Display the summary table per location with progress bars ---
    # -----------------------------------------------------------------
    st.markdown("### 📈 Summary & Progress by Location")
    
    #st.dataframe(group_summary, use_container_width=True)
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
            "total_wanted": st.column_config.NumberColumn("total_wanted", min_value=0),
            "found_parts": st.column_config.NumberColumn("found_parts", min_value=0),
        },
        use_container_width=True,
        hide_index=True,
    )
    
    # -----------------------------------------------------------------
    # --- Export merged CSV including Found column ---
    # -----------------------------------------------------------------
    csv = merged.to_csv(index=False).encode("utf-8")
    st.download_button("💾 Download merged CSV (with Found parts)", csv, "lego_wanted_with_location.csv")

else:
    st.info("📤 Upload at least one Wanted list and one Collection list to begin.")

st.caption("Powered by BrickArchitect & Rebricable Color DB • Made with ❤️ and Streamlit")

