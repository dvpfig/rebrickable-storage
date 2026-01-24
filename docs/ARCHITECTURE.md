# Software Architecture

## File System Structure

```
rebrickable-storage/
│
├── app.py                          # Main application entry
│
├── core/                           # Core modules
│   ├── auth.py                     # Authentication
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
│   ├── auth_config.yaml            # User credentials
│   ├── mappings/                   # Part mappings
│   ├── collection/                 # Default collection for demo session
│   └── colors.csv                  # Color data
│
├── user_data/                      # User-specific data
│   ├── {username1}/
│   │   ├── collection/             # User's uploaded files
│   │   └── session_data.json       # Saved progress
│   │
│   └── {username2}/
│       ├── collection/
│       └── session_data.json
│
└── cache/                          # Shared cache
│   ├── images/						# Cached images
    └── labels/                     # Cached labels
```

## Session State Management

```
┌──────────────────────────────────────────────────────────────┐
│                   Streamlit Session State                    │
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

## Deployment Architecture

```
Development:
┌────────────────────────────────────────┐
│  localhost:8501                        │
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
│                    Technology Stack                      │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  Frontend                                                │
│  └─ Streamlit (Web UI Framework)                         │
│                                                          │
│  Authentication                                          │
│  ├─ streamlit-authenticator (Auth library)               │
│  ├─ bcrypt (Password hashing)                            │
│  └─ PyYAML (Config management)                           │
│                                                          │
│  Data Processing                                         │
│  ├─ pandas (Data manipulation)                           │
│  └─ requests (HTTP client)                               │
│                                                          │
│  Storage                                                 │
│  ├─ Local filesystem (Development)                       │
│  └─ JSON (Session serialization)                         │
│                                                          │
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

┌─────────────────────┐
│  resources/         │──► Shared resources
│  - auth_config.yaml │    Authentication config
│  - colors.csv       │    Colors mapping
│  - collection/      │    Default collection for demo user
└─────────────────────┘

```

