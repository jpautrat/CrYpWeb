"""
Position sizing logic based on Kelly criterion and risk parameters.
Optimizes trade sizes for small capital accounts.
"""
import numpy as np
from typing import Dict, Optional
from loguru import logger

from ..config.settings import TradingConfig


class PositionSizer:
    """Calculates optimal position sizes based on risk management rules"""
    
    def __init__(self, config: TradingConfig):
        self.config = config
        self.portfolio_size = config.portfolio_size_usd
        self.max_position_pct = config.max_position_pct
    
    def calculate_position_size(self, pair: str, expected_return: float, confidence: float,
                               current_price: float, available_balance: float,
                               pair_metadata: Optional[Dict] = None) -> float:
        """
        Calculate optimal position size in USD.
        
        Args:
            pair: Trading pair
            expected_return: Expected return (as decimal, e.g., 0.01 for 1%)
            confidence: Model confidence (0-1)
            current_price: Current market price
            available_balance: Available balance in quote currency
            pair_metadata: Pair-specific metadata (ordermin, etc.)
        
        Returns:
            Position size in USD
        """
        # Base position size from risk rules
        max_position_usd = (self.portfolio_size * self.max_position_pct) / 100.0
        
        # Adjust for confidence
        confidence_multiplier = confidence  # Use confidence directly as multiplier
        adjusted_size = max_position_usd * confidence_multiplier
        
        # Kelly criterion adjustment (conservative)
        if expected_return > 0:
            # Simplified Kelly: f = (p * b - q) / b
            # where p = win probability (use confidence), b = odds, q = loss probability
            win_prob = confidence
            loss_prob = 1 - win_prob
            odds = expected_return / abs(expected_return) if expected_return != 0 else 1.0
            
            kelly_fraction = (win_prob * odds - loss_prob) / odds if odds > 0 else 0.0
            
            # Apply fractional Kelly (25% for safety)
            kelly_size = max_position_usd * kelly_fraction * 0.25
            adjusted_size = min(adjusted_size, kelly_size)
        
        # Ensure we don't exceed available balance
        adjusted_size = min(adjusted_size, available_balance * 0.95)  # Leave 5% buffer
        
        # Check minimum order size
        if pair_metadata:
            ordermin_base = pair_metadata.get('ordermin', 0)
            if ordermin_base > 0:
                min_order_usd = ordermin_base * current_price
                if adjusted_size < min_order_usd:
                    logger.warning(f"Calculated size {adjusted_size:.2f} below minimum {min_order_usd:.2f}")
                    # Still return it, let order manager handle rejection
                    return 0.0  # Don't trade if below minimum
        
        return max(0.0, adjusted_size)
    
    def calculate_base_currency_size(self, usd_size: float, current_price: float,
                                     pair_decimals: int = 8) -> float:
        """
        Convert USD size to base currency size.
        
        Args:
            usd_size: Size in USD
            current_price: Current price
            pair_decimals: Decimal places for pair
        
        Returns:
            Size in base currency, rounded appropriately
        """
        base_size = usd_size / current_price if current_price > 0 else 0.0
        return round(base_size, pair_decimals)
    
    def apply_anti_gaming_randomization(self, base_size: float, variance_pct: float = 5.0) -> float:
        """
        Apply small randomization to order sizes to avoid gaming.
        
        Args:
            base_size: Base size
            variance_pct: Variance percentage (e.g., 5 for ±5%)
        
        Returns:
            Randomized size
        """
        variance = base_size * (variance_pct / 100.0)
        randomized = base_size + np.random.uniform(-variance, variance)
        return max(0.0, randomized)
