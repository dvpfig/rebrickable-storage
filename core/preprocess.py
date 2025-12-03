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
    merged = pd.merge(
        wanted,
        collection[["Part", "Color", "Location", "Quantity"]],
        on=["Part", "Color"],
        how="left",
        suffixes=("_wanted", "_have")
    )
    merged["Available"] = merged["Location"].notna()
    merged["Location"] = merged["Location"].fillna("❌ Not Found")
    merged["Quantity_have"] = merged.get("Quantity", 0).fillna(0).astype(int)
    merged = merged.sort_values(by=["Location", "Part"]) 
    return merged
