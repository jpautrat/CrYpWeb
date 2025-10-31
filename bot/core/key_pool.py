"""
API key pooling and routing system.
Implements round-robin with health monitoring and automatic failover.
"""
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from collections import deque
import time
from loguru import logger

from ..config.settings import APIConfig


class KeyHealth:
    """Health status for an API key"""
    def __init__(self, key_id: int):
        self.key_id = key_id
        self.is_healthy = True
        self.last_error: Optional[datetime] = None
        self.error_count = 0
        self.success_count = 0
        self.last_success: Optional[datetime] = None
        self.request_count = 0
        self.rate_limit_reset: Optional[datetime] = None
        self.avg_latency_ms = 0.0
        self.latency_history = deque(maxlen=100)
        self.consecutive_failures = 0
        self.cooldown_until: Optional[datetime] = None
    
    def record_success(self, latency_ms: float):
        """Record successful API call"""
        self.success_count += 1
        self.last_success = datetime.now()
        self.consecutive_failures = 0
        self.latency_history.append(latency_ms)
        self.avg_latency_ms = sum(self.latency_history) / len(self.latency_history)
        
        if not self.is_healthy and self.consecutive_failures == 0:
            self.is_healthy = True
            logger.info(f"Key {self.key_id} recovered and marked healthy")
    
    def record_error(self, error_type: str = "generic"):
        """Record API error"""
        self.error_count += 1
        self.last_error = datetime.now()
        self.consecutive_failures += 1
        
        if error_type == "rate_limit":
            # Rate limit cooldown: 60 seconds
            self.rate_limit_reset = datetime.now() + timedelta(seconds=60)
            self.cooldown_until = self.rate_limit_reset
            logger.warning(f"Key {self.key_id} hit rate limit, cooldown until {self.rate_limit_reset}")
        
        # Mark unhealthy after 3 consecutive failures
        if self.consecutive_failures >= 3:
            self.is_healthy = False
            # Cooldown for 5 minutes on multiple failures
            self.cooldown_until = datetime.now() + timedelta(minutes=5)
            logger.error(f"Key {self.key_id} marked unhealthy after {self.consecutive_failures} failures")
    
    def is_available(self) -> bool:
        """Check if key is available for use"""
        if not self.is_healthy:
            return False
        
        if self.cooldown_until and datetime.now() < self.cooldown_until:
            return False
        
        if self.rate_limit_reset and datetime.now() < self.rate_limit_reset:
            return False
        
        return True
    
    def get_health_score(self) -> float:
        """Calculate health score (0-1) for routing"""
        if not self.is_available():
            return 0.0
        
        # Base score from health status
        score = 1.0
        
        # Penalize high latency (target: <100ms)
        if self.avg_latency_ms > 100:
            latency_penalty = min(0.3, (self.avg_latency_ms - 100) / 500)
            score -= latency_penalty
        
        # Penalize recent errors
        if self.error_count > 0:
            error_penalty = min(0.2, self.error_count / (self.error_count + self.success_count))
            score -= error_penalty
        
        return max(0.0, min(1.0, score))


class KeyPool:
    """Manages pool of API keys with intelligent routing"""
    
    def __init__(self, api_config: APIConfig):
        self.api_config = api_config
        self.keys: List[Dict] = api_config.keys
        self.health: Dict[int, KeyHealth] = {}
        self.round_robin_index = 0
        self.usage_history = deque(maxlen=1000)  # Track usage for load balancing
        
        # Initialize health tracking for all keys
        for key in self.keys:
            key_id = key["id"]
            self.health[key_id] = KeyHealth(key_id)
        
        logger.info(f"Initialized key pool with {len(self.keys)} keys")
    
    def get_next_key(self, strategy: str = "round_robin") -> Optional[Dict]:
        """
        Get next available API key based on routing strategy.
        
        Args:
            strategy: 'round_robin', 'health_based', or 'least_used'
        
        Returns:
            API key dictionary or None if no keys available
        """
        available_keys = [k for k in self.keys if self.health[k["id"]].is_available()]
        
        if not available_keys:
            logger.error("No healthy API keys available")
            return None
        
        if strategy == "health_based":
            # Select key with best health score
            key_scores = [
                (k, self.health[k["id"]].get_health_score())
                for k in available_keys
            ]
            key_scores.sort(key=lambda x: x[1], reverse=True)
            selected_key = key_scores[0][0]
        
        elif strategy == "least_used":
            # Select key with fewest recent requests
            key_usage = [
                (k, self.health[k["id"]].request_count)
                for k in available_keys
            ]
            key_usage.sort(key=lambda x: x[1])
            selected_key = key_usage[0][0]
        
        else:  # round_robin
            # Simple round-robin among available keys
            selected_key = available_keys[self.round_robin_index % len(available_keys)]
            self.round_robin_index += 1
        
        # Record usage
        key_id = selected_key["id"]
        self.health[key_id].request_count += 1
        self.usage_history.append({
            'key_id': key_id,
            'timestamp': datetime.now()
        })
        
        return selected_key
    
    def record_success(self, key_id: int, latency_ms: float):
        """Record successful API call"""
        if key_id in self.health:
            self.health[key_id].record_success(latency_ms)
    
    def record_error(self, key_id: int, error_type: str = "generic"):
        """Record API error"""
        if key_id in self.health:
            self.health[key_id].record_error(error_type)
    
    def get_key_health(self, key_id: int) -> Optional[KeyHealth]:
        """Get health status for a specific key"""
        return self.health.get(key_id)
    
    def get_all_health_status(self) -> Dict[int, Dict]:
        """Get health status for all keys"""
        return {
            key_id: {
                'is_healthy': health.is_healthy,
                'is_available': health.is_available(),
                'success_count': health.success_count,
                'error_count': health.error_count,
                'avg_latency_ms': health.avg_latency_ms,
                'consecutive_failures': health.consecutive_failures,
                'cooldown_until': health.cooldown_until.isoformat() if health.cooldown_until else None
            }
            for key_id, health in self.health.items()
        }
    
    def force_health_check(self, key_id: int):
        """Force health check for a key (mark as healthy)"""
        if key_id in self.health:
            self.health[key_id].is_healthy = True
            self.health[key_id].cooldown_until = None
            self.health[key_id].consecutive_failures = 0
            logger.info(f"Force marked key {key_id} as healthy")
