"""
WebSocket manager for real-time Kraken market data.
Handles trades, order book updates, and reconnection logic.
"""
import json
import time
import threading
from typing import Dict, Callable, Optional, List
from datetime import datetime
import websocket
from loguru import logger

from bot.config.settings import settings


class KrakenWebSocketManager:
    """Manages WebSocket connections to Kraken."""
    
    WS_URL = "wss://ws.kraken.com"
    HEARTBEAT_TIMEOUT = settings.performance.websocket_timeout_seconds
    
    def __init__(self):
        """Initialize WebSocket manager."""
        self.ws: Optional[websocket.WebSocketApp] = None
        self.subscriptions: Dict[str, List[str]] = {}  # pair -> [channels]
        self.callbacks: Dict[str, Callable] = {}  # channel -> callback
        self.connected = False
        self.last_heartbeat: Optional[datetime] = None
        self.reconnect_delay = 1.0
        self.max_reconnect_delay = 60.0
        self.stop_event = threading.Event()
        self.ws_thread: Optional[threading.Thread] = None
        self.lock = threading.Lock()
        
    def subscribe(self, pair: str, channels: List[str], callback: Callable):
        """
        Subscribe to market data channels.
        
        Args:
            pair: Trading pair (e.g., 'BTC/USD')
            channels: List of channels (e.g., ['trades', 'book'])
            callback: Callback function for data
        """
        with self.lock:
            # Convert pair to Kraken format
            kraken_pair = self._format_pair(pair)
            
            if kraken_pair not in self.subscriptions:
                self.subscriptions[kraken_pair] = []
            
            for channel in channels:
                if channel not in self.subscriptions[kraken_pair]:
                    self.subscriptions[kraken_pair].append(channel)
                
                # Store callback
                callback_key = f"{kraken_pair}:{channel}"
                self.callbacks[callback_key] = callback
    
    def _format_pair(self, pair: str) -> str:
        """Convert pair format (BTC/USD -> XBTUSD)."""
        # Kraken uses XBT for BTC
        parts = pair.split("/")
        if len(parts) != 2:
            return pair
        
        base, quote = parts
        if base == "BTC":
            base = "XBT"
        
        return f"{base}{quote}"
    
    def start(self):
        """Start WebSocket connection."""
        if self.ws_thread and self.ws_thread.is_alive():
            logger.warning("WebSocket already running")
            return
        
        self.stop_event.clear()
        self.ws_thread = threading.Thread(target=self._run, daemon=True)
        self.ws_thread.start()
        logger.info("WebSocket manager started")
    
    def stop(self):
        """Stop WebSocket connection."""
        self.stop_event.set()
        if self.ws:
            try:
                self.ws.close()
            except:
                pass
        
        if self.ws_thread:
            self.ws_thread.join(timeout=5.0)
        
        self.connected = False
        logger.info("WebSocket manager stopped")
    
    def _run(self):
        """Main WebSocket loop with reconnection."""
        while not self.stop_event.is_set():
            try:
                self._connect()
            except Exception as e:
                logger.error(f"WebSocket error: {e}", exc_info=True)
            
            if not self.stop_event.is_set():
                # Exponential backoff
                logger.info(f"Reconnecting in {self.reconnect_delay:.1f} seconds...")
                time.sleep(self.reconnect_delay)
                self.reconnect_delay = min(self.reconnect_delay * 2, self.max_reconnect_delay)
    
    def _connect(self):
        """Establish WebSocket connection."""
        self.ws = websocket.WebSocketApp(
            self.WS_URL,
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
        )
        
        self.ws.run_forever()
    
    def _on_open(self, ws):
        """Handle WebSocket open."""
        logger.info("WebSocket connected")
        self.connected = True
        self.last_heartbeat = datetime.utcnow()
        self.reconnect_delay = 1.0
        
        # Subscribe to channels
        self._send_subscriptions()
        
        # Start heartbeat monitor
        threading.Thread(target=self._heartbeat_monitor, daemon=True).start()
    
    def _on_message(self, ws, message):
        """Handle WebSocket message."""
        try:
            data = json.loads(message)
            
            # Check for heartbeat
            if isinstance(data, list) and len(data) > 0:
                if data[0] == 0:  # Heartbeat
                    self.last_heartbeat = datetime.utcnow()
                    return
                
                # Parse channel message
                if len(data) >= 4:
                    channel_id = data[0]
                    channel_data = data[1]
                    pair = data[2]
                    
                    # Find callback
                    for callback_key, callback in self.callbacks.items():
                        if callback_key.startswith(f"{pair}:"):
                            callback(pair, channel_data, datetime.utcnow())
                            break
        
        except Exception as e:
            logger.error(f"Error processing WebSocket message: {e}")
    
    def _on_error(self, ws, error):
        """Handle WebSocket error."""
        logger.error(f"WebSocket error: {error}")
    
    def _on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket close."""
        logger.warning(f"WebSocket closed: {close_status_code} - {close_msg}")
        self.connected = False
    
    def _send_subscriptions(self):
        """Send subscription messages for all pairs."""
        if not self.ws:
            return
        
        for pair, channels in self.subscriptions.items():
            for channel in channels:
                if channel == "trades":
                    sub = {
                        "event": "subscribe",
                        "pair": [pair],
                        "subscription": {"name": "trade"}
                    }
                elif channel == "book":
                    sub = {
                        "event": "subscribe",
                        "pair": [pair],
                        "subscription": {"name": "book", "depth": 10}
                    }
                else:
                    continue
                
                self.ws.send(json.dumps(sub))
                logger.debug(f"Subscribed to {pair}:{channel}")
    
    def _heartbeat_monitor(self):
        """Monitor heartbeat and reconnect if needed."""
        while not self.stop_event.is_set() and self.connected:
            time.sleep(10)  # Check every 10 seconds
            
            if self.last_heartbeat:
                elapsed = (datetime.utcnow() - self.last_heartbeat).total_seconds()
                if elapsed > self.HEARTBEAT_TIMEOUT:
                    logger.warning(f"Heartbeat timeout ({elapsed:.1f}s), reconnecting...")
                    if self.ws:
                        self.ws.close()
                    break
