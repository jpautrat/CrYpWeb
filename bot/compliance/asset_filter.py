"""
Asset filtering for US-NC compliance.
Enforces exclusion list and validates assets before trading.
"""
from typing import List, Set
from loguru import logger

from ..config.settings import UniverseConfig


class AssetFilter:
    """Filters assets based on compliance rules"""
    
    def __init__(self, universe_config: UniverseConfig):
        self.universe_config = universe_config
        self.restricted_base: Set[str] = set(universe_config.restricted_assets)
        self.restricted_quote: Set[str] = set()  # Can be extended
    
    def is_allowed(self, pair: str) -> tuple[bool, str]:
        """
        Check if a pair is allowed for trading.
        
        Returns:
            (is_allowed, reason)
        """
        # Extract base asset
        quote_currency = self.universe_config.base_quote
        base_asset = pair.replace(quote_currency, "").replace("/", "")
        
        # Check if base asset is restricted
        if base_asset in self.restricted_base:
            return False, f"Base asset {base_asset} is on restricted list"
        
        # Check if quote asset is restricted
        if quote_currency in self.restricted_quote:
            return False, f"Quote asset {quote_currency} is restricted"
        
        return True, ""
    
    def filter_pairs(self, pairs: List[str]) -> List[str]:
        """Filter list of pairs to only allowed ones"""
        allowed = []
        
        for pair in pairs:
            is_allowed, reason = self.is_allowed(pair)
            if is_allowed:
                allowed.append(pair)
            else:
                logger.debug(f"Filtered out {pair}: {reason}")
        
        return allowed
    
    def get_restricted_assets(self) -> List[str]:
        """Get list of restricted assets"""
        return sorted(list(self.restricted_base))
