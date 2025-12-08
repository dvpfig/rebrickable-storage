# Rebrickable Storage - Multi-User Edition

A Streamlit application for identifying and tracking LEGO parts in your collection, now with **multi-user support** allowing concurrent users to work independently.

## 🎯 What's New

### Multi-User Authentication
- ✅ Secure user registration and login
- ✅ Password hashing with bcrypt
- ✅ Session-based authentication
- ✅ Individual user accounts

### Data Isolation
- ✅ Separate collection directories per user
- ✅ Independent session tracking
- ✅ No data conflicts between users
- ✅ Concurrent user support

### Progress Persistence
- ✅ Save your progress anytime
- ✅ Load previous session
- ✅ Resume work from any device
- ✅ Data persists across sessions

## 🚀 Quick Start

### 1. Install
```bash
pip install -r requirements.txt
```

### 2. Run
```bash
streamlit run app.py
```

### 3. Login
- **Demo Account**: `demo` / `demo123`
- **Or Register**: Create your own account

That's it! Start uploading your LEGO collection.

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [**QUICKSTART.md**](QUICKSTART.md) | Get started in 3 minutes |
| [**INSTALLATION.md**](INSTALLATION.md) | Detailed setup instructions |
| [**AUTHENTICATION_GUIDE.md**](AUTHENTICATION_GUIDE.md) | Complete auth documentation |
| [**ARCHITECTURE.md**](ARCHITECTURE.md) | System architecture and design |
| [**CHANGELOG_AUTH.md**](CHANGELOG_AUTH.md) | All changes and features |

## ✨ Features

### For Users
- 🔐 **Secure Authentication**: Bcrypt password hashing
- 👥 **Multi-User**: Multiple users can work simultaneously
- 📁 **Data Isolation**: Your data is private and separate
- 💾 **Save/Load**: Persist your progress between sessions
- 🔄 **Resume Work**: Pick up where you left off
- 🎨 **Dark Theme**: Eye-friendly interface

### For Developers
- 🏗️ **Modular Design**: Clean separation of concerns
- 🔌 **Easy Extension**: Add new features easily
- 📦 **Session Management**: Built-in save/load
- 🛡️ **Security**: Production-ready patterns
- 📖 **Well Documented**: Comprehensive guides

## 🏗️ Architecture

```
┌─────────────────────────────────────────┐
│         Streamlit Application           │
├─────────────────────────────────────────┤
│  Authentication Layer (core/auth.py)    │
│  ├─ Login/Register                      │
│  ├─ User Management                     │
│  └─ Session Persistence                 │
├─────────────────────────────────────────┤
│  Business Logic (core/)                 │
│  ├─ Part Mapping                        │
│  ├─ Image Resolution                    │
│  ├─ Color Management                    │
│  └─ Data Processing                     │
├─────────────────────────────────────────┤
│  User Interface (ui/)                   │
│  ├─ Theme & Layout                      │
│  ├─ Summary Views                       │
│  └─ Interactive Controls                │
└─────────────────────────────────────────┘
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed diagrams.

## 📂 Project Structure

```
rebrickable-storage/
├── app.py                      # Main application
├── core/
│   ├── auth.py                # ★ Authentication module
│   ├── paths.py               # Path management
│   ├── mapping.py             # Part mapping
│   ├── preprocess.py          # Data processing
│   ├── images.py              # Image handling
│   └── colors.py              # Color management
├── ui/
│   ├── theme.py               # UI theming
│   ├── layout.py              # Layout components
│   └── summary.py             # Summary tables
├── resources/
│   ├── auth_config.yaml       # ★ User credentials
│   └── mappings/              # Part mappings
├── user_data/                 # ★ User-specific data
│   └── {username}/
│       ├── collection/        # Uploaded files
│       └── session_data.json  # Saved progress
└── cache/
    └── images/                # Cached images
```

## 🔐 Security

### Current Implementation
- ✅ Bcrypt password hashing
- ✅ Secure session cookies
- ✅ File-based user storage
- ✅ Data isolation per user

### Production Recommendations
- 🔄 Database backend (PostgreSQL/MongoDB)
- 🔄 Environment-based secrets
- 🔄 HTTPS/SSL enforcement
- 🔄 Email verification
- 🔄 Two-factor authentication

See [AUTHENTICATION_GUIDE.md](AUTHENTICATION_GUIDE.md) for details.

## 👥 User Workflow

```
1. Register/Login
   ↓
2. Upload Collection Files
   ↓
3. Upload Wanted Files
   ↓
4. Start Processing
   ↓
5. Mark Parts as Found
   ↓
6. Save Progress
   ↓
7. Download Results
```

## 🛠️ Development

### Setup Development Environment

```bash
# Clone or navigate to project
cd rebrickable-storage

# Create virtual environment
python -m venv .venv

# Activate (Windows)
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Run tests
python test_auth.py

# Start app
streamlit run app.py
```

### Adding New Features

1. **New Session Data**:
   - Edit `core/auth.py` → `save_user_session()`
   - Add serialization logic
   - Update `load_user_session()`

2. **New UI Components**:
   - Add to `ui/` directory
   - Import in `app.py`
   - Follow existing patterns

3. **New Core Logic**:
   - Add to `core/` directory
   - Keep separation of concerns
   - Document public APIs

## 🧪 Testing

### Test Authentication System
```bash
python test_auth.py
```

Expected output:
```
All tests passed! ✓
Demo credentials:
  Username: demo
  Password: demo123
```

### Manual Testing Checklist
- [ ] User registration
- [ ] User login
- [ ] File upload
- [ ] Progress tracking
- [ ] Save session
- [ ] Load session
- [ ] Multi-user isolation
- [ ] Logout

## 📊 User Data

Each user has isolated data:

```
user_data/
└── {username}/
    ├── collection/              # Uploaded collection files
    │   ├── collection_1.csv
    │   └── collection_2.csv
    └── session_data.json        # Saved progress
        {
          "found_counts": {...},
          "locations_index": {...},
          "last_updated": "2025-12-04T10:30:00"
        }
```

## 🔧 Configuration

### Auth Config (`resources/auth_config.yaml`)

```yaml
credentials:
  usernames:
    demo:
      email: demo@example.com
      name: Demo User
      password: $2b$12$... # Bcrypt hash

cookie:
  name: rebrickable_storage_cookie
  key: secret_key_here  # Change in production!
  expiry_days: 30
```

### Environment Variables (Optional)

```bash
# Recommended for production
export COOKIE_SECRET_KEY="your-secret-key"
export DATABASE_URL="postgresql://..."
```

## 🚢 Deployment

### Local Development
```bash
streamlit run app.py
```

### Production (Streamlit Cloud)
```bash
# Push to GitHub
git push origin main

# Deploy on streamlit.io
# Add secrets in dashboard
```

### Docker (Optional)
```bash
# Build
docker build -t rebrickable-storage .

# Run
docker run -p 8501:8501 rebrickable-storage
```

## 🆘 Troubleshooting

### Can't Login
- Check username/password
- Try demo account (demo/demo123)
- Verify `resources/auth_config.yaml` exists

### No Data Persisting
- Click "Save Progress" button
- Check `user_data/{username}/` directory
- Verify write permissions

### Multiple Users Conflict
- Should not happen - data is isolated
- Check different usernames are used
- Verify user_data paths

### Installation Issues
See [INSTALLATION.md](INSTALLATION.md) for detailed troubleshooting.

## 📝 Migration from Single-User

If you have the old version:

1. **Backup your data**
   ```bash
   cp -r collection/ collection_backup/
   ```

2. **Install new version**
   ```bash
   pip install -r requirements.txt
   ```

3. **Create user account**
   - Register with username
   - Login

4. **Copy old data**
   ```bash
   cp collection_backup/* user_data/{username}/collection/
   ```

5. **Start using**
   - Upload files or use existing
   - Continue tracking

## 🤝 Contributing

### Areas for Contribution
- Database backend integration
- Email verification system
- Enhanced security features
- UI/UX improvements
- Performance optimizations
- Additional tests

### Development Process
1. Fork repository
2. Create feature branch
3. Make changes
4. Test thoroughly
5. Submit pull request

## 📜 License

See [LICENSE](LICENSE) file for details.

## 🙏 Credits

- **Rebrickable** - LEGO part data
- **BrickArchitect** - Part images
- **Streamlit** - Web framework
- **streamlit-authenticator** - Auth library

## 📮 Support

### Documentation
- [Quick Start](QUICKSTART.md) - Get started fast
- [Installation](INSTALLATION.md) - Setup help
- [Authentication Guide](AUTHENTICATION_GUIDE.md) - Auth details
- [Architecture](ARCHITECTURE.md) - System design
- [Changelog](CHANGELOG_AUTH.md) - What's new

### Issues
- Check documentation first
- Review error messages
- Verify configuration
- Test with demo account

## 🗺️ Roadmap

### Version 1.1 (Current)
- ✅ Multi-user authentication
- ✅ Session persistence
- ✅ Data isolation
- ✅ Save/Load progress

### Version 1.2 (Planned)
- 🔄 Database backend
- 🔄 Email verification
- 🔄 Password recovery
- 🔄 Admin dashboard

### Version 2.0 (Future)
- 🔮 OAuth2 integration
- 🔮 Two-factor auth
- 🔮 API endpoints
- 🔮 Mobile app

## 📈 Stats

- **Languages**: Python
- **Framework**: Streamlit
- **Authentication**: streamlit-authenticator + bcrypt
- **Storage**: File-based (YAML + JSON)
- **Multi-user**: Full support
- **Concurrent**: Yes

---

## 🎉 Get Started Now!

```bash
# Quick start
pip install -r requirements.txt
streamlit run app.py

# Login with
Username: demo
Password: demo123

# Or register your own account!
```

**Made with ❤️ for the LEGO community**
