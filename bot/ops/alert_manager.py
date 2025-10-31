"""
Alert management system for notifications.
"""
from typing import Dict, List
from datetime import datetime
from enum import Enum
from loguru import logger


class AlertLevel(Enum):
    """Alert severity levels"""
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class AlertManager:
    """Manages alerts and notifications"""
    
    def __init__(self):
        self.alerts: List[Dict] = []
        self.max_alerts = 1000
    
    def send_alert(self, level: AlertLevel, message: str, context: Dict = None):
        """Send an alert"""
        alert = {
            'timestamp': datetime.now(),
            'level': level.value,
            'message': message,
            'context': context or {}
        }
        
        self.alerts.append(alert)
        if len(self.alerts) > self.max_alerts:
            self.alerts.pop(0)
        
        # Log based on level
        if level == AlertLevel.CRITICAL:
            logger.critical(f"ALERT: {message}")
        elif level == AlertLevel.WARNING:
            logger.warning(f"ALERT: {message}")
        else:
            logger.info(f"ALERT: {message}")
    
    def get_recent_alerts(self, level: AlertLevel = None, limit: int = 100) -> List[Dict]:
        """Get recent alerts"""
        filtered = self.alerts
        
        if level:
            filtered = [a for a in filtered if a['level'] == level.value]
        
        return filtered[-limit:]
    
    def get_alert_statistics(self) -> Dict:
        """Get alert statistics"""
        stats = {
            'total': len(self.alerts),
            'critical': len([a for a in self.alerts if a['level'] == 'critical']),
            'warning': len([a for a in self.alerts if a['level'] == 'warning']),
            'info': len([a for a in self.alerts if a['level'] == 'info'])
        }
        return stats
