"""
Market data aggregation and management.
Handles real-time data from WebSocket and REST API.
"""
import pandas as pd
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from collections import deque
from loguru import logger


class MarketDataManager:
    """Manages real-time market data."""
    
    def __init__(self, lookback_seconds: int = 300):
        """
        Initialize market data manager.
        
        Args:
            lookback_seconds: Lookback window for data retention
        """
        self.lookback_seconds = lookback_seconds
        self.trades: Dict[str, deque] = {}  # pair -> deque of trades
        self.orderbooks: Dict[str, Dict] = {}  # pair -> latest orderbook
        self.last_update: Dict[str, datetime] = {}
    
    def add_trade(self, pair: str, price: float, volume: float, side: str, timestamp: datetime):
        """Add a trade to the data buffer."""
        if pair not in self.trades:
            self.trades[pair] = deque(maxlen=10000)
        
        self.trades[pair].append({
            'timestamp': timestamp,
            'price': price,
            'volume': volume,
            'side': side,
        })
        self.last_update[pair] = timestamp
    
    def update_orderbook(self, pair: str, orderbook: Dict):
        """Update order book snapshot."""
        self.orderbooks[pair] = orderbook
        self.last_update[pair] = datetime.utcnow()
    
    def get_trades_dataframe(self, pair: str, seconds: Optional[int] = None) -> pd.DataFrame:
        """
        Get trades as DataFrame for a time window.
        
        Args:
            pair: Trading pair
            seconds: Number of seconds to look back (default: lookback_seconds)
            
        Returns:
            DataFrame with trades
        """
        if pair not in self.trades or not self.trades[pair]:
            return pd.DataFrame(columns=['timestamp', 'price', 'volume', 'side'])
        
        window = seconds or self.lookback_seconds
        cutoff = datetime.utcnow() - timedelta(seconds=window)
        
        trades_list = [
            t for t in self.trades[pair]
            if t['timestamp'] >= cutoff
        ]
        
        if not trades_list:
            return pd.DataFrame(columns=['timestamp', 'price', 'volume', 'side'])
        
        return pd.DataFrame(trades_list)
    
    def get_orderbook(self, pair: str) -> Optional[Dict]:
        """Get latest order book for a pair."""
        return self.orderbooks.get(pair)
    
    def get_latest_price(self, pair: str) -> Optional[float]:
        """Get latest trade price for a pair."""
        if pair in self.trades and self.trades[pair]:
            return self.trades[pair][-1]['price']
        return None
