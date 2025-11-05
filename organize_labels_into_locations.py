import os
import shutil
import pandas as pd
import re
from pathlib import Path
import glob # Added for finding files

# --- 1. Configuration ---
# File and folder names
LOCATIONS_DIR = Path("collection") # Directory for all location CSVs

RESOURCES_DIR = Path("resources")
MAPPING_FILE = RESOURCES_DIR / 'part number - BA vs RB - filled.xlsx' 

GLOBAL_CACHE_DIR = Path("cache")
LABELS_SOURCE_DIR = GLOBAL_CACHE_DIR / "labels"

OUTPUT_BASE_DIR = Path('locations')

# Column names identified from file inspection
LOC_PART_COL = 'Part'                 # Rebrickable part num in locations file
LOC_LOCATION_COL = 'Location'         # Location name in locations file
MAP_BA_PART_COL = 'BA partnum'        # BA part num in mapping file
MAP_RB_PREFIX = 'RB part '            # Prefix for RB part columns in mapping file

def main():
    print("Starting label organization script...")

    # --- 2. Load Data ---
    try:
        # --- MODIFIED SECTION: Load all location CSVs from a directory ---
        print(f"Loading location files from '{LOCATIONS_DIR}' directory...")
        location_csv_files = glob.glob(os.path.join(LOCATIONS_DIR, '*.csv'))
        
        if not location_csv_files:
            print(f"Error: No .csv files found in the '{LOCATIONS_DIR}' directory.")
            print("Please make sure your location files are inside that folder.")
            return

        print(f"Found {len(location_csv_files)} location files to process:")
        all_locations_dfs = []
        for f in location_csv_files:
            print(f"  - Loading {f}")
            try:
                df_temp = pd.read_csv(f)
                all_locations_dfs.append(df_temp)
            except Exception as e:
                print(f"    Warning: Could not read file {f}. Error: {e}")
        
        if not all_locations_dfs:
            print("Error: No location files were successfully loaded.")
            return
            
        # Combine all loaded dataframes into one
        df_locations = pd.concat(all_locations_dfs, ignore_index=True)
        print(f"Loaded a total of {len(df_locations)} parts from all files.")
        # --- END MODIFIED SECTION ---

        print(f"Loading part mappings from '{MAPPING_FILE}'...")
        # Read the Excel file, specifying the sheet name
        df_mapping = pd.read_excel(MAPPING_FILE, sheet_name="BA Parts") 
        
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Please make sure all files/folders are in the same directory as the script.")
        return
    except ImportError:
        print("Error: The 'openpyxl' library is required to read Excel files.")
        print("Please install it by running: pip install openpyxl")
        return
    except Exception as e:
        print(f"An error occurred loading files: {e}")
        return

    # --- 3. Build Mappings ---
    
    # Create a map from any RB part number -> BA part number
    print("Building Rebrickable-to-BrickArchitect part map...")
    rb_to_ba_map = {}
    rb_cols = [col for col in df_mapping.columns if col.startswith(MAP_RB_PREFIX)]
    
    for _, row in df_mapping.iterrows():
        ba_part = str(row[MAP_BA_PART_COL]).strip()
        if not ba_part or pd.isna(ba_part):
            continue
            
        for col in rb_cols:
            rb_part = str(row[col]).strip()
            if rb_part and not pd.isna(rb_part) and rb_part != 'nan':
                rb_to_ba_map[rb_part] = ba_part

    print(f"Mapped {len(rb_to_ba_map)} unique RB parts to BA parts.")

    # Create a map of { 'Location Name': set('ba_part_1', 'ba_part_2'), ... }
    print("Building location-to-parts map...")
    location_to_ba_parts = {}
    
    for _, row in df_locations.iterrows():
        location = str(row[LOC_LOCATION_COL]).strip()
        rb_part = str(row[LOC_PART_COL]).strip()
        
        if not location or pd.isna(location) or location == 'nan':
            continue 
            
        ba_part = rb_to_ba_map.get(rb_part)
        
        if ba_part:
            if location not in location_to_ba_parts:
                location_to_ba_parts[location] = set()
            location_to_ba_parts[location].add(ba_part)

    print(f"Found {len(location_to_ba_parts)} unique locations.")

    # --- 4. Create Folders and Copy Files ---
    print(f"Creating output structure in '{OUTPUT_BASE_DIR}'...")
    os.makedirs(OUTPUT_BASE_DIR, exist_ok=True)
    
    files_copied_count = 0
    missing_labels = set()
    total_parts_processed = 0

    for location, ba_parts_set in location_to_ba_parts.items():
        # Sanitize location name for use as a directory name
        sanitized_location_name = re.sub(r'[\\/|:*?"<>]', '_', location)
        
        location_dir = os.path.join(OUTPUT_BASE_DIR, sanitized_location_name)
        os.makedirs(location_dir, exist_ok=True)
        
        for ba_part in ba_parts_set:
            total_parts_processed += 1
            label_filename = f"{ba_part}.lbx"
            source_file_path = os.path.join(LABELS_SOURCE_DIR, label_filename)
            dest_file_path = os.path.join(location_dir, label_filename)
            
            if os.path.exists(source_file_path):
                if not os.path.exists(dest_file_path):
                    try:
                        shutil.copy2(source_file_path, dest_file_path)
                        files_copied_count += 1
                    except Exception as e:
                        print(f"  ERROR copying {label_filename}: {e}")
            else:
                missing_labels.add(label_filename)

    # --- 5. Final Report ---
    print("\n--- Script Finished ---")
    print(f"Processed {total_parts_processed} part entries across {len(location_to_ba_parts)} locations.")
    print(f"Successfully copied {files_copied_count} new files.")
    
    if missing_labels:
        print(f"\nWarning: {len(missing_labels)} label files were not found in '{LABELS_SOURCE_DIR}':")
        # Print a few examples
        for i, label in enumerate(list(missing_labels)):
            if i < 10:
                print(f"  - {label}")
            else:
                print(f"  ...and {len(missing_labels) - 10} more.")
                break

if __name__ == "__main__":
    main()