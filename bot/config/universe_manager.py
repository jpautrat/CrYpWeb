"""
Universe management for selecting and maintaining tradeable asset pairs.
Implements US-NC compliance filtering and dynamic universe updates.
"""
from typing import List, Dict, Set
from datetime import datetime, timedelta
import pandas as pd
from loguru import logger

from .settings import Settings
from ..core.rest_client import KrakenRESTClient


class UniverseManager:
    """Manages the tradeable asset universe with compliance filtering"""
    
    def __init__(self, settings: Settings, rest_client: KrakenRESTClient):
        self.settings = settings
        self.rest_client = rest_client
        self.universe_config = settings.get_universe_config()
        self.current_universe: List[str] = []
        self.last_refresh: datetime = None
        self.pair_metadata: Dict[str, Dict] = {}
        self.restricted_base: Set[str] = set(self.universe_config.restricted_assets)
        self.restricted_quote: Set[str] = set()  # Can be extended if needed
    
    def refresh_universe(self) -> List[str]:
        """
        Refresh the trading universe based on volume and compliance rules.
        Returns list of eligible pair symbols.
        """
        try:
            logger.info("Refreshing trading universe...")
            
            # Get all tradable pairs from Kraken
            all_pairs = self.rest_client.get_tradable_pairs()
            if not all_pairs:
                logger.error("Failed to fetch tradable pairs from Kraken")
                return self.current_universe if self.current_universe else []
            
            # Filter for quote currency
            quote_pairs = [
                pair for pair in all_pairs 
                if pair.endswith(self.universe_config.base_quote)
            ]
            
            logger.info(f"Found {len(quote_pairs)} pairs with {self.universe_config.base_quote} quote")
            
            # Get 24h volume data
            volume_data = []
            for pair in quote_pairs:
                try:
                    ticker = self.rest_client.get_ticker(pair)
                    if ticker:
                        volume_24h = float(ticker.get('v', [0])[1]) * float(ticker.get('c', [0])[0])
                        volume_data.append({
                            'pair': pair,
                            'volume_24h_usd': volume_24h,
                            'last_price': float(ticker.get('c', [0])[0])
                        })
                except Exception as e:
                    logger.warning(f"Failed to get ticker for {pair}: {e}")
                    continue
            
            # Filter by minimum volume
            filtered = [
                p for p in volume_data 
                if p['volume_24h_usd'] >= self.universe_config.min_daily_volume_usd
            ]
            
            # Apply compliance filtering
            compliant_pairs = self._filter_compliance(filtered)
            
            # Sort by volume and take top N
            compliant_pairs.sort(key=lambda x: x['volume_24h_usd'], reverse=True)
            top_pairs = compliant_pairs[:self.universe_config.universe_size]
            
            # Extract pair symbols
            new_universe = [p['pair'] for p in top_pairs]
            
            # Get pair metadata for minimum order sizes
            for pair in new_universe:
                try:
                    pair_info = self.rest_client.get_pair_info(pair)
                    if pair_info:
                        self.pair_metadata[pair] = {
                            'ordermin': float(pair_info.get('ordermin', 0)),
                            'lot_decimals': int(pair_info.get('lot_decimals', 0)),
                            'pair_decimals': int(pair_info.get('pair_decimals', 0)),
                            'volume_24h_usd': next(
                                (p['volume_24h_usd'] for p in top_pairs if p['pair'] == pair), 
                                0
                            )
                        }
                except Exception as e:
                    logger.warning(f"Failed to get metadata for {pair}: {e}")
            
            self.current_universe = new_universe
            self.last_refresh = datetime.now()
            
            logger.info(f"Universe refreshed: {len(new_universe)} pairs selected")
            logger.info(f"Universe pairs: {', '.join(new_universe)}")
            
            return new_universe
        
        except Exception as e:
            logger.error(f"Error refreshing universe: {e}")
            return self.current_universe if self.current_universe else []
    
    def _filter_compliance(self, pairs: List[Dict]) -> List[Dict]:
        """
        Filter pairs based on US-NC compliance rules.
        Excludes any pair containing restricted base or quote assets.
        """
        compliant = []
        
        for pair_data in pairs:
            pair = pair_data['pair']
            
            # Extract base asset (everything before the quote currency)
            base_asset = pair.replace(self.universe_config.base_quote, "").replace("/", "")
            
            # Check if base asset is restricted
            if base_asset in self.restricted_base:
                logger.warning(f"Excluding restricted pair: {pair} (base: {base_asset})")
                continue
            
            # Check if quote asset is restricted (unlikely but check anyway)
            if self.universe_config.base_quote in self.restricted_quote:
                logger.warning(f"Excluding pair with restricted quote: {pair}")
                continue
            
            compliant.append(pair_data)
        
        return compliant
    
    def get_universe(self) -> List[str]:
        """Get current universe, refreshing if needed"""
        if not self.current_universe or self._should_refresh():
            return self.refresh_universe()
        return self.current_universe
    
    def _should_refresh(self) -> bool:
        """Check if universe should be refreshed"""
        if not self.last_refresh:
            return True
        
        refresh_interval = timedelta(minutes=self.universe_config.universe_refresh_minutes)
        return datetime.now() - self.last_refresh > refresh_interval
    
    def get_pair_metadata(self, pair: str) -> Dict:
        """Get metadata for a specific pair"""
        if pair not in self.pair_metadata:
            try:
                pair_info = self.rest_client.get_pair_info(pair)
                if pair_info:
                    self.pair_metadata[pair] = {
                        'ordermin': float(pair_info.get('ordermin', 0)),
                        'lot_decimals': int(pair_info.get('lot_decimals', 0)),
                        'pair_decimals': int(pair_info.get('pair_decimals', 0)),
                    }
            except Exception as e:
                logger.error(f"Failed to get metadata for {pair}: {e}")
        
        return self.pair_metadata.get(pair, {})
    
    def is_eligible(self, pair: str) -> bool:
        """Check if a pair is eligible for trading"""
        return pair in self.get_universe()
    
    def validate_pair(self, pair: str) -> tuple[bool, str]:
        """
        Validate if a pair can be traded.
        Returns (is_valid, error_message)
        """
        # Check if in universe
        if not self.is_eligible(pair):
            return False, f"Pair {pair} not in current trading universe"
        
        # Check compliance
        base_asset = pair.replace(self.universe_config.base_quote, "").replace("/", "")
        if base_asset in self.restricted_base:
            return False, f"Pair {pair} contains restricted asset {base_asset}"
        
        return True, ""
