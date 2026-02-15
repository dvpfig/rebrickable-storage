# core/mapping.py
import streamlit as st
import pandas as pd
from io import BytesIO
from pathlib import Path
from streamlit import cache_data

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

@st.cache_data(show_spinner=False)
def load_ba_mapping(mapping_path):
    if mapping_path.exists():
        with open(mapping_path, "rb") as f:
            return read_ba_mapping_from_excel_bytes(f.read())

    return {}

@st.cache_data(show_spinner=False)
def count_parts_in_mapping(mapping_path_str: str, collection_parts: tuple = None, count_type: str = "labels"):
    """
    Count parts in the mapping file.
    
    Args:
        mapping_path_str: String path to mapping file (for caching)
        collection_parts: Tuple of RB part numbers from collection (tuple for hashability)
        count_type: "labels" or "images"
    
    Returns:
        tuple: (total_count, collection_count)
    """
    import openpyxl
    
    mapping_path = Path(mapping_path_str)
    wb = openpyxl.load_workbook(mapping_path)
    ws = wb.active
    header_row = [cell.value for cell in ws[1]]
    
    # Find relevant columns
    if count_type == "labels":
        target_col = header_row.index("BA label URL") + 1 if "BA label URL" in header_row else None
    else:  # images
        target_col = header_row.index("BA partnum") + 1 if "BA partnum" in header_row else None
    
    # Find all RB part columns
    rb_part_cols = []
    for idx, col_name in enumerate(header_row):
        if col_name and col_name.startswith("RB part_"):
            rb_part_cols.append(idx + 1)
    
    total_count = 0
    collection_count = 0
    collection_parts_set = set(collection_parts) if collection_parts else set()
    
    if target_col:
        for row in ws.iter_rows(min_row=2):
            target_val = row[target_col - 1].value
            
            # Check if row is valid
            if count_type == "labels":
                is_valid = target_val and "No label available" not in str(target_val)
            else:  # images
                is_valid = target_val is not None
            
            if is_valid:
                total_count += 1
                
                # Check if any RB part matches collection
                if rb_part_cols and collection_parts_set:
                    for col_idx in rb_part_cols:
                        rb_partnum = str(row[col_idx - 1].value).strip() if row[col_idx - 1].value else None
                        if rb_partnum and rb_partnum in collection_parts_set:
                            collection_count += 1
                            break
    
    wb.close()
    return (total_count, collection_count)