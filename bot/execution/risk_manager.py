"""
Risk Manager - Comprehensive risk management and circuit breakers
"""

from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
from collections import deque
from loguru import logger


class RiskManager:
    """
    Manages trading risk with multiple layers of protection.
    Implements drawdown limits, consecutive loss protection, and circuit breakers.
    """
    
    def __init__(
        self,
        portfolio_size_usd: float,
        max_daily_drawdown_pct: float = 10.0,
        max_weekly_drawdown_pct: float = 20.0,
        max_consecutive_losses: int = 5,
        circuit_breaker_cooldown_minutes: int = 60
    ):
        """
        Initialize risk manager.
        
        Args:
            portfolio_size_usd: Total portfolio value
            max_daily_drawdown_pct: Maximum daily drawdown %
            max_weekly_drawdown_pct: Maximum weekly drawdown %
            max_consecutive_losses: Max losses before cooldown
            circuit_breaker_cooldown_minutes: Cooldown duration
        """
        self.portfolio_size_usd = portfolio_size_usd
        self.max_daily_drawdown_pct = max_daily_drawdown_pct
        self.max_weekly_drawdown_pct = max_weekly_drawdown_pct
        self.max_consecutive_losses = max_consecutive_losses
        self.circuit_breaker_cooldown_minutes = circuit_breaker_cooldown_minutes
        
        # Performance tracking
        self.daily_pnl = 0.0
        self.weekly_pnl = 0.0
        self.daily_start_value = portfolio_size_usd
        self.weekly_start_value = portfolio_size_usd
        
        # Loss tracking
        self.consecutive_losses = 0
        self.trade_history = deque(maxlen=1000)
        
        # Circuit breaker state
        self.circuit_breaker_active = False
        self.circuit_breaker_until: Optional[datetime] = None
        self.circuit_breaker_reason = ""
        
        logger.info(
            f"RiskManager initialized: max_daily_dd={max_daily_drawdown_pct}%, "
            f"max_weekly_dd={max_weekly_drawdown_pct}%"
        )
    
    def check_trade_allowed(
        self,
        pair: str,
        size_usd: float,
        side: str
    ) -> Tuple[bool, str]:
        """
        Check if a trade is allowed under current risk constraints.
        
        Args:
            pair: Trading pair
            size_usd: Trade size in USD
            side: 'buy' or 'sell'
            
        Returns:
            Tuple of (is_allowed, reason)
        """
        # Check circuit breaker
        if self.circuit_breaker_active:
            if datetime.now() < self.circuit_breaker_until:
                remaining = (self.circuit_breaker_until - datetime.now()).total_seconds() / 60
                return False, f"Circuit breaker active: {self.circuit_breaker_reason} (remaining: {remaining:.1f}min)"
            else:
                # Reset circuit breaker
                self._reset_circuit_breaker()
        
        # Check daily drawdown
        current_daily_dd_pct = abs(self.daily_pnl / self.daily_start_value * 100)
        if current_daily_dd_pct >= self.max_daily_drawdown_pct:
            self._activate_circuit_breaker("Daily drawdown limit exceeded")
            return False, f"Daily drawdown {current_daily_dd_pct:.2f}% >= {self.max_daily_drawdown_pct}%"
        
        # Check weekly drawdown
        current_weekly_dd_pct = abs(self.weekly_pnl / self.weekly_start_value * 100)
        if current_weekly_dd_pct >= self.max_weekly_drawdown_pct:
            self._activate_circuit_breaker("Weekly drawdown limit exceeded")
            return False, f"Weekly drawdown {current_weekly_dd_pct:.2f}% >= {self.max_weekly_drawdown_pct}%"
        
        # Check consecutive losses
        if self.consecutive_losses >= self.max_consecutive_losses:
            self._activate_circuit_breaker("Maximum consecutive losses exceeded")
            return False, f"Consecutive losses: {self.consecutive_losses}"
        
        # All checks passed
        return True, "Trade allowed"
    
    def record_trade_result(
        self,
        pair: str,
        side: str,
        pnl: float,
        size_usd: float
    ):
        """
        Record a trade result for risk tracking.
        
        Args:
            pair: Trading pair
            side: 'buy' or 'sell'
            pnl: Profit/loss in USD
            size_usd: Trade size in USD
        """
        # Update P&L
        self.daily_pnl += pnl
        self.weekly_pnl += pnl
        
        # Update consecutive losses
        if pnl < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0
        
        # Store trade history
        trade_record = {
            'timestamp': datetime.now(),
            'pair': pair,
            'side': side,
            'pnl': pnl,
            'size_usd': size_usd,
            'consecutive_losses': self.consecutive_losses
        }
        self.trade_history.append(trade_record)
        
        logger.info(
            f"Trade result: {pair} {side} PnL=${pnl:.4f} | "
            f"Daily PnL=${self.daily_pnl:.2f} | Consecutive losses: {self.consecutive_losses}"
        )
    
    def _activate_circuit_breaker(self, reason: str):
        """Activate circuit breaker"""
        self.circuit_breaker_active = True
        self.circuit_breaker_until = datetime.now() + timedelta(
            minutes=self.circuit_breaker_cooldown_minutes
        )
        self.circuit_breaker_reason = reason
        
        logger.critical(
            f"CIRCUIT BREAKER ACTIVATED: {reason} | "
            f"Cooldown until {self.circuit_breaker_until.strftime('%H:%M:%S')}"
        )
    
    def _reset_circuit_breaker(self):
        """Reset circuit breaker"""
        logger.info("Circuit breaker reset")
        self.circuit_breaker_active = False
        self.circuit_breaker_until = None
        self.circuit_breaker_reason = ""
    
    def reset_daily_metrics(self):
        """Reset daily metrics (call at start of new day)"""
        logger.info(f"Resetting daily metrics. Yesterday's PnL: ${self.daily_pnl:.2f}")
        self.daily_pnl = 0.0
        self.daily_start_value = self.portfolio_size_usd
    
    def reset_weekly_metrics(self):
        """Reset weekly metrics (call at start of new week)"""
        logger.info(f"Resetting weekly metrics. Last week's PnL: ${self.weekly_pnl:.2f}")
        self.weekly_pnl = 0.0
        self.weekly_start_value = self.portfolio_size_usd
    
    def get_risk_status(self) -> Dict:
        """Get comprehensive risk status"""
        daily_dd_pct = abs(self.daily_pnl / self.daily_start_value * 100) if self.daily_start_value > 0 else 0
        weekly_dd_pct = abs(self.weekly_pnl / self.weekly_start_value * 100) if self.weekly_start_value > 0 else 0
        
        return {
            'daily_pnl': self.daily_pnl,
            'weekly_pnl': self.weekly_pnl,
            'daily_drawdown_pct': daily_dd_pct,
            'weekly_drawdown_pct': weekly_dd_pct,
            'daily_limit_pct': self.max_daily_drawdown_pct,
            'weekly_limit_pct': self.max_weekly_drawdown_pct,
            'consecutive_losses': self.consecutive_losses,
            'max_consecutive_losses': self.max_consecutive_losses,
            'circuit_breaker_active': self.circuit_breaker_active,
            'circuit_breaker_reason': self.circuit_breaker_reason,
            'circuit_breaker_until': self.circuit_breaker_until.isoformat() if self.circuit_breaker_until else None,
            'trading_allowed': not self.circuit_breaker_active
        }
    
    def update_portfolio_size(self, new_size: float):
        """Update portfolio size (e.g., after deposits/withdrawals)"""
        logger.info(f"Portfolio size updated: ${self.portfolio_size_usd:.2f} → ${new_size:.2f}")
        self.portfolio_size_usd = new_size
