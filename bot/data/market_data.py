"""
Market Data Manager - Real-time data aggregation and preprocessing
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import deque
from loguru import logger
from .storage_manager import StorageManager


class MarketDataManager:
    """
    Manages real-time market data streams.
    Aggregates ticks, maintains order book, and provides data for feature computation.
    """
    
    def __init__(
        self,
        storage_manager: StorageManager,
        buffer_size: int = 10000
    ):
        """
        Initialize market data manager.
        
        Args:
            storage_manager: Storage manager for persistence
            buffer_size: Number of recent data points to keep in memory
        """
        self.storage = storage_manager
        self.buffer_size = buffer_size
        
        # In-memory buffers for each pair
        self.tick_buffers: Dict[str, deque] = {}
        self.orderbook_buffers: Dict[str, deque] = {}
        self.last_prices: Dict[str, float] = {}
        self.vwap_cache: Dict[str, Dict] = {}
        
        logger.info("MarketDataManager initialized")
    
    def add_tick(
        self,
        pair: str,
        timestamp: datetime,
        price: float,
        volume: float,
        side: str
    ):
        """
        Add a new tick to the buffer.
        
        Args:
            pair: Trading pair
            timestamp: Tick timestamp
            price: Trade price
            volume: Trade volume
            side: 'buy' or 'sell'
        """
        if pair not in self.tick_buffers:
            self.tick_buffers[pair] = deque(maxlen=self.buffer_size)
        
        tick = {
            'timestamp': timestamp,
            'price': price,
            'volume': volume,
            'side': side
        }
        
        self.tick_buffers[pair].append(tick)
        self.last_prices[pair] = price
    
    def add_orderbook_snapshot(
        self,
        pair: str,
        timestamp: datetime,
        bids: List[tuple],
        asks: List[tuple]
    ):
        """
        Add order book snapshot.
        
        Args:
            pair: Trading pair
            timestamp: Snapshot timestamp
            bids: List of (price, volume) tuples
            asks: List of (price, volume) tuples
        """
        if pair not in self.orderbook_buffers:
            self.orderbook_buffers[pair] = deque(maxlen=1000)
        
        snapshot = {
            'timestamp': timestamp,
            'bids': bids,
            'asks': asks,
            'bid_price': bids[0][0] if bids else 0,
            'ask_price': asks[0][0] if asks else 0,
            'mid_price': (bids[0][0] + asks[0][0]) / 2 if bids and asks else 0,
            'spread': asks[0][0] - bids[0][0] if bids and asks else 0
        }
        
        self.orderbook_buffers[pair].append(snapshot)
    
    def get_recent_ticks(
        self,
        pair: str,
        seconds: int = 60
    ) -> pd.DataFrame:
        """
        Get recent ticks for a pair.
        
        Args:
            pair: Trading pair
            seconds: Number of seconds to look back
            
        Returns:
            DataFrame of recent ticks
        """
        if pair not in self.tick_buffers or not self.tick_buffers[pair]:
            return pd.DataFrame()
        
        cutoff = datetime.now() - timedelta(seconds=seconds)
        
        recent_ticks = [
            tick for tick in self.tick_buffers[pair]
            if tick['timestamp'] > cutoff
        ]
        
        if not recent_ticks:
            return pd.DataFrame()
        
        return pd.DataFrame(recent_ticks)
    
    def get_recent_orderbook(
        self,
        pair: str,
        count: int = 100
    ) -> pd.DataFrame:
        """
        Get recent order book snapshots.
        
        Args:
            pair: Trading pair
            count: Number of snapshots to return
            
        Returns:
            DataFrame of recent order book data
        """
        if pair not in self.orderbook_buffers or not self.orderbook_buffers[pair]:
            return pd.DataFrame()
        
        recent = list(self.orderbook_buffers[pair])[-count:]
        
        # Extract key metrics
        data = []
        for snapshot in recent:
            data.append({
                'timestamp': snapshot['timestamp'],
                'bid_price': snapshot['bid_price'],
                'ask_price': snapshot['ask_price'],
                'mid_price': snapshot['mid_price'],
                'spread': snapshot['spread']
            })
        
        return pd.DataFrame(data)
    
    def get_ohlcv(
        self,
        pair: str,
        seconds: int = 60,
        interval: str = '1s'
    ) -> pd.DataFrame:
        """
        Compute OHLCV bars from tick data.
        
        Args:
            pair: Trading pair
            seconds: Number of seconds to look back
            interval: Bar interval (e.g., '1s', '5s', '15s', '1m')
            
        Returns:
            DataFrame with OHLCV data
        """
        ticks = self.get_recent_ticks(pair, seconds)
        
        if ticks.empty:
            return pd.DataFrame()
        
        ticks['timestamp'] = pd.to_datetime(ticks['timestamp'])
        ticks = ticks.set_index('timestamp')
        
        # Resample to interval
        ohlc = ticks['price'].resample(interval).ohlc()
        volume = ticks['volume'].resample(interval).sum()
        
        ohlcv = pd.concat([ohlc, volume], axis=1)
        ohlcv.columns = ['open', 'high', 'low', 'close', 'volume']
        
        return ohlcv.dropna()
    
    def compute_vwap(
        self,
        pair: str,
        seconds: int = 300
    ) -> Optional[float]:
        """
        Compute Volume-Weighted Average Price.
        
        Args:
            pair: Trading pair
            seconds: Lookback period in seconds
            
        Returns:
            VWAP or None if insufficient data
        """
        ticks = self.get_recent_ticks(pair, seconds)
        
        if ticks.empty:
            return None
        
        total_volume = ticks['volume'].sum()
        
        if total_volume == 0:
            return None
        
        vwap = (ticks['price'] * ticks['volume']).sum() / total_volume
        
        # Cache result
        if pair not in self.vwap_cache:
            self.vwap_cache[pair] = {}
        self.vwap_cache[pair][seconds] = {
            'vwap': vwap,
            'timestamp': datetime.now()
        }
        
        return vwap
    
    def get_current_spread(self, pair: str) -> Optional[Dict]:
        """
        Get current bid-ask spread.
        
        Args:
            pair: Trading pair
            
        Returns:
            Dictionary with spread data
        """
        if pair not in self.orderbook_buffers or not self.orderbook_buffers[pair]:
            return None
        
        latest = self.orderbook_buffers[pair][-1]
        
        return {
            'bid': latest['bid_price'],
            'ask': latest['ask_price'],
            'mid': latest['mid_price'],
            'spread_abs': latest['spread'],
            'spread_pct': (latest['spread'] / latest['mid_price'] * 100) if latest['mid_price'] > 0 else 0
        }
    
    def get_orderbook_depth(
        self,
        pair: str,
        levels: int = 5
    ) -> Optional[Dict]:
        """
        Get order book depth at multiple levels.
        
        Args:
            pair: Trading pair
            levels: Number of price levels to analyze
            
        Returns:
            Dictionary with depth metrics
        """
        if pair not in self.orderbook_buffers or not self.orderbook_buffers[pair]:
            return None
        
        latest = self.orderbook_buffers[pair][-1]
        bids = latest['bids'][:levels]
        asks = latest['asks'][:levels]
        
        bid_volume = sum(b[1] for b in bids)
        ask_volume = sum(a[1] for a in asks)
        
        imbalance = (bid_volume - ask_volume) / (bid_volume + ask_volume) if (bid_volume + ask_volume) > 0 else 0
        
        return {
            'bid_volume': bid_volume,
            'ask_volume': ask_volume,
            'total_volume': bid_volume + ask_volume,
            'imbalance': imbalance,
            'levels': levels
        }
    
    def persist_buffers(self):
        """Persist buffered data to storage"""
        for pair, buffer in self.tick_buffers.items():
            if not buffer:
                continue
            
            df = pd.DataFrame(list(buffer))
            self.storage.store_tick_data(pair, df)
        
        for pair, buffer in self.orderbook_buffers.items():
            if not buffer:
                continue
            
            # Convert orderbook snapshots to DataFrame
            data = []
            for snapshot in buffer:
                data.append({
                    'timestamp': snapshot['timestamp'],
                    'bid_price': snapshot['bid_price'],
                    'ask_price': snapshot['ask_price'],
                    'mid_price': snapshot['mid_price'],
                    'spread': snapshot['spread']
                })
            
            df = pd.DataFrame(data)
            self.storage.store_orderbook_data(pair, df)
        
        logger.info("Market data buffers persisted to storage")
    
    def get_market_summary(self, pair: str) -> Optional[Dict]:
        """
        Get comprehensive market summary for a pair.
        
        Args:
            pair: Trading pair
            
        Returns:
            Dictionary with market metrics
        """
        ticks_1m = self.get_recent_ticks(pair, 60)
        ticks_5m = self.get_recent_ticks(pair, 300)
        
        if ticks_1m.empty and ticks_5m.empty:
            return None
        
        spread_data = self.get_current_spread(pair)
        vwap_5m = self.compute_vwap(pair, 300)
        
        summary = {
            'pair': pair,
            'last_price': self.last_prices.get(pair, 0),
            'ticks_1m': len(ticks_1m),
            'ticks_5m': len(ticks_5m),
            'vwap_5m': vwap_5m,
            'spread': spread_data,
            'timestamp': datetime.now()
        }
        
        if not ticks_1m.empty:
            summary['volume_1m'] = ticks_1m['volume'].sum()
            summary['price_change_1m_pct'] = (
                (ticks_1m['price'].iloc[-1] - ticks_1m['price'].iloc[0]) /
                ticks_1m['price'].iloc[0] * 100
            ) if len(ticks_1m) > 1 else 0
        
        return summary
