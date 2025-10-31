"""
Threshold definitions for trading system.
"""
from dataclasses import dataclass
from typing import Dict


@dataclass
class TradingThresholds:
    """Thresholds for trading decisions."""
    # Spread thresholds
    max_spread_percentile: float = 0.95  # Halt if spread >95th percentile
    
    # Latency thresholds
    max_api_latency_ms: float = 500.0  # Circuit breaker if exceeded
    
    # Volatility thresholds
    max_volatility_move_pct: float = 10.0  # 10% in 5 minutes
    
    # Order book thresholds
    min_order_book_depth_bps: float = 10.0  # Minimum 0.1% depth
    
    # Model confidence thresholds
    confidence_levels: Dict[str, float] = None
    
    def __post_init__(self):
        """Initialize confidence levels."""
        if self.confidence_levels is None:
            self.confidence_levels = {
                "very_high": 0.90,  # 90%+ -> max position
                "high": 0.80,       # 80-90% -> 75% position
                "medium": 0.70,     # 70-80% -> 50% position
                "low": 0.65,        # 65-70% -> 25% position (conservative only)
            } Predicting next file...
