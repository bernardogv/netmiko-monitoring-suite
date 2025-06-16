"""
Device type detection and command mapping utilities

This module provides:
- Automatic device type detection
- Multi-vendor command mapping
- Device capability detection
- Command templates for different vendors
"""

import re
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from netmiko import ConnectHandler


logger = logging.getLogger(__name__)


class DeviceVendor(Enum):
    """Supported device vendors"""
    CISCO_IOS = "cisco_ios"
    CISCO_IOS_XE = "cisco_xe"
    CISCO_IOS_XR = "cisco_xr"
    CISCO_NXOS = "cisco_nxos"
    CISCO_ASA = "cisco_asa"
    ARISTA_EOS = "arista_eos"
    JUNIPER_JUNOS = "juniper_junos"
    HP_PROCURVE = "hp_procurve"
    HP_COMWARE = "hp_comware"
    FORTINET = "fortinet"
    PALO_ALTO = "paloalto_panos"
    F5_TMSH = "f5_tmsh"
    F5_LINUX = "f5_linux"
    VYOS = "vyos"
    LINUX = "linux"
    UNKNOWN = "unknown"


@dataclass
class DeviceCapabilities:
    """Device capability information"""
    vendor: str
    model: Optional[str] = None
    version: Optional[str] = None
    supports_enable_mode: bool = True
    supports_config_mode: bool = True
    supports_commit: bool = False
    supports_rollback: bool = False
    supports_archive: bool = False
    supports_scp: bool = False
    supports_https: bool = False
    max_vlan_id: int = 4094
    features: List[str] = field(default_factory=list)
    command_syntax: str = "cisco"  # cisco, junos, linux, etc.


class DeviceTypeDetector:
    """Detects device type and capabilities"""
    
    def detect_device_type(self, host: str, username: str, password: str, 
                          port: int = 22) -> Tuple[Optional[str], Optional[DeviceCapabilities]]:
        """
        Auto-detect device type by trying different device types
        
        Args:
            host: Device hostname/IP
            username: Username
            password: Password
            port: SSH port
            
        Returns:
            Tuple of (netmiko_device_type, DeviceCapabilities)
        """
        # Common device types to try
        device_types = [
            'cisco_ios',
            'cisco_xe',
            'cisco_xr',
            'cisco_nxos',
            'cisco_asa',
            'arista_eos',
            'juniper_junos',
            'hp_procurve',
            'hp_comware',
            'fortinet',
            'paloalto_panos',
            'vyos',
            'linux'
        ]
        
        for device_type in device_types:
            try:
                device_config = {
                    'device_type': device_type,
                    'host': host,
                    'username': username,
                    'password': password,
                    'port': port,
                    'timeout': 10,
                    'conn_timeout': 10
                }
                
                connection = ConnectHandler(**device_config)
                
                # Get version output
                try:
                    version_output = connection.send_command("show version")
                except:
                    version_output = ""
                
                # Detect capabilities
                capabilities = self._detect_capabilities(device_type, version_output)
                
                connection.disconnect()
                
                logger.info(f"Successfully detected device type: {device_type}")
                return device_type, capabilities
                
            except Exception as e:
                logger.debug(f"Failed to connect with device_type {device_type}: {str(e)}")
                continue
        
        return None, None
    
    def _detect_capabilities(self, device_type: str, version_output: str) -> DeviceCapabilities:
        """Detect device capabilities based on device type and output"""
        capabilities = DeviceCapabilities(vendor=device_type)
        
        # Parse version info
        if 'cisco' in device_type:
            capabilities.vendor = 'cisco'
            if 'IOS XR' in version_output:
                capabilities.supports_commit = True
                capabilities.supports_rollback = True
            elif 'IOS' in version_output or 'IOS-XE' in version_output:
                capabilities.supports_archive = True
                
        elif device_type == 'arista_eos':
            capabilities.vendor = 'arista'
            capabilities.supports_rollback = True
            
        elif device_type == 'juniper_junos':
            capabilities.vendor = 'juniper'
            capabilities.supports_commit = True
            capabilities.supports_rollback = True
            capabilities.command_syntax = 'junos'
            
        elif device_type == 'linux':
            capabilities.vendor = 'linux'
            capabilities.supports_enable_mode = False
            capabilities.supports_config_mode = False
            capabilities.command_syntax = 'linux'
        
        return capabilities
    
    def get_device_commands(self, vendor: str) -> Dict[str, str]:
        """Get common commands for a vendor"""
        commands = {
            'cisco': {
                'version': 'show version',
                'interfaces': 'show interfaces',
                'inventory': 'show inventory',
                'cpu': 'show processes cpu sorted',
                'memory': 'show memory statistics',
                'config': 'show running-config'
            },
            'arista': {
                'version': 'show version',
                'interfaces': 'show interfaces',
                'inventory': 'show inventory',
                'cpu': 'show processes top once',
                'memory': 'show version detail',
                'config': 'show running-config'
            },
            'juniper': {
                'version': 'show version',
                'interfaces': 'show interfaces terse',
                'inventory': 'show chassis hardware',
                'cpu': 'show chassis routing-engine',
                'memory': 'show chassis routing-engine',
                'config': 'show configuration'
            },
            'linux': {
                'version': 'uname -a',
                'interfaces': 'ip addr show',
                'inventory': 'dmidecode -t system',
                'cpu': 'top -bn1 | head -20',
                'memory': 'free -m',
                'config': 'cat /etc/network/interfaces'
            }
        }
        
        return commands.get(vendor, {})