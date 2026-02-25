# core/state/__init__.py
"""
State management module.

Handles application state, progress tracking, and business logic
for finding wanted parts.
"""

from .progress import render_summary_table
from .find_wanted_parts import (
    get_unfound_parts,
    merge_set_results,
    render_missing_parts_by_set,
    render_set_search_section
)

__all__ = [
    'render_summary_table',
    'get_unfound_parts',
    'merge_set_results',
    'render_missing_parts_by_set',
    'render_set_search_section',
]
