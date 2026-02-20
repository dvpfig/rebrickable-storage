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
    - Have insufficient quantity (Quantity_have < Quantity_wanted)
    
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
        available = row.get("Available", False)
        
        # Check if part is not found or has insufficient quantity
        if not available or qty_have < qty_wanted:
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
    Render missing parts grouped by set in a separate section.
    
    This function displays set search results in a dedicated section,
    showing which parts from the wanted list can be found in owned sets.
    Parts are grouped by set for easy identification.
    
    Args:
        set_results: Dictionary mapping (part_num, color_name) to list of set locations
        merged_df: Original merged dataframe (for part details)
        part_images_map: Dictionary mapping part numbers to image URLs
        ba_part_names: Dictionary mapping part numbers to BrickArchitect names
        color_lookup: Dictionary for color rendering (maps color_id to color info dict)
        
    Requirements: 7.2, 7.8, 8.3
    """
    import streamlit as st
    from core.colors import render_color_cell
    
    if not set_results:
        return
    
    st.markdown("---")
    st.markdown("### 📦 Missing Parts Grouped by Set")
    st.markdown("Parts from your wanted list that can be found in your owned sets:")
    
    # Build reverse color lookup: color_name -> color_id
    color_name_to_id = {}
    for color_id, color_info in color_lookup.items():
        color_name = color_info.get("name", "")
        if color_name:
            color_name_to_id[color_name] = color_id
    
    # Reorganize results by set instead of by part
    sets_dict = {}
    for (part_num, color_name), locations in set_results.items():
        for location_info in locations:
            set_number = location_info["set_number"]
            set_name = location_info["set_name"]
            set_key = f"{set_number} - {set_name}"
            
            if set_key not in sets_dict:
                sets_dict[set_key] = []
            
            # Convert color name back to color ID for matching with merged_df
            color_id = color_name_to_id.get(color_name)
            
            # Find the wanted and have quantities from merged_df
            qty_wanted = 0
            qty_have = 0
            
            if color_id is not None:
                matching_rows = merged_df[
                    (merged_df["Part"].astype(str) == str(part_num)) & 
                    (merged_df["Color"] == color_id)
                ]
                
                if not matching_rows.empty:
                    qty_wanted = int(matching_rows.iloc[0].get("Quantity_wanted", 0))
                    qty_have = int(matching_rows.iloc[0].get("Quantity_have", 0))
            
            # Calculate missing quantity (wanted - have in collection)
            qty_missing = max(0, qty_wanted - qty_have)
            
            sets_dict[set_key].append({
                "part_num": part_num,
                "color_name": color_name,
                "color_id": color_id,
                "quantity": location_info["quantity"],
                "qty_missing": qty_missing,
                "is_spare": location_info.get("is_spare", False)
            })
    
    # Display each set with its parts
    for set_key, parts_list in sorted(sets_dict.items()):
        with st.expander(f"📦 {set_key} ({len(parts_list)} part type(s))", expanded=True):
            for part_info in parts_list:
                part_num = part_info["part_num"]
                color_name = part_info["color_name"]
                color_id = part_info["color_id"]
                quantity = part_info["quantity"]
                qty_missing = part_info["qty_missing"]
                is_spare = part_info["is_spare"]
                
                # Get part image and name
                img_url = part_images_map.get(str(part_num), "")
                ba_name = ba_part_names.get(str(part_num), "")
                
                # Display part
                left, right = st.columns([1, 4])
                
                with left:
                    st.markdown(f"**{part_num}**")
                    if ba_name:
                        st.markdown(f"{ba_name}")
                    
                    if img_url:
                        st.image(img_url, width=100)
                    else:
                        st.text("🚫 No image")
                
                with right:
                    # Render color
                    if color_id is not None:
                        color_html = render_color_cell(color_id, color_lookup)
                    else:
                        color_html = f"<span>{color_name}</span>"
                    
                    st.markdown(f"**Color:** {color_html}", unsafe_allow_html=True)
                    st.markdown(f"**Missing:** {qty_missing}")
                    st.markdown(f"**Available in set:** {quantity}")
                    
                    if is_spare:
                        st.markdown("**(Spare part)**")
                    
                    if quantity >= qty_missing:
                        st.markdown(f"✅ **Sufficient quantity available**")
                    else:
                        st.markdown(f"⚠️ **Partial match** ({quantity}/{qty_missing})")
                
                st.markdown("---")
