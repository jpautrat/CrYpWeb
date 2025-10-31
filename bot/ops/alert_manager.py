"""
Alert Manager - System alerts and notifications
"""

from typing import List, Dict
from datetime import datetime
from enum import Enum
from loguru import logger


class AlertLevel(str, Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertManager:
    """
    Manages system alerts and notifications.
    Tracks alert history and provides alerting capabilities.
    """
    
    def __init__(self, max_alerts: int = 1000):
        self.max_alerts = max_alerts
        self.alerts: List[Dict] = []
        self.alert_counts = {level.value: 0 for level in AlertLevel}
        
        logger.info("AlertManager initialized")
    
    def alert(
        self,
        level: AlertLevel,
        component: str,
        message: str,
        details: Dict = None
    ):
        """
        Create an alert.
        
        Args:
            level: Alert severity level
            component: Component that generated alert
            message: Alert message
            details: Additional details dictionary
        """
        alert = {
            'timestamp': datetime.now().isoformat(),
            'level': level.value,
            'component': component,
            'message': message,
            'details': details or {}
        }
        
        self.alerts.append(alert)
        self.alert_counts[level.value] += 1
        
        # Keep only recent alerts
        if len(self.alerts) > self.max_alerts:
            self.alerts = self.alerts[-self.max_alerts:]
        
        # Log based on level
        log_message = f"[{component}] {message}"
        
        if level == AlertLevel.CRITICAL:
            logger.critical(log_message)
        elif level == AlertLevel.ERROR:
            logger.error(log_message)
        elif level == AlertLevel.WARNING:
            logger.warning(log_message)
        else:
            logger.info(log_message)
    
    def get_recent_alerts(self, count: int = 100, level: AlertLevel = None) -> List[Dict]:
        """
        Get recent alerts.
        
        Args:
            count: Number of alerts to return
            level: Filter by alert level
            
        Returns:
            List of alert dictionaries
        """
        alerts = self.alerts
        
        if level:
            alerts = [a for a in alerts if a['level'] == level.value]
        
        return alerts[-count:]
    
    def get_alert_summary(self) -> Dict:
        """Get alert statistics"""
        return {
            'total_alerts': len(self.alerts),
            'alert_counts': self.alert_counts.copy(),
            'recent_critical': len([a for a in self.alerts[-100:] if a['level'] == 'critical']),
            'recent_errors': len([a for a in self.alerts[-100:] if a['level'] == 'error'])
        }
