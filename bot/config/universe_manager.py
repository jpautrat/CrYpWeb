"""
Universe management for dynamic pair selection.
Handles Top-10 volume selection with US-NC compliance filtering.
"""
import time
from datetime import datetime, timedelta
from typing import List, Set, Dict, Optional
import pandas as pd
from loguru import logger

from bot.config.settings import settings
from bot.compliance.asset_filter import AssetFilter
from bot.core.rest_client import KrakenRESTClient


class UniverseManager:
    """Manages the trading universe with dynamic updates."""
    
    def __init__(self, rest_client: KrakenRESTClient, asset_filter: AssetFilter):
        """
        Initialize universe manager.
        
        Args:
            rest_client: REST client for Kraken API
            asset_filter: Asset filter for compliance
        """
        self.rest_client = rest_client
        self.asset_filter = asset_filter
        self.current_universe: List[str] = []
        self.last_refresh: Optional[datetime] = None
        self.pair_metadata: Dict[str, Dict] = {}
        self.min_order_sizes: Dict[str, float] = {}
    
    def get_universe(self, force_refresh: bool = False) -> List[str]:
        """
        Get current trading universe.
        
        Args:
            force_refresh: Force refresh even if within refresh interval
            
        Returns:
            List of trading pairs (e.g., ['BTC/USD', 'ETH/USD'])
        """
        now = datetime.utcnow()
        
        # Check if refresh is needed
        needs_refresh = (
            force_refresh or
            self.last_refresh is None or
            (now - self.last_refresh).total_seconds() > 
            (settings.universe.universe_refresh_minutes * 60)
        )
        
        if needs_refresh:
            logger.info("Refreshing trading universe...")
            self._refresh_universe()
            self.last_refresh = now
        
        return self.current_universe.copy()
    
    def _refresh_universe(self):
        """Refresh universe from Kraken API."""
        try:
            # Get all asset pairs
            pairs_data = self.rest_client.get_tradable_asset_pairs()
            
            if not pairs_data or "result" not in pairs_data:
                logger.error("Failed to fetch asset pairs from Kraken")
                return
            
            # Filter for USD pairs and compliance
            eligible_pairs = []
            pair_volumes = []
            
            for pair_name, pair_info in pairs_data["result"].items():
                # Check if USD quote
                quote = pair_info.get("quote", "")
                if quote != settings.universe.base_quote:
                    continue
                
                # Parse pair name
                if "/" not in pair_name:
                    # Handle Kraken pair naming (e.g., "XBTUSD" -> "BTC/USD")
                    base = pair_info.get("base", "")
                    quote = pair_info.get("quote", "")
                    if not base or not quote:
                        continue
                    formatted_pair = f"{base}/{quote}"
                else:
                    formatted_pair = pair_name
                
                # Compliance check
                if not self.asset_filter.is_tradeable(formatted_pair):
                    logger.debug(f"Skipping restricted pair: {formatted_pair}")
                    continue
                
                # Get 24h volume
                volume = self._get_pair_volume(pair_name, pairs_data["result"])
                
                if volume >= settings.universe.min_daily_volume_usd:
                    eligible_pairs.append(formatted_pair)
                    pair_volumes.append({
                        "pair": formatted_pair,
                        "volume_usd": volume,
                        "raw_pair": pair_name,
                        "metadata": pair_info,
                    })
            
            # Sort by volume and take top N
            pair_volumes.sort(key=lambda x: x["volume_usd"], reverse=True)
            top_pairs = pair_volumes[:settings.universe.universe_size]
            
            # Update universe
            self.current_universe = [p["pair"] for p in top_pairs]
            
            # Update metadata and min order sizes
            for p in top_pairs:
                self.pair_metadata[p["pair"]] = p["metadata"]
                self.min_order_sizes[p["pair"]] = self._calculate_min_order_size(
                    p["pair"], p["metadata"]
                )
            
            logger.info(
                f"Universe refreshed: {len(self.current_universe)} pairs selected. "
                f"Pairs: {', '.join(self.current_universe)}"
            )
            
        except Exception as e:
            logger.error(f"Error refreshing universe: {e}", exc_info=True)
            # Keep existing universe if refresh fails
    
    def _get_pair_volume(self, pair_name: str, all_pairs: Dict) -> float:
        """
        Get 24h USD volume for a pair.
        
        Args:
            pair_name: Kraken pair name
            all_pairs: All pair metadata
            
        Returns:
            Volume in USD
        """
        try:
            # Try to get ticker data for volume
            ticker = self.rest_client.get_ticker(pair_name)
            if ticker and "result" in ticker and pair_name in ticker["result"]:
                vol_data = ticker["result"][pair_name]
                volume_24h = float(vol_data.get("v", [0])[1] if isinstance(vol_data.get("v"), list) else 0)
                last_price = float(vol_data.get("c", [0])[0] if isinstance(vol_data.get("c"), list) else 0)
                return volume_24h * last_price
        except Exception as e:
            logger.warning(f"Could not fetch volume for {pair_name}: {e}")
        
        return 0.0
    
    def _calculate_min_order_size(self, pair: str, metadata: Dict) -> float:
        """
        Calculate minimum order size using stricter of Kraken minimum or user-defined minimum.
        
        Args:
            pair: Trading pair (e.g., "BTC/USD")
            metadata: Pair metadata from Kraken
            
        Returns:
            Minimum order size in quote currency
        """
        # Get Kraken minimum
        kraken_min = float(metadata.get("ordermin", 0))
        
        # Get user-defined minimum for quote currency
        quote_currency = pair.split("/")[-1]
        user_min = settings.universe.currency_minimums.get(quote_currency, 0.0)
        
        # Return the stricter (higher) limit
        return max(kraken_min, user_min)
    
    def get_min_order_size(self, pair: str) -> float:
        """Get minimum order size for a pair."""
        return self.min_order_sizes.get(pair, settings.universe.currency_minimums.get("USD", 5.0))
    
    def get_pair_metadata(self, pair: str) -> Optional[Dict]:
        """Get metadata for a trading pair."""
        return self.pair_metadata.get(pair)
