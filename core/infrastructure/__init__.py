# core/infrastructure/__init__.py
"""
Infrastructure and utilities module.

Handles path resolution, session state management,
and other foundational services.
"""

from .paths import (
    Paths,
    init_paths,
    save_uploadedfiles,
    manage_default_collection
)
from .session import ensure_session_state_keys, short_key

__all__ = [
    'Paths',
    'init_paths',
    'save_uploadedfiles',
    'manage_default_collection',
    'ensure_session_state_keys',
    'short_key',
]
