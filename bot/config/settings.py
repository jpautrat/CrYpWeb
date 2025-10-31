"""
Configuration management for ML Kraken Live Trader.
Handles environment variables, default values, and configuration validation.
"""
import os
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from pathlib import Path
import json


@dataclass
class TradingConfig:
    """Trading configuration parameters."""
    live_trading: bool = True  # Default to live (no test mode)
    portfolio_size_usd: float = 500.0
    risk_mode: str = "balanced"  # conservative, balanced, aggressive
    
    # Risk parameters by mode
    risk_params: Dict[str, Dict[str, float]] = field(default_factory=lambda: {
        "conservative": {
            "max_position_pct": 1.0,
            "max_daily_volume_pct": 5.0,
            "confidence_threshold": 0.70,
        },
        "balanced": {
            "max_position_pct": 3.0,
            "max_daily_volume_pct": 15.0,
            "confidence_threshold": 0.65,
        },
        "aggressive": {
            "max_position_pct": 5.0,
            "max_daily_volume_pct": 25.0,
            "confidence_threshold": 0.55,
        },
    })
    
    max_daily_drawdown_pct: float = 10.0
    max_weekly_drawdown_pct: float = 20.0
    max_concurrent_positions: int = 5
    max_consecutive_losses: int = 5
    
    # Fee and edge requirements
    edge_buffer_bps: float = 20.0  # 0.2% minimum edge
    min_edge_multiplier: float = 3.0  # Must exceed 3x fees
    
    def get_risk_param(self, param_name: str) -> float:
        """Get risk parameter for current mode."""
        return self.risk_params.get(self.risk_mode, self.risk_params["balanced"]).get(param_name, 0.0)


@dataclass
class APIConfig:
    """Kraken API configuration for 5 keys."""
    keys: List[Dict[str, str]] = field(default_factory=list)
    
    def __post_init__(self):
        """Load API keys from environment."""
        for i in range(1, 6):
            key = os.getenv(f"KRAKEN_KEY_{i}")
            secret = os.getenv(f"KRAKEN_SECRET_{i}")
            if key and secret:
                self.keys.append({
                    "key_id": i,
                    "api_key": key,
                    "api_secret": secret,
                })
        
        if not self.keys:
            raise ValueError("At least one Kraken API key pair must be configured")


@dataclass
class UniverseConfig:
    """Trading universe configuration."""
    base_quote: str = "USD"
    universe_size: int = 10
    universe_refresh_minutes: int = 60
    min_daily_volume_usd: float = 1000000.0
    
    # Hardcoded restricted assets for US-NC compliance
    restricted_assets: List[str] = field(default_factory=lambda: [
        "ACA", "AGLD", "ALICE", "ANLOG", "ASTR", "ATLAS", "AUDIO", "AVAAI",
        "C98", "CFG", "CLOUD", "CSM", "DBR", "DUCK", "FHE", "GLMR", "GRASS",
        "HDX", "INTR", "K", "KERNEL", "KIN", "KMNO", "L3", "LAYER", "LMWR",
        "MC", "MV", "NIL", "NMR", "NODL", "NYM", "OMNI", "ORCA", "OXY", "PARA",
        "PERP", "PORTAL", "PRCL", "PSTAKE", "RAY", "REQ", "REZ", "ROOK", "RSR",
        "SAMO", "SDN", "SPICE", "STEP", "SWARMS", "SWELL", "TEER", "TERM",
        "VVV", "WAL", "WEN", "WOO", "XRT", "YGG", "ZEX",
    ])
    
    # Currency-specific minimum order sizes
    currency_minimums: Dict[str, float] = field(default_factory=lambda: {
        "USD": 5.0,
        "BTC": 0.0001,
        "ETH": 0.001,
    })


@dataclass
class ModelConfig:
    """ML model configuration."""
    model_retrain_hours: int = 24
    confidence_threshold: float = 0.65
    ensemble_models: bool = True
    
    # Training parameters
    training_window_days: int = 30
    validation_days: int = 1
    purge_hours: int = 24
    embargo_hours: int = 48
    
    # Prediction latency
    max_decision_latency_ms: float = 100.0


@dataclass
class PerformanceConfig:
    """Performance tuning parameters."""
    feature_lookback_seconds: int = 300
    order_timeout_seconds: int = 30
    websocket_timeout_seconds: int = 30
    api_request_timeout_seconds: float = 5.0
    
    # Data retention
    data_retention_days: int = 90
    feature_cache_size_mb: int = 512
    
    # Latency targets
    target_latency_ms: float = 100.0
    max_latency_ms: float = 500.0


@dataclass
class SystemConfig:
    """System configuration."""
    log_level: str = "INFO"
    metrics_port: int = 8080
    health_check_port: int = 8081
    
    # Data directories
    base_data_dir: Path = field(default_factory=lambda: Path("data"))
    raw_data_dir: Path = field(default_factory=lambda: Path("data/raw"))
    features_dir: Path = field(default_factory=lambda: Path("data/features"))
    models_dir: Path = field(default_factory=lambda: Path("data/models"))
    logs_dir: Path = field(default_factory=lambda: Path("data/logs"))
    
    # Emergency controls
    kill_switch_password: Optional[str] = None
    circuit_breaker_cooldown_minutes: int = 60


class Settings:
    """Main settings container."""
    
    def __init__(self):
        """Initialize settings from environment variables."""
        # Trading config
        self.trading = TradingConfig(
            live_trading=os.getenv("LIVE_TRADING", "1") == "1",
            portfolio_size_usd=float(os.getenv("PORTFOLIO_SIZE_USD", "500.0")),
            risk_mode=os.getenv("RISK_MODE", "balanced"),
            max_daily_drawdown_pct=float(os.getenv("MAX_DAILY_DRAWDOWN_PCT", "10.0")),
            max_weekly_drawdown_pct=float(os.getenv("MAX_WEEKLY_DRAWDOWN_PCT", "20.0")),
            max_concurrent_positions=int(os.getenv("MAX_CONCURRENT_POSITIONS", "5")),
            max_consecutive_losses=int(os.getenv("MAX_CONSECUTIVE_LOSSES", "5")),
            edge_buffer_bps=float(os.getenv("EDGE_BUFFER_BPS", "20.0")),
            min_edge_multiplier=float(os.getenv("MIN_EDGE_MULTIPLIER", "3.0")),
        )
        
        # API config
        self.api = APIConfig()
        
        # Universe config
        self.universe = UniverseConfig(
            base_quote=os.getenv("BASE_QUOTE", "USD"),
            universe_size=int(os.getenv("UNIVERSE_SIZE", "10")),
            universe_refresh_minutes=int(os.getenv("UNIVERSE_REFRESH_MINUTES", "60")),
            min_daily_volume_usd=float(os.getenv("MIN_DAILY_VOLUME_USD", "1000000.0")),
        )
        
        # Model config
        self.model = ModelConfig(
            model_retrain_hours=int(os.getenv("MODEL_RETRAIN_HOURS", "24")),
            confidence_threshold=float(os.getenv("CONFIDENCE_THRESHOLD", "0.65")),
            ensemble_models=os.getenv("ENSEMBLE_MODELS", "true").lower() == "true",
            max_decision_latency_ms=float(os.getenv("MAX_DECISION_LATENCY_MS", "100.0")),
        )
        
        # Performance config
        self.performance = PerformanceConfig(
            feature_lookback_seconds=int(os.getenv("FEATURE_LOOKBACK_SECONDS", "300")),
            order_timeout_seconds=int(os.getenv("ORDER_TIMEOUT_SECONDS", "30")),
            websocket_timeout_seconds=int(os.getenv("WEBSOCKET_TIMEOUT_SECONDS", "30")),
            api_request_timeout_seconds=float(os.getenv("API_REQUEST_TIMEOUT_SECONDS", "5.0")),
            data_retention_days=int(os.getenv("DATA_RETENTION_DAYS", "90")),
            feature_cache_size_mb=int(os.getenv("FEATURE_CACHE_SIZE_MB", "512")),
            target_latency_ms=float(os.getenv("TARGET_LATENCY_MS", "100.0")),
            max_latency_ms=float(os.getenv("MAX_LATENCY_MS", "500.0")),
        )
        
        # System config
        self.system = SystemConfig(
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            metrics_port=int(os.getenv("METRICS_PORT", "8080")),
            health_check_port=int(os.getenv("HEALTH_CHECK_PORT", "8081")),
            kill_switch_password=os.getenv("KILL_SWITCH_PASSWORD"),
            circuit_breaker_cooldown_minutes=int(os.getenv("CIRCUIT_BREAKER_COOLDOWN_MINUTES", "60")),
        )
        
        # Create directories
        self._create_directories()
    
    def _create_directories(self):
        """Create necessary data directories."""
        for dir_path in [
            self.system.raw_data_dir,
            self.system.features_dir,
            self.system.models_dir,
            self.system.logs_dir,
        ]:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def validate(self) -> List[str]:
        """Validate configuration and return list of errors."""
        errors = []
        
        if not self.trading.live_trading:
            errors.append("WARNING: LIVE_TRADING is disabled - system will not place orders")
        
        if len(self.api.keys) < 1:
            errors.append("ERROR: No API keys configured")
        
        if self.trading.portfolio_size_usd < 200 or self.trading.portfolio_size_usd > 1000:
            errors.append("WARNING: Portfolio size outside recommended range ($200-$1000)")
        
        if self.trading.risk_mode not in ["conservative", "balanced", "aggressive"]:
            errors.append(f"ERROR: Invalid risk mode: {self.trading.risk_mode}")
        
        return errors


# Global settings instance
settings = Settings()
