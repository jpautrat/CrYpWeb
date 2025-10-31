"""
Health Monitor - System health checking and metrics collection
"""

import psutil
from typing import Dict
from datetime import datetime
from loguru import logger


class HealthMonitor:
    """
    Monitors system health metrics including CPU, memory, latency, and component status.
    """
    
    def __init__(self):
        self.start_time = datetime.now()
        self.health_checks = 0
        logger.info("HealthMonitor initialized")
    
    def check_system_health(self) -> Dict:
        """
        Perform comprehensive system health check.
        
        Returns:
            Dictionary with health metrics
        """
        self.health_checks += 1
        
        # System metrics
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Uptime
        uptime = (datetime.now() - self.start_time).total_seconds()
        
        health_status = {
            'timestamp': datetime.now().isoformat(),
            'uptime_seconds': uptime,
            'uptime_hours': uptime / 3600,
            'cpu_percent': cpu_percent,
            'memory_used_mb': memory.used / (1024 * 1024),
            'memory_available_mb': memory.available / (1024 * 1024),
            'memory_percent': memory.percent,
            'disk_used_gb': disk.used / (1024 * 1024 * 1024),
            'disk_free_gb': disk.free / (1024 * 1024 * 1024),
            'disk_percent': disk.percent,
            'health_checks_performed': self.health_checks,
            'is_healthy': self._determine_health(cpu_percent, memory.percent, disk.percent)
        }
        
        return health_status
    
    def _determine_health(self, cpu: float, memory: float, disk: float) -> bool:
        """Determine overall health status"""
        # Thresholds for health
        if cpu > 90:
            logger.warning(f"High CPU usage: {cpu}%")
            return False
        
        if memory > 85:
            logger.warning(f"High memory usage: {memory}%")
            return False
        
        if disk > 90:
            logger.warning(f"High disk usage: {disk}%")
            return False
        
        return True
    
    def check_component_health(self, components: Dict) -> Dict:
        """
        Check health of trading system components.
        
        Args:
            components: Dictionary of component names to status
            
        Returns:
            Component health summary
        """
        healthy_count = sum(1 for status in components.values() if status)
        total_count = len(components)
        
        return {
            'components': components,
            'healthy_count': healthy_count,
            'total_count': total_count,
            'all_healthy': healthy_count == total_count
        }
