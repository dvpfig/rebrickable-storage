# Self-Hosting Rebrickable Storage with Docker

This guide explains how to self-host the Rebrickable Storage application using Docker Compose.

## Prerequisites

- Docker Engine installed
- Docker Compose installed

## Quick Start

1. Create a directory for your application data:
```bash
mkdir -p /path/to/your/data/rebrickable-storage/{data,cache}
```

2. Create a `.env` file in the same directory as `docker-compose.yml`:
```bash
cd docker
nano .env
```

3. Add the following environment variables to `.env`:
```env
# Required: Base path for application data
APP_DATA_LOCATION=/path/to/your/data

# Optional: User and group IDs (uncomment if needed)
#PUID=1000
#PGID=1000

# Optional: Timezone (uncomment if needed)
#TZ=America/New_York
```

4. Start the application:
```bash
docker-compose up -d
```

5. Access the application at `http://localhost:8501`

## Environment Variables

### Required Variables

- `APP_DATA_LOCATION`: Base directory path where application data will be stored
  - Example: `/home/user/appdata` or `C:\AppData` (Windows)
  - The application will create subdirectories: `rebrickable-storage/data` and `rebrickable-storage/cache`

### Optional Variables

- `PUID`: User ID for file permissions (default: container default)
- `PGID`: Group ID for file permissions (default: container default)
- `TZ`: Timezone for the container (default: UTC)
  - Examples: `America/New_York`, `Europe/London`, `Asia/Tokyo`

## Directory Structure

After setup, your data directory will look like this:

```
/path/to/your/data/
└── rebrickable-storage/
    ├── data/          # User data and session files
    └── cache/         # Cached images and labels
```

## Configuration Examples

### Linux/macOS Example

`.env` file:
```env
APP_DATA_LOCATION=/home/username/docker-data
PUID=1000
PGID=1000
TZ=America/Los_Angeles
```

## Port Configuration

By default, the application runs on port `8501`. To change this, edit the `ports` section in `docker-compose.yml`:

```yaml
ports:
  - "8080:8501"  # Access via http://localhost:8080
```

## Default Credentials

The application includes a demo account:
- Username: `demo`
- Password: `demo123`

You can create additional users through the registration interface or by editing the `user_data/auth_config.yaml` file in the data directory.
