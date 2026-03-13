# ui/layout.py
import streamlit as st
from hashlib import md5

def ensure_session_state_keys():
    # ---------------------------------------------------------------------
    # --- Session-state initialization
    # ---------------------------------------------------------------------
    if "collection_df" not in st.session_state:
        st.session_state["collection_df"] = None
    if "found_counts" not in st.session_state:
        st.session_state["found_counts"] = {}
    if "locations_index" not in st.session_state:
        st.session_state["locations_index"] = {}
#    if "ba_mapping" not in st.session_state:
#        st.session_state["ba_mapping"] = None
#    if "mapping_warnings" not in st.session_state:
#        st.session_state["mapping_warnings"] = {"missing_mappings": set(), "missing_images": set()}
    if "expanded_loc" not in st.session_state:
        st.session_state["expanded_loc"] = None
    if "merged_df" not in st.session_state:
        st.session_state["merged_df"] = None
    if "merged_source_hash" not in st.session_state:
        st.session_state["merged_source_hash"] = None
    if "start_processing" not in st.session_state:
        st.session_state["start_processing"] = False
    
    # Sets management session state
    if "sets_metadata" not in st.session_state:
        st.session_state["sets_metadata"] = None
    if "sets_inventories_cache" not in st.session_state:
        st.session_state["sets_inventories_cache"] = {}
    if "sets_data_loaded" not in st.session_state:
        st.session_state["sets_data_loaded"] = False

    # Progress management session state
    if "current_progress_filename" not in st.session_state:
        st.session_state["current_progress_filename"] = None
    if "loaded_progress_wanted_files" not in st.session_state:
        st.session_state["loaded_progress_wanted_files"] = None
    if "loaded_progress_found_counts" not in st.session_state:
        st.session_state["loaded_progress_found_counts"] = None
    if "loaded_progress_set_found_counts" not in st.session_state:
        st.session_state["loaded_progress_set_found_counts"] = None
    if "_session_restored_from_progress" not in st.session_state:
        st.session_state["_session_restored_from_progress"] = False

def short_key(*args) -> str:
    return md5("::".join(map(str, args)).encode("utf-8")).hexdigest()