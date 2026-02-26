# core/custom_mapping.py
import pandas as pd
import re
from pathlib import Path
import streamlit as st


def create_default_custom_mapping_csv(csv_path: Path):
    """
    Create a default custom mapping CSV file with all mapping rules.
    Includes the previously hardcoded generalized rules.

    Wildcard patterns:
    - * matches any single digit
    - ** matches any sequence of digits
    - ? matches any single letter

    Args:
        csv_path: Path where the CSV file should be created
    """
    default_data = {
        "BA partnum": [
            "973",
            "73200",
            "73141",
            "73161",
            "3626pb"
        ],
        "Part description": [
            "Minifig torso with color codes",
            "Minifig legs with color codes - any 970c{number} maps to 970c{number}",
            "Minidoll torso, girl",
            "Minidoll torso, boy",
            "Minifig face printed"
        ],
        "RB pattern 1": [
            "973c**h**pr**",
            "970?**pr**",
            "92816c**pr**",
            "92815c**pr**",
            "3626?pr**"
        ],
        "RB pattern 2": [
            "973g**c**h**pr**",
            "970l**r**pr**",
            "",
            "",
            "28621pr**"
        ],
        "RB pattern 3": [
            "973?**pr**",
            "970?**",
            "",
            "",
            ""
        ],
        "RB pattern 4": [
            "",
            "",
            "",
            "",
            ""
        ]
    }

    df = pd.DataFrame(default_data)
    df.to_csv(csv_path, index=False)



def load_custom_mapping_csv(csv_path: Path) -> pd.DataFrame:
    """
    Load custom mapping CSV file. Create default if it doesn't exist.
    
    Args:
        csv_path: Path to the custom mapping CSV file
    
    Returns:
        pd.DataFrame: Custom mapping data
    """
    if not csv_path.exists():
        create_default_custom_mapping_csv(csv_path)
    
    try:
        # Read all columns as strings to avoid type issues
        df = pd.read_csv(csv_path, dtype=str)
        
        # Replace NaN with empty strings
        df = df.fillna("")
        
        # Ensure required columns exist
        if "BA partnum" not in df.columns:
            df["BA partnum"] = ""
        if "Part description" not in df.columns:
            df["Part description"] = ""
        if "RB pattern 1" not in df.columns:
            df["RB pattern 1"] = ""
        if "RB pattern 2" not in df.columns:
            df["RB pattern 2"] = ""
        if "RB pattern 3" not in df.columns:
            df["RB pattern 3"] = ""
        if "RB pattern 4" not in df.columns:
            df["RB pattern 4"] = ""
        
        return df
    except Exception as e:
        st.error(f"Error loading custom mapping CSV: {e}")
        return pd.DataFrame(columns=["BA partnum", "Part description", "RB pattern 1", "RB pattern 2", "RB pattern 3", "RB pattern 4"])


def save_custom_mapping_csv(df: pd.DataFrame, csv_path: Path):
    """
    Save custom mapping CSV file.
    
    Args:
        df: DataFrame with custom mapping data
        csv_path: Path where the CSV file should be saved
    """
    try:
        # Ensure all columns are strings and replace NaN with empty strings
        df_to_save = df.copy()
        for col in df_to_save.columns:
            df_to_save[col] = df_to_save[col].astype(str).replace('nan', '').replace('<NA>', '')
        
        df_to_save.to_csv(csv_path, index=False)
    except Exception as e:
        st.error(f"Error saving custom mapping CSV: {e}")




def match_wildcard_pattern(rb_part: str, pattern: str) -> bool:
    """
    Check if an RB part number matches a wildcard pattern.

    Wildcard rules:
    - * matches any single digit (0-9)
    - ** matches any sequence of digits (one or more)
    - ? matches any single letter (a-z, A-Z)

    Examples:
    - "973?**" matches "973c12" (? matches 'c', ** matches '12')
    - "970?**" matches "970a123" (? matches 'a', ** matches '123')
    - "3626?pr****" matches "3626apr1234" (? matches 'a', * matches '1', ** matches '234')

    Args:
        rb_part: RB part number to check
        pattern: Wildcard pattern (e.g., "973?**")

    Returns:
        bool: True if the part matches the pattern
    """
    # Escape special regex characters except * and ?
    # We need to handle these wildcards before escaping
    # Replace wildcards with placeholders first
    pattern = pattern.replace('**', '\x00DOUBLESTAR\x00')
    pattern = pattern.replace('*', '\x00STAR\x00')
    pattern = pattern.replace('?', '\x00QUESTION\x00')
    
    # Now escape all regex special characters
    escaped = re.escape(pattern)
    
    # Replace placeholders with regex patterns
    regex = escaped.replace('\x00DOUBLESTAR\x00', r'\d+')  # ** -> one or more digits
    regex = regex.replace('\x00STAR\x00', r'\d')           # * -> single digit
    regex = regex.replace('\x00QUESTION\x00', r'[a-zA-Z]') # ? -> single letter

    # Anchor the pattern to match the entire string
    regex = f"^{regex}$"

    return bool(re.match(regex, rb_part, re.IGNORECASE))



def build_custom_mapping_dict(df: pd.DataFrame) -> dict:
    """
    Build a mapping dictionary from custom mapping DataFrame.
    Handles both exact matches and wildcard patterns.
    Supports multiple RB pattern columns (RB pattern 1 through RB pattern 4).
    
    Wildcard patterns:
    - * matches any single digit
    - ** matches any sequence of digits
    - ? matches any single letter
    
    Args:
        df: DataFrame with custom mapping data
    
    Returns:
        dict: {
            'exact': {rb_part: ba_part},
            'patterns': [(rb_pattern, ba_part), ...]
        }
    """
    exact_mapping = {}
    pattern_mapping = []
    
    for _, row in df.iterrows():
        ba_part = str(row.get("BA partnum", "")).strip()
        
        # Skip empty BA part
        if not ba_part or ba_part.lower() in ["nan", "none"]:
            continue
        
        # Process all RB pattern columns
        for col_name in ["RB pattern 1", "RB pattern 2", "RB pattern 3", "RB pattern 4"]:
            rb_part = str(row.get(col_name, "")).strip()
            
            # Skip empty RB parts
            if not rb_part or rb_part.lower() in ["nan", "none", ""]:
                continue
            
            # Check if RB part contains wildcards
            if "*" in rb_part or "?" in rb_part:
                pattern_mapping.append((rb_part, ba_part))
            else:
                exact_mapping[rb_part.lower()] = ba_part
    
    return {
        'exact': exact_mapping,
        'patterns': pattern_mapping
    }


def apply_custom_mapping(rb_part: str, custom_mapping: dict) -> str:
    """
    Apply custom mapping to an RB part number.
    
    Priority:
    1. Exact match in custom mapping
    2. Pattern match in custom mapping
    3. Return original part if no match
    
    Args:
        rb_part: RB part number
        custom_mapping: Custom mapping dictionary from build_custom_mapping_dict
    
    Returns:
        str: Mapped BA part number or original RB part
    """
    rb_part_lower = rb_part.lower().strip()
    
    # Check exact matches first
    if rb_part_lower in custom_mapping['exact']:
        return custom_mapping['exact'][rb_part_lower]
    
    # Check pattern matches
    for pattern, ba_part in custom_mapping['patterns']:
        if match_wildcard_pattern(rb_part_lower, pattern):
            return ba_part
    
    # No match found
    return rb_part


