"""
Threshold and limit definitions for risk management and trading decisions.
"""
from typing import Dict
from dataclasses import dataclass


@dataclass
class TradingThresholds:
    """Trading decision thresholds"""
    min_confidence: float = 0.55
    min_edge_bps: float = 20.0
    min_fee_multiplier: float = 3.0
    max_spread_bps: float = 100.0
    max_latency_ms: float = 500.0
    min_liquidity_usd: float = 10000.0


@dataclass
class RiskThresholds:
    """Risk management thresholds"""
    max_position_pct: float = 3.0
    max_daily_volume_pct: float = 15.0
    max_drawdown_daily_pct: float = 10.0
    max_drawdown_weekly_pct: float = 20.0
    max_concurrent_positions: int = 5
    max_consecutive_losses: int = 5


@dataclass
class SystemThresholds:
    """System operation thresholds"""
    websocket_timeout_seconds: int = 30
    api_timeout_seconds: int = 30
    max_reconnect_attempts: int = 10
    health_check_interval_seconds: int = 30
    data_validation_tolerance_pct: float = 5.0


class ThresholdManager:
    """Manages all thresholds and limits"""
    
    def __init__(self, risk_mode: str = "balanced"):
        self.risk_mode = risk_mode
        self.trading = TradingThresholds()
        self.risk = RiskThresholds()
        self.system = SystemThresholds()
        self._apply_risk_mode()
    
    def _apply_risk_mode(self):
        """Apply risk mode specific thresholds"""
        if self.risk_mode == "conservative":
            self.trading.min_confidence = 0.65
            self.risk.max_position_pct = 1.0
            self.risk.max_daily_volume_pct = 5.0
            self.risk.max_drawdown_daily_pct = 5.0
        elif self.risk_mode == "aggressive":
            self.trading.min_confidence = 0.55
            self.risk.max_position_pct = 5.0
            self.risk.max_daily_volume_pct = 25.0
            self.risk.max_drawdown_daily_pct = 15.0
        else:  # balanced
            self.trading.min_confidence = 0.60
            self.risk.max_position_pct = 3.0
            self.risk.max_daily_volume_pct = 15.0
            self.risk.max_drawdown_daily_pct = 10.0
    
    def get_trading_thresholds(self) -> Dict:
        """Get trading thresholds as dictionary"""
        return {
            "min_confidence": self.trading.min_confidence,
            "min_edge_bps": self.trading.min_edge_bps,
            "min_fee_multiplier": self.trading.min_fee_multiplier,
            "max_spread_bps": self.trading.max_spread_bps,
            "max_latency_ms": self.trading.max_latency_ms,
            "min_liquidity_usd": self.trading.min_liquidity_usd,
        }
    
    def get_risk_thresholds(self) -> Dict:
        """Get risk thresholds as dictionary"""
        return {
            "max_position_pct": self.risk.max_position_pct,
            "max_daily_volume_pct": self.risk.max_daily_volume_pct,
            "max_drawdown_daily_pct": self.risk.max_drawdown_daily_pct,
            "max_drawdown_weekly_pct": self.risk.max_drawdown_weekly_pct,
            "max_concurrent_positions": self.risk.max_concurrent_positions,
            "max_consecutive_losses": self.risk.max_consecutive_losses,
        }
    
    def get_system_thresholds(self) -> Dict:
        """Get system thresholds as dictionary"""
        return {
            "websocket_timeout_seconds": self.system.websocket_timeout_seconds,
            "api_timeout_seconds": self.system.api_timeout_seconds,
            "max_reconnect_attempts": self.system.max_reconnect_attempts,
            "health_check_interval_seconds": self.system.health_check_interval_seconds,
            "data_validation_tolerance_pct": self.system.data_validation_tolerance_pct,
        }
