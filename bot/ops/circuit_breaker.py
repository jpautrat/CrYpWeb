"""
Circuit breaker system for automatic trading halts.
"""
from typing import Dict, Optional
from datetime import datetime, timedelta
from loguru import logger


class CircuitBreaker:
    """Circuit breaker for trading protection"""
    
    def __init__(self, max_spread_pct: float = 95.0, max_latency_ms: float = 500.0,
                 max_volatility_pct: float = 10.0):
        self.max_spread_pct = max_spread_pct
        self.max_latency_ms = max_latency_ms
        self.max_volatility_pct = max_volatility_pct
        
        self.active = False
        self.triggered_at: Optional[datetime] = None
        self.reason: str = ""
        self.cooldown_minutes = 60
    
    def check_spread(self, spread_bps: float, spread_percentile: float) -> bool:
        """Check if spread triggers circuit breaker"""
        if spread_percentile >= self.max_spread_pct:
            self._trigger(f"Spread percentile {spread_percentile:.1f}% exceeds threshold")
            return False
        return True
    
    def check_latency(self, latency_ms: float) -> bool:
        """Check if latency triggers circuit breaker"""
        if latency_ms > self.max_latency_ms:
            self._trigger(f"Latency {latency_ms:.1f}ms exceeds threshold")
            return False
        return True
    
    def check_volatility(self, price_change_pct: float, time_window_minutes: int = 5) -> bool:
        """Check if volatility triggers circuit breaker"""
        if abs(price_change_pct) > self.max_volatility_pct:
            self._trigger(f"Volatility {price_change_pct:.2f}% in {time_window_minutes}min exceeds threshold")
            return False
        return True
    
    def _trigger(self, reason: str):
        """Trigger circuit breaker"""
        if not self.active:
            self.active = True
            self.triggered_at = datetime.now()
            self.reason = reason
            logger.error(f"Circuit breaker triggered: {reason}")
    
    def is_active(self) -> bool:
        """Check if circuit breaker is active"""
        if self.active and self.triggered_at:
            elapsed = (datetime.now() - self.triggered_at).total_seconds() / 60
            if elapsed >= self.cooldown_minutes:
                self._reset()
        return self.active
    
    def _reset(self):
        """Reset circuit breaker"""
        self.active = False
        self.triggered_at = None
        self.reason = ""
        logger.info("Circuit breaker reset")
    
    def get_status(self) -> Dict:
        """Get circuit breaker status"""
        return {
            'active': self.is_active(),
            'triggered_at': self.triggered_at.isoformat() if self.triggered_at else None,
            'reason': self.reason,
            'cooldown_minutes': self.cooldown_minutes
        }
