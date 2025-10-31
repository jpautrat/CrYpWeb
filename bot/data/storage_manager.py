"""
Data storage manager for market data and features.
Handles Parquet file I/O with partitioning and compression.
"""
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from loguru import logger
import os


class StorageManager:
    """Manages storage of raw market data and computed features"""
    
    def __init__(self, base_dir: Path, retention_days: int = 90):
        self.base_dir = Path(base_dir)
        self.retention_days = retention_days
        self.raw_dir = self.base_dir / "raw"
        self.features_dir = self.base_dir / "features"
        
        # Create directories
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.features_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_raw_path(self, pair: str, date: datetime) -> Path:
        """Get path for raw data file"""
        year = date.year
        month = f"{date.month:02d}"
        day = f"{date.day:02d}"
        return self.raw_dir / pair / str(year) / month / day
    
    def _get_features_path(self, pair: str, date: datetime) -> Path:
        """Get path for features file"""
        year = date.year
        month = f"{date.month:02d}"
        day = f"{date.day:02d}"
        return self.features_dir / pair / str(year) / month / day
    
    def save_trades(self, pair: str, trades: pd.DataFrame, append: bool = True):
        """
        Save trade data to Parquet file.
        
        Args:
            pair: Trading pair symbol
            trades: DataFrame with columns: timestamp, price, volume, side
            append: If True, append to existing file; if False, overwrite
        """
        if trades.empty:
            return
        
        # Get date from first timestamp
        first_ts = pd.to_datetime(trades['timestamp'].iloc[0])
        date = first_ts.date()
        file_dir = self._get_raw_path(pair, datetime.combine(date, datetime.min.time()))
        file_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = file_dir / "trades.parquet"
        
        # Ensure proper types
        trades = trades.copy()
        if 'timestamp' in trades.columns:
            trades['timestamp'] = pd.to_datetime(trades['timestamp'])
        
        try:
            if append and file_path.exists():
                # Read existing data
                existing = pd.read_parquet(file_path)
                # Combine and remove duplicates
                combined = pd.concat([existing, trades]).drop_duplicates(subset=['timestamp'], keep='last')
                combined = combined.sort_values('timestamp')
                # Write back
                table = pa.Table.from_pandas(combined)
                pq.write_table(
                    table,
                    file_path,
                    compression='snappy',
                    use_dictionary=True
                )
            else:
                # Write new file
                table = pa.Table.from_pandas(trades)
                pq.write_table(
                    table,
                    file_path,
                    compression='snappy',
                    use_dictionary=True
                )
            
            logger.debug(f"Saved {len(trades)} trades for {pair} to {file_path}")
        
        except Exception as e:
            logger.error(f"Failed to save trades for {pair}: {e}")
    
    def save_orderbook(self, pair: str, book: pd.DataFrame, append: bool = True):
        """Save order book snapshot to Parquet file"""
        if book.empty:
            return
        
        first_ts = pd.to_datetime(book['timestamp'].iloc[0])
        date = first_ts.date()
        file_dir = self._get_raw_path(pair, date)
        file_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = file_dir / "orderbook.parquet"
        
        book = book.copy()
        if 'timestamp' in book.columns:
            book['timestamp'] = pd.to_datetime(book['timestamp'])
        
        try:
            if append and file_path.exists():
                existing = pd.read_parquet(file_path)
                combined = pd.concat([existing, book]).drop_duplicates(subset=['timestamp'], keep='last')
                combined = combined.sort_values('timestamp')
                table = pa.Table.from_pandas(combined)
                pq.write_table(table, file_path, compression='snappy', use_dictionary=True)
            else:
                table = pa.Table.from_pandas(book)
                pq.write_table(table, file_path, compression='snappy', use_dictionary=True)
            
            logger.debug(f"Saved order book snapshot for {pair}")
        
        except Exception as e:
            logger.error(f"Failed to save order book for {pair}: {e}")
    
    def save_features(self, pair: str, features: pd.DataFrame, version: str = "v1"):
        """
        Save computed features to Parquet file.
        
        Args:
            pair: Trading pair symbol
            features: DataFrame with computed features
            version: Feature version identifier
        """
        if features.empty:
            return
        
        first_ts = pd.to_datetime(features.index[0]) if isinstance(features.index, pd.DatetimeIndex) else pd.to_datetime(features['timestamp'].iloc[0])
        date = first_ts.date()
        file_dir = self._get_features_path(pair, datetime.combine(date, datetime.min.time()))
        file_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = file_dir / f"features_{version}.parquet"
        
        try:
            table = pa.Table.from_pandas(features.reset_index() if isinstance(features.index, pd.DatetimeIndex) else features)
            pq.write_table(
                table,
                file_path,
                compression='snappy',
                use_dictionary=True
            )
            logger.debug(f"Saved features for {pair} to {file_path}")
        
        except Exception as e:
            logger.error(f"Failed to save features for {pair}: {e}")
    
    def load_trades(self, pair: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Load trade data for date range"""
        all_trades = []
        current_date = start_date.date()
        end_date_only = end_date.date()
        
        while current_date <= end_date_only:
            file_dir = self._get_raw_path(pair, datetime.combine(current_date, datetime.min.time()))
            file_path = file_dir / "trades.parquet"
            
            if file_path.exists():
                try:
                    df = pd.read_parquet(file_path)
                    all_trades.append(df)
                except Exception as e:
                    logger.warning(f"Failed to load trades from {file_path}: {e}")
            
            current_date += timedelta(days=1)
        
        if all_trades:
            combined = pd.concat(all_trades, ignore_index=True)
            combined = combined.sort_values('timestamp')
            # Filter by date range
            combined = combined[
                (combined['timestamp'] >= start_date) & 
                (combined['timestamp'] <= end_date)
            ]
            return combined
        
        return pd.DataFrame()
    
    def load_features(self, pair: str, start_date: datetime, end_date: datetime, version: str = "v1") -> pd.DataFrame:
        """Load features for date range"""
        all_features = []
        current_date = start_date.date()
        end_date_only = end_date.date()
        
        while current_date <= end_date_only:
            file_dir = self._get_features_path(pair, datetime.combine(current_date, datetime.min.time()))
            file_path = file_dir / f"features_{version}.parquet"
            
            if file_path.exists():
                try:
                    df = pd.read_parquet(file_path)
                    all_features.append(df)
                except Exception as e:
                    logger.warning(f"Failed to load features from {file_path}: {e}")
            
            current_date += timedelta(days=1)
        
        if all_features:
            combined = pd.concat(all_features, ignore_index=True)
            if 'timestamp' in combined.columns:
                combined['timestamp'] = pd.to_datetime(combined['timestamp'])
                combined = combined.set_index('timestamp')
            combined = combined.sort_index()
            # Filter by date range
            combined = combined[
                (combined.index >= start_date) & 
                (combined.index <= end_date)
            ]
            return combined
        
        return pd.DataFrame()
    
    def cleanup_old_data(self):
        """Clean up old data beyond retention period"""
        cutoff_date = datetime.now() - timedelta(days=self.retention_days)
        cutoff_path = cutoff_date.strftime("%Y/%m/%d")
        
        logger.info(f"Cleaning up data older than {cutoff_date.date()}")
        
        # Clean raw data
        for pair_dir in self.raw_dir.iterdir():
            if pair_dir.is_dir():
                for year_dir in pair_dir.iterdir():
                    if year_dir.is_dir():
                        year = int(year_dir.name)
                        for month_dir in year_dir.iterdir():
                            if month_dir.is_dir():
                                month = int(month_dir.name)
                                for day_dir in month_dir.iterdir():
                                    if day_dir.is_dir():
                                        day = int(day_dir.name)
                                        dir_date = datetime(year, month, day)
                                        if dir_date < cutoff_date:
                                            try:
                                                import shutil
                                                shutil.rmtree(day_dir)
                                                logger.info(f"Removed old data: {day_dir}")
                                            except Exception as e:
                                                logger.error(f"Failed to remove {day_dir}: {e}")
        
        # Clean features data (similar logic)
        # ... (similar implementation for features_dir)
    
    def get_data_statistics(self) -> Dict:
        """Get statistics about stored data"""
        stats = {
            'pairs': [],
            'total_trade_files': 0,
            'total_feature_files': 0,
            'oldest_date': None,
            'newest_date': None
        }
        
        # Analyze raw data
        for pair_dir in self.raw_dir.iterdir():
            if pair_dir.is_dir():
                pair = pair_dir.name
                stats['pairs'].append(pair)
                
                for year_dir in pair_dir.iterdir():
                    if year_dir.is_dir():
                        for month_dir in year_dir.iterdir():
                            if month_dir.is_dir():
                                for day_dir in month_dir.iterdir():
                                    if day_dir.is_dir():
                                        trade_file = day_dir / "trades.parquet"
                                        if trade_file.exists():
                                            stats['total_trade_files'] += 1
        
        return stats
