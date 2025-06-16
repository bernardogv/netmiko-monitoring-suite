"""
Common utilities for network monitoring scripts

This module provides essential functions for:
- Device connection management with retry logic
- Multi-vendor command mapping
- Credential management
- Progress tracking
- Error handling
- Concurrent execution
"""

import os
import time
import json
import logging
import getpass
import threading
from typing import Dict, List, Any, Optional, Callable, Tuple, Union
from functools import wraps
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
import yaml
from netmiko import ConnectHandler
from netmiko.exceptions import NetmikoTimeoutException, NetmikoAuthenticationException
from tqdm import tqdm
from pathlib import Path
import paramiko
import socket


# Configure logging
logger = logging.getLogger(__name__)


# Custom Exceptions
class NetworkError(Exception):
    """Base exception for network-related errors"""
    pass


class ConnectionError(NetworkError):
    """Exception for connection-related errors"""
    pass


class CommandError(NetworkError):
    """Exception for command execution errors"""
    pass


class CredentialError(NetworkError):
    """Exception for credential-related errors"""
    pass


# Retry decorator
def retry_on_failure(max_attempts: int = 3, delay: int = 5, backoff: float = 2.0,
                    exceptions: tuple = (NetmikoTimeoutException, socket.timeout)):
    """
    Decorator to retry function execution on failure
    
    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Backoff multiplier for delay
        exceptions: Tuple of exceptions to catch for retry
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 1
            current_delay = delay
            
            while attempt <= max_attempts:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts:
                        logger.error(f"Failed after {max_attempts} attempts: {str(e)}")
                        raise
                    
                    logger.warning(f"Attempt {attempt} failed: {str(e)}. Retrying in {current_delay} seconds...")
                    time.sleep(current_delay)
                    current_delay *= backoff
                    attempt += 1
                    
            return None
        return wrapper
    return decorator


# Connection management
class ConnectionManager:
    """Manages device connections with pooling and retry logic"""
    
    def __init__(self, config: Dict[str, Any] = None):
        config = config or {}
        self.max_connections = config.get('max_connections', 50)
        self.connection_timeout = config.get('timeout', 30)
        self._connection_pool = {}
        self._lock = threading.Lock()
        
    @retry_on_failure(max_attempts=3, delay=2)
    def create_connection(self, device_config: Dict[str, Any], 
                         enable_mode: bool = False) -> ConnectHandler:
        """
        Create a connection to a network device with retry logic
        
        Args:
            device_config: Device configuration dictionary
            enable_mode: Whether to enter enable mode after connection
            
        Returns:
            ConnectHandler object
        """
        device_key = f"{device_config['host']}:{device_config.get('port', 22)}"
        
        # Check if we have a cached connection
        with self._lock:
            if device_key in self._connection_pool:
                conn = self._connection_pool[device_key]
                if conn.is_alive():
                    return conn
                else:
                    # Remove dead connection
                    del self._connection_pool[device_key]
        
        # Create new connection
        try:
            # Set default timeout if not specified
            if 'timeout' not in device_config:
                device_config['timeout'] = self.connection_timeout
                
            # Set default connection timeout
            if 'conn_timeout' not in device_config:
                device_config['conn_timeout'] = self.connection_timeout
                
            logger.info(f"Connecting to {device_config['host']}...")
            connection = ConnectHandler(**device_config)
            
            if enable_mode and 'secret' in device_config:
                connection.enable()
                
            # Cache the connection
            with self._lock:
                if len(self._connection_pool) < self.max_connections:
                    self._connection_pool[device_key] = connection
                    
            return connection
            
        except NetmikoAuthenticationException as e:
            logger.error(f"Authentication failed for {device_config['host']}: {str(e)}")
            raise CredentialError(f"Authentication failed: {str(e)}")
        except NetmikoTimeoutException as e:
            logger.error(f"Connection timeout for {device_config['host']}: {str(e)}")
            raise ConnectionError(f"Connection timeout: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error connecting to {device_config['host']}: {str(e)}")
            raise ConnectionError(f"Connection failed: {str(e)}")
    
    def close_all_connections(self):
        """Close all cached connections"""
        with self._lock:
            for conn in self._connection_pool.values():
                try:
                    conn.disconnect()
                except:
                    pass
            self._connection_pool.clear()


# Credential management
class CredentialManager:
    """Manages device credentials with environment variable support"""
    
    def __init__(self):
        self._credentials_cache = {}
        
    def get_credentials(self, username: Optional[str] = None, 
                       prompt_for_password: bool = True) -> Dict[str, str]:
        """
        Get credentials for device access
        
        Args:
            username: Username (will use env or prompt if not provided)
            prompt_for_password: Whether to prompt for password
            
        Returns:
            Dictionary with username, password, and optional secret
        """
        # Get username
        if not username:
            username = os.environ.get('NETWORK_USERNAME') or os.environ.get('DEFAULT_USERNAME')
            if not username and prompt_for_password:
                username = input("Enter username: ").strip()
                
        # Check cache first
        if username in self._credentials_cache:
            return self._credentials_cache[username]
            
        # Get password from environment
        password = os.environ.get('NETWORK_PASSWORD') or os.environ.get('DEFAULT_PASSWORD')
        secret = os.environ.get('ENABLE_PASSWORD') or os.environ.get('DEFAULT_SECRET')
        
        # Prompt for password if needed
        if not password and prompt_for_password:
            password = getpass.getpass(f"Enter password for {username}: ")
            
        if not password:
            raise CredentialError("No password available")
            
        credentials = {
            'username': username,
            'password': password
        }
        
        if secret:
            credentials['secret'] = secret
            
        self._credentials_cache[username] = credentials
        return credentials


# Progress tracking
class ProgressTracker:
    """Track and display progress for operations"""
    
    def __init__(self, total: int, description: str = "Processing", 
                 disable: bool = False):
        """
        Initialize progress tracker
        
        Args:
            total: Total number of items to process
            description: Description of the operation
            disable: Whether to disable progress display
        """
        self.total = total
        self.description = description
        self.disable = disable
        self._pbar = None
        self._lock = threading.Lock()
        self._completed = 0
        self._failed = 0
        
    def __enter__(self):
        if not self.disable:
            self._pbar = tqdm(total=self.total, desc=self.description)
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._pbar:
            self._pbar.close()
            
    def update(self, success: bool = True, description: Optional[str] = None):
        """Update progress"""
        with self._lock:
            if success:
                self._completed += 1
            else:
                self._failed += 1
                
            if self._pbar:
                self._pbar.update(1)
                if description:
                    self._pbar.set_description(description)
                    
    def set_description(self, description: str):
        """Update progress description"""
        if self._pbar:
            self._pbar.set_description(description)
            
    @property
    def stats(self) -> Dict[str, int]:
        """Get progress statistics"""
        with self._lock:
            return {
                'total': self.total,
                'completed': self._completed,
                'failed': self._failed,
                'success_rate': (self._completed / self.total * 100) if self.total > 0 else 0
            }


# Configuration management
def load_config(config_file: Union[str, Path]) -> Dict[str, Any]:
    """
    Load configuration from YAML or JSON file
    
    Args:
        config_file: Path to configuration file
        
    Returns:
        Configuration dictionary
    """
    config_path = Path(config_file)
    
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_file}")
    
    with open(config_path, 'r') as f:
        if config_path.suffix in ['.yaml', '.yml']:
            return yaml.safe_load(f)
        elif config_path.suffix == '.json':
            return json.load(f)
        else:
            raise ValueError(f"Unsupported configuration file format: {config_path.suffix}")


# Logging utilities
def setup_logging(script_name: str, config: Dict[str, Any]) -> logging.Logger:
    """
    Setup logging configuration
    
    Args:
        script_name: Name of the script for log file
        config: Logging configuration dict
        
    Returns:
        Configured logger
    """
    log_level = config.get('level', 'INFO')
    log_format = config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Create logs directory if needed
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    
    # Setup handlers
    handlers = []
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_level.upper()))
    console_handler.setFormatter(logging.Formatter(log_format))
    handlers.append(console_handler)
    
    # File handler
    log_file = log_dir / f"{script_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(getattr(logging, log_level.upper()))
    file_handler.setFormatter(logging.Formatter(log_format))
    handlers.append(file_handler)
    
    # Configure logger
    logger = logging.getLogger(script_name)
    logger.setLevel(getattr(logging, log_level.upper()))
    logger.handlers = handlers
    
    return logger