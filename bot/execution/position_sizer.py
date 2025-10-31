"""
Position Sizer - Determines optimal position sizes for trades
Implements Kelly criterion and risk-adjusted sizing.
"""

import numpy as np
from typing import Dict, Optional
from loguru import logger


class PositionSizer:
    """
    Calculates position sizes based on confidence, risk parameters, and capital.
    Critical for small capital accounts to maximize efficiency while preserving capital.
    """
    
    def __init__(
        self,
        portfolio_size_usd: float,
        max_position_pct: float = 3.0,
        max_daily_volume_pct: float = 15.0,
        max_concurrent_positions: int = 5
    ):
        """
        Initialize position sizer.
        
        Args:
            portfolio_size_usd: Total portfolio value in USD
            max_position_pct: Maximum % per single position
            max_daily_volume_pct: Maximum % traded per day
            max_concurrent_positions: Maximum open positions
        """
        self.portfolio_size_usd = portfolio_size_usd
        self.max_position_pct = max_position_pct
        self.max_daily_volume_pct = max_daily_volume_pct
        self.max_concurrent_positions = max_concurrent_positions
        
        self.daily_volume_used = 0.0
        self.current_positions: Dict[str, float] = {}
        
        logger.info(
            f"PositionSizer initialized: portfolio=${portfolio_size_usd:.2f}, "
            f"max_position={max_position_pct}%, max_daily={max_daily_volume_pct}%"
        )
    
    def calculate_position_size(
        self,
        pair: str,
        confidence: float,
        price: float,
        min_order_size: float,
        available_balance: float,
        risk_multiplier: float = 1.0
    ) -> Optional[Dict]:
        """
        Calculate optimal position size for a trade.
        
        Args:
            pair: Trading pair
            confidence: Model confidence (0-1)
            price: Current price
            min_order_size: Minimum order size for pair
            available_balance: Available USD balance
            risk_multiplier: Additional risk adjustment (0-1)
            
        Returns:
            Dictionary with position sizing details or None if trade not viable
        """
        # Base position size from portfolio percentage
        base_position_usd = self.portfolio_size_usd * (self.max_position_pct / 100)
        
        # Adjust based on confidence
        confidence_multiplier = self._confidence_to_multiplier(confidence)
        adjusted_position_usd = base_position_usd * confidence_multiplier * risk_multiplier
        
        # Check daily volume limit
        daily_limit_usd = self.portfolio_size_usd * (self.max_daily_volume_pct / 100)
        remaining_daily_capacity = daily_limit_usd - self.daily_volume_used
        
        if adjusted_position_usd > remaining_daily_capacity:
            logger.warning(
                f"Position size ${adjusted_position_usd:.2f} exceeds daily capacity "
                f"${remaining_daily_capacity:.2f}"
            )
            adjusted_position_usd = remaining_daily_capacity
        
        # Check available balance
        if adjusted_position_usd > available_balance:
            logger.warning(
                f"Position size ${adjusted_position_usd:.2f} exceeds available "
                f"balance ${available_balance:.2f}"
            )
            adjusted_position_usd = available_balance
        
        # Calculate volume in base currency
        volume = adjusted_position_usd / price
        
        # Check minimum order size
        if volume < min_order_size:
            logger.info(
                f"Position volume {volume:.8f} below minimum {min_order_size:.8f} for {pair}"
            )
            return None
        
        # Check concurrent position limit
        if len(self.current_positions) >= self.max_concurrent_positions:
            if pair not in self.current_positions:
                logger.warning(
                    f"Maximum concurrent positions ({self.max_concurrent_positions}) reached"
                )
                return None
        
        return {
            'pair': pair,
            'size_usd': adjusted_position_usd,
            'volume': volume,
            'price': price,
            'confidence': confidence,
            'confidence_multiplier': confidence_multiplier,
            'risk_multiplier': risk_multiplier
        }
    
    def _confidence_to_multiplier(self, confidence: float) -> float:
        """
        Convert confidence to position size multiplier.
        
        Args:
            confidence: Model confidence (0-1)
            
        Returns:
            Size multiplier (0-1)
        """
        if confidence >= 0.90:
            return 1.0
        elif confidence >= 0.80:
            return 0.75
        elif confidence >= 0.70:
            return 0.50
        elif confidence >= 0.65:
            return 0.25
        else:
            return 0.0
    
    def record_trade(self, pair: str, size_usd: float, side: str):
        """
        Record a trade for tracking.
        
        Args:
            pair: Trading pair
            size_usd: Trade size in USD
            side: 'buy' or 'sell'
        """
        # Update daily volume
        self.daily_volume_used += size_usd
        
        # Update positions
        if side == 'buy':
            self.current_positions[pair] = self.current_positions.get(pair, 0) + size_usd
        elif side == 'sell':
            current_pos = self.current_positions.get(pair, 0)
            self.current_positions[pair] = max(0, current_pos - size_usd)
            
            # Remove if position closed
            if self.current_positions[pair] == 0:
                del self.current_positions[pair]
        
        logger.debug(
            f"Trade recorded: {side} ${size_usd:.2f} {pair} | "
            f"Daily: ${self.daily_volume_used:.2f} | Positions: {len(self.current_positions)}"
        )
    
    def reset_daily_limits(self):
        """Reset daily volume counter (call at start of new trading day)"""
        logger.info(f"Resetting daily limits. Previous volume: ${self.daily_volume_used:.2f}")
        self.daily_volume_used = 0.0
    
    def get_position_info(self, pair: str) -> Optional[float]:
        """Get current position size for a pair"""
        return self.current_positions.get(pair)
    
    def get_available_capacity(self) -> Dict:
        """Get available capacity metrics"""
        daily_limit = self.portfolio_size_usd * (self.max_daily_volume_pct / 100)
        remaining_daily = daily_limit - self.daily_volume_used
        
        return {
            'daily_limit_usd': daily_limit,
            'daily_used_usd': self.daily_volume_used,
            'daily_remaining_usd': remaining_daily,
            'daily_used_pct': (self.daily_volume_used / daily_limit * 100) if daily_limit > 0 else 0,
            'open_positions': len(self.current_positions),
            'max_positions': self.max_concurrent_positions,
            'can_open_new': len(self.current_positions) < self.max_concurrent_positions
        }
