"""
Kraken WebSocket manager for real-time market data.
Handles trades, order book updates, and automatic reconnection.
"""
import json
import asyncio
import websocket
import threading
from typing import Dict, List, Callable, Optional
from datetime import datetime
from collections import deque
from loguru import logger

from ..config.settings import APIConfig


class KrakenWebSocketManager:
    """Manages WebSocket connections to Kraken for real-time data"""
    
    def __init__(self, websocket_url: str = "wss://ws.kraken.com"):
        self.websocket_url = websocket_url
        self.ws: Optional[websocket.WebSocketApp] = None
        self.is_connected = False
        self.is_running = False
        self.subscribed_pairs: List[str] = []
        self.callbacks: Dict[str, List[Callable]] = {
            'trade': [],
            'book': [],
            'ticker': [],
            'ohlc': [],
            'heartbeat': [],
            'error': [],
            'open': [],
            'close': []
        }
        self.last_heartbeat: Optional[datetime] = None
        self.heartbeat_timeout = 30  # seconds
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 10
        self.reconnect_delay = 1
        self.message_queue = deque(maxlen=10000)
        self.thread: Optional[threading.Thread] = None
    
    def register_callback(self, event_type: str, callback: Callable):
        """Register callback for WebSocket events"""
        if event_type in self.callbacks:
            self.callbacks[event_type].append(callback)
    
    def _on_message(self, ws, message):
        """Handle incoming WebSocket message"""
        try:
            data = json.loads(message)
            
            # Handle array messages (market data)
            if isinstance(data, list):
                channel_id = data[0]
                channel_name = data[-2] if len(data) > 2 else None
                payload = data[-1] if len(data) > 1 else None
                
                if channel_name == 'trade':
                    self._handle_trade_message(channel_id, payload)
                elif channel_name == 'book':
                    self._handle_book_message(channel_id, payload)
                elif channel_name == 'ticker':
                    self._handle_ticker_message(channel_id, payload)
                elif channel_name == 'ohlc':
                    self._handle_ohlc_message(channel_id, payload)
            
            # Handle object messages (system messages)
            elif isinstance(data, dict):
                if data.get('event') == 'heartbeat':
                    self._handle_heartbeat()
                elif data.get('event') == 'systemStatus':
                    logger.info(f"System status: {data.get('status')}")
                elif data.get('event') == 'subscriptionStatus':
                    self._handle_subscription_status(data)
                elif data.get('event') == 'error':
                    self._handle_error(data)
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse WebSocket message: {e}")
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}")
    
    def _handle_trade_message(self, channel_id: int, payload: List):
        """Handle trade message"""
        if isinstance(payload, list) and len(payload) > 0:
            # Payload is array of trades: [price, volume, time, side, order_type, misc]
            for trade in payload:
                if isinstance(trade, list) and len(trade) >= 3:
                    trade_data = {
                        'channel_id': channel_id,
                        'price': float(trade[0]),
                        'volume': float(trade[1]),
                        'timestamp': float(trade[2]),
                        'side': trade[3] if len(trade) > 3 else None,
                        'order_type': trade[4] if len(trade) > 4 else None,
                        'misc': trade[5] if len(trade) > 5 else None,
                        'received_at': datetime.now()
                    }
                    self.message_queue.append(('trade', trade_data))
                    
                    for callback in self.callbacks['trade']:
                        try:
                            callback(trade_data)
                        except Exception as e:
                            logger.error(f"Trade callback error: {e}")
    
    def _handle_book_message(self, channel_id: int, payload: Dict):
        """Handle order book update message"""
        if isinstance(payload, dict):
            book_data = {
                'channel_id': channel_id,
                'asks': payload.get('as', payload.get('a', [])),  # Snapshot or update
                'bids': payload.get('bs', payload.get('b', [])),  # Snapshot or update
                'timestamp': datetime.now()
            }
            self.message_queue.append(('book', book_data))
            
            for callback in self.callbacks['book']:
                try:
                    callback(book_data)
                except Exception as e:
                    logger.error(f"Book callback error: {e}")
    
    def _handle_ticker_message(self, channel_id: int, payload: Dict):
        """Handle ticker message"""
        ticker_data = {
            'channel_id': channel_id,
            'data': payload,
            'timestamp': datetime.now()
        }
        self.message_queue.append(('ticker', ticker_data))
        
        for callback in self.callbacks['ticker']:
            try:
                callback(ticker_data)
            except Exception as e:
                logger.error(f"Ticker callback error: {e}")
    
    def _handle_ohlc_message(self, channel_id: int, payload: List):
        """Handle OHLC message"""
        ohlc_data = {
            'channel_id': channel_id,
            'data': payload,
            'timestamp': datetime.now()
        }
        self.message_queue.append(('ohlc', ohlc_data))
        
        for callback in self.callbacks['ohlc']:
            try:
                callback(ohlc_data)
            except Exception as e:
                logger.error(f"OHLC callback error: {e}")
    
    def _handle_heartbeat(self):
        """Handle heartbeat message"""
        self.last_heartbeat = datetime.now()
        for callback in self.callbacks['heartbeat']:
            try:
                callback()
            except Exception as e:
                logger.error(f"Heartbeat callback error: {e}")
    
    def _handle_subscription_status(self, data: Dict):
        """Handle subscription status message"""
        status = data.get('status')
        pair = data.get('pair', 'unknown')
        
        if status == 'subscribed':
            logger.info(f"Subscribed to {pair}")
            if pair not in self.subscribed_pairs:
                self.subscribed_pairs.append(pair)
        elif status == 'error':
            error_msg = data.get('errorMessage', 'Unknown error')
            logger.error(f"Subscription error for {pair}: {error_msg}")
            for callback in self.callbacks['error']:
                try:
                    callback({'pair': pair, 'error': error_msg})
                except Exception as e:
                    logger.error(f"Error callback error: {e}")
    
    def _handle_error(self, data: Dict):
        """Handle error message"""
        error_msg = data.get('errorMessage', 'Unknown error')
        logger.error(f"WebSocket error: {error_msg}")
        for callback in self.callbacks['error']:
            try:
                callback({'error': error_msg})
            except Exception as e:
                logger.error(f"Error callback error: {e}")
    
    def _on_open(self, ws):
        """Handle WebSocket open"""
        logger.info("WebSocket connection opened")
        self.is_connected = True
        self.reconnect_attempts = 0
        self.last_heartbeat = datetime.now()
        
        for callback in self.callbacks['open']:
            try:
                callback()
            except Exception as e:
                logger.error(f"Open callback error: {e}")
        
        # Re-subscribe to all pairs
        if self.subscribed_pairs:
            self.subscribe_multiple(self.subscribed_pairs)
    
    def _on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket close"""
        logger.warning(f"WebSocket connection closed: {close_status_code}")
        self.is_connected = False
        
        for callback in self.callbacks['close']:
            try:
                callback(close_status_code)
            except Exception as e:
                logger.error(f"Close callback error: {e}")
        
        # Attempt reconnection
        if self.is_running:
            self._attempt_reconnect()
    
    def _on_error(self, ws, error):
        """Handle WebSocket error"""
        logger.error(f"WebSocket error: {error}")
        for callback in self.callbacks['error']:
            try:
                callback({'error': str(error)})
            except Exception as e:
                logger.error(f"Error callback error: {e}")
    
    def _attempt_reconnect(self):
        """Attempt to reconnect WebSocket"""
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            logger.error("Max reconnection attempts reached")
            return
        
        self.reconnect_attempts += 1
        delay = min(self.reconnect_delay * (2 ** (self.reconnect_attempts - 1)), 60)
        logger.info(f"Reconnecting in {delay} seconds (attempt {self.reconnect_attempts})...")
        
        import time
        time.sleep(delay)
        
        if self.is_running:
            self.connect()
    
    def connect(self):
        """Connect to WebSocket"""
        try:
            self.ws = websocket.WebSocketApp(
                self.websocket_url,
                on_message=self._on_message,
                on_open=self._on_open,
                on_close=self._on_close,
                on_error=self._on_error
            )
            
            # Run in separate thread
            def run_ws():
                self.ws.run_forever()
            
            self.thread = threading.Thread(target=run_ws, daemon=True)
            self.thread.start()
            
        except Exception as e:
            logger.error(f"Failed to connect WebSocket: {e}")
            if self.is_running:
                self._attempt_reconnect()
    
    def subscribe_trades(self, pair: str):
        """Subscribe to trade data for a pair"""
        if not self.is_connected:
            logger.error("WebSocket not connected")
            return False
        
        subscription = {
            "event": "subscribe",
            "pair": [pair],
            "subscription": {"name": "trade"}
        }
        
        try:
            self.ws.send(json.dumps(subscription))
            logger.info(f"Subscribed to trades for {pair}")
            return True
        except Exception as e:
            logger.error(f"Failed to subscribe to {pair}: {e}")
            return False
    
    def subscribe_book(self, pair: str, depth: int = 10):
        """Subscribe to order book data for a pair"""
        if not self.is_connected:
            logger.error("WebSocket not connected")
            return False
        
        subscription = {
            "event": "subscribe",
            "pair": [pair],
            "subscription": {
                "name": "book",
                "depth": depth
            }
        }
        
        try:
            self.ws.send(json.dumps(subscription))
            logger.info(f"Subscribed to order book for {pair}")
            return True
        except Exception as e:
            logger.error(f"Failed to subscribe to book for {pair}: {e}")
            return False
    
    def subscribe_ticker(self, pair: str):
        """Subscribe to ticker data for a pair"""
        if not self.is_connected:
            logger.error("WebSocket not connected")
            return False
        
        subscription = {
            "event": "subscribe",
            "pair": [pair],
            "subscription": {"name": "ticker"}
        }
        
        try:
            self.ws.send(json.dumps(subscription))
            logger.info(f"Subscribed to ticker for {pair}")
            return True
        except Exception as e:
            logger.error(f"Failed to subscribe to ticker for {pair}: {e}")
            return False
    
    def subscribe_multiple(self, pairs: List[str], subscriptions: List[str] = ['trade', 'book']):
        """Subscribe to multiple pairs with multiple subscription types"""
        for pair in pairs:
            if 'trade' in subscriptions:
                self.subscribe_trades(pair)
            if 'book' in subscriptions:
                self.subscribe_book(pair)
            if 'ticker' in subscriptions:
                self.subscribe_ticker(pair)
    
    def start(self):
        """Start WebSocket manager"""
        self.is_running = True
        self.connect()
        logger.info("WebSocket manager started")
    
    def stop(self):
        """Stop WebSocket manager"""
        self.is_running = False
        if self.ws:
            self.ws.close()
        logger.info("WebSocket manager stopped")
    
    def check_heartbeat(self) -> bool:
        """Check if heartbeat is within timeout"""
        if self.last_heartbeat is None:
            return False
        
        elapsed = (datetime.now() - self.last_heartbeat).total_seconds()
        if elapsed > self.heartbeat_timeout:
            logger.warning(f"Heartbeat timeout: {elapsed:.1f}s since last heartbeat")
            return False
        
        return True
    
    def get_message_queue(self) -> deque:
        """Get message queue (for testing/monitoring)"""
        return self.message_queue
