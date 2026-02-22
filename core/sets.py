"""
Sets database manager for LEGO set collection management.

This module manages LEGO set collection data, inventory retrieval,
and part searching within owned sets.
"""

import json
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from core.rebrickable_api import RebrickableAPI, APIError


class SetsManager:
    """Manages LEGO set collection and inventory data."""
    
    def __init__(self, user_data_dir: Path, global_cache_dir: Path, api_key: Optional[str] = None):
        """
        Initialize the sets manager.

        Args:
            user_data_dir: Path to user's data directory
            global_cache_dir: Path to global cache directory for set inventories
            api_key: Optional Rebrickable API key
        """
        self.user_data_dir = user_data_dir
        self.sets_dir = user_data_dir / "sets"
        self.inventories_dir = global_cache_dir  # Use the path directly, it's already cache/set_inventories
        self.api_key = api_key
        self.sets_metadata_file = user_data_dir / "collection_sets.json"

        # Ensure directories exist
        self.sets_dir.mkdir(parents=True, exist_ok=True)
        self.inventories_dir.mkdir(parents=True, exist_ok=True)

    
    def load_sets_from_csv(self, csv_file, source_name: str) -> List[Dict]:
        """
        Parse and validate sets CSV file.
        
        Expected CSV format (case-insensitive):
        Set number,Quantity,Includes spares,Inventory ver
        31147-1,1,true,1
        
        Args:
            csv_file: Uploaded CSV file (Streamlit UploadedFile) or file path
            source_name: Name to identify this CSV source
            
        Returns:
            List of set dictionaries with metadata
            
        Raises:
            ValueError: If CSV format is invalid
        """
        try:
            # Read CSV file
            if hasattr(csv_file, 'read'):
                # Streamlit UploadedFile
                df = pd.read_csv(csv_file)
            else:
                # File path
                df = pd.read_csv(csv_file)
            
            # Normalize column names (strip whitespace and convert to lowercase for matching)
            df.columns = df.columns.str.strip()
            column_map = {col: col for col in df.columns}
            column_map_lower = {col.lower(): col for col in df.columns}
            
            # Define required columns with their variations
            required_fields = {
                "set_number": ["set number", "set_number", "setnumber"],
                "quantity": ["quantity", "qty"],
                "includes_spares": ["includes spares", "includes_spares", "includesspares"],
                "inventory_ver": ["inventory ver", "inventory_ver", "inventoryver", "inventory version"]
            }
            
            # Find actual column names (case-insensitive)
            actual_columns = {}
            missing_fields = []
            
            for field, variations in required_fields.items():
                found = False
                for variation in variations:
                    if variation.lower() in column_map_lower:
                        actual_columns[field] = column_map_lower[variation.lower()]
                        found = True
                        break
                if not found:
                    missing_fields.append(variations[0])  # Use first variation in error message
            
            if missing_fields:
                raise ValueError(
                    f"Invalid CSV format. Missing columns: {', '.join(missing_fields)}"
                )
            
            # Parse sets from dataframe
            sets = []
            for _, row in df.iterrows():
                set_data = {
                    "set_number": str(row[actual_columns["set_number"]]).strip(),
                    "quantity": int(row[actual_columns["quantity"]]),
                    "includes_spares": self._parse_bool(row[actual_columns["includes_spares"]]),
                    "inventory_version": int(row[actual_columns["inventory_ver"]]),
                    "source_csv": source_name,
                    "date_added": datetime.now().isoformat(),
                    "inventory_fetched": False,
                    "inventory_fetch_date": None,
                    "set_name": None,
                    "part_count": 0
                }
                sets.append(set_data)
            
            if not sets:
                raise ValueError("CSV file contains no valid sets")
            
            return sets
            
        except pd.errors.EmptyDataError:
            raise ValueError("CSV file is empty")
        except pd.errors.ParserError as e:
            raise ValueError(f"CSV parsing error: {str(e)}")
        except KeyError as e:
            raise ValueError(f"Missing required column: {str(e)}")
        except Exception as e:
            raise ValueError(f"Error reading CSV file: {str(e)}")
    
    def _parse_bool(self, value) -> bool:
        """Parse boolean value from CSV (handles 'true', 'True', '1', etc.)."""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ('true', 'yes', '1', 't', 'y')
        return bool(value)

    def save_sets_metadata(self, sets: List[Dict]) -> None:
        """
        Save sets metadata to collection_sets.json.
        
        Args:
            sets: List of set dictionaries to save
        """
        metadata = {
            "sets": sets,
            "version": "1.0",
            "last_updated": datetime.now().isoformat()
        }
        
        with open(self.sets_metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    def load_sets_metadata(self) -> List[Dict]:
        """
        Load sets metadata from collection_sets.json.
        
        Returns:
            List of set dictionaries, or empty list if file doesn't exist
        """
        if not self.sets_metadata_file.exists():
            return []
        
        try:
            with open(self.sets_metadata_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("sets", [])
        except (json.JSONDecodeError, IOError):
            # If file is corrupted, return empty list
            return []
    
    def add_manual_set(self, set_number: str) -> Dict:
        """
        Add a single set manually.
        
        Args:
            set_number: LEGO set number (e.g., "31147-1")
            
        Returns:
            Set metadata dictionary
            
        Raises:
            ValueError: If set number is invalid or duplicate
        """
        # Validate set number format (basic validation)
        set_number = set_number.strip()
        if not set_number:
            raise ValueError("Set number cannot be empty")
        
        # Check for duplicates
        existing_sets = self.load_sets_metadata()
        if any(s["set_number"] == set_number for s in existing_sets):
            raise ValueError(f"Set {set_number} is already in your collection")
        
        # Create set metadata
        set_data = {
            "set_number": set_number,
            "quantity": 1,
            "includes_spares": True,
            "inventory_version": 1,
            "source_csv": "Manual Entry",
            "date_added": datetime.now().isoformat(),
            "inventory_fetched": False,
            "inventory_fetch_date": None,
            "set_name": None,
            "part_count": 0
        }
        
        # Add to existing sets and save
        existing_sets.append(set_data)
        self.save_sets_metadata(existing_sets)
        
        return set_data
    
    def delete_set(self, set_number: str) -> None:
        """
        Delete a set and its inventory data.
        
        Args:
            set_number: Set number to delete
        """
        # Load existing sets
        sets = self.load_sets_metadata()
        
        # Filter out the set to delete
        updated_sets = [s for s in sets if s["set_number"] != set_number]
        
        # Save updated metadata
        self.save_sets_metadata(updated_sets)
        
        # Delete inventory file if it exists
        inventory_file = self.inventories_dir / f"{set_number}.json"
        if inventory_file.exists():
            inventory_file.unlink()
    
    def delete_source_group(self, source_name: str) -> None:
        """
        Delete all sets from a specific CSV source.
        
        Args:
            source_name: Name of the source CSV to delete
        """
        # Load existing sets
        sets = self.load_sets_metadata()
        
        # Get set numbers to delete (for inventory cleanup)
        sets_to_delete = [s["set_number"] for s in sets if s["source_csv"] == source_name]
        
        # Filter out sets from this source
        updated_sets = [s for s in sets if s["source_csv"] != source_name]
        
        # Save updated metadata
        self.save_sets_metadata(updated_sets)
        
        # Delete inventory files
        for set_number in sets_to_delete:
            inventory_file = self.inventories_dir / f"{set_number}.json"
            if inventory_file.exists():
                inventory_file.unlink()
    
    def get_sets_by_source(self) -> Dict[str, List[Dict]]:
        """
        Get sets grouped by their source CSV.
        
        Returns:
            Dictionary mapping source names to lists of sets
        """
        sets = self.load_sets_metadata()
        
        # Group by source
        grouped = {}
        for set_data in sets:
            source = set_data["source_csv"]
            if source not in grouped:
                grouped[source] = []
            grouped[source].append(set_data)
        
        return grouped
    
    def fetch_inventory(self, set_number: str, api_client: RebrickableAPI) -> Dict:
        """
        Fetch inventory for a single set from Rebrickable API.
        First checks global cache, only fetches from API if not cached.

        Args:
            set_number: LEGO set number
            api_client: Configured API client

        Returns:
            Inventory data dictionary

        Raises:
            APIError: If API call fails
        """
        # Check if inventory already exists in global cache
        inventory_file = self.inventories_dir / f"{set_number}.json"
        if inventory_file.exists():
            try:
                with open(inventory_file, 'r', encoding='utf-8') as f:
                    cached_inventory = json.load(f)

                # Update set metadata with cached info
                sets = self.load_sets_metadata()
                for set_data in sets:
                    if set_data["set_number"] == set_number:
                        set_data["inventory_fetched"] = True
                        set_data["inventory_fetch_date"] = cached_inventory.get("fetch_date", "unknown")
                        set_data["set_name"] = cached_inventory.get("set_name", set_number)
                        set_data["part_count"] = cached_inventory.get("total_parts", 0)
                        break
                self.save_sets_metadata(sets)

                return cached_inventory
            except (json.JSONDecodeError, IOError):
                # If cached file is corrupted, fetch from API
                pass

        # Get set info and parts from API
        set_info = api_client.get_set_info(set_number)
        parts = api_client.get_set_parts(set_number, include_spares=True)

        # Build inventory structure
        inventory = {
            "set_number": set_number,
            "set_name": set_info["name"],
            "fetch_date": datetime.now().isoformat(),
            "parts": parts,
            "total_parts": len(parts)
        }

        # Save to global cache
        with open(inventory_file, 'w', encoding='utf-8') as f:
            json.dump(inventory, f, indent=2, ensure_ascii=False)

        # Update set metadata
        sets = self.load_sets_metadata()
        for set_data in sets:
            if set_data["set_number"] == set_number:
                set_data["inventory_fetched"] = True
                set_data["inventory_fetch_date"] = inventory["fetch_date"]
                set_data["set_name"] = set_info["name"]
                set_data["part_count"] = len(parts)
                break
        self.save_sets_metadata(sets)

        return inventory

    
    def fetch_all_inventories(self, api_client: RebrickableAPI, 
                             progress_callback=None) -> Dict:
        """
        Fetch inventories for all sets in collection.
        
        Args:
            api_client: Configured API client
            progress_callback: Optional callback for progress updates
                             Called with (current_index, total_sets, set_number, status)
            
        Returns:
            Statistics dictionary with success/failure counts and errors
        """
        sets = self.load_sets_metadata()
        
        stats = {
            "total_sets": len(sets),
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "errors": []
        }
        
        for idx, set_data in enumerate(sets):
            set_number = set_data["set_number"]
            
            # Skip if already fetched (cached)
            if set_data.get("inventory_fetched", False):
                stats["skipped"] += 1
                if progress_callback:
                    progress_callback(idx + 1, len(sets), set_number, "skipped (cached)")
                continue
            
            # Notify progress
            if progress_callback:
                progress_callback(idx + 1, len(sets), set_number, "fetching")
            
            try:
                # Fetch inventory
                self.fetch_inventory(set_number, api_client)
                stats["successful"] += 1
                
                if progress_callback:
                    progress_callback(idx + 1, len(sets), set_number, "success")
                    
            except APIError as e:
                # Log error and continue
                error_msg = f"Set {set_number}: {str(e)}"
                stats["errors"].append(error_msg)
                stats["failed"] += 1
                
                if progress_callback:
                    progress_callback(idx + 1, len(sets), set_number, f"failed: {str(e)}")
                    
            except Exception as e:
                # Unexpected error
                error_msg = f"Set {set_number}: Unexpected error - {str(e)}"
                stats["errors"].append(error_msg)
                stats["failed"] += 1
                
                if progress_callback:
                    progress_callback(idx + 1, len(sets), set_number, f"error: {str(e)}")
        
        return stats
    
    def load_inventory(self, set_number: str) -> Optional[Dict]:
        """
        Load cached inventory for a set.
        
        Args:
            set_number: LEGO set number
            
        Returns:
            Inventory data dictionary or None if not cached
        """
        inventory_file = self.inventories_dir / f"{set_number}.json"
        
        if not inventory_file.exists():
            return None
        
        try:
            with open(inventory_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            # If file is corrupted, return None
            return None
    
    def load_all_inventories(self) -> Dict[str, Dict]:
        """
        Load all cached inventories for sets in the collection.
        
        Returns:
            Dictionary mapping set numbers to inventory data
        """
        inventories = {}
        sets = self.load_sets_metadata()
        
        for set_data in sets:
            if set_data.get("inventory_fetched", False):
                set_number = set_data["set_number"]
                inventory = self.load_inventory(set_number)
                if inventory:
                    inventories[set_number] = inventory
        
        return inventories
    
    def load_into_session_state(self, session_state) -> None:
        """
        Load sets data into Streamlit session state for caching.
        
        This method loads sets metadata and inventories from disk into session state
        to avoid redundant file reads during the session.
        
        Args:
            session_state: Streamlit session state object
        """
        # Load sets metadata
        session_state["sets_metadata"] = self.load_sets_metadata()
        
        # Load all inventories
        session_state["sets_inventories_cache"] = self.load_all_inventories()
        
        # Mark as loaded
        session_state["sets_data_loaded"] = True
    
    def save_to_session_state(self, session_state) -> None:
        """
        Save current sets data to session state.
        
        This method updates session state with the latest sets metadata and inventories.
        Call this after any modification to sets data (add, delete, fetch inventory).
        
        Args:
            session_state: Streamlit session state object
        """
        # Reload metadata from disk
        session_state["sets_metadata"] = self.load_sets_metadata()
        
        # Reload inventories from disk
        session_state["sets_inventories_cache"] = self.load_all_inventories()

    def search_parts(self, part_color_pairs: List[Tuple[str, str]], 
                    selected_sets: Optional[List[str]] = None,
                    inventories_cache: Optional[Dict[str, Dict]] = None) -> Dict[Tuple[str, str], List[Dict]]:
        """
        Search for specific part/color combinations in set inventories.
        
        This method searches through cached set inventories to find matching parts
        with specific colors. Only exact part number + color matches are returned.
        
        Args:
            part_color_pairs: List of (part_number, color) tuples to search for.
                            Color can be either color name (str) or color ID (int).
            selected_sets: Optional list of set numbers to search in.
                         If None, searches all sets with fetched inventories.
            inventories_cache: Optional pre-loaded inventories cache from session state.
                             If None, will load from disk.
            
        Returns:
            Dictionary mapping (part_number, color_name) tuples to lists of location dictionaries.
            Each location dictionary contains:
                - location: Formatted as "Set {set_number} - {set_name}"
                - quantity: Quantity available in that set
                - set_number: The set number
                - set_name: The set name
                - is_spare: Whether this is a spare part
        
        Example:
            {
                ("3001", "White"): [
                    {
                        "location": "Set 31147-1 - Retro Camera",
                        "quantity": 4,
                        "set_number": "31147-1",
                        "set_name": "Retro Camera",
                        "is_spare": False
                    }
                ]
            }
        """
        # Load sets metadata to determine which sets to search
        all_sets = self.load_sets_metadata()
        
        # Filter to only sets with fetched inventories
        sets_to_search = [
            s for s in all_sets 
            if s.get("inventory_fetched", False)
        ]
        
        # Further filter by selected_sets if provided
        if selected_sets is not None:
            sets_to_search = [
                s for s in sets_to_search 
                if s["set_number"] in selected_sets
            ]
        
        # Build results dictionary
        results = {}
        
        # Convert part_color_pairs to set for O(1) lookup
        # Normalize colors to strings for comparison
        search_set = set()
        for part_num, color in part_color_pairs:
            search_set.add((str(part_num), str(color)))
        
        # Search through each set's inventory
        for set_data in sets_to_search:
            set_number = set_data["set_number"]
            set_name = set_data.get("set_name", set_number)
            
            # Load inventory from cache or disk
            if inventories_cache and set_number in inventories_cache:
                inventory = inventories_cache[set_number]
            else:
                inventory = self.load_inventory(set_number)
            
            if not inventory:
                continue
            
            # Search for matching parts in this set
            for part in inventory.get("parts", []):
                part_num = str(part.get("part_num", ""))
                color_name = str(part.get("color_name", "Unknown"))
                
                # Check if this part/color combination is in our search list
                if (part_num, color_name) not in search_set:
                    continue
                
                # Extract part details
                quantity = part.get("quantity", 0)
                is_spare = part.get("is_spare", False)
                
                # Create key tuple
                key = (part_num, color_name)
                
                # Create location entry
                location_entry = {
                    "location": f"Set {set_number} - {set_name}",
                    "quantity": quantity,
                    "set_number": set_number,
                    "set_name": set_name,
                    "is_spare": is_spare
                }
                
                # Add to results
                if key not in results:
                    results[key] = []
                results[key].append(location_entry)
        
        return results
