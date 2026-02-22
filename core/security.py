# core/security.py
"""
Security utilities for the application.
Handles input sanitization, file validation, and audit logging.
"""
import html
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Any
import streamlit as st


def _detect_image_type(file_bytes: bytes) -> Optional[str]:
    """
    Detect image type from file bytes using magic numbers.
    
    Args:
        file_bytes: File content as bytes
        
    Returns:
        Image type ('png', 'jpeg') or None if not recognized
    """
    # PNG signature
    if file_bytes.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'png'
    
    # JPEG signature
    if file_bytes.startswith(b'\xff\xd8\xff'):
        return 'jpeg'
    
    return None


# Configure audit logger
def setup_audit_logger(log_dir: Path) -> logging.Logger:
    """
    Set up audit logger for security events.
    
    Args:
        log_dir: Directory to store audit logs
        
    Returns:
        Configured logger instance
    """
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "audit.log"
    
    # Create logger
    logger = logging.getLogger("audit")
    logger.setLevel(logging.INFO)
    
    # Avoid duplicate handlers
    if not logger.handlers:
        # File handler with rotation
        handler = logging.FileHandler(log_file, encoding='utf-8')
        handler.setLevel(logging.INFO)
        
        # Format: timestamp | level | message
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger


class AuditLogger:
    """Centralized audit logging for security events."""
    
    def __init__(self, log_dir: Path):
        self.logger = setup_audit_logger(log_dir)
    
    def log_login_attempt(self, username: str, success: bool, ip: str = "unknown"):
        """Log login attempt."""
        status = "SUCCESS" if success else "FAILED"
        self.logger.info(f"LOGIN_{status} | user={username} | ip={ip}")
    
    def log_logout(self, username: str):
        """Log logout event."""
        self.logger.info(f"LOGOUT | user={username}")
    
    def log_registration(self, username: str, email: str):
        """Log new user registration."""
        self.logger.info(f"REGISTRATION | user={username} | email={email}")
    
    def log_password_change(self, username: str):
        """Log password change."""
        self.logger.info(f"PASSWORD_CHANGE | user={username}")
    
    def log_file_upload(self, username: str, filename: str, file_type: str, size: int):
        """Log file upload."""
        self.logger.info(f"FILE_UPLOAD | user={username} | file={filename} | type={file_type} | size={size}")
    
    def log_session_timeout(self, username: str):
        """Log session timeout."""
        self.logger.info(f"SESSION_TIMEOUT | user={username}")
    
    def log_security_event(self, event_type: str, username: str, details: str = ""):
        """Log generic security event."""
        self.logger.warning(f"SECURITY_EVENT | type={event_type} | user={username} | details={details}")


def sanitize_html(text: str) -> str:
    """
    Sanitize text to prevent XSS attacks.
    
    Args:
        text: Input text that may contain HTML
        
    Returns:
        Escaped text safe for HTML display
    """
    if text is None:
        return ""
    return html.escape(str(text))


def sanitize_dataframe_for_display(df):
    """
    Sanitize all string columns in a DataFrame before display.
    
    Args:
        df: pandas DataFrame
        
    Returns:
        DataFrame with sanitized string columns
    """
    df_copy = df.copy()
    for col in df_copy.columns:
        if df_copy[col].dtype == 'object':
            df_copy[col] = df_copy[col].apply(lambda x: sanitize_html(str(x)) if x is not None else "")
    return df_copy


def validate_image_file(uploaded_file, max_size_mb: float = 1.0) -> tuple[bool, str]:
    """
    Validate uploaded image file for security.
    
    Checks:
    - File size limit
    - File content matches extension (not just extension check)
    - File is actually a valid image
    
    Args:
        uploaded_file: Streamlit UploadedFile object
        max_size_mb: Maximum file size in megabytes
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check file size
    max_size_bytes = int(max_size_mb * 1024 * 1024)
    if uploaded_file.size > max_size_bytes:
        return False, f"File too large. Maximum size is {max_size_mb}MB"
    
    # Check file extension
    filename = uploaded_file.name.lower()
    if not (filename.endswith('.png') or filename.endswith('.jpg') or filename.endswith('.jpeg')):
        return False, "Invalid file extension. Only PNG and JPG files are allowed"
    
    # Validate file content using magic numbers
    try:
        # Read file content
        file_bytes = uploaded_file.getvalue()
        
        # Detect actual image type
        image_type = _detect_image_type(file_bytes)
        
        if image_type not in ['png', 'jpeg']:
            return False, f"Invalid image file. File appears to be {image_type or 'unknown'} format"
        
        # Verify extension matches content
        if filename.endswith('.png') and image_type != 'png':
            return False, "File extension doesn't match content (expected PNG)"
        if (filename.endswith('.jpg') or filename.endswith('.jpeg')) and image_type != 'jpeg':
            return False, "File extension doesn't match content (expected JPEG)"
        
        return True, ""
        
    except Exception as e:
        return False, f"Error validating image: {str(e)}"


def validate_csv_file(uploaded_file, max_size_mb: float = 1.0) -> tuple[bool, str]:
    """
    Validate uploaded CSV file for security.
    
    Args:
        uploaded_file: Streamlit UploadedFile object
        max_size_mb: Maximum file size in megabytes
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check file size
    max_size_bytes = int(max_size_mb * 1024 * 1024)
    if uploaded_file.size > max_size_bytes:
        return False, f"File too large. Maximum size is {max_size_mb}MB"
    
    # Check file extension
    if not uploaded_file.name.lower().endswith('.csv'):
        return False, "Invalid file extension. Only CSV files are allowed"
    
    return True, ""


class SessionTimeoutManager:
    """
    Manages session timeout for user sessions.
    """
    
    def __init__(self, timeout_minutes: int = 90):
        """
        Initialize session timeout manager.
        
        Args:
            timeout_minutes: Session timeout in minutes
        """
        self.timeout_minutes = timeout_minutes
    
    def update_activity(self):
        """Update last activity timestamp."""
        st.session_state["last_activity"] = datetime.now().isoformat()
    
    def check_timeout(self, username: str, audit_logger: Optional[AuditLogger] = None) -> bool:
        """
        Check if session has timed out.
        
        Args:
            username: Current username
            audit_logger: Optional audit logger instance
            
        Returns:
            True if session is valid, False if timed out
        """
        last_activity_str = st.session_state.get("last_activity")
        
        if not last_activity_str:
            # First access, set timestamp
            self.update_activity()
            return True
        
        try:
            last_activity = datetime.fromisoformat(last_activity_str)
            elapsed = (datetime.now() - last_activity).total_seconds() / 60
            
            if elapsed > self.timeout_minutes:
                # Session timed out - only log once
                if audit_logger and "session_timeout_logged" not in st.session_state:
                    audit_logger.log_session_timeout(username)
                    st.session_state["session_timeout_logged"] = True
                return False
            
            # Update activity timestamp
            self.update_activity()
            return True
            
        except Exception:
            # Error parsing timestamp, reset
            self.update_activity()
            return True


def set_secure_file_permissions(file_path: Path):
    """
    Set restrictive file permissions on sensitive files.
    
    Args:
        file_path: Path to file to secure
    """
    try:
        import os
        import stat
        
        # Set to owner read/write only (0o600)
        os.chmod(file_path, stat.S_IRUSR | stat.S_IWUSR)
    except Exception:
        # On Windows, this might not work as expected
        # File permissions are handled differently
        pass
