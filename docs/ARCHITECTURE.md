# Multi-User Authentication Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Streamlit App                            │
│                          (app.py)                                │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
                  ┌─────────────────┐
                  │ Authentication  │
                  │    Required?    │
                  └────────┬────────┘
                           │
                ┌──────────┴──────────┐
                │                     │
             No │                     │ Yes
                ▼                     ▼
        ┌───────────────┐     ┌──────────────┐
        │  Login/       │     │  Main App    │
        │  Register UI  │     │  Interface   │
        └───────────────┘     └──────────────┘
```

## Authentication Flow

```
┌─────────────┐
│   User      │
│   Access    │
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│ Check Session   │◄──── Cookies
│ State           │
└─────┬───────────┘
      │
      ├─ Authenticated ────────┐
      │                        │
      └─ Not Authenticated     │
            │                  │
            ▼                  ▼
    ┌──────────────┐   ┌──────────────┐
    │   Show       │   │   Load       │
    │   Login      │   │   User       │
    │   Page       │   │   Data       │
    └──────┬───────┘   └──────┬───────┘
           │                  │
           │                  ▼
           │          ┌──────────────┐
           │          │   Show       │
           └─────────►│   Main App   │
                      └──────────────┘
```

## Data Isolation Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Application Layer                        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    AuthManager (core/auth.py)                │
│  - User authentication                                       │
│  - Session management                                        │
│  - Data path resolution                                      │
└────────────┬────────────────────────────────────────────────┘
             │
             ├──────────────────────┬──────────────────────┐
             │                      │                      │
             ▼                      ▼                      ▼
    ┌────────────────┐    ┌────────────────┐    ┌────────────────┐
    │   User 1       │    │   User 2       │    │   User N       │
    ├────────────────┤    ├────────────────┤    ├────────────────┤
    │ user_data/user1│    │ user_data/user2│    │ user_data/userN│
    │ ├─collection/  │    │ ├─collection/  │    │ ├─collection/  │
    │ └─session_data │    │ └─session_data │    │ └─session_data │
    └────────────────┘    └────────────────┘    └────────────────┘
```

## File System Structure

```
rebrickable-storage/
│
├── app.py                          # Main application entry
│
├── core/                           # Core modules
│   ├── auth.py                     # ★ NEW: Authentication
│   ├── paths.py                    # Path management
│   ├── mapping.py                  # Part mapping
│   ├── preprocess.py               # Data processing
│   ├── images.py                   # Image handling
│   └── colors.py                   # Color management
│
├── ui/                             # UI components
│   ├── theme.py                    # Theming
│   ├── layout.py                   # Layout helpers
│   └── summary.py                  # Summary views
│
├── resources/                      # Shared resources
│   ├── auth_config.yaml           # ★ NEW: User credentials
│   ├── mappings/                   # Part mappings
│   └── colors.csv                  # Color data
│
├── user_data/                      # ★ NEW: User-specific data
│   ├── {username1}/
│   │   ├── collection/             # User's uploaded files
│   │   └── session_data.json       # Saved progress
│   │
│   └── {username2}/
│       ├── collection/
│       └── session_data.json
│
└── cache/                          # Shared cache
    └── images/                     # Cached images
```

## Session State Management

```
┌──────────────────────────────────────────────────────────────┐
│                   Streamlit Session State                     │
├──────────────────────────────────────────────────────────────┤
│  Global (Shared)              │  User-Specific (Isolated)    │
├───────────────────────────────┼──────────────────────────────┤
│  • ba_mapping                 │  • username                  │
│  • color_lookup               │  • name                      │
│  • theme                      │  • authenticated             │
│                               │  • collection_df             │
│                               │  • found_counts              │
│                               │  • locations_index           │
│                               │  • merged_df                 │
└───────────────────────────────┴──────────────────────────────┘
```

## Authentication Component Details

```
┌────────────────────────────────────────────────────────────────┐
│                        AuthManager Class                        │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Configuration                                                  │
│  ├─ config_path: Path to auth_config.yaml                     │
│  └─ user_data_dir: Path to user_data/ directory               │
│                                                                 │
│  Methods                                                        │
│  ├─ login() → bool                                             │
│  │   └─ Validates credentials, creates session                │
│  │                                                              │
│  ├─ logout()                                                   │
│  │   └─ Clears session, removes cookies                       │
│  │                                                              │
│  ├─ register_user()                                            │
│  │   └─ Creates new user, hashes password                     │
│  │                                                              │
│  ├─ get_user_data_path(username) → Path                       │
│  │   └─ Returns user-specific directory                       │
│  │                                                              │
│  ├─ save_user_session(username, session_data)                 │
│  │   └─ Persists found_counts & locations_index               │
│  │                                                              │
│  ├─ load_user_session(username) → dict                        │
│  │   └─ Restores saved session data                           │
│  │                                                              │
│  └─ reset_password()                                           │
│      └─ Updates password in config                             │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

## Data Flow Diagram

```
┌─────────┐
│  User   │
│ Login   │
└────┬────┘
     │
     ▼
┌─────────────────┐
│ Authenticate    │
│ (streamlit-     │
│  authenticator) │
└────┬────────────┘
     │
     ├─ Success ─────────┐
     │                   │
     └─ Failure          │
         │               │
         ▼               ▼
    ┌────────┐    ┌──────────────┐
    │ Reject │    │ Create User  │
    │        │    │ Session      │
    └────────┘    └──────┬───────┘
                         │
                         ▼
                  ┌──────────────┐
                  │ Get User     │
                  │ Data Path    │
                  └──────┬───────┘
                         │
                         ▼
                  ┌──────────────┐
                  │ Load User    │
                  │ Collection   │
                  └──────┬───────┘
                         │
                         ▼
                  ┌──────────────┐
                  │ Show Main    │
                  │ App          │
                  └──────────────┘
```

## Security Architecture

```
┌────────────────────────────────────────────────────────────┐
│                      Security Layers                        │
├────────────────────────────────────────────────────────────┤
│                                                             │
│  Layer 1: Password Security                                │
│  ├─ Bcrypt hashing (cost factor 12)                       │
│  ├─ Salt per password                                      │
│  └─ No plaintext storage                                   │
│                                                             │
│  Layer 2: Session Security                                 │
│  ├─ Signed cookies                                         │
│  ├─ Secret key for signing                                 │
│  ├─ 30-day expiry                                          │
│  └─ HTTPS recommended for production                       │
│                                                             │
│  Layer 3: Data Isolation                                   │
│  ├─ Separate directories per user                          │
│  ├─ Path validation                                        │
│  ├─ No cross-user data access                             │
│  └─ File system permissions                                │
│                                                             │
│  Layer 4: Application Security                             │
│  ├─ Authentication check on every page                     │
│  ├─ Session state validation                               │
│  └─ Auto-redirect if not authenticated                     │
│                                                             │
└────────────────────────────────────────────────────────────┘
```

## Concurrent User Handling

```
┌──────────────────────────────────────────────────────────────┐
│                    Concurrent Users                           │
└──────────────────────────────────────────────────────────────┘

Browser 1 (User A)          Browser 2 (User B)          Browser 3 (User C)
      │                           │                           │
      ▼                           ▼                           ▼
┌─────────────┐            ┌─────────────┐            ┌─────────────┐
│  Session A  │            │  Session B  │            │  Session C  │
└──────┬──────┘            └──────┬──────┘            └──────┬──────┘
       │                          │                          │
       ▼                          ▼                          ▼
┌─────────────┐            ┌─────────────┐            ┌─────────────┐
│  User A     │            │  User B     │            │  User C     │
│  Data       │            │  Data       │            │  Data       │
└─────────────┘            └─────────────┘            └─────────────┘

No conflicts - completely isolated!
```

## Deployment Architecture

```
Development:
┌────────────────────────────────────────┐
│  localhost:8501                         │
│  ├─ File-based storage                 │
│  ├─ Local user_data/                   │
│  └─ YAML configuration                 │
└────────────────────────────────────────┘

Production (Recommended):
┌────────────────────────────────────────┐
│  https://your-domain.com               │
│  ├─ Database backend                   │
│  │   └─ PostgreSQL/MongoDB             │
│  ├─ Cloud storage                      │
│  │   └─ S3/Azure Blob                  │
│  ├─ Environment secrets                │
│  │   └─ Key management                 │
│  └─ SSL/TLS encryption                 │
└────────────────────────────────────────┘
```

## Technology Stack

```
┌──────────────────────────────────────────────────────────┐
│                    Technology Stack                       │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  Frontend                                                 │
│  └─ Streamlit (Web UI Framework)                         │
│                                                           │
│  Authentication                                           │
│  ├─ streamlit-authenticator (Auth library)              │
│  ├─ bcrypt (Password hashing)                            │
│  └─ PyYAML (Config management)                           │
│                                                           │
│  Data Processing                                          │
│  ├─ pandas (Data manipulation)                           │
│  └─ requests (HTTP client)                               │
│                                                           │
│  Storage                                                  │
│  ├─ Local filesystem (Development)                       │
│  └─ JSON (Session serialization)                         │
│                                                           │
└──────────────────────────────────────────────────────────┘
```

## Integration Points

```
External Systems:
┌────────────────┐
│  Rebrickable   │──► Part data, mappings
│  API           │
└────────────────┘

┌────────────────┐
│ BrickArchitect │──► Part images
│  Images        │
└────────────────┘

Internal Modules:
┌────────────────┐
│  core/         │──► Business logic
│  - auth.py     │    Authentication
│  - mapping.py  │    Part mapping
│  - colors.py   │    Color data
└────────────────┘

┌────────────────┐
│  ui/           │──► User interface
│  - theme.py    │    Styling
│  - layout.py   │    Components
└────────────────┘
```

## Performance Considerations

```
┌──────────────────────────────────────────────────────────┐
│                  Performance Factors                      │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  Per-User Load                                            │
│  ├─ Session state: ~1-5 MB per user                     │
│  ├─ Collection files: Variable size                      │
│  └─ Session data: ~100 KB per user                       │
│                                                           │
│  Shared Resources                                         │
│  ├─ Image cache: Shared across users                    │
│  ├─ Mapping data: Loaded once                           │
│  └─ Color lookup: Shared reference                       │
│                                                           │
│  Concurrency                                              │
│  ├─ Streamlit: One thread per session                   │
│  ├─ File I/O: Sequential per user                       │
│  └─ No database locking issues                           │
│                                                           │
└──────────────────────────────────────────────────────────┘
```

---

This architecture provides a scalable foundation for multi-user support while maintaining data isolation and security.
