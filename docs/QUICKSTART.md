# Quick Start Guide - Multi-User Authentication

## 🚀 Get Started in 3 Minutes

### Step 1: Install Dependencies (1 minute)

```bash
# Navigate to project
cd "D:\Tools - Progs\rebrickable-storage"

# Install required packages
pip install -r requirements.txt
```

Or if you don't have a virtual environment yet:

```bash
# Create virtual environment
python -m venv .venv

# Activate it (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Run the App (30 seconds)

```bash
streamlit run app.py
```

Your browser will open automatically at `http://localhost:8501`

### Step 3: Login or Register (1 minute)

**Option A: Use Demo Account**
- Username: `demo`
- Password: `demo123`
- Click "Login"

**Option B: Create Your Own Account**
- Click "Register" tab
- Fill in:
  - Email: your.email@example.com
  - Username: yourname
  - Name: Your Full Name
  - Password: your_secure_password
  - Repeat password
- Click "Register user"
- Return to "Login" tab and login

### Step 4: Use the App! 🎉

Once logged in, you'll see:
- Welcome message with your name
- Main app interface
- Sidebar with Save/Load progress buttons

## 📁 What You Can Do Now

### Upload Files
1. Upload wanted parts CSV files
2. Upload collection files
3. Click "Start Processing"

### Track Progress
- Mark parts as found
- Use location-specific controls
- See summary of your progress

### Save Your Work
- Click "💾 Save Progress" in sidebar
- Your data is saved to disk
- Safe to close browser

### Resume Later
- Login again with same credentials
- Click "📂 Load Progress"
- Continue where you left off

## 🔄 Multiple Users

Each user can:
- Have their own account
- Upload different collections
- Work simultaneously
- Have isolated data

No conflicts - everyone's data is separate!

## 📋 File Locations

Your data is stored in:
```
user_data/
└── {your_username}/
    ├── collection/          # Your uploaded files
    └── session_data.json    # Your saved progress
```

## 🆘 Quick Troubleshooting

### Can't install packages?
```bash
# Try upgrading pip first
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Streamlit not found?
```bash
pip install streamlit
```

### Port already in use?
```bash
streamlit run app.py --server.port 8502
```

### Can't login?
- Check username/password spelling
- Try demo account (demo/demo123)
- Register a new account

## 📚 Learn More

- **Full Installation Guide**: See `INSTALLATION.md`
- **Authentication Details**: See `AUTHENTICATION_GUIDE.md`
- **All Changes**: See `CHANGELOG_AUTH.md`

## ✅ Verify Setup

Run the test script:
```bash
python test_auth.py
```

Should show "All tests passed! ✓"

---

**That's it!** You're ready to use the multi-user Rebrickable Storage app. 🎊
