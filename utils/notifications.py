"""
Notification utilities for alerts and reports

Supports:
- Email notifications
- Webhook notifications (Slack, Teams, etc.)
- Logging notifications
"""

import os
import json
import logging
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from enum import Enum


logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class NotificationManager:
    """Manages notifications across different channels"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize notification manager with configuration"""
        self.config = config or {}
        self.email_config = self.config.get('email', {})
        self.webhook_config = self.config.get('webhook', {})
        self.enabled = self.config.get('enabled', True)
        
    def send_notification(self, notification_type: str, message: str, 
                         data: Dict[str, Any] = None, 
                         severity: AlertSeverity = AlertSeverity.MEDIUM,
                         attachments: List[str] = None) -> bool:
        """
        Send notification through configured channels
        
        Args:
            notification_type: Type of notification (e.g., 'health_check', 'error')
            message: Notification message
            data: Additional data to include
            severity: Alert severity level
            attachments: List of file paths to attach
            
        Returns:
            Success status
        """
        if not self.enabled:
            logger.info("Notifications disabled")
            return True
            
        success = True
        
        # Send through each configured channel
        if self.email_config.get('enabled'):
            try:
                self._send_email(notification_type, message, data, severity, attachments)
            except Exception as e:
                logger.error(f"Failed to send email notification: {e}")
                success = False
                
        if self.webhook_config.get('enabled'):
            try:
                self._send_webhook(notification_type, message, data, severity)
            except Exception as e:
                logger.error(f"Failed to send webhook notification: {e}")
                success = False
                
        # Always log notifications
        self._log_notification(notification_type, message, data, severity)
        
        return success
    
    def _send_email(self, notification_type: str, message: str,
                   data: Dict[str, Any] = None, 
                   severity: AlertSeverity = AlertSeverity.MEDIUM,
                   attachments: List[str] = None):
        """Send email notification"""
        # Get email configuration
        smtp_server = self.email_config.get('smtp_server')
        smtp_port = self.email_config.get('smtp_port', 587)
        username = os.environ.get('EMAIL_USERNAME') or self.email_config.get('username')
        password = os.environ.get('EMAIL_PASSWORD') or self.email_config.get('password')
        from_addr = self.email_config.get('from_address', username)
        to_addrs = self.email_config.get('recipients', [])
        
        if not all([smtp_server, username, password, to_addrs]):
            raise ValueError("Email configuration incomplete")
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = from_addr
        msg['To'] = ', '.join(to_addrs)
        msg['Subject'] = f"[{severity.value.upper()}] Network Monitoring Alert: {notification_type}"
        
        # Create body
        body = f"""
        <html>
        <body>
            <h2>Network Monitoring Alert</h2>
            <p><strong>Type:</strong> {notification_type}</p>
            <p><strong>Severity:</strong> {severity.value.upper()}</p>
            <p><strong>Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            
            <h3>Message:</h3>
            <p>{message}</p>
            
            {self._format_data_html(data) if data else ''}
        </body>
        </html>
        """
        
        msg.attach(MIMEText(body, 'html'))
        
        # Add attachments
        if attachments:
            for filepath in attachments:
                if os.path.exists(filepath):
                    self._attach_file(msg, filepath)
        
        # Send email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(username, password)
            server.send_message(msg)
            
        logger.info(f"Email notification sent to {', '.join(to_addrs)}")
    
    def _send_webhook(self, notification_type: str, message: str,
                     data: Dict[str, Any] = None,
                     severity: AlertSeverity = AlertSeverity.MEDIUM):
        """Send webhook notification"""
        webhook_url = self.webhook_config.get('url')
        if not webhook_url:
            raise ValueError("Webhook URL not configured")
        
        # Prepare payload based on webhook type
        webhook_type = self.webhook_config.get('type', 'generic')
        
        if webhook_type == 'slack':
            payload = self._format_slack_payload(notification_type, message, data, severity)
        elif webhook_type == 'teams':
            payload = self._format_teams_payload(notification_type, message, data, severity)
        else:
            # Generic webhook payload
            payload = {
                'notification_type': notification_type,
                'message': message,
                'severity': severity.value,
                'timestamp': datetime.now().isoformat(),
                'data': data
            }
        
        # Send webhook
        response = requests.post(webhook_url, json=payload, timeout=30)
        response.raise_for_status()
        
        logger.info(f"Webhook notification sent to {webhook_type}")
    
    def _log_notification(self, notification_type: str, message: str,
                         data: Dict[str, Any] = None,
                         severity: AlertSeverity = AlertSeverity.MEDIUM):
        """Log notification"""
        log_level = {
            AlertSeverity.LOW: logging.INFO,
            AlertSeverity.MEDIUM: logging.WARNING,
            AlertSeverity.HIGH: logging.ERROR,
            AlertSeverity.CRITICAL: logging.CRITICAL
        }.get(severity, logging.INFO)
        
        logger.log(log_level, f"[{notification_type}] {message}")
        if data:
            logger.log(log_level, f"Data: {json.dumps(data, indent=2, default=str)}")
    
    def _format_data_html(self, data: Dict[str, Any]) -> str:
        """Format data dictionary as HTML"""
        if not data:
            return ""
            
        html = "<h3>Additional Data:</h3><table border='1' style='border-collapse: collapse;'>"
        for key, value in data.items():
            html += f"<tr><td style='padding: 5px;'><strong>{key}</strong></td>"
            html += f"<td style='padding: 5px;'>{value}</td></tr>"
        html += "</table>"
        
        return html
    
    def _attach_file(self, msg: MIMEMultipart, filepath: str):
        """Attach file to email message"""
        with open(filepath, 'rb') as f:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(f.read())
            
        encoders.encode_base64(part)
        part.add_header(
            'Content-Disposition',
            f'attachment; filename= {os.path.basename(filepath)}'
        )
        
        msg.attach(part)
    
    def _format_slack_payload(self, notification_type: str, message: str,
                             data: Dict[str, Any] = None,
                             severity: AlertSeverity = AlertSeverity.MEDIUM) -> Dict:
        """Format payload for Slack webhook"""
        color = {
            AlertSeverity.LOW: '#36a64f',      # green
            AlertSeverity.MEDIUM: '#ff9900',   # orange
            AlertSeverity.HIGH: '#ff0000',     # red
            AlertSeverity.CRITICAL: '#990000'  # dark red
        }.get(severity, '#808080')
        
        fields = [
            {
                "title": "Type",
                "value": notification_type,
                "short": True
            },
            {
                "title": "Severity",
                "value": severity.value.upper(),
                "short": True
            }
        ]
        
        if data:
            for key, value in data.items():
                fields.append({
                    "title": key,
                    "value": str(value),
                    "short": len(str(value)) < 40
                })
        
        return {
            "attachments": [
                {
                    "color": color,
                    "title": "Network Monitoring Alert",
                    "text": message,
                    "fields": fields,
                    "footer": "Network Monitoring Suite",
                    "ts": int(datetime.now().timestamp())
                }
            ]
        }
    
    def _format_teams_payload(self, notification_type: str, message: str,
                             data: Dict[str, Any] = None,
                             severity: AlertSeverity = AlertSeverity.MEDIUM) -> Dict:
        """Format payload for Microsoft Teams webhook"""
        theme_color = {
            AlertSeverity.LOW: '00FF00',      # green
            AlertSeverity.MEDIUM: 'FFA500',   # orange
            AlertSeverity.HIGH: 'FF0000',     # red
            AlertSeverity.CRITICAL: '8B0000'  # dark red
        }.get(severity, '808080')
        
        facts = [
            {
                "name": "Type:",
                "value": notification_type
            },
            {
                "name": "Severity:",
                "value": severity.value.upper()
            },
            {
                "name": "Time:",
                "value": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        ]
        
        if data:
            for key, value in data.items():
                facts.append({
                    "name": f"{key}:",
                    "value": str(value)
                })
        
        return {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "themeColor": theme_color,
            "summary": f"Network Monitoring Alert: {notification_type}",
            "sections": [
                {
                    "activityTitle": "Network Monitoring Alert",
                    "activitySubtitle": message,
                    "facts": facts,
                    "markdown": True
                }
            ]
        }