"""
Universe Manager - Handles dynamic asset universe selection and refresh
"""

import pandas as pd
from typing import List, Dict, Set, Optional
from datetime import datetime, timedelta
from loguru import logger
from ..core.rest_client import KrakenRestClient
from ..compliance.asset_filter import AssetFilter


class UniverseManager:
    """
    Manages the trading universe of cryptocurrency pairs.
    Dynamically selects top pairs by volume while respecting compliance filters.
    """
    
    def __init__(
        self,
        rest_client: KrakenRestClient,
        asset_filter: AssetFilter,
        base_quote: str = "USD",
        universe_size: int = 10,
        min_daily_volume_usd: float = 1_000_000.0,
        refresh_minutes: int = 60
    ):
        self.rest_client = rest_client
        self.asset_filter = asset_filter
        self.base_quote = base_quote
        self.universe_size = universe_size
        self.min_daily_volume_usd = min_daily_volume_usd
        self.refresh_minutes = refresh_minutes
        
        self.current_universe: List[str] = []
        self.pair_info: Dict[str, Dict] = {}
        self.last_refresh: Optional[datetime] = None
        
        logger.info(
            f"UniverseManager initialized: base={base_quote}, "
            f"size={universe_size}, min_volume=${min_daily_volume_usd:,.0f}"
        )
    
    def refresh_universe(self) -> List[str]:
        """
        Refresh the trading universe by querying Kraken for top pairs.
        
        Returns:
            List of tradeable pair symbols
        """
        logger.info("Refreshing trading universe...")
        
        try:
            # Get all tradeable pairs from Kraken
            ticker_data = self.rest_client.get_ticker_information()
            asset_pairs = self.rest_client.get_tradeable_asset_pairs()
            
            # Filter pairs for our base quote currency
            eligible_pairs = []
            
            for pair_name, pair_data in asset_pairs.items():
                # Skip if not our base quote
                if not pair_data.get('quote', '').endswith(self.base_quote):
                    continue
                
                # Get the wsname (WebSocket name) for the pair
                wsname = pair_data.get('wsname')
                if not wsname:
                    continue
                
                # Check compliance (US North Carolina restrictions)
                base_asset = pair_data.get('base', '')
                if not self.asset_filter.is_compliant(base_asset):
                    logger.debug(f"Excluding non-compliant asset: {base_asset}")
                    continue
                
                # Get ticker data for this pair
                ticker_key = list(ticker_data.keys())[0] if ticker_data else None
                if pair_name in ticker_data:
                    ticker = ticker_data[pair_name]
                elif ticker_key and pair_name == ticker_key:
                    ticker = ticker_data[ticker_key]
                else:
                    # Try to find by wsname
                    ticker = None
                    for tk, tv in ticker_data.items():
                        if asset_pairs.get(tk, {}).get('wsname') == wsname:
                            ticker = tv
                            break
                    if not ticker:
                        continue
                
                # Calculate 24h volume in USD
                volume_24h = float(ticker.get('v', [0, 0])[1])  # 24h volume
                last_price = float(ticker.get('c', [0])[0])  # Last price
                volume_usd = volume_24h * last_price
                
                # Check minimum volume requirement
                if volume_usd < self.min_daily_volume_usd:
                    continue
                
                # Get minimum order size for small capital optimization
                min_order = float(pair_data.get('ordermin', 0))
                
                eligible_pairs.append({
                    'pair': wsname,
                    'pair_name': pair_name,
                    'base': base_asset,
                    'volume_usd': volume_usd,
                    'min_order': min_order,
                    'last_price': last_price,
                    'lot_decimals': pair_data.get('lot_decimals', 8),
                    'pair_decimals': pair_data.get('pair_decimals', 5),
                    'ordermin': min_order,
                    'fee_maker': float(pair_data.get('fees_maker', [[0, 0.16]])[0][1]),
                    'fee_taker': float(pair_data.get('fees', [[0, 0.26]])[0][1])
                })
            
            # Sort by volume and select top N
            eligible_pairs.sort(key=lambda x: x['volume_usd'], reverse=True)
            
            # For small capital, also consider minimum order size
            # Prioritize pairs with good volume AND reasonable minimums
            for pair in eligible_pairs:
                pair['capital_efficiency'] = pair['volume_usd'] / (pair['min_order'] * pair['last_price'])
            
            # Select top universe_size pairs
            selected_pairs = eligible_pairs[:self.universe_size]
            
            # Update state
            self.current_universe = [p['pair'] for p in selected_pairs]
            self.pair_info = {p['pair']: p for p in selected_pairs}
            self.last_refresh = datetime.now()
            
            logger.info(
                f"Universe refreshed: {len(self.current_universe)} pairs selected"
            )
            
            for pair_data in selected_pairs:
                logger.info(
                    f"  {pair_data['pair']}: "
                    f"Volume=${pair_data['volume_usd']:,.0f}, "
                    f"MinOrder={pair_data['min_order']:.8f}, "
                    f"Price=${pair_data['last_price']:,.2f}"
                )
            
            return self.current_universe
            
        except Exception as e:
            logger.error(f"Failed to refresh universe: {e}", exc_info=True)
            # Return current universe if refresh fails
            return self.current_universe
    
    def should_refresh(self) -> bool:
        """Check if universe needs refresh based on time"""
        if self.last_refresh is None:
            return True
        
        time_since_refresh = datetime.now() - self.last_refresh
        return time_since_refresh > timedelta(minutes=self.refresh_minutes)
    
    def get_universe(self, force_refresh: bool = False) -> List[str]:
        """
        Get current trading universe, optionally forcing a refresh.
        
        Args:
            force_refresh: Force immediate refresh regardless of timing
            
        Returns:
            List of tradeable pair symbols
        """
        if force_refresh or self.should_refresh():
            return self.refresh_universe()
        return self.current_universe
    
    def get_pair_info(self, pair: str) -> Optional[Dict]:
        """Get detailed information about a specific pair"""
        return self.pair_info.get(pair)
    
    def get_minimum_order_size(self, pair: str) -> float:
        """Get minimum order size for a pair"""
        pair_data = self.pair_info.get(pair, {})
        return pair_data.get('ordermin', 0.0)
    
    def get_pair_decimals(self, pair: str) -> tuple:
        """Get (lot_decimals, pair_decimals) for order formatting"""
        pair_data = self.pair_info.get(pair, {})
        return (
            pair_data.get('lot_decimals', 8),
            pair_data.get('pair_decimals', 5)
        )
    
    def get_fees(self, pair: str) -> tuple:
        """Get (maker_fee, taker_fee) for a pair"""
        pair_data = self.pair_info.get(pair, {})
        return (
            pair_data.get('fee_maker', 0.0016),
            pair_data.get('fee_taker', 0.0026)
        )
