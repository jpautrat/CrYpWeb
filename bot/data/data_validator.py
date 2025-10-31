"""
Data validation and quality checks for market data.
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from datetime import datetime
from loguru import logger


class DataValidator:
    """Validates market data quality and detects anomalies"""
    
    def __init__(self, tolerance_pct: float = 5.0):
        self.tolerance_pct = tolerance_pct
    
    def validate_trades(self, trades: pd.DataFrame) -> Tuple[bool, List[str]]:
        """
        Validate trade data.
        Returns (is_valid, list_of_errors)
        """
        errors = []
        
        if trades.empty:
            return False, ["Empty trades DataFrame"]
        
        required_columns = ['timestamp', 'price', 'volume']
        missing = [col for col in required_columns if col not in trades.columns]
        if missing:
            errors.append(f"Missing required columns: {missing}")
        
        # Check for NaN values
        for col in required_columns:
            if col in trades.columns:
                nan_count = trades[col].isna().sum()
                if nan_count > 0:
                    errors.append(f"Column {col} has {nan_count} NaN values")
        
        # Check price validity
        if 'price' in trades.columns:
            if (trades['price'] <= 0).any():
                errors.append("Found non-positive prices")
            
            # Check for extreme outliers (beyond 3 standard deviations)
            prices = trades['price'].dropna()
            if len(prices) > 10:
                mean_price = prices.mean()
                std_price = prices.std()
                outliers = prices[abs(prices - mean_price) > 3 * std_price]
                if len(outliers) > len(prices) * 0.01:  # More than 1% outliers
                    errors.append(f"Excessive price outliers: {len(outliers)}")
        
        # Check volume validity
        if 'volume' in trades.columns:
            if (trades['volume'] < 0).any():
                errors.append("Found negative volumes")
        
        # Check timestamp monotonicity
        if 'timestamp' in trades.columns:
            timestamps = pd.to_datetime(trades['timestamp'])
            if not timestamps.is_monotonic_increasing:
                errors.append("Timestamps are not monotonically increasing")
        
        return len(errors) == 0, errors
    
    def validate_orderbook(self, orderbook: pd.DataFrame) -> Tuple[bool, List[str]]:
        """Validate order book data"""
        errors = []
        
        if orderbook.empty:
            return False, ["Empty orderbook DataFrame"]
        
        # Basic structure checks
        required_cols = ['timestamp']
        missing = [col for col in required_cols if col not in orderbook.columns]
        if missing:
            errors.append(f"Missing required columns: {missing}")
        
        # Check bid-ask consistency
        if 'best_bid' in orderbook.columns and 'best_ask' in orderbook.columns:
            invalid_spread = orderbook[orderbook['best_bid'] >= orderbook['best_ask']]
            if len(invalid_spread) > 0:
                errors.append(f"Found {len(invalid_spread)} invalid bid-ask spreads")
        
        return len(errors) == 0, errors
    
    def detect_anomalies(self, trades: pd.DataFrame) -> pd.DataFrame:
        """Detect anomalous trades"""
        anomalies = pd.DataFrame()
        
        if trades.empty or 'price' not in trades.columns:
            return anomalies
        
        prices = trades['price'].values
        
        # Z-score based anomaly detection
        if len(prices) > 10:
            mean_price = prices.mean()
            std_price = prices.std()
            
            if std_price > 0:
                z_scores = np.abs((prices - mean_price) / std_price)
                anomaly_mask = z_scores > 3.0
                
                if anomaly_mask.any():
                    anomalies = trades[anomaly_mask].copy()
                    anomalies['z_score'] = z_scores[anomaly_mask]
                    logger.warning(f"Detected {len(anomalies)} anomalous trades")
        
        return anomalies
    
    def interpolate_missing(self, data: pd.DataFrame, method: str = 'linear') -> pd.DataFrame:
        """Interpolate missing values"""
        if data.empty:
            return data
        
        numeric_cols = data.select_dtypes(include=[np.number]).columns
        interpolated = data.copy()
        
        for col in numeric_cols:
            if interpolated[col].isna().any():
                interpolated[col] = interpolated[col].interpolate(method=method)
        
        return interpolated
    
    def validate_latency(self, timestamp: datetime, received_at: datetime, max_latency_ms: float = 1000) -> bool:
        """Validate data latency"""
        latency_ms = (received_at - timestamp).total_seconds() * 1000
        
        if latency_ms > max_latency_ms:
            logger.warning(f"High latency detected: {latency_ms:.2f}ms")
            return False
        
        return True
