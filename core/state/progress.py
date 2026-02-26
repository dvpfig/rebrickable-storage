# ui/summary.py
import streamlit as st
import pandas as pd


def render_summary_table(merged_df, set_search_results=None, set_found_counts=None, color_lookup=None):
    """
    Render summary & progress table by location, including set-found counts.
    
    Args:
        merged_df: Merged dataframe with Found column already populated
        set_search_results: Dict from set search {(part_num, color_name): [locations...]}
        set_found_counts: Dict {(part_num, color_name, set_key): found_count}
        color_lookup: Dict mapping color_id to color info (with 'name' key)
    """
    # Start with the location-based summary from merged_df
    summary = merged_df.groupby("Location").agg(
        parts_count=("Part", "count"),
        found_parts=("Found", "sum"),
        total_wanted=("Quantity_wanted", "sum")
    ).reset_index()

    # Add set-based rows if we have set search results
    if set_search_results and set_found_counts:
        # Build reverse color lookup: color_name -> color_id
        color_name_to_id = {}
        if color_lookup:
            for color_id, color_info in color_lookup.items():
                color_name = color_info.get("name", "")
                if color_name:
                    color_name_to_id[color_name] = color_id

        # Reorganize by set
        sets_dict = {}
        for (part_num, color_name), locations in set_search_results.items():
            for location_info in locations:
                set_number = location_info["set_number"]
                set_name = location_info["set_name"]
                set_key = f"{set_number} - {set_name}"

                if set_key not in sets_dict:
                    sets_dict[set_key] = {"parts_count": 0, "found_parts": 0, "total_wanted": 0}

                color_id = color_name_to_id.get(color_name)
                # Find qty_missing from merged_df
                qty_wanted = 0
                qty_have = 0
                if color_id is not None:
                    matching = merged_df[
                        (merged_df["Part"].astype(str) == str(part_num)) &
                        (merged_df["Color"].astype(str) == str(color_id))
                    ]
                    if not matching.empty:
                        qty_wanted = int(matching.iloc[0].get("Quantity_wanted", 0))
                        qty_have = int(matching.iloc[0].get("Quantity_have", 0))

                qty_missing = max(0, qty_wanted - qty_have)
                qty_in_set = min(location_info.get("quantity", 0), qty_missing)

                sets_dict[set_key]["parts_count"] += 1
                sets_dict[set_key]["total_wanted"] += qty_in_set

                found_key = (part_num, color_name, set_key)
                found = set_found_counts.get(found_key, 0)
                sets_dict[set_key]["found_parts"] += found

        # Append set rows
        set_rows = []
        for set_key, data in sorted(sets_dict.items()):
            set_rows.append({
                "Location": f"📦 Set {set_key}",
                "parts_count": data["parts_count"],
                "found_parts": data["found_parts"],
                "total_wanted": data["total_wanted"]
            })
        if set_rows:
            summary = pd.concat([summary, pd.DataFrame(set_rows)], ignore_index=True)

    summary["completion_%"] = (100 * summary["found_parts"] / summary["total_wanted"]).round(1).fillna(0)

    st.markdown("### 📈 Summary & Progress by Location")
    st.data_editor(
        summary,
        column_config={
            "completion_%": st.column_config.ProgressColumn(
                "completion_%", format="%d%%", min_value=0, max_value=100, color="auto"
            )
        },
        hide_index=True,
        width='stretch'
    )
