# Application Flow Analyzer

## Overview

The `analyze_app.py` script provides automated analysis and visualization of the Rebrickable Storage application's architecture, execution flow, and data structures. It dynamically analyzes the codebase and generates up-to-date documentation.

## Features

The analyzer generates six main visualizations:

1. **Application Execution Flow** - Shows the main entry point, core modules, UI modules, and their key functions
2. **User Experience Flow** - Documents the 7-step user journey from login to export
3. **Data Structures & Dimensions** - Details session state, DataFrames, and file system organization
4. **Module Dependencies** - Maps the dependency graph between modules
5. **Architecture Overview** - Technology stack, session management, integrations, and deployment options
6. **Runtime Metrics** - Real-time statistics including cache sizes, resource dimensions, and user data

## Usage

### Run the Analyzer

```bash
# From project root
python docs/analyze_app.py
```

### Generate HTML Report (Optional)

For an interactive web-based view:

```bash
python docs/generate_html_report.py
```

Then open `docs/app_analysis.html` in your browser.

### Output Files

The analyzer generates three files in the `docs/` directory:

1. **app_flow_analysis.txt** - Human-readable text visualization with ASCII diagrams
2. **app_analysis.json** - Machine-readable JSON with detailed metadata
3. **app_analysis.html** - Interactive HTML report (generated separately)

### Example Output

```
================================================================================
APPLICATION EXECUTION FLOW
================================================================================

┌─ app.py (Main Entry Point)
│
├─┬─ CORE MODULES
│ ├─ core/auth.py
│     └─ __init__(self, config_path)
│     └─ _create_default_config(self)
│     └─ register_user(self)
...
```

## What It Analyzes

### Code Structure
- Function definitions and their parameters
- Class definitions and methods
- Import statements and dependencies
- Docstrings and documentation

### Data Flow
- Session state keys and their usage
- DataFrame operations and transformations
- File I/O operations
- API calls and external integrations

### Architecture
- Module organization
- Dependency relationships
- Function call chains
- Data structure dimensions

### Runtime Metrics (NEW)
- Cached images count and size
- Resource file dimensions (CSV/Excel rows and columns)
- User data statistics
- Data structure memory footprints

## Dynamic Updates

The analyzer uses Python's AST (Abstract Syntax Tree) parser to analyze the actual code, meaning:

- **Always current** - Reflects the latest code changes
- **No manual updates** - Automatically discovers new functions, classes, and modules
- **Accurate** - Based on actual code structure, not documentation

## Use Cases

### For Developers
- Understand the application architecture quickly
- Identify function dependencies before refactoring
- Document code changes automatically
- Onboard new team members

### For Documentation
- Generate up-to-date architecture diagrams
- Track application complexity over time
- Maintain accurate technical documentation
- Create visual aids for presentations

### For Code Review
- Verify module dependencies
- Check for circular dependencies
- Ensure proper separation of concerns
- Validate architectural decisions

## Extending the Analyzer

The script is modular and can be extended:

### Add New Visualizations

```python
class FlowVisualizer:
    def generate_custom_view(self):
        # Add your custom visualization logic
        pass
```

### Analyze Additional Patterns

```python
class CodeAnalyzer:
    def _extract_custom_pattern(self, node):
        # Add custom AST pattern matching
        pass
```

### Export to Different Formats

```python
# Add exporters for GraphViz, Mermaid, PlantUML, etc.
def export_to_graphviz(analyzer):
    # Generate .dot file
    pass
```

## Statistics Tracked

- Total functions across all modules
- Total classes and their methods
- Session state keys used
- Number of modules analyzed
- Import relationships
- DataFrame operations
- **Cached images count and size (NEW)**
- **Resource file dimensions (NEW)**
- **User data statistics (NEW)**
- **Data structure dimensions (NEW)**

## Technical Details

### Dependencies
- Python 3.x standard library only
- No external dependencies required
- Uses `ast` module for code parsing
- Uses `pathlib` for cross-platform paths

### Performance
- Analyzes entire codebase in < 1 second
- Lightweight AST parsing
- Minimal memory footprint
- Can be run frequently during development

### Compatibility
- Works on Windows, macOS, Linux
- Python 3.7+
- Handles syntax errors gracefully
- Skips non-Python files automatically

## Troubleshooting

### Script Fails to Run
```bash
# Ensure you're in the project root
cd /path/to/rebrickable-storage
python docs/analyze_app.py
```

### Missing Modules
The analyzer only processes files that exist. If modules are missing from the output, verify:
- Files exist in expected directories (`core/`, `ui/`, etc.)
- Files have `.py` extension
- Files contain valid Python syntax

### Incomplete Analysis
If some functions aren't detected:
- Check for syntax errors in source files
- Verify function definitions use standard `def` syntax
- Ensure files are not in `__pycache__` directories

## Future Enhancements

Potential additions to the analyzer:

- [ ] Generate interactive HTML visualizations
- [ ] Export to Mermaid diagram format
- [ ] Track code complexity metrics
- [ ] Identify unused functions
- [ ] Detect circular dependencies
- [ ] Generate API documentation
- [ ] Create sequence diagrams
- [ ] Measure test coverage gaps

## Related Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) - Detailed architecture documentation
- [structure.md](../.kiro/steering/structure.md) - Project structure guide
- [tech.md](../.kiro/steering/tech.md) - Technology stack details
- [product.md](../.kiro/steering/product.md) - Product overview

## License

Same as parent project (see LICENSE file in root directory).
