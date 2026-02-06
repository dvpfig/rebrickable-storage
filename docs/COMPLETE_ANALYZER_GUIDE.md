# Complete Application Analyzer Guide

## Overview

The Rebrickable Storage Application Analyzer is a comprehensive tool that dynamically analyzes your codebase and generates detailed visualizations of architecture, execution flow, and runtime metrics.

## Quick Start

```bash
# Generate all analysis files
python docs/analyze_app.py
python docs/generate_html_report.py

# View results
# - Text: docs/app_flow_analysis.txt
# - JSON: docs/app_analysis.json  
# - HTML: docs/app_analysis.html (open in browser)
```

## What You Get

### 1. Application Execution Flow
Visual representation of:
- Main entry point (app.py)
- Core modules (auth, paths, mapping, preprocess, images, colors, labels, lbx_merger)
- UI modules (theme, layout, summary)
- Key functions in each module

### 2. User Experience Flow
7-step user journey:
1. Login
2. Upload wanted parts
3. Select collection
4. Process & match
5. Browse locations
6. Mark found parts
7. Export results

### 3. Data Structures & Dimensions
Complete documentation of:
- Session state keys (11 tracked)
- DataFrame schemas (wanted_df, collection_df, merged_df)
- Dictionary structures (found_counts, locations_index, ba_mapping, color_lookup)
- File system organization

### 4. Module Dependencies
Dependency graph showing:
- app.py dependencies
- Core module relationships
- UI module connections
- Import chains

### 5. Architecture Overview (NEW)
Comprehensive architecture documentation:
- **Technology Stack**
  - Frontend: Streamlit
  - Authentication: streamlit-authenticator, bcrypt, PyYAML
  - Data Processing: pandas, requests
  - Storage: Local filesystem, JSON

- **Session State Management**
  - Global (Shared): ba_mapping, color_lookup, theme
  - User-Specific: username, authenticated, collection_df, found_counts, locations_index, merged_df

- **External Integrations**
  - Rebrickable API
  - BrickArchitect Images

- **Deployment Options**
  - Development: localhost:8501, file-based
  - Production: HTTPS, database, cloud storage

### 6. Runtime Metrics (NEW)
Real-time statistics:

#### Cache Statistics
- Cached Images: 1,815 files (13.61 MB)
- Cached Labels: 0 files

#### Resource Data
- Colors Database: 273 rows × 8 columns
- Part Mappings: 4,342 rows × 14 columns

#### User Data
- Total Users: 1
- User Collection Files: 0
- Default Collection Files: 14

#### Data Structure Dimensions
- DataFrame column counts
- Dictionary structure patterns
- Memory footprint estimates

## Output Formats

### Text Report (app_flow_analysis.txt)
- ASCII diagrams
- Tree structures
- Easy to read in terminal
- Version control friendly
- ~10 KB file size

### JSON Data (app_analysis.json)
- Structured data
- Programmatic access
- All functions with parameters
- All classes with methods
- Runtime metrics
- ~27 KB file size

### HTML Report (app_analysis.html)
- Interactive web interface
- Tabbed navigation (5 tabs)
- Searchable function reference
- Visual statistics dashboard
- Color-coded metric cards
- ~41 KB file size

## Statistics Dashboard

The analyzer tracks and displays:

| Metric | Current Value |
|--------|---------------|
| Total Functions | 47 |
| Total Classes | 3 |
| Session State Keys | 11 |
| Modules Analyzed | 12 |
| Cached Images | 1,815 |
| Cache Size | 13.61 MB |
| Total Users | 1 |
| Color Entries | 273 |

## Use Cases

### For Development
- Understand codebase quickly
- Identify refactoring opportunities
- Track complexity growth
- Document architecture automatically
- Monitor cache growth
- Optimize resource usage

### For Onboarding
- Visual overview for new developers
- Function reference with parameters
- Module dependency understanding
- Data flow comprehension
- Architecture patterns
- Deployment options

### For Documentation
- Always up-to-date diagrams
- Multiple format options
- Shareable HTML reports
- Version-controlled analysis
- Architecture reference
- Metrics tracking

### For Operations
- Monitor cache sizes
- Track user adoption
- Identify resource usage
- Plan capacity
- Optimize performance
- Troubleshoot issues

## How It Works

### Code Analysis (AST Parsing)
1. Parses Python files using `ast` module
2. Extracts functions, classes, imports
3. Identifies session state usage
4. Maps dependencies
5. Discovers data structures

### Runtime Metrics Collection
1. Scans `cache/images/` for cached files
2. Counts files and calculates sizes
3. Reads CSV/Excel dimensions from `resources/`
4. Scans `user_data/` for user directories
5. Counts collection files per user

### Visualization Generation
1. Creates ASCII diagrams for text output
2. Generates structured JSON data
3. Builds interactive HTML with tabs
4. Adds statistics dashboard
5. Includes architecture overview

## Technical Details

### Dependencies
- Python 3.7+ standard library only
- `ast` - Code parsing
- `pathlib` - File operations
- `json` - JSON output
- `pandas` - CSV/Excel reading (already in requirements.txt)

### Performance
- Analyzes entire codebase in < 2 seconds
- Lightweight memory footprint
- Can run on every commit
- No build step required

### Compatibility
- Works on Windows, macOS, Linux
- Python 3.7+
- Handles syntax errors gracefully
- Skips non-Python files automatically

## Files in the Analyzer System

### Scripts
1. **analyze_app.py** (Main analyzer)
   - Parses code with AST
   - Collects runtime metrics
   - Generates text visualizations
   - Creates JSON output

2. **generate_html_report.py** (HTML generator)
   - Reads JSON data
   - Creates interactive HTML
   - Adds tabbed navigation
   - Builds statistics dashboard

### Documentation
3. **README_ANALYZER.md** - Complete documentation
4. **QUICK_START_ANALYZER.md** - Quick reference
5. **ANALYZER_SUMMARY.md** - Original overview
6. **ANALYZER_UPDATE_SUMMARY.md** - Enhancement details
7. **COMPLETE_ANALYZER_GUIDE.md** - This file

### Generated Output
8. **app_flow_analysis.txt** - Text visualizations
9. **app_analysis.json** - Structured data
10. **app_analysis.html** - Interactive report

## Maintenance

### No Maintenance Required
The analyzer dynamically analyzes current code. Simply run it whenever you want updated documentation.

### Recommended Schedule
- After adding new features
- Before major releases
- During code reviews
- Weekly for active projects
- On-demand for documentation

### Updating the Analyzer
If you add new modules or change structure:
1. No changes needed - analyzer auto-discovers
2. Run analyzer to see new structure
3. Commit updated output files

## Advanced Usage

### Integrate with CI/CD
```bash
# In your CI pipeline
python docs/analyze_app.py
python docs/generate_html_report.py

# Commit results
git add docs/app_*.txt docs/app_*.json docs/app_*.html
git commit -m "Update architecture analysis"
```

### Track Metrics Over Time
```bash
# Save metrics with timestamp
python docs/analyze_app.py
cp docs/app_analysis.json "metrics/analysis_$(date +%Y%m%d).json"
```

### Generate Custom Reports
```python
import json

# Load analysis data
with open('docs/app_analysis.json') as f:
    data = json.load(f)

# Access metrics
print(f"Cache size: {data['runtime_metrics']['cached_images_size_mb']} MB")
print(f"Functions: {data['statistics']['total_functions']}")
```

## Troubleshooting

### Script Fails to Run
```bash
# Ensure you're in project root
cd /path/to/rebrickable-storage
python docs/analyze_app.py
```

### Missing Metrics
If some metrics show 0:
- Check that directories exist (cache/, resources/, user_data/)
- Verify CSV/Excel files are present
- Ensure files have correct extensions (.csv, .xlsx, .png)

### Incomplete Analysis
If functions aren't detected:
- Check for syntax errors in source files
- Verify files have .py extension
- Ensure files aren't in __pycache__

## Future Enhancements

Potential additions:
- [ ] Historical metrics tracking
- [ ] Trend charts and graphs
- [ ] Alert on threshold violations
- [ ] Version comparison
- [ ] Export to monitoring systems
- [ ] Database metrics (when using DB)
- [ ] API call statistics
- [ ] Memory usage profiling
- [ ] Code complexity metrics
- [ ] Test coverage integration

## Support

For issues or questions:
1. Check this guide
2. Review [README_ANALYZER.md](README_ANALYZER.md)
3. Examine [QUICK_START_ANALYZER.md](QUICK_START_ANALYZER.md)
4. Look at generated output files

## Related Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) - Application architecture
- [structure.md](../.kiro/steering/structure.md) - Project structure
- [tech.md](../.kiro/steering/tech.md) - Technology stack
- [product.md](../.kiro/steering/product.md) - Product overview

## License

Same as parent project (see LICENSE file in root directory).

---

**Last Updated**: February 6, 2026  
**Analyzer Version**: 2.0 (with Architecture & Metrics)  
**Python Version**: 3.7+
