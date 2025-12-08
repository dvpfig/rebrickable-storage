# Authentication Feature Changelog

## Summary

Added multi-user authentication system to support concurrent users with isolated data and session management.

## Changes Made

### New Files

1. **`core/auth.py`** - Authentication module
   - `AuthManager` class for user management
   - User registration and login
   - Password hashing with bcrypt
   - Session save/load functionality
   - User-specific data directory management

2. **`AUTHENTICATION_GUIDE.md`** - Comprehensive authentication documentation
   - Feature overview
   - Usage instructions
   - Security considerations
   - API reference
   - Troubleshooting guide

3. **`INSTALLATION.md`** - Installation and setup guide
   - Step-by-step installation instructions
   - Virtual environment setup
   - Dependency installation
   - Troubleshooting common issues

4. **`test_auth.py`** - Authentication test script
   - Validates auth system setup
   - Tests user directory creation
   - Tests session save/load
   - Provides demo credentials

5. **`.gitignore`** - Git ignore rules
   - Excludes user data
   - Excludes auth config
   - Standard Python ignores

### Modified Files

1. **`app.py`** - Main application
   - Added authentication check at startup
   - Login/Register UI before main app
   - User-specific collection directory
   - Sidebar with user info and controls
   - Save/Load progress buttons
   - Logout functionality
   - Password change option

2. **`requirements.txt`** - Dependencies
   - Added `streamlit-authenticator`
   - Added `pyyaml`
   - Added `bcrypt`

### Auto-Generated Files (Runtime)

1. **`resources/auth_config.yaml`** - User credentials storage
   - Created automatically on first run
   - Contains hashed passwords
   - Cookie configuration
   - Demo user (username: `demo`, password: `demo123`)

2. **`user_data/{username}/`** - User-specific directories
   - Created per user
   - Contains `collection/` for uploaded files
   - Contains `session_data.json` for saved progress

## Features Added

### 1. User Authentication
- Secure login with bcrypt password hashing
- User registration with validation
- 30-day session cookies
- Password reset functionality

### 2. Multi-User Support
- Complete data isolation per user
- Concurrent user sessions
- No data conflicts between users
- Independent file processing

### 3. Session Persistence
- Save progress button (found_counts, locations_index)
- Load progress from previous sessions
- JSON-based session storage
- Automatic user directory creation

### 4. UI Enhancements
- Login/Register tabs on authentication page
- User welcome message in sidebar
- Save/Load progress buttons
- Logout button
- Password change expander

## Technical Details

### Authentication Flow

```
User Access → Login Check → Authenticated?
                              ├─ No  → Show Login/Register
                              └─ Yes → Load User Session
                                       ↓
                                  Show Main App
                                       ↓
                                  User-Specific Data
```

### Data Isolation

Each user has isolated:
- **Collection files**: `user_data/{username}/collection/`
- **Session data**: `user_data/{username}/session_data.json`
- **Found counts**: Tracked per user
- **Location index**: Independent per user

### Session Data Structure

```json
{
  "found_counts": {
    "('part_id', 'color_id', 'location')": quantity
  },
  "locations_index": {
    "location": ["parts_list"]
  },
  "last_updated": "2025-12-04T10:30:00"
}
```

## Security Implementation

### Current (Development)
- ✓ Bcrypt password hashing
- ✓ Secure cookie-based sessions
- ✓ Local file-based user storage
- ✓ YAML configuration

### Recommended for Production
- Database backend (PostgreSQL/MongoDB)
- Environment-based secrets
- HTTPS/SSL enforcement
- Email verification
- Rate limiting
- Two-factor authentication
- Password complexity requirements

## Migration Notes

### From Single-User Version

If upgrading from previous version:

1. Existing data location: `collection/` directory
2. Create a user account
3. Copy files to `user_data/{username}/collection/`
4. Login and continue using

### Backward Compatibility

- Old collection files remain in `collection/` directory
- Not automatically migrated to user-specific folders
- Manual migration required per user

## Testing

### Test Coverage

1. **Auth Module** (`test_auth.py`):
   - Config file creation
   - User directory creation
   - Session save/load
   - Password hashing

2. **Manual Testing**:
   - User registration
   - Login/logout flow
   - Multi-user isolation
   - Progress persistence
   - File upload per user

### Demo Account

Pre-configured demo account for testing:
- **Username**: `demo`
- **Password**: `demo123`
- Location: `resources/auth_config.yaml`

## API Changes

### New Functions

```python
# core/auth.py
AuthManager(config_path, user_data_dir)
auth_manager.login() → bool
auth_manager.logout()
auth_manager.register_user()
auth_manager.get_user_data_path(username) → Path
auth_manager.save_user_session(username, session_data)
auth_manager.load_user_session(username) → dict
auth_manager.reset_password()
ensure_authenticated() → bool
```

### Modified Behavior

- `DEFAULT_COLLECTION_DIR` now points to user-specific directory
- Session state includes `username`, `name`, `authenticated`
- App stops if not authenticated

## Configuration

### Auth Config File

```yaml
credentials:
  usernames:
    {username}:
      email: user@example.com
      name: User Name
      password: $2b$12$hashed_password

cookie:
  name: rebrickable_storage_cookie
  key: secret_key_here
  expiry_days: 30

preauthorized:
  emails: []
```

## Dependencies Added

| Package | Version | Purpose |
|---------|---------|---------|
| streamlit-authenticator | latest | User authentication |
| pyyaml | latest | Config file parsing |
| bcrypt | latest | Password hashing |

## Known Limitations

1. **File-based storage**: Not suitable for high-scale production
2. **No email verification**: Users can register with any email
3. **No password recovery**: Users must manually reset via UI
4. **Session data serialization**: Tuple keys converted to strings
5. **No admin panel**: User management via config file only

## Future Enhancements

- [ ] Database backend integration
- [ ] Email verification system
- [ ] Forgot password with email reset
- [ ] Admin dashboard
- [ ] User activity logging
- [ ] Role-based access control
- [ ] API for external integrations
- [ ] OAuth2 support (Google, GitHub)
- [ ] Two-factor authentication

## Breaking Changes

None - this is a new feature addition.

Existing single-user setups will need to:
1. Create a user account
2. Manually move collection files to user directory

## Version

- **Feature**: Multi-User Authentication
- **Date**: 2025-12-04
- **Status**: Complete - Ready for Testing

## Support

See documentation:
- `AUTHENTICATION_GUIDE.md` - Usage and troubleshooting
- `INSTALLATION.md` - Setup instructions
- `test_auth.py` - Validation script
