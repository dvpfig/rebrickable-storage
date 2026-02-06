"""
HTML Report Generator
Converts the analysis output to an interactive HTML report.

Run: python docs/generate_html_report.py
"""

import json
from pathlib import Path
from datetime import datetime


def generate_html_report():
    """Generate an interactive HTML report from analysis data."""
    
    script_dir = Path(__file__).parent
    
    # Load analysis data
    json_file = script_dir / 'app_analysis.json'
    txt_file = script_dir / 'app_flow_analysis.txt'
    
    if not json_file.exists():
        print("Error: app_analysis.json not found. Run analyze_app.py first.")
        return
    
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    with open(txt_file, 'r', encoding='utf-8') as f:
        text_content = f.read()
    
    # Generate HTML
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Rebrickable Storage - Application Analysis</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            overflow: hidden;
        }}
        
        header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        
        header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
        }}
        
        header p {{
            font-size: 1.1em;
            opacity: 0.9;
        }}
        
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            padding: 30px;
            background: #f8f9fa;
        }}
        
        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            transition: transform 0.3s;
        }}
        
        .stat-card:hover {{
            transform: translateY(-5px);
        }}
        
        .stat-number {{
            font-size: 2.5em;
            font-weight: bold;
            color: #667eea;
            display: block;
        }}
        
        .stat-label {{
            color: #666;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        .tabs {{
            display: flex;
            background: #f8f9fa;
            border-bottom: 2px solid #ddd;
            padding: 0 30px;
        }}
        
        .tab {{
            padding: 15px 30px;
            cursor: pointer;
            border: none;
            background: none;
            font-size: 1em;
            color: #666;
            transition: all 0.3s;
            border-bottom: 3px solid transparent;
        }}
        
        .tab:hover {{
            color: #667eea;
        }}
        
        .tab.active {{
            color: #667eea;
            border-bottom-color: #667eea;
            font-weight: bold;
        }}
        
        .tab-content {{
            display: none;
            padding: 40px;
        }}
        
        .tab-content.active {{
            display: block;
        }}
        
        pre {{
            background: #1e1e1e;
            color: #d4d4d4;
            padding: 20px;
            border-radius: 8px;
            overflow-x: auto;
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 0.9em;
            line-height: 1.5;
        }}
        
        .function-list {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }}
        
        .function-card {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }}
        
        .function-name {{
            font-weight: bold;
            color: #667eea;
            margin-bottom: 5px;
        }}
        
        .function-module {{
            color: #666;
            font-size: 0.85em;
        }}
        
        .function-params {{
            color: #888;
            font-size: 0.85em;
            font-family: monospace;
        }}
        
        footer {{
            background: #f8f9fa;
            padding: 20px;
            text-align: center;
            color: #666;
            font-size: 0.9em;
        }}
        
        .timestamp {{
            color: #999;
            font-style: italic;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🧱 Rebrickable Storage</h1>
            <p>Application Architecture Analysis</p>
        </header>
        
        <div class="stats">
            <div class="stat-card">
                <span class="stat-number">{data['statistics']['total_functions']}</span>
                <span class="stat-label">Functions</span>
            </div>
            <div class="stat-card">
                <span class="stat-number">{data['statistics']['total_classes']}</span>
                <span class="stat-label">Classes</span>
            </div>
            <div class="stat-card">
                <span class="stat-number">{data['statistics']['session_keys']}</span>
                <span class="stat-label">Session Keys</span>
            </div>
            <div class="stat-card">
                <span class="stat-number">{len(set(f['module'] for f in data['functions'].values()))}</span>
                <span class="stat-label">Modules</span>
            </div>
            <div class="stat-card">
                <span class="stat-number">{data['statistics'].get('cached_images', 0)}</span>
                <span class="stat-label">Cached Images</span>
            </div>
            <div class="stat-card">
                <span class="stat-number">{data['statistics'].get('cached_labels', 0)}</span>
                <span class="stat-label">Cached Labels</span>
            </div>
            <div class="stat-card">
                <span class="stat-number">{data['statistics'].get('cache_size_mb', 0)} MB</span>
                <span class="stat-label">Images Cache</span>
            </div>
            <div class="stat-card">
                <span class="stat-number">{data['statistics'].get('labels_size_mb', 0)} MB</span>
                <span class="stat-label">Labels Cache</span>
            </div>
        </div>
        
        <div class="tabs">
            <button class="tab active" onclick="showTab('overview')">Overview</button>
            <button class="tab" onclick="showTab('architecture')">Architecture</button>
            <button class="tab" onclick="showTab('metrics')">Metrics</button>
            <button class="tab" onclick="showTab('functions')">Functions</button>
            <button class="tab" onclick="showTab('flow')">Flow Diagram</button>
        </div>
        
        <div id="overview" class="tab-content active">
            <h2>Application Overview</h2>
            <p>This report provides a comprehensive analysis of the Rebrickable Storage application architecture, 
            including execution flow, user experience journey, data structures, and module dependencies.</p>
            
            <h3 style="margin-top: 30px;">Key Components</h3>
            <ul style="margin-left: 20px; margin-top: 10px;">
                <li><strong>Core Modules:</strong> Authentication, path management, data preprocessing, image handling, color mapping, label generation</li>
                <li><strong>UI Modules:</strong> Theme management, layout helpers, summary tables</li>
                <li><strong>Data Flow:</strong> CSV upload → validation → merging → enrichment → display → export</li>
                <li><strong>Storage:</strong> User-specific data directories, shared image cache, session persistence</li>
            </ul>
            
            <h3 style="margin-top: 30px;">Session State Keys</h3>
            <div class="function-list">
                {''.join(f'<div class="function-card"><div class="function-name">{key}</div></div>' 
                         for key in sorted(data['session_state_keys']))}
            </div>
        </div>
        
        <div id="architecture" class="tab-content">
            <h2>Architecture Overview</h2>
            
            <h3>Technology Stack</h3>
            <ul style="margin-left: 20px; margin-top: 10px;">
                <li><strong>Frontend:</strong> Streamlit (Web UI Framework)</li>
                <li><strong>Authentication:</strong> streamlit-authenticator, bcrypt, PyYAML</li>
                <li><strong>Data Processing:</strong> pandas, requests</li>
                <li><strong>Storage:</strong> Local filesystem (Development), JSON (Session serialization)</li>
            </ul>
            
            <h3 style="margin-top: 30px;">Session State Management</h3>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 15px;">
                <div style="background: #f8f9fa; padding: 20px; border-radius: 8px;">
                    <h4>Global (Shared)</h4>
                    <ul style="margin-left: 20px; margin-top: 10px;">
                        <li>ba_mapping - Part number mappings</li>
                        <li>color_lookup - Color database</li>
                        <li>theme - UI theme preference</li>
                    </ul>
                </div>
                <div style="background: #f8f9fa; padding: 20px; border-radius: 8px;">
                    <h4>User-Specific (Isolated)</h4>
                    <ul style="margin-left: 20px; margin-top: 10px;">
                        <li>username - Current user</li>
                        <li>authenticated - Auth status</li>
                        <li>collection_df - User's collection</li>
                        <li>found_counts - Parts marked as found</li>
                        <li>locations_index - Location grouping</li>
                        <li>merged_df - Matched parts</li>
                    </ul>
                </div>
            </div>
            
            <h3 style="margin-top: 30px;">External Integrations</h3>
            <ul style="margin-left: 20px; margin-top: 10px;">
                <li><strong>Rebrickable API:</strong> Part data and mappings</li>
                <li><strong>BrickArchitect Images:</strong> Part images (cached locally)</li>
            </ul>
            
            <h3 style="margin-top: 30px;">Deployment</h3>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 15px;">
                <div style="background: #e3f2fd; padding: 20px; border-radius: 8px;">
                    <h4>Development</h4>
                    <ul style="margin-left: 20px; margin-top: 10px;">
                        <li>localhost:8501</li>
                        <li>File-based storage</li>
                        <li>Local user_data/</li>
                        <li>YAML configuration</li>
                    </ul>
                </div>
                <div style="background: #e8f5e9; padding: 20px; border-radius: 8px;">
                    <h4>Production (Recommended)</h4>
                    <ul style="margin-left: 20px; margin-top: 10px;">
                        <li>HTTPS with SSL/TLS</li>
                        <li>Database backend (PostgreSQL/MongoDB)</li>
                        <li>Cloud storage (S3/Azure Blob)</li>
                        <li>Environment secrets management</li>
                    </ul>
                </div>
            </div>
        </div>
        
        <div id="metrics" class="tab-content">
            <h2>Runtime Metrics & Data Dimensions</h2>
            
            <h3>Cache Statistics</h3>
            <div class="function-list">
                <div class="function-card">
                    <div class="function-name">Cached Images</div>
                    <div class="function-module">{data.get('runtime_metrics', {}).get('cached_images', 0)} files</div>
                </div>
                <div class="function-card">
                    <div class="function-name">Images Cache Size</div>
                    <div class="function-module">{data.get('runtime_metrics', {}).get('cached_images_size_mb', 0)} MB</div>
                </div>
                <div class="function-card">
                    <div class="function-name">Cached Labels</div>
                    <div class="function-module">{data.get('runtime_metrics', {}).get('cached_labels', 0)} files</div>
                </div>
                <div class="function-card">
                    <div class="function-name">Labels Cache Size</div>
                    <div class="function-module">{data.get('runtime_metrics', {}).get('cached_labels_size_mb', 0)} MB</div>
                </div>
            </div>
            
            <h3 style="margin-top: 30px;">Resource Data</h3>
            <div class="function-list">
                <div class="function-card">
                    <div class="function-name">Colors Database</div>
                    <div class="function-module">{data.get('runtime_metrics', {}).get('colors_csv_rows', 0)} rows × {data.get('runtime_metrics', {}).get('colors_csv_columns', 0)} columns</div>
                </div>
                <div class="function-card">
                    <div class="function-name">Part Mappings (BA ↔ RB)</div>
                    <div class="function-module">{data.get('runtime_metrics', {}).get('part_mappings_rows', 0)} rows × {data.get('runtime_metrics', {}).get('part_mappings_columns', 0)} columns</div>
                </div>
            </div>
            
            <h3 style="margin-top: 30px;">User Data</h3>
            <div class="function-list">
                <div class="function-card">
                    <div class="function-name">Total Users</div>
                    <div class="function-module">{data.get('runtime_metrics', {}).get('total_users', 0)} users</div>
                </div>
                <div class="function-card">
                    <div class="function-name">User Collection Files</div>
                    <div class="function-module">{data.get('runtime_metrics', {}).get('total_collection_files', 0)} files</div>
                </div>
                <div class="function-card">
                    <div class="function-name">Default Collection Files</div>
                    <div class="function-module">{data.get('runtime_metrics', {}).get('default_collection_files', 0)} files</div>
                </div>
            </div>
            
            <h3 style="margin-top: 30px;">Data Structure Dimensions</h3>
            <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin-top: 15px;">
                <h4>DataFrame Schemas</h4>
                <ul style="margin-left: 20px; margin-top: 10px;">
                    <li><strong>wanted_df:</strong> ~4-5 columns (Part, Color, Quantity, Location)</li>
                    <li><strong>collection_df:</strong> ~4 columns (Part, Color, Quantity, Location)</li>
                    <li><strong>merged_df:</strong> ~8-10 columns (includes Image URL, Color data)</li>
                </ul>
                
                <h4 style="margin-top: 20px;">Dictionary Structures</h4>
                <ul style="margin-left: 20px; margin-top: 10px;">
                    <li><strong>found_counts:</strong> {{(part, color, location): count}}</li>
                    <li><strong>locations_index:</strong> {{location: [image_urls]}}</li>
                    <li><strong>ba_mapping:</strong> {{ba_part_number: rb_part_number}}</li>
                    <li><strong>color_lookup:</strong> {{color_id: {{name, rgb, ...}}}}</li>
                </ul>
            </div>
        </div>
        
        <div id="functions" class="tab-content">
            <h2>Function Reference</h2>
            <p>All functions discovered in the application ({len(data['functions'])} total)</p>
            
            <div class="function-list">
                {''.join(f'''
                <div class="function-card">
                    <div class="function-name">{func_name.split('.')[-1]}</div>
                    <div class="function-module">📁 {func_data['file']}</div>
                    <div class="function-params">({', '.join(func_data['params'])})</div>
                </div>
                ''' for func_name, func_data in sorted(data['functions'].items()))}
            </div>
        </div>
        
        <div id="flow" class="tab-content">
            <h2>Application Flow Diagram</h2>
            <pre>{text_content}</pre>
        </div>
        
        <footer>
            <p class="timestamp">Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>Run <code>python docs/analyze_app.py</code> to update this report</p>
        </footer>
    </div>
    
    <script>
        function showTab(tabName) {{
            // Hide all tabs
            document.querySelectorAll('.tab-content').forEach(tab => {{
                tab.classList.remove('active');
            }});
            document.querySelectorAll('.tab').forEach(tab => {{
                tab.classList.remove('active');
            }});
            
            // Show selected tab
            document.getElementById(tabName).classList.add('active');
            event.target.classList.add('active');
        }}
    </script>
</body>
</html>
"""
    
    # Save HTML
    output_file = script_dir / 'app_analysis.html'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✓ HTML report generated: {output_file}")
    print(f"  Open in browser: file://{output_file.absolute()}")


if __name__ == '__main__':
    generate_html_report()
