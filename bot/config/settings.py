"""
Configuration management for Kraken Live Trading System.
Handles environment variables, defaults, and configuration validation.
"""
import os
from typing import Dict, List, Optional
from dataclasses import dataclass
from pathlib import Path
import json


@dataclass
class TradingConfig:
    """Trading configuration parameters"""
    live_trading: bool = True
    portfolio_size_usd: float = 500.0
    risk_mode: str = "balanced"  # conservative|balanced|aggressive
    max_position_pct: float = 3.0
    max_daily_volume_pct: float = 15.0
    max_daily_drawdown_pct: float = 10.0
    max_weekly_drawdown_pct: float = 20.0
    max_concurrent_positions: int = 5
    max_consecutive_losses: int = 5
    edge_buffer_bps: float = 20.0  # 0.2% minimum edge
    fee_multiplier_threshold: float = 3.0  # Must exceed 3x fees


@dataclass
class RiskLimits:
    """Risk limits for different risk modes"""
    conservative: Dict[str, float] = None
    balanced: Dict[str, float] = None
    aggressive: Dict[str, float] = None
    
    def __post_init__(self):
        if self.conservative is None:
            self.conservative = {
                "max_position_pct": 1.0,
                "max_daily_volume_pct": 5.0,
                "max_daily_drawdown_pct": 5.0,
                "confidence_threshold": 0.65
            }
        if self.balanced is None:
            self.balanced = {
                "max_position_pct": 3.0,
                "max_daily_volume_pct": 15.0,
                "max_daily_drawdown_pct": 10.0,
                "confidence_threshold": 0.60
            }
        if self.aggressive is None:
            self.aggressive = {
                "max_position_pct": 5.0,
                "max_daily_volume_pct": 25.0,
                "max_daily_drawdown_pct": 15.0,
                "confidence_threshold": 0.55
            }


@dataclass
class APIConfig:
    """API configuration for Kraken"""
    keys: List[Dict[str, str]] = None
    base_url: str = "https://api.kraken.com"
    websocket_url: str = "wss://ws.kraken.com"
    timeout: int = 30
    max_retries: int = 3
    rate_limit_per_key: int = 20  # requests per second per key
    health_check_interval: int = 30  # seconds


@dataclass
class UniverseConfig:
    """Trading universe configuration"""
    base_quote: str = "USD"
    universe_size: int = 10
    universe_refresh_minutes: int = 60
    min_daily_volume_usd: float = 1000000.0
    restricted_assets: List[str] = None
    
    def __post_init__(self):
        if self.restricted_assets is None:
            self.restricted_assets = [
                "ACA", "AGLD", "ALICE", "ANLOG", "ASTR", "ATLAS", "AUDIO", 
                "AVAAI", "C98", "CFG", "CLOUD", "CSM", "DBR", "DUCK", "FHE", 
                "GLMR", "GRASS", "HDX", "INTR", "K", "KERNEL", "KIN", "KMNO", 
                "L3", "LAYER", "LMWR", "MC", "MV", "NIL", "NMR", "NODL", 
                "NYM", "OMNI", "ORCA", "OXY", "PARA", "PERP", "PORTAL", 
                "PRCL", "PSTAKE", "RAY", "REQ", "REZ", "ROOK", "RSR", "SAMO", 
                "SDN", "SPICE", "STEP", "SWARMS", "SWELL", "TEER", "TERM", 
                "VVV", "WAL", "WEN", "WOO", "XRT", "YGG", "ZEX"
            ]


@dataclass
class MLConfig:
    """Machine learning configuration"""
    model_retrain_hours: int = 24
    confidence_threshold: float = 0.65
    ensemble_models: bool = True
    feature_lookback_seconds: int = 300
    training_window_days: int = 30
    validation_window_days: int = 7
    test_window_hours: int = 72
    purge_hours: int = 24
    embargo_hours: int = 48


@dataclass
class SystemConfig:
    """System configuration"""
    log_level: str = "INFO"
    metrics_port: int = 8080
    health_check_port: int = 8081
    data_retention_days: int = 90
    feature_cache_size_mb: int = 512
    max_decision_latency_ms: int = 100
    order_timeout_seconds: int = 30
    kill_switch_password: Optional[str] = None
    circuit_breaker_cooldown_minutes: int = 60


class Settings:
    """Main settings class that loads and manages all configuration"""
    
    def __init__(self, config_file: Optional[str] = None):
        self.project_root = Path(__file__).parent.parent.parent
        self.data_dir = self.project_root / "data"
        self.models_dir = self.project_root / "models"
        self.logs_dir = self.project_root / "logs"
        
        # Create directories
        self._create_directories()
        
        # Load configuration
        self.trading = self._load_trading_config()
        self.risk_limits = RiskLimits()
        self.api = self._load_api_config()
        self.universe = UniverseConfig()
        self.ml = MLConfig()
        self.system = self._load_system_config()
        
        # Apply risk mode
        self._apply_risk_mode()
        
        # Validate configuration
        self._validate_config()
    
    def _create_directories(self):
        """Create necessary directories"""
        dirs = [
            self.data_dir / "raw",
            self.data_dir / "features",
            self.models_dir,
            self.logs_dir,
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)
    
    def _load_trading_config(self) -> TradingConfig:
        """Load trading configuration from environment"""
        return TradingConfig(
            live_trading=os.getenv("LIVE_TRADING", "1") == "1",
            portfolio_size_usd=float(os.getenv("PORTFOLIO_SIZE_USD", "500")),
            risk_mode=os.getenv("RISK_MODE", "balanced"),
            max_position_pct=float(os.getenv("MAX_POSITION_PCT", "3")),
            max_daily_volume_pct=float(os.getenv("MAX_DAILY_VOLUME_PCT", "15")),
            max_daily_drawdown_pct=float(os.getenv("MAX_DAILY_DRAWDOWN_PCT", "10")),
            max_weekly_drawdown_pct=float(os.getenv("MAX_WEEKLY_DRAWDOWN_PCT", "20")),
            max_concurrent_positions=int(os.getenv("MAX_CONCURRENT_POSITIONS", "5")),
            max_consecutive_losses=int(os.getenv("MAX_CONSECUTIVE_LOSSES", "5")),
            edge_buffer_bps=float(os.getenv("EDGE_BUFFER_BPS", "20")),
            fee_multiplier_threshold=float(os.getenv("FEE_MULTIPLIER_THRESHOLD", "3")),
        )
    
    def _load_api_config(self) -> APIConfig:
        """Load API keys from environment"""
        keys = []
        for i in range(1, 6):
            key = os.getenv(f"KRAKEN_KEY_{i}")
            secret = os.getenv(f"KRAKEN_SECRET_{i}")
            if key and secret:
                keys.append({"key": key, "secret": secret, "id": i})
        
        if not keys:
            raise ValueError("At least one KRAKEN_KEY and KRAKEN_SECRET must be provided")
        
        return APIConfig(keys=keys)
    
    def _load_system_config(self) -> SystemConfig:
        """Load system configuration"""
        return SystemConfig(
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            metrics_port=int(os.getenv("METRICS_PORT", "8080")),
            health_check_port=int(os.getenv("HEALTH_CHECK_PORT", "8081")),
            data_retention_days=int(os.getenv("DATA_RETENTION_DAYS", "90")),
            feature_cache_size_mb=int(os.getenv("FEATURE_CACHE_SIZE_MB", "512")),
            max_decision_latency_ms=int(os.getenv("MAX_DECISION_LATENCY_MS", "100")),
            order_timeout_seconds=int(os.getenv("ORDER_TIMEOUT_SECONDS", "30")),
            kill_switch_password=os.getenv("KILL_SWITCH_PASSWORD"),
            circuit_breaker_cooldown_minutes=int(os.getenv("CIRCUIT_BREAKER_COOLDOWN_MINUTES", "60")),
        )
    
    def _apply_risk_mode(self):
        """Apply risk mode specific limits"""
        limits = self.risk_limits.__dict__[self.trading.risk_mode]
        self.trading.max_position_pct = limits["max_position_pct"]
        self.trading.max_daily_volume_pct = limits["max_daily_volume_pct"]
        self.trading.max_daily_drawdown_pct = limits["max_daily_drawdown_pct"]
        self.ml.confidence_threshold = limits["confidence_threshold"]
    
    def _validate_config(self):
        """Validate configuration settings"""
        if not self.trading.live_trading:
            raise ValueError("System must run in live mode (LIVE_TRADING=1)")
        
        if self.trading.portfolio_size_usd < 200 or self.trading.portfolio_size_usd > 800:
            raise ValueError("Portfolio size must be between $200 and $800")
        
        if not self.api.keys:
            raise ValueError("At least one API key must be configured")
        
        if len(self.api.keys) < 5:
            raise Warning(f"Only {len(self.api.keys)} API keys configured. System expects 5 keys.")
    
    def get_active_limits(self) -> Dict[str, float]:
        """Get active risk limits based on current risk mode"""
        return self.risk_limits.__dict__[self.trading.risk_mode]
    
    def get_universe_config(self) -> UniverseConfig:
        """Get universe configuration"""
        return self.universe
    
    def get_api_key(self, key_id: Optional[int] = None) -> Dict[str, str]:
        """Get API key by ID or return first available"""
        if key_id:
            for key in self.api.keys:
                if key["id"] == key_id:
                    return key
        return self.api.keys[0] if self.api.keys else None
