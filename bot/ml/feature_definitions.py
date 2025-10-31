"""
Feature Definitions - Schema and metadata for ML features
"""

from typing import List, Dict
from enum import Enum


class FeatureType(str, Enum):
    """Feature type categories"""
    PRICE = "price"
    SPREAD = "spread"
    VOLUME = "volume"
    VOLATILITY = "volatility"
    TEMPORAL = "temporal"
    CROSS_ASSET = "cross_asset"


class FeatureDefinition:
    """Definition of a single feature"""
    
    def __init__(
        self,
        name: str,
        feature_type: FeatureType,
        description: str,
        is_required: bool = True,
        fill_value: float = 0.0
    ):
        self.name = name
        self.feature_type = feature_type
        self.description = description
        self.is_required = is_required
        self.fill_value = fill_value


# Complete feature schema
FEATURE_SCHEMA: List[FeatureDefinition] = [
    # Price Features
    FeatureDefinition("price_last", FeatureType.PRICE, "Last trade price"),
    FeatureDefinition("return_pct_1s", FeatureType.PRICE, "1-second return %", False),
    FeatureDefinition("return_pct_5s", FeatureType.PRICE, "5-second return %", False),
    FeatureDefinition("return_pct_15s", FeatureType.PRICE, "15-second return %", False),
    FeatureDefinition("return_pct_30s", FeatureType.PRICE, "30-second return %", False),
    FeatureDefinition("return_pct_1m", FeatureType.PRICE, "1-minute return %", False),
    FeatureDefinition("return_pct_5m", FeatureType.PRICE, "5-minute return %", False),
    FeatureDefinition("return_log_1s", FeatureType.PRICE, "1-second log return", False),
    FeatureDefinition("return_log_5s", FeatureType.PRICE, "5-second log return", False),
    FeatureDefinition("return_log_15s", FeatureType.PRICE, "15-second log return", False),
    FeatureDefinition("return_log_30s", FeatureType.PRICE, "30-second log return", False),
    FeatureDefinition("return_log_1m", FeatureType.PRICE, "1-minute log return", False),
    FeatureDefinition("return_log_5m", FeatureType.PRICE, "5-minute log return", False),
    FeatureDefinition("return_zscore_10p", FeatureType.PRICE, "Return z-score 10 periods", False),
    FeatureDefinition("return_zscore_30p", FeatureType.PRICE, "Return z-score 30 periods", False),
    FeatureDefinition("return_zscore_60p", FeatureType.PRICE, "Return z-score 60 periods", False),
    FeatureDefinition("price_momentum_1m", FeatureType.PRICE, "1-minute price momentum", False),
    FeatureDefinition("price_momentum_5m", FeatureType.PRICE, "5-minute price momentum", False),
    
    # Spread & Liquidity Features
    FeatureDefinition("spread_abs", FeatureType.SPREAD, "Absolute spread", False),
    FeatureDefinition("spread_pct", FeatureType.SPREAD, "Percentage spread"),
    FeatureDefinition("bid_price", FeatureType.SPREAD, "Best bid price", False),
    FeatureDefinition("ask_price", FeatureType.SPREAD, "Best ask price", False),
    FeatureDefinition("mid_price", FeatureType.SPREAD, "Mid price"),
    FeatureDefinition("spread_percentile_1h", FeatureType.SPREAD, "Spread percentile 1h", False),
    FeatureDefinition("spread_percentile_4h", FeatureType.SPREAD, "Spread percentile 4h", False),
    FeatureDefinition("spread_percentile_24h", FeatureType.SPREAD, "Spread percentile 24h", False),
    FeatureDefinition("orderbook_imbalance_L5", FeatureType.SPREAD, "L5 orderbook imbalance", False),
    FeatureDefinition("orderbook_bid_volume", FeatureType.SPREAD, "Bid side volume L5", False),
    FeatureDefinition("orderbook_ask_volume", FeatureType.SPREAD, "Ask side volume L5", False),
    
    # Volume & Flow Features
    FeatureDefinition("volume_total", FeatureType.VOLUME, "Total volume", False),
    FeatureDefinition("trade_count", FeatureType.VOLUME, "Number of trades", False),
    FeatureDefinition("avg_trade_size", FeatureType.VOLUME, "Average trade size", False),
    FeatureDefinition("vwap_deviation_5m", FeatureType.VOLUME, "VWAP deviation 5m", False),
    FeatureDefinition("vwap_deviation_1m", FeatureType.VOLUME, "VWAP deviation 1m", False),
    FeatureDefinition("vwap_zscore_5m", FeatureType.VOLUME, "VWAP z-score 5m", False),
    FeatureDefinition("volume_burst", FeatureType.VOLUME, "Volume burst indicator", False),
    FeatureDefinition("buy_pressure", FeatureType.VOLUME, "Buy pressure ratio", False),
    FeatureDefinition("sell_pressure", FeatureType.VOLUME, "Sell pressure ratio", False),
    FeatureDefinition("order_flow_imbalance", FeatureType.VOLUME, "Order flow imbalance", False),
    
    # Volatility Features
    FeatureDefinition("realized_vol_1m", FeatureType.VOLATILITY, "Realized vol 1m", False),
    FeatureDefinition("realized_vol_5m", FeatureType.VOLATILITY, "Realized vol 5m", False),
    FeatureDefinition("realized_vol_15m", FeatureType.VOLATILITY, "Realized vol 15m", False),
    FeatureDefinition("parkinson_vol", FeatureType.VOLATILITY, "Parkinson volatility", False),
    FeatureDefinition("vol_percentile", FeatureType.VOLATILITY, "Volatility percentile", False),
    FeatureDefinition("garch_vol_forecast", FeatureType.VOLATILITY, "GARCH vol forecast", False),
    
    # Temporal Features
    FeatureDefinition("hour_sin", FeatureType.TEMPORAL, "Hour sine encoding"),
    FeatureDefinition("hour_cos", FeatureType.TEMPORAL, "Hour cosine encoding"),
    FeatureDefinition("minute_sin", FeatureType.TEMPORAL, "Minute sine encoding", False),
    FeatureDefinition("minute_cos", FeatureType.TEMPORAL, "Minute cosine encoding", False),
    FeatureDefinition("day_of_week_sin", FeatureType.TEMPORAL, "Day of week sine"),
    FeatureDefinition("day_of_week_cos", FeatureType.TEMPORAL, "Day of week cosine"),
    FeatureDefinition("us_session", FeatureType.TEMPORAL, "US trading session"),
    FeatureDefinition("eu_session", FeatureType.TEMPORAL, "EU trading session"),
    FeatureDefinition("asia_session", FeatureType.TEMPORAL, "Asia trading session"),
    FeatureDefinition("is_weekend", FeatureType.TEMPORAL, "Weekend indicator"),
    
    # Cross-Asset Features
    FeatureDefinition("btc_correlation_5m", FeatureType.CROSS_ASSET, "BTC correlation 5m", False),
]


def get_feature_names() -> List[str]:
    """Get list of all feature names"""
    return [f.name for f in FEATURE_SCHEMA]


def get_required_features() -> List[str]:
    """Get list of required feature names"""
    return [f.name for f in FEATURE_SCHEMA if f.is_required]


def get_features_by_type(feature_type: FeatureType) -> List[str]:
    """Get feature names filtered by type"""
    return [f.name for f in FEATURE_SCHEMA if f.feature_type == feature_type]


def get_fill_values() -> Dict[str, float]:
    """Get default fill values for missing features"""
    return {f.name: f.fill_value for f in FEATURE_SCHEMA}
