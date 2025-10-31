"""
Base strategy interface for trading strategies.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any
import pandas as pd
from datetime import datetime


class StrategyInterface(ABC):
    """Base interface for trading strategies"""
    
    @abstractmethod
    def signal(self, features: pd.Series, pair: str, timestamp: datetime) -> Dict[str, Any]:
        """
        Generate trading signal from features.
        
        Args:
            features: Feature vector
            pair: Trading pair symbol
            timestamp: Current timestamp
        
        Returns:
            Dictionary with:
                - side: 'buy'|'sell'|'hold'
                - size: float (USD amount)
                - limit_price: Optional[float]
                - ttl: int (seconds)
                - confidence: float (0.0-1.0)
                - reason: str
                - expected_return: float
                - risk_score: float (0.0-1.0)
        """
        pass
    
    @abstractmethod
    def should_trade(self, signal: Dict[str, Any], market_data: Dict) -> bool:
        """
        Determine if signal should be executed.
        
        Args:
            signal: Signal dictionary from signal()
            market_data: Current market data (price, spread, etc.)
        
        Returns:
            True if should trade, False otherwise
        """
        pass
