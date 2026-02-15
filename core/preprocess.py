# core/preprocess.py
import pandas as pd
from streamlit import cache_data

def sanitize_and_validate(df, required, label):
    df.columns = df.columns.str.strip().str.title()
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"File {label} missing required columns: {', '.join(missing)}")
    return df

@cache_data(show_spinner=False)
def load_wanted_files(files):
    dfs = []
    for file in files:
        df = pd.read_csv(file)
        df = sanitize_and_validate(df, ["Part", "Color", "Quantity"], getattr(file, "name", "uploaded_wanted"))
        df = df.rename(columns={"Quantity": "Quantity_wanted"})
        dfs.append(df)
    return pd.concat(dfs, ignore_index=True)

@cache_data(show_spinner=False)
def load_collection_files(files):
    dfs = []
    for file in files:
        if hasattr(file, "read"):
            df = pd.read_csv(file)
            label = getattr(file, "name", "uploaded_collection")
        else:
            df = pd.read_csv(file)
            label = str(file)
        df = sanitize_and_validate(df, ["Part", "Color", "Quantity", "Location"], label)
        dfs.append(df)
    return pd.concat(dfs, ignore_index=True)


@cache_data(show_spinner=False)
def merge_wanted_collection(wanted, collection, rb_to_similar_mapping=None):
    """
    Merge wanted and collection dataframes, identifying exact matches and similar parts.

    Args:
        wanted: DataFrame with wanted parts
        collection: DataFrame with collection parts
        rb_to_similar_mapping: Optional dict mapping RB parts to similar RB parts

    Returns:
        DataFrame with merged data including replacement part suggestions
    """
    # First merge: exact Part+Color match
    merged = pd.merge(
        wanted,
        collection[["Part", "Color", "Location", "Quantity"]],
        on=["Part", "Color"],
        how="left",
        suffixes=("_wanted", "_have")
    )
    merged["Available"] = merged["Location"].notna()
    merged["Quantity_have"] = merged.get("Quantity", 0).fillna(0).astype(int)
    merged["Replacement_parts"] = ""  # Initialize replacement parts column

    # Identify parts that were not found in the exact color
    not_found_exact = merged[merged["Location"].isna()].copy()

    # Create a mapping of Part -> set of Locations where the part exists (any color)
    part_to_locations = collection.groupby("Part")["Location"].apply(set).to_dict()

    # For similar parts matching, create a mapping of (Part, Color, Location) -> Quantity
    collection_inventory = {}
    for _, row in collection.iterrows():
        key = (str(row["Part"]), str(row["Color"]), str(row["Location"]))
        collection_inventory[key] = int(row["Quantity"])

    # For wanted parts not found in exact color, check for similar parts
    additional_rows = []
    truly_not_found_rows = []

    for _, row in not_found_exact.iterrows():
        wanted_part = str(row["Part"])
        wanted_color = str(row["Color"])

        # Check if similar parts exist in collection
        similar_parts_found = {}  # {location: [list of similar part numbers]}

        if rb_to_similar_mapping and wanted_part in rb_to_similar_mapping:
            similar_parts = rb_to_similar_mapping[wanted_part]

            # Check each similar part in the collection
            for similar_part in similar_parts:
                # Check if this similar part exists in the wanted color
                key = (similar_part, wanted_color, None)
                for (part, color, location), qty in collection_inventory.items():
                    if part == similar_part and color == wanted_color and qty > 0:
                        if location not in similar_parts_found:
                            similar_parts_found[location] = []
                        similar_parts_found[location].append(similar_part)

        # If similar parts found, create entries for each location
        if similar_parts_found:
            for location, similar_list in similar_parts_found.items():
                new_row = row.copy()
                new_row["Location"] = location
                new_row["Available"] = True  # Similar part available

                # Calculate total quantity of similar parts in this location
                total_similar_qty = 0
                for similar_part in similar_list:
                    key = (similar_part, wanted_color, location)
                    total_similar_qty += collection_inventory.get(key, 0)

                new_row["Quantity_have"] = total_similar_qty
                new_row["Replacement_parts"] = ", ".join(sorted(set(similar_list)))
                additional_rows.append(new_row)

        # Also check if part exists in collection in different color(s)
        elif wanted_part in part_to_locations:
            # Part exists in collection in different color(s)
            for location in part_to_locations[wanted_part]:
                new_row = row.copy()
                new_row["Location"] = location
                new_row["Available"] = False  # Not in exact color
                new_row["Quantity_have"] = 0
                new_row["Replacement_parts"] = ""
                additional_rows.append(new_row)
        else:
            # Part doesn't exist in collection in any form
            new_row = row.copy()
            new_row["Location"] = "❌ Not Found"
            new_row["Available"] = False
            new_row["Quantity_have"] = 0
            new_row["Replacement_parts"] = ""
            truly_not_found_rows.append(new_row)

    # Combine all rows: found (exact match), similar parts, found in different colors, and truly not found
    found_rows = merged[merged["Location"].notna()].copy()
    all_rows = [found_rows]

    if additional_rows:
        all_rows.append(pd.DataFrame(additional_rows))
    if truly_not_found_rows:
        all_rows.append(pd.DataFrame(truly_not_found_rows))

    merged = pd.concat(all_rows, ignore_index=True)
    merged = merged.sort_values(by=["Location", "Part"])
    return merged



def get_collection_parts_tuple(collection_dir):
    """
    Load collection files from a directory and return unique part numbers as a tuple.
    
    Args:
        collection_dir: Path object pointing to directory containing collection CSV files
    
    Returns:
        tuple: Tuple of unique RB part numbers (as strings), or None if no files found
    """
    from pathlib import Path
    
    collection_dir = Path(collection_dir)
    collection_files = sorted(collection_dir.glob("*.csv"))
    
    if not collection_files:
        return None
    
    collection_file_handles = [open(f, "rb") for f in collection_files]
    try:
        collection_df = load_collection_files(collection_file_handles)
        return tuple(collection_df["Part"].astype(str).unique())
    finally:
        # Always close file handles
        for fh in collection_file_handles:
            fh.close()


def get_collection_parts_set(collection_dir):
    """
    Load collection files from a directory and return unique part numbers as a set.
    
    Args:
        collection_dir: Path object pointing to directory containing collection CSV files
    
    Returns:
        set: Set of unique RB part numbers (as strings), or None if no files found
    """
    from pathlib import Path
    
    collection_dir = Path(collection_dir)
    collection_files = sorted(collection_dir.glob("*.csv"))
    
    if not collection_files:
        return None
    
    collection_file_handles = [open(f, "rb") for f in collection_files]
    try:
        collection_df = load_collection_files(collection_file_handles)
        return set(collection_df["Part"].astype(str).unique())
    finally:
        # Always close file handles
        for fh in collection_file_handles:
            fh.close()
