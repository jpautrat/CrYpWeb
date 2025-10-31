"""
Decision engine that processes signals and makes trading decisions.
"""
from typing import Dict, Optional
import pandas as pd
from datetime import datetime
from loguru import logger

from .signal_generator import SignalGenerator
from ..execution.position_sizer import PositionSizer
from ..execution.risk_manager import RiskManager
from ..config.universe_manager import UniverseManager
from ..core.rest_client import KrakenRESTClient


class DecisionEngine:
    """Makes final trading decisions based on signals and risk checks"""
    
    def __init__(self, signal_generator: SignalGenerator, position_sizer: PositionSizer,
                 risk_manager: RiskManager, universe_manager: UniverseManager,
                 rest_client: KrakenRESTClient):
        self.signal_generator = signal_generator
        self.position_sizer = position_sizer
        self.risk_manager = risk_manager
        self.universe_manager = universe_manager
        self.rest_client = rest_client
    
    def process_signal(self, features: pd.Series, pair: str, timestamp: datetime,
                      market_data: Dict) -> Optional[Dict]:
        """
        Process signal and make trading decision.
        
        Returns:
            Order dictionary or None if no trade
        """
        # Validate pair is eligible
        is_valid, error_msg = self.universe_manager.validate_pair(pair)
        if not is_valid:
            logger.warning(f"Pair {pair} not eligible: {error_msg}")
            return None
        
        # Generate signal
        signal = self.signal_generator.generate_signal(features, pair, timestamp, market_data)
        
        if signal['side'] == 'hold':
            return None
        
        # Get current price and balance
        current_price = market_data.get('price', features.get('price_current', 0.0))
        if current_price <= 0:
            logger.warning(f"Invalid price for {pair}")
            return None
        
        # Get balance
        balance_data = self.rest_client.get_balance()
        if not balance_data:
            logger.error("Failed to get balance")
            return None
        
        # Find quote currency balance (e.g., USD)
        quote_currency = pair[-3:] if len(pair) >= 3 else "USD"
        available_balance = float(balance_data.get(quote_currency, 0))
        
        if available_balance <= 0:
            logger.warning(f"Insufficient balance in {quote_currency}")
            return None
        
        # Calculate position size
        pair_metadata = self.universe_manager.get_pair_metadata(pair)
        position_size_usd = self.position_sizer.calculate_position_size(
            pair=pair,
            expected_return=signal['expected_return'],
            confidence=signal['confidence'],
            current_price=current_price,
            available_balance=available_balance,
            pair_metadata=pair_metadata
        )
        
        if position_size_usd <= 0:
            logger.debug(f"Position size too small for {pair}")
            return None
        
        # Check risk limits
        is_allowed, risk_error = self.risk_manager.check_pre_trade_limits(
            pair=pair,
            order_size_usd=position_size_usd,
            side=signal['side']
        )
        
        if not is_allowed:
            logger.warning(f"Risk check failed for {pair}: {risk_error}")
            return None
        
        # Check position concentration
        if not self.risk_manager.check_position_concentration(pair, position_size_usd):
            logger.warning(f"Position concentration limit would be exceeded for {pair}")
            return None
        
        # Convert to base currency
        base_size = self.position_sizer.calculate_base_currency_size(
            position_size_usd,
            current_price,
            pair_metadata.get('lot_decimals', 8)
        )
        
        if base_size <= 0:
            logger.warning(f"Invalid base size for {pair}")
            return None
        
        # Create order
        order = {
            'pair': pair,
            'side': signal['side'],
            'size': base_size,
            'size_usd': position_size_usd,
            'price': signal.get('limit_price', current_price),
            'order_type': 'limit',
            'post_only': True,
            'confidence': signal['confidence'],
            'expected_return': signal['expected_return'],
            'reason': signal['reason']
        }
        
        return order
