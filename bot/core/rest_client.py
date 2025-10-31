"""
Kraken REST API Client
Handles all REST API interactions with Kraken exchange.
"""

import time
import requests
from typing import Dict, List, Optional, Any
from loguru import logger
from .auth_manager import AuthManager


class KrakenRestClient:
    """
    REST API client for Kraken exchange.
    Implements all necessary endpoints for live trading.
    """
    
    BASE_URL = "https://api.kraken.com"
    
    def __init__(self, auth_manager: Optional[AuthManager] = None):
        """
        Initialize REST client.
        
        Args:
            auth_manager: Authentication manager for private endpoints
        """
        self.auth_manager = auth_manager
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'ML-Kraken-Pro-Trader/1.0'
        })
        
        self.last_request_time = 0.0
        self.min_request_interval = 0.5  # 500ms between requests
        
        logger.info("KrakenRestClient initialized")
    
    def _rate_limit(self):
        """Enforce rate limiting between requests"""
        now = time.time()
        time_since_last = now - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _public_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """
        Make a public API request.
        
        Args:
            endpoint: API endpoint (e.g., 'Ticker')
            params: Query parameters
            
        Returns:
            Response data dictionary
        """
        self._rate_limit()
        
        url = f"{self.BASE_URL}/0/public/{endpoint}"
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('error') and len(data['error']) > 0:
                logger.error(f"API error: {data['error']}")
                raise Exception(f"Kraken API error: {data['error']}")
            
            return data.get('result', {})
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise
    
    def _private_request(self, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """
        Make a private (authenticated) API request.
        
        Args:
            endpoint: API endpoint (e.g., 'Balance')
            data: POST data
            
        Returns:
            Response data dictionary
        """
        if not self.auth_manager:
            raise Exception("Auth manager required for private endpoints")
        
        self._rate_limit()
        
        url = f"{self.BASE_URL}/0/private/{endpoint}"
        urlpath = f"/0/private/{endpoint}"
        
        # Add nonce
        if data is None:
            data = {}
        data['nonce'] = self.auth_manager.generate_nonce()
        
        # Get authenticated headers
        headers = self.auth_manager.get_headers(urlpath, data)
        
        try:
            response = self.session.post(url, headers=headers, data=data, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            
            if result.get('error') and len(result['error']) > 0:
                logger.error(f"API error: {result['error']}")
                raise Exception(f"Kraken API error: {result['error']}")
            
            return result.get('result', {})
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise
    
    # =============================================================================
    # PUBLIC ENDPOINTS
    # =============================================================================
    
    def get_server_time(self) -> Dict:
        """Get Kraken server time"""
        return self._public_request('Time')
    
    def get_tradeable_asset_pairs(self, pairs: Optional[List[str]] = None) -> Dict:
        """
        Get tradeable asset pairs.
        
        Args:
            pairs: Optional list of specific pairs to query
            
        Returns:
            Dictionary of pair information
        """
        params = {}
        if pairs:
            params['pair'] = ','.join(pairs)
        
        return self._public_request('AssetPairs', params)
    
    def get_ticker_information(self, pairs: Optional[List[str]] = None) -> Dict:
        """
        Get ticker information for pairs.
        
        Args:
            pairs: Optional list of specific pairs
            
        Returns:
            Dictionary of ticker data
        """
        params = {}
        if pairs:
            params['pair'] = ','.join(pairs)
        
        return self._public_request('Ticker', params)
    
    def get_ohlc_data(
        self,
        pair: str,
        interval: int = 1,
        since: Optional[int] = None
    ) -> Dict:
        """
        Get OHLC data.
        
        Args:
            pair: Trading pair
            interval: Time interval in minutes (1, 5, 15, 30, 60, 240, 1440, 10080, 21600)
            since: Return committed OHLC data since given ID
            
        Returns:
            Dictionary with OHLC data and last ID
        """
        params = {'pair': pair, 'interval': interval}
        if since:
            params['since'] = since
        
        return self._public_request('OHLC', params)
    
    def get_order_book(self, pair: str, count: int = 10) -> Dict:
        """
        Get order book.
        
        Args:
            pair: Trading pair
            count: Number of levels (default 10)
            
        Returns:
            Order book data
        """
        params = {'pair': pair, 'count': count}
        return self._public_request('Depth', params)
    
    def get_recent_trades(self, pair: str, since: Optional[int] = None) -> Dict:
        """
        Get recent trades.
        
        Args:
            pair: Trading pair
            since: Return trades since this timestamp
            
        Returns:
            Recent trades data
        """
        params = {'pair': pair}
        if since:
            params['since'] = since
        
        return self._public_request('Trades', params)
    
    # =============================================================================
    # PRIVATE ENDPOINTS
    # =============================================================================
    
    def get_account_balance(self) -> Dict:
        """Get account balance"""
        return self._private_request('Balance')
    
    def get_trade_balance(self, asset: str = "ZUSD") -> Dict:
        """
        Get trade balance.
        
        Args:
            asset: Base asset for balance calculation
            
        Returns:
            Trade balance info
        """
        return self._private_request('TradeBalance', {'asset': asset})
    
    def get_open_orders(self, trades: bool = False) -> Dict:
        """
        Get open orders.
        
        Args:
            trades: Whether to include trades
            
        Returns:
            Dictionary of open orders
        """
        return self._private_request('OpenOrders', {'trades': trades})
    
    def get_closed_orders(
        self,
        trades: bool = False,
        start: Optional[int] = None,
        end: Optional[int] = None
    ) -> Dict:
        """
        Get closed orders.
        
        Args:
            trades: Whether to include trades
            start: Starting timestamp
            end: Ending timestamp
            
        Returns:
            Dictionary of closed orders
        """
        data = {'trades': trades}
        if start:
            data['start'] = start
        if end:
            data['end'] = end
        
        return self._private_request('ClosedOrders', data)
    
    def query_orders_info(self, txids: List[str], trades: bool = False) -> Dict:
        """
        Query orders info.
        
        Args:
            txids: List of transaction IDs
            trades: Whether to include trades
            
        Returns:
            Order information
        """
        data = {
            'txid': ','.join(txids),
            'trades': trades
        }
        return self._private_request('QueryOrders', data)
    
    def add_order(
        self,
        pair: str,
        side: str,
        order_type: str,
        volume: float,
        price: Optional[float] = None,
        price2: Optional[float] = None,
        leverage: Optional[str] = None,
        oflags: Optional[str] = None,
        starttm: Optional[str] = None,
        expiretm: Optional[str] = None,
        validate: bool = False
    ) -> Dict:
        """
        Place an order.
        
        Args:
            pair: Trading pair
            side: 'buy' or 'sell'
            order_type: Order type ('market', 'limit', etc.)
            volume: Order volume in base currency
            price: Price (required for limit orders)
            price2: Secondary price (for stop-loss, etc.)
            leverage: Leverage amount
            oflags: Order flags (e.g., 'post' for post-only)
            starttm: Start time
            expiretm: Expiration time
            validate: Validate only, don't submit
            
        Returns:
            Order result with transaction IDs
        """
        data = {
            'pair': pair,
            'type': side,
            'ordertype': order_type,
            'volume': str(volume)
        }
        
        if price is not None:
            data['price'] = str(price)
        if price2 is not None:
            data['price2'] = str(price2)
        if leverage:
            data['leverage'] = leverage
        if oflags:
            data['oflags'] = oflags
        if starttm:
            data['starttm'] = starttm
        if expiretm:
            data['expiretm'] = expiretm
        if validate:
            data['validate'] = 'true'
        
        return self._private_request('AddOrder', data)
    
    def cancel_order(self, txid: str) -> Dict:
        """
        Cancel an open order.
        
        Args:
            txid: Transaction ID to cancel
            
        Returns:
            Cancellation result
        """
        return self._private_request('CancelOrder', {'txid': txid})
    
    def cancel_all_orders(self) -> Dict:
        """Cancel all open orders"""
        return self._private_request('CancelAll')
    
    def get_websocket_token(self) -> str:
        """
        Get WebSocket authentication token.
        
        Returns:
            WebSocket token string
        """
        result = self._private_request('GetWebSocketsToken')
        return result.get('token', '')
