# Spec Provenance

**Created:** 2025-12-07  
**Context:** Existing Rebrickable Storage multi-user app with authentication already implemented using `streamlit-authenticator`. Cookie configuration exists with 30-day expiry, but user wants opt-in persistent login behavior.  
**Request:** "When a user logs in, the browser should save a cookie to keep the user logged in for 30 days without need to re-enter the password every time there is a refresh"

---

# Spec Header

## Feature Name
Remember Me Checkbox for Persistent Login

## Smallest Acceptable Scope
Add a "Remember Me" checkbox to the login form that:
- When **checked**: Cookie persists for 30 days (user stays logged in across browser sessions)
- When **unchecked** (default): Cookie expires when browser closes (session-only)
- Works with existing `streamlit-authenticator` library and auth flow

## Non-Goals (Defer to Later)
- Biometric authentication or OAuth integration
- Token refresh mechanisms or JWT implementation
- Multiple device session management or "logout everywhere" feature
- Custom cookie security configuration beyond streamlit-authenticator defaults
- Migration of existing users to new cookie scheme (existing cookies continue to work)

---

# Paths to Supplementary Guidelines

**Tech Stack Reference:**  
https://raw.githubusercontent.com/memextech/templates/refs/heads/main/stack/python_streamlit.md

---

# Decision Snapshot

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Cookie Library** | streamlit-authenticator (existing) | Already integrated; supports dynamic expiry configuration |
| **Default Behavior** | Session-only (unchecked) | More secure; users opt-in to persistence |
| **Remember Me Duration** | 30 days | Matches existing config; industry standard for "remember me" |
| **Session-Only Duration** | 0 days (browser close) | Standard session cookie behavior |
| **UI Location** | Below password field in login tab | Standard placement for login forms |
| **State Management** | Streamlit session_state for checkbox value | Native Streamlit pattern; no external storage needed |

---

# Architecture at a Glance

```
┌─────────────────────────────────────────────┐
│           app.py (main app)                 │
│  ┌────────────────────────────────────┐    │
│  │ Authentication Check                │    │
│  │ - ensure_authenticated()            │    │
│  │ - If not authenticated → show login │    │
│  └────────────────────────────────────┘    │
│                   │                          │
│                   ▼                          │
│  ┌────────────────────────────────────┐    │
│  │  Login Tab                          │    │
│  │  ├─ Username field                  │    │
│  │  ├─ Password field                  │    │
│  │  ├─ [NEW] Remember Me checkbox      │    │
│  │  └─ Login button                    │    │
│  └────────────────────────────────────┘    │
└─────────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│      core/auth.py (AuthManager)             │
│  ┌────────────────────────────────────┐    │
│  │ __init__(config_path)               │    │
│  │ - Load auth_config.yaml             │    │
│  │ - Initialize authenticator          │    │
│  └────────────────────────────────────┘    │
│                   │                          │
│  ┌────────────────────────────────────┐    │
│  │ login()  [MODIFIED]                 │    │
│  │ - Render checkbox                   │    │
│  │ - Get remember_me value from state  │    │
│  │ - Set dynamic cookie expiry         │    │
│  │ - Call authenticator.login()        │    │
│  └────────────────────────────────────┘    │
└─────────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│   streamlit-authenticator library           │
│   - Sets browser cookie with expiry_days    │
│   - Manages authentication state            │
└─────────────────────────────────────────────┘
```

**Flow:**
1. User opens app → `ensure_authenticated()` checks cookie
2. If no valid cookie → show login form with "Remember Me" checkbox
3. User enters credentials and checks/unchecks "Remember Me"
4. `AuthManager.login()` reads checkbox state from `st.session_state`
5. Sets cookie expiry: 30 days if checked, 0 days (session) if unchecked
6. Authenticator creates cookie with appropriate expiry
7. On next visit: cookie auto-authenticates if still valid

---

# Implementation Plan

## Phase 1: Update AuthManager.login() Method
**File:** `core/auth.py`

### Step 1.1: Add Remember Me Checkbox to Login UI
- Modify `login()` method in `AuthManager` class
- Before calling `self.authenticator.login()`, add checkbox widget:
  ```python
  remember_me = st.checkbox(
      "Remember me for 30 days",
      value=False,  # Default unchecked
      key="remember_me_checkbox",
      help="Keep me logged in across browser sessions"
  )
  ```
- Store checkbox value in session state for access during authentication

### Step 1.2: Implement Dynamic Cookie Expiry Logic
- Capture `remember_me` value before authentication
- Temporarily update the authenticator's cookie expiry configuration:
  ```python
  # Store original expiry setting
  original_expiry = self.config['cookie']['expiry_days']
  
  # Set expiry based on remember_me checkbox
  if remember_me:
      self.config['cookie']['expiry_days'] = 30
  else:
      self.config['cookie']['expiry_days'] = 0  # Session-only
  
  # Recreate authenticator with new expiry
  self.authenticator = stauth.Authenticate(
      self.config['credentials'],
      self.config['cookie']['name'],
      self.config['cookie']['key'],
      self.config['cookie']['expiry_days']
  )
  ```

### Step 1.3: Call Authentication with Updated Config
- Execute `self.authenticator.login()` with the dynamic expiry setting
- After authentication completes, optionally restore original config for consistency:
  ```python
  # Restore original setting (optional, for config consistency)
  self.config['cookie']['expiry_days'] = original_expiry
  ```

### Step 1.4: Update Method Return Logic
- Ensure existing return behavior is preserved
- Method should still return authentication status and handle success/failure messages

**Expected Code Structure:**
```python
def login(self):
    """Render login widget with Remember Me option"""
    
    # Render remember me checkbox BEFORE login form
    remember_me = st.checkbox(
        "Remember me for 30 days",
        value=False,
        key="remember_me_checkbox",
        help="Keep me logged in across browser sessions"
    )
    
    # Store original expiry
    original_expiry = self.config['cookie']['expiry_days']
    
    # Set dynamic expiry based on checkbox
    self.config['cookie']['expiry_days'] = 30 if remember_me else 0
    
    # Recreate authenticator with updated expiry
    self.authenticator = stauth.Authenticate(
        self.config['credentials'],
        self.config['cookie']['name'],
        self.config['cookie']['key'],
        self.config['cookie']['expiry_days']
    )
    
    # Perform login
    self.authenticator.login()
    
    # Restore original config (optional)
    self.config['cookie']['expiry_days'] = original_expiry
    
    # Check authentication status (existing logic)
    authentication_status = st.session_state.get('authentication_status')
    # ... rest of existing authentication handling
```

## Phase 2: Test Cookie Behavior

### Step 2.1: Test Remember Me Checked (30-day persistence)
- Log in with "Remember Me" checked
- Close browser completely
- Reopen browser and navigate to app
- **Expected:** User is still logged in, no password required
- **Verify:** Cookie exists in browser dev tools with 30-day expiry

### Step 2.2: Test Remember Me Unchecked (session-only)
- Log out
- Log in with "Remember Me" unchecked
- Refresh page (should stay logged in during same session)
- Close browser completely
- Reopen browser and navigate to app
- **Expected:** User is logged out, must enter password again
- **Verify:** Cookie has session-only expiry (expires with browser close)

### Step 2.3: Test Switching Between Modes
- Log in with "Remember Me" unchecked → verify session behavior
- Log out → Log in with "Remember Me" checked → verify persistence
- Confirm no conflicts or stale cookie issues

## Phase 3: Update Documentation

### Step 3.1: Update Code Comments
- Add docstring to `login()` method explaining "Remember Me" behavior
- Document cookie expiry logic in inline comments

### Step 3.2: User-Facing Instructions (Optional)
- If the app has a README or help section, document the "Remember Me" feature
- Explain security implications (shared/public computers should not use "Remember Me")

---

# Verification & Demo Script

## Pre-Demo Setup
1. Ensure app is running locally or on deployment environment
2. Clear all browser cookies for the app domain
3. Open browser dev tools → Application/Storage → Cookies

## Demo Flow

### Scenario 1: Session-Only Login (Default)
```
1. Navigate to app → see login screen
2. Enter valid credentials
3. Leave "Remember me for 30 days" UNCHECKED
4. Click Login
5. ✓ User is logged in, sees main app interface
6. Open dev tools → Cookies → verify cookie exists with session expiry
7. Refresh page
8. ✓ User remains logged in (same session)
9. Close browser completely (all windows)
10. Reopen browser → navigate to app
11. ✓ User is logged out, sees login screen again
```

### Scenario 2: Persistent Login (Remember Me)
```
1. Navigate to app → see login screen
2. Enter valid credentials
3. CHECK "Remember me for 30 days"
4. Click Login
5. ✓ User is logged in, sees main app interface
6. Open dev tools → Cookies → verify cookie has 30-day expiry date
7. Close browser completely (all windows)
8. Reopen browser → navigate to app
9. ✓ User is STILL logged in, no password required
10. Verify welcome message shows correct username
```

### Scenario 3: Mode Switching
```
1. If logged in → Log out
2. Log in WITHOUT "Remember Me"
3. Close browser → reopen → ✓ logged out
4. Log in WITH "Remember Me" checked
5. Close browser → reopen → ✓ still logged in
6. Logout → verify cookie is cleared
```

## Success Criteria
- [ ] Checkbox appears on login form with clear label
- [ ] Default state is unchecked (session-only)
- [ ] Checked → user stays logged in after browser close (30 days)
- [ ] Unchecked → user must re-login after browser close
- [ ] No errors or warnings in browser console
- [ ] Existing authentication flow unchanged (logout, user data save/load still work)
- [ ] Cookie security flags remain as configured by streamlit-authenticator

---

# Deploy

**Deployment:** No changes required to deployment configuration. This is a code-only change to the existing authentication flow.

**Environments:**
- **Local Development:** Test with `streamlit run app.py`
- **Production:** Deploy as usual (existing deployment process unchanged)

**Post-Deployment Verification:**
- Test both scenarios (with/without "Remember Me") in production environment
- Verify cookies work correctly with HTTPS (cookie security requirements)
- Confirm no CORS or cookie domain issues in deployed environment

**Rollback Plan:**
- If issues arise, revert `core/auth.py` to previous version
- Existing users will continue with 30-day cookies (original config behavior)
- No data migration or user action required

---

# Notes & Assumptions

1. **streamlit-authenticator Library Behavior:** Assumes the library supports dynamic `expiry_days` configuration at runtime by recreating the `Authenticate` object. If this doesn't work, alternative approach would be to fork the library or use custom cookie management.

2. **Cookie Security:** Relies on streamlit-authenticator's default cookie security settings (httponly, secure flags). No custom security configuration in this scope.

3. **Existing Users:** Users with existing 30-day cookies will continue to work. Next login will respect their "Remember Me" choice.

4. **Browser Privacy Modes:** "Remember Me" will NOT persist in private/incognito browsing (browser limitation, expected behavior).

5. **Multi-Device:** Each device/browser maintains its own cookie. Logging out on one device doesn't affect others (limitation of cookie-based auth).

6. **Session State:** The `remember_me` checkbox value is ephemeral (not persisted). This is intentional—user makes choice each login.
