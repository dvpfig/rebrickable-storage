"""
Debug script to check part matching and similar parts detection.
Run this to diagnose why parts aren't matching correctly.
"""

import pandas as pd
from pathlib import Path
from core.infrastructure.paths import init_paths
from core.parts.mapping import build_rb_to_similar_parts_mapping, build_ba_to_rb_mapping
from core.data.preprocess import load_collection_files

# Initialize paths
paths = init_paths()

# Load the BA-RB mapping
print("=" * 60)
print("PART MAPPING ANALYSIS")
print("=" * 60)

# Build mappings
ba_to_rb = build_ba_to_rb_mapping(paths.mapping_path)
rb_to_similar = build_rb_to_similar_parts_mapping(paths.mapping_path)

# Check specific parts
test_parts = ['3626b', '3626c', '3626bpr0004', '3626bpr0005', '3626bpr0006']

print("\n1. BA Part Number Lookup:")
print("-" * 60)
for part in test_parts:
    # Find BA number for this RB part
    ba_num = None
    for ba, rb_list in ba_to_rb.items():
        if part in rb_list:
            ba_num = ba
            break
    
    if ba_num:
        print(f"  {part:15} → BA: {ba_num}")
        print(f"                    → Similar RB parts: {ba_to_rb[ba_num]}")
    else:
        print(f"  {part:15} → NOT FOUND in mapping")

print("\n2. Similar Parts Mapping:")
print("-" * 60)
for part in test_parts:
    if part in rb_to_similar:
        print(f"  {part:15} → Similar: {rb_to_similar[part]}")
    else:
        print(f"  {part:15} → No similar parts found")

# Check collection data
print("\n3. Collection Data Check:")
print("-" * 60)
print("Enter username to check their collection (or press Enter to skip):")
username = input().strip()

if username:
    user_collection_dir = paths.get_user_collection_parts_dir(username)
    collection_files = sorted(user_collection_dir.glob("*.csv"))
    
    if collection_files:
        print(f"\nFound {len(collection_files)} collection file(s)")
        
        # Load collection
        collection_file_handles = [open(f, "rb") for f in collection_files]
        try:
            collection = load_collection_files(collection_file_handles)
            
            # Normalize
            collection["Part"] = collection["Part"].astype(str).str.strip()
            collection["Color"] = collection["Color"].astype(str).str.strip()
            
            print(f"\nTotal parts in collection: {len(collection)}")
            
            # Check for specific parts
            print("\nSearching for test parts in collection:")
            for part in test_parts:
                matches = collection[collection["Part"] == part]
                if len(matches) > 0:
                    print(f"\n  {part}:")
                    for _, row in matches.iterrows():
                        print(f"    Color: {row['Color']:3} | Qty: {row['Quantity']:3} | Location: {row['Location']}")
                else:
                    print(f"  {part}: NOT FOUND in collection")
            
            # Check for parts starting with 3626
            print("\n\nAll parts starting with '3626' in collection:")
            parts_3626 = collection[collection["Part"].str.startswith("3626")]
            if len(parts_3626) > 0:
                for part_num in sorted(parts_3626["Part"].unique()):
                    part_data = parts_3626[parts_3626["Part"] == part_num]
                    colors = part_data["Color"].unique()
                    print(f"  {part_num}: Colors {list(colors)}")
            else:
                print("  No parts starting with 3626 found")
                
        finally:
            for fh in collection_file_handles:
                fh.close()
    else:
        print(f"No collection files found in {user_collection_dir}")

print("\n" + "=" * 60)
print("DIAGNOSIS COMPLETE")
print("=" * 60)
print("\nIf you see '0 + 2' instead of '6 + 2', check:")
print("1. Are 3626b and 3626c mapped to the same BA part number?")
print("2. Does your collection actually have 3626b in the correct color?")
print("3. Have you cleared Streamlit's cache? (Press 'C' in the app)")
print("4. Are the part numbers and colors exactly matching (no extra spaces)?")
