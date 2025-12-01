# core/mapping.py
import streamlit as st
import pandas as pd
from io import BytesIO

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
    

def load_ba_mapping(mapping_path):
    if mapping_path.exists():
        with open(mapping_path, "rb") as f:
            st.session_state["ba_mapping"] = read_ba_mapping_from_excel_bytes(f.read())
            return st.session_state["ba_mapping"]
    else:
        st.session_state["ba_mapping"] = {}
    return {}