"""
Application Flow Analyzer
Generates visual representations of:
1. Main execution flow and function calls
2. User experience journey
3. Data structures and their dimensions

Run independently: python docs/analyze_app.py
"""

import ast
import os
from pathlib import Path
from collections import defaultdict
import json


class CodeAnalyzer:
    """Analyzes Python code to extract structure and flow information."""
    
    def __init__(self, root_dir):
        self.root_dir = Path(root_dir)
        self.functions = {}
        self.classes = {}
        self.imports = defaultdict(list)
        self.dataframes = {}
        self.session_state_keys = set()
        self.file_operations = []
        self.runtime_metrics = {}
        
    def analyze_file(self, filepath):
        """Parse a Python file and extract relevant information."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            tree = ast.parse(content)
            
            module_name = filepath.stem
            
            for node in ast.walk(tree):
                # Extract function definitions
                if isinstance(node, ast.FunctionDef):
                    self._extract_function(node, module_name, filepath)
                
                # Extract class definitions
                elif isinstance(node, ast.ClassDef):
                    self._extract_class(node, module_name, filepath)
                
                # Extract imports
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    self._extract_imports(node, module_name)
                
                # Extract session state usage
                elif isinstance(node, ast.Subscript):
                    self._extract_session_state(node)
                
                # Extract DataFrame operations
                elif isinstance(node, ast.Call):
                    self._extract_dataframe_ops(node, module_name)
                    
        except Exception as e:
            print(f"Error analyzing {filepath}: {e}")
    
    def _extract_function(self, node, module, filepath):
        """Extract function information."""
        func_name = f"{module}.{node.name}"
        
        # Get parameters
        params = [arg.arg for arg in node.args.args]
        
        # Get docstring
        docstring = ast.get_docstring(node) or ""
        
        # Find function calls within this function
        calls = []
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name):
                    calls.append(child.func.id)
                elif isinstance(child.func, ast.Attribute):
                    calls.append(f"{self._get_name(child.func.value)}.{child.func.attr}")
        
        self.functions[func_name] = {
            'params': params,
            'docstring': docstring,
            'calls': calls,
            'module': module,
            'file': str(filepath.relative_to(self.root_dir))
        }
    
    def _extract_class(self, node, module, filepath):
        """Extract class information."""
        class_name = f"{module}.{node.name}"
        
        methods = []
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                methods.append(item.name)
        
        self.classes[class_name] = {
            'methods': methods,
            'module': module,
            'file': str(filepath.relative_to(self.root_dir))
        }
    
    def _extract_imports(self, node, module):
        """Extract import statements."""
        if isinstance(node, ast.Import):
            for alias in node.names:
                self.imports[module].append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                for alias in node.names:
                    self.imports[module].append(f"{node.module}.{alias.name}")
    
    def _extract_session_state(self, node):
        """Extract session state keys."""
        if isinstance(node.value, ast.Attribute):
            if isinstance(node.value.value, ast.Name):
                if node.value.value.id == 'st' and node.value.attr == 'session_state':
                    if isinstance(node.slice, ast.Constant):
                        self.session_state_keys.add(node.slice.value)
    
    def _extract_dataframe_ops(self, node, module):
        """Extract DataFrame operations and dimensions."""
        func_name = self._get_name(node.func)
        
        # Look for pd.read_csv, pd.DataFrame, etc.
        if 'read_csv' in func_name or 'read_excel' in func_name:
            self.dataframes[module] = self.dataframes.get(module, [])
            self.dataframes[module].append({
                'operation': func_name,
                'type': 'load'
            })
    
    def _get_name(self, node):
        """Recursively get the full name of a node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        return ""
    
    def analyze_directory(self, directory):
        """Analyze all Python files in a directory."""
        dir_path = self.root_dir / directory
        if not dir_path.exists():
            return
        
        for py_file in dir_path.rglob('*.py'):
            if '__pycache__' not in str(py_file):
                self.analyze_file(py_file)
    
    def collect_runtime_metrics(self):
        """Collect runtime metrics about the application."""
        metrics = {}
        
        # Count cached images
        cache_images_dir = self.root_dir / 'cache' / 'images'
        if cache_images_dir.exists():
            image_files = list(cache_images_dir.glob('*.png')) + list(cache_images_dir.glob('*.jpg'))
            metrics['cached_images'] = len(image_files)
            # Calculate total size
            total_size = sum(f.stat().st_size for f in image_files)
            metrics['cached_images_size_mb'] = round(total_size / (1024 * 1024), 2)
        else:
            metrics['cached_images'] = 0
            metrics['cached_images_size_mb'] = 0
        
        # Count cached labels
        cache_labels_dir = self.root_dir / 'cache' / 'labels'
        if cache_labels_dir.exists():
            label_files = list(cache_labels_dir.glob('*.lbx'))
            metrics['cached_labels'] = len(label_files)
            # Calculate total size
            if label_files:
                total_label_size = sum(f.stat().st_size for f in label_files)
                metrics['cached_labels_size_mb'] = round(total_label_size / (1024 * 1024), 2)
            else:
                metrics['cached_labels_size_mb'] = 0
        else:
            metrics['cached_labels'] = 0
            metrics['cached_labels_size_mb'] = 0
        
        # Count CSV rows in resources
        colors_csv = self.root_dir / 'resources' / 'colors.csv'
        if colors_csv.exists():
            try:
                import pandas as pd
                df = pd.read_csv(colors_csv)
                metrics['colors_csv_rows'] = len(df)
                metrics['colors_csv_columns'] = len(df.columns)
            except:
                metrics['colors_csv_rows'] = 'N/A'
                metrics['colors_csv_columns'] = 'N/A'
        else:
            metrics['colors_csv_rows'] = 0
            metrics['colors_csv_columns'] = 0
        
        # Count part mappings
        mapping_file = self.root_dir / 'resources' / 'part number - BA vs RB - 2025-11-11.xlsx'
        if mapping_file.exists():
            try:
                import pandas as pd
                df = pd.read_excel(mapping_file)
                metrics['part_mappings_rows'] = len(df)
                metrics['part_mappings_columns'] = len(df.columns)
            except:
                metrics['part_mappings_rows'] = 'N/A'
                metrics['part_mappings_columns'] = 'N/A'
        else:
            metrics['part_mappings_rows'] = 0
            metrics['part_mappings_columns'] = 0
        
        # Count users
        user_data_dir = self.root_dir / 'user_data'
        if user_data_dir.exists():
            user_dirs = [d for d in user_data_dir.iterdir() if d.is_dir()]
            metrics['total_users'] = len(user_dirs)
            
            # Count collection files per user
            total_collections = 0
            for user_dir in user_dirs:
                collection_dir = user_dir / 'collection'
                if collection_dir.exists():
                    csv_files = list(collection_dir.glob('*.csv'))
                    total_collections += len(csv_files)
            metrics['total_collection_files'] = total_collections
        else:
            metrics['total_users'] = 0
            metrics['total_collection_files'] = 0
        
        # Count default collection files
        default_collection_dir = self.root_dir / 'resources' / 'collection'
        if default_collection_dir.exists():
            csv_files = list(default_collection_dir.glob('*.csv'))
            metrics['default_collection_files'] = len(csv_files)
        else:
            metrics['default_collection_files'] = 0
        
        self.runtime_metrics = metrics
        return metrics


class FlowVisualizer:
    """Generates visual representations of the application flow."""
    
    def __init__(self, analyzer):
        self.analyzer = analyzer
    
    def generate_execution_flow(self):
        """Generate execution flow diagram."""
        lines = []
        lines.append("=" * 80)
        lines.append("APPLICATION EXECUTION FLOW")
        lines.append("=" * 80)
        lines.append("")
        
        # Main entry point
        lines.append("┌─ app.py (Main Entry Point)")
        lines.append("│")
        
        # Core modules
        lines.append("├─┬─ CORE MODULES")
        core_modules = ['auth', 'paths', 'mapping', 'preprocess', 'images', 'colors', 'labels', 'lbx_merger']
        for i, module in enumerate(core_modules):
            is_last = i == len(core_modules) - 1
            prefix = "│ └─" if is_last else "│ ├─"
            
            module_key = f"{module}"
            matching_funcs = [f for f in self.analyzer.functions.keys() if f.startswith(module_key)]
            
            lines.append(f"{prefix} core/{module}.py")
            
            if matching_funcs:
                for func in matching_funcs[:3]:  # Show first 3 functions
                    func_name = func.split('.')[-1]
                    params = self.analyzer.functions[func]['params']
                    param_str = ', '.join(params[:3])  # Show first 3 params
                    if len(params) > 3:
                        param_str += ', ...'
                    
                    connector = "│   " if not is_last else "    "
                    lines.append(f"{connector}  └─ {func_name}({param_str})")
        
        lines.append("│")
        
        # UI modules
        lines.append("├─┬─ UI MODULES")
        ui_modules = ['theme', 'layout', 'summary']
        for i, module in enumerate(ui_modules):
            is_last = i == len(ui_modules) - 1
            prefix = "│ └─" if is_last else "│ ├─"
            lines.append(f"{prefix} ui/{module}.py")
        
        lines.append("│")
        
        # Resources
        lines.append("└─┬─ RESOURCES")
        lines.append("  ├─ auth_config.yaml (User credentials)")
        lines.append("  ├─ colors.csv (LEGO color database)")
        lines.append("  └─ part number mapping.xlsx (BA ↔ RB)")
        
        return '\n'.join(lines)
    
    def generate_user_flow(self):
        """Generate user experience flow diagram."""
        lines = []
        lines.append("")
        lines.append("=" * 80)
        lines.append("USER EXPERIENCE FLOW")
        lines.append("=" * 80)
        lines.append("")
        
        flow_steps = [
            ("1. LOGIN", [
                "User enters credentials",
                "AuthManager.login() validates",
                "Session initialized",
                "Redirect to main app"
            ]),
            ("2. UPLOAD WANTED PARTS", [
                "File uploader widget",
                "CSV validation",
                "Store in session_state['wanted_df']",
                "Display preview"
            ]),
            ("3. SELECT COLLECTION", [
                "List available collection files",
                "User selects files",
                "Load CSVs into session_state['collection_df']",
                "Merge collections"
            ]),
            ("4. PROCESS & MATCH", [
                "preprocess.merge_wanted_collection()",
                "mapping.apply_part_mappings()",
                "images.fetch_images()",
                "colors.add_color_data()",
                "Group by location"
            ]),
            ("5. BROWSE LOCATIONS", [
                "Display location cards",
                "Show part images",
                "Display quantities needed/available",
                "Expandable details"
            ]),
            ("6. MARK FOUND PARTS", [
                "User clicks 'Found' button",
                "Update session_state['found_counts']",
                "Recalculate remaining",
                "Visual feedback"
            ]),
            ("7. EXPORT RESULTS", [
                "Download merged CSV",
                "Generate location labels",
                "Create LBX file",
                "Save session progress"
            ])
        ]
        
        for step, details in flow_steps:
            lines.append(f"┌─ {step}")
            for i, detail in enumerate(details):
                is_last = i == len(details) - 1
                prefix = "└─" if is_last else "├─"
                lines.append(f"│  {prefix} {detail}")
            lines.append("│")
            if step != flow_steps[-1][0]:
                lines.append("▼")
                lines.append("│")
        
        return '\n'.join(lines)
    
    def generate_data_structures(self):
        """Generate data structures diagram."""
        lines = []
        lines.append("")
        lines.append("=" * 80)
        lines.append("DATA STRUCTURES & DIMENSIONS")
        lines.append("=" * 80)
        lines.append("")
        
        # Session State
        lines.append("┌─ SESSION STATE (st.session_state)")
        lines.append("│")
        
        session_keys = [
            ("wanted_df", "DataFrame", "Wanted parts list", "Columns: Part, Color, Quantity, Location"),
            ("collection_df", "DataFrame", "User's collection", "Columns: Part, Color, Quantity, Location"),
            ("merged_df", "DataFrame", "Matched parts", "wanted_df + collection_df merged"),
            ("found_counts", "Dict", "Tracking found parts", "{(part, color, location): count}"),
            ("locations_index", "Dict", "Location grouping", "{location: [image_urls]}"),
            ("expanded_loc", "str", "UI state", "Currently expanded location"),
            ("start_processing", "bool", "Trigger flag", "Initiates processing"),
            ("theme", "str", "UI preference", "'dark' or 'light'")
        ]
        
        for i, (key, dtype, desc, details) in enumerate(session_keys):
            is_last = i == len(session_keys) - 1
            prefix = "└─" if is_last else "├─"
            lines.append(f"│  {prefix} {key}: {dtype}")
            connector = "   " if is_last else "│  "
            lines.append(f"│  {connector}   └─ {desc}")
            lines.append(f"│  {connector}      └─ {details}")
        
        lines.append("│")
        
        # DataFrames
        lines.append("├─ DATAFRAMES")
        lines.append("│")
        
        dataframes = [
            ("wanted_df", [
                "Part Number (str)",
                "Color (str)",
                "Quantity Needed (int)",
                "Location (str, optional)"
            ]),
            ("collection_df", [
                "Part Number (str)",
                "Color (str)",
                "Quantity Available (int)",
                "Location (str)"
            ]),
            ("merged_df", [
                "Part Number (str)",
                "Color (str)",
                "Quantity Needed (int)",
                "Quantity Available (int)",
                "Location (str)",
                "Image URL (str)",
                "Color Name (str)",
                "Color RGB (str)"
            ])
        ]
        
        for i, (df_name, columns) in enumerate(dataframes):
            is_last = i == len(dataframes) - 1
            prefix = "└─" if is_last else "├─"
            lines.append(f"│  {prefix} {df_name}")
            connector = "   " if is_last else "│  "
            
            for j, col in enumerate(columns):
                col_is_last = j == len(columns) - 1
                col_prefix = "└─" if col_is_last else "├─"
                lines.append(f"│  {connector}   {col_prefix} {col}")
        
        lines.append("│")
        
        # File System
        lines.append("└─ FILE SYSTEM")
        lines.append("")
        
        fs_structure = [
            (r"user_data/{username}/", [
                "collection/*.csv - User's collection files",
                "session_data.json - Saved progress"
            ]),
            ("cache/", [
                "images/*.png - Cached part images",
                r"labels/*.png - Generated label images"
            ]),
            ("resources/", [
                "auth_config.yaml - User credentials (hashed)",
                "colors.csv - LEGO color database (~200 colors)",
                r"part number mapping.xlsx - BA↔RB mappings (~2000 parts)"
            ])
        ]
        
        for i, (path, files) in enumerate(fs_structure):
            is_last = i == len(fs_structure) - 1
            prefix = "└─" if is_last else "├─"
            lines.append(f"   {prefix} {path}")
            connector = "   " if is_last else "│  "
            
            for j, file_desc in enumerate(files):
                file_is_last = j == len(files) - 1
                file_prefix = "└─" if file_is_last else "├─"
                lines.append(f"   {connector}   {file_prefix} {file_desc}")
        
        return '\n'.join(lines)
    
    def generate_module_dependencies(self):
        """Generate module dependency diagram."""
        lines = []
        lines.append("")
        lines.append("=" * 80)
        lines.append("MODULE DEPENDENCIES")
        lines.append("=" * 80)
        lines.append("")
        
        # Build dependency graph
        deps = {
            'app.py': ['core.auth', 'core.paths', 'core.preprocess', 'core.images', 
                      'core.colors', 'core.labels', 'ui.theme', 'ui.layout', 'ui.summary'],
            'core.auth': ['core.paths'],
            'core.preprocess': ['core.mapping', 'core.paths'],
            'core.images': ['core.paths'],
            'core.labels': ['core.paths', 'core.images'],
            'core.lbx_merger': ['core.paths'],
            'ui.layout': [],
            'ui.summary': ['core.colors'],
            'ui.theme': []
        }
        
        lines.append("app.py")
        lines.append("│")
        
        for module, dependencies in deps.items():
            if module == 'app.py':
                continue
            
            indent = "├─" if module != list(deps.keys())[-1] else "└─"
            lines.append(f"{indent} {module}")
            
            if dependencies:
                connector = "│  " if module != list(deps.keys())[-1] else "   "
                for i, dep in enumerate(dependencies):
                    dep_prefix = "└─" if i == len(dependencies) - 1 else "├─"
                    lines.append(f"{connector}  {dep_prefix} → {dep}")
        
        return '\n'.join(lines)
    
    def generate_architecture_overview(self):
        """Generate architecture overview from ARCHITECTURE.md concepts."""
        lines = []
        lines.append("")
        lines.append("=" * 80)
        lines.append("ARCHITECTURE OVERVIEW")
        lines.append("=" * 80)
        lines.append("")
        
        # Technology Stack
        lines.append("┌─ TECHNOLOGY STACK")
        lines.append("│")
        lines.append("│  Frontend")
        lines.append("│  └─ Streamlit (Web UI Framework)")
        lines.append("│")
        lines.append("│  Authentication")
        lines.append("│  ├─ streamlit-authenticator (Auth library)")
        lines.append("│  ├─ bcrypt (Password hashing)")
        lines.append("│  └─ PyYAML (Config management)")
        lines.append("│")
        lines.append("│  Data Processing")
        lines.append("│  ├─ pandas (Data manipulation)")
        lines.append("│  └─ requests (HTTP client)")
        lines.append("│")
        lines.append("│  Storage")
        lines.append("│  ├─ Local filesystem (Development)")
        lines.append("│  └─ JSON (Session serialization)")
        lines.append("│")
        
        # Session State Management
        lines.append("├─ SESSION STATE MANAGEMENT")
        lines.append("│")
        lines.append("│  Global (Shared)")
        lines.append("│  ├─ ba_mapping - Part number mappings")
        lines.append("│  ├─ color_lookup - Color database")
        lines.append("│  └─ theme - UI theme preference")
        lines.append("│")
        lines.append("│  User-Specific (Isolated)")
        lines.append("│  ├─ username - Current user")
        lines.append("│  ├─ authenticated - Auth status")
        lines.append("│  ├─ collection_df - User's collection")
        lines.append("│  ├─ found_counts - Parts marked as found")
        lines.append("│  ├─ locations_index - Location grouping")
        lines.append("│  └─ merged_df - Matched parts")
        lines.append("│")
        
        # External Integrations
        lines.append("├─ EXTERNAL INTEGRATIONS")
        lines.append("│")
        lines.append("│  ┌─ Rebrickable API")
        lines.append("│  │  └─ Part data and mappings")
        lines.append("│  │")
        lines.append("│  └─ BrickArchitect Images")
        lines.append("│     └─ Part images (cached locally)")
        lines.append("│")
        
        # Deployment Architecture
        lines.append("└─ DEPLOYMENT")
        lines.append("")
        lines.append("   Development:")
        lines.append("   ├─ localhost:8501")
        lines.append("   ├─ File-based storage")
        lines.append("   ├─ Local user_data/")
        lines.append("   └─ YAML configuration")
        lines.append("")
        lines.append("   Production (Recommended):")
        lines.append("   ├─ HTTPS with SSL/TLS")
        lines.append("   ├─ Database backend (PostgreSQL/MongoDB)")
        lines.append("   ├─ Cloud storage (S3/Azure Blob)")
        lines.append("   └─ Environment secrets management")
        
        return '\n'.join(lines)
    
    def generate_runtime_metrics(self):
        """Generate runtime metrics section."""
        lines = []
        lines.append("")
        lines.append("=" * 80)
        lines.append("RUNTIME METRICS & DATA DIMENSIONS")
        lines.append("=" * 80)
        lines.append("")
        
        metrics = self.analyzer.runtime_metrics
        
        lines.append("┌─ CACHE STATISTICS")
        lines.append("│")
        lines.append(f"│  Cached Images: {metrics.get('cached_images', 0)} files")
        lines.append(f"│  Images Size: {metrics.get('cached_images_size_mb', 0)} MB")
        lines.append(f"│  Cached Labels: {metrics.get('cached_labels', 0)} files")
        lines.append(f"│  Labels Size: {metrics.get('cached_labels_size_mb', 0)} MB")
        lines.append("│")
        
        lines.append("├─ RESOURCE DATA")
        lines.append("│")
        lines.append(f"│  Colors Database:")
        lines.append(f"│  ├─ Rows: {metrics.get('colors_csv_rows', 0)}")
        lines.append(f"│  └─ Columns: {metrics.get('colors_csv_columns', 0)}")
        lines.append("│")
        lines.append(f"│  Part Mappings (BA ↔ RB):")
        lines.append(f"│  ├─ Rows: {metrics.get('part_mappings_rows', 0)}")
        lines.append(f"│  └─ Columns: {metrics.get('part_mappings_columns', 0)}")
        lines.append("│")
        
        lines.append("├─ USER DATA")
        lines.append("│")
        lines.append(f"│  Total Users: {metrics.get('total_users', 0)}")
        lines.append(f"│  User Collection Files: {metrics.get('total_collection_files', 0)}")
        lines.append(f"│  Default Collection Files: {metrics.get('default_collection_files', 0)}")
        lines.append("│")
        
        lines.append("└─ DATA STRUCTURE DIMENSIONS")
        lines.append("")
        lines.append("   DataFrame Schemas:")
        lines.append("   ├─ wanted_df: ~4-5 columns (Part, Color, Quantity, Location)")
        lines.append("   ├─ collection_df: ~4 columns (Part, Color, Quantity, Location)")
        lines.append("   └─ merged_df: ~8-10 columns (includes Image URL, Color data)")
        lines.append("")
        lines.append("   Dictionary Structures:")
        lines.append("   ├─ found_counts: {(part, color, location): count}")
        lines.append("   ├─ locations_index: {location: [image_urls]}")
        lines.append("   ├─ ba_mapping: {ba_part_number: rb_part_number}")
        lines.append("   └─ color_lookup: {color_id: {name, rgb, ...}}")
        
        return '\n'.join(lines)


def main():
    """Main execution function."""
    # Get project root (parent of docs/)
    script_dir = Path(__file__).parent
    root_dir = script_dir.parent
    
    print("Analyzing Rebrickable Storage Application...")
    print(f"Root directory: {root_dir}")
    print()
    
    # Initialize analyzer
    analyzer = CodeAnalyzer(root_dir)
    
    # Analyze main app
    app_file = root_dir / 'app.py'
    if app_file.exists():
        analyzer.analyze_file(app_file)
    
    # Analyze directories
    for directory in ['core', 'ui', 'resources']:
        analyzer.analyze_directory(directory)
    
    # Collect runtime metrics
    print("Collecting runtime metrics...")
    analyzer.collect_runtime_metrics()
    
    # Generate visualizations
    visualizer = FlowVisualizer(analyzer)
    
    # Create output
    output = []
    output.append(visualizer.generate_execution_flow())
    output.append(visualizer.generate_user_flow())
    output.append(visualizer.generate_data_structures())
    output.append(visualizer.generate_module_dependencies())
    output.append(visualizer.generate_architecture_overview())
    output.append(visualizer.generate_runtime_metrics())
    
    # Statistics
    output.append("")
    output.append("=" * 80)
    output.append("STATISTICS SUMMARY")
    output.append("=" * 80)
    output.append(f"Total Functions: {len(analyzer.functions)}")
    output.append(f"Total Classes: {len(analyzer.classes)}")
    output.append(f"Session State Keys: {len(analyzer.session_state_keys)}")
    output.append(f"Modules Analyzed: {len(set(f['module'] for f in analyzer.functions.values()))}")
    output.append(f"Cached Images: {analyzer.runtime_metrics.get('cached_images', 0)} ({analyzer.runtime_metrics.get('cached_images_size_mb', 0)} MB)")
    output.append(f"Cached Labels: {analyzer.runtime_metrics.get('cached_labels', 0)} ({analyzer.runtime_metrics.get('cached_labels_size_mb', 0)} MB)")
    
    # Print to console
    full_output = '\n'.join(output)
    print(full_output)
    
    # Save to file
    output_file = script_dir / 'app_flow_analysis.txt'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(full_output)
    
    print()
    print(f"✓ Analysis saved to: {output_file}")
    
    # Generate JSON summary for programmatic access
    summary = {
        'functions': analyzer.functions,
        'classes': analyzer.classes,
        'session_state_keys': list(analyzer.session_state_keys),
        'runtime_metrics': analyzer.runtime_metrics,
        'statistics': {
            'total_functions': len(analyzer.functions),
            'total_classes': len(analyzer.classes),
            'session_keys': len(analyzer.session_state_keys),
            'cached_images': analyzer.runtime_metrics.get('cached_images', 0),
            'cache_size_mb': analyzer.runtime_metrics.get('cached_images_size_mb', 0),
            'cached_labels': analyzer.runtime_metrics.get('cached_labels', 0),
            'labels_size_mb': analyzer.runtime_metrics.get('cached_labels_size_mb', 0)
        }
    }
    
    json_file = script_dir / 'app_analysis.json'
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)
    
    print(f"✓ JSON summary saved to: {json_file}")


if __name__ == '__main__':
    main()
