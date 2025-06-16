"""
Output formatting utilities for various export formats

Supports:
- JSON
- CSV
- HTML
- Excel
- PDF (requires additional dependencies)
"""

import json
import csv
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Union
import logging

import pandas as pd
from jinja2 import Template


logger = logging.getLogger(__name__)


def format_output(data: Union[Dict, List], format_type: str, 
                 filename: str = None, output_dir: str = 'output') -> str:
    """
    Format data for output in various formats
    
    Args:
        data: Data to format (dict or list)
        format_type: Output format (json, csv, html, excel, pdf)
        filename: Base filename (without extension)
        output_dir: Output directory
        
    Returns:
        Path to saved file
    """
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Generate filename if not provided
    if not filename:
        filename = f"output_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Format based on type
    if format_type.lower() == 'json':
        return _format_json(data, output_path / f"{filename}.json")
    elif format_type.lower() == 'csv':
        return _format_csv(data, output_path / f"{filename}.csv")
    elif format_type.lower() == 'html':
        return _format_html(data, output_path / f"{filename}.html")
    elif format_type.lower() == 'excel':
        return _format_excel(data, output_path / f"{filename}.xlsx")
    elif format_type.lower() == 'pdf':
        return _format_pdf(data, output_path / f"{filename}.pdf")
    else:
        raise ValueError(f"Unsupported format type: {format_type}")


def _format_json(data: Union[Dict, List], filepath: Path) -> str:
    """Save data as JSON"""
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2, default=str)
    return str(filepath)


def _format_csv(data: Union[Dict, List], filepath: Path) -> str:
    """Save data as CSV"""
    # Convert to DataFrame
    if isinstance(data, dict):
        # If dict has 'data' key with list, use that
        if 'data' in data and isinstance(data['data'], list):
            df = pd.DataFrame(data['data'])
        # If dict has lists as values, assume it's column data
        elif all(isinstance(v, list) for v in data.values()):
            df = pd.DataFrame(data)
        # Otherwise treat as single row
        else:
            df = pd.DataFrame([data])
    elif isinstance(data, list):
        # List of dicts
        if data and isinstance(data[0], dict):
            df = pd.DataFrame(data)
        # List of lists
        else:
            df = pd.DataFrame(data)
    else:
        raise ValueError("Data must be dict or list for CSV formatting")
    
    # Save to CSV
    df.to_csv(filepath, index=False)
    return str(filepath)


def _format_html(data: Union[Dict, List], filepath: Path) -> str:
    """Save data as HTML with nice formatting"""
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Network Monitoring Report</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 20px;
                background-color: #f5f5f5;
            }
            .header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px;
                border-radius: 10px;
                margin-bottom: 20px;
            }
            .content {
                background: white;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            }
            table {
                width: 100%;
                border-collapse: collapse;
                margin-top: 20px;
            }
            th, td {
                padding: 12px;
                text-align: left;
                border-bottom: 1px solid #ddd;
            }
            th {
                background-color: #667eea;
                color: white;
            }
            tr:hover {
                background-color: #f5f5f5;
            }
            .metadata {
                background: #e9ecef;
                padding: 15px;
                border-radius: 5px;
                margin-bottom: 20px;
            }
            .metadata h3 {
                margin-top: 0;
            }
            .timestamp {
                color: #6c757d;
                font-size: 0.9em;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Network Monitoring Report</h1>
            <p class="timestamp">Generated on: {{ timestamp }}</p>
        </div>
        
        <div class="content">
            {% if metadata %}
            <div class="metadata">
                <h3>Report Summary</h3>
                {% for key, value in metadata.items() %}
                <p><strong>{{ key }}:</strong> {{ value }}</p>
                {% endfor %}
            </div>
            {% endif %}
            
            {% if table_data %}
            <h2>Data</h2>
            <table>
                <thead>
                    <tr>
                        {% for header in headers %}
                        <th>{{ header }}</th>
                        {% endfor %}
                    </tr>
                </thead>
                <tbody>
                    {% for row in table_data %}
                    <tr>
                        {% for cell in row %}
                        <td>{{ cell }}</td>
                        {% endfor %}
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
            {% endif %}
            
            {% if raw_data %}
            <h2>Raw Data</h2>
            <pre>{{ raw_data }}</pre>
            {% endif %}
        </div>
    </body>
    </html>
    """
    
    # Prepare template data
    template_data = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    # Extract metadata if present
    if isinstance(data, dict) and 'metadata' in data:
        template_data['metadata'] = data['metadata']
        actual_data = data.get('data', data)
    else:
        actual_data = data
    
    # Convert data to table format
    if isinstance(actual_data, list) and actual_data:
        if isinstance(actual_data[0], dict):
            # List of dicts - convert to table
            headers = list(actual_data[0].keys())
            table_data = [[str(row.get(h, '')) for h in headers] for row in actual_data]
            template_data['headers'] = headers
            template_data['table_data'] = table_data
        else:
            # Raw data
            template_data['raw_data'] = json.dumps(actual_data, indent=2, default=str)
    else:
        # Raw data
        template_data['raw_data'] = json.dumps(actual_data, indent=2, default=str)
    
    # Render template
    template = Template(html_template)
    html_content = template.render(**template_data)
    
    # Save to file
    with open(filepath, 'w') as f:
        f.write(html_content)
    
    return str(filepath)


def _format_excel(data: Union[Dict, List], filepath: Path) -> str:
    """Save data as Excel with multiple sheets if needed"""
    with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
        # If data has multiple datasets, create multiple sheets
        if isinstance(data, dict):
            for sheet_name, sheet_data in data.items():
                if isinstance(sheet_data, list) and sheet_data:
                    df = pd.DataFrame(sheet_data)
                    # Limit sheet name to 31 characters (Excel limit)
                    sheet_name = sheet_name[:31]
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
                elif isinstance(sheet_data, dict):
                    df = pd.DataFrame([sheet_data])
                    sheet_name = sheet_name[:31]
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
        elif isinstance(data, list):
            df = pd.DataFrame(data)
            df.to_excel(writer, sheet_name='Data', index=False)
        else:
            df = pd.DataFrame([data])
            df.to_excel(writer, sheet_name='Data', index=False)
    
    return str(filepath)


def _format_pdf(data: Union[Dict, List], filepath: Path) -> str:
    """Save data as PDF (requires additional dependencies)"""
    # For now, create HTML and note that PDF conversion requires additional tools
    html_path = filepath.with_suffix('.html')
    _format_html(data, html_path)
    
    logger.warning(f"PDF output requested but not implemented. HTML saved to {html_path}")
    logger.warning("To convert to PDF, install wkhtmltopdf or use a browser's print-to-PDF feature")
    
    return str(html_path)