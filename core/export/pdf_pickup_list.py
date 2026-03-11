"""
PDF Pickup List Generator

Generates a printable PDF checklist of wanted parts grouped by storage location,
mirroring the pickup list view from the web application.
"""

import unicodedata
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional
from fpdf import FPDF

# Unicode fraction/symbol replacements for Latin-1 safe output
_UNICODE_REPLACEMENTS = {
    "\u2153": "1/3", "\u2154": "2/3", "\u00bc": "1/4", "\u00be": "3/4",
    "\u00bd": "1/2", "\u215b": "1/8", "\u215c": "3/8", "\u215d": "5/8",
    "\u215e": "7/8", "\u2155": "1/5", "\u2156": "2/5", "\u2157": "3/5",
    "\u2158": "4/5", "\u2159": "1/6", "\u215a": "5/6", "\u2150": "1/7",
    "\u2151": "1/9", "\u2152": "1/10",
    "\u2013": "-", "\u2014": "-", "\u2018": "'", "\u2019": "'",
    "\u201c": '"', "\u201d": '"', "\u2026": "...", "\u2022": "*",
    "\u00d7": "x",
}


def _sanitize_text(text: str) -> str:
    """Replace Unicode characters unsupported by Latin-1 built-in fonts."""
    for char, replacement in _UNICODE_REPLACEMENTS.items():
        text = text.replace(char, replacement)
    result = []
    for ch in text:
        try:
            ch.encode("latin-1")
            result.append(ch)
        except UnicodeEncodeError:
            decomposed = unicodedata.normalize("NFKD", ch)
            ascii_approx = decomposed.encode("latin-1", errors="ignore").decode("latin-1")
            result.append(ascii_approx if ascii_approx else "?")
    return "".join(result)


class PickupListPDF(FPDF):
    """Custom PDF class for the pickup list with header/footer."""

    def __init__(self, title: str = "LEGO Parts Pickup List"):
        super().__init__(orientation="P", unit="mm", format="A4")
        self._doc_title = title
        self.set_auto_page_break(auto=True, margin=20)

    def header(self):
        self.set_font("Helvetica", "B", 14)
        self.cell(0, 8, self._doc_title, new_x="LMARGIN", new_y="NEXT", align="C")
        self.ln(2)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")


def _hex_to_rgb(hex_str: str):
    """Convert hex color string to (r, g, b) tuple."""
    hex_str = hex_str.lstrip("#")
    if len(hex_str) != 6:
        return (128, 128, 128)
    return tuple(int(hex_str[i:i + 2], 16) for i in (0, 2, 4))


def _safe_image_path(part_num: str, part_images_map: Dict) -> Optional[str]:
    """Get a valid local image path for a part, or None."""
    img_path = part_images_map.get(str(part_num), "")
    if img_path and Path(img_path).is_file():
        return str(img_path)
    return None


# Layout constants (mm)
COL_IMAGE = 18
COL_PART = 38       # wider for part name text
COL_COLOR_SWATCH = 8
COL_COLOR_NAME = 42
COL_WANTED = 16
COL_AVAILABLE = 20
COL_CHECK = 26      # wider check column for manual writing
ROW_HEIGHT = 8
IMG_SIZE = 7
LOCATION_IMG_SIZE = 8
LOCATION_IMG_GAP = 1
TABLE_WIDTH = COL_IMAGE + COL_PART + COL_COLOR_SWATCH + COL_COLOR_NAME + COL_WANTED + COL_AVAILABLE + COL_CHECK


def _draw_table_header(pdf: FPDF):
    """Draw the table header row."""
    pdf.set_font("Helvetica", "B", 6)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(COL_IMAGE, 5, "Image", border=1, fill=True, align="C")
    pdf.cell(COL_PART, 5, "Part", border=1, fill=True, align="C")
    pdf.cell(COL_COLOR_SWATCH + COL_COLOR_NAME, 5, "Color", border=1, fill=True, align="C")
    pdf.cell(COL_WANTED, 5, "Wanted", border=1, fill=True, align="C")
    pdf.cell(COL_AVAILABLE, 5, "Available", border=1, fill=True, align="C")
    pdf.cell(COL_CHECK, 5, "Check", border=1, fill=True, align="C")
    pdf.ln()


def _draw_location_images(pdf: FPDF, location_imgs: List[str]):
    """Draw a row of small part images for a location (stored-here preview)."""
    if not location_imgs:
        return
    x_start = pdf.get_x()
    y_row_top = pdf.get_y()
    x = x_start
    max_per_row = int(TABLE_WIDTH / (LOCATION_IMG_SIZE + LOCATION_IMG_GAP))
    count = 0
    y_last_row = y_row_top
    for img_path in location_imgs[:60]:
        if not Path(img_path).is_file():
            continue
        if count > 0 and count % max_per_row == 0:
            x = x_start
            y_last_row += LOCATION_IMG_SIZE + LOCATION_IMG_GAP
            if y_last_row > 270:
                break
        try:
            pdf.image(img_path, x=x, y=y_last_row, w=LOCATION_IMG_SIZE, h=LOCATION_IMG_SIZE)
        except Exception:
            pass
        x += LOCATION_IMG_SIZE + LOCATION_IMG_GAP
        count += 1
    # Position cursor just below the last row of images
    if count > 0:
        pdf.set_y(y_last_row + LOCATION_IMG_SIZE + 1)
    else:
        pdf.set_y(y_row_top + 1)


def _draw_part_rows(
    pdf: FPDF, part_num: str, part_group: pd.DataFrame,
    color_lookup: Dict, part_images_map: Dict, ba_part_names: Dict,
    location: str,
):
    """
    Draw rows for a single part, grouping multiple colors under one part image/name.
    The part image + name spans multiple color rows if needed.
    Row height adapts when replacement text is present.
    """
    color_rows = list(part_group.iterrows())
    num_colors = len(color_rows)

    # Determine part text lines to calculate required height
    ba_name = _sanitize_text(ba_part_names.get(part_num, ""))
    replacement = ""
    if "Replacement_parts" in part_group.columns:
        rp = part_group["Replacement_parts"].iloc[0]
        if rp and str(rp).strip():
            replacement = _sanitize_text(f"(replace with {rp})")

    # Build text lines: (style, font_size, line_height, text)
    text_lines = [("B", 7, 5.5, part_num)]
    if ba_name:
        text_lines.append(("", 5.5, 4, ba_name))
    if replacement:
        text_lines.append(("I", 5, 3.5, replacement))

    total_text_h = sum(lh for _, _, lh, _ in text_lines) + 2  # 2mm padding
    min_part_height = max(total_text_h, IMG_SIZE + 2)
    # Each color row is at least ROW_HEIGHT, but part cell must fit text
    color_row_h = ROW_HEIGHT
    part_block_height = max(color_row_h * num_colors, min_part_height)
    # If part text needs more space, increase each color row proportionally
    if part_block_height > color_row_h * num_colors:
        color_row_h = part_block_height / num_colors

    # Check page break
    if pdf.get_y() + part_block_height > 265:
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_fill_color(220, 220, 220)
        pdf.cell(0, 5, _sanitize_text(f"{location} (continued)"),
                 new_x="LMARGIN", new_y="NEXT", fill=True)
        pdf.ln(1)
        _draw_table_header(pdf)

    y_block_start = pdf.get_y()
    x_start = pdf.get_x()

    # --- Part image cell (spans all color rows) ---
    img_path = _safe_image_path(part_num, part_images_map)
    if img_path:
        try:
            img_x = x_start + (COL_IMAGE - IMG_SIZE) / 2
            img_y = y_block_start + (part_block_height - IMG_SIZE) / 2
            pdf.image(img_path, x=img_x, y=img_y, w=IMG_SIZE, h=IMG_SIZE)
        except Exception:
            pass
    pdf.set_xy(x_start, y_block_start)
    pdf.cell(COL_IMAGE, part_block_height, "", border=1)

    # --- Part number + name cell (spans all color rows) ---
    pdf.set_xy(x_start + COL_IMAGE, y_block_start)
    pdf.cell(COL_PART, part_block_height, "", border=1)

    # Draw text inside the part cell, vertically centered
    text_x = x_start + COL_IMAGE + 1
    text_y = y_block_start + (part_block_height - total_text_h + 2) / 2

    for style, size, lh, text in text_lines:
        pdf.set_font("Helvetica", style, size)
        pdf.set_xy(text_x, text_y)
        pdf.cell(COL_PART - 2, lh, text, align="C")
        text_y += lh

    # --- Color rows ---
    pdf.set_font("Helvetica", "", 7)
    for i, (_, row) in enumerate(color_rows):
        y_row = y_block_start + i * color_row_h
        color_x = x_start + COL_IMAGE + COL_PART

        color_id = row["Color"]
        qty_wanted = int(row["Quantity_wanted"])
        qty_have = int(row["Quantity_have"])
        qty_similar = int(row.get("Quantity_similar", 0))

        try:
            cid = int(color_id)
            color_info = color_lookup.get(cid, {})
            color_name = color_info.get("name", str(color_id))
            color_rgb = color_info.get("rgb", "808080")
            is_trans = color_info.get("is_trans", False)
        except (ValueError, TypeError):
            color_name = str(color_id)
            color_rgb = "808080"
            is_trans = False

        # Color swatch
        r, g, b = _hex_to_rgb(color_rgb)
        pdf.set_fill_color(r, g, b)
        swatch_y = y_row + (color_row_h - 5) / 2
        pdf.rect(color_x + 1, swatch_y, 5, 5, style="FD")
        pdf.set_fill_color(255, 255, 255)

        # Color swatch border cell
        pdf.set_xy(color_x, y_row)
        pdf.cell(COL_COLOR_SWATCH, color_row_h, "",
                 border="LTB" if i == num_colors - 1 else "LT")

        # Color name
        pdf.set_xy(color_x + COL_COLOR_SWATCH, y_row)
        trans_prefix = "(T) " if is_trans else ""
        pdf.set_font("Helvetica", "", 7)
        border_right = "TRB" if i == num_colors - 1 else "TR"
        pdf.cell(COL_COLOR_NAME, color_row_h,
                 _sanitize_text(f"{trans_prefix}{color_name}"), border=border_right, align="L")

        # Wanted
        wanted_x = color_x + COL_COLOR_SWATCH + COL_COLOR_NAME
        pdf.set_xy(wanted_x, y_row)
        pdf.cell(COL_WANTED, color_row_h, str(qty_wanted), border=1, align="C")

        # Available
        avail_x = wanted_x + COL_WANTED
        if qty_similar > 0:
            avail_str = f"{qty_have}+{qty_similar}"
        else:
            avail_str = str(qty_have)
        pdf.set_xy(avail_x, y_row)
        pdf.cell(COL_AVAILABLE, color_row_h, avail_str, border=1, align="C")

        # Check (empty for manual writing)
        check_x = avail_x + COL_AVAILABLE
        pdf.set_xy(check_x, y_row)
        pdf.cell(COL_CHECK, color_row_h, "", border=1, align="C")

    # Move cursor to after the part block
    pdf.set_xy(x_start, y_block_start + part_block_height)


def generate_pickup_list_pdf(
    merged_df: pd.DataFrame,
    color_lookup: Dict,
    part_images_map: Dict,
    found_counts: Dict = None,
    ba_part_names: Dict = None,
    second_loc_by_location: Dict = None,
    locations_index: Dict = None,
    wanted_file_names: List[str] = None,
    collection_file_names: List[str] = None,
) -> bytes:
    """
    Generate a PDF pickup list with parts grouped by location.

    Args:
        merged_df: Merged DataFrame with Part, Color, Location,
                   Quantity_wanted, Quantity_have, Available, etc.
        color_lookup: Dict mapping color_id -> {name, rgb, is_trans}
        part_images_map: Dict mapping part_num -> local image file path
        found_counts: Dict {(part, color, location): found_count} (unused, kept for API compat)
        ba_part_names: Dict mapping part_num -> BA part name
        second_loc_by_location: Dict {location: [rows]} for second-location parts
        locations_index: Dict {location: [image_paths]} for stored-here preview
        wanted_file_names: List of wanted CSV file names
        collection_file_names: List of collection CSV file names

    Returns:
        bytes: PDF file content
    """
    if ba_part_names is None:
        ba_part_names = {}
    if second_loc_by_location is None:
        second_loc_by_location = {}
    if locations_index is None:
        locations_index = {}

    pdf = PickupListPDF()
    pdf.alias_nb_pages()
    pdf.add_page()

    # --- Source files info at the top ---
    if wanted_file_names:
        pdf.set_font("Helvetica", "B", 8)
        pdf.cell(0, 5, "Wanted files:", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 8)
        for fname in wanted_file_names:
            pdf.cell(0, 4, f"  - {_sanitize_text(fname)}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)

    # Build location summary
    loc_summary = merged_df.groupby("Location").agg(
        parts_count=("Part", "count"),
        total_wanted=("Quantity_wanted", "sum"),
    ).reset_index()

    existing_locations = set(loc_summary["Location"].values)
    for sl_location in second_loc_by_location:
        if sl_location not in existing_locations:
            new_row = pd.DataFrame([{
                "Location": sl_location, "parts_count": 0, "total_wanted": 0
            }])
            loc_summary = pd.concat([loc_summary, new_row], ignore_index=True)

    loc_summary = loc_summary.sort_values("Location")

    for _, loc_row in loc_summary.iterrows():
        location = loc_row["Location"]
        parts_count = int(loc_row["parts_count"])
        total_wanted = int(loc_row["total_wanted"])

        loc_group = merged_df.loc[merged_df["Location"] == location]
        second_loc_count = len(second_loc_by_location.get(location, []))

        # --- Location header ---
        if pdf.get_y() > 240:
            pdf.add_page()

        pdf.set_font("Helvetica", "B", 10)
        pdf.set_fill_color(220, 220, 220)

        if parts_count == 0 and second_loc_count > 0:
            status = f"{second_loc_count} part(s) from other locations"
        else:
            status = f"{parts_count} part(s), {total_wanted} total wanted"

        pdf.cell(0, 6, _sanitize_text(f"{location}  --  {status}"),
                 new_x="LMARGIN", new_y="NEXT", fill=True)
        pdf.ln(1)

        # --- Location images (stored-here preview) ---
        loc_imgs = locations_index.get(location, [])
        _draw_location_images(pdf, loc_imgs)

        # --- Parts table ---
        if not loc_group.empty:
            _draw_table_header(pdf)
            pdf.set_font("Helvetica", "", 7)

            # Group by Part to show each part once with multiple color rows
            for part_num, part_group in loc_group.groupby("Part", sort=False):
                _draw_part_rows(
                    pdf, str(part_num), part_group,
                    color_lookup, part_images_map, ba_part_names,
                    str(location),
                )

        # --- Second location parts ---
        second_loc_rows = second_loc_by_location.get(location, [])
        if second_loc_rows:
            if pdf.get_y() > 260:
                pdf.add_page()
            pdf.set_font("Helvetica", "I", 7)
            pdf.cell(0, 5,
                     f"Also check here (from other locations): {len(second_loc_rows)} part(s)",
                     new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 7)
            for sl_row in second_loc_rows:
                if pdf.get_y() > 270:
                    pdf.add_page()
                sl_part = str(sl_row["Part"])
                try:
                    cid = int(sl_row["Color"])
                    c_info = color_lookup.get(cid, {})
                    c_name = c_info.get("name", str(sl_row["Color"]))
                except (ValueError, TypeError):
                    c_name = str(sl_row["Color"])
                qty = int(sl_row.get("Quantity_wanted", 0))
                primary_loc = str(sl_row.get("Location", ""))
                pdf.cell(0, 5, _sanitize_text(
                    f"  {sl_part} - {c_name} (qty: {qty}, primary: {primary_loc})"
                ), new_x="LMARGIN", new_y="NEXT")

        pdf.ln(2)

    return bytes(pdf.output())
