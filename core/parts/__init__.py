# core/parts/__init__.py
"""
Parts management module.

Handles part number mapping between BrickArchitect and Rebrickable,
custom mapping rules, and part image fetching and caching.
"""

from .mapping import (
    EnhancedMapping,
    read_ba_mapping_from_excel_bytes,
    load_ba_part_names,
    load_ba_mapping,
    count_parts_in_mapping,
    build_ba_to_rb_mapping,
    build_rb_to_similar_parts_mapping
)
from .custom_mapping import (
    create_default_custom_mapping_csv,
    load_custom_mapping_csv,
    save_custom_mapping_csv,
    match_wildcard_pattern,
    build_custom_mapping_dict,
    apply_custom_mapping
)
from .images import (
    precompute_location_images,
    fetch_image_bytes,
    get_cached_images_batch,
    fetch_wanted_part_images,
    save_user_uploaded_image,
    create_custom_images_zip,
    count_custom_images,
    upload_custom_images,
    delete_all_custom_images,
    clear_unavailable_images_cache,
    get_unavailable_images_count
)

__all__ = [
    'EnhancedMapping',
    'read_ba_mapping_from_excel_bytes',
    'load_ba_part_names',
    'load_ba_mapping',
    'count_parts_in_mapping',
    'build_ba_to_rb_mapping',
    'build_rb_to_similar_parts_mapping',
    'create_default_custom_mapping_csv',
    'load_custom_mapping_csv',
    'save_custom_mapping_csv',
    'match_wildcard_pattern',
    'build_custom_mapping_dict',
    'apply_custom_mapping',
    'precompute_location_images',
    'fetch_image_bytes',
    'get_cached_images_batch',
    'fetch_wanted_part_images',
    'save_user_uploaded_image',
    'create_custom_images_zip',
    'count_custom_images',
    'upload_custom_images',
    'delete_all_custom_images',
    'clear_unavailable_images_cache',
    'get_unavailable_images_count',
]
