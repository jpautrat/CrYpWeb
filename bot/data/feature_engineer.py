"""
Feature engineering pipeline for ML models.
Computes comprehensive features from market data.
"""
import pandas as pd
import numpy as np
from typing import Dict, Optional
from datetime import datetime, timedelta
from loguru import logger


class FeatureEngineer:
    """Engineers features from raw market data."""
    
    def __init__(self, lookback_seconds: int = 300):
        """
        Initialize feature engineer.
        
        Args:
            lookback_seconds: Lookback window for feature computation
        """
        self.lookback_seconds = lookback_seconds
        self.cache: Dict[str, pd.DataFrame] = {}
    
    def compute_features(self, pair: str, trades_df: pd.DataFrame, 
                        orderbook: Optional[Dict] = None,
                        timestamp: Optional[datetime] = None) -> pd.Series:
        """
        Compute features for a trading pair.
        
        Args:
            pair: Trading pair
            trades_df: DataFrame with trades (timestamp, price, volume, side)
            orderbook: Current order book snapshot
            timestamp: Current timestamp
            
        Returns:
            Series with computed features
        """
        if trades_df.empty:
            return pd.Series()
        
        features = pd.Series(dtype=float)
        trades_df = trades_df.sort_values('timestamp')
        
        # Price features
        features = pd.concat([features, self._compute_price_features(trades_df)])
        
        # Volume features
        features = pd.concat([features, self._compute_volume_features(trades_df)])
        
        # Spread and liquidity features
        if orderbook:
            features = pd.concat([features, self._compute_spread_features(orderbook)])
        
        # Volatility features
        features = pd.concat([features, self._compute_volatility_features(trades_df)])
        
        # Temporal features
        if timestamp:
            features = pd.concat([features, self._compute_temporal_features(timestamp)])
        
        return features
    
    def _compute_price_features(self, df: pd.DataFrame) -> pd.Series:
        """Compute price-based features."""
        features = pd.Series(dtype=float)
        prices = df['price'].values
        
        # Returns at different horizons
        for window in [1, 5, 15, 30, 60]:
            if len(prices) > window:
                ret = (prices[-1] - prices[-window-1]) / prices[-window-1] * 100
                features[f'return_{window}s'] = ret
                
                # Log returns
                log_ret = np.log(prices[-1] / prices[-window-1]) * 100
                features[f'log_return_{window}s'] = log_ret
        
        # Rolling z-scores
        if len(prices) > 60:
            returns = np.diff(prices) / prices[:-1]
            for window in [10, 30, 60]:
                if len(returns) >= window:
                    rolling_mean = pd.Series(returns[-window:]).mean()
                    rolling_std = pd.Series(returns[-window:]).std()
                    if rolling_std > 0:
                        zscore = (returns[-1] - rolling_mean) / rolling_std
                        features[f'zscore_{window}'] = zscore
        
        return features
    
    def _compute_volume_features(self, df: pd.DataFrame) -> pd.Series:
        """Compute volume-based features."""
        features = pd.Series(dtype=float)
        
        if 'volume' not in df.columns:
            return features
        
        volumes = df['volume'].values
        
        # Volume bursts
        if len(volumes) > 60:
            recent_vol = volumes[-60:].sum()
            avg_vol = volumes[-300:].sum() / 5 if len(volumes) >= 300 else recent_vol
            if avg_vol > 0:
                features['volume_burst'] = recent_vol / avg_vol
        
        # VWAP deviation
        if len(df) > 60:
            vwap = (df['price'] * df['volume']).sum() / df['volume'].sum()
            last_price = df['price'].iloc[-1]
            features['vwap_deviation'] = (last_price - vwap) / vwap * 100
        
        return features
    
    def _compute_spread_features(self, orderbook: Dict) -> pd.Series:
        """Compute spread and liquidity features."""
        features = pd.Series(dtype=float)
        
        bids = orderbook.get('bids', [])
        asks = orderbook.get('asks', [])
        
        if not bids or not asks:
            return features
        
        best_bid = float(bids[0][0])
        best_ask = float(asks[0][0])
        mid_price = (best_bid + best_ask) / 2
        
        # Spread
        spread = best_ask - best_bid
        spread_pct = (spread / mid_price) * 100 if mid_price > 0 else 0
        features['spread_abs'] = spread
        features['spread_pct'] = spread_pct
        
        # Order book imbalance
        bid_volume = sum(float(b[1]) for b in bids[:5])
        ask_volume = sum(float(a[1]) for a in asks[:5])
        total_volume = bid_volume + ask_volume
        if total_volume > 0:
            features['orderbook_imbalance'] = (bid_volume - ask_volume) / total_volume
        
        return features
    
    def _compute_volatility_features(self, df: pd.DataFrame) -> pd.Series:
        """Compute volatility features."""
        features = pd.Series(dtype=float)
        prices = df['price'].values
        
        if len(prices) < 60:
            return features
        
        returns = np.diff(prices) / prices[:-1]
        
        # Realized volatility
        for window in [60, 300, 900]:  # 1m, 5m, 15m
            if len(returns) >= window:
                vol = np.std(returns[-window:]) * np.sqrt(window) * 100
                features[f'realized_vol_{window}'] = vol
        
        return features
    
    def _compute_temporal_features(self, timestamp: datetime) -> pd.Series:
        """Compute temporal features."""
        features = pd.Series(dtype=float)
        
        # Time of day (cyclical encoding)
        hour = timestamp.hour
        minute = timestamp.minute
        total_minutes = hour * 60 + minute
        
        # Sine/cosine encoding for 24-hour cycle
        features['hour_sin'] = np.sin(2 * np.pi * hour / 24)
        features['hour_cos'] = np.cos(2 * np.pi * hour / 24)
        features['minute_sin'] = np.sin(2 * np.pi * total_minutes / (24 * 60))
        features['minute_cos'] = np.cos(2 * np.pi * total_minutes / (24 * 60))
        
        # Day of week
        features['day_of_week'] = timestamp.weekday()
        
        return features
