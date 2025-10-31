"""
Kraken REST API client with rate limiting, error handling, and key pooling.
"""
import requests
import time
from typing import Dict, List, Optional, Any
from urllib.parse import urlencode
from datetime import datetime
from loguru import logger

from .auth_manager import KrakenAuthManager
from .key_pool import KeyPool
from ..config.settings import APIConfig


class KrakenRESTClient:
    """REST API client for Kraken with key pooling and rate limiting"""
    
    def __init__(self, key_pool: KeyPool, time_sync):
        self.key_pool = key_pool
        self.time_sync = time_sync
        self.base_url = "https://api.kraken.com"
        self.public_base_url = f"{self.base_url}/0/public"
        self.private_base_url = f"{self.base_url}/0/private"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'KrakenLiveTrader/1.0',
            'Connection': 'keep-alive'
        })
        self.rate_limit_delay = 0.05  # 50ms between requests to stay under 20 req/s
    
    def _make_public_request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """Make public API request (no authentication)"""
        url = f"{self.public_base_url}/{endpoint}"
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if data.get('error') and len(data['error']) > 0:
                logger.error(f"Kraken API error: {data['error']}")
                return None
            
            return data.get('result')
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Public API request failed: {e}")
            return None
    
    def _make_private_request(self, endpoint: str, data: Optional[Dict] = None) -> Optional[Dict]:
        """
        Make private API request (authenticated).
        Automatically routes through key pool with failover.
        """
        urlpath = f"/0/private/{endpoint}"
        url = f"{self.base_url}{urlpath}"
        
        # Get API key from pool
        key = self.key_pool.get_next_key(strategy="health_based")
        if not key:
            logger.error("No available API keys for private request")
            return None
        
        key_id = key["id"]
        start_time = time.time()
        
        # Prepare request data
        if data is None:
            data = {}
        
        # Create auth manager for this key
        auth = KrakenAuthManager(key["key"], key["secret"])
        
        # Generate nonce and signature
        data['nonce'] = int(self.time_sync.get_unix_timestamp() * 1000)
        headers = auth.get_headers(urlpath, data)
        
        try:
            # Rate limiting
            time.sleep(self.rate_limit_delay)
            
            response = self.session.post(url, data=data, headers=headers, timeout=30)
            latency_ms = (time.time() - start_time) * 1000
            
            response.raise_for_status()
            response_data = response.json()
            
            # Check for API errors
            if response_data.get('error') and len(response_data['error']) > 0:
                errors = response_data['error']
                
                # Check for rate limit error
                if any('EAPI:Rate limit exceeded' in str(e) for e in errors):
                    self.key_pool.record_error(key_id, "rate_limit")
                    logger.warning(f"Rate limit hit on key {key_id}, will retry with different key")
                    
                    # Retry with different key
                    return self._make_private_request(endpoint, data)
                
                # Other errors
                logger.error(f"Kraken API error on key {key_id}: {errors}")
                self.key_pool.record_error(key_id, "api_error")
                return None
            
            # Success
            self.key_pool.record_success(key_id, latency_ms)
            return response_data.get('result')
        
        except requests.exceptions.Timeout:
            self.key_pool.record_error(key_id, "timeout")
            logger.error(f"Request timeout on key {key_id}")
            return None
        
        except requests.exceptions.RequestException as e:
            self.key_pool.record_error(key_id, "network_error")
            logger.error(f"Request failed on key {key_id}: {e}")
            return None
    
    # Public API methods
    def get_server_time(self) -> Optional[Dict]:
        """Get Kraken server time"""
        return self._make_public_request("Time")
    
    def get_asset_info(self) -> Optional[Dict]:
        """Get asset information"""
        return self._make_public_request("Assets")
    
    def get_tradable_pairs(self) -> Optional[List[str]]:
        """Get list of tradable pairs"""
        pairs_data = self._make_public_request("AssetPairs")
        if pairs_data:
            return list(pairs_data.keys())
        return None
    
    def get_pair_info(self, pair: str) -> Optional[Dict]:
        """Get information about a specific pair"""
        params = {"pair": pair}
        pairs_data = self._make_public_request("AssetPairs", params)
        if pairs_data and pair in pairs_data:
            return pairs_data[pair]
        return None
    
    def get_ticker(self, pair: str) -> Optional[Dict]:
        """Get ticker information for a pair"""
        params = {"pair": pair}
        ticker_data = self._make_public_request("Ticker", params)
        if ticker_data and pair in ticker_data:
            return ticker_data[pair]
        return None
    
    def get_ohlc(self, pair: str, interval: int = 1, since: Optional[int] = None) -> Optional[Dict]:
        """
        Get OHLC data.
        interval: 1, 5, 15, 30, 60, 240, 1440, 10080, 21600 (minutes)
        """
        params = {"pair": pair, "interval": interval}
        if since:
            params["since"] = since
        return self._make_public_request("OHLC", params)
    
    def get_orderbook(self, pair: str, count: int = 100) -> Optional[Dict]:
        """Get order book data"""
        params = {"pair": pair, "count": count}
        return self._make_public_request("Depth", params)
    
    def get_trades(self, pair: str, since: Optional[int] = None) -> Optional[Dict]:
        """Get recent trades"""
        params = {"pair": pair}
        if since:
            params["since"] = since
        return self._make_public_request("Trades", params)
    
    # Private API methods
    def get_balance(self) -> Optional[Dict]:
        """Get account balance"""
        return self._make_private_request("Balance")
    
    def get_trade_balance(self) -> Optional[Dict]:
        """Get trade balance"""
        return self._make_private_request("TradeBalance")
    
    def get_open_orders(self) -> Optional[Dict]:
        """Get open orders"""
        return self._make_private_request("OpenOrders")
    
    def get_closed_orders(self, start: Optional[int] = None, end: Optional[int] = None) -> Optional[Dict]:
        """Get closed orders"""
        data = {}
        if start:
            data["start"] = start
        if end:
            data["end"] = end
        return self._make_private_request("ClosedOrders", data)
    
    def get_trades_history(self, start: Optional[int] = None, end: Optional[int] = None) -> Optional[Dict]:
        """Get trades history"""
        data = {}
        if start:
            data["start"] = start
        if end:
            data["end"] = end
        return self._make_private_request("TradesHistory", data)
    
    def place_order(self, pair: str, side: str, order_type: str, 
                   volume: float, price: Optional[float] = None,
                   post_only: bool = True) -> Optional[Dict]:
        """
        Place an order.
        
        Args:
            pair: Trading pair (e.g., 'XBTUSD')
            side: 'buy' or 'sell'
            order_type: 'limit' or 'market'
            volume: Order size in base currency
            price: Limit price (required for limit orders)
            post_only: Use post-only (maker) order
        
        Returns:
            Order response dictionary
        """
        data = {
            "pair": pair,
            "type": side,
            "ordertype": order_type,
            "volume": str(volume),
        }
        
        if order_type == "limit":
            if price is None:
                logger.error("Price required for limit orders")
                return None
            data["price"] = str(price)
            
            if post_only:
                data["oflags"] = "post"
        
        result = self._make_private_request("AddOrder", data)
        return result
    
    def cancel_order(self, txid: str) -> Optional[Dict]:
        """Cancel an order by transaction ID"""
        data = {"txid": txid}
        return self._make_private_request("CancelOrder", data)
    
    def cancel_all_orders(self) -> Optional[Dict]:
        """Cancel all open orders"""
        return self._make_private_request("CancelAll")
    
    def get_order_status(self, txid: str) -> Optional[Dict]:
        """Get status of a specific order"""
        data = {"txid": txid}
        return self._make_private_request("QueryOrders", data)
