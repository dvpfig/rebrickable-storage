# streamlit-authenticator API Compatibility Guide

## Current Implementation (v1.0.3)

This document describes the correct API usage for the current version of `streamlit-authenticator`.

---

## Authentication Methods

### 1. Login

**Current API (Working):**
```python
def login(self):
    """Render login widget and return authentication status"""
    self.authenticator.login()
    
    # Read from session state
    authentication_status = st.session_state.get('authentication_status')
    name = st.session_state.get('name')
    username = st.session_state.get('username')
    
    if authentication_status:
        st.session_state['authenticated'] = True
        return True
    elif authentication_status is False:
        st.error('Username/password is incorrect')
        return False
    elif authentication_status is None:
        st.warning('Please enter your username and password')
        return False
```

**❌ Old API (Broken):**
```python
# Don't use this!
name, authentication_status, username = self.authenticator.login('Login', 'main')
```

**Key Changes:**
- No parameters needed
- Returns `None` (not a tuple)
- Sets values in `st.session_state` instead

**Session State Keys Set:**
- `st.session_state['authentication_status']` - `True`, `False`, or `None`
- `st.session_state['name']` - User's full name
- `st.session_state['username']` - Username

---

### 2. Logout

**Current API (Working):**
```python
def logout(self):
    """Render logout button"""
    self.authenticator.logout()
    # Clear our custom authenticated flag
    if st.session_state.get('authentication_status') is False or \
       st.session_state.get('authentication_status') is None:
        st.session_state['authenticated'] = False
```

**❌ Old API (Broken):**
```python
# Don't use this!
self.authenticator.logout('Logout', 'sidebar')
```

**Key Changes:**
- No parameters needed
- No location specification
- Automatically updates session state

---

### 3. Register User

**Current API (Working):**
```python
def register_user(self):
    """Render registration widget"""
    try:
        self.authenticator.register_user()
        st.success('User registered successfully')
        # Save updated config
        with open(self.config_path, 'w') as file:
            yaml.dump(self.config, file, default_flow_style=False)
    except Exception as e:
        st.error(f'Registration failed: {e}')
```

**❌ Old API (Broken):**
```python
# Don't use this!
self.authenticator.register_user('Register user', preauthorization=False)
```

**Key Changes:**
- No parameters needed
- No `preauthorization` argument
- No location string
- Updates `self.config` in place

---

### 4. Reset Password

**Current API (Working):**
```python
def reset_password(self):
    """Render password reset widget"""
    try:
        username = st.session_state.get('username')
        if username and self.authenticator.reset_password(username):
            st.success('Password modified successfully')
            with open(self.config_path, 'w') as file:
                yaml.dump(self.config, file, default_flow_style=False)
    except Exception as e:
        st.error(f'Password reset failed: {e}')
```

**❌ Old API (Broken):**
```python
# Don't use this!
self.authenticator.reset_password(username, 'Reset password')
```

**Key Changes:**
- Only username parameter
- No location string
- Returns boolean on success

---

## Session State Management

### Authentication Status

The authenticator sets these keys in `st.session_state`:

| Key | Type | Values | Description |
|-----|------|--------|-------------|
| `authentication_status` | bool/None | `True`, `False`, `None` | Authentication state |
| `name` | str/None | User's full name | Display name |
| `username` | str/None | Username | Unique identifier |

### Custom Application Keys

Our app adds these additional keys:

| Key | Type | Description |
|-----|------|-------------|
| `authenticated` | bool | Our custom auth flag |
| `found_counts` | dict | Part tracking data |
| `locations_index` | dict | Location mapping |

### Safe Access Pattern

Always use `.get()` with defaults:

```python
# Safe access
username = st.session_state.get('username', 'default')
name = st.session_state.get('name', username)
auth_status = st.session_state.get('authentication_status')

# Avoid direct access (can raise KeyError)
# username = st.session_state['username']  # Don't do this!
```

---

## Configuration File Structure

### auth_config.yaml Format

```yaml
credentials:
  usernames:
    demo:
      email: demo@example.com
      name: Demo User
      password: $2b$12$hashed_password_here
    
    another_user:
      email: user@example.com
      name: Another User
      password: $2b$12$hashed_password_here

cookie:
  name: rebrickable_storage_cookie
  key: secret_key_change_in_production
  expiry_days: 30

preauthorized:
  emails: []
```

### Required Structure

- `credentials.usernames` - Dict of users
- `cookie.name` - Cookie identifier
- `cookie.key` - Secret signing key
- `cookie.expiry_days` - Session duration
- `preauthorized.emails` - List (can be empty)

---

## Common Patterns

### Check if User is Authenticated

```python
def ensure_authenticated():
    auth_status = st.session_state.get('authentication_status')
    if auth_status:
        st.session_state['authenticated'] = True
        return True
    return False
```

### Get Current User Info

```python
# In your app
if ensure_authenticated():
    username = st.session_state.get('username', 'unknown')
    name = st.session_state.get('name', username)
    st.write(f"Welcome, {name}!")
```

### Handle Login Flow

```python
# Check authentication
if not ensure_authenticated():
    st.title("Login Required")
    auth_manager.login()
    st.stop()

# User is authenticated - continue with app
st.title("Main Application")
```

---

## Breaking Changes History

### v1.0.0 → v1.0.1
- **Issue:** Location parameters no longer supported
- **Fix:** Remove location strings from all methods

### v1.0.1 → v1.0.2
- **Issue:** Login returns None instead of tuple
- **Fix:** Read from session state instead of unpacking

### v1.0.2 → v1.0.3
- **Issue:** preauthorization parameter removed
- **Fix:** Remove preauthorization argument from register_user()

---

## Testing Your Implementation

### Unit Test for Auth

```python
def test_auth():
    # Test login
    auth_manager.login()
    auth_status = st.session_state.get('authentication_status')
    assert auth_status in [True, False, None]
    
    # Test username access
    if auth_status:
        username = st.session_state.get('username')
        assert username is not None
```

### Integration Test

```bash
# Run test script
python test_auth.py

# Expected output:
# All tests passed! ✓
# Demo credentials:
#   Username: demo
#   Password: demo123
```

---

## Debugging Tips

### Enable Debug Mode

```python
import streamlit as st
st.write("Debug - Session State:")
st.write(st.session_state)
```

### Check Authentication Status

```python
auth_status = st.session_state.get('authentication_status')
st.write(f"Auth Status: {auth_status}")
st.write(f"Type: {type(auth_status)}")
```

### Verify User Data

```python
if st.session_state.get('authentication_status'):
    st.write(f"Username: {st.session_state.get('username')}")
    st.write(f"Name: {st.session_state.get('name')}")
```

---

## Migration Guide

### If You Have Old Code

1. **Remove location parameters:**
   - `login()` → `login()`
   - `logout('Logout', 'sidebar')` → `logout()`
   - `register_user('Register', preauth=False)` → `register_user()`
   - `reset_password(user, 'Reset')` → `reset_password(user)`

2. **Change return value handling:**
   ```python
   # Old
   name, status, username = auth.login()
   
   # New
   auth.login()
   status = st.session_state.get('authentication_status')
   name = st.session_state.get('name')
   username = st.session_state.get('username')
   ```

3. **Add safe access:**
   ```python
   # Add defaults
   username = st.session_state.get('username', 'default')
   name = st.session_state.get('name', username)
   ```

---

## Reference Links

- **streamlit-authenticator**: Check latest docs for updates
- **Streamlit Session State**: https://docs.streamlit.io/library/api-reference/session-state
- **Project Docs**: See `AUTHENTICATION_GUIDE.md`

---

## Quick Reference Card

```python
# Login
auth.login()  # No params!
auth_status = st.session_state.get('authentication_status')

# Logout
auth.logout()  # No params!

# Register
auth.register_user()  # No params!

# Reset Password
auth.reset_password(username)  # Only username!

# Check Auth
if st.session_state.get('authentication_status'):
    # User is authenticated
    username = st.session_state.get('username')
    name = st.session_state.get('name')
```

---

**Version:** 1.0.3  
**Date:** 2025-12-04  
**Status:** ✅ Current & Working
