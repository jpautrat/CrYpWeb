"""Position sizing based on Kelly criterion and risk parameters."""
import numpy as np
from typing import Dict
from loguru import logger

from bot.config.settings import settings


class PositionSizer:
    """Calculates position sizes based on risk parameters."""
    
    def calculate_size(self, pair: str, confidence: float, expected_return: float,
                      volatility: float, current_price: float) -> float:
        """
        Calculate position size.
        
        Args:
            pair: Trading pair
            confidence: Model confidence (0-1)
            expected_return: Expected return percentage
            volatility: Current volatility
            current_price: Current price
            
        Returns:
            Position size in USD
        """
        # Base position size from risk parameters
        max_position_pct = settings.trading.get_risk_param("max_position_pct")
        base_size_usd = settings.trading.portfolio_size_usd * (max_position_pct / 100.0)
        
        # Scale by confidence
        if confidence >= 0.90:
            size_multiplier = 1.0
        elif confidence >= 0.80:
            size_multiplier = 0.75
        elif confidence >= 0.70:
            size_multiplier = 0.50
        elif confidence >= 0.65:
            size_multiplier = 0.25
        else:
            return 0.0  # Too low confidence
        
        # Kelly criterion adjustment (conservative)
        if expected_return > 0 and volatility > 0:
            kelly_fraction = expected_return / volatility
            kelly_fraction = min(kelly_fraction, 0.25)  # Cap at 25%
            size_multiplier *= kelly_fraction
        
        size_usd = base_size_usd * size_multiplier
        
        # Round to reasonable precision
        return round(size_usd, 2)
