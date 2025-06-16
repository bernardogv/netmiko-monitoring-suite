#!/usr/bin/env python3
"""
Device Discovery & Inventory Script

This script automatically discovers and inventories all network devices in specified IP ranges.
It uses SNMP, SSH, and API methods to identify devices and collect comprehensive inventory data.

Features:
- Multi-vendor support (Cisco, Arista, Juniper, HP, Dell, etc.)
- Concurrent device discovery for performance
- Multiple discovery methods (SNMP, SSH, API)
- Incremental discovery (only new devices)
- Export to CSV/JSON/HTML formats
- Device role detection (core, distribution, access)
- Comprehensive error handling and logging

Author: Network Monitoring Suite
Version: 1.0
"""

import argparse
import asyncio
import ipaddress
import json
import logging
import os
import socket
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union

import yaml
from netmiko import ConnectHandler
from pysnmp.hlapi import (
    getCmd, SnmpEngine, CommunityData, UdpTransportTarget,
    ContextData, ObjectType, ObjectIdentity
)
from tqdm import tqdm

sys.path.append(str(Path(__file__).parent.parent))
from utils.common import (
    CredentialManager, ConnectionManager, ProgressTracker,
    retry_on_failure, setup_logging, load_config
)
from utils.device_types import DeviceTypeDetector, DeviceCapabilities
from utils.output_formatters import format_output
from utils.notifications import NotificationManager


@dataclass
class DeviceInfo:
    """Data class to store device information"""
    ip_address: str
    hostname: str = ""
    vendor: str = ""
    model: str = ""
    serial: str = ""
    os_version: str = ""
    device_type: str = ""
    role: str = ""
    location: str = ""
    uptime: str = ""
    management_ip: str = ""
    interfaces_count: int = 0
    vlans_count: int = 0
    mac_address: str = ""
    snmp_community: str = ""
    ssh_enabled: bool = False
    telnet_enabled: bool = False
    https_enabled: bool = False
    discovery_method: str = ""
    last_seen: str = ""
    reachable: bool = False
    response_time: float = 0.0
    capabilities: Optional[DeviceCapabilities] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for export"""
        data = asdict(self)
        if self.capabilities:
            data['capabilities'] = asdict(self.capabilities)
        return data


class DeviceDiscovery:
    """Main class for network device discovery"""
    
    def __init__(self, config_file: str = None):
        """Initialize the device discovery system"""
        self.config = load_config(config_file or 'config/config.yaml')
        self.logger = setup_logging('device_discovery', self.config.get('logging', {}))
        self.credential_manager = CredentialManager()
        self.connection_manager = ConnectionManager(self.config.get('connection', {}))
        self.detector = DeviceTypeDetector()
        self.notification_manager = NotificationManager(self.config.get('notifications', {}))
        
        # Discovery settings
        self.discovery_config = self.config.get('discovery', {})
        self.max_workers = self.discovery_config.get('max_workers', 50)
        self.timeout = self.discovery_config.get('timeout', 10)
        self.snmp_communities = self.discovery_config.get('snmp_communities', ['public', 'private'])
        self.common_ports = [22, 23, 80, 443, 161, 830]
        
        # Storage for discovered devices
        self.discovered_devices: Dict[str, DeviceInfo] = {}
        self.known_devices: Dict[str, DeviceInfo] = {}
        
        # Load existing inventory if available
        self.inventory_file = self.config.get('inventory_file', 'output/inventory.json')
        self.load_existing_inventory()
        
    def load_existing_inventory(self):
        """Load existing device inventory"""
        try:
            if os.path.exists(self.inventory_file):
                with open(self.inventory_file, 'r') as f:
                    data = json.load(f)
                    for device_data in data.get('devices', []):
                        device = DeviceInfo(**device_data)
                        self.known_devices[device.ip_address] = device
                self.logger.info(f"Loaded {len(self.known_devices)} devices from existing inventory")
        except Exception as e:
            self.logger.error(f"Error loading existing inventory: {e}")
    
    def is_host_reachable(self, ip: str) -> Tuple[bool, float]:
        """Check if host is reachable using ICMP ping"""
        start_time = time.time()
        try:
            # Use socket to test basic connectivity
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            result = sock.connect_ex((ip, 22))  # Try SSH port
            sock.close()
            
            response_time = (time.time() - start_time) * 1000
            return result == 0, response_time
        except Exception:
            return False, 0.0
    
    def scan_ports(self, ip: str) -> Dict[int, bool]:
        """Scan common network device ports"""
        open_ports = {}
        
        for port in self.common_ports:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                result = sock.connect_ex((ip, port))
                open_ports[port] = (result == 0)
                sock.close()
            except Exception:
                open_ports[port] = False
        
        return open_ports
    
    @retry_on_failure(max_attempts=3, delay=1)
    def snmp_discovery(self, ip: str) -> Optional[DeviceInfo]:
        """Discover device using SNMP"""
        for community in self.snmp_communities:
            try:
                # System OID queries
                oids = {
                    'sysDescr': '1.3.6.1.2.1.1.1.0',
                    'sysName': '1.3.6.1.2.1.1.5.0',
                    'sysUpTime': '1.3.6.1.2.1.1.3.0',
                    'sysContact': '1.3.6.1.2.1.1.4.0',
                    'sysLocation': '1.3.6.1.2.1.1.6.0'
                }
                
                device_info = DeviceInfo(ip_address=ip, discovery_method='SNMP')
                device_info.snmp_community = community
                
                for name, oid in oids.items():
                    for (errorIndication, errorStatus, errorIndex, varBinds) in getCmd(
                        SnmpEngine(),
                        CommunityData(community),
                        UdpTransportTarget((ip, 161), timeout=self.timeout),
                        ContextData(),
                        ObjectType(ObjectIdentity(oid))
                    ):
                        if errorIndication or errorStatus:
                            break
                        
                        value = str(varBinds[0][1])
                        if name == 'sysDescr':
                            device_info.os_version = value
                            # Parse vendor and model from description
                            vendor, model = self.parse_snmp_description(value)
                            device_info.vendor = vendor
                            device_info.model = model
                        elif name == 'sysName':
                            device_info.hostname = value
                        elif name == 'sysLocation':
                            device_info.location = value
                        elif name == 'sysUpTime':
                            device_info.uptime = self.format_uptime(int(value))
                
                if device_info.vendor:
                    device_info.reachable = True
                    return device_info
                    
            except Exception as e:
                self.logger.debug(f"SNMP discovery failed for {ip} with community {community}: {e}")
                continue
        
        return None
    
    def parse_snmp_description(self, description: str) -> Tuple[str, str]:
        """Parse vendor and model from SNMP sysDescr"""
        description = description.lower()
        
        # Cisco patterns
        if 'cisco' in description:
            vendor = 'Cisco'
            if 'catalyst' in description:
                model = 'Catalyst'
            elif 'nexus' in description:
                model = 'Nexus'
            elif 'asr' in description:
                model = 'ASR'
            elif 'isr' in description:
                model = 'ISR'
            else:
                model = 'Unknown'
        # Arista patterns
        elif 'arista' in description or 'eos' in description:
            vendor = 'Arista'
            model = 'EOS Switch'
        # Juniper patterns
        elif 'juniper' in description or 'junos' in description:
            vendor = 'Juniper'
            if 'ex' in description:
                model = 'EX Series'
            elif 'qfx' in description:
                model = 'QFX Series'
            elif 'mx' in description:
                model = 'MX Series'
            else:
                model = 'Unknown'
        # HP patterns
        elif 'hp' in description or 'hewlett' in description:
            vendor = 'HP'
            if 'procurve' in description:
                model = 'ProCurve'
            elif 'aruba' in description:
                model = 'Aruba'
            else:
                model = 'Unknown'
        # Dell patterns
        elif 'dell' in description:
            vendor = 'Dell'
            model = 'PowerConnect'
        else:
            vendor = 'Unknown'
            model = 'Unknown'
        
        return vendor, model
    
    def format_uptime(self, ticks: int) -> str:
        """Format uptime from SNMP ticks to human readable"""
        seconds = ticks // 100
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        minutes = (seconds % 3600) // 60
        
        if days > 0:
            return f"{days}d {hours}h {minutes}m"
        elif hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"
    
    @retry_on_failure(max_attempts=2, delay=2)
    def ssh_discovery(self, ip: str) -> Optional[DeviceInfo]:
        """Discover device using SSH connection"""
        try:
            credentials = self.credential_manager.get_credentials()
            
            # Try to detect device type first
            device_type, capabilities = self.detector.detect_device_type(
                ip, credentials['username'], credentials['password']
            )
            
            if not device_type:
                return None
            
            # Create connection
            device_config = {
                'device_type': device_type,
                'host': ip,
                'username': credentials['username'],
                'password': credentials['password'],
                'timeout': self.timeout,
                'global_delay_factor': 0.5
            }
            
            connection = self.connection_manager.create_connection(device_config)
            if not connection:
                return None
            
            device_info = DeviceInfo(ip_address=ip, discovery_method='SSH')
            device_info.device_type = device_type
            device_info.capabilities = capabilities
            device_info.ssh_enabled = True
            device_info.reachable = True
            
            # Get device information
            commands = self.detector.get_device_commands(capabilities.vendor)
            
            if 'version' in commands:
                output = connection.send_command(commands['version'])
                device_info.os_version = self.parse_version_output(output, capabilities.vendor)
                device_info.hostname = self.parse_hostname(output, capabilities.vendor)
                device_info.model = self.parse_model(output, capabilities.vendor)
                device_info.serial = self.parse_serial(output, capabilities.vendor)
                device_info.vendor = capabilities.vendor
            
            # Get interface count
            if 'interfaces' in commands:
                output = connection.send_command(commands['interfaces'])
                device_info.interfaces_count = self.count_interfaces(output, capabilities.vendor)
            
            # Determine device role
            device_info.role = self.determine_device_role(device_info)
            
            connection.disconnect()
            return device_info
            
        except Exception as e:
            self.logger.debug(f"SSH discovery failed for {ip}: {e}")
            return None
    
    def parse_version_output(self, output: str, vendor: str) -> str:
        """Parse OS version from show version output"""
        lines = output.lower().split('\n')
        
        if vendor.lower() == 'cisco':
            for line in lines:
                if 'version' in line and ('ios' in line or 'nx-os' in line):
                    return line.strip()
        elif vendor.lower() == 'arista':
            for line in lines:
                if 'software image version' in line:
                    return line.split(':')[1].strip() if ':' in line else line.strip()
        elif vendor.lower() == 'juniper':
            for line in lines:
                if 'junos' in line and 'version' in line:
                    return line.strip()
        
        return "Unknown"
    
    def parse_hostname(self, output: str, vendor: str) -> str:
        """Parse hostname from version output"""
        lines = output.split('\n')
        
        for line in lines:
            line = line.strip()
            if vendor.lower() == 'cisco':
                if line.endswith(' uptime is'):
                    return line.split(' uptime is')[0]
            elif vendor.lower() == 'arista':
                if 'hostname' in line.lower():
                    return line.split(':')[1].strip() if ':' in line else ""
        
        return ""
    
    def parse_model(self, output: str, vendor: str) -> str:
        """Parse device model from version output"""
        lines = output.lower().split('\n')
        
        if vendor.lower() == 'cisco':
            for line in lines:
                if 'cisco' in line and ('catalyst' in line or 'nexus' in line or 'asr' in line):
                    return line.strip()
        elif vendor.lower() == 'arista':
            for line in lines:
                if 'hardware version' in line:
                    return line.split(':')[1].strip() if ':' in line else ""
        
        return "Unknown"
    
    def parse_serial(self, output: str, vendor: str) -> str:
        """Parse serial number from version output"""
        lines = output.split('\n')
        
        for line in lines:
            line_lower = line.lower()
            if 'serial' in line_lower and 'number' in line_lower:
                # Extract serial number
                parts = line.split()
                for i, part in enumerate(parts):
                    if 'serial' in part.lower() and i + 1 < len(parts):
                        return parts[i + 1].strip(':')
        
        return ""
    
    def count_interfaces(self, output: str, vendor: str) -> int:
        """Count interfaces from interface output"""
        lines = output.split('\n')
        count = 0
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if vendor.lower() == 'cisco':
                if line.startswith(('GigabitEthernet', 'FastEthernet', 'TenGigabitEthernet', 'Ethernet')):
                    count += 1
            elif vendor.lower() == 'arista':
                if line.startswith('Ethernet'):
                    count += 1
            elif vendor.lower() == 'juniper':
                if line.startswith(('ge-', 'xe-', 'et-')):
                    count += 1
        
        return count
    
    def determine_device_role(self, device_info: DeviceInfo) -> str:
        """Determine device role based on various factors"""
        # Simple heuristics for role determination
        if device_info.interfaces_count > 48:
            return 'core'
        elif device_info.interfaces_count > 24:
            return 'distribution'
        elif device_info.interfaces_count > 0:
            return 'access'
        else:
            return 'unknown'
    
    def discover_single_device(self, ip: str) -> Optional[DeviceInfo]:
        """Discover a single device using multiple methods"""
        start_time = time.time()
        
        # Check if host is reachable
        reachable, response_time = self.is_host_reachable(ip)
        if not reachable:
            return None
        
        # Scan ports to determine available services
        open_ports = self.scan_ports(ip)
        
        device_info = None
        
        # Try SNMP first (faster)
        if open_ports.get(161, False):
            device_info = self.snmp_discovery(ip)
            if device_info:
                device_info.response_time = response_time
                device_info.last_seen = datetime.now().isoformat()
                device_info.https_enabled = open_ports.get(443, False)
                device_info.telnet_enabled = open_ports.get(23, False)
                return device_info
        
        # Try SSH if SNMP failed
        if open_ports.get(22, False):
            device_info = self.ssh_discovery(ip)
            if device_info:
                device_info.response_time = response_time
                device_info.last_seen = datetime.now().isoformat()
                device_info.https_enabled = open_ports.get(443, False)
                device_info.telnet_enabled = open_ports.get(23, False)
                return device_info
        
        return None
    
    def discover_network(self, ip_ranges: List[str], incremental: bool = False) -> Dict[str, DeviceInfo]:
        """Discover devices in specified IP ranges"""
        all_ips = []
        
        # Parse IP ranges
        for ip_range in ip_ranges:
            try:
                if '/' in ip_range:
                    # CIDR notation
                    network = ipaddress.ip_network(ip_range, strict=False)
                    all_ips.extend([str(ip) for ip in network.hosts()])
                elif '-' in ip_range:
                    # Range notation (e.g., 192.168.1.1-192.168.1.100)
                    start_ip, end_ip = ip_range.split('-')
                    start = ipaddress.ip_address(start_ip.strip())
                    end = ipaddress.ip_address(end_ip.strip())
                    current = start
                    while current <= end:
                        all_ips.append(str(current))
                        current += 1
                else:
                    # Single IP
                    all_ips.append(ip_range)
            except Exception as e:
                self.logger.error(f"Invalid IP range format: {ip_range} - {e}")
        
        # Filter for incremental discovery
        if incremental:
            new_ips = [ip for ip in all_ips if ip not in self.known_devices]
            self.logger.info(f"Incremental discovery: {len(new_ips)} new IPs to scan")
            all_ips = new_ips
        
        self.logger.info(f"Starting discovery of {len(all_ips)} IP addresses")
        
        # Concurrent discovery
        discovered = {}
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_ip = {executor.submit(self.discover_single_device, ip): ip for ip in all_ips}
            
            # Process results with progress bar
            with tqdm(total=len(all_ips), desc="Discovering devices") as pbar:
                for future in as_completed(future_to_ip):
                    ip = future_to_ip[future]
                    try:
                        device_info = future.result(timeout=self.timeout * 2)
                        if device_info:
                            discovered[ip] = device_info
                            self.logger.info(f"Discovered device: {ip} ({device_info.vendor} {device_info.model})")
                    except Exception as e:
                        self.logger.debug(f"Discovery failed for {ip}: {e}")
                    
                    pbar.update(1)
        
        self.discovered_devices.update(discovered)
        self.logger.info(f"Discovery complete: {len(discovered)} devices found")
        
        return discovered
    
    def save_inventory(self, output_formats: List[str] = None):
        """Save inventory to specified formats"""
        if output_formats is None:
            output_formats = ['json', 'csv', 'html']
        
        # Combine known and discovered devices
        all_devices = {**self.known_devices, **self.discovered_devices}
        
        # Convert to list of dictionaries
        device_list = [device.to_dict() for device in all_devices.values()]
        
        # Prepare data for export
        export_data = {
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'total_devices': len(device_list),
                'discovery_method': 'network_discovery',
                'version': '1.0'
            },
            'devices': device_list
        }
        
        # Save in requested formats
        output_files = []
        for fmt in output_formats:
            try:
                filename = f"inventory_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                output_file = format_output(export_data, fmt, filename=filename)
                output_files.append(output_file)
                self.logger.info(f"Inventory saved to {output_file}")
            except Exception as e:
                self.logger.error(f"Failed to save inventory in {fmt} format: {e}")
        
        # Also save the main JSON file for incremental discovery
        try:
            os.makedirs(os.path.dirname(self.inventory_file), exist_ok=True)
            with open(self.inventory_file, 'w') as f:
                json.dump(export_data, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save main inventory file: {e}")
        
        return output_files
    
    def generate_summary_report(self) -> Dict:
        """Generate discovery summary report"""
        all_devices = {**self.known_devices, **self.discovered_devices}
        
        # Summary statistics
        total_devices = len(all_devices)
        vendors = {}
        roles = {}
        reachable_count = 0
        
        for device in all_devices.values():
            # Vendor statistics
            vendor = device.vendor or 'Unknown'
            vendors[vendor] = vendors.get(vendor, 0) + 1
            
            # Role statistics
            role = device.role or 'Unknown'
            roles[role] = roles.get(role, 0) + 1
            
            # Reachability
            if device.reachable:
                reachable_count += 1
        
        summary = {
            'total_devices': total_devices,
            'reachable_devices': reachable_count,
            'unreachable_devices': total_devices - reachable_count,
            'vendor_distribution': vendors,
            'role_distribution': roles,
            'discovery_timestamp': datetime.now().isoformat(),
            'newly_discovered': len(self.discovered_devices)
        }
        
        return summary


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Network Device Discovery Tool')
    parser.add_argument('--ranges', nargs='+', required=True,
                       help='IP ranges to scan (CIDR, range, or single IP)')
    parser.add_argument('--config', default='config/config.yaml',
                       help='Configuration file path')
    parser.add_argument('--output-formats', nargs='+', 
                       choices=['json', 'csv', 'html', 'excel', 'pdf'],
                       default=['json', 'csv', 'html'],
                       help='Output formats for inventory')
    parser.add_argument('--incremental', action='store_true',
                       help='Only discover new devices (not in existing inventory)')
    parser.add_argument('--max-workers', type=int, default=50,
                       help='Maximum concurrent workers')
    parser.add_argument('--timeout', type=int, default=10,
                       help='Connection timeout in seconds')
    parser.add_argument('--site', help='Filter by site')
    parser.add_argument('--vendor', help='Filter by vendor')
    parser.add_argument('--role', help='Filter by device role')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    try:
        # Initialize discovery system
        discovery = DeviceDiscovery(args.config)
        
        # Set verbosity
        if args.verbose:
            discovery.logger.setLevel(logging.DEBUG)
        
        # Override settings from command line
        if args.max_workers:
            discovery.max_workers = args.max_workers
        if args.timeout:
            discovery.timeout = args.timeout
        
        print(f"Starting device discovery for ranges: {', '.join(args.ranges)}")
        
        # Perform discovery
        start_time = time.time()
        discovered_devices = discovery.discover_network(args.ranges, args.incremental)
        discovery_time = time.time() - start_time
        
        # Generate summary
        summary = discovery.generate_summary_report()
        
        print(f"\nDiscovery Summary:")
        print(f"  Total devices: {summary['total_devices']}")
        print(f"  Newly discovered: {summary['newly_discovered']}")
        print(f"  Reachable: {summary['reachable_devices']}")
        print(f"  Discovery time: {discovery_time:.2f} seconds")
        
        print(f"\nVendor Distribution:")
        for vendor, count in summary['vendor_distribution'].items():
            print(f"  {vendor}: {count}")
        
        print(f"\nRole Distribution:")
        for role, count in summary['role_distribution'].items():
            print(f"  {role}: {count}")
        
        # Save inventory
        print(f"\nSaving inventory...")
        output_files = discovery.save_inventory(args.output_formats)
        
        print(f"\nInventory files generated:")
        for file_path in output_files:
            print(f"  {file_path}")
        
        # Send notifications if configured
        if summary['newly_discovered'] > 0:
            discovery.notification_manager.send_notification(
                'device_discovery',
                f"Device discovery completed: {summary['newly_discovered']} new devices found",
                summary
            )
        
        print(f"\nDevice discovery completed successfully!")
        
    except KeyboardInterrupt:
        print("\nDiscovery interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error during discovery: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
