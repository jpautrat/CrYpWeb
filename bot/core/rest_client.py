"""
Kraken REST API client.
Handles all REST API interactions with rate limiting and error handling.
"""
import requests
import time
from typing import Dict, Optional, Any, List
from datetime import datetime
from loguru import logger

from bot.config.settings import settings
from bot.core.auth_manager import KrakenAuthManager


class KrakenRESTClient:
    """Kraken REST API client with authentication."""
    
    BASE_URL = "https://api.kraken.com"
    PUBLIC_ENDPOINTS = {
        "ticker": "/0/public/Ticker",
        "assets": "/0/public/Assets",
        "asset_pairs": "/0/public/AssetPairs",
        "ohlc": "/0/public/OHLC",
        "trades": "/0/public/Trades",
        "depth": "/0/public/Depth",
    }
    PRIVATE_ENDPOINTS = {
        "balance": "/0/private/Balance",
        "trade_balance": "/0/private/TradeBalance",
        "open_orders": "/0/private/OpenOrders",
        "closed_orders": "/0/private/ClosedOrders",
        "query_orders": "/0/private/QueryOrders",
        "add_order": "/0/private/AddOrder",
        "cancel_order": "/0/private/CancelOrder",
        "cancel_all": "/0/private/CancelAll",
    }
    
    def __init__(self, api_key: str, api_secret: str):
        """
        Initialize REST client.
        
        Args:
            api_key: Kraken API key
            api_secret: Kraken API secret
        """
        self.auth = KrakenAuthManager(api_key, api_secret) if api_key and api_secret else None
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'ML-Kraken-Trader/1.0',
        })
        
        # Rate limiting
        self.last_request_time = 0.0
        self.min_request_interval = 0.5  # Minimum 500ms between requests
        
    def _rate_limit(self):
        """Enforce rate limiting."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        self.last_request_time = time.time()
    
    def _request(self, endpoint: str, method: str = "GET", params: Optional[Dict] = None,
                 private: bool = False) -> Optional[Dict[str, Any]]:
        """
        Make API request.
        
        Args:
            endpoint: API endpoint path
            method: HTTP method
            params: Request parameters
            private: Whether this is a private (authenticated) endpoint
            
        Returns:
            API response as dictionary, or None if error
        """
        self._rate_limit()
        
        url = self.BASE_URL + endpoint
        params = params or {}
        
        try:
            if private:
                if not self.auth:
                    logger.error("Private endpoint requires authentication")
                    return None
                
                # Get headers for authenticated request
                headers = self.auth.get_headers(endpoint, params)
                
                response = self.session.post(
                    url,
                    data=params,
                    headers=headers,
                    timeout=settings.performance.api_request_timeout_seconds,
                )
            else:
                if method == "GET":
                    response = self.session.get(
                        url,
                        params=params,
                        timeout=settings.performance.api_request_timeout_seconds,
                    )
                else:
                    response = self.session.post(
                        url,
                        data=params,
                        timeout=settings.performance.api_request_timeout_seconds,
                    )
            
            response.raise_for_status()
            data = response.json()
            
            if "error" in data and data["error"]:
                logger.error(f"Kraken API error: {data['error']}")
                return None
            
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in API request: {e}", exc_info=True)
            return None
    
    # Public endpoints
    
    def get_ticker(self, pair: str) -> Optional[Dict]:
        """Get ticker data for a pair."""
        return self._request(
            self.PUBLIC_ENDPOINTS["ticker"],
            params={"pair": pair}
        )
    
    def get_tradable_asset_pairs(self, info: str = "info") -> Optional[Dict]:
        """Get tradable asset pairs."""
        return self._request(
            self.PUBLIC_ENDPOINTS["asset_pairs"],
            params={"info": info}
        )
    
    def get_assets(self) -> Optional[Dict]:
        """Get asset information."""
        return self._request(self.PUBLIC_ENDPOINTS["assets"])
    
    def get_ohlc(self, pair: str, interval: int = 1, since: Optional[int] = None) -> Optional[Dict]:
        """
        Get OHLC data.
        
        Args:
            pair: Trading pair
            interval: Minutes per candle (1, 5, 15, 30, 60, 240, 1440, 10080, 21600)
            since: Return data since this timestamp
        """
        params = {"pair": pair, "interval": interval}
        if since:
            params["since"] = since
        return self._request(self.PUBLIC_ENDPOINTS["ohlc"], params=params)
    
    def get_trades(self, pair: str, since: Optional[int] = None) -> Optional[Dict]:
        """Get recent trades."""
        params = {"pair": pair}
        if since:
            params["since"] = since
        return self._request(self.PUBLIC_ENDPOINTS["trades"], params=params)
    
    def get_orderbook(self, pair: str, count: int = 100) -> Optional[Dict]:
        """Get order book."""
        return self._request(
            self.PUBLIC_ENDPOINTS["depth"],
            params={"pair": pair, "count": count}
        )
    
    # Private endpoints
    
    def get_balance(self) -> Optional[Dict]:
        """Get account balance."""
        return self._request(self.PRIVATE_ENDPOINTS["balance"], private=True)
    
    def get_open_orders(self, trades: bool = False) -> Optional[Dict]:
        """Get open orders."""
        return self._request(
            self.PRIVATE_ENDPOINTS["open_orders"],
            private=True,
            params={"trades": trades}
        )
    
    def add_order(self, pair: str, side: str, order_type: str, volume: float,
                  price: Optional[float] = None, post_only: bool = False) -> Optional[Dict]:
        """
        Add order.
        
        Args:
            pair: Trading pair
            side: 'buy' or 'sell'
            order_type: 'market' or 'limit'
            volume: Order volume
            price: Limit price (required for limit orders)
            post_only: Post-only flag for maker orders
        """
        params = {
            "pair": pair,
            "type": side,
            "ordertype": order_type,
            "volume": str(volume),
        }
        
        if order_type == "limit":
            if not price:
                logger.error("Price required for limit orders")
                return None
            params["price"] = str(price)
        
        if post_only:
            params["oflags"] = "post"
        
        return self._request(self.PRIVATE_ENDPOINTS["add_order"], private=True, params=params)
    
    def cancel_order(self, txid: str) -> Optional[Dict]:
        """Cancel order by transaction ID."""
        return self._request(
            self.PRIVATE_ENDPOINTS["cancel_order"],
            private=True,
            params={"txid": txid}
        )
    
    def cancel_all_orders(self) -> Optional[Dict]:
        """Cancel all open orders."""
        return self._request(self.PRIVATE_ENDPOINTS["cancel_all"], private=True)
    
    def query_orders(self, txids: List[str], trades: bool = False) -> Optional[Dict]:
        """Query orders by transaction IDs."""
        return self._request(
            self.PRIVATE_ENDPOINTS["query_orders"],
            private=True,
            params={"txid": ",".join(txids), "trades": trades}
        )
