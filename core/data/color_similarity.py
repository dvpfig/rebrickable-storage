# core/color_similarity.py
import pandas as pd
import numpy as np
from streamlit import cache_data


def rgb_to_lab(rgb_hex):
    """
    Convert RGB hex color to LAB color space for perceptual color difference.
    LAB color space is better for human perception of color similarity.
    
    Args:
        rgb_hex: RGB color as hex string (e.g., "FF0000")
    
    Returns:
        tuple: (L, a, b) values in LAB color space
    """
    # Convert hex to RGB
    rgb_hex = rgb_hex.lstrip('#')
    r, g, b = int(rgb_hex[0:2], 16), int(rgb_hex[2:4], 16), int(rgb_hex[4:6], 16)
    
    # Normalize to 0-1
    r, g, b = r / 255.0, g / 255.0, b / 255.0
    
    # Convert to linear RGB
    def to_linear(c):
        if c <= 0.04045:
            return c / 12.92
        else:
            return ((c + 0.055) / 1.055) ** 2.4
    
    r, g, b = to_linear(r), to_linear(g), to_linear(b)
    
    # Convert to XYZ
    x = r * 0.4124564 + g * 0.3575761 + b * 0.1804375
    y = r * 0.2126729 + g * 0.7151522 + b * 0.0721750
    z = r * 0.0193339 + g * 0.1191920 + b * 0.9503041
    
    # Normalize by D65 white point
    x, y, z = x / 0.95047, y / 1.00000, z / 1.08883
    
    # Convert to LAB
    def f(t):
        if t > 0.008856:
            return t ** (1/3)
        else:
            return (7.787 * t) + (16 / 116)
    
    fx, fy, fz = f(x), f(y), f(z)
    
    L = (116 * fy) - 16
    a = 500 * (fx - fy)
    b = 200 * (fy - fz)
    
    return (L, a, b)


def calculate_color_distance(color1_rgb, color2_rgb, is_trans1=False, is_trans2=False):
    """
    Calculate perceptual color distance using CIEDE2000 approximation.
    
    Args:
        color1_rgb: RGB hex string for first color
        color2_rgb: RGB hex string for second color
        is_trans1: Whether first color is transparent
        is_trans2: Whether second color is transparent
    
    Returns:
        float: Color distance (0 = identical, higher = more different)
    """
    # Penalize transparency mismatch heavily
    if is_trans1 != is_trans2:
        return 1000.0
    
    try:
        lab1 = rgb_to_lab(color1_rgb)
        lab2 = rgb_to_lab(color2_rgb)
        
        # Calculate Delta E (CIE76 - simpler than CIEDE2000 but good enough)
        delta_L = lab1[0] - lab2[0]
        delta_a = lab1[1] - lab2[1]
        delta_b = lab1[2] - lab2[2]
        
        delta_e = np.sqrt(delta_L**2 + delta_a**2 + delta_b**2)
        
        return delta_e
    except Exception:
        return 1000.0


@cache_data(show_spinner=False)
def build_color_similarity_matrix(colors_df):
    """
    Build a matrix of color similarities for all colors.
    
    Args:
        colors_df: DataFrame with color information (id, name, rgb, is_trans)
    
    Returns:
        dict: {color_id: [(similar_color_id, distance), ...]} sorted by distance
    """
    similarity_matrix = {}
    
    # Create list of valid colors
    valid_colors = []
    for _, row in colors_df.iterrows():
        try:
            color_id = int(row.get("id", -1))
            if color_id >= 0:
                valid_colors.append({
                    "id": color_id,
                    "rgb": row.get("rgb", "000000"),
                    "is_trans": bool(row.get("is_trans", False)),
                    "name": row.get("name", "Unknown")
                })
        except Exception:
            continue
    
    # Calculate distances between all color pairs
    for color1 in valid_colors:
        distances = []
        for color2 in valid_colors:
            if color1["id"] != color2["id"]:
                distance = calculate_color_distance(
                    color1["rgb"], 
                    color2["rgb"],
                    color1["is_trans"],
                    color2["is_trans"]
                )
                distances.append((color2["id"], distance, color2["name"]))
        
        # Sort by distance (closest first)
        distances.sort(key=lambda x: x[1])
        similarity_matrix[color1["id"]] = distances
    
    return similarity_matrix


def get_similar_colors(color_id, similarity_matrix, max_distance=50.0):
    """
    Get similar colors within a given distance threshold.
    
    Args:
        color_id: The color ID to find similar colors for
        similarity_matrix: Pre-computed similarity matrix
        max_distance: Maximum color distance to consider (0-100 scale)
    
    Returns:
        list: [(color_id, distance, color_name), ...] of similar colors
    """
    try:
        color_id = int(color_id)
        if color_id not in similarity_matrix:
            return []
        
        similar = []
        for similar_id, distance, name in similarity_matrix[color_id]:
            if distance <= max_distance:
                similar.append((similar_id, distance, name))
        
        return similar
    except Exception:
        return []


def find_alternative_colors_for_parts(
    parts_df, 
    collection_df, 
    similarity_matrix,
    max_distance=50.0
):
    """
    Find alternative colors for parts that are unavailable or insufficient.
    Includes replacement parts in the search.
    
    Args:
        parts_df: DataFrame with wanted parts (Part, Color, Quantity_wanted, Quantity_have, Available, Replacement_parts)
        collection_df: DataFrame with collection (Part, Color, Quantity, Location)
        similarity_matrix: Pre-computed color similarity matrix
        max_distance: Maximum color distance threshold
    
    Returns:
        dict: {(part, original_color, location): [(alt_color_id, alt_color_name, available_qty, distance), ...]}
    """
    alternatives = {}
    
    # Create collection inventory: {(part, color, location): quantity}
    collection_inventory = {}
    for _, row in collection_df.iterrows():
        key = (str(row["Part"]), int(row["Color"]), str(row["Location"]))
        collection_inventory[key] = int(row["Quantity"])
    
    # For each wanted part that's unavailable or insufficient
    for _, row in parts_df.iterrows():
        part = str(row["Part"])
        original_color = int(row["Color"])
        location = str(row["Location"])
        qty_wanted = int(row["Quantity_wanted"])
        qty_have = int(row.get("Quantity_have", 0))
        available = row.get("Available", False)
        
        # Skip if we have enough in the exact color
        if available and qty_have >= qty_wanted:
            continue
        
        # Get replacement parts if available
        replacement_parts_str = row.get("Replacement_parts", "")
        replacement_parts = []
        if replacement_parts_str:
            replacement_parts = [p.strip() for p in str(replacement_parts_str).split(",")]
        
        # Build list of parts to check (original + replacements)
        parts_to_check = [part] + replacement_parts
        
        # Find similar colors
        similar_colors = get_similar_colors(original_color, similarity_matrix, max_distance)
        
        if not similar_colors:
            continue
        
        # Check which similar colors are available in collection for this part or its replacements
        part_alternatives = []
        for alt_color_id, distance, alt_color_name in similar_colors:
            # Check each part variant (original + replacements)
            for check_part in parts_to_check:
                key = (check_part, alt_color_id, location)
                if key in collection_inventory:
                    alt_qty = collection_inventory[key]
                    if alt_qty > 0:
                        # Add note if this is a replacement part
                        display_name = alt_color_name
                        if check_part != part:
                            display_name = f"{alt_color_name} (part {check_part})"
                        
                        part_alternatives.append((
                            alt_color_id,
                            display_name,
                            alt_qty,
                            distance
                        ))
                        break  # Only add once per color (first matching part)
        
        if part_alternatives:
            # Sort by distance (closest colors first)
            part_alternatives.sort(key=lambda x: x[3])
            alternatives[(part, original_color, location)] = part_alternatives
    
    return alternatives
