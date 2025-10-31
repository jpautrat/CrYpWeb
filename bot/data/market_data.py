"""
Market data aggregator and manager.
Collects and processes real-time market data from WebSocket and REST API.
"""
import pandas as pd
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import deque
from loguru import logger
import threading

from .storage_manager import StorageManager
from .data_validator import DataValidator


class MarketDataManager:
    """Manages real-time market data collection and storage"""
    
    def __init__(self, storage: StorageManager, validator: DataValidator):
        self.storage = storage
        self.validator = validator
        
        # In-memory buffers for real-time data
        self.trades_buffer: Dict[str, deque] = {}
        self.orderbook_buffer: Dict[str, deque] = {}
        self.buffer_max_size = 10000
        
        # Thread safety
        self.lock = threading.Lock()
        
        # Statistics
        self.stats = {
            'trades_received': 0,
            'trades_stored': 0,
            'orderbook_updates': 0,
            'last_update': None
        }
    
    def add_trade(self, pair: str, trade_data: Dict):
        """Add trade to buffer"""
        with self.lock:
            if pair not in self.trades_buffer:
                self.trades_buffer[pair] = deque(maxlen=self.buffer_max_size)
            
            trade_df = pd.DataFrame([{
                'timestamp': pd.to_datetime(trade_data.get('timestamp', datetime.now())),
                'price': trade_data.get('price', 0.0),
                'volume': trade_data.get('volume', 0.0),
                'side': trade_data.get('side', 'unknown')
            }])
            
            self.trades_buffer[pair].append(trade_df)
            self.stats['trades_received'] += 1
            self.stats['last_update'] = datetime.now()
            
            # Periodically flush to disk (every 100 trades or 60 seconds)
            if len(self.trades_buffer[pair]) >= 100:
                self._flush_trades(pair)
    
    def add_orderbook(self, pair: str, book_data: Dict):
        """Add order book snapshot to buffer"""
        with self.lock:
            if pair not in self.orderbook_buffer:
                self.orderbook_buffer[pair] = deque(maxlen=1000)  # Smaller buffer for orderbook
            
            # Extract best bid/ask
            bids = book_data.get('bids', [])
            asks = book_data.get('asks', [])
            
            best_bid = float(bids[0][0]) if bids and len(bids[0]) > 0 else 0.0
            best_ask = float(asks[0][0]) if asks and len(asks[0]) > 0 else 0.0
            
            book_df = pd.DataFrame([{
                'timestamp': pd.to_datetime(book_data.get('timestamp', datetime.now())),
                'best_bid': best_bid,
                'best_ask': best_ask,
                'spread': best_ask - best_bid if best_bid > 0 and best_ask > 0 else 0.0,
                'spread_bps': ((best_ask - best_bid) / ((best_bid + best_ask) / 2) * 10000) 
                              if best_bid > 0 and best_ask > 0 else 0.0
            }])
            
            self.orderbook_buffer[pair].append(book_df)
            self.stats['orderbook_updates'] += 1
    
    def get_recent_trades(self, pair: str, seconds: int = 300) -> pd.DataFrame:
        """Get recent trades for a pair"""
        with self.lock:
            if pair not in self.trades_buffer or len(self.trades_buffer[pair]) == 0:
                return pd.DataFrame()
            
            # Load from buffer
            all_trades = pd.concat(list(self.trades_buffer[pair]), ignore_index=True)
            
            # Also load from storage for longer history
            cutoff = datetime.now() - timedelta(seconds=seconds)
            stored_trades = self.storage.load_trades(pair, cutoff, datetime.now())
            
            # Combine and deduplicate
            if not stored_trades.empty:
                combined = pd.concat([stored_trades, all_trades])
                combined = combined.drop_duplicates(subset=['timestamp'], keep='last')
            else:
                combined = all_trades
            
            # Filter by time window
            combined = combined[combined['timestamp'] >= cutoff]
            combined = combined.sort_values('timestamp')
            
            return combined
    
    def get_recent_orderbook(self, pair: str, seconds: int = 60) -> pd.DataFrame:
        """Get recent order book snapshots"""
        with self.lock:
            if pair not in self.orderbook_buffer or len(self.orderbook_buffer[pair]) == 0:
                return pd.DataFrame()
            
            all_books = pd.concat(list(self.orderbook_buffer[pair]), ignore_index=True)
            
            cutoff = datetime.now() - timedelta(seconds=seconds)
            all_books = all_books[all_books['timestamp'] >= cutoff]
            all_books = all_books.sort_values('timestamp')
            
            return all_books
    
    def _flush_trades(self, pair: str):
        """Flush trades to disk storage"""
        try:
            if pair not in self.trades_buffer or len(self.trades_buffer[pair]) == 0:
                return
            
            trades_df = pd.concat(list(self.trades_buffer[pair]), ignore_index=True)
            
            # Validate before storing
            is_valid, errors = self.validator.validate_trades(trades_df)
            if not is_valid:
                logger.warning(f"Invalid trades for {pair}: {errors}")
                # Still store, but log warning
            
            # Store
            self.storage.save_trades(pair, trades_df, append=True)
            self.stats['trades_stored'] += len(trades_df)
            
            # Clear buffer
            self.trades_buffer[pair].clear()
            
            logger.debug(f"Flushed {len(trades_df)} trades for {pair} to disk")
        
        except Exception as e:
            logger.error(f"Failed to flush trades for {pair}: {e}")
    
    def flush_all(self):
        """Flush all buffers to disk"""
        with self.lock:
            for pair in list(self.trades_buffer.keys()):
                if len(self.trades_buffer[pair]) > 0:
                    self._flush_trades(pair)
    
    def get_statistics(self) -> Dict:
        """Get data collection statistics"""
        return self.stats.copy()
