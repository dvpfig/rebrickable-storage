import streamlit as st
import pandas as pd
import requests
from pathlib import Path
from io import BytesIO
import re
import json
import hashlib

# ---------------------------------------------------------------------
# --- Local Libraries
# ---------------------------------------------------------------------
from ui.theme import apply_dark_theme
from ui.layout import ensure_session_state_keys, short_key
from ui.summary import render_summary_table
from core.paths import init_paths
from core.mapping import load_ba_mapping
from core.preprocess import load_wanted_files, load_collection_files, merge_wanted_collection
from core.images import precompute_location_images, resolve_part_image
from core.colors import load_colors, build_color_lookup, render_color_cell

# ---------------------------------------------------------------------
# --- Page setup
# ---------------------------------------------------------------------
st.set_page_config(page_title="Rebrickable Storage - Parts Finder", layout="wide")

# APPLY THEME
st.session_state["theme"] = "dark-enhanced"
# Always apply dark CSS on load
st.markdown("""
    <script>
    document.documentElement.setAttribute('data-theme', 'dark-enhanced');
    </script>
""", unsafe_allow_html=True)

if st.session_state["theme"] == "dark-enhanced":
    apply_dark_theme()

# Set Title
st.title("🧱 Rebrickable Storage - Parts Finder")

# --- Base path resolution (cross-platform)
paths = init_paths()

CACHE_IMAGES_DIR = paths.cache_images
RESOURCES_DIR = paths.resources_dir
DEFAULT_COLLECTION_DIR = paths.default_collection_dir
MAPPING_PATH = paths.mapping_path
COLORS_PATH = paths.colors_path

# --- Session-state initialization
ensure_session_state_keys()

# --- Mapping file
if st.session_state["ba_mapping"] is None:
    load_ba_mapping(MAPPING_PATH)

# --- Color Lookup
colors_df = load_colors(COLORS_PATH)
color_lookup = build_color_lookup(colors_df)
#st.session_state["color_lookup_index"] = color_lookup


# ---------------------------------------------------------------------
# --- File upload section
# ---------------------------------------------------------------------
#col1, col2, col3 = st.columns(3)
col1, col2 = st.columns(2)
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

    with st.spinner("Processing Collection & Wanted parts..."):   
        
        try:
            wanted = load_wanted_files(wanted_files)
            collection = load_collection_files(collection_files_stream)
        except Exception as e:
            st.error(f"Error parsing uploaded files: {e}")
            st.stop()

        st.session_state["collection_df"] = collection
        st.write("Status: Loaded collection and wanted parts. Starting to precompute image locations.")

        def _df_bytes(df):
            return df.to_csv(index=False).encode('utf-8')
        
        merged_source_hash = hashlib.md5(_df_bytes(collection) + _df_bytes(wanted)).hexdigest()
        if st.session_state.get("merged_df") is None or st.session_state.get("merged_source_hash") != merged_source_hash:
            merged = merge_wanted_collection(wanted, collection)
            st.session_state["merged_df"] = merged
            st.session_state["merged_source_hash"] = merged_source_hash

        merged = st.session_state["merged_df"]
        
        collection_bytes = _df_bytes(collection)
        images_index = precompute_location_images(collection_bytes, st.session_state.get("ba_mapping", {}), CACHE_IMAGES_DIR)
        st.session_state["locations_index"] = images_index
        st.write("Status: Loaded image locations for parts.")
        
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
            img_url = resolve_part_image(part_num, st.session_state.get("ba_mapping", {}), CACHE_IMAGES_DIR)
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
                    color_html = render_color_cell(row["Color"], color_lookup)
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

    # Render summary table
    render_summary_table(merged)

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
