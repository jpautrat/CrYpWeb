"""
Data Validator - Quality checks and anomaly detection for market data
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from loguru import logger


class DataValidator:
    """
    Validates market data quality and detects anomalies.
    Critical for ensuring ML models receive clean data.
    """
    
    def __init__(
        self,
        max_price_change_pct: float = 20.0,
        max_spread_pct: float = 5.0,
        min_tick_interval_ms: float = 0.1
    ):
        """
        Initialize data validator.
        
        Args:
            max_price_change_pct: Maximum acceptable price change %
            max_spread_pct: Maximum acceptable spread %
            min_tick_interval_ms: Minimum time between ticks
        """
        self.max_price_change_pct = max_price_change_pct
        self.max_spread_pct = max_spread_pct
        self.min_tick_interval_ms = min_tick_interval_ms
        
        self.validation_stats: Dict = {
            'total_checks': 0,
            'failed_checks': 0,
            'anomalies_detected': 0
        }
        
        logger.info("DataValidator initialized")
    
    def validate_tick(
        self,
        pair: str,
        price: float,
        volume: float,
        timestamp: datetime,
        previous_price: Optional[float] = None
    ) -> Tuple[bool, str]:
        """
        Validate a single tick.
        
        Args:
            pair: Trading pair
            price: Trade price
            volume: Trade volume
            timestamp: Tick timestamp
            previous_price: Previous price for change validation
            
        Returns:
            Tuple of (is_valid, reason)
        """
        self.validation_stats['total_checks'] += 1
        
        # Check price is positive
        if price <= 0:
            self.validation_stats['failed_checks'] += 1
            return False, f"Invalid price: {price}"
        
        # Check volume is positive
        if volume <= 0:
            self.validation_stats['failed_checks'] += 1
            return False, f"Invalid volume: {volume}"
        
        # Check price change if previous price available
        if previous_price is not None and previous_price > 0:
            price_change_pct = abs(price - previous_price) / previous_price * 100
            
            if price_change_pct > self.max_price_change_pct:
                self.validation_stats['anomalies_detected'] += 1
                logger.warning(
                    f"Large price change detected for {pair}: "
                    f"{price_change_pct:.2f}% (${previous_price:.2f} → ${price:.2f})"
                )
                # Don't reject, just log
        
        # Check timestamp is reasonable (not in future, not too old)
        now = datetime.now()
        if timestamp > now + timedelta(seconds=10):
            self.validation_stats['failed_checks'] += 1
            return False, "Timestamp in future"
        
        if timestamp < now - timedelta(hours=24):
            self.validation_stats['failed_checks'] += 1
            return False, "Timestamp too old"
        
        return True, "Valid"
    
    def validate_orderbook(
        self,
        pair: str,
        bid_price: float,
        ask_price: float,
        timestamp: datetime
    ) -> Tuple[bool, str]:
        """
        Validate order book snapshot.
        
        Args:
            pair: Trading pair
            bid_price: Best bid price
            ask_price: Best ask price
            timestamp: Snapshot timestamp
            
        Returns:
            Tuple of (is_valid, reason)
        """
        self.validation_stats['total_checks'] += 1
        
        # Check prices are positive
        if bid_price <= 0 or ask_price <= 0:
            self.validation_stats['failed_checks'] += 1
            return False, "Invalid bid/ask prices"
        
        # Check bid < ask
        if bid_price >= ask_price:
            self.validation_stats['failed_checks'] += 1
            return False, f"Crossed book: bid={bid_price} >= ask={ask_price}"
        
        # Check spread is reasonable
        mid_price = (bid_price + ask_price) / 2
        spread_pct = (ask_price - bid_price) / mid_price * 100
        
        if spread_pct > self.max_spread_pct:
            self.validation_stats['anomalies_detected'] += 1
            logger.warning(
                f"Wide spread detected for {pair}: {spread_pct:.3f}% "
                f"(bid=${bid_price:.2f}, ask=${ask_price:.2f})"
            )
            # Don't reject - wide spreads can be legitimate
        
        return True, "Valid"
    
    def validate_dataframe(
        self,
        df: pd.DataFrame,
        required_columns: List[str]
    ) -> Tuple[bool, str]:
        """
        Validate a DataFrame has required structure.
        
        Args:
            df: DataFrame to validate
            required_columns: List of required column names
            
        Returns:
            Tuple of (is_valid, reason)
        """
        if df.empty:
            return False, "DataFrame is empty"
        
        # Check required columns exist
        missing_columns = set(required_columns) - set(df.columns)
        if missing_columns:
            return False, f"Missing columns: {missing_columns}"
        
        # Check for null values in critical columns
        null_counts = df[required_columns].isnull().sum()
        if null_counts.any():
            return False, f"Null values found: {null_counts[null_counts > 0].to_dict()}"
        
        return True, "Valid"
    
    def detect_missing_data(
        self,
        df: pd.DataFrame,
        timestamp_col: str = 'timestamp',
        expected_interval_seconds: float = 1.0
    ) -> List[Dict]:
        """
        Detect gaps in time series data.
        
        Args:
            df: DataFrame with timestamp column
            timestamp_col: Name of timestamp column
            expected_interval_seconds: Expected time between samples
            
        Returns:
            List of detected gaps
        """
        if df.empty or len(df) < 2:
            return []
        
        df = df.sort_values(timestamp_col)
        df[timestamp_col] = pd.to_datetime(df[timestamp_col])
        
        # Calculate time differences
        time_diffs = df[timestamp_col].diff()
        
        # Find gaps larger than 2x expected interval
        gap_threshold = pd.Timedelta(seconds=expected_interval_seconds * 2)
        gaps = time_diffs[time_diffs > gap_threshold]
        
        gap_list = []
        for idx, gap_size in gaps.items():
            gap_list.append({
                'index': idx,
                'gap_seconds': gap_size.total_seconds(),
                'timestamp': df.loc[idx, timestamp_col]
            })
        
        if gap_list:
            logger.warning(f"Detected {len(gap_list)} data gaps")
        
        return gap_list
    
    def detect_outliers(
        self,
        df: pd.DataFrame,
        column: str,
        method: str = 'iqr',
        threshold: float = 3.0
    ) -> pd.Series:
        """
        Detect outliers in a data series.
        
        Args:
            df: DataFrame with data
            column: Column to analyze
            method: 'iqr' or 'zscore'
            threshold: Threshold for outlier detection
            
        Returns:
            Boolean series indicating outliers
        """
        if df.empty or column not in df.columns:
            return pd.Series(dtype=bool)
        
        if method == 'iqr':
            Q1 = df[column].quantile(0.25)
            Q3 = df[column].quantile(0.75)
            IQR = Q3 - Q1
            
            lower_bound = Q1 - threshold * IQR
            upper_bound = Q3 + threshold * IQR
            
            outliers = (df[column] < lower_bound) | (df[column] > upper_bound)
            
        elif method == 'zscore':
            mean = df[column].mean()
            std = df[column].std()
            
            if std == 0:
                return pd.Series([False] * len(df))
            
            z_scores = np.abs((df[column] - mean) / std)
            outliers = z_scores > threshold
        
        else:
            raise ValueError(f"Unknown method: {method}")
        
        outlier_count = outliers.sum()
        if outlier_count > 0:
            logger.debug(f"Detected {outlier_count} outliers in {column}")
        
        return outliers
    
    def interpolate_missing(
        self,
        df: pd.DataFrame,
        method: str = 'linear',
        limit: int = 5
    ) -> pd.DataFrame:
        """
        Interpolate missing values in DataFrame.
        
        Args:
            df: DataFrame with potential missing values
            method: Interpolation method
            limit: Maximum consecutive NaNs to fill
            
        Returns:
            DataFrame with interpolated values
        """
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        
        for col in numeric_cols:
            df[col] = df[col].interpolate(method=method, limit=limit)
        
        return df
    
    def get_validation_stats(self) -> Dict:
        """Get validation statistics"""
        stats = self.validation_stats.copy()
        
        if stats['total_checks'] > 0:
            stats['fail_rate'] = stats['failed_checks'] / stats['total_checks']
            stats['anomaly_rate'] = stats['anomalies_detected'] / stats['total_checks']
        else:
            stats['fail_rate'] = 0.0
            stats['anomaly_rate'] = 0.0
        
        return stats
