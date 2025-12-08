# Troubleshooting Guide

## Common Issues and Solutions

### 1. App Won't Start

#### Error: `ModuleNotFoundError: No module named 'streamlit'`
**Solution:**
```bash
pip install -r requirements.txt
```

#### Error: `ModuleNotFoundError: No module named 'streamlit_authenticator'`
**Solution:**
```bash
pip install streamlit-authenticator
```

### 2. Authentication Issues

#### Can't Login with Demo Account
**Symptoms:** Username/password rejected
**Solution:**
1. Check spelling: `demo` / `demo123`
2. Ensure `resources/auth_config.yaml` exists
3. Try deleting `resources/auth_config.yaml` and restart app (it will regenerate)

#### Login Form Not Showing
**Symptoms:** Blank page or errors
**Solution:**
1. Check that `core/auth.py` exists
2. Verify imports work: `python -c "from core.auth import AuthManager"`
3. Check terminal for error messages

#### "TypeError: cannot unpack non-iterable NoneType object"
**Symptoms:** Error after entering credentials
**Solution:**
This was fixed in version 1.0.2. Ensure you have the latest code:
- `core/auth.py` should use `st.session_state.get('authentication_status')`
- See `QUICK_FIX_SUMMARY.md` for details

#### "Registration failed: unexpected keyword argument 'preauthorization'"
**Symptoms:** Error when trying to register new user
**Solution:**
This was fixed in version 1.0.3. Ensure you have the latest code:
- `core/auth.py` in `register_user()` should call `self.authenticator.register_user()` without parameters
- See `QUICK_FIX_SUMMARY.md` for details

### 3. Session/Progress Issues

#### Progress Not Saving
**Symptoms:** Click "Save Progress" but data not persisted
**Solution:**
1. Check that `user_data/{username}/` directory exists
2. Verify write permissions on `user_data/` folder
3. Check for `session_data.json` file after saving
4. Look for error messages in terminal

#### Can't Load Progress
**Symptoms:** "No saved progress found" message
**Solution:**
1. Ensure you saved progress at least once
2. Check `user_data/{username}/session_data.json` exists
3. Verify you're logged in with the same username
4. Try opening the JSON file to check it's valid

#### Progress Lost After Logout
**Symptoms:** Data disappears when logging out
**Solution:**
- Click "💾 Save Progress" BEFORE logging out
- Progress is not auto-saved, must be manual
- Each user's progress is separate

### 4. File Upload Issues

#### Can't Upload Files
**Symptoms:** Upload button not responding
**Solution:**
1. Check file format (CSV required)
2. Verify file size (very large files may timeout)
3. Check browser console for errors
4. Try refreshing the page

#### Files Upload But Don't Process
**Symptoms:** Files upload but no data appears
**Solution:**
1. Check CSV format matches expected structure
2. Look for error messages in Streamlit
3. Check terminal output for processing errors
4. Verify collection/wanted file structure

### 5. Multi-User Issues

#### Users See Each Other's Data
**Symptoms:** Data not isolated
**Solution:**
This should NOT happen. If it does:
1. Check each user is logged in with different username
2. Verify `user_data/{username}/` directories are separate
3. Review code in `app.py` around line 95-100
4. File a bug report

#### Two Users Can't Work Simultaneously
**Symptoms:** Second user can't login while first is active
**Solution:**
- Use different browser/incognito window for each user
- Or different devices
- Session cookies are per-browser

### 6. Display/UI Issues

#### Dark Theme Not Applied
**Symptoms:** App shows light theme
**Solution:**
1. Check `ui/theme.py` exists
2. Verify theme CSS is loaded
3. Try refreshing browser (Ctrl+F5)
4. Check browser console for CSS errors

#### Images Not Loading
**Symptoms:** Part images show as broken links
**Solution:**
1. Check internet connection (images fetched from BrickArchitect)
2. Verify `cache/images/` directory exists
3. Check terminal for image fetch errors
4. Some parts may not have images available

#### Layout Broken
**Symptoms:** UI elements misaligned
**Solution:**
1. Try refreshing page
2. Clear browser cache
3. Check browser zoom level (should be 100%)
4. Try different browser

### 7. Performance Issues

#### App Slow to Start
**Symptoms:** Long loading time
**Solution:**
- Normal for first run (mapping files loaded)
- Subsequent runs should be faster (cached)
- Large collection files take longer to process

#### App Slow During Processing
**Symptoms:** "Start Processing" takes long time
**Solution:**
- Expected for large collections
- Check terminal for progress messages
- Be patient, processing is CPU-intensive

#### High Memory Usage
**Symptoms:** System slow, high RAM usage
**Solution:**
- Normal for large datasets
- Close other applications
- Consider processing smaller batches
- Restart app periodically

### 8. Configuration Issues

#### Auth Config Missing
**Symptoms:** `resources/auth_config.yaml` not found
**Solution:**
- App should create it automatically on first run
- Check `resources/` directory exists
- Verify write permissions
- Manually create from template in `AUTHENTICATION_GUIDE.md`

#### Invalid YAML Config
**Symptoms:** "Error parsing config file"
**Solution:**
1. Check YAML syntax (indentation, colons, etc.)
2. Validate with online YAML validator
3. Compare with template in docs
4. Delete and let app regenerate

### 9. Windows-Specific Issues

#### PowerShell Execution Policy Error
**Symptoms:** Can't run scripts
**Solution:**
```powershell
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
```

#### Path Issues
**Symptoms:** "File not found" errors
**Solution:**
- Use full paths with quotes: `"D:\Tools - Progs\rebrickable-storage"`
- Check for spaces in path
- Use forward slashes or double backslashes

### 10. Deployment Issues

#### Streamlit Cloud Deployment Fails
**Symptoms:** App won't deploy online
**Solution:**
1. Check all dependencies in `requirements.txt`
2. Add secrets in Streamlit Cloud dashboard
3. Ensure Python version compatibility
4. Check logs for specific errors

#### Port Already in Use
**Symptoms:** Can't start on port 8501
**Solution:**
```bash
streamlit run app.py --server.port 8502
```

## Getting More Help

### Check Documentation
1. `START_HERE.md` - Overview
2. `QUICKSTART.md` - Getting started
3. `AUTHENTICATION_GUIDE.md` - Auth details
4. `INSTALLATION.md` - Setup help
5. `QUICK_FIX_SUMMARY.md` - Recent fixes

### Debug Mode
Run with verbose output:
```bash
streamlit run app.py --logger.level=debug
```

### Test Authentication System
```bash
python test_auth.py
```

### Check Logs
Look at terminal output for error messages and stack traces.

### Still Stuck?

1. Check all documentation files
2. Verify you're using latest code
3. Review error messages carefully
4. Try with demo account first
5. Test with minimal data (small files)

## Quick Diagnostics Checklist

Run through this list:
- [ ] `requirements.txt` dependencies installed
- [ ] Python 3.8+ installed
- [ ] `core/auth.py` exists and updated (v1.0.2+)
- [ ] `resources/` directory exists
- [ ] `resources/auth_config.yaml` present (or will be created)
- [ ] `user_data/` directory has write permissions
- [ ] Demo account works (demo/demo123)
- [ ] No errors in terminal when starting app
- [ ] Login form displays correctly
- [ ] Can register new user
- [ ] Logout works

## Version History

- **v1.0.0** - Initial multi-user implementation
- **v1.0.1** - Fixed location parameter errors
- **v1.0.2** - Fixed session state unpacking errors
- **v1.0.3** - Fixed registration preauthorization parameter (current)

---

**Last Updated:** 2025-12-04
