"""
Configuration Management for ML Kraken Pro Live Trader
Loads and validates all configuration parameters from environment variables.
"""

import os
from typing import List, Optional, Dict
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field, validator
from enum import Enum


class RiskMode(str, Enum):
    """Risk management modes"""
    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"


class LogLevel(str, Enum):
    """Logging levels"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"


class Settings(BaseSettings):
    """
    Main configuration class. All settings loaded from environment variables.
    Provides validation and type conversion.
    """
    
    # =============================================================================
    # TRADING CONFIGURATION
    # =============================================================================
    
    live_trading: int = Field(default=1, description="Must be 1 for live trading")
    portfolio_size_usd: float = Field(default=500.0, ge=200.0, le=10000.0)
    risk_mode: RiskMode = Field(default=RiskMode.BALANCED)
    
    # =============================================================================
    # KRAKEN API KEYS
    # =============================================================================
    
    kraken_key_1: str = Field(..., min_length=1)
    kraken_secret_1: str = Field(..., min_length=1)
    
    kraken_key_2: str = Field(..., min_length=1)
    kraken_secret_2: str = Field(..., min_length=1)
    
    kraken_key_3: str = Field(..., min_length=1)
    kraken_secret_3: str = Field(..., min_length=1)
    
    kraken_key_4: str = Field(..., min_length=1)
    kraken_secret_4: str = Field(..., min_length=1)
    
    kraken_key_5: str = Field(..., min_length=1)
    kraken_secret_5: str = Field(..., min_length=1)
    
    # =============================================================================
    # UNIVERSE CONFIGURATION
    # =============================================================================
    
    base_quote: str = Field(default="USD")
    universe_size: int = Field(default=10, ge=1, le=50)
    universe_refresh_minutes: int = Field(default=60, ge=15, le=1440)
    min_daily_volume_usd: float = Field(default=1_000_000.0)
    
    # =============================================================================
    # RISK MANAGEMENT
    # =============================================================================
    
    max_position_pct: float = Field(default=3.0, ge=0.1, le=10.0)
    max_daily_volume_pct: float = Field(default=15.0, ge=1.0, le=50.0)
    max_concurrent_positions: int = Field(default=5, ge=1, le=20)
    max_daily_drawdown_pct: float = Field(default=10.0, ge=1.0, le=50.0)
    max_weekly_drawdown_pct: float = Field(default=20.0, ge=5.0, le=80.0)
    edge_buffer_bps: float = Field(default=20.0, ge=0.0, le=200.0)
    fee_multiplier: float = Field(default=3.0, ge=1.0, le=10.0)
    max_single_asset_pct: float = Field(default=25.0, ge=10.0, le=100.0)
    
    # =============================================================================
    # PERFORMANCE TUNING
    # =============================================================================
    
    max_decision_latency_ms: int = Field(default=100, ge=10, le=1000)
    order_timeout_seconds: int = Field(default=30, ge=5, le=300)
    feature_lookback_seconds: int = Field(default=300, ge=60, le=3600)
    websocket_heartbeat_timeout: int = Field(default=30, ge=10, le=120)
    feature_cache_size_mb: int = Field(default=512, ge=64, le=4096)
    data_retention_days: int = Field(default=90, ge=7, le=365)
    
    # =============================================================================
    # MODEL CONFIGURATION
    # =============================================================================
    
    model_retrain_hours: int = Field(default=24, ge=1, le=168)
    training_window_days: int = Field(default=30, ge=7, le=180)
    validation_days: int = Field(default=1, ge=1, le=7)
    min_training_samples: int = Field(default=10000, ge=1000, le=1000000)
    confidence_threshold: float = Field(default=0.65, ge=0.5, le=0.95)
    confidence_threshold_aggressive: float = Field(default=0.55, ge=0.5, le=0.9)
    ensemble_models: bool = Field(default=True)
    enable_cross_asset_features: bool = Field(default=True)
    enable_temporal_features: bool = Field(default=True)
    enable_volatility_regimes: bool = Field(default=True)
    
    # =============================================================================
    # SYSTEM CONFIGURATION
    # =============================================================================
    
    log_level: LogLevel = Field(default=LogLevel.INFO)
    log_retention_days: int = Field(default=30, ge=1, le=365)
    enable_trade_logging: bool = Field(default=True)
    metrics_port: int = Field(default=8080, ge=1024, le=65535)
    health_check_port: int = Field(default=8081, ge=1024, le=65535)
    
    # =============================================================================
    # EMERGENCY CONTROLS
    # =============================================================================
    
    kill_switch_password: str = Field(..., min_length=8)
    circuit_breaker_cooldown_minutes: int = Field(default=60, ge=10, le=1440)
    max_consecutive_losses: int = Field(default=5, ge=2, le=20)
    enable_circuit_breakers: bool = Field(default=True)
    enable_spread_protection: bool = Field(default=True)
    spread_percentile_threshold: float = Field(default=95.0, ge=50.0, le=99.9)
    enable_latency_protection: bool = Field(default=True)
    max_api_latency_ms: int = Field(default=500, ge=100, le=5000)
    
    # =============================================================================
    # ADVANCED SETTINGS
    # =============================================================================
    
    maker_order_price_improvement_bps: float = Field(default=1.0, ge=0.0, le=10.0)
    iceberg_threshold_usd: float = Field(default=100.0, ge=10.0, le=1000.0)
    order_size_randomization_pct: float = Field(default=5.0, ge=0.0, le=20.0)
    requests_per_key_per_second: float = Field(default=1.0, ge=0.1, le=10.0)
    rate_limit_cooldown_seconds: int = Field(default=10, ge=1, le=60)
    orderbook_depth_levels: int = Field(default=10, ge=5, le=50)
    tick_data_buffer_size: int = Field(default=10000, ge=1000, le=100000)
    min_sharpe_ratio: float = Field(default=0.5, ge=0.0, le=5.0)
    min_model_accuracy: float = Field(default=0.55, ge=0.5, le=1.0)
    model_drift_threshold: float = Field(default=0.1, ge=0.01, le=0.5)
    enable_asset_restrictions: bool = Field(default=True)
    enable_audit_logging: bool = Field(default=True)
    audit_log_retention_days: int = Field(default=365, ge=30, le=3650)
    
    @validator('live_trading')
    def validate_live_trading(cls, v):
        """Ensure live trading is enabled"""
        if v != 1:
            raise ValueError("LIVE_TRADING must be 1 for production use")
        return v
    
    @property
    def api_keys(self) -> List[Dict[str, str]]:
        """Return list of API key dictionaries"""
        return [
            {"key": self.kraken_key_1, "secret": self.kraken_secret_1, "id": 1},
            {"key": self.kraken_key_2, "secret": self.kraken_secret_2, "id": 2},
            {"key": self.kraken_key_3, "secret": self.kraken_secret_3, "id": 3},
            {"key": self.kraken_key_4, "secret": self.kraken_secret_4, "id": 4},
            {"key": self.kraken_key_5, "secret": self.kraken_secret_5, "id": 5},
        ]
    
    @property
    def risk_parameters(self) -> Dict:
        """Get risk parameters based on selected risk mode"""
        if self.risk_mode == RiskMode.CONSERVATIVE:
            return {
                "max_position_pct": 1.0,
                "max_daily_volume_pct": 5.0,
                "confidence_threshold": 0.70,
                "max_concurrent_positions": 3,
            }
        elif self.risk_mode == RiskMode.AGGRESSIVE:
            return {
                "max_position_pct": 5.0,
                "max_daily_volume_pct": 25.0,
                "confidence_threshold": 0.55,
                "max_concurrent_positions": 8,
            }
        else:  # BALANCED
            return {
                "max_position_pct": self.max_position_pct,
                "max_daily_volume_pct": self.max_daily_volume_pct,
                "confidence_threshold": self.confidence_threshold,
                "max_concurrent_positions": self.max_concurrent_positions,
            }
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Singleton instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Get or create the global settings instance.
    Loads from .env file in project root.
    """
    global _settings
    if _settings is None:
        # Try to load from .env file
        env_path = Path(__file__).parent.parent.parent / ".env"
        if env_path.exists():
            _settings = Settings(_env_file=str(env_path))
        else:
            _settings = Settings()
    return _settings


def reload_settings() -> Settings:
    """Force reload of settings from environment"""
    global _settings
    _settings = None
    return get_settings()
