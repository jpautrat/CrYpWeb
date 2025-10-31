"""
Feature definitions and specifications for ML models.
Defines expected feature names and types for model compatibility.
"""
from typing import List, Dict


class FeatureDefinitions:
    """Defines all feature names and categories"""
    
    # Price features
    PRICE_FEATURES = [
        'price_current',
        'return_1s', 'return_5s', 'return_15s', 'return_30s', 'return_1m', 'return_5m',
        'log_return_1s', 'log_return_5s', 'log_return_15s', 'log_return_30s', 
        'log_return_1m', 'log_return_5m',
        'return_zscore_10', 'return_zscore_30', 'return_zscore_60'
    ]
    
    # Spread and liquidity features
    SPREAD_FEATURES = [
        'spread_abs', 'spread_bps',
        'spread_percentile_1h', 'spread_percentile_4h', 'spread_percentile_24h',
        'depth_0.1pct', 'depth_0.5pct', 'depth_1pct'
    ]
    
    # Volume features
    VOLUME_FEATURES = [
        'volume_ratio_5m', 'volume_ratio_15m', 'volume_ratio_1h',
        'buy_pressure', 'sell_pressure',
        'vwap_deviation_5m', 'vwap_deviation_15m', 'vwap_deviation_1h',
        'avg_trade_size'
    ]
    
    # Volatility features
    VOLATILITY_FEATURES = [
        'realized_vol_1m', 'realized_vol_5m', 'realized_vol_15m',
        'parkinson_vol',
        'volatility_percentile'
    ]
    
    # Temporal features
    TEMPORAL_FEATURES = [
        'hour_sin', 'hour_cos',
        'day_of_week_sin', 'day_of_week_cos',
        'minute_sin', 'minute_cos',
        'us_session', 'eu_session', 'asia_session',
        'hours_since_midnight'
    ]
    
    # Cross-asset features (to be added dynamically)
    CROSS_ASSET_FEATURES = [
        'btc_correlation',
        'usd_strength',
        'relative_performance'
    ]
    
    @classmethod
    def get_all_features(cls) -> List[str]:
        """Get all feature names"""
        return (
            cls.PRICE_FEATURES +
            cls.SPREAD_FEATURES +
            cls.VOLUME_FEATURES +
            cls.VOLATILITY_FEATURES +
            cls.TEMPORAL_FEATURES +
            cls.CROSS_ASSET_FEATURES
        )
    
    @classmethod
    def get_feature_categories(cls) -> Dict[str, List[str]]:
        """Get features grouped by category"""
        return {
            'price': cls.PRICE_FEATURES,
            'spread': cls.SPREAD_FEATURES,
            'volume': cls.VOLUME_FEATURES,
            'volatility': cls.VOLATILITY_FEATURES,
            'temporal': cls.TEMPORAL_FEATURES,
            'cross_asset': cls.CROSS_ASSET_FEATURES
        }
    
    @classmethod
    def validate_features(cls, features: List[str]) -> tuple[bool, List[str]]:
        """
        Validate feature names.
        Returns (is_valid, list_of_unknown_features)
        """
        all_valid = cls.get_all_features()
        unknown = [f for f in features if f not in all_valid]
        return len(unknown) == 0, unknown
    
    @classmethod
    def get_feature_count(cls) -> int:
        """Get total number of features"""
        return len(cls.get_all_features())
