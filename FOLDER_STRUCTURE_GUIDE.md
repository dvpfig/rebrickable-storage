# User Data Folder Structure Guide

## Overview

This guide explains the purpose of each folder in the user data directory structure.

## Folder Structure

```
user_data/{username}/
├── collection_parts/        # Loose parts collection CSV files
├── collection_sets/         # Set collection CSV files
├── collection_sets.json     # Set metadata (managed by app)
├── sets/                    # Legacy folder (kept for compatibility)
└── images_uploaded/         # Custom part images
```

## Detailed Explanation

### collection_parts/

**Purpose**: Stores CSV files containing your loose parts inventories.

**Content**: CSV files exported from Rebrickable with your parts organized by storage location.

**Example files**:
- `rebrickable_parts_399620_1-A_Basic_Plates-Tiles.csv`
- `rebrickable_parts_400456_6-A_Minifig_Accessories.csv`

**When to use**: Upload these files on the "My Collection - Parts" page to manage your loose parts.

### collection_sets/

**Purpose**: Stores CSV files containing lists of LEGO sets you own.

**Content**: CSV files exported from Rebrickable with your set collections.

**Example files**:
- `rebrickable_sets_city-fire-police-construction.csv`
- `rebrickable_sets_creator-expert.csv`

**CSV Format**:
```csv
Set Number,Quantity,Includes Spares,Inventory Ver
60393-1,1,True,1
60286-1,1,True,1
```

**When to use**: Upload these files on the "My Collection - Sets" page to add multiple sets at once.

### collection_sets.json

**Purpose**: Stores metadata about your set collection (managed automatically by the app).

**Location**: `user_data/{username}/collection_sets.json` (in the user root folder)

**Content**: Contains metadata about all sets you've added, including:
- Set numbers and names
- Quantities
- Inventory fetch status
- Source (CSV file or manual entry)
- Date added

**Important**: This file is managed automatically by the application. Don't edit it manually.

### sets/

**Purpose**: Legacy folder kept for backward compatibility.

**Content**: Empty (no longer actively used)

**Note**: This folder was previously used to store `collection.json`, which has been moved to `collection_sets.json` in the user root folder.

**Purpose**: Stores custom part images you've uploaded.

**Content**: PNG/JPG images of parts that you've manually uploaded to replace or supplement the default images.

**When to use**: Upload custom images on the "My Collection - Parts" page when you want to use your own photos.

## Global Cache

```
cache/
├── images/              # Cached part images (shared)
├── labels/              # Cached label files (shared)
└── set_inventories/     # Cached set inventories (shared)
```

### cache/set_inventories/

**Purpose**: Global cache of set inventories shared across all users.

**Content**: JSON files containing the parts list for each set.

**Example files**:
- `60393-1.json` (4x4 Fire Truck Rescue inventory)
- `31147-1.json` (Retro Camera inventory)

**Benefits**:
- Reduces API calls to Rebrickable
- Faster loading when multiple users own the same set
- Shared resource across all users

## Common Scenarios

### Adding Loose Parts

1. Export your parts from Rebrickable as CSV
2. Go to "My Collection - Parts" page
3. Upload CSV files → They go to `collection_parts/`

### Adding Sets

**Option 1: Upload CSV**
1. Export your sets from Rebrickable as CSV
2. Go to "My Collection - Sets" page
3. Upload CSV file → It goes to `collection_sets/`
4. App creates/updates `collection_sets.json` in user root folder

**Option 2: Manual Entry**
1. Go to "My Collection - Sets" page
2. Enter set number manually
3. App adds to `collection_sets.json` in user root folder

### Fetching Set Inventories

1. On "My Collection - Sets" page, click "Retrieve Inventories"
2. App checks `cache/set_inventories/` first
3. If not cached, fetches from Rebrickable API
4. Saves to global cache for future use

## Migration Notes

If you're migrating from the old structure:
- Old `collection/` → New `collection_parts/`
- Old `set_inventories/` → Global `cache/set_inventories/`
- Old `sets/collection.json` → New `collection_sets.json` (in user root folder)

Run `python migrate_folder_structure.py` to automate the migration.
