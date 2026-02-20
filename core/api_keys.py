# core/api_keys.py
"""
API key storage module for Rebrickable API keys.

This module provides secure storage and retrieval of Rebrickable API keys
in the user's data directory.
"""

from pathlib import Path
from typing import Optional


def save_api_key(user_data_dir: Path, api_key: str) -> None:
    """
    Save Rebrickable API key to user's directory.
    
    The API key is stored in a plain text file at:
    user_data/{username}/rebrickable_api_key.txt
    
    Args:
        user_data_dir: Path to user's data directory
        api_key: API key string to save
        
    Raises:
        ValueError: If api_key is empty or None
        IOError: If file cannot be written
    """
    if not api_key or not api_key.strip():
        raise ValueError("API key cannot be empty")
    
    # Ensure the user data directory exists
    user_data_dir.mkdir(parents=True, exist_ok=True)
    
    # Define the API key file path
    api_key_file = user_data_dir / "rebrickable_api_key.txt"
    
    # Write the API key to the file
    try:
        api_key_file.write_text(api_key.strip(), encoding="utf-8")
    except Exception as e:
        raise IOError(f"Failed to save API key: {e}")


def load_api_key(user_data_dir: Path) -> Optional[str]:
    """
    Load Rebrickable API key from user's directory.
    
    Args:
        user_data_dir: Path to user's data directory
        
    Returns:
        API key string if found, None if file doesn't exist or is empty
    """
    api_key_file = user_data_dir / "rebrickable_api_key.txt"
    
    # Check if the file exists
    if not api_key_file.exists():
        return None
    
    # Read and return the API key
    try:
        api_key = api_key_file.read_text(encoding="utf-8").strip()
        return api_key if api_key else None
    except Exception:
        # If there's any error reading the file, return None
        return None


def delete_api_key(user_data_dir: Path) -> None:
    """
    Delete stored API key from user's directory.
    
    Args:
        user_data_dir: Path to user's data directory
        
    Note:
        This function does not raise an error if the file doesn't exist.
    """
    api_key_file = user_data_dir / "rebrickable_api_key.txt"
    
    # Delete the file if it exists
    if api_key_file.exists():
        try:
            api_key_file.unlink()
        except Exception:
            # Silently ignore errors during deletion
            pass
