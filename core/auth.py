# core/auth.py
"""
Authentication module for multi-user support
"""
import streamlit as st
import yaml
from yaml.loader import SafeLoader
import streamlit_authenticator as stauth
from pathlib import Path
import bcrypt
import json
from datetime import datetime

class AuthManager:
    def __init__(self, config_path: Path):
        self.config_path = config_path
        
        # Initialize config if it doesn't exist
        if not self.config_path.exists():
            self._create_default_config()
        
        # Load config
        with open(self.config_path, 'r') as file:
            self.config = yaml.load(file, Loader=SafeLoader)
        
        # Create authenticator ONCE
        self.authenticator = stauth.Authenticate(
            self.config['credentials'],
            self.config['cookie']['name'],
            self.config['cookie']['key'],
            self.config['cookie']['expiry_days']
        )

    def _create_default_config(self):
        """Create a default configuration file with demo user"""
        hashed_password = bcrypt.hashpw(
            'demo123'.encode('utf-8'),
            bcrypt.gensalt()
        ).decode('utf-8')

        default_config = {
            'credentials': {
                'usernames': {
                    'demo': {
                        'email': 'demo@example.com',
                        'name': 'Demo User',
                        'password': hashed_password
                    }
                }
            },
            'cookie': {
                'name': 'rebrickable_storage_cookie',
                'key': 'rebrickable_storage_secret_key_12345',
                'expiry_days': 30
            },
            'preauthorized': {
                'emails': []
            }
        }

        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w') as file:
            yaml.dump(default_config, file)

    def register_user(self):
        try:
            email, username, name = self.authenticator.register_user(
                merge_username_email=True,
                password_hint=False,
                captcha=False,
                clear_on_submit=False
            )
            if email:
                st.success("User registered successfully")

                # Save updated config
                with open(self.config_path, 'w') as file:
                    yaml.dump(self.config, file)

        except Exception as e:
            st.error(f"Registration failed: {e}")

    def logout(self):
        self.authenticator.logout()

    def save_user_session(self, username: str, session_data: dict, user_data_dir: Path):
        user_path = user_data_dir / username
        session_file = user_path / "session_data.json"

        serializable_data = {
            'found_counts': {str(k): v for k, v in session_data.get('found_counts', {}).items()},
            'locations_index': session_data.get('locations_index', {}),
            'last_updated': datetime.now().isoformat()
        }

        user_path.mkdir(parents=True, exist_ok=True)
        with open(session_file, 'w') as f:
            json.dump(serializable_data, f, indent=2)

    def load_user_session(self, username: str, user_data_dir: Path) -> dict:
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
                return data
        return {}

    def reset_password(self):
        try:
            username = st.session_state.get("username")
            if username and self.authenticator.reset_password(username):
                st.success("Password modified successfully")
                with open(self.config_path, 'w') as file:
                    yaml.dump(self.config, file)
        except Exception as e:
            st.error(f"Password reset failed: {e}")
