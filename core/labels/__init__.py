# core/labels/__init__.py
"""
Label generation module.

Handles label organization, ZIP generation for printable labels,
and LBX file operations and merging.
"""

from .labels import (
    organize_labels_by_location,
    generate_collection_labels_zip
)
from .lbx_merger import LbxMerger

__all__ = [
    'organize_labels_by_location',
    'generate_collection_labels_zip',
    'LbxMerger',
]
