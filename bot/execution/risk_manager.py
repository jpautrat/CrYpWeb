"""Risk management and position limits."""
from typing import Dict, List
from datetime import datetime, timedelta
from loguru import logger

from bot.config.settings import settings


class RiskManager:
    """Manages risk limits and circuit breakers."""
    
    def __init__(self):
        self.positions: Dict[str, Dict] = {}
        self.daily_volume = 0.0
        self.daily_start = datetime.utcnow().replace(hour=0, minute=0, second=0)
        self.consecutive_losses = 0
        self.starting_balance = settings.trading.portfolio_size_usd
        self.current_balance = self.starting_balance
    
    def can_trade(self, pair: str, size_usd: float) -> tuple[bool, str]:
        """Check if trade is allowed."""
        # Check daily volume limit
        if datetime.utcnow().date() != self.daily_start.date():
            self.daily_volume = 0.0
            self.daily_start = datetime.utcnow().replace(hour=0, minute=0, second=0)
        
        max_daily = settings.trading.portfolio_size_usd * (
            settings.trading.get_risk_param("max_daily_volume_pct") / 100.0
        )
        
        if self.daily_volume + size_usd > max_daily:
            return False, "Daily volume limit exceeded"
        
        # Check position concentration
        max_position_pct = settings.trading.get_risk_param("max_position_pct")
        total_exposure = sum(p.get('size_usd', 0) for p in self.positions.values())
        if total_exposure + size_usd > settings.trading.portfolio_size_usd * (max_position_pct / 100.0) * settings.trading.max_concurrent_positions:
            return False, "Position concentration limit exceeded"
        
        # Check consecutive losses
        if self.consecutive_losses >= settings.trading.max_consecutive_losses:
            return False, "Circuit breaker: too many consecutive losses"
        
        # Check drawdown
        drawdown = (self.starting_balance - self.current_balance) / self.starting_balance * 100
        if drawdown >= settings.trading.max_daily_drawdown_pct:
            return False, f"Circuit breaker: drawdown {drawdown:.2f}% exceeds limit"
        
        return True, ""
    
    def record_trade(self, pair: str, size_usd: float):
        """Record a trade."""
        self.daily_volume += size_usd
        self.positions[pair] = {'size_usd': size_usd, 'opened_at': datetime.utcnow()}
    
    def record_fill(self, pair: str, pnl: float):
        """Record a fill and update PnL."""
        if pnl < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0
        
        self.current_balance += pnl
        if pair in self.positions:
            del self.positions[pair]
