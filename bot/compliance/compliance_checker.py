"""
Compliance Checker - Pre-trade validation and compliance enforcement
"""

from typing import Dict, List, Optional
from datetime import datetime
from loguru import logger
from .asset_filter import AssetFilter


class ComplianceChecker:
    """
    Comprehensive compliance checking system.
    Validates all trades against regulatory requirements and internal policies.
    """
    
    def __init__(self, asset_filter: AssetFilter):
        self.asset_filter = asset_filter
        self.violation_log: List[Dict] = []
        
        logger.info("ComplianceChecker initialized")
    
    def check_order(
        self,
        pair: str,
        side: str,
        size: float,
        price: Optional[float] = None,
        account_balance: Optional[float] = None
    ) -> tuple[bool, str]:
        """
        Comprehensive pre-trade compliance check.
        
        Args:
            pair: Trading pair symbol
            side: 'buy' or 'sell'
            size: Order size in base currency
            price: Order price (if limit order)
            account_balance: Current account balance
            
        Returns:
            Tuple of (is_compliant, reason)
        """
        # Check 1: Asset restriction compliance
        if not self.asset_filter.validate_order(pair):
            reason = f"Asset restriction violation: {pair}"
            self._log_violation(pair, side, size, reason)
            return False, reason
        
        # Check 2: Order size validation
        if size <= 0:
            reason = f"Invalid order size: {size}"
            self._log_violation(pair, side, size, reason)
            return False, reason
        
        # Check 3: Side validation
        if side not in ['buy', 'sell']:
            reason = f"Invalid order side: {side}"
            self._log_violation(pair, side, size, reason)
            return False, reason
        
        # Check 4: Price validation (if limit order)
        if price is not None and price <= 0:
            reason = f"Invalid order price: {price}"
            self._log_violation(pair, side, size, reason)
            return False, reason
        
        # Check 5: Account balance check (if provided)
        if account_balance is not None and side == 'buy':
            estimated_cost = size * (price if price else 0)
            if estimated_cost > account_balance:
                reason = f"Insufficient balance: need ${estimated_cost:.2f}, have ${account_balance:.2f}"
                self._log_violation(pair, side, size, reason)
                return False, reason
        
        # All checks passed
        logger.debug(f"Compliance check PASSED: {side} {size} {pair}")
        return True, "Compliant"
    
    def check_position_limits(
        self,
        pair: str,
        new_position_size: float,
        current_positions: Dict[str, float],
        max_position_pct: float,
        max_single_asset_pct: float,
        portfolio_value: float
    ) -> tuple[bool, str]:
        """
        Check position concentration limits.
        
        Args:
            pair: Trading pair symbol
            new_position_size: Proposed position size in USD
            current_positions: Dict of {pair: position_size_usd}
            max_position_pct: Maximum % for single position
            max_single_asset_pct: Maximum % for single asset
            portfolio_value: Total portfolio value in USD
            
        Returns:
            Tuple of (is_compliant, reason)
        """
        # Check single position limit
        position_pct = (new_position_size / portfolio_value) * 100
        if position_pct > max_position_pct:
            reason = (
                f"Position size {position_pct:.2f}% exceeds limit {max_position_pct:.2f}%"
            )
            logger.warning(reason)
            return False, reason
        
        # Check single asset concentration
        # Calculate total exposure to this asset including new position
        base_asset = pair.split('/')[0] if '/' in pair else pair.split('-')[0]
        total_asset_exposure = new_position_size
        
        for existing_pair, position_size in current_positions.items():
            existing_base = existing_pair.split('/')[0] if '/' in existing_pair else existing_pair.split('-')[0]
            if existing_base == base_asset:
                total_asset_exposure += position_size
        
        asset_pct = (total_asset_exposure / portfolio_value) * 100
        if asset_pct > max_single_asset_pct:
            reason = (
                f"Asset concentration {asset_pct:.2f}% exceeds limit {max_single_asset_pct:.2f}%"
            )
            logger.warning(reason)
            return False, reason
        
        return True, "Position limits compliant"
    
    def check_daily_limits(
        self,
        proposed_trade_size: float,
        daily_volume: float,
        max_daily_volume_pct: float,
        portfolio_value: float
    ) -> tuple[bool, str]:
        """
        Check daily trading volume limits.
        
        Args:
            proposed_trade_size: Size of proposed trade in USD
            daily_volume: Total USD volume traded today
            max_daily_volume_pct: Maximum % of portfolio to trade daily
            portfolio_value: Total portfolio value in USD
            
        Returns:
            Tuple of (is_compliant, reason)
        """
        total_daily_volume = daily_volume + proposed_trade_size
        daily_volume_pct = (total_daily_volume / portfolio_value) * 100
        
        if daily_volume_pct > max_daily_volume_pct:
            reason = (
                f"Daily volume {daily_volume_pct:.2f}% would exceed limit "
                f"{max_daily_volume_pct:.2f}%"
            )
            logger.warning(reason)
            return False, reason
        
        return True, "Daily limits compliant"
    
    def _log_violation(self, pair: str, side: str, size: float, reason: str):
        """Log a compliance violation for audit trail"""
        violation = {
            'timestamp': datetime.now().isoformat(),
            'pair': pair,
            'side': side,
            'size': size,
            'reason': reason
        }
        self.violation_log.append(violation)
        
        logger.error(f"COMPLIANCE VIOLATION: {reason} | {side} {size} {pair}")
        
        # Keep only last 1000 violations
        if len(self.violation_log) > 1000:
            self.violation_log = self.violation_log[-1000:]
    
    def get_violation_history(self, hours: int = 24) -> List[Dict]:
        """Get recent compliance violations"""
        cutoff = datetime.now().timestamp() - (hours * 3600)
        recent = [
            v for v in self.violation_log
            if datetime.fromisoformat(v['timestamp']).timestamp() > cutoff
        ]
        return recent
    
    def get_restricted_assets(self) -> List[str]:
        """Get list of all restricted assets"""
        return sorted(self.asset_filter.get_restricted_assets())
