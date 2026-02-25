# core/auth.py
"""
Authentication module for multi-user support with enhanced security
"""
import streamlit as st
import yaml
from yaml.loader import SafeLoader
import streamlit_authenticator as stauth
from pathlib import Path
import bcrypt
import json
import os
from datetime import datetime
from typing import Optional
from core.auth.security import AuditLogger, SessionTimeoutManager, set_secure_file_permissions

class AuthManager:
    # Bcrypt rounds for password hashing (higher = more secure but slower)
    BCRYPT_ROUNDS = 12
    
    def __init__(self, config_path: Path, audit_log_dir: Optional[Path] = None):
        self.config_path = config_path
        
        # Initialize audit logger
        if audit_log_dir:
            self.audit_logger = AuditLogger(audit_log_dir)
        else:
            self.audit_logger = None
        
        # Initialize session timeout manager (90 minutes)
        timeout_minutes = int(os.getenv('SESSION_TIMEOUT_MINUTES', '90'))
        self.session_timeout = SessionTimeoutManager(timeout_minutes)
        
        # Initialize config if it doesn't exist
        if not self.config_path.exists():
            self._create_default_config()
        
        # Set secure file permissions on config
        set_secure_file_permissions(self.config_path)
        
        # Load config with environment variable overrides
        with open(self.config_path, 'r') as file:
            self.config = yaml.load(file, Loader=SafeLoader)
        
        # Override cookie settings from environment variables
        cookie_key = os.getenv('COOKIE_SECRET_KEY')
        if not cookie_key:
            # In production, this should fail. For development, use config value
            if os.getenv('APP_ENV') == 'production':
                raise ValueError("COOKIE_SECRET_KEY environment variable is required in production")
            cookie_key = self.config['cookie']['key']
        
        cookie_name = os.getenv('COOKIE_NAME', self.config['cookie']['name'])
        cookie_expiry = int(os.getenv('COOKIE_EXPIRY_DAYS', str(self.config['cookie']['expiry_days'])))
        
        # Create authenticator ONCE with environment-based config
        self.authenticator = stauth.Authenticate(
            self.config['credentials'],
            cookie_name,
            cookie_key,
            cookie_expiry
        )

    def _create_default_config(self):
        """
        Create a default configuration file with demo user.
        
        Creates auth_config.yaml with a demo user account and secure settings.
        Uses environment variables for sensitive configuration.
        """
        hashed_password = bcrypt.hashpw(
            'demo123'.encode('utf-8'),
            bcrypt.gensalt(rounds=self.BCRYPT_ROUNDS)
        ).decode('utf-8')

        # Use environment variable for cookie key, fallback to default for development
        cookie_key = os.getenv('COOKIE_SECRET_KEY', 'rebrickable_storage_secret_key_12345')
        
        default_config = {
            'credentials': {
                'usernames': {
                    'demo': {
                        'email': 'demo@example.com',
                        'name': 'Demo User',
                        'password': hashed_password,
                        'failed_login_attempts': 0,
                        'locked_until': None
                    }
                }
            },
            'cookie': {
                'name': os.getenv('COOKIE_NAME', 'rebrickable_storage_cookie'),
                'key': cookie_key,
                'expiry_days': int(os.getenv('COOKIE_EXPIRY_DAYS', '30'))
            },
            'preauthorized': {
                'emails': []
            }
        }

        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w') as file:
            yaml.dump(default_config, file)
        
        # Set secure permissions
        set_secure_file_permissions(self.config_path)

    def check_session_timeout(self, username: str) -> bool:
        """
        Check if session has timed out.
        
        Args:
            username: Current username
            
        Returns:
            True if session is valid, False if timed out
        """
        return self.session_timeout.check_timeout(username, self.audit_logger)
    
    def _check_rate_limit(self, username: str) -> tuple[bool, str]:
        """
        Check if user has exceeded login rate limit.
        
        Args:
            username: Username attempting to login
            
        Returns:
            Tuple of (is_allowed, error_message)
        """
        if username not in self.config['credentials']['usernames']:
            return True, ""
        
        user_data = self.config['credentials']['usernames'][username]
        failed_attempts = user_data.get('failed_login_attempts', 0)
        locked_until = user_data.get('locked_until')
        
        # Check if account is locked
        if locked_until:
            try:
                locked_until_dt = datetime.fromisoformat(locked_until)
                if datetime.now() < locked_until_dt:
                    remaining = (locked_until_dt - datetime.now()).total_seconds() / 60
                    return False, f"Account locked. Try again in {int(remaining)} minutes"
                else:
                    # Lock expired, reset
                    user_data['failed_login_attempts'] = 0
                    user_data['locked_until'] = None
                    self._save_config()
            except Exception:
                pass
        
        # Check failed attempts (lock after 5 failed attempts)
        if failed_attempts >= 5:
            # Lock account for 15 minutes
            from datetime import timedelta
            locked_until = (datetime.now() + timedelta(minutes=15)).isoformat()
            user_data['locked_until'] = locked_until
            self._save_config()
            
            if self.audit_logger:
                self.audit_logger.log_security_event(
                    "ACCOUNT_LOCKED",
                    username,
                    f"Too many failed login attempts ({failed_attempts})"
                )
            
            return False, "Too many failed login attempts. Account locked for 15 minutes"
        
        return True, ""
    
    def _record_login_attempt(self, username: str, success: bool):
        """
        Record login attempt for rate limiting and audit logging.
        
        Args:
            username: Username that attempted login
            success: Whether login was successful
        """
        if username not in self.config['credentials']['usernames']:
            return
        
        user_data = self.config['credentials']['usernames'][username]
        
        if success:
            # Reset failed attempts on successful login
            user_data['failed_login_attempts'] = 0
            user_data['locked_until'] = None
            if self.audit_logger:
                self.audit_logger.log_login_attempt(username, True)
        else:
            # Increment failed attempts
            failed_attempts = user_data.get('failed_login_attempts', 0) + 1
            user_data['failed_login_attempts'] = failed_attempts
            if self.audit_logger:
                self.audit_logger.log_login_attempt(username, False)
        
        self._save_config()
    
    def _save_config(self):
        """
        Save configuration to file with secure permissions.
        """
        with open(self.config_path, 'w') as file:
            yaml.dump(self.config, file)
        set_secure_file_permissions(self.config_path)

    def register_user(self):
        """
        Handle user registration with validation and audit logging.
        
        Creates a new user account with rate limiting fields initialized.
        Displays success/error messages in the UI.
        """
        try:
            email, username, name = self.authenticator.register_user(
                merge_username_email=True,
                password_hint=False,
                captcha=False,
                clear_on_submit=False
            )
            if email:
                st.success("User registered successfully")
                
                # Initialize rate limiting fields for new user
                if username in self.config['credentials']['usernames']:
                    self.config['credentials']['usernames'][username]['failed_login_attempts'] = 0
                    self.config['credentials']['usernames'][username]['locked_until'] = None

                # Save updated config
                self._save_config()
                
                # Log registration
                if self.audit_logger:
                    self.audit_logger.log_registration(username, email)

        except Exception as e:
            st.error(f"Registration failed: {e}")

    def logout(self, skip_audit_log: bool = False):
        """
        Handle user logout with audit logging.
        
        Args:
            skip_audit_log: If True, skip audit logging (used for timeout scenarios)
        """
        username = st.session_state.get("username")
        was_authenticated = st.session_state.get("authentication_status") is True
        
        # Call the authenticator's logout (renders button and handles click)
        self.authenticator.logout()
        
        # Only log if user actually logged out (status changed from True to False/None)
        is_authenticated = st.session_state.get("authentication_status") is True
        if was_authenticated and not is_authenticated and username and self.audit_logger and not skip_audit_log:
            self.audit_logger.log_logout(username)

    def save_user_session(self, username: str, session_data: dict, user_data_dir: Path):
        """
        Save user session data to JSON file.
        
        Args:
            username: Username for the session
            session_data: Dictionary containing session state data
            user_data_dir: Path to user data directory
        """
        user_path = user_data_dir / username
        session_file = user_path / "session_data.json"

        serializable_data = {
            'found_counts': {str(k): v for k, v in session_data.get('found_counts', {}).items()},
            'locations_index': session_data.get('locations_index', {}),
            'sets_metadata': session_data.get('sets_metadata'),
            'sets_inventories_cache': session_data.get('sets_inventories_cache', {}),
            'last_updated': datetime.now().isoformat()
        }

        user_path.mkdir(parents=True, exist_ok=True)
        with open(session_file, 'w') as f:
            json.dump(serializable_data, f, indent=2)

    def load_user_session(self, username: str, user_data_dir: Path) -> dict:
        """
        Load user session data from JSON file.
        
        Args:
            username: Username for the session
            user_data_dir: Path to user data directory
            
        Returns:
            dict: Session data dictionary, or empty dict if file doesn't exist
        """
        user_path = user_data_dir / username
        session_file = user_path / "session_data.json"

        if session_file.exists():
            with open(session_file, 'r') as f:
                data = json.load(f)
                if 'found_counts' in data:
                    parsed = {}
                    for k, v in data['found_counts'].items():
                        parsed[eval(k)] = v
                    data['found_counts'] = parsed
                # Sets data is already in the correct format (lists/dicts)
                # No need to parse sets_metadata or sets_inventories_cache
                return data
        return {}

    def reset_password(self):
        """
        Handle password reset for authenticated user with audit logging.
        
        Displays success/error messages in the UI.
        """
        try:
            username = st.session_state.get("username")
            if username and self.authenticator.reset_password(username):
                st.success("Password modified successfully")
                self._save_config()
                
                # Log password change
                if self.audit_logger:
                    self.audit_logger.log_password_change(username)
        except Exception as e:
            st.error(f"Password reset failed: {e}")
