"""
API Key Pool Manager
Manages multiple Kraken API keys with load balancing and health monitoring.
"""

import time
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from loguru import logger
from .auth_manager import AuthManager
from .rest_client import KrakenRestClient


@dataclass
class KeyStatus:
    """Status tracking for an API key"""
    key_id: int
    auth_manager: AuthManager
    rest_client: KrakenRestClient
    
    # Health metrics
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    last_request_time: float = 0.0
    last_success_time: float = 0.0
    last_failure_time: float = 0.0
    
    # Rate limiting
    rate_limit_hit: bool = False
    rate_limit_until: float = 0.0
    
    # Performance
    avg_latency_ms: float = 0.0
    latency_samples: List[float] = field(default_factory=list)
    
    # Health status
    is_healthy: bool = True
    consecutive_failures: int = 0
    cooldown_until: Optional[datetime] = None
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate"""
        if self.total_requests == 0:
            return 1.0
        return self.successful_requests / self.total_requests
    
    @property
    def is_available(self) -> bool:
        """Check if key is available for use"""
        now = time.time()
        
        # Check cooldown
        if self.cooldown_until and datetime.now() < self.cooldown_until:
            return False
        
        # Check rate limit
        if self.rate_limit_hit and now < self.rate_limit_until:
            return False
        
        # Check health
        if not self.is_healthy:
            return False
        
        return True


class KeyPool:
    """
    Manages pool of API keys with intelligent routing and failover.
    Implements round-robin with health awareness and rate limit management.
    """
    
    def __init__(
        self,
        api_keys: List[Dict[str, str]],
        rate_limit_cooldown: int = 10,
        max_consecutive_failures: int = 3,
        failure_cooldown_minutes: int = 5
    ):
        """
        Initialize key pool.
        
        Args:
            api_keys: List of dicts with 'key', 'secret', 'id'
            rate_limit_cooldown: Seconds to wait after rate limit
            max_consecutive_failures: Failures before cooldown
            failure_cooldown_minutes: Minutes to cool down after failures
        """
        self.rate_limit_cooldown = rate_limit_cooldown
        self.max_consecutive_failures = max_consecutive_failures
        self.failure_cooldown_minutes = failure_cooldown_minutes
        
        # Initialize key statuses
        self.keys: Dict[int, KeyStatus] = {}
        
        for key_info in api_keys:
            key_id = key_info['id']
            auth_manager = AuthManager(
                key_info['key'],
                key_info['secret'],
                key_id
            )
            rest_client = KrakenRestClient(auth_manager)
            
            self.keys[key_id] = KeyStatus(
                key_id=key_id,
                auth_manager=auth_manager,
                rest_client=rest_client
            )
        
        self.current_key_index = 0
        self.key_ids = sorted(self.keys.keys())
        
        logger.info(f"KeyPool initialized with {len(self.keys)} API keys")
    
    def get_next_key(self) -> Optional[KeyStatus]:
        """
        Get next available key using round-robin with health awareness.
        
        Returns:
            KeyStatus if available, None if all keys unavailable
        """
        # Try each key once
        for _ in range(len(self.keys)):
            key_id = self.key_ids[self.current_key_index]
            key_status = self.keys[key_id]
            
            # Move to next key for next request (round-robin)
            self.current_key_index = (self.current_key_index + 1) % len(self.keys)
            
            if key_status.is_available:
                return key_status
        
        # No keys available
        logger.error("No API keys available! All keys are in cooldown or unhealthy.")
        return None
    
    def get_best_key(self) -> Optional[KeyStatus]:
        """
        Get the best performing available key.
        
        Returns:
            KeyStatus with best performance metrics
        """
        available_keys = [k for k in self.keys.values() if k.is_available]
        
        if not available_keys:
            logger.error("No API keys available!")
            return None
        
        # Sort by performance (success rate, then latency)
        best_key = max(
            available_keys,
            key=lambda k: (k.success_rate, -k.avg_latency_ms)
        )
        
        return best_key
    
    def get_key_by_id(self, key_id: int) -> Optional[KeyStatus]:
        """Get specific key by ID"""
        key_status = self.keys.get(key_id)
        
        if not key_status:
            logger.error(f"Key ID {key_id} not found in pool")
            return None
        
        if not key_status.is_available:
            logger.warning(f"Key ID {key_id} is not available")
            return None
        
        return key_status
    
    def record_success(self, key_id: int, latency_ms: float):
        """
        Record successful request.
        
        Args:
            key_id: ID of key that was used
            latency_ms: Request latency in milliseconds
        """
        if key_id not in self.keys:
            return
        
        key_status = self.keys[key_id]
        key_status.total_requests += 1
        key_status.successful_requests += 1
        key_status.last_request_time = time.time()
        key_status.last_success_time = time.time()
        key_status.consecutive_failures = 0
        
        # Update latency
        key_status.latency_samples.append(latency_ms)
        if len(key_status.latency_samples) > 100:
            key_status.latency_samples = key_status.latency_samples[-100:]
        key_status.avg_latency_ms = sum(key_status.latency_samples) / len(key_status.latency_samples)
        
        # Restore health if it was degraded
        if not key_status.is_healthy and key_status.consecutive_failures == 0:
            key_status.is_healthy = True
            key_status.cooldown_until = None
            logger.info(f"Key {key_id} restored to healthy status")
    
    def record_failure(self, key_id: int, error: str, is_rate_limit: bool = False):
        """
        Record failed request.
        
        Args:
            key_id: ID of key that was used
            error: Error message
            is_rate_limit: Whether failure was due to rate limit
        """
        if key_id not in self.keys:
            return
        
        key_status = self.keys[key_id]
        key_status.total_requests += 1
        key_status.failed_requests += 1
        key_status.last_request_time = time.time()
        key_status.last_failure_time = time.time()
        key_status.consecutive_failures += 1
        
        if is_rate_limit:
            # Handle rate limit
            key_status.rate_limit_hit = True
            key_status.rate_limit_until = time.time() + self.rate_limit_cooldown
            logger.warning(
                f"Key {key_id} hit rate limit, cooldown until "
                f"{datetime.fromtimestamp(key_status.rate_limit_until).strftime('%H:%M:%S')}"
            )
        else:
            # Handle general failure
            logger.warning(
                f"Key {key_id} failure ({key_status.consecutive_failures}/"
                f"{self.max_consecutive_failures}): {error}"
            )
            
            # Put key in cooldown if too many consecutive failures
            if key_status.consecutive_failures >= self.max_consecutive_failures:
                key_status.is_healthy = False
                key_status.cooldown_until = datetime.now() + timedelta(
                    minutes=self.failure_cooldown_minutes
                )
                logger.error(
                    f"Key {key_id} marked unhealthy, cooldown until "
                    f"{key_status.cooldown_until.strftime('%H:%M:%S')}"
                )
    
    def get_pool_status(self) -> Dict:
        """
        Get overall pool status.
        
        Returns:
            Dictionary with pool health metrics
        """
        available_keys = sum(1 for k in self.keys.values() if k.is_available)
        healthy_keys = sum(1 for k in self.keys.values() if k.is_healthy)
        
        total_requests = sum(k.total_requests for k in self.keys.values())
        total_successes = sum(k.successful_requests for k in self.keys.values())
        
        avg_latency = 0.0
        if self.keys:
            latencies = [k.avg_latency_ms for k in self.keys.values() if k.avg_latency_ms > 0]
            if latencies:
                avg_latency = sum(latencies) / len(latencies)
        
        return {
            'total_keys': len(self.keys),
            'available_keys': available_keys,
            'healthy_keys': healthy_keys,
            'total_requests': total_requests,
            'total_successes': total_successes,
            'overall_success_rate': total_successes / total_requests if total_requests > 0 else 1.0,
            'avg_latency_ms': avg_latency
        }
    
    def get_key_status_report(self) -> List[Dict]:
        """
        Get detailed status report for all keys.
        
        Returns:
            List of status dictionaries
        """
        report = []
        
        for key_id, key_status in self.keys.items():
            report.append({
                'key_id': key_id,
                'is_available': key_status.is_available,
                'is_healthy': key_status.is_healthy,
                'total_requests': key_status.total_requests,
                'success_rate': key_status.success_rate,
                'avg_latency_ms': key_status.avg_latency_ms,
                'consecutive_failures': key_status.consecutive_failures,
                'cooldown_until': key_status.cooldown_until.isoformat() if key_status.cooldown_until else None
            })
        
        return report
