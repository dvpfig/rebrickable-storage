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
def merge_wanted_collection(wanted, collection):
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
    
    # Identify parts that were not found in the exact color
    not_found_exact = merged[merged["Location"].isna()].copy()
    
    # Create a mapping of Part -> set of Locations where the part exists (any color)
    part_to_locations = collection.groupby("Part")["Location"].apply(set).to_dict()
    
    # For wanted parts not found in exact color, check if part exists in other colors
    additional_rows = []
    truly_not_found_rows = []
    
    for _, row in not_found_exact.iterrows():
        part = row["Part"]
        if part in part_to_locations:
            # Part exists in collection in different color(s)
            # Add an entry for each location where the part exists
            for location in part_to_locations[part]:
                new_row = row.copy()
                new_row["Location"] = location
                new_row["Available"] = False  # Not in exact color
                new_row["Quantity_have"] = 0  # Not available in this color
                additional_rows.append(new_row)
        else:
            # Part doesn't exist in collection in any color
            new_row = row.copy()
            new_row["Location"] = "❌ Not Found"
            new_row["Available"] = False
            new_row["Quantity_have"] = 0
            truly_not_found_rows.append(new_row)
    
    # Combine all rows: found (exact match), found in different colors, and truly not found
    found_rows = merged[merged["Location"].notna()].copy()
    all_rows = [found_rows]
    
    if additional_rows:
        all_rows.append(pd.DataFrame(additional_rows))
    if truly_not_found_rows:
        all_rows.append(pd.DataFrame(truly_not_found_rows))
    
    merged = pd.concat(all_rows, ignore_index=True)
    merged = merged.sort_values(by=["Location", "Part"]) 
    return merged
