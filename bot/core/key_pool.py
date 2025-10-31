"""
API key pooling and load balancing system.
Manages 5 API keys with round-robin routing, health monitoring, and failover.
"""
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from loguru import logger
from enum import Enum

from bot.core.rest_client import KrakenRESTClient
from bot.config.settings import settings


class KeyStatus(Enum):
    """Key health status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"
    COOLDOWN = "cooldown"


@dataclass
class KeyHealth:
    """Health status for an API key."""
    key_id: int
    status: KeyStatus = KeyStatus.HEALTHY
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    consecutive_failures: int = 0
    total_requests: int = 0
    total_failures: int = 0
    avg_response_time_ms: float = 0.0
    last_response_time_ms: Optional[float] = None
    rate_limit_reset: Optional[datetime] = None
    
    # Response time tracking (for load balancing)
    response_times: List[float] = field(default_factory=list)
    max_response_times = 10  # Keep last 10 response times
    
    def update_response_time(self, response_time_ms: float):
        """Update response time tracking."""
        self.last_response_time_ms = response_time_ms
        self.response_times.append(response_time_ms)
        if len(self.response_times) > self.max_response_times:
            self.response_times.pop(0)
        
        # Update average
        if self.response_times:
            self.avg_response_time_ms = sum(self.response_times) / len(self.response_times)
    
    def record_success(self):
        """Record successful request."""
        self.last_success = datetime.utcnow()
        self.total_requests += 1
        self.consecutive_failures = 0
        
        if self.status == KeyStatus.FAILED:
            # Attempt recovery
            self.status = KeyStatus.DEGRADED
        elif self.consecutive_failures == 0 and self.status == KeyStatus.DEGRADED:
            self.status = KeyStatus.HEALTHY
    
    def record_failure(self, error_type: str = "unknown"):
        """Record failed request."""
        self.last_failure = datetime.utcnow()
        self.total_requests += 1
        self.total_failures += 1
        self.consecutive_failures += 1
        
        if "rate_limit" in error_type.lower():
            # Set cooldown for rate limit
            self.status = KeyStatus.COOLDOWN
            self.rate_limit_reset = datetime.utcnow() + timedelta(minutes=1)
        elif self.consecutive_failures >= 3:
            self.status = KeyStatus.FAILED
    
    def is_available(self) -> bool:
        """Check if key is available for use."""
        if self.status == KeyStatus.FAILED:
            # Check if enough time has passed for retry
            if self.last_failure:
                time_since_failure = (datetime.utcnow() - self.last_failure).total_seconds()
                if time_since_failure > 300:  # 5 minutes cooldown
                    self.status = KeyStatus.DEGRADED
                    return True
            return False
        
        if self.status == KeyStatus.COOLDOWN:
            if self.rate_limit_reset and datetime.utcnow() >= self.rate_limit_reset:
                self.status = KeyStatus.HEALTHY
                return True
            return False
        
        return True
    
    def get_score(self) -> float:
        """Get key score for load balancing (higher is better)."""
        if not self.is_available():
            return 0.0
        
        score = 1.0
        
        # Penalize by average response time (lower is better)
        if self.avg_response_time_ms > 0:
            score *= max(0.1, 1.0 - (self.avg_response_time_ms / 1000.0))
        
        # Penalize by failure rate
        if self.total_requests > 0:
            failure_rate = self.total_failures / self.total_requests
            score *= (1.0 - failure_rate)
        
        # Penalize degraded status
        if self.status == KeyStatus.DEGRADED:
            score *= 0.5
        
        return score


class KeyPool:
    """Manages pool of API keys with load balancing and failover."""
    
    def __init__(self):
        """Initialize key pool."""
        self.keys: List[KrakenRESTClient] = []
        self.health: Dict[int, KeyHealth] = {}
        self.current_index = 0
        
        # Initialize keys from settings
        for key_config in settings.api.keys:
            key_id = key_config["key_id"]
            client = KrakenRESTClient(key_config["api_key"], key_config["api_secret"])
            self.keys.append(client)
            self.health[key_id] = KeyHealth(key_id=key_id)
        
        logger.info(f"Initialized key pool with {len(self.keys)} keys")
    
    def get_key(self, preferred_key_id: Optional[int] = None) -> Tuple[KrakenRESTClient, int]:
        """
        Get next available key with load balancing.
        
        Args:
            preferred_key_id: Preferred key ID (if available)
            
        Returns:
            Tuple of (client, key_id)
        """
        # Try preferred key first if specified and available
        if preferred_key_id is not None and preferred_key_id in self.health:
            health = self.health[preferred_key_id]
            if health.is_available():
                key_idx = preferred_key_id - 1
                if 0 <= key_idx < len(self.keys):
                    return self.keys[key_idx], preferred_key_id
        
        # Find best available key
        available_keys = []
        for key_id, health in self.health.items():
            if health.is_available():
                score = health.get_score()
                available_keys.append((key_id, score))
        
        if not available_keys:
            # All keys unavailable - use round-robin on failed keys
            logger.warning("All keys unavailable, using round-robin on failed keys")
            self.current_index = (self.current_index + 1) % len(self.keys)
            return self.keys[self.current_index], self.current_index + 1
        
        # Sort by score (highest first)
        available_keys.sort(key=lambda x: x[1], reverse=True)
        best_key_id = available_keys[0][0]
        
        # Round-robin among top 3 keys to distribute load
        if len(available_keys) > 1:
            top_keys = available_keys[:3]
            key_idx = self.current_index % len(top_keys)
            best_key_id = top_keys[key_idx][0]
            self.current_index += 1
        
        key_idx = best_key_id - 1
        return self.keys[key_idx], best_key_id
    
    def record_request(self, key_id: int, success: bool, response_time_ms: float,
                      error_type: str = "unknown"):
        """
        Record request outcome for health tracking.
        
        Args:
            key_id: Key identifier
            success: Whether request succeeded
            response_time_ms: Response time in milliseconds
            error_type: Error type if failed
        """
        if key_id not in self.health:
            return
        
        health = self.health[key_id]
        health.update_response_time(response_time_ms)
        
        if success:
            health.record_success()
        else:
            health.record_failure(error_type)
    
    def get_health_summary(self) -> Dict:
        """Get health summary for all keys."""
        summary = {}
        for key_id, health in self.health.items():
            summary[key_id] = {
                "status": health.status.value,
                "avg_response_time_ms": health.avg_response_time_ms,
                "total_requests": health.total_requests,
                "total_failures": health.total_failures,
                "failure_rate": health.total_failures / health.total_requests if health.total_requests > 0 else 0.0,
                "consecutive_failures": health.consecutive_failures,
                "available": health.is_available(),
            }
        return summary
