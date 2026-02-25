# core/external/__init__.py
"""
External API integration module.

Handles integration with external services including Rebrickable API
and download progress management.
"""

from .rebrickable_api import RebrickableAPI, APIError, RateLimitError
from .download_helpers import DownloadCallbacks, create_download_callbacks

__all__ = [
    'RebrickableAPI',
    'APIError',
    'RateLimitError',
    'DownloadCallbacks',
    'create_download_callbacks',
]
