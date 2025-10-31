"""
Risk management and circuit breaker system.
Monitors positions, drawdowns, and trading limits.
"""
import pandas as pd
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import deque
from loguru import logger

from ..config.settings import TradingConfig


class RiskManager:
    """Manages risk limits and circuit breakers"""
    
    def __init__(self, config: TradingConfig):
        self.config = config
        self.portfolio_size = config.portfolio_size_usd
        
        # Track daily/weekly metrics
        self.daily_trades: deque = deque(maxlen=1000)
        self.daily_volume = 0.0
        self.daily_start_capital = self.portfolio_size
        self.daily_pnl = 0.0
        self.weekly_pnl = 0.0
        
        # Circuit breaker states
        self.circuit_breaker_active = False
        self.circuit_breaker_until: Optional[datetime] = None
        self.consecutive_losses = 0
        
        # Position tracking
        self.open_positions: Dict[str, Dict] = {}
        self.position_history: List[Dict] = []
        
        # Daily reset tracking
        self.last_reset_date = datetime.now().date()
    
    def check_pre_trade_limits(self, pair: str, order_size_usd: float,
                              side: str) -> tuple[bool, str]:
        """
        Check if trade is allowed under risk limits.
        
        Returns:
            (is_allowed, error_message)
        """
        # Reset daily metrics if new day
        self._reset_if_new_day()
        
        # Check circuit breaker
        if self.circuit_breaker_active:
            if self.circuit_breaker_until and datetime.now() < self.circuit_breaker_until:
                return False, "Circuit breaker active"
            else:
                self.circuit_breaker_active = False
                logger.info("Circuit breaker deactivated")
        
        # Check maximum position size
        max_position_usd = (self.portfolio_size * self.config.max_position_pct) / 100.0
        if order_size_usd > max_position_usd:
            return False, f"Order size {order_size_usd:.2f} exceeds maximum {max_position_usd:.2f}"
        
        # Check daily volume limit
        max_daily_volume = (self.portfolio_size * self.config.max_daily_volume_pct) / 100.0
        if self.daily_volume + order_size_usd > max_daily_volume:
            return False, f"Daily volume limit would be exceeded"
        
        # Check maximum concurrent positions
        if side == 'buy':
            current_positions = len([p for p in self.open_positions.values() if p.get('size', 0) > 0])
            if current_positions >= self.config.max_concurrent_positions:
                return False, f"Maximum concurrent positions ({self.config.max_concurrent_positions}) reached"
        
        # Check consecutive losses
        if self.consecutive_losses >= self.config.max_consecutive_losses:
            self._activate_circuit_breaker(
                f"Maximum consecutive losses ({self.config.max_consecutive_losses}) reached"
            )
            return False, "Consecutive loss limit reached, circuit breaker activated"
        
        # Check daily drawdown
        current_capital = self.daily_start_capital + self.daily_pnl
        drawdown_pct = ((self.daily_start_capital - current_capital) / self.daily_start_capital) * 100
        
        if drawdown_pct >= self.config.max_daily_drawdown_pct:
            self._activate_circuit_breaker(f"Daily drawdown limit ({drawdown_pct:.2f}%) reached")
            return False, f"Daily drawdown limit exceeded: {drawdown_pct:.2f}%"
        
        return True, ""
    
    def record_trade(self, pair: str, side: str, size_usd: float, price: float,
                    fees: float = 0.0, pnl: float = 0.0):
        """Record a completed trade"""
        trade_record = {
            'timestamp': datetime.now(),
            'pair': pair,
            'side': side,
            'size_usd': size_usd,
            'price': price,
            'fees': fees,
            'pnl': pnl
        }
        
        self.daily_trades.append(trade_record)
        self.daily_volume += size_usd
        self.daily_pnl += pnl
        
        # Update consecutive losses
        if pnl < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0
        
        # Update position tracking
        if side == 'buy':
            if pair not in self.open_positions:
                self.open_positions[pair] = {
                    'size': 0.0,
                    'entry_price': 0.0,
                    'entry_time': datetime.now()
                }
            self.open_positions[pair]['size'] += (size_usd / price)
            if self.open_positions[pair]['entry_price'] == 0:
                self.open_positions[pair]['entry_price'] = price
        
        elif side == 'sell':
            if pair in self.open_positions:
                self.open_positions[pair]['size'] -= (size_usd / price)
                if self.open_positions[pair]['size'] <= 0:
                    del self.open_positions[pair]
        
        logger.info(f"Recorded trade: {side} {size_usd:.2f} USD {pair} | P&L: {pnl:.2f} | Daily: {self.daily_pnl:.2f}")
    
    def get_position_concentration(self) -> Dict[str, float]:
        """Get position concentration percentages"""
        total_value = 0.0
        position_values = {}
        
        for pair, position in self.open_positions.items():
            # Would need current price to calculate accurately
            # For now, use entry value as approximation
            value = position.get('size', 0) * position.get('entry_price', 0)
            position_values[pair] = value
            total_value += value
        
        concentrations = {}
        if total_value > 0:
            for pair, value in position_values.items():
                concentrations[pair] = (value / self.portfolio_size) * 100
        
        return concentrations
    
    def check_position_concentration(self, pair: str, new_position_value: float) -> bool:
        """Check if new position would exceed concentration limits"""
        concentrations = self.get_position_concentration()
        current_concentration = concentrations.get(pair, 0.0)
        
        new_concentration = (new_position_value / self.portfolio_size) * 100
        max_concentration = 25.0  # 25% max per asset
        
        return (current_concentration + new_concentration) <= max_concentration
    
    def _activate_circuit_breaker(self, reason: str):
        """Activate circuit breaker"""
        self.circuit_breaker_active = True
        cooldown_minutes = self.config.circuit_breaker_cooldown_minutes if hasattr(self.config, 'circuit_breaker_cooldown_minutes') else 60
        self.circuit_breaker_until = datetime.now() + timedelta(minutes=cooldown_minutes)
        logger.error(f"Circuit breaker activated: {reason}. Cooldown until {self.circuit_breaker_until}")
    
    def _reset_if_new_day(self):
        """Reset daily metrics if new day"""
        today = datetime.now().date()
        if today > self.last_reset_date:
            logger.info("Resetting daily metrics")
            self.daily_start_capital = self.portfolio_size + self.daily_pnl
            self.daily_volume = 0.0
            self.daily_pnl = 0.0
            self.consecutive_losses = 0
            self.last_reset_date = today
    
    def get_risk_metrics(self) -> Dict:
        """Get current risk metrics"""
        current_capital = self.daily_start_capital + self.daily_pnl
        drawdown_pct = ((self.daily_start_capital - current_capital) / self.daily_start_capital) * 100 if self.daily_start_capital > 0 else 0.0
        
        return {
            'portfolio_size': self.portfolio_size,
            'daily_volume': self.daily_volume,
            'daily_volume_pct': (self.daily_volume / self.portfolio_size) * 100,
            'daily_pnl': self.daily_pnl,
            'daily_drawdown_pct': drawdown_pct,
            'consecutive_losses': self.consecutive_losses,
            'open_positions': len(self.open_positions),
            'circuit_breaker_active': self.circuit_breaker_active,
            'circuit_breaker_until': self.circuit_breaker_until.isoformat() if self.circuit_breaker_until else None
        }
