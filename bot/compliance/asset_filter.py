"""
Asset Filter - US North Carolina Compliance
Enforces restricted asset list and validates trading pairs.
"""

from typing import Set, List
from loguru import logger


class AssetFilter:
    """
    Enforces asset restrictions for US North Carolina compliance.
    Hard-coded restricted asset list that cannot be traded.
    """
    
    # US North Carolina Restricted Assets
    # This list is IMMUTABLE and represents assets that cannot be traded
    # in North Carolina due to regulatory restrictions
    RESTRICTED_ASSETS: Set[str] = {
        'ACA', 'AGLD', 'ALICE', 'ANLOG', 'ASTR', 'ATLAS', 'AUDIO', 'AVAAI',
        'C98', 'CFG', 'CLOUD', 'CSM', 'DBR', 'DUCK', 'FHE', 'GLMR', 'GRASS',
        'HDX', 'INTR', 'K', 'KERNEL', 'KIN', 'KMNO', 'L3', 'LAYER', 'LMWR',
        'MC', 'MV', 'NIL', 'NMR', 'NODL', 'NYM', 'OMNI', 'ORCA', 'OXY',
        'PARA', 'PERP', 'PORTAL', 'PRCL', 'PSTAKE', 'RAY', 'REQ', 'REZ',
        'ROOK', 'RSR', 'SAMO', 'SDN', 'SPICE', 'STEP', 'SWARMS', 'SWELL',
        'TEER', 'TERM', 'VVV', 'WAL', 'WEN', 'WOO', 'XRT', 'YGG', 'ZEX'
    }
    
    def __init__(self):
        """Initialize asset filter with restricted assets"""
        self.restricted_count = len(self.RESTRICTED_ASSETS)
        logger.info(
            f"AssetFilter initialized with {self.restricted_count} restricted assets "
            f"for US North Carolina compliance"
        )
        logger.debug(f"Restricted assets: {sorted(self.RESTRICTED_ASSETS)}")
    
    def is_compliant(self, asset: str) -> bool:
        """
        Check if an asset is compliant (not restricted).
        
        Args:
            asset: Asset symbol to check
            
        Returns:
            True if asset is compliant (tradeable), False if restricted
        """
        # Normalize asset symbol (uppercase, strip whitespace)
        asset_normalized = asset.strip().upper()
        
        # Check against restricted list
        is_allowed = asset_normalized not in self.RESTRICTED_ASSETS
        
        if not is_allowed:
            logger.warning(
                f"Asset {asset_normalized} is RESTRICTED for US North Carolina trading"
            )
        
        return is_allowed
    
    def filter_pairs(self, pairs: List[str]) -> List[str]:
        """
        Filter a list of trading pairs, removing any with restricted assets.
        
        Args:
            pairs: List of trading pair symbols (e.g., ['BTC/USD', 'ETH/USD'])
            
        Returns:
            Filtered list containing only compliant pairs
        """
        compliant_pairs = []
        
        for pair in pairs:
            # Extract base asset (before '/')
            parts = pair.split('/')
            if len(parts) < 2:
                # Try other delimiters
                parts = pair.split('-')
            
            if len(parts) < 2:
                logger.warning(f"Cannot parse pair format: {pair}")
                continue
            
            base_asset = parts[0].strip().upper()
            
            if self.is_compliant(base_asset):
                compliant_pairs.append(pair)
            else:
                logger.info(f"Excluding pair {pair} due to restricted asset {base_asset}")
        
        logger.info(
            f"Filtered {len(pairs)} pairs → {len(compliant_pairs)} compliant pairs"
        )
        
        return compliant_pairs
    
    def validate_order(self, pair: str) -> bool:
        """
        Validate that an order can be placed for this pair.
        This is a final safety check before order submission.
        
        Args:
            pair: Trading pair symbol
            
        Returns:
            True if order is allowed, False if blocked
        """
        # Extract base asset
        parts = pair.replace('/', '-').split('-')
        if len(parts) < 2:
            logger.error(f"Invalid pair format for order validation: {pair}")
            return False
        
        base_asset = parts[0].strip().upper()
        
        if not self.is_compliant(base_asset):
            logger.error(
                f"ORDER BLOCKED: Asset {base_asset} is restricted for NC trading. "
                f"Pair: {pair}"
            )
            return False
        
        return True
    
    def get_restricted_assets(self) -> Set[str]:
        """Get the complete list of restricted assets"""
        return self.RESTRICTED_ASSETS.copy()
    
    def get_restriction_reason(self, asset: str) -> str:
        """
        Get human-readable reason for asset restriction.
        
        Args:
            asset: Asset symbol
            
        Returns:
            Explanation string
        """
        asset_normalized = asset.strip().upper()
        
        if asset_normalized in self.RESTRICTED_ASSETS:
            return (
                f"Asset {asset_normalized} is restricted for trading in "
                f"US North Carolina due to regulatory requirements."
            )
        else:
            return f"Asset {asset_normalized} is compliant and tradeable."
