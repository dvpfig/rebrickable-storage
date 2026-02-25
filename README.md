# Rebrickable Storage - LEGO Parts Finder

A web application for LEGO enthusiasts to efficiently manage and locate parts from their collection. Upload your parts and sets, match wanted parts against your inventory, and find exactly where each piece is stored.

Built with Python and Streamlit, using data from [Rebrickable](https://rebrickable.com) and [BrickArchitect](https://brickarchitect.com).

## Features

- **Multi-user authentication** with session persistence
- **Parts collection management** with location-based organization
- **Sets collection management** with automatic inventory retrieval via Rebrickable API
- **Smart part matching** between wanted lists and your collection or sets
- **Visual part identification** with images from BrickArchitect
- **Label generation** for storage containers (LBX and image formats)
- **Progress tracking** to resume work across sessions
- **Dark/light theme** support
- **BrickArchitect integration** for part images and labels

## Screenshots

[Add screenshots here]

## Getting Started

### Prerequisites

- Python 3.11 or higher
- pip package manager

### Security Setup (Required for Production)

Before deploying to production or exposing via HTTPS, run the security setup:

```bash
python tools/security/setup_security.py
```

This will:
- Generate a secure cookie secret key
- Create `.env` file with secure defaults
- Verify `.gitignore` configuration
- Set appropriate file permissions
- Auto-install missing dependencies if needed

**Important:** Never commit the `.env` file or share your `COOKIE_SECRET_KEY`.

For detailed security information, see [plans/SECURITY_ENHANCEMENTS.md](plans/SECURITY_ENHANCEMENTS.md).

### Option 1: Run Locally

1. Clone the repository:
```bash
git clone https://github.com/yourusername/rebrickable-storage.git
cd rebrickable-storage
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
streamlit run app.py
```

4. Open your browser to `http://localhost:8501`

### Option 2: Self-Host with Docker

For detailed Docker deployment instructions, see [docker/README.md](docker/README.md).

Quick start:
```bash
cd docker
# Edit .env file with your data location
docker-compose up -d
```

Access at `http://localhost:8501`

## Usage

### Managing Your Collection

1. **Login** with demo credentials (`demo` / `demo123`) or create a new account
2. Navigate to **My Collection - Parts** to:
   - Upload collection CSV files from Rebrickable
   - Generate printable labels organized by storage location
3. Navigate to **My Collection - Sets** to:
   - Upload sets CSV or manually add set numbers
   - Configure your Rebrickable API key
   - Retrieve part inventories for your sets

### Finding Wanted Parts

1. Navigate to **Find Wanted Parts**
2. **Upload wanted parts** CSV from Rebrickable (e.g., from a MOC or set inventory)
3. **Select collection files or sets** to search through
4. **Generate pickup list** organized by storage location
5. **Mark parts as found** while collecting
6. **Download results** or generate printable labels

## Data Sources

- **Rebrickable**: Part numbers, set inventories, and part data
- **BrickArchitect**: Part images and label files

## Configuration

### Security Configuration

The application uses environment variables for sensitive configuration:

- `COOKIE_SECRET_KEY` - Secret key for cookie signing (required in production)
- `SESSION_TIMEOUT_MINUTES` - Session inactivity timeout (default: 90)
- `MAX_FILE_SIZE_MB` - Maximum file upload size (default: 1.0)

See `.env.example` for all available options.

### User Data

User-specific data is stored in `user_data/{username}/`:
- `collection_parts/` - Collection CSV files
- `collection_sets/` - Sets CSV files
- `collection_sets.json` - Sets metadata and inventories
- `images_uploaded/` - Custom part images
- `session_data.json` - Session progress
- `rebrickable_api_key.txt` - Rebrickable API key

Shared user data in `user_data/`:
- `auth_config.yaml` - User credentials (auto-generated, hashed passwords)
- `_audit_logs/` - Security audit logs

### Cache

Shared cache in `cache/`:
- Part images (PNG)
- Label files (LBX)

### Authentication

User credentials are managed in `user_data/auth_config.yaml` (auto-generated on first run with a demo user).

**Default demo user:**
- Username: `demo`
- Password: `demo123`

**Security features:**
- Passwords are hashed using bcrypt
- Session timeout after inactivity (default: 90 minutes)
- Rate limiting (account locked for 15 minutes after 5 failed attempts)
- Audit logging of authentication events
- Secure cookie-based session management

**Managing users:**
- Users can register through the web interface
- Passwords can be reset by authenticated users
- Admin can manually edit `user_data/auth_config.yaml` (passwords must be bcrypt hashed)

## Contributing

Contributions are welcome! This is a niche tool built for the LEGO community.

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## Troubleshooting

### Images not loading
- Check internet connection
- Verify cache directory permissions
- Try clearing cache and re-downloading

### Authentication issues
- Delete `user_data/auth_config.yaml` to reset to demo user
- Check file permissions on `user_data/` directory
- Review audit logs in `user_data/_audit_logs/audit.log`
- Verify `.env` file exists and contains `COOKIE_SECRET_KEY`

### Account locked
- Wait 15 minutes after 5 failed login attempts
- Check audit logs for security events
- Contact administrator if issue persists

### Docker issues
- Verify `APP_DATA_LOCATION` in `.env` file
- Check container logs: `docker-compose logs -f`
- Ensure ports are not already in use

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Rebrickable](https://rebrickable.com) for comprehensive LEGO part data
- [BrickArchitect](https://brickarchitect.com) for part images and labels
- The LEGO community for inspiration and feedback

## Support

For issues, questions, or feature requests, please open an issue on GitHub.

---

**Note**: This is an unofficial tool created by LEGO enthusiasts for LEGO enthusiasts. Not affiliated with the LEGO Group.
