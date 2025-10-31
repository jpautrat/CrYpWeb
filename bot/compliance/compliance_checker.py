"""
Compliance checking system.
Validates orders and trading decisions against regulatory requirements.
"""
from typing import Dict, Optional, Tuple
from datetime import datetime
from loguru import logger

from bot.compliance.asset_filter import AssetFilter
from bot.config.settings import settings


class ComplianceChecker:
    """Validates trading operations for compliance."""
    
    def __init__(self, asset_filter: AssetFilter):
        """
        Initialize compliance checker.
        
        Args:
            asset_filter: Asset filter instance
        """
        self.asset_filter = asset_filter
    
    def check_order(self, pair: str, order_size: float, order_type: str) -> Tuple[bool, str]:
        """
        Check if an order complies with regulations.
        
        Args:
            pair: Trading pair
            order_size: Order size in quote currency
            order_type: Order type (market, limit, etc.)
            
        Returns:
            Tuple of (is_compliant, error_message)
        """
        # Check asset restriction
        is_valid, error = self.asset_filter.validate_order(pair)
        if not is_valid:
            return False, error
        
        # Additional compliance checks can be added here
        # (e.g., position limits, trading hours, etc.)
        
        return True, ""
    
    def check_trading_allowed(self) -> Tuple[bool, str]:
        """
        Check if trading is currently allowed.
        
        Returns:
            Tuple of (is_allowed, reason)
        """
        # Check if live trading is enabled
        if not settings.trading.live_trading:
            return False, "Live trading is disabled"
        
        return True, ""
