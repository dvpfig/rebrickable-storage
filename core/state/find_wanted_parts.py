"""
Helper functions for Find Wanted Parts page.

This module contains reusable functions for set search integration
that can be imported and tested independently.
"""

import pandas as pd
from typing import List, Tuple, Dict


def get_unfound_parts(merged_df: pd.DataFrame, color_lookup: Dict = None) -> List[Tuple[str, str]]:
    """
    Extract parts that are not found or have insufficient quantities.
    
    This function identifies parts from the merged dataframe that either:
    - Are not available in the collection (Available = False)
    - Have insufficient quantity (Quantity_have + Quantity_similar < Quantity_wanted)
    
    Args:
        merged_df: Merged dataframe containing wanted parts and collection matches
        color_lookup: Optional dictionary mapping color IDs to color info (with 'name' key)
        
    Returns:
        List of (part_number, color_name) tuples for parts that need to be found.
        Color is returned as color name (string) for API compatibility.
        
    Requirements: 7.2, 7.8
    """
    unfound_parts = []
    
    for _, row in merged_df.iterrows():
        qty_wanted = int(row.get("Quantity_wanted", 0))
        qty_have = int(row.get("Quantity_have", 0))
        qty_similar = int(row.get("Quantity_similar", 0))
        available = row.get("Available", False)
        
        # Check if part is not found or has insufficient quantity (including similar parts)
        total_available = qty_have + qty_similar
        if not available or total_available < qty_wanted:
            part_num = str(row["Part"])
            color_id = row["Color"]
            
            # Convert color ID to color name if color_lookup is provided
            if color_lookup is not None:
                try:
                    color_id_int = int(color_id)
                    color_info = color_lookup.get(color_id_int, {})
                    color_name = color_info.get("name", str(color_id))
                except (ValueError, TypeError):
                    # If conversion fails, use the value as-is
                    color_name = str(color_id)
            else:
                # No lookup provided, use color ID as string
                color_name = str(color_id)
            
            unfound_parts.append((part_num, color_name))
    
    # Remove duplicates while preserving order
    seen = set()
    unique_unfound = []
    for part in unfound_parts:
        if part not in seen:
            seen.add(part)
            unique_unfound.append(part)
    
    return unique_unfound


def merge_set_results(original_df: pd.DataFrame, set_results: Dict) -> pd.DataFrame:
    """
    Merge set search results into the original dataframe.
    
    This function combines set-based part locations with the original pickup list
    while preserving all original results. Set locations are added as new rows
    with the format "Set {set_number} - {set_name}".
    
    Args:
        original_df: Original merged dataframe from pickup list generation
        set_results: Dictionary mapping (part_num, color_name) to list of set locations
                    Each location is a dict with keys: set_number, set_name, quantity
        
    Returns:
        Updated dataframe with set-based locations added as new rows
        
    Requirements: 7.2, 7.8, 8.1, 8.2, 8.3
    """
    # Create a copy to avoid modifying the original
    result_df = original_df.copy()
    
    # Collect new rows for set-based locations
    new_rows = []
    
    for (part_num, color_name), locations in set_results.items():
        # Find the original row for this part/color combination
        # Color field contains color names (strings like "White", "Black")
        matching_rows = original_df[
            (original_df["Part"].astype(str) == str(part_num)) & 
            (original_df["Color"].astype(str) == str(color_name))
        ]
        
        if matching_rows.empty:
            continue
        
        # Use the first matching row as a template
        template_row = matching_rows.iloc[0].to_dict()
        
        # Create a new row for each set location
        for location_info in locations:
            new_row = template_row.copy()
            
            # Update location-specific fields
            set_number = location_info.get("set_number", "")
            set_name = location_info.get("set_name", "")
            quantity = location_info.get("quantity", 0)
            
            # Format location as "Set {set_number} - {set_name}" (Requirement 8.1)
            new_row["Location"] = f"Set {set_number} - {set_name}"
            # Show quantity available in each set (Requirement 8.2)
            new_row["Quantity_have"] = quantity
            new_row["Available"] = True
            
            # Reset found counts for set-based locations
            if "Found" in new_row:
                new_row["Found"] = 0
            if "Complete" in new_row:
                new_row["Complete"] = False
            
            new_rows.append(new_row)
    
    # Append new rows to the result dataframe (Requirement 8.3 - maintain separation)
    if new_rows:
        new_rows_df = pd.DataFrame(new_rows)
        result_df = pd.concat([result_df, new_rows_df], ignore_index=True)
    
    return result_df


def render_missing_parts_by_set(set_results: Dict, merged_df: pd.DataFrame,
                                part_images_map: Dict, ba_part_names: Dict,
                                color_lookup: Dict) -> None:
    """
    Render missing parts grouped by set, with color/missing/available/found columns
    matching the location-based layout.
    """
    import streamlit as st
    from core.data.colors import render_color_cell
    from core.infrastructure.session import short_key

    if not set_results:
        return

    st.markdown("---")
    st.markdown("### 📦 Missing Parts Found in Owned Sets")
    st.markdown("Parts from your wanted list that can be found in your owned sets:")

    # Build reverse color lookup: color_name -> color_id
    color_name_to_id = {}
    for color_id, color_info in color_lookup.items():
        color_name = color_info.get("name", "")
        if color_name:
            color_name_to_id[color_name] = color_id

    # Initialize set_found_counts in session state
    if "set_found_counts" not in st.session_state:
        st.session_state["set_found_counts"] = {}

    # Reorganize results by set
    sets_dict = {}
    for (part_num, color_name), locations in set_results.items():
        for location_info in locations:
            set_number = location_info["set_number"]
            set_name = location_info["set_name"]
            set_key = f"{set_number} - {set_name}"

            if set_key not in sets_dict:
                sets_dict[set_key] = []

            color_id = color_name_to_id.get(color_name)

            # Find wanted and have quantities from merged_df
            qty_wanted = 0
            qty_have = 0
            if color_id is not None:
                matching_rows = merged_df[
                    (merged_df["Part"].astype(str) == str(part_num)) &
                    (merged_df["Color"].astype(str) == str(color_id))
                ]
                if not matching_rows.empty:
                    qty_wanted = int(matching_rows.iloc[0].get("Quantity_wanted", 0))
                    qty_have = int(matching_rows.iloc[0].get("Quantity_have", 0))

            qty_missing = max(0, qty_wanted - qty_have)

            sets_dict[set_key].append({
                "part_num": part_num,
                "color_name": color_name,
                "color_id": color_id,
                "quantity": location_info["quantity"],
                "qty_missing": qty_missing,
                "is_spare": location_info.get("is_spare", False)
            })

    # Display each set with its parts (layout matching location cards)
    for set_key, parts_list in sorted(sets_dict.items()):
        with st.expander(f"📦 {set_key} ({len(parts_list)} part type(s))", expanded=True):
            for part_info in parts_list:
                part_num = part_info["part_num"]
                color_name = part_info["color_name"]
                color_id = part_info["color_id"]
                quantity = part_info["quantity"]
                qty_missing = part_info["qty_missing"]
                is_spare = part_info["is_spare"]

                img_url = part_images_map.get(str(part_num), "")
                ba_name = ba_part_names.get(str(part_num), "")

                left, right = st.columns([1, 4])

                with left:
                    st.markdown(f"##### **{part_num}**")
                    if ba_name:
                        st.markdown(f"{ba_name}")
                    if img_url:
                        st.image(img_url, width=100)
                    else:
                        st.text("🚫 No image")

                with right:
                    # Header row matching location card style
                    header = st.columns([2.5, 1, 1, 2])
                    header[0].markdown("**Color**")
                    header[1].markdown("**Missing**")
                    header[2].markdown("**Available**")
                    header[3].markdown("**Found**")

                    # Color cell
                    if color_id is not None:
                        color_html = render_color_cell(color_id, color_lookup)
                    else:
                        color_html = f"<span>{color_name}</span>"

                    # Available display with status indicator
                    available_in_set = min(quantity, qty_missing)
                    if available_in_set >= qty_missing:
                        available_display = f"✅ {available_in_set}"
                    else:
                        available_display = f"⚠️ {available_in_set}"

                    if is_spare:
                        available_display += " *(spare)*"

                    # Found input
                    found_key = (part_num, color_name, set_key)
                    current_found = st.session_state.get("set_found_counts", {}).get(found_key, 0)
                    max_found = min(quantity, qty_missing)

                    cols = st.columns([2.5, 1, 1, 2])
                    cols[0].markdown(color_html, unsafe_allow_html=True)
                    cols[1].markdown(f"{qty_missing}")
                    cols[2].markdown(available_display)

                    widget_key = short_key("set_found", part_num, color_name, set_key)
                    new_found = cols[3].number_input(
                        " ", min_value=0, max_value=max(max_found, 1), value=int(current_found), step=1,
                        key=widget_key, label_visibility="collapsed"
                    )
                    if int(new_found) != int(current_found):
                        if "set_found_counts" not in st.session_state:
                            st.session_state["set_found_counts"] = {}
                        st.session_state["set_found_counts"][found_key] = int(new_found)

                    complete = new_found >= qty_missing
                    cols[3].markdown(
                        f"✅ Found all ({new_found}/{qty_missing})"
                        if complete
                        else f"**Found:** {new_found}/{qty_missing}"
                    )

                st.markdown("---")



def render_set_search_section(merged_df: pd.DataFrame, sets_manager, color_lookup: Dict) -> None:
    """
    Render set search interface for parts not found or insufficient.
    
    This function displays a UI section that allows users to search for wanted parts
    within their owned LEGO sets. It only appears when there are parts that are not
    found or have insufficient quantities in the loose parts collection.
    
    The interface includes:
    - "Include Owned Sets" button to trigger the set selection interface
    - Set selection checkboxes grouped by source CSV
    - "Search Selected Sets" button to execute the search
    - Results display with set-based locations
    
    Args:
        merged_df: Merged dataframe containing wanted parts and collection matches
        sets_manager: SetsManager instance for accessing set data
        color_lookup: Dictionary mapping color IDs to color info (for ID->name conversion)
    """
    import streamlit as st
    
    # Get unfound parts (with color names for API compatibility)
    unfound_parts = get_unfound_parts(merged_df, color_lookup)
    
    # Only show this section if there are unfound parts
    if not unfound_parts:
        return
    
    st.markdown("---")
    st.markdown("### 📦 Search in Owned Sets")
    
    # Check if user has any sets with fetched inventories
    # Use session state if available, otherwise load from disk
    if st.session_state.get("sets_data_loaded", False) and st.session_state.get("sets_metadata") is not None:
        all_sets = st.session_state["sets_metadata"]
        # Group by source
        sets_by_source = {}
        for set_data in all_sets:
            source = set_data["source_csv"]
            if source not in sets_by_source:
                sets_by_source[source] = []
            sets_by_source[source].append(set_data)
    else:
        sets_by_source = sets_manager.get_sets_by_source()
    
    available_sets = []
    for source, sets_list in sets_by_source.items():
        for set_data in sets_list:
            if set_data.get("inventory_fetched", False):
                available_sets.append(set_data)
    
    if not available_sets:
        st.info("📭 No set inventories available. Add sets and retrieve inventories on the 'My Collection - Sets' page.")
        return
    
    # Display info about unfound parts
    st.markdown(f"**{len(unfound_parts)} part(s)** not found or insufficient in your loose parts collection.")
    
    # Initialize session state for set search UI
    if "show_set_selection" not in st.session_state:
        st.session_state["show_set_selection"] = False
    
    # "Include Owned Sets" button
    if not st.session_state["show_set_selection"]:
        if st.button("🔍 Include Owned Sets", key="include_owned_sets_btn", type="primary"):
            st.session_state["show_set_selection"] = True
            st.rerun()
        return
    
    # Set selection interface
    st.markdown("#### Select Sets to Search")
    st.markdown("Choose which sets to search for the missing parts:")
    
    # Initialize selected sets in session state
    if "selected_sets_for_search" not in st.session_state:
        st.session_state["selected_sets_for_search"] = set()
    
    # Group sets by source CSV and display with checkboxes
    for source_name, sets_list in sorted(sets_by_source.items()):
        # Filter to only sets with fetched inventories
        fetched_sets = [s for s in sets_list if s.get("inventory_fetched", False)]
        
        if not fetched_sets:
            continue
        
        with st.expander(f"📁 {source_name} ({len(fetched_sets)} set(s))", expanded=True):
            # "Select All" / "Deselect All" for this source
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button(f"Select All", key=f"select_all_{source_name}"):
                    for set_data in fetched_sets:
                        set_num = set_data["set_number"]
                        st.session_state["selected_sets_for_search"].add(set_num)
                        # Sync the checkbox widget state so it doesn't override on rerun
                        st.session_state[f"set_checkbox_{set_num}"] = True
                    st.rerun()
            with col2:
                if st.button(f"Deselect All", key=f"deselect_all_{source_name}"):
                    for set_data in fetched_sets:
                        set_num = set_data["set_number"]
                        st.session_state["selected_sets_for_search"].discard(set_num)
                        # Sync the checkbox widget state so it doesn't override on rerun
                        st.session_state[f"set_checkbox_{set_num}"] = False
                    st.rerun()
            
            # Display checkboxes for each set
            for set_data in fetched_sets:
                set_number = set_data["set_number"]
                set_name = set_data.get("set_name", set_number)
                part_count = set_data.get("part_count", 0)
                
                checkbox_label = f"{set_number} - {set_name} ({part_count} parts)"
                
                # Use on_change callback to sync checkbox state back to selected_sets_for_search
                def sync_checkbox_to_set(set_num=set_number):
                    cb_key = f"set_checkbox_{set_num}"
                    if st.session_state.get(cb_key, False):
                        st.session_state["selected_sets_for_search"].add(set_num)
                    else:
                        st.session_state["selected_sets_for_search"].discard(set_num)
                
                is_selected = set_number in st.session_state["selected_sets_for_search"]
                st.checkbox(
                    checkbox_label, 
                    value=is_selected, 
                    key=f"set_checkbox_{set_number}",
                    on_change=sync_checkbox_to_set,
                    args=(set_number,)
                )
    
    # Action buttons
    st.markdown("---")
    col1, col2 = st.columns([1, 1])
    
    with col1:
        # "Search Selected Sets" button
        selected_count = len(st.session_state["selected_sets_for_search"])
        if selected_count == 0:
            st.button("🔍 Search Selected Sets", key="search_sets_btn", disabled=True, type="primary")
        else:
            if st.button(f"🔍 Search Selected Sets ({selected_count})", key="search_sets_btn", type="primary"):
                with st.spinner(f"Searching {selected_count} set(s)..."):
                    # Get cached inventories from session state
                    inventories_cache = st.session_state.get("sets_inventories_cache", {})
                    
                    # Search in selected sets with part/color combinations
                    selected_sets_list = list(st.session_state["selected_sets_for_search"])
                    set_results = sets_manager.search_parts(
                        unfound_parts,  # Pass the full list of (part_num, color) tuples
                        selected_sets=selected_sets_list,
                        inventories_cache=inventories_cache
                    )
                    
                    # Store results separately (don't merge into merged_df)
                    if set_results:
                        st.session_state["set_search_results"] = set_results
                        st.success(f"✅ Found parts in {len(set_results)} part/color combination(s)!")
                        st.rerun()
                    else:
                        st.session_state["set_search_results"] = {}
                        st.warning("No matching parts found in selected sets.")
    
    with col2:
        # "Cancel" button
        if st.button("❌ Cancel", key="cancel_set_search_btn", help="Close set selection"):
            st.session_state["show_set_selection"] = False
            st.session_state["selected_sets_for_search"] = set()
            st.rerun()


def render_second_location_parts(location: str, second_loc_rows: list, color_lookup: Dict) -> None:
    """
    Render parts that are available at a location as their second location.
    
    Args:
        location: The current location being rendered
        second_loc_rows: List of row dicts for parts whose Second_location matches this location
        color_lookup: Dictionary mapping color IDs to color info
    """
    import streamlit as st
    from core.data.colors import render_color_cell
    
    if not second_loc_rows:
        return
    
    st.markdown("---")
    st.markdown("**📌 Also available here (second location):**")
    sl_df = pd.DataFrame(second_loc_rows)
    for sl_part_num, sl_part_group in sl_df.groupby("Part"):
        img_url = st.session_state.get("part_images_map", {}).get(str(sl_part_num), "")
        ba_name = sl_part_group["BA_part_name"].iloc[0] if "BA_part_name" in sl_part_group.columns else ""

        left, right = st.columns([1, 4])
        with left:
            st.markdown(f"##### **{sl_part_num}**")
            if ba_name:
                st.markdown(f"{ba_name}")
            if img_url:
                st.image(img_url, width=100)
            else:
                st.text("🚫 No image")
        with right:
            header = st.columns([2.5, 1, 2.5])
            header[0].markdown("**Color**")
            header[1].markdown("**Wanted**")
            header[2].markdown("**Primary location**")

            for _, sl_row in sl_part_group.iterrows():
                color_html = render_color_cell(sl_row["Color"], color_lookup)
                sl_qty_wanted = int(sl_row["Quantity_wanted"])
                sl_primary = str(sl_row["Location"])
                cols = st.columns([2.5, 1, 2.5])
                cols[0].markdown(color_html, unsafe_allow_html=True)
                cols[1].markdown(f"{sl_qty_wanted}")
                cols[2].markdown(f"📍 {sl_primary}")


def render_part_detail(part_num, part_group, location: str, alternative_colors: dict,
                       color_lookup: Dict, user_uploaded_images_dir) -> None:
    """
    Render the detail view for a single part within a location card.
    
    Shows part image, color rows with wanted/available/found counts,
    found input widgets, and alternative color suggestions.
    
    Args:
        part_num: The part number being rendered
        part_group: DataFrame group for this part at this location
        location: Current location name
        alternative_colors: Dict of alternative colors from similarity search
        color_lookup: Dictionary mapping color IDs to color info
        user_uploaded_images_dir: Path to user's uploaded images directory
    """
    import streamlit as st
    from core.infrastructure.session import short_key
    from core.data.colors import render_color_cell
    from core.parts.images import save_user_uploaded_image, precompute_location_images, fetch_wanted_part_images
    
    img_url = st.session_state.get("part_images_map", {}).get(str(part_num), "")
    ba_name = part_group["BA_part_name"].iloc[0] if "BA_part_name" in part_group.columns else ""
    
    left, right = st.columns([1, 4])
    with left:
        st.markdown(f"##### **{part_num}**")
        st.markdown(f"{ba_name}")
        replacement_parts = part_group["Replacement_parts"].iloc[0] if "Replacement_parts" in part_group.columns else ""
        if replacement_parts:
            st.markdown(f"(replace with {replacement_parts})")

        if img_url:
            st.image(img_url, width=100)
        else:
            st.text("🚫 No image")
            upload_key = f"upload_{part_num}_{location}"
            uploaded_file = st.file_uploader(
                "Upload image",
                type=["png", "jpg", "jpeg"],
                key=upload_key,
                label_visibility="collapsed",
                help=f"Upload a custom image for part {part_num}"
            )
            if uploaded_file is not None:
                if save_user_uploaded_image(uploaded_file, str(part_num), user_uploaded_images_dir):
                    st.success("✅ Image saved!")
                    precompute_location_images.clear()
                    fetch_wanted_part_images.clear()
                    st.rerun()
                else:
                    st.error("❌ Failed to save image")
    
    with right:
        header = st.columns([2.5, 1, 1, 2])
        header[0].markdown("**Color**")
        header[1].markdown("**Wanted**")
        header[2].markdown("**Available**")
        header[3].markdown("**Found**")

        for row_idx, row in part_group.iterrows():
            color_html = render_color_cell(row["Color"], color_lookup)
            qty_wanted = int(row["Quantity_wanted"])
            qty_have = int(row["Quantity_have"])
            qty_similar = int(row.get("Quantity_similar", 0))
            key = (str(row["Part"]), str(row["Color"]), str(row["Location"]))
            found = st.session_state.get("found_counts", {}).get(key, 0)

            cols = st.columns([2.5, 1, 1, 2])
            cols[0].markdown(color_html, unsafe_allow_html=True)
            cols[1].markdown(f"{qty_wanted}")
            
            # Display format: exact + similar (if similar parts exist)
            if qty_similar > 0:
                total_available = qty_have + qty_similar
                if qty_have == 0:
                    if total_available >= qty_wanted:
                        available_display = f"✅ 0 + {qty_similar}"
                    else:
                        available_display = f"⚠️ 0 + {qty_similar}"
                else:
                    if total_available >= qty_wanted:
                        available_display = f"✅ {qty_have} + {qty_similar}"
                    else:
                        available_display = f"⚠️ {qty_have} + {qty_similar}"
            else:
                if not row["Available"] or qty_have == 0:
                    available_display = "0 ❌"
                elif qty_have >= qty_wanted:
                    available_display = f"✅ {qty_have}"
                else:
                    available_display = f"⚠️ {qty_have}"
            cols[2].markdown(available_display)

            widget_key = short_key("found_input", row["Part"], row["Color"], row["Location"], row_idx)
            new_found = cols[3].number_input(
                " ", min_value=0, max_value=qty_wanted, value=int(found), step=1,
                key=widget_key, label_visibility="collapsed"
            )
            if int(new_found) != int(found):
                if "found_counts" not in st.session_state:
                    st.session_state["found_counts"] = {}
                st.session_state["found_counts"][key] = int(new_found)

            complete = st.session_state.get("found_counts", {}).get(key, 0) >= qty_wanted
            cols[3].markdown(
                f"✅ Found all ({st.session_state.get('found_counts', {}).get(key, 0)}/{qty_wanted})"
                if complete 
                else f"**Found:** {st.session_state.get('found_counts', {}).get(key, 0)}/{qty_wanted}"
            )
            
            # Show alternative colors
            alt_key = (str(row["Part"]), int(row["Color"]), str(row["Location"]))
            if alt_key in alternative_colors and (not row["Available"] or qty_have < qty_wanted):
                alternatives = alternative_colors[alt_key]
                if alternatives:
                    with st.expander(f"🎨 {len(alternatives)} alternative color(s) available", expanded=False):
                        st.markdown("**Alternative colors in this location:**")
                        for alt_color_id, alt_color_name, alt_qty, distance in alternatives[:5]:
                            alt_color_html = render_color_cell(alt_color_id, color_lookup)
                            alt_cols = st.columns([2.5, 1, 1])
                            alt_cols[0].markdown(alt_color_html, unsafe_allow_html=True)
                            alt_cols[1].markdown(f"Qty: **{alt_qty}**")
                            if distance < 15:
                                similarity = "Very similar"
                            elif distance < 30:
                                similarity = "Similar"
                            elif distance < 50:
                                similarity = "Somewhat similar"
                            else:
                                similarity = "Different"
                            alt_cols[2].markdown(f"*{similarity}*")


def render_location_actions(location: str, loc_group) -> None:
    """
    Render Mark all / Clear all buttons for a location.
    
    Args:
        location: Location name
        loc_group: DataFrame group for this location
    """
    import streamlit as st
    from core.infrastructure.session import short_key
    
    st.markdown("---")
    colM, colC = st.columns([1, 1])
    with colM:
        if st.button("Mark all found ✔", key=short_key("markall", location), help="Fill all items for this location", width='stretch'):
            if "found_counts" not in st.session_state:
                st.session_state["found_counts"] = {}
            for _, r in loc_group.iterrows():
                k = (str(r["Part"]), str(r["Color"]), str(r["Location"]))
                st.session_state["found_counts"][k] = int(r["Quantity_wanted"])
    with colC:
        if st.button("Clear found ✖", key=short_key("clearall", location), help="Clear found counts for this location", width='stretch'):
            for _, r in loc_group.iterrows():
                k = (str(r["Part"]), str(r["Color"]), str(r["Location"]))
                st.session_state.get("found_counts", {}).pop(k, None)


def render_missing_parts_export(merged: pd.DataFrame) -> None:
    """
    Render the export section for parts not found in the collection.
    
    Args:
        merged: Merged DataFrame with all parts data
    """
    import streamlit as st
    
    not_found_parts = merged[merged["Location"] == "❌ Not Found"].copy()
    if not not_found_parts.empty:
        st.markdown("---")
        st.markdown("### ❌ Not Available")
        st.markdown(f"**{len(not_found_parts)} part(s)** not found in your collection.")
        
        # Create Rebrickable format CSV (Part, Color, Quantity)
        export_df = not_found_parts[["Part", "Color", "Quantity_wanted"]].copy()
        export_df.columns = ["Part", "Color", "Quantity"]
        export_csv = export_df.to_csv(index=False).encode("utf-8")
        
        st.download_button("📥 Export Missing Parts (Rebrickable Format)",
            export_csv, "missing_parts_rebrickable.csv", type="primary")
