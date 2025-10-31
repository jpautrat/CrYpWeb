"""
Asset filtering for US-NC compliance.
Hard-coded exclusion list with runtime verification.
"""
from typing import Set, List
from loguru import logger

from bot.config.settings import settings


class AssetFilter:
    """Filters assets based on compliance rules."""
    
    def __init__(self):
        """Initialize asset filter with restricted list."""
        self.restricted_assets: Set[str] = set(settings.universe.restricted_assets)
        logger.info(f"Initialized asset filter with {len(self.restricted_assets)} restricted assets")
    
    def is_tradeable(self, pair: str) -> bool:
        """
        Check if a trading pair is tradeable.
        
        Args:
            pair: Trading pair (e.g., 'BTC/USD' or 'ETH/USD')
            
        Returns:
            True if tradeable, False if restricted
        """
        # Extract base asset
        if "/" in pair:
            base_asset = pair.split("/")[0]
        else:
            # Handle Kraken format
            base_asset = pair.replace("USD", "").replace("EUR", "").replace("XBT", "BTC")
        
        # Check against restricted list
        if base_asset in self.restricted_assets:
            logger.warning(f"Asset {base_asset} is restricted for US-NC compliance")
            return False
        
        return True
    
    def filter_pairs(self, pairs: List[str]) -> List[str]:
        """
        Filter list of pairs to only tradeable ones.
        
        Args:
            pairs: List of trading pairs
            
        Returns:
            Filtered list of tradeable pairs
        """
        return [pair for pair in pairs if self.is_tradeable(pair)]
    
    def validate_order(self, pair: str) -> tuple[bool, str]:
        """
        Validate if an order can be placed for a pair.
        
        Args:
            pair: Trading pair
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not self.is_tradeable(pair):
            return False, f"Asset is restricted for US-NC compliance: {pair}"
        
        return True, ""
