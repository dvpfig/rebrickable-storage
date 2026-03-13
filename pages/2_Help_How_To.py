"""
Help / How To page - Step-by-step instructions for using the application.

Provides a comprehensive guide organized by the three main pages:
- My Collection Parts
- My Collection Sets
- Find Wanted Parts
"""

import streamlit as st

# Page configuration
st.title("📖 Help / How To")
st.sidebar.header("📖 Help / How To")

# CSS to offset anchor targets below the fixed Streamlit top navbar
st.markdown("""
<style>
/* Anchor offset so headings are visible when jumping via TOC links */
[id] {
    scroll-margin-top: 80px;
}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------
# --- Sidebar Table of Contents
# --- Anchors must match Streamlit's auto-generated heading IDs:
# ---   lowercase, emoji stripped, spaces/special chars become hyphens
# ---------------------------------------------------------------------
with st.sidebar:
    st.markdown("---")
    st.markdown("### 📑 Table of Contents")

    st.markdown("""
- [🗺️ Quick Reference — Typical Workflow](#quick-reference-typical-workflow)

---

**🏷️ My Collection - Parts**
- [📤 Upload Parts CSV](#upload-parts-csv)
- [📂 Manage Collection Files](#manage-collection-files)
- [🔄 BrickArchitect Sync](#brick-architect-sync)
- [🧩 Custom RB↔BA Mapping](#custom-rb-ba-mapping-rules)
- [🖼️ Precompute Collection Images](#precompute-collection-images)
- [🏷️ Generate Labels by Location](#generate-labels-by-location)
- [🖼️ Custom Images Management](#custom-images-management)
- [🔑 Rebrickable API Key](#rebrickable-api-key)
- [🎨 Colors Database](#colors-database)

---

**📦 My Collection - Sets**
- [📤 Upload Sets CSV](#upload-sets-csv)
- [✏️ Add Set Manually](#add-set-manually)
- [🔄 Retrieve Inventories](#retrieve-inventories)
- [📋 View Sets Collection](#view-sets-collection)
- [🔑 API Key Configuration](#api-key-configuration)

---

**🔍 Find Wanted Parts**
- [🗂️ Upload Wanted Parts](#upload-wanted-parts)
- [🗂️ Select Collection Files](#select-collection-files)
- [▶️ Search Alternatives (A/B)](#search-alternatives-a-b)
- [🚀 Precompute & Generate](#precompute-and-generate-pickup-list)
- [📦 Browse Locations](#browse-locations)
- [✅ Mark Parts as Found](#mark-parts-as-found)
- [🎨 Color Alternatives](#color-alternatives)
- [📥 Export Results & PDF](#export-results-and-pdf-pickup-list)
- [🔎 Search in Owned Sets](#search-in-owned-sets)
- [💾 Save & Load Progress](#save-and-load-progress)
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------
# --- Main Content
# ---------------------------------------------------------------------

st.markdown("""
This guide walks you through every feature of the application, organized by page. 
Use the sidebar table of contents to jump directly to the section you need.
""")

st.markdown("---")

# =====================================================================
# QUICK REFERENCE — TYPICAL WORKFLOW (moved to top)
# =====================================================================
st.markdown("## 🗺️ Quick Reference — Typical Workflow")

st.markdown("""
Here's the recommended sequence for a first-time user:

| Step | Page | Action |
|------|------|--------|
| 1 | Welcome | Log in or register |
| 2 | My Collection - Parts | Upload your collection CSV files |
| 3 | My Collection - Parts | Run BrickArchitect Sync (Step 1 + Step 2) to create the mapping file |
| 4 | My Collection - Parts | Download BA labels and images |
| 5 | My Collection - Parts | Precompute collection images |
| 6 | My Collection - Sets | Upload sets CSV or add sets manually |
| 7 | My Collection - Sets | Configure Rebrickable API key |
| 8 | My Collection - Sets | Retrieve set inventories |
| 9 | Find Wanted Parts | Upload wanted parts CSV |
| 10 | Find Wanted Parts | Select collection files and precompute images |
| 11 | Find Wanted Parts | Generate pickup list |
| 12 | Find Wanted Parts | Browse locations and mark parts as found |
| 13 | Find Wanted Parts | Export PDF pickup list for offline use |
| 14 | Find Wanted Parts | Search owned sets for missing parts |
| 15 | Find Wanted Parts | Save progress |
""")

st.markdown("---")

# =====================================================================
# MY COLLECTION - PARTS
# =====================================================================
st.markdown("## 🏷️ My Collection — Parts")
st.markdown("""
This page is your hub for managing loose LEGO parts. Here you upload your collection CSV files, 
sync data from BrickArchitect, generate printable labels, and manage part images.
""")

st.markdown("---")

# --- Upload Parts CSV ---
st.markdown("### 📤 Upload Parts CSV")
st.markdown("""
Upload CSV files exported from [Rebrickable](https://rebrickable.com/) containing your loose parts collection.

**Expected CSV columns:**
| Column | Description | Example |
|--------|-------------|---------|
| Part | Part number | `3001` |
| Color | Rebrickable color ID | `4` (Red) |
| Quantity | Number of parts | `12` |
| Location | Storage location | `Box A`, `Drawer 3` |

**Steps:**
1. Navigate to **My Collection - Parts** page
2. In the **"📤 Upload Parts CSV"** section (left column), click **Browse files**
3. Select one or more `.csv` files from your computer
4. Files are automatically validated and saved to your collection

Files are stored per-user, so each user has their own collection.
""")

st.markdown("---")

# --- Manage Collection Files ---
st.markdown("### 📂 Manage Collection Files")
st.markdown("""
After uploading, your files appear in the **"Current Parts Collection files"** section (right column).

**Available actions:**
- **View** the list of uploaded CSV files
- **Delete** individual files you no longer need via the **📂 Manage Collection Files** expander
- Files persist across sessions — they're saved to your user directory

These collection files are used by the label generator and the Find Wanted Parts page.
""")

st.markdown("---")

# --- BrickArchitect Sync ---
st.markdown("### 🔄 Brick Architect Sync")
st.markdown("""
This section lets you download and cache data from BrickArchitect. It has two main areas side by side:
""")

col_help1, col_help2 = st.columns(2)

with col_help1:
    st.markdown("""
    **📥 Get latest Labels/Images** (left)
    
    Download label files (.lbx) and part images (.png) from BrickArchitect.
    
    - Choose **download mode**: only parts in your collection, or all available parts
    - Click **"📥 Get latest BA labels"** to download label files
    - Click **"📥 Get latest BA images"** to download part images
    - A **Stop** button appears during download if you need to cancel
    - Files are cached locally — only new files are downloaded on subsequent runs
    - Cache statistics show how many labels and images are already cached
    """)

with col_help2:
    st.markdown("""
    **🔄 Sync latest Parts from BrickArchitect** (right)
    
    Build and update the part number mapping database (BA ↔ RB).
    
    This is a **two-step process**:
    1. **Step 1:** Click **"📋 Get full list of BA parts"** — scrapes BrickArchitect to create an Excel mapping file
    2. **Step 2:** Click **"🔗 Get BA mappings for parts"** — enriches the Excel file with Rebrickable part number mappings
    
    Both steps are **resumable** — if interrupted, they continue from where they left off.
    The mapping file is required for labels, images, and part matching to work.
    """)

st.warning("⚠️ If you see a warning about missing mapping file, run the sync steps above first. This is required before labels, images, and part matching features will work.")

st.markdown("---")

# --- Custom RB-BA Mapping ---
st.markdown("### 🧩 Custom RB↔BA Mapping Rules")
st.markdown("""
The application uses a two-tier mapping system to convert Rebrickable (RB) part numbers to BrickArchitect (BA) part numbers:

1. **Excel File Mapping** (Primary) — from the BrickArchitect sync
2. **Custom Mapping CSV** (Secondary) — your own rules with wildcard support

**Wildcard patterns:**
| Pattern | Meaning | Example |
|---------|---------|---------|
| `*` | Any single digit (0-9) | `3001*` matches `30011`, `30012`, etc. |
| `**` | Any sequence of digits | `3626?pr**` matches `3626apr01`, `3626bpr9999` |
| `?` | Any single letter (a-z) | `970?**` matches `970c01`, `970a123` |

**How to use:**
- Expand the **"🧩 Custom RB→BA Mapping Rules"** section
- **Download** the current mapping CSV for backup
- **Upload** a replacement CSV file
- **Edit** mappings directly in the inline table editor (supports up to 4 RB patterns per BA part)
- Click **"💾 Save Custom Mappings"** to apply changes
- Click **"🔄 Reset to Defaults"** to restore the default mapping rules

**Mapping priority:** Base Excel file → Custom CSV wildcards → Leading digits match → Original RB part number
""")

st.markdown("---")

# --- Precompute Collection Images ---
st.markdown("### 🖼️ Precompute Collection Images")
st.markdown("""
Downloads and caches images for all parts in your collection files. This ensures images are ready 
when you browse locations in the Find Wanted Parts page.

**Steps:**
1. Make sure you have at least one collection CSV uploaded
2. Click **"🔄 Precompute collection images"**
3. A progress bar shows the download status
4. After completion, you'll see statistics:
   - How many images were found/downloaded
   - Parts confirmed unavailable (no image exists anywhere)
   - Parts not yet checked in Rebrickable (click **"🔍 Get RB img"** to try fetching individually)
   - Parts without a location assigned

**Image sources (in order):**
1. BrickArchitect cache (local)
2. User-uploaded custom images
3. Rebrickable API (requires API key)

Click **"🔄 Recompute images"** to re-run after uploading new custom images or after API rate limits reset.
Click **"🔓 Reset unavailable list"** to retry parts previously marked as unavailable.
""")

st.markdown("---")

# --- Generate Labels ---
st.markdown("### 🏷️ Generate Labels by Location")
st.markdown("""
Creates a downloadable ZIP file with printable label files organized by storage location.

**Steps:**
1. Make sure you have collection CSV files uploaded
2. Choose the **output mode**:
   - **Both individual and merged files** — one label per part plus a merged label per location
   - **Merged files only** — one combined label file per location (saves paper)
3. Click **"📦 Generate Labels Zip File"**
4. A progress bar tracks the generation
5. Click **"⬇️ Download Labels Zip File"** to save the ZIP

Labels are generated from cached `.lbx` files (downloaded via BrickArchitect Sync). 
Parts from LEGO sets are excluded — only loose parts get labels.
""")

st.markdown("---")

# --- Custom Images ---
st.markdown("### 🖼️ Custom Images Management")
st.markdown("""
Found in the **sidebar** under **"🖼️ Custom Images"**. Use this when no official image exists for a part.

**Features:**
- **View count** of your uploaded custom images
- **Download** all custom images as a ZIP backup
- **Upload** new custom images (PNG or JPG) — name the file with the part number (e.g., `3001.png`)
- **Delete all** custom images to start fresh

Custom images take priority over BrickArchitect images when displaying parts.
""")

st.markdown("---")

# --- Rebrickable API Key ---
st.markdown("### 🔑 Rebrickable API Key")
st.markdown("""
Found in the **sidebar** under **"🔑 Rebrickable API Key"**. Required for fetching part images 
from Rebrickable and retrieving set inventories.

**How to get your key:**
1. Go to [rebrickable.com/api](https://rebrickable.com/api/)
2. Create a free account if you don't have one
3. Generate an API key from your profile settings
4. Paste it in the sidebar input and click **"💾 Save API Key"**

The key is validated before saving. Each user stores their own key.
""")

st.markdown("---")

# --- Colors Database ---
st.markdown("### 🎨 Colors Database")
st.markdown("""
Found in the **sidebar** under **"🎨 Rebrickable Colors Database"**.

The LEGO colors database (`colors.csv`) is auto-downloaded from Rebrickable on first run. 
You can manually update it by clicking **"🔄 Download latest colors from Rebrickable"**.

This database is used for:
- Color name display throughout the app
- Color swatches in the pickup list
- Color similarity calculations for alternative suggestions
""")

st.markdown("---")

# =====================================================================
# MY COLLECTION - SETS
# =====================================================================
st.markdown("## 📦 My Collection — Sets")
st.markdown("""
This page lets you manage your LEGO set collection. Track which sets you own, 
retrieve their part inventories from Rebrickable, and enable set-based part searching.
""")

st.markdown("---")

# --- Upload Sets CSV ---
st.markdown("### 📤 Upload Sets CSV")
st.markdown("""
Upload a CSV file exported from Rebrickable containing your set collection.

**Expected CSV columns:**
| Column | Description | Example |
|--------|-------------|---------|
| Set number | LEGO set number | `31147-1` |
| Quantity | Number owned | `1` |
| Includes spares | Include spare parts | `true` |
| Inventory ver | Rebrickable inventory version | `1` |

**Steps:**
1. Navigate to **My Collection - Sets** page
2. In the **"📤 Upload Sets CSV"** section (left column), click **Browse files**
3. Select your `.csv` file
4. Click **"📥 Import Sets"** to add them to your collection
5. Duplicate sets are automatically detected and skipped
""")

st.markdown("---")

# --- Add Set Manually ---
st.markdown("### ✏️ Add Set Manually")
st.markdown("""
Add individual sets by typing their set number.

**Steps:**
1. In the **"✏️ Add Set Manually"** section (right column), enter a set number (e.g., `31147-1`)
2. Click **"➕ Add Set"**
3. The set is added to your collection
4. Remember to retrieve inventories afterward to enable part searching
""")

st.markdown("---")

# --- Retrieve Inventories ---
st.markdown("### 🔄 Retrieve Inventories")
st.markdown("""
Fetches the part list for each set from the Rebrickable API. This is required before you can 
search for wanted parts in your sets.

**Prerequisites:**
- At least one set in your collection
- A valid Rebrickable API key configured (sidebar)

**Steps:**
1. The section shows metrics: Total Sets, Fetched, and Pending
2. Click **"🔄 Retrieve Inventories"** to fetch all pending sets
3. A progress bar tracks the retrieval
4. After completion, a summary shows successful, skipped, and failed counts
5. If any fail (e.g., rate limiting), try again after a few moments

Once inventories are fetched, you can search for wanted parts within these sets on the 
**Find Wanted Parts** page.
""")

st.markdown("---")

# --- View Sets Collection ---
st.markdown("### 📋 View Sets Collection")
st.markdown("""
Your sets are displayed at the bottom of the page, grouped by source (CSV filename or "Manual Entry").

**For each set you can see:**
- Set number and name
- Quantity owned
- Part count (after inventory is fetched)
- Inventory status (Fetched / Pending)

**Management actions:**
- **🗑️ Delete** individual sets (with confirmation)
- **🗑️ Delete Group** to remove all sets from a source CSV (with confirmation)
""")

st.markdown("---")

# --- Sets API Key ---
st.markdown("### 🔑 API Key Configuration")
st.markdown("""
The Rebrickable API key can also be configured from this page's sidebar, under **"🔑 Rebrickable API Key"**.

This is the same key used across the application — setting it on any page makes it available everywhere.
See the [Rebrickable API Key](#rebrickable-api-key) section above for setup instructions.
""")

st.markdown("---")

# =====================================================================
# FIND WANTED PARTS
# =====================================================================
st.markdown("## 🔍 Find Wanted Parts")
st.markdown("""
This is the main workflow page. Upload the parts you need (from a set you want to build), 
match them against your collection and/or owned sets, and track your progress as you collect them.
""")

st.markdown("---")

# --- Upload Wanted Parts ---
st.markdown("### 🗂️ Upload Wanted Parts")
st.markdown("""
Upload CSV files with the parts you need for a build.

**Expected CSV columns:**
| Column | Description | Example |
|--------|-------------|---------|
| Part | Part number | `3001` |
| Color | Rebrickable color ID | `4` |
| Quantity | Number needed | `2` |

**How to get this file:**
1. Go to [rebrickable.com](https://rebrickable.com/)
2. Find the set you want to build
3. Go to its parts list and export as CSV

**Steps:**
1. In the **"🗂️ Wanted parts: Upload"** section (left column), click **Browse files**
2. Select one or more `.csv` files
3. The app shows how many unique part/color combinations were found
""")

st.markdown("---")

# --- Select Collection Files ---
st.markdown("### 🗂️ Select Collection Files")
st.markdown("""
Choose which collection files to search through.

**Steps:**
1. In the **"🗂️ Collection (Parts): Select Files"** section (right column), expand **"📁 Available files"**
2. Check/uncheck individual collection CSV files to include or exclude them
3. Optionally upload additional collection CSVs directly here

All checked files are combined when generating the pickup list.
""")

st.markdown("---")

# --- Search Alternatives ---
st.markdown("### ▶️ Search Alternatives (A / B)")
st.markdown("""
Choose how you want to search for wanted parts:

**Alternative A: Parts collection first, then sets** (recommended)
1. Searches your loose parts collection first
2. Shows a pickup list grouped by storage location
3. After reviewing, you can optionally search owned sets for any missing parts

**Alternative B: Search in owned sets only**
1. Skips the loose parts collection entirely
2. Searches directly in your owned set inventories
3. Shows which sets contain the wanted parts

Select your preferred mode using the radio buttons, then proceed with the steps below.
""")

st.markdown("---")

# --- Precompute and Generate ---
st.markdown("### 🚀 Precompute and Generate Pickup List")
st.markdown("""
For **Alternative A**, the workflow has two steps:

**Step 1: Precompute collection images**
1. Click **"🔄 Precompute collection images"**
2. This downloads and caches images for all parts in your selected collection files
3. Wait for the progress bar to complete

**Step 2: Generate pickup list**
1. After precompute is done, click **"🚀 Generate pickup list"**
2. The app merges your wanted parts with the collection
3. Parts are matched by part number and color
4. Results are grouped by storage location

If a **matching saved progress** is found (same wanted CSV files), you'll be asked whether to 
load the saved progress or start fresh.
""")

st.markdown("---")

# --- Browse Locations ---
st.markdown("### 📦 Browse Locations")
st.markdown("""
After generating the pickup list, parts are displayed grouped by storage location.

**Each location card shows:**
- Location name and status (parts count, or "✅ All parts found")
- Click the **location button** to expand/collapse it

**Inside an expanded location:**
- **Sample images** of parts stored at that location
- **Part details** for each wanted part found here:
  - Part number and name
  - Part image (from BrickArchitect, Rebrickable, or custom upload)
  - Color swatch and color name
  - Quantities: wanted, available, similar parts, and found count
  - For printed/patterned parts: option to view the Rebrickable image alongside
- **Second location parts** — parts that have this as an alternate storage location
- **Location actions** — Mark All Found / Clear All for the entire location
""")

st.markdown("---")

# --- Mark Parts Found ---
st.markdown("### ✅ Mark Parts as Found")
st.markdown("""
As you physically collect parts, mark them as found in the app.

**Per-part tracking:**
- Each part row shows a **found counter** — use the increment/decrement buttons to adjust
- The counter tracks how many of the wanted quantity you've collected

**Per-location bulk actions:**
- **Mark All Found** — marks all parts in that location as fully collected
- **Clear All** — resets all found counts for that location to zero

Found counts are stored in your session and can be saved to a progress file for later.
""")

st.markdown("---")

# --- Color Alternatives ---
st.markdown("### 🎨 Color Alternatives")
st.markdown("""
When an exact color match isn't available, the app can suggest similar colors.

**How it works:**
- Inside each expanded location, a **color similarity slider** appears
- Adjust the slider to set the maximum color distance (how different a color can be)
- Parts with similar colors in your collection are shown as alternatives
- This helps when you have a part in a slightly different shade

The similarity is calculated using the CIE Lab color space for perceptually accurate matching.
""")

st.markdown("---")

# --- Export Results ---
st.markdown("### 📥 Export Results and PDF Pickup List")
st.markdown("""
After generating the pickup list, you have several export options:

**Download merged CSV:**
- Click **"💾 Download merged CSV"** to get the full merged data as a CSV file
- Contains all wanted parts with their locations, quantities, and found status

**Generate PDF Pickup List:**
1. Click **"📄 Generate PDF Pickup List"**
2. The PDF is generated with:
   - Parts grouped by storage location
   - Part images and color swatches
   - Quantity columns (wanted, available, found)
   - Check boxes for manual tracking while collecting
   - Source file names in the header
3. Click **"⬇️ Download PDF Pickup List"** to save it

**Export missing parts:**
- A separate export for parts that are still missing (not found in collection)
- Useful for creating a shopping list or searching in sets

The PDF is ideal for **offline collecting** — print it and take it to your storage area.
""")

st.markdown("---")

# --- Set Search ---
st.markdown("### 🔎 Search in Owned Sets")
st.markdown("""
After reviewing the pickup list from your loose parts collection, you can search your owned sets 
for any remaining missing parts.

**For Alternative A (Parts → Sets):**
1. Scroll down past the location cards to the **set search section**
2. Select which sets to include in the search
3. Click **"🔍 Search in selected sets"**
4. Results show which sets contain the missing parts, with quantities

**For Alternative B (Sets only):**
1. The set search runs directly after uploading wanted parts
2. Select sets and click search
3. Results show all matches found in your set inventories
4. Parts not found in any set are listed separately

**Set search results show:**
- Set name and number
- Part image, color, and quantities
- Found counter per set (track which set you're taking parts from)
- Parts not found in any set
""")

st.markdown("---")

# --- Progress Management ---
st.markdown("### 💾 Save and Load Progress")
st.markdown("""
The sidebar on the Find Wanted Parts page has a **Progress Management** section.

**Saving progress:**
1. When a pickup list is active, a **progress name** input appears in the sidebar
2. Enter a name (or keep the auto-generated one)
3. Click **"💾 Save Progress"**
4. Your found counts, set found counts, and the full pickup list are saved

**Loading progress:**
1. Expand **"📂 Saved Progress"** in the sidebar
2. Each saved progress shows its name and last updated time
3. Click **📂** (load) to restore that progress — the full pickup list is restored without needing to re-upload files
4. Click **✏️** (rename) to change the name
5. Click **🗑️** (delete) to remove it (with confirmation)

**Auto-detection:**
- When you generate a new pickup list, the app checks if any saved progress matches the same wanted CSV files
- If a match is found, you're asked whether to load the saved progress or start fresh

Progress files are stored per-user and persist across sessions.
""")

st.markdown("---")
st.caption("📖 This guide covers all features available in the application. For questions or issues, check the [GitHub repository](https://github.com/dvpfig/rebrickable-storage).")
