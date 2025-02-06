"""
Advanced error alerting and notification system with multiple channels
"""
from typing import Dict, Optional, List, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
import asyncio
import json
import aiohttp
import smtplib
from email.mime.text import MIMEText
import logging
from enum import Enum

class AlertSeverity(Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class AlertChannel(Enum):
    EMAIL = "email"
    SLACK = "slack"
    SMS = "sms"
    PAGERDUTY = "pagerduty"

@dataclass
class AlertConfig:
    """Alert configuration"""
    severity: AlertSeverity
    channels: List[AlertChannel]
    cooldown: int  # seconds
    aggregation_window: int  # seconds
    max_alerts_per_hour: int

@dataclass
class Alert:
    """Alert details"""
    id: str
    timestamp: datetime
    severity: AlertSeverity
    source: str
    message: str
    details: Dict
    metrics: Optional[Dict] = None

class AlertManager:
    """Central alert management system"""
    
    def __init__(
        self,
        config: Dict,
        metrics_collector,
        logger,
        error_handler
    ):
        self.config = config
        self.metrics_collector = metrics_collector
        self.logger = logger
        self.error_handler = error_handler
        
        # Alert configuration
        self.alert_configs = self._load_alert_configs()
        
        # Alert state
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.alert_counts: Dict[str, int] = {}
        
        # Alert handlers
        self.alert_handlers: Dict[AlertChannel, Callable] = {
            AlertChannel.EMAIL: self._send_email_alert,
            AlertChannel.SLACK: self._send_slack_alert,
            AlertChannel.SMS: self._send_sms_alert,
            AlertChannel.PAGERDUTY: self._send_pagerduty_alert
        }
        
        # Rate limiting
        self._last_alert_times: Dict[str, datetime] = {}
        self._alert_cooldowns: Dict[str, datetime] = {}
        
        # HTTP session for API calls
        self._http_session: Optional[aiohttp.ClientSession] = None
    
    async def initialize(self) -> None:
        """Initialize alert manager"""
        self._http_session = aiohttp.ClientSession()
    
    async def cleanup(self) -> None:
        """Cleanup resources"""
        if self._http_session:
            await self._http_session.close()
    
    def _load_alert_configs(self) -> Dict[str, AlertConfig]:
        """Load alert configurations"""
        return {
            'latency_breach': AlertConfig(
                severity=AlertSeverity.CRITICAL,
                channels=[AlertChannel.SLACK, AlertChannel.PAGERDUTY],
                cooldown=300,
                aggregation_window=60,
                max_alerts_per_hour=10
            ),
            'error_rate_high': AlertConfig(
                severity=AlertSeverity.ERROR,
                channels=[AlertChannel.SLACK, AlertChannel.EMAIL],
                cooldown=600,
                aggregation_window=300,
                max_alerts_per_hour=20
            ),
            'position_limit_breach': AlertConfig(
                severity=AlertSeverity.CRITICAL,
                channels=[AlertChannel.SLACK, AlertChannel.PAGERDUTY, AlertChannel.SMS],
                cooldown=0,  # No cooldown for critical alerts
                aggregation_window=0,
                max_alerts_per_hour=100
            ),
            'system_warning': AlertConfig(
                severity=AlertSeverity.WARNING,
                channels=[AlertChannel.SLACK],
                cooldown=1800,
                aggregation_window=900,
                max_alerts_per_hour=50
            )
        }
    
    async def send_alert(
        self,
        alert_type: str,
        message: str,
        details: Dict,
        severity: Optional[AlertSeverity] = None,
        metrics: Optional[Dict] = None
    ) -> None:
        """Send alert through configured channels"""
        try:
            # Get alert configuration
            config = self.alert_configs.get(alert_type)
            if not config:
                self.logger.warning(f"No configuration found for alert type: {alert_type}")
                return
            
            # Check rate limits
            if not self._check_rate_limits(alert_type, config):
                return
            
            # Create alert
            alert = Alert(
                id=f"{alert_type}_{datetime.utcnow().timestamp()}",
                timestamp=datetime.utcnow(),
                severity=severity or config.severity,
                source=alert_type,
                message=message,
                details=details,
                metrics=metrics
            )
            
            # Store alert
            self.active_alerts[alert.id] = alert
            self.alert_history.append(alert)
            self._last_alert_times[alert_type] = datetime.utcnow()
            
            # Send through configured channels
            await self._send_alert_to_channels(alert, config.channels)
            
            # Record metric
            self.metrics_collector.record_error(alert_type, alert.severity.value)
            
        except Exception as e:
            self.error_handler.handle_error(f"Failed to send alert: {e}")
    
    def _check_rate_limits(
        self,
        alert_type: str,
        config: AlertConfig
    ) -> bool:
        """Check if alert should be rate limited"""
        current_time = datetime.utcnow()
        
        # Check cooldown
        last_alert = self._last_alert_times.get(alert_type)
        if last_alert and config.cooldown > 0:
            if (current_time - last_alert).total_seconds() < config.cooldown:
                return False
        
        # Check hourly limit
        hour_start = current_time.replace(minute=0, second=0, microsecond=0)
        alerts_this_hour = sum(
            1 for alert in self.alert_history
            if alert.source == alert_type
            and alert.timestamp >= hour_start
        )
        
        return alerts_this_hour < config.max_alerts_per_hour
    
    async def _send_alert_to_channels(
        self,
        alert: Alert,
        channels: List[AlertChannel]
    ) -> None:
        """Send alert through specified channels"""
        tasks = []
        for channel in channels:
            handler = self.alert_handlers.get(channel)
            if handler:
                tasks.append(handler(alert))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _send_email_alert(self, alert: Alert) -> None:
        """Send alert via email"""
        try:
            email_config = self.config['email']
            
            # Create message
            msg = MIMEText(self._format_alert_message(alert))
            msg['Subject'] = f"[{alert.severity.value}] {alert.source}: {alert.message}"
            msg['From'] = email_config['from_address']
            msg['To'] = email_config['to_address']
            
            # Send email
            with smtplib.SMTP(email_config['smtp_host'], email_config['smtp_port']) as server:
                if email_config.get('use_tls'):
                    server.starttls()
                if email_config.get('username'):
                    server.login(email_config['username'], email_config['password'])
                server.send_message(msg)
                
        except Exception as e:
            self.error_handler.handle_error(f"Failed to send email alert: {e}")
    
    async def _send_slack_alert(self, alert: Alert) -> None:
        """Send alert to Slack"""
        try:
            if not self._http_session:
                return
                
            webhook_url = self.config['slack']['webhook_url']
            
            # Create message
            message = {
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*[{alert.severity.value}] {alert.source}*\n{alert.message}"
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"```{json.dumps(alert.details, indent=2)}```"
                        }
                    }
                ]
            }
            
            # Send to Slack
            async with self._http_session.post(webhook_url, json=message) as response:
                if response.status != 200:
                    raise ValueError(f"Slack API returned status {response.status}")
                
        except Exception as e:
            self.error_handler.handle_error(f"Failed to send Slack alert: {e}")
    
    async def _send_sms_alert(self, alert: Alert) -> None:
        """Send alert via SMS"""
        try:
            if not self._http_session:
                return
                
            sms_config = self.config['sms']
            
            # Create message
            message = f"[{alert.severity.value}] {alert.source}: {alert.message}"
            
            # Send SMS using configured provider
            if sms_config['provider'] == 'twilio':
                await self._send_twilio_sms(message, sms_config)
            elif sms_config['provider'] == 'aws_sns':
                await self._send_sns_sms(message, sms_config)
                
        except Exception as e:
            self.error_handler.handle_error(f"Failed to send SMS alert: {e}")
    
    async def _send_pagerduty_alert(self, alert: Alert) -> None:
        """Send alert to PagerDuty"""
        try:
            if not self._http_session:
                return
                
            pagerduty_config = self.config['pagerduty']
            
            # Create incident
            payload = {
                "routing_key": pagerduty_config['routing_key'],
                "event_action": "trigger",
                "payload": {
                    "summary": f"[{alert.severity.value}] {alert.source}: {alert.message}",
                    "source": alert.source,
                    "severity": alert.severity.value.lower(),
                    "custom_details": alert.details
                }
            }
            
            # Send to PagerDuty
            async with self._http_session.post(
                "https://events.pagerduty.com/v2/enqueue",
                json=payload
            ) as response:
                if response.status != 202:
                    raise ValueError(f"PagerDuty API returned status {response.status}")
                
        except Exception as e:
            self.error_handler.handle_error(f"Failed to send PagerDuty alert: {e}")
    
    def _format_alert_message(self, alert: Alert) -> str:
        """Format alert message for text-based channels"""
        message_parts = [
            f"Alert: {alert.source}",
            f"Severity: {alert.severity.value}",
            f"Time: {alert.timestamp.isoformat()}",
            f"Message: {alert.message}",
            "\nDetails:",
            json.dumps(alert.details, indent=2)
        ]
        
        if alert.metrics:
            message_parts.extend([
                "\nMetrics:",
                json.dumps(alert.metrics, indent=2)
            ])
        
        return "\n".join(message_parts)

class AlertError(Exception):
    """Custom exception for alert-related errors"""
    pass