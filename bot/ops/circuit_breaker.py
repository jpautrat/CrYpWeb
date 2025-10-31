"""
Circuit Breaker - Additional safety mechanisms
"""

from typing import Dict, Optional
from datetime import datetime, timedelta
from loguru import logger


class CircuitBreaker:
    """
    Additional circuit breaker for abnormal market conditions.
    Complements the risk manager's circuit breakers.
    """
    
    def __init__(
        self,
        spread_percentile_threshold: float = 95.0,
        max_latency_ms: float = 500.0,
        volatility_threshold: float = 10.0,
        cooldown_minutes: int = 60
    ):
        """
        Initialize circuit breaker.
        
        Args:
            spread_percentile_threshold: Halt if spread exceeds this percentile
            max_latency_ms: Halt if latency exceeds this
            volatility_threshold: Halt if price moves > this % in 5 minutes
            cooldown_minutes: Cooldown duration after trigger
        """
        self.spread_percentile_threshold = spread_percentile_threshold
        self.max_latency_ms = max_latency_ms
        self.volatility_threshold = volatility_threshold
        self.cooldown_minutes = cooldown_minutes
        
        self.is_triggered = False
        self.trigger_reason = ""
        self.triggered_at: Optional[datetime] = None
        self.trigger_count = 0
        
        logger.info("CircuitBreaker initialized")
    
    def check_spread_protection(
        self,
        pair: str,
        current_spread_pct: float,
        spread_percentile: float
    ) -> bool:
        """
        Check if spread is abnormally wide.
        
        Args:
            pair: Trading pair
            current_spread_pct: Current spread percentage
            spread_percentile: Current spread percentile
            
        Returns:
            True if spread is normal, False if abnormal
        """
        if spread_percentile > self.spread_percentile_threshold:
            self.trigger(
                f"Abnormal spread for {pair}: {spread_percentile:.1f}th percentile "
                f"({current_spread_pct:.3f}%)"
            )
            return False
        
        return True
    
    def check_latency_protection(
        self,
        component: str,
        latency_ms: float
    ) -> bool:
        """
        Check if latency is acceptable.
        
        Args:
            component: Component name
            latency_ms: Measured latency in milliseconds
            
        Returns:
            True if latency is acceptable, False if too high
        """
        if latency_ms > self.max_latency_ms:
            self.trigger(
                f"High latency in {component}: {latency_ms:.1f}ms "
                f"(threshold: {self.max_latency_ms}ms)"
            )
            return False
        
        return True
    
    def check_volatility_protection(
        self,
        pair: str,
        price_change_pct: float
    ) -> bool:
        """
        Check for extreme volatility.
        
        Args:
            pair: Trading pair
            price_change_pct: Price change percentage
            
        Returns:
            True if volatility is normal, False if extreme
        """
        if abs(price_change_pct) > self.volatility_threshold:
            self.trigger(
                f"Extreme volatility in {pair}: {price_change_pct:+.2f}% in 5 minutes"
            )
            return False
        
        return True
    
    def trigger(self, reason: str):
        """
        Trigger the circuit breaker.
        
        Args:
            reason: Reason for trigger
        """
        if not self.is_triggered:
            self.is_triggered = True
            self.trigger_reason = reason
            self.triggered_at = datetime.now()
            self.trigger_count += 1
            
            logger.critical(f"CIRCUIT BREAKER TRIGGERED: {reason}")
    
    def reset(self):
        """Reset the circuit breaker"""
        if self.is_triggered:
            logger.info(f"Circuit breaker reset after: {self.trigger_reason}")
            
            self.is_triggered = False
            self.trigger_reason = ""
            self.triggered_at = None
    
    def check_and_reset(self) -> bool:
        """
        Check if cooldown has expired and reset if so.
        
        Returns:
            True if trading is allowed, False if still in cooldown
        """
        if not self.is_triggered:
            return True
        
        if self.triggered_at:
            cooldown_end = self.triggered_at + timedelta(minutes=self.cooldown_minutes)
            
            if datetime.now() >= cooldown_end:
                self.reset()
                return True
        
        return False
    
    def get_status(self) -> Dict:
        """Get circuit breaker status"""
        remaining_cooldown = 0
        if self.is_triggered and self.triggered_at:
            cooldown_end = self.triggered_at + timedelta(minutes=self.cooldown_minutes)
            remaining_cooldown = max(0, (cooldown_end - datetime.now()).total_seconds() / 60)
        
        return {
            'is_triggered': self.is_triggered,
            'trigger_reason': self.trigger_reason,
            'triggered_at': self.triggered_at.isoformat() if self.triggered_at else None,
            'remaining_cooldown_minutes': remaining_cooldown,
            'trigger_count': self.trigger_count,
            'spread_threshold': self.spread_percentile_threshold,
            'latency_threshold_ms': self.max_latency_ms,
            'volatility_threshold_pct': self.volatility_threshold
        }
