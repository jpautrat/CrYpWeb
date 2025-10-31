"""
Kraken WebSocket Manager
Handles real-time market data streams via WebSocket connections.
"""

import json
import time
import threading
from typing import Dict, List, Callable, Optional
from datetime import datetime
import websocket
from loguru import logger
from collections import deque


class KrakenWebSocketManager:
    """
    Manages WebSocket connections to Kraken for real-time market data.
    Handles subscriptions, reconnections, and data distribution.
    """
    
    WS_URL = "wss://ws.kraken.com"
    WS_AUTH_URL = "wss://ws-auth.kraken.com"
    
    def __init__(self, heartbeat_timeout: int = 30):
        """
        Initialize WebSocket manager.
        
        Args:
            heartbeat_timeout: Seconds without heartbeat before reconnect
        """
        self.heartbeat_timeout = heartbeat_timeout
        self.ws = None
        self.ws_auth = None
        
        self.subscriptions: Dict[str, List[str]] = {}  # channel -> [pairs]
        self.callbacks: Dict[str, List[Callable]] = {}  # channel -> [callbacks]
        
        self.last_heartbeat = time.time()
        self.is_connected = False
        self.should_run = False
        
        self.message_buffer = deque(maxlen=10000)
        
        self.reconnect_delay = 1.0
        self.max_reconnect_delay = 60.0
        
        logger.info("KrakenWebSocketManager initialized")
    
    def connect(self):
        """Establish WebSocket connection"""
        try:
            logger.info("Connecting to Kraken WebSocket...")
            
            self.ws = websocket.WebSocketApp(
                self.WS_URL,
                on_open=self._on_open,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close
            )
            
            self.should_run = True
            
            # Start WebSocket in separate thread
            self.ws_thread = threading.Thread(
                target=self.ws.run_forever,
                daemon=True
            )
            self.ws_thread.start()
            
            # Wait for connection
            timeout = 10
            start = time.time()
            while not self.is_connected and time.time() - start < timeout:
                time.sleep(0.1)
            
            if not self.is_connected:
                raise Exception("Failed to connect within timeout")
            
            # Start heartbeat monitor
            self.heartbeat_thread = threading.Thread(
                target=self._monitor_heartbeat,
                daemon=True
            )
            self.heartbeat_thread.start()
            
            logger.info("WebSocket connected successfully")
            
        except Exception as e:
            logger.error(f"WebSocket connection failed: {e}")
            raise
    
    def disconnect(self):
        """Close WebSocket connection"""
        logger.info("Disconnecting WebSocket...")
        self.should_run = False
        
        if self.ws:
            self.ws.close()
        
        self.is_connected = False
    
    def subscribe(
        self,
        channel: str,
        pairs: List[str],
        callback: Optional[Callable] = None
    ):
        """
        Subscribe to a WebSocket channel.
        
        Args:
            channel: Channel name ('ticker', 'trade', 'book', 'ohlc', 'spread')
            pairs: List of trading pairs
            callback: Optional callback function for messages
        """
        if not self.is_connected:
            raise Exception("WebSocket not connected")
        
        # Store subscription
        if channel not in self.subscriptions:
            self.subscriptions[channel] = []
        self.subscriptions[channel].extend(pairs)
        
        # Store callback
        if callback:
            if channel not in self.callbacks:
                self.callbacks[channel] = []
            self.callbacks[channel].append(callback)
        
        # Send subscription message
        sub_message = {
            "event": "subscribe",
            "pair": pairs,
            "subscription": {"name": channel}
        }
        
        self._send(sub_message)
        
        logger.info(f"Subscribed to {channel} for {len(pairs)} pairs")
    
    def unsubscribe(self, channel: str, pairs: List[str]):
        """
        Unsubscribe from a WebSocket channel.
        
        Args:
            channel: Channel name
            pairs: List of trading pairs
        """
        if not self.is_connected:
            return
        
        unsub_message = {
            "event": "unsubscribe",
            "pair": pairs,
            "subscription": {"name": channel}
        }
        
        self._send(unsub_message)
        
        # Remove from subscriptions
        if channel in self.subscriptions:
            for pair in pairs:
                if pair in self.subscriptions[channel]:
                    self.subscriptions[channel].remove(pair)
        
        logger.info(f"Unsubscribed from {channel} for {len(pairs)} pairs")
    
    def _send(self, message: Dict):
        """Send message via WebSocket"""
        if self.ws and self.is_connected:
            self.ws.send(json.dumps(message))
    
    def _on_open(self, ws):
        """WebSocket connection opened"""
        logger.info("WebSocket connection opened")
        self.is_connected = True
        self.last_heartbeat = time.time()
        self.reconnect_delay = 1.0  # Reset reconnect delay
    
    def _on_message(self, ws, message):
        """Handle incoming WebSocket message"""
        try:
            data = json.loads(message)
            
            # Handle heartbeat
            if isinstance(data, dict) and data.get('event') == 'heartbeat':
                self.last_heartbeat = time.time()
                return
            
            # Handle system status
            if isinstance(data, dict) and data.get('event') == 'systemStatus':
                logger.info(f"System status: {data.get('status')}")
                return
            
            # Handle subscription status
            if isinstance(data, dict) and data.get('event') in ['subscriptionStatus', 'unsubscribeStatus']:
                status = data.get('status')
                channel = data.get('subscription', {}).get('name')
                logger.info(f"Subscription status: {channel} - {status}")
                return
            
            # Handle channel data
            if isinstance(data, list) and len(data) >= 3:
                channel_id = data[0]
                channel_data = data[1]
                channel_name = data[2]
                pair = data[3] if len(data) > 3 else None
                
                # Store in buffer
                self.message_buffer.append({
                    'timestamp': datetime.now(),
                    'channel': channel_name,
                    'pair': pair,
                    'data': channel_data
                })
                
                # Call registered callbacks
                if channel_name in self.callbacks:
                    for callback in self.callbacks[channel_name]:
                        try:
                            callback(pair, channel_data, channel_name)
                        except Exception as e:
                            logger.error(f"Callback error: {e}")
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse WebSocket message: {e}")
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}")
    
    def _on_error(self, ws, error):
        """Handle WebSocket error"""
        logger.error(f"WebSocket error: {error}")
    
    def _on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket close"""
        logger.warning(f"WebSocket closed: {close_status_code} - {close_msg}")
        self.is_connected = False
        
        # Attempt reconnection
        if self.should_run:
            self._reconnect()
    
    def _reconnect(self):
        """Attempt to reconnect with exponential backoff"""
        logger.info(f"Attempting reconnection in {self.reconnect_delay}s...")
        time.sleep(self.reconnect_delay)
        
        # Exponential backoff
        self.reconnect_delay = min(
            self.reconnect_delay * 2,
            self.max_reconnect_delay
        )
        
        try:
            self.connect()
            
            # Re-subscribe to all channels
            for channel, pairs in self.subscriptions.items():
                if pairs:
                    self.subscribe(channel, pairs)
            
        except Exception as e:
            logger.error(f"Reconnection failed: {e}")
            if self.should_run:
                self._reconnect()
    
    def _monitor_heartbeat(self):
        """Monitor heartbeat and reconnect if stale"""
        while self.should_run:
            time.sleep(5)  # Check every 5 seconds
            
            if not self.is_connected:
                continue
            
            time_since_heartbeat = time.time() - self.last_heartbeat
            
            if time_since_heartbeat > self.heartbeat_timeout:
                logger.warning(
                    f"No heartbeat for {time_since_heartbeat:.1f}s, reconnecting..."
                )
                self.is_connected = False
                if self.ws:
                    self.ws.close()
                self._reconnect()
    
    def get_recent_messages(
        self,
        channel: Optional[str] = None,
        pair: Optional[str] = None,
        count: int = 100
    ) -> List[Dict]:
        """
        Get recent messages from buffer.
        
        Args:
            channel: Filter by channel name
            pair: Filter by pair
            count: Maximum number of messages
            
        Returns:
            List of recent messages
        """
        messages = list(self.message_buffer)
        
        # Filter by channel
        if channel:
            messages = [m for m in messages if m['channel'] == channel]
        
        # Filter by pair
        if pair:
            messages = [m for m in messages if m['pair'] == pair]
        
        # Return most recent
        return messages[-count:]
