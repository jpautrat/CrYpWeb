"""
Base Strategy Interface
Defines the contract for all trading strategies.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import pandas as pd
from datetime import datetime


class StrategyInterface(ABC):
    """
    Abstract base class for trading strategies.
    All strategies must implement the signal() method.
    """
    
    @abstractmethod
    def signal(
        self,
        features: pd.Series,
        pair: str,
        timestamp: datetime
    ) -> Dict[str, Any]:
        """
        Generate trading signal from features.
        
        Args:
            features: Feature series for current timestamp
            pair: Trading pair
            timestamp: Current timestamp
            
        Returns:
            Dictionary with signal information:
            {
                'side': 'buy'|'sell'|'hold',
                'size': float,  # USD amount
                'limit_price': Optional[float],
                'ttl': int,  # seconds
                'confidence': float,  # 0.0-1.0
                'reason': str,  # human-readable explanation
                'expected_return': float,  # after all costs
                'risk_score': float  # 0.0-1.0
            }
        """
        pass
    
    @abstractmethod
    def update_model(self, pair: str):
        """
        Update/retrain model for a pair.
        
        Args:
            pair: Trading pair
        """
        pass
    
    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """
        Get strategy status and metrics.
        
        Returns:
            Dictionary with strategy state
        """
        pass
