"""
Compliance checker for pre-trade validation.
Ensures all trades meet regulatory and policy requirements.
"""
from typing import Dict, List, tuple
from datetime import datetime
from loguru import logger

from .asset_filter import AssetFilter
from ..config.universe_manager import UniverseManager


class ComplianceChecker:
    """Checks compliance before placing orders"""
    
    def __init__(self, asset_filter: AssetFilter, universe_manager: UniverseManager):
        self.asset_filter = asset_filter
        self.universe_manager = universe_manager
        self.violations_log: List[Dict] = []
    
    def check_order(self, pair: str, order_details: Dict) -> tuple[bool, str]:
        """
        Check if order complies with all rules.
        
        Returns:
            (is_compliant, error_message)
        """
        # Check asset filter
        is_allowed, reason = self.asset_filter.is_allowed(pair)
        if not is_allowed:
            self._log_violation(pair, "asset_filter", reason)
            return False, f"Asset compliance violation: {reason}"
        
        # Check universe eligibility
        is_valid, error_msg = self.universe_manager.validate_pair(pair)
        if not is_valid:
            self._log_violation(pair, "universe", error_msg)
            return False, f"Universe compliance violation: {error_msg}"
        
        # Check minimum order size
        pair_metadata = self.universe_manager.get_pair_metadata(pair)
        ordermin = pair_metadata.get('ordermin', 0)
        
        if ordermin > 0:
            order_size = order_details.get('size', 0)
            if order_size < ordermin:
                self._log_violation(pair, "min_order", f"Order size {order_size} < minimum {ordermin}")
                return False, f"Order size below minimum: {order_size} < {ordermin}"
        
        return True, ""
    
    def _log_violation(self, pair: str, violation_type: str, reason: str):
        """Log compliance violation"""
        violation = {
            'timestamp': datetime.now(),
            'pair': pair,
            'violation_type': violation_type,
            'reason': reason
        }
        self.violations_log.append(violation)
        logger.error(f"Compliance violation: {pair} - {violation_type}: {reason}")
    
    def get_violations(self, limit: int = 100) -> List[Dict]:
        """Get recent compliance violations"""
        return self.violations_log[-limit:]
