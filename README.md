# Network Monitoring Scripts Suite

A comprehensive collection of read-only network monitoring scripts using netmiko for multi-vendor network environments. All scripts support concurrent execution, multiple output formats, and advanced error handling.

## 🚀 Quick Start

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Credentials**
   ```bash
   cp .env.example .env
   # Edit .env with your network credentials
   ```

3. **Configure Devices**
   ```bash
   # Edit config/config.yaml with your device list
   ```

4. **Run All Monitoring Scripts**
   ```bash
   python run_monitoring.py --all
   ```

## 📊 Available Scripts

### 1. Device Discovery & Inventory (`device_discovery.py`)
Automatically discovers and inventories network devices in specified IP ranges.

**Features:**
- Multi-method discovery (SNMP, SSH, port scanning)
- Device role detection (core, distribution, access)
- Incremental discovery support
- Export to CSV/JSON/HTML/Excel formats

**Usage:**
```bash
python scripts/device_discovery.py --ranges 192.168.1.0/24 10.0.0.0/16
python scripts/device_discovery.py --ranges 192.168.1.1-192.168.1.100 --incremental
```

### 2. Universal Health Check Dashboard (`health_check.py`)
Monitors health metrics across all network switches with color-coded dashboards.

**Features:**
- CPU, Memory, Temperature, Power, Fan monitoring
- Configurable thresholds with color-coding
- Historical trending for capacity planning
- HTML dashboard with beautiful visualization
- Alert generation for critical issues

**Usage:**
```bash
python scripts/health_check.py
python scripts/health_check.py --send-alerts --dashboard-only
```

### 3. Port Mapping & Documentation (`port_mapper.py`)
Creates comprehensive port documentation including neighbor discovery and utilization.

**Features:**
- Complete port mapping with CDP/LLDP neighbor discovery
- VLAN assignments and bandwidth utilization
- Visual topology maps and unused port identification
- Excel export with multiple sheets
- Historical port usage tracking

**Usage:**
```bash
python scripts/port_mapper.py
python scripts/port_mapper.py --unused-only --output-formats excel
```

### 4. VLAN Auditor (`vlan_audit.py`)
Audits VLAN configurations across the network for consistency and issues.

**Features:**
- VLAN consistency checking across switches
- Unused VLAN identification
- Trunk configuration validation
- VLAN naming convention validation
- Orphaned VLAN detection

**Usage:**
```bash
python scripts/vlan_audit.py
python scripts/vlan_audit.py --consistency-only --send-alerts
```

### 5. Interface Error Monitor (`interface_monitor.py`)
Monitors interface health and performance with error tracking and trend analysis.

**Features:**
- Error counter tracking and rate calculation
- Flapping interface detection
- Bandwidth utilization monitoring
- Historical baseline comparison
- Top talkers identification

**Usage:**
```bash
python scripts/interface_monitor.py
python scripts/interface_monitor.py --errors-only --send-alerts
```

### 6. Network Change Logger (`change_logger.py`)
Tracks and logs all network changes with diff reporting and timeline creation.

**Features:**
- Configuration change detection with diff reports
- Interface state change monitoring
- MAC address and routing table tracking
- Timeline creation and change history
- Continuous monitoring mode

**Usage:**
```bash
python scripts/change_logger.py
python scripts/change_logger.py --continuous --interval 300
python scripts/change_logger.py --config-only --send-alerts
```

### 7. Spanning Tree Analyzer (`stp_analyzer.py`)
Analyzes spanning tree health and topology with root bridge validation.

**Features:**
- Root bridge identification and validation
- STP topology mapping and visualization
- Blocked/alternate port identification
- BPDU guard violation detection
- Convergence time analysis

**Usage:**
```bash
python scripts/stp_analyzer.py
python scripts/stp_analyzer.py --topology-only --send-alerts
```

## 🔧 Configuration

### Main Configuration (`config/config.yaml`)
```yaml
# Global settings
logging:
  level: INFO
  file: logs/monitoring.log

connection:
  timeout: 30
  retries: 3
  delay_factor: 1

# Device list
devices:
  - host: 192.168.1.1
    device_type: cisco_ios
    vendor: cisco
    site: datacenter1
    role: core
  - host: 192.168.1.2
    device_type: arista_eos
    vendor: arista
    site: datacenter1
    role: distribution

# Monitoring thresholds
health_monitoring:
  thresholds:
    cpu: {warning: 70, critical: 85}
    memory: {warning: 70, critical: 85}
    temperature: {warning: 60, critical: 75}

# Notifications
notifications:
  email:
    enabled: true
    smtp_server: smtp.gmail.com
    smtp_port: 587
    username: your-email@gmail.com
    recipients: [admin@company.com]
```

### Environment Variables (`.env`)
```bash
# Device Credentials
NETWORK_USERNAME=your_username
NETWORK_PASSWORD=your_password
ENABLE_PASSWORD=your_enable_password

# Email Notifications
EMAIL_USERNAME=your-email@gmail.com
EMAIL_PASSWORD=your-app-password

# Optional: SNMP Communities
SNMP_COMMUNITY_RO=public
SNMP_COMMUNITY_RW=private
```

## 🌐 Multi-Vendor Support

The scripts support the following vendors and device types:

### Cisco
- IOS, IOS-XE, IOS-XR, NX-OS
- ASA Firewalls
- Catalyst, Nexus, ASR, ISR series

### Arista
- EOS switches
- All Arista hardware platforms

### Juniper
- Junos OS
- EX, QFX, MX series

### HP/HPE
- ProCurve switches
- Aruba switches

### Dell
- PowerConnect switches
- Dell Networking OS

### Others
- Fortinet FortiGate
- Palo Alto Networks
- F5 BIG-IP
- VyOS

## 📋 Common Usage Patterns

### Daily Health Check
```bash
python run_monitoring.py --health --interface --send-alerts
```

### Weekly Comprehensive Audit
```bash
python run_monitoring.py --all --output-formats excel html pdf
```

### Site-Specific Monitoring
```bash
python run_monitoring.py --all --site datacenter1 --send-alerts
```

### Vendor-Specific Analysis
```bash
python run_monitoring.py --health --vlan --vendor cisco
```

### Continuous Change Monitoring
```bash
python run_monitoring.py --change --continuous --interval 300
```

### Discovery and Mapping
```bash
python run_monitoring.py --discovery --port --output-formats excel
```

## 📊 Output Formats

All scripts support multiple output formats:

- **JSON**: Machine-readable format for integration
- **CSV**: Spreadsheet-compatible format
- **HTML**: Beautiful web-based reports with charts
- **Excel**: Professional reports with multiple sheets
- **PDF**: Printable reports for documentation

## 🔔 Notifications

The suite supports multiple notification channels:

### Email Notifications
- SMTP support for any email provider
- HTML email templates
- Attachment support for reports

### Webhook Notifications
- Generic webhook support
- Slack integration
- Microsoft Teams integration

### Alert Management
- Configurable severity levels
- Alert throttling and cooldowns
- Escalation policies

## 📈 Performance Features

### Concurrent Execution
- Configurable worker thread pools
- Parallel device processing
- Progress bars for long operations

### Caching and Optimization
- Connection pooling and reuse
- Intelligent retry logic with backoff
- Command batching where possible

### Scalability
- Tested with 100+ device networks
- Memory-efficient processing
- Streaming output for large datasets

## 🛡️ Security Features

### Credential Management
- Environment variable support
- Encrypted credential storage
- No hardcoded passwords

### Read-Only Operations
- All scripts are read-only by design
- No configuration changes
- Safe for production use

### Access Control
- Role-based device filtering
- Site-based access control
- Audit logging

## 🔍 Troubleshooting

### Common Issues

1. **Connection Timeouts**
   ```bash
   # Increase timeout values
   python script.py --timeout 120
   ```

2. **Authentication Failures**
   ```bash
   # Verify credentials in .env file
   # Check device access permissions
   ```

3. **Device Type Detection Issues**
   ```bash
   # Explicitly specify device type in config
   device_type: cisco_ios
   ```

4. **Memory Issues with Large Networks**
   ```bash
   # Reduce concurrent workers
   python script.py --max-workers 5
   ```

### Debug Mode
```bash
python script.py --verbose
```

### Log Files
- Main logs: `logs/monitoring.log`
- Script-specific logs: `logs/script_name_YYYYMMDD_HHMMSS.log`

## 🤝 Integration

### REST API Integration
The JSON output can be easily integrated with:
- Grafana dashboards
- ELK stack (Elasticsearch, Logstash, Kibana)
- Splunk
- Custom monitoring solutions

### Automation Platforms
- Ansible playbooks
- Python automation scripts
- Cron jobs for scheduled monitoring
- CI/CD pipelines

### Network Management Systems
- SolarWinds integration
- PRTG custom sensors
- Nagios/Icinga monitoring
- Zabbix integration

## 📚 Examples

See the `examples/` directory for:
- Configuration templates
- Integration scripts
- Dashboard examples
- Automation workflows

## 🆘 Support

For issues, questions, or contributions:
1. Check the troubleshooting section
2. Review log files with `--verbose` output
3. Open an issue with detailed error information
4. Include configuration (with credentials redacted)

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Built with [netmiko](https://github.com/ktbyers/netmiko) for multi-vendor support
- Uses [click](https://click.palletsprojects.com/) for CLI interfaces
- Powered by [pandas](https://pandas.pydata.org/) for data processing
- Visualization with [matplotlib](https://matplotlib.org/) and [seaborn](https://seaborn.pydata.org/)