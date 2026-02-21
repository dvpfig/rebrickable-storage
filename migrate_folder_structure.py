"""
Migration script to reorganize user data folders.

This script:
1. Renames user_data/{username}/collection -> collection_parts
2. Creates user_data/{username}/collection_sets folder
3. Moves user_data/{username}/set_inventories -> cache/set_inventories
4. Moves collection.json to user_data/{username}/collection_sets.json

NOTE: If files are locked, close the application first, then run this script.
"""

import shutil
from pathlib import Path
import json


def migrate_user_folders():
    """Migrate user folder structure to new organization."""
    root = Path(__file__).parent
    user_data_dir = root / "user_data"
    cache_dir = root / "cache"
    global_inventories_dir = cache_dir / "set_inventories"
    
    # Ensure global cache directory exists
    global_inventories_dir.mkdir(parents=True, exist_ok=True)
    
    if not user_data_dir.exists():
        print("No user_data directory found. Nothing to migrate.")
        return
    
    # Process each user directory
    for user_dir in user_data_dir.iterdir():
        if not user_dir.is_dir():
            continue
        
        username = user_dir.name
        print(f"\nProcessing user: {username}")
        
        # 1. Rename collection -> collection_parts
        old_collection = user_dir / "collection"
        new_collection_parts = user_dir / "collection_parts"
        
        if old_collection.exists() and not new_collection_parts.exists():
            try:
                print(f"  ✓ Renaming collection -> collection_parts")
                old_collection.rename(new_collection_parts)
            except (OSError, PermissionError) as e:
                print(f"  ⚠ Could not rename collection folder: {e}")
                print(f"    Please close the application and manually rename:")
                print(f"    {old_collection} -> {new_collection_parts}")
        elif new_collection_parts.exists():
            print(f"  - collection_parts already exists")
            # If both exist, suggest manual merge
            if old_collection.exists():
                print(f"  ⚠ Both 'collection' and 'collection_parts' exist!")
                print(f"    Please manually merge files from 'collection' to 'collection_parts'")
                print(f"    Then delete the old 'collection' folder")
        else:
            print(f"  - No collection folder found")
        
        # 2. Create collection_sets folder
        collection_sets = user_dir / "collection_sets"
        if not collection_sets.exists():
            print(f"  ✓ Creating collection_sets folder")
            collection_sets.mkdir(parents=True, exist_ok=True)
        else:
            print(f"  - collection_sets already exists")
        
        # 3. Ensure sets folder exists (for backward compatibility)
        sets_dir = user_dir / "sets"
        sets_dir.mkdir(parents=True, exist_ok=True)
        
        # 4. Move collection.json to user_data/{username}/collection_sets.json
        collection_json_target = user_dir / "collection_sets.json"
        
        # Check multiple possible locations
        possible_locations = [
            sets_dir / "collection.json",
            collection_sets / "collection.json",
            user_dir / "collection.json"
        ]
        
        for source_path in possible_locations:
            if source_path.exists() and not collection_json_target.exists():
                try:
                    print(f"  ✓ Moving {source_path.name} to collection_sets.json")
                    shutil.copy2(source_path, collection_json_target)
                    source_path.unlink()
                    break
                except (OSError, PermissionError) as e:
                    print(f"  ⚠ Could not move {source_path.name}: {e}")
                    print(f"    Please manually move:")
                    print(f"    {source_path} -> {collection_json_target}")
        
        if collection_json_target.exists():
            print(f"  - collection_sets.json already exists")
        
        # 5. Move set_inventories to global cache
        user_inventories = user_dir / "set_inventories"
        if user_inventories.exists():
            print(f"  ✓ Moving set_inventories to global cache")
            
            # Copy all inventory files to global cache
            for inventory_file in user_inventories.glob("*.json"):
                dest_file = global_inventories_dir / inventory_file.name
                if not dest_file.exists():
                    try:
                        shutil.copy2(inventory_file, dest_file)
                        print(f"    - Copied {inventory_file.name}")
                    except (OSError, PermissionError) as e:
                        print(f"    ⚠ Could not copy {inventory_file.name}: {e}")
                else:
                    print(f"    - {inventory_file.name} already exists in cache, skipping")
            
            # Try to remove the user-specific inventories directory
            try:
                shutil.rmtree(user_inventories)
                print(f"  ✓ Removed user-specific set_inventories folder")
            except (OSError, PermissionError) as e:
                print(f"  ⚠ Could not remove set_inventories folder: {e}")
                print(f"    Files have been copied to global cache.")
                print(f"    You can manually delete this folder later: {user_inventories}")
        else:
            print(f"  - No set_inventories folder found")
    
    print("\n✅ Migration complete!")
    print(f"\nGlobal set inventories are now stored in: {global_inventories_dir}")
    print("\nFolder structure:")
    print("  - collection_parts/      → Loose parts collection CSV files")
    print("  - collection_sets/       → Set collection CSV files (uploaded by user)")
    print("  - collection_sets.json   → Set metadata (in user root folder)")
    print("\nIf any warnings appeared above, please:")
    print("  1. Close the application")
    print("  2. Manually complete the suggested actions")
    print("  3. Restart the application")


if __name__ == "__main__":
    print("=" * 60)
    print("User Data Folder Migration Script")
    print("=" * 60)
    print("\nThis script will:")
    print("  1. Rename 'collection' folders to 'collection_parts'")
    print("  2. Create 'collection_sets' folders")
    print("  3. Move 'set_inventories' to global cache")
    print("  4. Move collection.json to collection_sets.json in user root")
    print("\nStarting migration...\n")
    
    migrate_user_folders()
