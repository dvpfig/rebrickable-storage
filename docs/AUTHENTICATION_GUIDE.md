# Multi-User Authentication Guide

## Overview

This application now supports multiple users with individual authentication and data isolation. Each user can:
- Register their own account
- Upload their own collection files
- Track their progress independently
- Save and load their session data

## Features

### 1. User Authentication
- **Login**: Secure username/password authentication
- **Registration**: New users can create accounts
- **Session Management**: 30-day cookie-based sessions
- **Password Reset**: Users can change their passwords

### 2. Data Isolation
Each user has their own:
- Collection directory: `user_data/{username}/collection/`
- Session data: `user_data/{username}/session_data.json`
- Found counts tracking
- Location index

### 3. Progress Persistence
Users can:
- **Save Progress**: Stores current found_counts and locations_index
- **Load Progress**: Restores previously saved session
- Data persists between sessions and browser refreshes

## Getting Started

### First Time Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the Application**:
   ```bash
   streamlit run app.py
   ```

3. **Default Demo User**:
   - Username: `demo`
   - Password: `demo123`

### Creating New Users

1. Navigate to the **Register** tab on the login page
2. Enter:
   - Email address
   - Username (unique identifier)
   - Full name
   - Password
   - Password confirmation
3. Click "Register user"
4. Login with your new credentials

## File Structure

```
rebrickable-storage/
├── app.py                          # Main application with auth
├── core/
│   ├── auth.py                     # Authentication module
│   └── ...
├── resources/
│   └── auth_config.yaml            # User credentials (auto-generated)
└── user_data/                      # User-specific data (auto-generated)
    ├── {username1}/
    │   ├── collection/             # User's uploaded collections
    │   └── session_data.json       # Saved progress
    └── {username2}/
        ├── collection/
        └── session_data.json
```

## Security Considerations

### Current Implementation (Development)
- Passwords are hashed using bcrypt
- Session data stored locally as JSON
- Cookie-based authentication with 30-day expiry
- Config file stored in resources/auth_config.yaml

### Production Recommendations

1. **Change Cookie Secret Key**:
   - Edit `resources/auth_config.yaml`
   - Change `cookie.key` to a strong random string

2. **Use Environment Variables**:
   ```python
   import os
   cookie_key = os.environ.get('COOKIE_SECRET_KEY', 'default_key')
   ```

3. **Database Storage**:
   - Replace YAML file with PostgreSQL/MongoDB
   - Use proper user management system

4. **HTTPS Only**:
   - Deploy with SSL/TLS certificates
   - Set secure cookie flags

5. **Enhanced Features**:
   - Email verification
   - Password complexity requirements
   - Rate limiting on login attempts
   - Two-factor authentication

## Usage Examples

### Workflow for a User

1. **Login**:
   - Enter username and password
   - Click "Login"

2. **Upload Files**:
   - Upload wanted parts CSVs
   - Upload collection files
   - Click "Start Processing"

3. **Track Progress**:
   - Mark parts as found
   - Use location-specific controls

4. **Save Work**:
   - Click "💾 Save Progress" in sidebar
   - Progress is saved to your user directory

5. **Resume Later**:
   - Login again
   - Click "📂 Load Progress" to restore session
   - Continue where you left off

6. **Logout**:
   - Click "Logout" in sidebar
   - Your data remains safe and isolated

## Concurrent Users

The application supports multiple users running simultaneously:
- Each user sees only their own data
- Session states are isolated
- No data conflicts between users
- Independent file uploads and processing

## Troubleshooting

### Can't Login
- Check username/password spelling
- Ensure account is registered
- Check `resources/auth_config.yaml` exists

### Lost Progress
- Click "📂 Load Progress" to restore
- Check `user_data/{username}/session_data.json` exists

### Registration Fails
- Username might already exist
- Check for error messages
- Ensure all fields are filled correctly

### Data Not Isolated
- Verify correct username in sidebar
- Check user_data directory structure
- Restart the application

## API Reference

### AuthManager Class

```python
from core.auth import AuthManager

# Initialize
auth_manager = AuthManager(config_path, user_data_dir)

# Login
authenticated = auth_manager.login()

# Get user directory
user_path = auth_manager.get_user_data_path(username)

# Save session
auth_manager.save_user_session(username, session_data)

# Load session
session_data = auth_manager.load_user_session(username)

# Logout
auth_manager.logout()
```

## Migration from Single-User

If you had a previous single-user version:

1. Create a user account
2. Copy old collection files to `user_data/{username}/collection/`
3. Login and start processing

## Development Notes

### Adding New Session Data

To add new fields to session persistence:

1. Edit `core/auth.py` in `save_user_session()`:
   ```python
   serializable_data = {
       'found_counts': ...,
       'locations_index': ...,
       'your_new_field': session_data.get('your_new_field', default),
       ...
   }
   ```

2. Edit `load_user_session()` to deserialize the field

### Custom Authentication Logic

Extend `AuthManager` class in `core/auth.py`:
```python
def custom_validation(self, username: str) -> bool:
    # Add your custom logic
    pass
```

## Support

For issues or questions:
1. Check this guide
2. Review error messages in the UI
3. Check application logs
4. Verify file permissions in user_data directory
