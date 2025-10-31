"""
Health monitoring system for trading infrastructure.
"""
from typing import Dict
from datetime import datetime, timedelta
from collections import deque
from loguru import logger


class HealthMonitor:
    """Monitors system health and performance"""
    
    def __init__(self):
        self.metrics: Dict[str, deque] = {
            'api_latency': deque(maxlen=1000),
            'decision_latency': deque(maxlen=1000),
            'feature_computation': deque(maxlen=1000),
            'order_execution': deque(maxlen=1000)
        }
        self.last_check: Dict[str, datetime] = {}
        self.health_status: Dict[str, bool] = {}
    
    def record_metric(self, metric_name: str, value: float):
        """Record a metric value"""
        if metric_name in self.metrics:
            self.metrics[metric_name].append({
                'value': value,
                'timestamp': datetime.now()
            })
    
    def get_health_status(self) -> Dict:
        """Get overall health status"""
        status = {
            'overall': True,
            'components': {}
        }
        
        # Check API latency
        if 'api_latency' in self.metrics and self.metrics['api_latency']:
            avg_latency = sum(m['value'] for m in self.metrics['api_latency']) / len(self.metrics['api_latency'])
            status['components']['api'] = {
                'healthy': avg_latency < 500,
                'avg_latency_ms': avg_latency
            }
            if avg_latency >= 500:
                status['overall'] = False
        
        # Check decision latency
        if 'decision_latency' in self.metrics and self.metrics['decision_latency']:
            avg_latency = sum(m['value'] for m in self.metrics['decision_latency']) / len(self.metrics['decision_latency'])
            status['components']['decision'] = {
                'healthy': avg_latency < 100,
                'avg_latency_ms': avg_latency
            }
            if avg_latency >= 100:
                status['overall'] = False
        
        return status
    
    def get_statistics(self) -> Dict:
        """Get performance statistics"""
        stats = {}
        
        for metric_name, values in self.metrics.items():
            if values:
                metric_values = [m['value'] for m in values]
                stats[metric_name] = {
                    'count': len(metric_values),
                    'avg': sum(metric_values) / len(metric_values),
                    'min': min(metric_values),
                    'max': max(metric_values),
                    'p50': sorted(metric_values)[len(metric_values) // 2],
                    'p95': sorted(metric_values)[int(len(metric_values) * 0.95)],
                    'p99': sorted(metric_values)[int(len(metric_values) * 0.99)]
                }
        
        return stats
