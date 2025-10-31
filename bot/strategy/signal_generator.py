"""
Signal generation coordinator.
Combines multiple strategies and generates final trading signals.
"""
from typing import Dict, List, Optional
import pandas as pd
from datetime import datetime
from loguru import logger

from .base_strategy import StrategyInterface
from .ml_strategy import MLStrategy


class SignalGenerator:
    """Generates trading signals from multiple strategies"""
    
    def __init__(self, strategies: List[StrategyInterface]):
        self.strategies = strategies
        self.primary_strategy: Optional[StrategyInterface] = None
        
        # Set primary strategy (ML strategy if available)
        for strategy in strategies:
            if isinstance(strategy, MLStrategy):
                self.primary_strategy = strategy
                break
        
        if not self.primary_strategy and strategies:
            self.primary_strategy = strategies[0]
    
    def generate_signal(self, features: pd.Series, pair: str, timestamp: datetime,
                       market_data: Dict) -> Dict:
        """
        Generate trading signal from all strategies.
        
        Returns:
            Signal dictionary
        """
        if not self.primary_strategy:
            logger.error("No strategy available")
            return {
                'side': 'hold',
                'confidence': 0.0,
                'reason': 'No strategy available'
            }
        
        try:
            # Generate signal from primary strategy
            signal = self.primary_strategy.signal(features, pair, timestamp)
            
            # Validate signal
            if signal['side'] != 'hold':
                if not self.primary_strategy.should_trade(signal, market_data):
                    signal['side'] = 'hold'
                    signal['reason'] = "Signal validation failed"
            
            return signal
        
        except Exception as e:
            logger.error(f"Error generating signal: {e}")
            return {
                'side': 'hold',
                'confidence': 0.0,
                'reason': f'Error: {str(e)}'
            }
