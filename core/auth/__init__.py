# core/auth/__init__.py
"""
Authentication and security module.

Handles user authentication, session management, API key storage,
and security utilities including audit logging and input validation.
"""

from .auth import AuthManager
from .security import (
    AuditLogger,
    SessionTimeoutManager,
    sanitize_html,
    sanitize_dataframe_for_display,
    validate_image_file,
    validate_csv_file,
    set_secure_file_permissions
)
from .api_keys import save_api_key, load_api_key, delete_api_key

__all__ = [
    'AuthManager',
    'AuditLogger',
    'SessionTimeoutManager',
    'sanitize_html',
    'sanitize_dataframe_for_display',
    'validate_image_file',
    'validate_csv_file',
    'set_secure_file_permissions',
    'save_api_key',
    'load_api_key',
    'delete_api_key',
]
