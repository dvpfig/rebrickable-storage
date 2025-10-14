import streamlit as st
import pandas as pd
import requests
import hashlib
import os
from pathlib import Path
from io import BytesIO
from PIL import Image
import re

st.set_page_config(page_title="LEGO Parts Finder", layout="wide")
st.title("🧱 LEGO Parts Finder with Location Highlights")

# ---------------------------------------------------------------------
# --- Directories for Cache and Resources ---
# ---------------------------------------------------------------------
CACHE_DIR = Path("cached_images")
CACHE_DIR.mkdir(exist_ok=True)

RESOURCES_DIR = Path("resources")

DEFAULT_COLLECTION_DIR = Path("collection")
DEFAULT_COLLECTION_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------
# --- File uploads and API key ---
# ---------------------------------------------------------------------
st.markdown("## 🔑 Rebrickable API (for part images)")
api_key = st.text_input("API Key (not needed for Brick Architect images)", type="password")

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
    
    local_path = CACHE_DIR / f"{part_str}.png"

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
    with st.expander("📦 Preview Collection Parts (merged)"):
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
    # --- Visual grouped display with collapsible sections ---
    # -----------------------------------------------------------------
    st.markdown("### 🧩 Parts Grouped by Location")

    if "found_counts" not in st.session_state:
        st.session_state["found_counts"] = {}

    for location, group in merged.groupby("Location"):
        with st.expander(f"📍 {location}", expanded=False):
            for idx, row in group.iterrows():
                bg = color_for_location(row["Location"])
                key = (str(row["Part"]), str(row["Color"]), str(row["Location"]))
                if key not in st.session_state["found_counts"]:
                    st.session_state["found_counts"][key] = 0

                found = st.session_state["found_counts"][key]
                qty_wanted = int(row["Quantity_wanted"])
                complete = found >= qty_wanted

                cols = st.columns([1, 1.8, 2, 1.5, 1.8, 2])  # Added column for Found parts

                # --- Part image ---
                with cols[0]:
                    img_url = get_part_image(row["Part"])
                    if img_url:
                        st.image(img_url, width=80)
                    else:
                        st.markdown("🚫 No image")

                # --- Color cell ---
                with cols[1]:
                    st.markdown(render_color_cell(row["Color"]), unsafe_allow_html=True)

                # --- Part number ---
                with cols[2]:
                    st.markdown(f"**{row['Part']}**")

                # --- Wanted quantity + location ---
                with cols[3]:
                    st.markdown(f"**Wanted:** {qty_wanted}")
                    st.markdown(
                        f"<div style='background:{bg};padding:6px;border-radius:6px;text-align:center'>"
                        f"📦 {row['Location']}</div>",
                        unsafe_allow_html=True
                    )

                # --- Availability ---
                with cols[4]:
                    if row["Available"]:
                        st.markdown(f"✅ {int(row['Quantity_have'])} available")
                    else:
                        st.markdown("❌ Not Found")

                # --- Found parts counter (+ / - buttons) ---
                with cols[5]:
                    display = f"✅ Found all ({found}/{qty_wanted})" if complete else f"**Found:** {found}/{qty_wanted}"
                    st.markdown(display)
                    col_minus, col_plus = st.columns(2)
                    with col_minus:
                        if st.button("➖", key=f"minus_{idx}"):
                            if found > 0:
                                st.session_state["found_counts"][key] -= 1
                                st.rerun()
                    with col_plus:
                        if st.button("➕", key=f"plus_{idx}"):
                            if found < qty_wanted:
                                st.session_state["found_counts"][key] += 1
                                st.rerun()

            st.divider()

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

    # --- Progress bars per location ---
    st.markdown("### 📈 Progress per Location")
    for _, row in group_summary.iterrows():
        loc = row["Location"]
        pct = row["completion_%"]
        st.markdown(f"**📍 {loc}** — {pct}% complete "
                    f"({int(row['found_parts'])}/{int(row['total_wanted'])} parts found)")
        st.progress(min(int(pct), 100))

    # --- Table with summary per location ---
    st.markdown("### 📊 Summary by Location (with Found parts)")
    st.dataframe(group_summary, use_container_width=True)

    # -----------------------------------------------------------------
    # --- Export merged CSV including Found column ---
    # -----------------------------------------------------------------
    csv = merged.to_csv(index=False).encode("utf-8")
    st.download_button("💾 Download merged CSV (with Found parts)", csv, "lego_wanted_with_location.csv")

else:
    st.info("📤 Upload at least one Wanted list and one Collection list to begin.")

st.caption("Powered by BrickArchitect & Rebricable Color DB • Made with ❤️ and Streamlit")

