# Folder Structure Migration Instructions

## What Changed?

The application's folder structure has been reorganized for better data management:

1. **User collection folders renamed**: `collection` → `collection_parts`
2. **New folder created**: `collection_sets` (for set collection CSV files)
3. **Set inventories moved to global cache**: `user_data/{username}/set_inventories` → `cache/set_inventories`
4. **Metadata location clarified**: `collection.json` stays in `sets/` folder

## Folder Structure Explained

- **collection_parts/**: Contains CSV files with your loose parts inventories (parts organized by location)
- **collection_sets/**: Contains CSV files with lists of sets you own (uploaded from Rebrickable)
- **collection_sets.json**: Metadata file in user root folder (managed automatically by the app)
- **sets/**: Legacy folder kept for backward compatibility
- **cache/set_inventories/**: Global cache of set inventories (shared across all users)

## Why This Change?

- **Efficiency**: Set inventories are now shared across all users, reducing API calls
- **Clarity**: Folder names better reflect their purpose
- **Performance**: If multiple users own the same set, inventory is only fetched once

## How to Migrate

### Option 1: Automatic Migration (Recommended)

1. **Close the application** if it's running
2. Run the migration script:
   ```bash
   python migrate_folder_structure.py
   ```
3. Follow any on-screen instructions
4. Restart the application

### Option 2: Manual Migration

If the automatic script encounters issues:

1. **Close the application**
2. For each user folder in `user_data/`:
   - Rename `collection` → `collection_parts`
   - Create new folder `collection_sets`
   - Copy all files from `set_inventories/*.json` to `cache/set_inventories/`
   - Delete the `set_inventories` folder
3. Restart the application

## What If I Don't Migrate?

The application will automatically create the new folder structure, but:
- Old `collection` folders won't be automatically found
- You'll need to re-upload your collection CSV files
- Set inventories will need to be re-fetched from the API

## Troubleshooting

### "Files are locked" Error

**Problem**: The application or another process is using the files.

**Solution**:
1. Close the Streamlit application completely
2. Close any file explorers viewing those folders
3. Run the migration script again

### Both `collection` and `collection_parts` Exist

**Problem**: Migration was partially completed.

**Solution**:
1. Check if `collection_parts` has your CSV files
2. If yes, manually delete the old `collection` folder
3. If no, move files from `collection` to `collection_parts`

### "collection.json in Wrong Location"

**Problem**: The `collection.json` file is in the wrong location.

**Solution**:
1. Move the file to `user_data/{username}/collection_sets.json` (in the user root folder)
2. Keep CSV files in `collection_sets/` folder (those are your set lists)
3. Restart the application

**Problem**: Application can't find set inventories after migration.

**Solution**:
1. Check that `cache/set_inventories/` exists and contains `.json` files
2. If empty, you can re-fetch inventories from the "My Collection - Sets" page
3. The global cache will be populated automatically

## Need Help?

If you encounter issues:
1. Check the migration script output for specific error messages
2. Verify folder permissions (read/write access)
3. Ensure no other applications are accessing the files
4. Try manual migration as a fallback

## After Migration

Once migrated successfully:
- Your collection CSV files will be in `collection_parts`
- Set inventories will load faster (from global cache)
- Multiple users can share set inventory data
- The old folder structure is no longer needed
