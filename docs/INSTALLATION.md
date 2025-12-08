# Installation and Setup Guide

## Prerequisites

- Python 3.8 or higher
- pip package manager

## Installation Steps

### 1. Clone or Navigate to Project Directory

```bash
cd "D:\Tools - Progs\rebrickable-storage"
```

### 2. Create Virtual Environment (Recommended)

**Using venv (built-in):**
```bash
python -m venv .venv
```

**Or using uv (faster):**
```bash
# Install uv first (Windows PowerShell)
powershell -Command "Set-ExecutionPolicy RemoteSigned -scope CurrentUser -Force; iwr https://astral.sh/uv/install.ps1 -useb | iex"

# Create environment
uv venv
```

### 3. Activate Virtual Environment

**Windows PowerShell:**
```powershell
.\.venv\Scripts\Activate.ps1
```

**Windows CMD:**
```cmd
.venv\Scripts\activate.bat
```

**Linux/Mac:**
```bash
source .venv/bin/activate
```

### 4. Install Dependencies

**Using pip:**
```bash
pip install -r requirements.txt
```

**Or using uv:**
```bash
uv pip install -r requirements.txt
```

### 5. Verify Installation

Run the test script to verify authentication setup:

```bash
python test_auth.py
```

Expected output:
```
Testing Authentication System
==================================================

1. Initializing AuthManager...
   ✓ AuthManager created

2. Checking config file...
   ✓ Config file created at: test_auth_config.yaml
   ✓ Default user 'demo' exists
   ✓ Cookie configuration present

3. Checking user data directory...
   ✓ User data directory created at: test_user_data

4. Testing user-specific paths...
   ✓ User directory created: test_user_data\testuser

5. Testing session save/load...
   ✓ Session saved
   ✓ Session loaded correctly

==================================================
All tests passed! ✓

Demo credentials:
  Username: demo
  Password: demo123
```

## Running the Application

### Start the Streamlit App

```bash
streamlit run app.py
```

The application will open in your default web browser at `http://localhost:8501`

### First Login

Use the demo credentials:
- **Username:** `demo`
- **Password:** `demo123`

Or register a new account using the "Register" tab.

## Directory Structure After Installation

```
rebrickable-storage/
├── .venv/                          # Virtual environment (created)
├── user_data/                      # User data (created on first run)
│   └── {username}/
│       ├── collection/             # User's uploaded files
│       └── session_data.json       # Saved progress
├── resources/
│   └── auth_config.yaml            # Authentication config (created on first run)
├── app.py                          # Main application
├── requirements.txt                # Python dependencies
├── AUTHENTICATION_GUIDE.md         # Auth documentation
└── INSTALLATION.md                 # This file
```

## Troubleshooting

### Issue: Python not found

**Solution:** Install Python from [python.org](https://www.python.org/downloads/) or use Windows Store version.

### Issue: Module not found errors

**Solution:** 
1. Ensure virtual environment is activated
2. Reinstall dependencies: `pip install -r requirements.txt`

### Issue: Streamlit not found

**Solution:** 
```bash
pip install streamlit
```

### Issue: Permission denied on PowerShell

**Solution:** Run PowerShell as Administrator and execute:
```powershell
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Issue: Port 8501 already in use

**Solution:** Stop other Streamlit instances or use a different port:
```bash
streamlit run app.py --server.port 8502
```

## Updating the Application

To get the latest changes:

```bash
# Pull latest code (if using git)
git pull

# Reinstall dependencies
pip install -r requirements.txt --upgrade

# Restart the application
streamlit run app.py
```

## Uninstallation

To remove the application:

1. Delete the project directory
2. Remove user data: Delete `user_data/` folder
3. Deactivate and remove virtual environment:
   ```bash
   deactivate
   rm -rf .venv  # Linux/Mac
   Remove-Item -Recurse -Force .venv  # PowerShell
   ```

## Next Steps

- Read `AUTHENTICATION_GUIDE.md` for detailed usage instructions
- Register your own user account
- Upload your Lego collection and wanted files
- Start tracking your parts!
