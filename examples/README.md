# Network Monitoring Suite - Examples

This directory contains example configurations and usage patterns for the Network Monitoring Suite.

## Configuration Examples

### Basic Configuration

```yaml
# config/config.yaml
devices:
  - host: 192.168.1.1
    device_type: cisco_ios
    vendor: cisco
    site: main-office
    role: core

health_monitoring:
  thresholds:
    cpu: {warning: 70, critical: 85}
    memory: {warning: 70, critical: 85}
```

### Environment Variables

```bash
# .env
NETWORK_USERNAME=admin
NETWORK_PASSWORD=your_secure_password
ENABLE_PASSWORD=your_enable_password

EMAIL_USERNAME=alerts@company.com
EMAIL_PASSWORD=email_app_password
```

## Usage Examples

### 1. Daily Health Check

```bash
# Run health check for all devices
python run_monitoring.py --health --output-formats html excel

# Check specific site
python run_monitoring.py --health --site datacenter1

# With email alerts
python run_monitoring.py --health --send-alerts
```

### 2. Device Discovery

```bash
# Discover devices in a subnet
python scripts/device_discovery.py --ranges 192.168.1.0/24

# Multiple ranges
python scripts/device_discovery.py --ranges 192.168.1.0/24 10.0.0.0/16

# Incremental discovery
python scripts/device_discovery.py --ranges 192.168.1.0/24 --incremental
```

### 3. Comprehensive Network Audit

```bash
# Run all monitoring scripts
python run_monitoring.py --all --output-formats excel html pdf

# Filter by vendor
python run_monitoring.py --all --vendor cisco
```

### 4. Continuous Monitoring

```bash
# Monitor changes every 5 minutes
python run_monitoring.py --change --continuous --interval 300
```

## Integration Examples

### Cron Job Setup

```bash
# /etc/cron.d/network-monitoring

# Daily health check at 6 AM
0 6 * * * /usr/bin/python3 /opt/netmiko-monitoring/run_monitoring.py --health --send-alerts

# Hourly interface monitoring
0 * * * * /usr/bin/python3 /opt/netmiko-monitoring/run_monitoring.py --interface

# Weekly comprehensive audit
0 2 * * 0 /usr/bin/python3 /opt/netmiko-monitoring/run_monitoring.py --all --output-formats excel html
```

### Ansible Integration

```yaml
---
- name: Run Network Health Check
  hosts: localhost
  tasks:
    - name: Execute health check
      command: python3 /opt/netmiko-monitoring/run_monitoring.py --health --output-formats json
      register: health_result

    - name: Parse results
      set_fact:
        health_data: "{{ (health_result.stdout | from_json).health_data }}"

    - name: Check for critical devices
      debug:
        msg: "Critical device: {{ item.hostname }}"
      loop: "{{ health_data }}"
      when: item.overall_status == "critical"
```

### Python Script Integration

```python
#!/usr/bin/env python3
"""
Example: Integrate monitoring suite into custom scripts
"""

import subprocess
import json
from pathlib import Path

def run_health_check():
    """Run health check and process results"""
    
    # Run the health check
    result = subprocess.run([
        'python3', 'run_monitoring.py',
        '--health',
        '--output-formats', 'json'
    ], capture_output=True, text=True)
    
    # Find the latest JSON output
    output_dir = Path('output')
    json_files = list(output_dir.glob('health_check_*.json'))
    latest_file = max(json_files, key=lambda p: p.stat().st_mtime)
    
    # Load and process the data
    with open(latest_file) as f:
        data = json.load(f)
    
    # Process critical devices
    critical_devices = [
        device for device in data['health_data']
        if device['overall_status'] == 'critical'
    ]
    
    if critical_devices:
        print(f"Found {len(critical_devices)} critical devices!")
        for device in critical_devices:
            print(f"- {device['hostname']} ({device['device_ip']})")
    
    return data

if __name__ == '__main__':
    health_data = run_health_check()
```

### Grafana Dashboard Integration

```json
{
  "dashboard": {
    "title": "Network Health Monitoring",
    "panels": [
      {
        "title": "Device Health Status",
        "targets": [
          {
            "target": "SELECT count(*) FROM health_data WHERE overall_status='$status' GROUP BY time(5m)"
          }
        ]
      }
    ]
  }
}
```

### Slack Webhook Configuration

```yaml
# config/config.yaml
notifications:
  webhook:
    enabled: true
    type: slack
    url: https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

### Email Template Example

```python
# Custom email template for health alerts
email_template = """
<html>
<head>
    <style>
        .critical { color: red; font-weight: bold; }
        .warning { color: orange; }
        .good { color: green; }
    </style>
</head>
<body>
    <h2>Network Health Report</h2>
    <p>Generated: {{ timestamp }}</p>
    
    <h3>Summary</h3>
    <ul>
        <li>Total Devices: {{ total_devices }}</li>
        <li class="critical">Critical: {{ critical_count }}</li>
        <li class="warning">Warning: {{ warning_count }}</li>
        <li class="good">Healthy: {{ good_count }}</li>
    </ul>
    
    {% if critical_devices %}
    <h3>Critical Devices</h3>
    <ul>
        {% for device in critical_devices %}
        <li>{{ device.hostname }} - {{ device.issues }}</li>
        {% endfor %}
    </ul>
    {% endif %}
</body>
</html>
"""
```

## Advanced Configuration Examples

### Multi-Site Configuration

```yaml
# config/config.yaml
devices:
  # Main Office
  - host: 192.168.1.1
    device_type: cisco_ios
    vendor: cisco
    site: main-office
    role: core
    
  - host: 192.168.1.2
    device_type: cisco_ios
    vendor: cisco
    site: main-office
    role: distribution
    
  # Branch Office
  - host: 10.0.1.1
    device_type: arista_eos
    vendor: arista
    site: branch-office
    role: core
    
  # Data Center
  - host: 172.16.1.1
    device_type: cisco_nxos
    vendor: cisco
    site: datacenter
    role: core
```

### Custom Thresholds per Site

```yaml
# config/config.yaml
health_monitoring:
  default_thresholds:
    cpu: {warning: 70, critical: 85}
    memory: {warning: 70, critical: 85}
    
  site_thresholds:
    datacenter:
      cpu: {warning: 80, critical: 95}
      memory: {warning: 80, critical: 95}
      temperature: {warning: 65, critical: 80}
    
    branch-office:
      cpu: {warning: 60, critical: 80}
      memory: {warning: 60, critical: 80}
```

### Notification Routing

```yaml
# config/config.yaml
notifications:
  email:
    enabled: true
    smtp_server: smtp.gmail.com
    smtp_port: 587
    
    # Different recipients for different severities
    recipients:
      default: [admin@company.com]
      critical: [admin@company.com, oncall@company.com]
      datacenter: [datacenter-team@company.com]
    
  webhook:
    enabled: true
    # Different webhooks for different sites
    urls:
      default: https://hooks.slack.com/services/DEFAULT/WEBHOOK
      datacenter: https://hooks.slack.com/services/DC/WEBHOOK
      critical: https://hooks.slack.com/services/CRITICAL/WEBHOOK
```

## Troubleshooting Examples

### Debug Mode

```bash
# Run with verbose logging
python run_monitoring.py --health --verbose

# Check specific device with debug
python scripts/health_check.py --verbose --site main-office
```

### Testing Connectivity

```python
#!/usr/bin/env python3
"""Test device connectivity before running full monitoring"""

from netmiko import ConnectHandler
import os

device = {
    'device_type': 'cisco_ios',
    'host': '192.168.1.1',
    'username': os.environ.get('NETWORK_USERNAME'),
    'password': os.environ.get('NETWORK_PASSWORD'),
    'timeout': 10
}

try:
    connection = ConnectHandler(**device)
    output = connection.send_command('show version')
    print("Connection successful!")
    print(f"Version info: {output[:100]}...")
    connection.disconnect()
except Exception as e:
    print(f"Connection failed: {e}")
```

## Performance Tuning

### Concurrent Workers

```bash
# Increase workers for large networks
python run_monitoring.py --all --max-workers 50

# Reduce workers for limited resources
python run_monitoring.py --all --max-workers 5
```

### Timeout Adjustments

```bash
# Increase timeout for slow devices
python run_monitoring.py --health --timeout 120

# Quick timeout for fast networks
python run_monitoring.py --health --timeout 10
```

## Report Examples

### Custom Report Generation

```python
#!/usr/bin/env python3
"""Generate custom executive report"""

import json
from datetime import datetime
from pathlib import Path

# Load latest health data
output_dir = Path('output')
json_files = list(output_dir.glob('health_check_*.json'))
latest_file = max(json_files, key=lambda p: p.stat().st_mtime)

with open(latest_file) as f:
    data = json.load(f)

# Generate executive summary
total_devices = len(data['health_data'])
critical = sum(1 for d in data['health_data'] if d['overall_status'] == 'critical')
warning = sum(1 for d in data['health_data'] if d['overall_status'] == 'warning')
healthy = sum(1 for d in data['health_data'] if d['overall_status'] == 'good')

print(f"""
EXECUTIVE NETWORK HEALTH SUMMARY
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}

Overall Health Score: {(healthy/total_devices*100):.1f}%

Status Summary:
- Critical Issues: {critical} devices
- Warnings: {warning} devices  
- Healthy: {healthy} devices
- Total Monitored: {total_devices} devices

Critical Devices Requiring Immediate Attention:
""")

for device in data['health_data']:
    if device['overall_status'] == 'critical':
        print(f"- {device['hostname']} ({device['device_ip']})")
        if device.get('cpu_utilization', {}).get('status') == 'critical':
            print(f"  CPU: {device['cpu_utilization']['value']}%")
        if device.get('memory_usage', {}).get('status') == 'critical':
            print(f"  Memory: {device['memory_usage']['value']}%")
```

## Docker Integration

### Dockerfile Example

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create directories
RUN mkdir -p logs output

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Run monitoring
CMD ["python", "run_monitoring.py", "--health", "--send-alerts"]
```

### Docker Compose

```yaml
version: '3.8'

services:
  network-monitor:
    build: .
    environment:
      - NETWORK_USERNAME=${NETWORK_USERNAME}
      - NETWORK_PASSWORD=${NETWORK_PASSWORD}
      - EMAIL_USERNAME=${EMAIL_USERNAME}
      - EMAIL_PASSWORD=${EMAIL_PASSWORD}
    volumes:
      - ./config:/app/config
      - ./output:/app/output
      - ./logs:/app/logs
    restart: unless-stopped
```

These examples should help you get started with the Network Monitoring Suite. For more detailed information, refer to the main README.md file.
