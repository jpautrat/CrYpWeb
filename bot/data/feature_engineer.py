"""
Feature Engineer - Comprehensive feature computation for ML models
Implements microstructure features, market regimes, and cross-asset features.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime
from loguru import logger
from .market_data import MarketDataManager


class FeatureEngineer:
    """
    Computes comprehensive feature set for ML trading models.
    Includes price features, spread/liquidity, volume/flow, volatility regimes,
    temporal features, and cross-asset features.
    """
    
    def __init__(
        self,
        market_data: MarketDataManager,
        enable_cross_asset: bool = True,
        enable_temporal: bool = True,
        enable_volatility: bool = True
    ):
        """
        Initialize feature engineer.
        
        Args:
            market_data: Market data manager
            enable_cross_asset: Enable cross-asset features
            enable_temporal: Enable temporal/cyclical features
            enable_volatility: Enable volatility regime features
        """
        self.market_data = market_data
        self.enable_cross_asset = enable_cross_asset
        self.enable_temporal = enable_temporal
        self.enable_volatility = enable_volatility
        
        self.feature_cache: Dict = {}
        
        logger.info(
            f"FeatureEngineer initialized: cross_asset={enable_cross_asset}, "
            f"temporal={enable_temporal}, volatility={enable_volatility}"
        )
    
    def compute_features(
        self,
        pair: str,
        timestamp: datetime,
        lookback_seconds: int = 300
    ) -> pd.Series:
        """
        Compute complete feature set for a pair at given timestamp.
        
        Args:
            pair: Trading pair
            timestamp: Timestamp for feature computation
            lookback_seconds: Historical data window
            
        Returns:
            Series with all computed features
        """
        features = {}
        
        try:
            # Get recent data
            ticks = self.market_data.get_recent_ticks(pair, lookback_seconds)
            orderbook_df = self.market_data.get_recent_orderbook(pair, 100)
            
            if ticks.empty:
                logger.warning(f"No tick data available for {pair}")
                return pd.Series(features)
            
            # 1. PRICE FEATURES
            price_features = self._compute_price_features(ticks)
            features.update(price_features)
            
            # 2. SPREAD & LIQUIDITY FEATURES
            if not orderbook_df.empty:
                spread_features = self._compute_spread_features(orderbook_df, pair)
                features.update(spread_features)
            
            # 3. VOLUME & FLOW FEATURES
            volume_features = self._compute_volume_features(ticks, pair)
            features.update(volume_features)
            
            # 4. VOLATILITY REGIME FEATURES
            if self.enable_volatility:
                vol_features = self._compute_volatility_features(ticks)
                features.update(vol_features)
            
            # 5. TEMPORAL FEATURES
            if self.enable_temporal:
                temporal_features = self._compute_temporal_features(timestamp)
                features.update(temporal_features)
            
            # 6. CROSS-ASSET FEATURES
            if self.enable_cross_asset:
                cross_features = self._compute_cross_asset_features(pair, timestamp)
                features.update(cross_features)
            
            # Add metadata
            features['timestamp'] = timestamp
            features['pair'] = pair
            
            return pd.Series(features)
            
        except Exception as e:
            logger.error(f"Feature computation failed for {pair}: {e}", exc_info=True)
            return pd.Series(features)
    
    def _compute_price_features(self, ticks: pd.DataFrame) -> Dict:
        """Compute price-based features"""
        features = {}
        
        prices = ticks['price'].values
        
        if len(prices) < 2:
            return features
        
        # Current price
        features['price_last'] = prices[-1]
        
        # Returns at multiple horizons
        for period, label in [(1, '1s'), (5, '5s'), (15, '15s'), (30, '30s'), (60, '1m'), (300, '5m')]:
            if len(prices) > period:
                ret_pct = (prices[-1] - prices[-period]) / prices[-period] * 100
                ret_log = np.log(prices[-1] / prices[-period])
                
                features[f'return_pct_{label}'] = ret_pct
                features[f'return_log_{label}'] = ret_log
        
        # Rolling z-scores of returns
        if len(prices) > 10:
            returns = np.diff(prices) / prices[:-1]
            
            for window in [10, 30, 60]:
                if len(returns) >= window:
                    recent_returns = returns[-window:]
                    mean = np.mean(recent_returns)
                    std = np.std(recent_returns)
                    
                    if std > 0:
                        current_return = returns[-1]
                        z_score = (current_return - mean) / std
                        features[f'return_zscore_{window}p'] = z_score
        
        # Price momentum
        if len(prices) > 60:
            features['price_momentum_1m'] = (prices[-1] - prices[-60]) / prices[-60]
        
        if len(prices) > 300:
            features['price_momentum_5m'] = (prices[-1] - prices[-300]) / prices[-300]
        
        return features
    
    def _compute_spread_features(self, orderbook_df: pd.DataFrame, pair: str) -> Dict:
        """Compute spread and liquidity features"""
        features = {}
        
        if orderbook_df.empty:
            return features
        
        # Current spread
        latest = orderbook_df.iloc[-1]
        features['spread_abs'] = latest['spread']
        features['spread_pct'] = (latest['spread'] / latest['mid_price'] * 100) if latest['mid_price'] > 0 else 0
        features['bid_price'] = latest['bid_price']
        features['ask_price'] = latest['ask_price']
        features['mid_price'] = latest['mid_price']
        
        # Spread percentile ranks
        for window, label in [(3600, '1h'), (14400, '4h'), (86400, '24h')]:
            window_samples = min(window, len(orderbook_df))
            if window_samples > 10:
                window_data = orderbook_df.tail(window_samples)
                current_spread = latest['spread']
                
                percentile = (window_data['spread'] < current_spread).sum() / len(window_data) * 100
                features[f'spread_percentile_{label}'] = percentile
        
        # Order book depth (if available from market data)
        depth = self.market_data.get_orderbook_depth(pair, levels=5)
        if depth:
            features['orderbook_imbalance_L5'] = depth['imbalance']
            features['orderbook_bid_volume'] = depth['bid_volume']
            features['orderbook_ask_volume'] = depth['ask_volume']
        
        return features
    
    def _compute_volume_features(self, ticks: pd.DataFrame, pair: str) -> Dict:
        """Compute volume and flow features"""
        features = {}
        
        if 'volume' not in ticks.columns or ticks['volume'].sum() == 0:
            return features
        
        # Recent volume
        features['volume_total'] = ticks['volume'].sum()
        features['trade_count'] = len(ticks)
        
        # Average trade size
        if len(ticks) > 0:
            features['avg_trade_size'] = ticks['volume'].mean()
        
        # VWAP deviation
        vwap_5m = self.market_data.compute_vwap(pair, 300)
        vwap_1m = self.market_data.compute_vwap(pair, 60)
        
        if vwap_5m and 'price' in ticks.columns:
            current_price = ticks['price'].iloc[-1]
            vwap_dev_5m = (current_price - vwap_5m) / vwap_5m * 100
            features['vwap_deviation_5m'] = vwap_dev_5m
            
            # VWAP z-score
            prices = ticks['price'].values
            if len(prices) > 10:
                vwap_devs = [(p - vwap_5m) / vwap_5m for p in prices]
                mean_dev = np.mean(vwap_devs)
                std_dev = np.std(vwap_devs)
                if std_dev > 0:
                    features['vwap_zscore_5m'] = (vwap_dev_5m - mean_dev) / std_dev
        
        if vwap_1m:
            current_price = ticks['price'].iloc[-1]
            features['vwap_deviation_1m'] = (current_price - vwap_1m) / vwap_1m * 100
        
        # Volume burst detection
        if len(ticks) > 60:
            recent_volume = ticks.tail(30)['volume'].sum()
            older_volume = ticks.iloc[-60:-30]['volume'].sum()
            
            if older_volume > 0:
                volume_ratio = recent_volume / older_volume
                features['volume_burst'] = volume_ratio
        
        # Trade aggressor direction (buy vs sell pressure)
        if 'side' in ticks.columns:
            buy_volume = ticks[ticks['side'] == 'buy']['volume'].sum()
            sell_volume = ticks[ticks['side'] == 'sell']['volume'].sum()
            total_volume = buy_volume + sell_volume
            
            if total_volume > 0:
                buy_pressure = buy_volume / total_volume
                features['buy_pressure'] = buy_pressure
                features['sell_pressure'] = sell_volume / total_volume
                features['order_flow_imbalance'] = (buy_volume - sell_volume) / total_volume
        
        return features
    
    def _compute_volatility_features(self, ticks: pd.DataFrame) -> Dict:
        """Compute volatility regime features"""
        features = {}
        
        if 'price' not in ticks.columns or len(ticks) < 10:
            return features
        
        prices = ticks['price'].values
        returns = np.diff(np.log(prices))
        
        # Realized volatility at multiple windows
        for window, label in [(60, '1m'), (300, '5m'), (900, '15m')]:
            if len(returns) >= window:
                window_returns = returns[-window:]
                realized_vol = np.std(window_returns) * np.sqrt(252 * 24 * 3600)  # Annualized
                features[f'realized_vol_{label}'] = realized_vol
        
        # Parkinson volatility estimator (uses high-low range)
        if len(ticks) > 20:
            # Create 1-minute bars
            ticks_copy = ticks.copy()
            ticks_copy['timestamp'] = pd.to_datetime(ticks_copy['timestamp'])
            ticks_copy = ticks_copy.set_index('timestamp')
            
            bars_1m = ticks_copy['price'].resample('1min').ohlc()
            bars_1m = bars_1m.dropna()
            
            if len(bars_1m) > 1:
                hl_ratio = np.log(bars_1m['high'] / bars_1m['low'])
                parkinson_vol = np.sqrt(np.mean(hl_ratio**2) / (4 * np.log(2))) * np.sqrt(252 * 24 * 60)
                features['parkinson_vol'] = parkinson_vol
        
        # Volatility percentile rank
        if len(returns) > 100:
            recent_vol = np.std(returns[-20:])
            historical_vols = [np.std(returns[i:i+20]) for i in range(0, len(returns)-20, 10)]
            
            if historical_vols:
                percentile = sum(v < recent_vol for v in historical_vols) / len(historical_vols) * 100
                features['vol_percentile'] = percentile
        
        # Simple GARCH-style volatility forecast
        if len(returns) > 50:
            # Exponentially weighted moving average of squared returns
            alpha = 0.06  # Standard GARCH parameter
            ewma_var = returns[0]**2
            
            for ret in returns[1:]:
                ewma_var = alpha * ret**2 + (1 - alpha) * ewma_var
            
            garch_vol = np.sqrt(ewma_var) * np.sqrt(252 * 24 * 3600)
            features['garch_vol_forecast'] = garch_vol
        
        return features
    
    def _compute_temporal_features(self, timestamp: datetime) -> Dict:
        """Compute temporal/cyclical features"""
        features = {}
        
        # Time of day (cyclical encoding)
        hour = timestamp.hour
        minute = timestamp.minute
        
        # Hour of day (0-23)
        hour_sin = np.sin(2 * np.pi * hour / 24)
        hour_cos = np.cos(2 * np.pi * hour / 24)
        features['hour_sin'] = hour_sin
        features['hour_cos'] = hour_cos
        
        # Minute of hour (0-59)
        minute_sin = np.sin(2 * np.pi * minute / 60)
        minute_cos = np.cos(2 * np.pi * minute / 60)
        features['minute_sin'] = minute_sin
        features['minute_cos'] = minute_cos
        
        # Day of week (0-6)
        day_of_week = timestamp.weekday()
        dow_sin = np.sin(2 * np.pi * day_of_week / 7)
        dow_cos = np.cos(2 * np.pi * day_of_week / 7)
        features['day_of_week_sin'] = dow_sin
        features['day_of_week_cos'] = dow_cos
        
        # Market session indicators
        # US session: 9:30-16:00 EST (14:30-21:00 UTC)
        # EU session: 8:00-16:30 CET (7:00-15:30 UTC)
        # Asia session: 9:00-15:00 JST (0:00-6:00 UTC)
        
        utc_hour = timestamp.hour
        features['us_session'] = 1 if 14 <= utc_hour < 21 else 0
        features['eu_session'] = 1 if 7 <= utc_hour < 16 else 0
        features['asia_session'] = 1 if utc_hour < 6 else 0
        
        # Weekend indicator
        features['is_weekend'] = 1 if day_of_week >= 5 else 0
        
        return features
    
    def _compute_cross_asset_features(
        self,
        pair: str,
        timestamp: datetime
    ) -> Dict:
        """Compute cross-asset features"""
        features = {}
        
        # Get BTC price for correlation (if pair is not BTC)
        if not pair.startswith('BTC') and not pair.startswith('XBT'):
            btc_pair = 'XBT/USD'  # Kraken uses XBT for Bitcoin
            
            btc_ticks = self.market_data.get_recent_ticks(btc_pair, 300)
            pair_ticks = self.market_data.get_recent_ticks(pair, 300)
            
            if not btc_ticks.empty and not pair_ticks.empty and len(btc_ticks) > 10 and len(pair_ticks) > 10:
                # Align timestamps and compute correlation
                btc_prices = btc_ticks.set_index('timestamp')['price']
                pair_prices = pair_ticks.set_index('timestamp')['price']
                
                # Resample to common frequency
                btc_resampled = btc_prices.resample('10s').last().ffill()
                pair_resampled = pair_prices.resample('10s').last().ffill()
                
                # Compute correlation
                common_index = btc_resampled.index.intersection(pair_resampled.index)
                if len(common_index) > 10:
                    btc_returns = btc_resampled.loc[common_index].pct_change().dropna()
                    pair_returns = pair_resampled.loc[common_index].pct_change().dropna()
                    
                    if len(btc_returns) > 5 and len(pair_returns) > 5:
                        correlation = btc_returns.corr(pair_returns)
                        features['btc_correlation_5m'] = correlation
        
        # USD strength indicator (average performance across major pairs)
        # Could be extended to look at multiple USD pairs
        
        return features
    
    def get_feature_names(self) -> List[str]:
        """Get list of all possible feature names"""
        # This is a representative list - actual features depend on data availability
        feature_names = [
            # Price features
            'price_last', 'return_pct_1s', 'return_pct_5s', 'return_pct_15s',
            'return_pct_30s', 'return_pct_1m', 'return_pct_5m',
            'return_log_1s', 'return_log_5s', 'return_log_15s',
            'return_log_30s', 'return_log_1m', 'return_log_5m',
            'return_zscore_10p', 'return_zscore_30p', 'return_zscore_60p',
            'price_momentum_1m', 'price_momentum_5m',
            
            # Spread & liquidity
            'spread_abs', 'spread_pct', 'bid_price', 'ask_price', 'mid_price',
            'spread_percentile_1h', 'spread_percentile_4h', 'spread_percentile_24h',
            'orderbook_imbalance_L5', 'orderbook_bid_volume', 'orderbook_ask_volume',
            
            # Volume & flow
            'volume_total', 'trade_count', 'avg_trade_size',
            'vwap_deviation_5m', 'vwap_deviation_1m', 'vwap_zscore_5m',
            'volume_burst', 'buy_pressure', 'sell_pressure', 'order_flow_imbalance',
            
            # Volatility
            'realized_vol_1m', 'realized_vol_5m', 'realized_vol_15m',
            'parkinson_vol', 'vol_percentile', 'garch_vol_forecast',
            
            # Temporal
            'hour_sin', 'hour_cos', 'minute_sin', 'minute_cos',
            'day_of_week_sin', 'day_of_week_cos',
            'us_session', 'eu_session', 'asia_session', 'is_weekend',
            
            # Cross-asset
            'btc_correlation_5m',
        ]
        
        return feature_names
