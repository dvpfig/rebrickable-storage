# Quick Start: Application Analyzer

## What is it?

A dynamic code analysis tool that visualizes your application's architecture, execution flow, and data structures. It automatically updates as your code evolves.

## Quick Commands

```bash
# Generate text analysis
python docs/analyze_app.py

# Generate HTML report
python docs/generate_html_report.py

# View HTML report
# Open docs/app_analysis.html in your browser
```

## What You Get

### 1. Text Report (`app_flow_analysis.txt`)
- ASCII diagrams of execution flow
- User experience journey (7 steps)
- Data structures with dimensions
- Module dependency graph
- Statistics summary

### 2. JSON Data (`app_analysis.json`)
- All functions with parameters
- All classes with methods
- Session state keys
- Module relationships
- Programmatic access to analysis

### 3. HTML Report (`app_analysis.html`)
- Interactive web interface
- Searchable function reference
- Visual statistics cards
- Tabbed navigation
- Beautiful styling

## When to Run

- After adding new features
- Before code reviews
- When onboarding new developers
- For documentation updates
- To track complexity growth

## Example Output

```
================================================================================
APPLICATION EXECUTION FLOW
================================================================================

┌─ app.py (Main Entry Point)
│
├─┬─ CORE MODULES
│ ├─ core/auth.py
│     └─ __init__(self, config_path)
│     └─ register_user(self)
...
```

## Tips

- Run frequently - it's fast (< 1 second)
- Commit the output files to track changes over time
- Use JSON output for custom tooling
- Share HTML report with team members
- No external dependencies required

## Full Documentation

See [README_ANALYZER.md](README_ANALYZER.md) for complete details.
