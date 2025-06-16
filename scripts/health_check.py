#!/usr/bin/env python3
"""
Universal Health Check Dashboard (continued)

This script monitors health metrics across all network switches and generates
comprehensive health reports with color-coded dashboards.
"""

                for line in lines:
                    if ('PS' in line or 'Power Supply' in line) and ('OK' in line or 'Normal' in line or 'Failed' in line):
                        parts = line.split()
                        for i, part in enumerate(parts):
                            if part in ['OK', 'Normal', 'Failed', 'Absent']:
                                ps_name = ' '.join(parts[:i])
                                status_text = part
                                
                                metric = HealthMetric(
                                    name=f"Power Supply - {ps_name}",
                                    value=status_text,
                                    unit=""
                                )
                                
                                if status_text in ['Failed', 'Absent']:
                                    metric.status = HealthStatus.CRITICAL
                                    metric.message = f"Power supply {ps_name} is {status_text}"
                                else:
                                    metric.status = HealthStatus.GOOD
                                    metric.message = f"Power supply {ps_name} is {status_text}"
                                
                                health.power_supplies.append(metric)
                                break
                                
            elif vendor == 'cisco_nxos':
                output = connection.send_command('show environment power')
                lines = output.split('\n')
                
                for line in lines:
                    if 'PS' in line and ('OK' in line or 'Absent' in line or 'Failed' in line):
                        match = re.search(r'(PS\d+)\s+.*?\s+(OK|Absent|Failed)', line)
                        if match:
                            ps_name = match.group(1)
                            status_text = match.group(2)
                            
                            metric = HealthMetric(
                                name=f"Power Supply - {ps_name}",
                                value=status_text,
                                unit=""
                            )
                            
                            if status_text in ['Failed', 'Absent']:
                                metric.status = HealthStatus.CRITICAL
                            else:
                                metric.status = HealthStatus.GOOD
                            
                            health.power_supplies.append(metric)
                            
        except Exception as e:
            self.logger.debug(f"Failed to collect power metrics: {e}")
    
    def collect_fan_metrics(self, connection, vendor: str, health: DeviceHealth):
        """Collect fan status and RPM metrics"""
        try:
            if vendor in ['cisco', 'cisco_ios', 'cisco_xe']:
                output = connection.send_command('show environment fan', delay_factor=2)
                lines = output.split('\n')
                
                for line in lines:
                    if ('Fan' in line or 'FAN' in line) and ('OK' in line or 'Normal' in line or 'Failed' in line):
                        # Parse fan status and RPM if available
                        match = re.search(r'(Fan.*?)\s+(\d+)\s*RPM\s+(OK|Normal|Failed)', line)
                        if match:
                            fan_name = match.group(1).strip()
                            rpm_value = int(match.group(2))
                            status_text = match.group(3)
                            
                            metric = HealthMetric(
                                name=f"Fan - {fan_name}",
                                value=rpm_value,
                                unit="RPM"
                            )
                            
                            if status_text == 'Failed':
                                metric.status = HealthStatus.CRITICAL
                                metric.message = f"Fan {fan_name} failed: {rpm_value} RPM"
                            else:
                                metric.status = HealthStatus.GOOD
                                metric.message = f"Fan {fan_name} OK: {rpm_value} RPM"
                            
                            health.fans.append(metric)
                        else:
                            # Just status without RPM
                            match = re.search(r'(Fan.*?)\s+(OK|Normal|Failed)', line)
                            if match:
                                fan_name = match.group(1).strip()
                                status_text = match.group(2)
                                
                                metric = HealthMetric(
                                    name=f"Fan - {fan_name}",
                                    value=status_text,
                                    unit=""
                                )
                                
                                if status_text == 'Failed':
                                    metric.status = HealthStatus.CRITICAL
                                else:
                                    metric.status = HealthStatus.GOOD
                                
                                health.fans.append(metric)
                                
        except Exception as e:
            self.logger.debug(f"Failed to collect fan metrics: {e}")
    
    def collect_interface_metrics(self, connection, vendor: str, health: DeviceHealth):
        """Collect interface error and utilization metrics"""
        try:
            if vendor in ['cisco', 'cisco_ios', 'cisco_xe']:
                # Get interface errors
                output = connection.send_command('show interfaces summary', delay_factor=3)
                
                # Parse interface statistics for high-level overview
                error_count = 0
                up_count = 0
                total_count = 0
                
                lines = output.split('\n')
                for line in lines:
                    if any(intf in line for intf in ['GigabitEthernet', 'FastEthernet', 'TenGigabitEthernet', 'Ethernet']):
                        total_count += 1
                        if 'up' in line:
                            up_count += 1
                        if any(word in line.lower() for word in ['error', 'drop', 'crc']):
                            error_count += 1
                
                if total_count > 0:
                    # Interface availability metric
                    availability = (up_count / total_count) * 100
                    metric = HealthMetric(
                        name="Interface Availability",
                        value=round(availability, 2),
                        unit="%"
                    )
                    
                    if availability < 80:
                        metric.status = HealthStatus.CRITICAL
                    elif availability < 95:
                        metric.status = HealthStatus.WARNING
                    else:
                        metric.status = HealthStatus.GOOD
                    
                    health.interface_utilization.append(metric)
                    
                    # Error rate metric
                    error_rate = (error_count / total_count) * 100
                    error_metric = HealthMetric(
                        name="Interface Error Rate",
                        value=round(error_rate, 2),
                        unit="%"
                    )
                    
                    if error_rate > 10:
                        error_metric.status = HealthStatus.CRITICAL
                    elif error_rate > 5:
                        error_metric.status = HealthStatus.WARNING
                    else:
                        error_metric.status = HealthStatus.GOOD
                    
                    health.interface_errors.append(error_metric)
                    
        except Exception as e:
            self.logger.debug(f"Failed to collect interface metrics: {e}")
    
    def collect_system_metrics(self, connection, vendor: str, health: DeviceHealth):
        """Collect additional system metrics"""
        try:
            # Uptime
            if vendor in ['cisco', 'cisco_ios', 'cisco_xe']:
                output = connection.send_command('show version | include uptime')
                if 'uptime is' in output:
                    uptime_str = output.split('uptime is')[1].strip()
                    metric = HealthMetric(
                        name="System Uptime",
                        value=uptime_str,
                        unit=""
                    )
                    metric.status = HealthStatus.GOOD
                    health.uptime = metric
                
                # Flash usage
                output = connection.send_command('show file systems | include flash')
                if output:
                    lines = output.split('\n')
                    for line in lines:
                        if 'flash:' in line and 'bytes' in line:
                            # Parse flash usage
                            match = re.search(r'(\d+)\s+bytes total\s+\((\d+)\s+bytes free\)', line)
                            if match:
                                total_bytes = int(match.group(1))
                                free_bytes = int(match.group(2))
                                used_bytes = total_bytes - free_bytes
                                usage_percent = (used_bytes / total_bytes) * 100
                                
                                metric = HealthMetric(
                                    name="Flash Usage",
                                    value=round(usage_percent, 2),
                                    unit="%"
                                )
                                health.flash_usage = self.evaluate_metric(metric, 'flash_usage')
                            break
                            
        except Exception as e:
            self.logger.debug(f"Failed to collect system metrics: {e}")
    
    def calculate_overall_status(self, health: DeviceHealth) -> HealthStatus:
        """Calculate overall device health status"""
        if not health.reachable:
            return HealthStatus.CRITICAL
        
        critical_count = 0
        warning_count = 0
        total_metrics = 0
        
        # Check all metrics
        all_metrics = []
        
        if health.cpu_utilization:
            all_metrics.append(health.cpu_utilization)
        if health.memory_usage:
            all_metrics.append(health.memory_usage)
        
        all_metrics.extend(health.temperature_sensors)
        all_metrics.extend(health.power_supplies)
        all_metrics.extend(health.fans)
        all_metrics.extend(health.interface_errors)
        all_metrics.extend(health.interface_utilization)
        
        for metric in all_metrics:
            total_metrics += 1
            if metric.status == HealthStatus.CRITICAL:
                critical_count += 1
            elif metric.status == HealthStatus.WARNING:
                warning_count += 1
        
        if total_metrics == 0:
            return HealthStatus.UNKNOWN
        
        # Determine overall status
        if critical_count > 0:
            return HealthStatus.CRITICAL
        elif warning_count > 0:
            return HealthStatus.WARNING
        else:
            return HealthStatus.GOOD
    
    def check_all_devices(self) -> Dict[str, DeviceHealth]:
        """Check health of all configured devices"""
        self.logger.info(f"Starting health check for {len(self.devices)} devices")
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_device = {
                executor.submit(self.check_device_health, device): device 
                for device in self.devices
            }
            
            # Process results with progress bar
            with tqdm(total=len(self.devices), desc="Checking device health") as pbar:
                for future in as_completed(future_to_device):
                    device_config = future_to_device[future]
                    device_ip = device_config['host']
                    
                    try:
                        health = future.result(timeout=self.check_timeout * 2)
                        self.health_data[device_ip] = health
                        
                        status_color = {
                            HealthStatus.GOOD: "✅",
                            HealthStatus.WARNING: "⚠️",
                            HealthStatus.CRITICAL: "❌",
                            HealthStatus.UNKNOWN: "❓"
                        }
                        
                        self.logger.info(f"Health check completed for {device_ip}: {status_color.get(health.overall_status, '❓')} {health.overall_status.value}")
                        
                    except Exception as e:
                        self.logger.error(f"Health check failed for {device_ip}: {e}")
                        error_health = DeviceHealth(device_ip=device_ip)
                        error_health.errors.append(str(e))
                        error_health.overall_status = HealthStatus.UNKNOWN
                        self.health_data[device_ip] = error_health
                    
                    pbar.update(1)
        
        return self.health_data
    
    def generate_dashboard_html(self) -> str:
        """Generate HTML dashboard"""
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Network Health Dashboard</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
                .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; }
                .summary { display: flex; justify-content: space-around; margin-bottom: 30px; }
                .summary-card { background: white; padding: 20px; border-radius: 10px; text-align: center; box-shadow: 0 2px 5px rgba(0,0,0,0.1); min-width: 150px; }
                .status-good { color: #28a745; }
                .status-warning { color: #ffc107; }
                .status-critical { color: #dc3545; }
                .status-unknown { color: #6c757d; }
                .device-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(400px, 1fr)); gap: 20px; }
                .device-card { background: white; border-radius: 10px; padding: 20px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
                .device-header { display: flex; justify-content: between; align-items: center; margin-bottom: 15px; }
                .device-status { font-weight: bold; font-size: 18px; }
                .metric { margin: 8px 0; padding: 8px; background: #f8f9fa; border-radius: 5px; }
                .metric-critical { border-left: 4px solid #dc3545; }
                .metric-warning { border-left: 4px solid #ffc107; }
                .metric-good { border-left: 4px solid #28a745; }
                .metric-unknown { border-left: 4px solid #6c757d; }
                .timestamp { color: #6c757d; font-size: 12px; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🏥 Network Health Dashboard</h1>
                <p>Generated on: {timestamp}</p>
            </div>
            
            <div class="summary">
                <div class="summary-card">
                    <h3>Total Devices</h3>
                    <h2>{total_devices}</h2>
                </div>
                <div class="summary-card">
                    <h3 class="status-good">Healthy</h3>
                    <h2 class="status-good">{good_count}</h2>
                </div>
                <div class="summary-card">
                    <h3 class="status-warning">Warning</h3>
                    <h2 class="status-warning">{warning_count}</h2>
                </div>
                <div class="summary-card">
                    <h3 class="status-critical">Critical</h3>
                    <h2 class="status-critical">{critical_count}</h2>
                </div>
            </div>
            
            <div class="device-grid">
                {device_cards}
            </div>
        </body>
        </html>
        """
        
        # Calculate summary statistics
        total_devices = len(self.health_data)
        good_count = sum(1 for h in self.health_data.values() if h.overall_status == HealthStatus.GOOD)
        warning_count = sum(1 for h in self.health_data.values() if h.overall_status == HealthStatus.WARNING)
        critical_count = sum(1 for h in self.health_data.values() if h.overall_status == HealthStatus.CRITICAL)
        
        # Generate device cards
        device_cards = []
        for device_ip, health in self.health_data.items():
            status_class = f"status-{health.overall_status.value}"
            status_icon = {
                HealthStatus.GOOD: "✅",
                HealthStatus.WARNING: "⚠️",
                HealthStatus.CRITICAL: "❌",
                HealthStatus.UNKNOWN: "❓"
            }.get(health.overall_status, "❓")
            
            # Build metrics HTML
            metrics_html = []
            
            # Add all metrics
            all_metrics = []
            if health.cpu_utilization:
                all_metrics.append(health.cpu_utilization)
            if health.memory_usage:
                all_metrics.append(health.memory_usage)
            
            all_metrics.extend(health.temperature_sensors[:3])  # Limit to first 3
            all_metrics.extend(health.power_supplies[:2])       # Limit to first 2
            all_metrics.extend(health.fans[:2])                 # Limit to first 2
            
            for metric in all_metrics:
                metric_class = f"metric-{metric.status.value}"
                metrics_html.append(f"""
                    <div class="metric {metric_class}">
                        <strong>{metric.name}:</strong> {metric.value}{metric.unit}
                        {' - ' + metric.message if metric.message else ''}
                    </div>
                """)
            
            device_card = f"""
            <div class="device-card">
                <div class="device-header">
                    <div>
                        <h3>{health.hostname or device_ip}</h3>
                        <small>{health.vendor} {health.model}</small>
                    </div>
                    <div class="device-status {status_class}">
                        {status_icon} {health.overall_status.value.upper()}
                    </div>
                </div>
                {''.join(metrics_html)}
                <div class="timestamp">
                    Last checked: {health.last_check}
                    {' | Duration: ' + str(round(health.check_duration, 2)) + 's' if health.check_duration else ''}
                    {' | Errors: ' + str(len(health.errors)) if health.errors else ''}
                </div>
            </div>
            """
            device_cards.append(device_card)
        
        return html_content.format(
            timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            total_devices=total_devices,
            good_count=good_count,
            warning_count=warning_count,
            critical_count=critical_count,
            device_cards=''.join(device_cards)
        )
    
    def save_health_data(self, output_formats: List[str] = None):
        """Save health data in specified formats"""
        if output_formats is None:
            output_formats = ['json', 'csv', 'html']
        
        # Prepare data for export
        health_list = [health.to_dict() for health in self.health_data.values()]
        
        export_data = {
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'total_devices': len(health_list),
                'check_type': 'health_monitoring',
                'version': '1.0'
            },
            'health_data': health_list
        }
        
        # Save in requested formats
        output_files = []
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        for fmt in output_formats:
            try:
                if fmt == 'html':
                    # Generate custom HTML dashboard
                    filename = f"health_dashboard_{timestamp}.html"
                    filepath = f"output/{filename}"
                    os.makedirs('output', exist_ok=True)
                    
                    with open(filepath, 'w') as f:
                        f.write(self.generate_dashboard_html())
                    
                    output_files.append(filepath)
                    self.logger.info(f"Health dashboard saved to {filepath}")
                else:
                    filename = f"health_check_{timestamp}"
                    output_file = format_output(export_data, fmt, filename=filename)
                    output_files.append(output_file)
                    self.logger.info(f"Health data saved to {output_file}")
                    
            except Exception as e:
                self.logger.error(f"Failed to save health data in {fmt} format: {e}")
        
        # Save to historical data
        self.save_historical_data()
        
        return output_files
    
    def save_historical_data(self):
        """Save current health data to historical records"""
        try:
            # Add current data to historical records
            historical_record = {
                'timestamp': datetime.now().isoformat(),
                'health_data': [health.to_dict() for health in self.health_data.values()]
            }
            
            self.historical_data.append(historical_record)
            
            # Keep only last 30 days of data
            cutoff_date = datetime.now() - timedelta(days=30)
            self.historical_data = [
                record for record in self.historical_data
                if datetime.fromisoformat(record['timestamp']) > cutoff_date
            ]
            
            # Save to file
            history_file = self.config.get('history_file', 'output/health_history.json')
            os.makedirs(os.path.dirname(history_file), exist_ok=True)
            
            with open(history_file, 'w') as f:
                json.dump(self.historical_data, f, indent=2)
                
            self.logger.info(f"Historical data saved: {len(self.historical_data)} records")
            
        except Exception as e:
            self.logger.error(f"Failed to save historical data: {e}")
    
    def generate_summary_report(self) -> Dict:
        """Generate health check summary report"""
        total_devices = len(self.health_data)
        reachable_devices = sum(1 for h in self.health_data.values() if h.reachable)
        
        status_counts = {
            'good': sum(1 for h in self.health_data.values() if h.overall_status == HealthStatus.GOOD),
            'warning': sum(1 for h in self.health_data.values() if h.overall_status == HealthStatus.WARNING),
            'critical': sum(1 for h in self.health_data.values() if h.overall_status == HealthStatus.CRITICAL),
            'unknown': sum(1 for h in self.health_data.values() if h.overall_status == HealthStatus.UNKNOWN)
        }
        
        # Find devices with issues
        critical_devices = [
            (ip, health.hostname or ip) 
            for ip, health in self.health_data.items() 
            if health.overall_status == HealthStatus.CRITICAL
        ]
        
        warning_devices = [
            (ip, health.hostname or ip) 
            for ip, health in self.health_data.items() 
            if health.overall_status == HealthStatus.WARNING
        ]
        
        # Calculate average metrics
        cpu_values = [h.cpu_utilization.value for h in self.health_data.values() 
                     if h.cpu_utilization and isinstance(h.cpu_utilization.value, (int, float))]
        memory_values = [h.memory_usage.value for h in self.health_data.values() 
                        if h.memory_usage and isinstance(h.memory_usage.value, (int, float))]
        
        avg_cpu = sum(cpu_values) / len(cpu_values) if cpu_values else 0
        avg_memory = sum(memory_values) / len(memory_values) if memory_values else 0
        
        summary = {
            'timestamp': datetime.now().isoformat(),
            'total_devices': total_devices,
            'reachable_devices': reachable_devices,
            'status_distribution': status_counts,
            'critical_devices': critical_devices,
            'warning_devices': warning_devices,
            'average_metrics': {
                'cpu_utilization': round(avg_cpu, 2),
                'memory_usage': round(avg_memory, 2)
            },
            'health_score': round((status_counts['good'] / total_devices * 100) if total_devices > 0 else 0, 2)
        }
        
        return summary
    
    def send_alerts(self):
        """Send alerts for critical and warning conditions"""
        try:
            critical_devices = []
            warning_devices = []
            
            for device_ip, health in self.health_data.items():
                if health.overall_status == HealthStatus.CRITICAL:
                    critical_devices.append({
                        'ip': device_ip,
                        'hostname': health.hostname or device_ip,
                        'issues': [error for error in health.errors] + 
                                [metric.message for metric in [health.cpu_utilization, health.memory_usage] + 
                                 health.temperature_sensors + health.power_supplies + health.fans
                                 if metric and metric.status == HealthStatus.CRITICAL and metric.message]
                    })
                elif health.overall_status == HealthStatus.WARNING:
                    warning_devices.append({
                        'ip': device_ip,
                        'hostname': health.hostname or device_ip,
                        'issues': [metric.message for metric in [health.cpu_utilization, health.memory_usage] + 
                                 health.temperature_sensors + health.power_supplies + health.fans
                                 if metric and metric.status == HealthStatus.WARNING and metric.message]
                    })
            
            # Send critical alerts
            if critical_devices:
                alert_message = f"🚨 CRITICAL: {len(critical_devices)} device(s) require immediate attention:\n\n"
                for device in critical_devices[:5]:  # Limit to first 5
                    alert_message += f"• {device['hostname']} ({device['ip']})\n"
                    for issue in device['issues'][:3]:  # Limit issues
                        alert_message += f"  - {issue}\n"
                    alert_message += "\n"
                
                self.notification_manager.send_notification(
                    'health_critical',
                    alert_message,
                    {'severity': AlertSeverity.CRITICAL, 'device_count': len(critical_devices)}
                )
            
            # Send warning alerts (with lower frequency)
            if warning_devices and len(warning_devices) >= 3:  # Only if multiple warnings
                alert_message = f"⚠️ WARNING: {len(warning_devices)} device(s) showing warning conditions:\n\n"
                for device in warning_devices[:3]:  # Limit to first 3
                    alert_message += f"• {device['hostname']} ({device['ip']})\n"
                
                self.notification_manager.send_notification(
                    'health_warning',
                    alert_message,
                    {'severity': AlertSeverity.MEDIUM, 'device_count': len(warning_devices)}
                )
                
        except Exception as e:
            self.logger.error(f"Failed to send alerts: {e}")


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Network Health Check Tool')
    parser.add_argument('--config', default='config/config.yaml',
                       help='Configuration file path')
    parser.add_argument('--output-formats', nargs='+',
                       choices=['json', 'csv', 'html', 'excel', 'pdf'],
                       default=['json', 'csv', 'html'],
                       help='Output formats for health data')
    parser.add_argument('--max-workers', type=int, default=20,
                       help='Maximum concurrent workers')
    parser.add_argument('--timeout', type=int, default=30,
                       help='Check timeout in seconds')
    parser.add_argument('--site', help='Filter by site')
    parser.add_argument('--vendor', help='Filter by vendor')
    parser.add_argument('--role', help='Filter by device role')
    parser.add_argument('--send-alerts', action='store_true',
                       help='Send notifications for critical/warning conditions')
    parser.add_argument('--dashboard-only', action='store_true',
                       help='Only generate HTML dashboard')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    try:
        # Initialize health monitor
        monitor = HealthMonitor(args.config)
        
        # Set verbosity
        if args.verbose:
            monitor.logger.setLevel(logging.DEBUG)
        
        # Override settings from command line
        if args.max_workers:
            monitor.max_workers = args.max_workers
        if args.timeout:
            monitor.check_timeout = args.timeout
        
        # Apply filters
        if args.site or args.vendor or args.role:
            filtered_devices = []
            for device in monitor.devices:
                if args.site and device.get('site', '').lower() != args.site.lower():
                    continue
                if args.vendor and device.get('vendor', '').lower() != args.vendor.lower():
                    continue
                if args.role and device.get('role', '').lower() != args.role.lower():
                    continue
                filtered_devices.append(device)
            
            monitor.devices = filtered_devices
            print(f"Filtered to {len(monitor.devices)} devices")
        
        print(f"Starting health check for {len(monitor.devices)} devices...")
        
        # Perform health checks
        start_time = time.time()
        health_data = monitor.check_all_devices()
        check_duration = time.time() - start_time
        
        # Generate summary
        summary = monitor.generate_summary_report()
        
        print(f"\n📊 Health Check Summary:")
        print(f"  Total devices checked: {summary['total_devices']}")
        print(f"  Reachable devices: {summary['reachable_devices']}")
        print(f"  Health score: {summary['health_score']}%")
        print(f"  Check duration: {check_duration:.2f} seconds")
        
        print(f"\n📈 Status Distribution:")
        for status, count in summary['status_distribution'].items():
            emoji = {'good': '✅', 'warning': '⚠️', 'critical': '❌', 'unknown': '❓'}
            print(f"  {emoji.get(status, '')} {status.capitalize()}: {count}")
        
        if summary['critical_devices']:
            print(f"\n🚨 Critical Devices ({len(summary['critical_devices'])}):")
            for ip, hostname in summary['critical_devices'][:5]:
                print(f"  • {hostname} ({ip})")
        
        if summary['warning_devices']:
            print(f"\n⚠️  Warning Devices ({len(summary['warning_devices'])}):")
            for ip, hostname in summary['warning_devices'][:5]:
                print(f"  • {hostname} ({ip})")
        
        print(f"\n💾 Saving health data...")
        
        # Save health data
        if not args.dashboard_only:
            output_files = monitor.save_health_data(args.output_formats)
        else:
            # Generate only HTML dashboard
            output_files = monitor.save_health_data(['html'])
        
        print(f"\n📁 Output files generated:")
        for file_path in output_files:
            print(f"  📄 {file_path}")
        
        # Send alerts if requested
        if args.send_alerts:
            print(f"\n📢 Sending alerts...")
            monitor.send_alerts()
        
        print(f"\n✅ Health check completed successfully!")
        
        # Return appropriate exit code
        if summary['status_distribution']['critical'] > 0:
            print(f"⚠️  Exiting with code 2 due to critical health issues")
            sys.exit(2)
        elif summary['status_distribution']['warning'] > 0:
            print(f"ℹ️  Exiting with code 1 due to warning conditions")
            sys.exit(1)
        else:
            sys.exit(0)
        
    except KeyboardInterrupt:
        print("\nHealth check interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error during health check: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
