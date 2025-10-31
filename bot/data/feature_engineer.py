"""
Feature engineering pipeline for ML model inputs.
Computes price, spread, volume, volatility, temporal, and cross-asset features.
"""
import pandas as pd
import numpy as np
from typing import Dict, Optional
from datetime import datetime, timedelta
from loguru import logger
from scipy import stats
from sklearn.preprocessing import StandardScaler


class FeatureEngineer:
    """Computes comprehensive features for ML models"""
    
    def __init__(self):
        self.scaler = StandardScaler()
        self.feature_cache: Dict[str, pd.DataFrame] = {}
        self.cache_ttl = timedelta(minutes=5)
    
    def compute_all_features(self, trades: pd.DataFrame, orderbook: Optional[pd.DataFrame] = None,
                            pair: str = "", timestamp: Optional[datetime] = None) -> pd.Series:
        """
        Compute all features for a given timestamp.
        
        Args:
            trades: DataFrame with columns: timestamp, price, volume, side
            orderbook: Optional DataFrame with order book data
            pair: Trading pair symbol
            timestamp: Current timestamp (defaults to most recent trade)
        
        Returns:
            Series with all computed features
        """
        if trades.empty:
            logger.warning("Empty trades DataFrame")
            return pd.Series()
        
        if timestamp is None:
            timestamp = pd.to_datetime(trades['timestamp'].iloc[-1])
        
        # Ensure sorted by timestamp
        trades = trades.sort_values('timestamp').copy()
        trades['timestamp'] = pd.to_datetime(trades['timestamp'])
        
        # Set timestamp as index if not already
        if not isinstance(trades.index, pd.DatetimeIndex):
            trades = trades.set_index('timestamp')
        
        features = pd.Series(index=[timestamp], dtype=float)
        
        # Price features
        price_features = self._compute_price_features(trades, timestamp)
        features = pd.concat([features, price_features])
        
        # Spread and liquidity features
        if orderbook is not None and not orderbook.empty:
            spread_features = self._compute_spread_features(orderbook, trades, timestamp)
            features = pd.concat([features, spread_features])
        
        # Volume and flow features
        volume_features = self._compute_volume_features(trades, timestamp)
        features = pd.concat([features, volume_features])
        
        # Volatility features
        volatility_features = self._compute_volatility_features(trades, timestamp)
        features = pd.concat([features, volatility_features])
        
        # Temporal features
        temporal_features = self._compute_temporal_features(timestamp)
        features = pd.concat([features, temporal_features])
        
        # Fill NaN values
        features = features.fillna(0.0)
        
        return features
    
    def _compute_price_features(self, trades: pd.DataFrame, timestamp: datetime) -> pd.Series:
        """Compute price-based features"""
        features = {}
        
        # Get recent price data
        window_end = timestamp
        window_1s = window_end - timedelta(seconds=1)
        window_5s = window_end - timedelta(seconds=5)
        window_15s = window_end - timedelta(seconds=15)
        window_30s = window_end - timedelta(seconds=30)
        window_1m = window_end - timedelta(minutes=1)
        window_5m = window_end - timedelta(minutes=5)
        
        # Current mid-price (use last trade as proxy)
        recent_trades = trades[trades.index <= window_end].tail(100)
        if not recent_trades.empty:
            current_price = recent_trades['price'].iloc[-1]
            features['price_current'] = current_price
            
            # Mid-price returns for different horizons
            for period_name, window_start in [
                ('1s', window_1s),
                ('5s', window_5s),
                ('15s', window_15s),
                ('30s', window_30s),
                ('1m', window_1m),
                ('5m', window_5m)
            ]:
                period_trades = trades[
                    (trades.index >= window_start) & 
                    (trades.index <= window_end)
                ]
                if len(period_trades) > 0:
                    start_price = period_trades['price'].iloc[0]
                    if start_price > 0:
                        # Simple return
                        ret = (current_price - start_price) / start_price
                        features[f'return_{period_name}'] = ret
                        
                        # Log return
                        log_ret = np.log(current_price / start_price)
                        features[f'log_return_{period_name}'] = log_ret
                else:
                    features[f'return_{period_name}'] = 0.0
                    features[f'log_return_{period_name}'] = 0.0
            
            # Rolling z-scores of returns
            for window in [10, 30, 60]:
                window_trades = trades[trades.index <= window_end].tail(window * 2)
                if len(window_trades) >= window:
                    prices = window_trades['price'].values
                    returns = np.diff(prices) / prices[:-1]
                    if len(returns) >= window:
                        rolling_ret = returns[-window:]
                        if len(rolling_ret) > 1 and rolling_ret.std() > 0:
                            z_score = (rolling_ret[-1] - rolling_ret.mean()) / rolling_ret.std()
                            features[f'return_zscore_{window}'] = z_score
                        else:
                            features[f'return_zscore_{window}'] = 0.0
                    else:
                        features[f'return_zscore_{window}'] = 0.0
                else:
                    features[f'return_zscore_{window}'] = 0.0
        else:
            # Default values if no trades
            features['price_current'] = 0.0
            for period in ['1s', '5s', '15s', '30s', '1m', '5m']:
                features[f'return_{period}'] = 0.0
                features[f'log_return_{period}'] = 0.0
            for window in [10, 30, 60]:
                features[f'return_zscore_{window}'] = 0.0
        
        return pd.Series(features)
    
    def _compute_spread_features(self, orderbook: pd.DataFrame, trades: pd.DataFrame, timestamp: datetime) -> pd.Series:
        """Compute spread and liquidity features"""
        features = {}
        
        # Get most recent order book snapshot
        if isinstance(orderbook.index, pd.DatetimeIndex):
            recent_book = orderbook[orderbook.index <= timestamp].tail(1)
        else:
            recent_book = orderbook[orderbook['timestamp'] <= timestamp].tail(1)
        
        if not recent_book.empty:
            # Extract best bid and ask (assuming orderbook has these columns)
            if 'best_bid' in recent_book.columns and 'best_ask' in recent_book.columns:
                best_bid = recent_book['best_bid'].iloc[-1]
                best_ask = recent_book['best_ask'].iloc[-1]
                
                if best_bid > 0 and best_ask > 0:
                    mid_price = (best_bid + best_ask) / 2
                    spread = best_ask - best_bid
                    spread_pct = (spread / mid_price) * 10000  # Basis points
                    
                    features['spread_abs'] = spread
                    features['spread_bps'] = spread_pct
                    
                    # Spread percentile rank (rolling 1h, 4h, 24h)
                    for period_name, hours in [('1h', 1), ('4h', 4), ('24h', 24)]:
                        period_start = timestamp - timedelta(hours=hours)
                        period_book = orderbook[
                            (orderbook.index >= period_start) & 
                            (orderbook.index <= timestamp)
                        ] if isinstance(orderbook.index, pd.DatetimeIndex) else orderbook[
                            (orderbook['timestamp'] >= period_start) & 
                            (orderbook['timestamp'] <= timestamp)
                        ]
                        
                        if len(period_book) > 10 and 'spread_bps' in period_book.columns:
                            spreads = period_book['spread_bps'].values
                            if len(spreads) > 0:
                                percentile = stats.percentileofscore(spreads, spread_pct) / 100
                                features[f'spread_percentile_{period_name}'] = percentile
                            else:
                                features[f'spread_percentile_{period_name}'] = 0.5
                        else:
                            features[f'spread_percentile_{period_name}'] = 0.5
                    
                    # Order book depth features (if available)
                    if 'depth_0.1pct' in recent_book.columns:
                        features['depth_0.1pct'] = recent_book['depth_0.1pct'].iloc[-1]
                    if 'depth_0.5pct' in recent_book.columns:
                        features['depth_0.5pct'] = recent_book['depth_0.5pct'].iloc[-1]
                    if 'depth_1pct' in recent_book.columns:
                        features['depth_1pct'] = recent_book['depth_1pct'].iloc[-1]
                else:
                    features['spread_abs'] = 0.0
                    features['spread_bps'] = 0.0
                    for period in ['1h', '4h', '24h']:
                        features[f'spread_percentile_{period}'] = 0.5
            else:
                # Default values if orderbook structure unknown
                features['spread_abs'] = 0.0
                features['spread_bps'] = 0.0
                for period in ['1h', '4h', '24h']:
                    features[f'spread_percentile_{period}'] = 0.5
        else:
            features['spread_abs'] = 0.0
            features['spread_bps'] = 0.0
            for period in ['1h', '4h', '24h']:
                features[f'spread_percentile_{period}'] = 0.5
        
        return pd.Series(features)
    
    def _compute_volume_features(self, trades: pd.DataFrame, timestamp: datetime) -> pd.Series:
        """Compute volume and trade flow features"""
        features = {}
        
        window_end = timestamp
        window_5m = window_end - timedelta(minutes=5)
        window_15m = window_end - timedelta(minutes=15)
        window_1h = window_end - timedelta(hours=1)
        window_4h = window_end - timedelta(hours=4)
        
        # Current volume metrics
        recent_trades = trades[trades.index <= window_end]
        
        if not recent_trades.empty:
            # Volume bursts
            for period_name, window_start in [
                ('5m', window_5m),
                ('15m', window_15m),
                ('1h', window_1h)
            ]:
                period_trades = trades[
                    (trades.index >= window_start) & 
                    (trades.index <= window_end)
                ]
                
                if len(period_trades) > 0:
                    current_volume = period_trades['volume'].sum()
                    
                    # Compare to rolling average
                    lookback_start = window_start - timedelta(hours=1)
                    lookback_trades = trades[
                        (trades.index >= lookback_start) & 
                        (trades.index < window_start)
                    ]
                    
                    if len(lookback_trades) > 0:
                        avg_volume = lookback_trades['volume'].sum()
                        if avg_volume > 0:
                            volume_ratio = current_volume / avg_volume
                            features[f'volume_ratio_{period_name}'] = volume_ratio
                        else:
                            features[f'volume_ratio_{period_name}'] = 1.0
                    else:
                        features[f'volume_ratio_{period_name}'] = 1.0
                else:
                    features[f'volume_ratio_{period_name}'] = 0.0
            
            # Trade aggressor direction
            if 'side' in recent_trades.columns:
                buy_volume = recent_trades[recent_trades['side'] == 'b']['volume'].sum()
                sell_volume = recent_trades[recent_trades['side'] == 's']['volume'].sum()
                total_volume = buy_volume + sell_volume
                
                if total_volume > 0:
                    buy_pressure = buy_volume / total_volume
                    features['buy_pressure'] = buy_pressure
                    features['sell_pressure'] = 1.0 - buy_pressure
                else:
                    features['buy_pressure'] = 0.5
                    features['sell_pressure'] = 0.5
            else:
                features['buy_pressure'] = 0.5
                features['sell_pressure'] = 0.5
            
            # VWAP deviation
            for period_name, window_start in [
                ('5m', window_5m),
                ('15m', window_15m),
                ('1h', window_1h)
            ]:
                period_trades = trades[
                    (trades.index >= window_start) & 
                    (trades.index <= window_end)
                ]
                
                if len(period_trades) > 0:
                    # Calculate VWAP
                    vwap = (period_trades['price'] * period_trades['volume']).sum() / period_trades['volume'].sum()
                    current_price = recent_trades['price'].iloc[-1]
                    
                    # Deviation z-score
                    prices = period_trades['price'].values
                    if len(prices) > 1 and prices.std() > 0:
                        z_score = (current_price - vwap) / prices.std()
                        features[f'vwap_deviation_{period_name}'] = z_score
                    else:
                        features[f'vwap_deviation_{period_name}'] = 0.0
                else:
                    features[f'vwap_deviation_{period_name}'] = 0.0
            
            # Average trade size
            avg_trade_size = recent_trades['volume'].mean()
            features['avg_trade_size'] = avg_trade_size
        else:
            features['buy_pressure'] = 0.5
            features['sell_pressure'] = 0.5
            for period in ['5m', '15m', '1h']:
                features[f'volume_ratio_{period}'] = 0.0
                features[f'vwap_deviation_{period}'] = 0.0
            features['avg_trade_size'] = 0.0
        
        return pd.Series(features)
    
    def _compute_volatility_features(self, trades: pd.DataFrame, timestamp: datetime) -> pd.Series:
        """Compute volatility regime features"""
        features = {}
        
        window_end = timestamp
        window_1m = window_end - timedelta(minutes=1)
        window_5m = window_end - timedelta(minutes=5)
        window_15m = window_end - timedelta(minutes=15)
        
        recent_trades = trades[trades.index <= window_end].tail(1000)
        
        if len(recent_trades) > 1:
            prices = recent_trades['price'].values
            
            # Realized volatility for different windows
            for period_name, window_start in [
                ('1m', window_1m),
                ('5m', window_5m),
                ('15m', window_15m)
            ]:
                period_trades = trades[
                    (trades.index >= window_start) & 
                    (trades.index <= window_end)
                ]
                
                if len(period_trades) > 1:
                    period_prices = period_trades['price'].values
                    returns = np.diff(period_prices) / period_prices[:-1]
                    
                    if len(returns) > 0:
                        # Annualized realized volatility (assuming 1-minute intervals)
                        realized_vol = np.std(returns) * np.sqrt(365 * 24 * 60)
                        features[f'realized_vol_{period_name}'] = realized_vol
                    else:
                        features[f'realized_vol_{period_name}'] = 0.0
                else:
                    features[f'realized_vol_{period_name}'] = 0.0
            
            # Parkinson volatility estimator (using high-low)
            if len(recent_trades) > 10:
                # Use price range as proxy for high-low
                price_range = prices.max() - prices.min()
                mean_price = prices.mean()
                if mean_price > 0:
                    parkinson_vol = np.sqrt(
                        (1 / (4 * np.log(2))) * 
                        (np.log(price_range / mean_price)) ** 2
                    )
                    features['parkinson_vol'] = parkinson_vol
                else:
                    features['parkinson_vol'] = 0.0
            else:
                features['parkinson_vol'] = 0.0
            
            # Volatility percentile rank
            all_vols = []
            for i in range(len(prices) - 100):
                window_prices = prices[i:i+100]
                if len(window_prices) > 1:
                    returns = np.diff(window_prices) / window_prices[:-1]
                    vol = np.std(returns)
                    all_vols.append(vol)
            
            if len(all_vols) > 10:
                current_vol = features.get('realized_vol_5m', 0.0)
                if current_vol > 0:
                    percentile = stats.percentileofscore(all_vols, current_vol) / 100
                    features['volatility_percentile'] = percentile
                else:
                    features['volatility_percentile'] = 0.5
            else:
                features['volatility_percentile'] = 0.5
        else:
            for period in ['1m', '5m', '15m']:
                features[f'realized_vol_{period}'] = 0.0
            features['parkinson_vol'] = 0.0
            features['volatility_percentile'] = 0.5
        
        return pd.Series(features)
    
    def _compute_temporal_features(self, timestamp: datetime) -> pd.Series:
        """Compute temporal/cyclical features"""
        features = {}
        
        # Time of day (hour)
        hour = timestamp.hour
        minute = timestamp.minute
        
        # Cyclical encodings (sine/cosine transforms)
        # Hour of day (0-23)
        features['hour_sin'] = np.sin(2 * np.pi * hour / 24)
        features['hour_cos'] = np.cos(2 * np.pi * hour / 24)
        
        # Day of week (0=Monday, 6=Sunday)
        day_of_week = timestamp.weekday()
        features['day_of_week_sin'] = np.sin(2 * np.pi * day_of_week / 7)
        features['day_of_week_cos'] = np.cos(2 * np.pi * day_of_week / 7)
        
        # Minute of hour (for intraday patterns)
        features['minute_sin'] = np.sin(2 * np.pi * minute / 60)
        features['minute_cos'] = np.cos(2 * np.pi * minute / 60)
        
        # Market session indicators
        # US: 9:30 - 16:00 ET (13:30 - 20:00 UTC)
        # EU: 8:00 - 16:30 CET (7:00 - 15:30 UTC)
        # Asia: 9:00 - 16:00 JST (0:00 - 7:00 UTC)
        
        utc_hour = timestamp.hour  # Assuming timestamp is UTC
        
        features['us_session'] = 1.0 if 13 <= utc_hour < 20 else 0.0
        features['eu_session'] = 1.0 if 7 <= utc_hour < 16 else 0.0
        features['asia_session'] = 1.0 if 0 <= utc_hour < 7 else 0.0
        
        # Trading intensity (hours since midnight)
        features['hours_since_midnight'] = hour + minute / 60.0
        
        return pd.Series(features)
    
    def compute_batch_features(self, trades: pd.DataFrame, orderbook: Optional[pd.DataFrame] = None,
                               pair: str = "") -> pd.DataFrame:
        """Compute features for entire DataFrame"""
        if trades.empty:
            return pd.DataFrame()
        
        trades = trades.sort_values('timestamp').copy()
        trades['timestamp'] = pd.to_datetime(trades['timestamp'])
        
        if not isinstance(trades.index, pd.DatetimeIndex):
            trades = trades.set_index('timestamp')
        
        # Sample timestamps (e.g., every second or based on trade frequency)
        timestamps = trades.index.unique()
        
        all_features = []
        for ts in timestamps:
            try:
                features = self.compute_all_features(
                    trades[trades.index <= ts],
                    orderbook[orderbook.index <= ts] if orderbook is not None else None,
                    pair,
                    ts
                )
                all_features.append(features)
            except Exception as e:
                logger.warning(f"Failed to compute features for {ts}: {e}")
                continue
        
        if all_features:
            features_df = pd.DataFrame(all_features)
            features_df.index = timestamps[:len(features_df)]
            return features_df
        
        return pd.DataFrame()
