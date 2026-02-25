# core/data/__init__.py
"""
Data processing and management module.

Handles CSV processing, color data, color similarity algorithms,
and LEGO set collection management.
"""

from .preprocess import (
    sanitize_and_validate,
    load_wanted_files,
    load_collection_files,
    merge_wanted_collection,
    get_collection_parts_tuple,
    get_collection_parts_set
)
from .colors import load_colors, build_color_lookup, render_color_cell
from .color_similarity import (
    rgb_to_lab,
    calculate_color_distance,
    build_color_similarity_matrix,
    get_similar_colors,
    find_alternative_colors_for_parts
)
from .sets import SetsManager

__all__ = [
    'sanitize_and_validate',
    'load_wanted_files',
    'load_collection_files',
    'merge_wanted_collection',
    'get_collection_parts_tuple',
    'get_collection_parts_set',
    'load_colors',
    'build_color_lookup',
    'render_color_cell',
    'rgb_to_lab',
    'calculate_color_distance',
    'build_color_similarity_matrix',
    'get_similar_colors',
    'find_alternative_colors_for_parts',
    'SetsManager',
]
