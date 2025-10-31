"""
Storage Manager - Parquet-based data storage system
Handles efficient storage and retrieval of market data and features.
"""

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from loguru import logger
import shutil


class StorageManager:
    """
    Manages data storage using Parquet files.
    Implements efficient partitioning and compression strategies.
    """
    
    def __init__(self, base_path: str = "data"):
        """
        Initialize storage manager.
        
        Args:
            base_path: Base directory for data storage
        """
        self.base_path = Path(base_path)
        self.raw_path = self.base_path / "raw"
        self.features_path = self.base_path / "features"
        self.models_path = self.base_path / "models"
        
        # Create directories
        self.raw_path.mkdir(parents=True, exist_ok=True)
        self.features_path.mkdir(parents=True, exist_ok=True)
        self.models_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"StorageManager initialized: {self.base_path}")
    
    def _get_partition_path(
        self,
        base_path: Path,
        pair: str,
        timestamp: datetime,
        data_type: str = "data"
    ) -> Path:
        """
        Get partitioned file path.
        
        Args:
            base_path: Base directory
            pair: Trading pair
            timestamp: Timestamp for partitioning
            data_type: Type of data ('trades', 'book', 'features', etc.)
            
        Returns:
            Path to partitioned file
        """
        # Partition by pair/year/month/day
        year = timestamp.strftime("%Y")
        month = timestamp.strftime("%m")
        day = timestamp.strftime("%d")
        
        partition_dir = base_path / pair / year / month / day
        partition_dir.mkdir(parents=True, exist_ok=True)
        
        return partition_dir / f"{data_type}.parquet"
    
    def store_tick_data(self, pair: str, data: pd.DataFrame):
        """
        Store tick/trade data.
        
        Args:
            pair: Trading pair
            data: DataFrame with columns: timestamp, price, volume, side
        """
        if data.empty:
            return
        
        # Ensure timestamp column
        if 'timestamp' not in data.columns:
            data['timestamp'] = pd.Timestamp.now()
        
        # Partition by day
        for date, group in data.groupby(pd.Grouper(key='timestamp', freq='D')):
            if group.empty:
                continue
            
            file_path = self._get_partition_path(
                self.raw_path,
                pair,
                date,
                'trades'
            )
            
            # Append or create
            if file_path.exists():
                existing = pd.read_parquet(file_path)
                combined = pd.concat([existing, group], ignore_index=True)
                combined = combined.drop_duplicates(subset=['timestamp'], keep='last')
                combined = combined.sort_values('timestamp')
                combined.to_parquet(file_path, compression='snappy', index=False)
            else:
                group.to_parquet(file_path, compression='snappy', index=False)
        
        logger.debug(f"Stored {len(data)} ticks for {pair}")
    
    def store_orderbook_data(self, pair: str, data: pd.DataFrame):
        """
        Store order book snapshots.
        
        Args:
            pair: Trading pair
            data: DataFrame with order book data
        """
        if data.empty:
            return
        
        if 'timestamp' not in data.columns:
            data['timestamp'] = pd.Timestamp.now()
        
        for date, group in data.groupby(pd.Grouper(key='timestamp', freq='D')):
            if group.empty:
                continue
            
            file_path = self._get_partition_path(
                self.raw_path,
                pair,
                date,
                'orderbook'
            )
            
            if file_path.exists():
                existing = pd.read_parquet(file_path)
                combined = pd.concat([existing, group], ignore_index=True)
                combined = combined.drop_duplicates(subset=['timestamp'], keep='last')
                combined = combined.sort_values('timestamp')
                combined.to_parquet(file_path, compression='snappy', index=False)
            else:
                group.to_parquet(file_path, compression='snappy', index=False)
        
        logger.debug(f"Stored {len(data)} orderbook snapshots for {pair}")
    
    def store_features(self, pair: str, features: pd.DataFrame):
        """
        Store computed features.
        
        Args:
            pair: Trading pair
            features: DataFrame with feature columns
        """
        if features.empty:
            return
        
        if 'timestamp' not in features.columns:
            features['timestamp'] = pd.Timestamp.now()
        
        for date, group in features.groupby(pd.Grouper(key='timestamp', freq='D')):
            if group.empty:
                continue
            
            file_path = self._get_partition_path(
                self.features_path,
                pair,
                date,
                'features'
            )
            
            if file_path.exists():
                existing = pd.read_parquet(file_path)
                combined = pd.concat([existing, group], ignore_index=True)
                combined = combined.drop_duplicates(subset=['timestamp'], keep='last')
                combined = combined.sort_values('timestamp')
                combined.to_parquet(file_path, compression='snappy', index=False)
            else:
                group.to_parquet(file_path, compression='snappy', index=False)
        
        logger.debug(f"Stored {len(features)} feature rows for {pair}")
    
    def load_tick_data(
        self,
        pair: str,
        start_time: datetime,
        end_time: datetime
    ) -> pd.DataFrame:
        """
        Load tick/trade data for a time range.
        
        Args:
            pair: Trading pair
            start_time: Start timestamp
            end_time: End timestamp
            
        Returns:
            DataFrame with tick data
        """
        all_data = []
        
        # Iterate through days in range
        current_date = start_time.date()
        end_date = end_time.date()
        
        while current_date <= end_date:
            file_path = self._get_partition_path(
                self.raw_path,
                pair,
                datetime.combine(current_date, datetime.min.time()),
                'trades'
            )
            
            if file_path.exists():
                df = pd.read_parquet(file_path)
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                
                # Filter to time range
                df = df[
                    (df['timestamp'] >= start_time) &
                    (df['timestamp'] <= end_time)
                ]
                
                if not df.empty:
                    all_data.append(df)
            
            current_date += timedelta(days=1)
        
        if all_data:
            result = pd.concat(all_data, ignore_index=True)
            result = result.sort_values('timestamp')
            return result
        
        return pd.DataFrame()
    
    def load_features(
        self,
        pair: str,
        start_time: datetime,
        end_time: datetime
    ) -> pd.DataFrame:
        """
        Load computed features for a time range.
        
        Args:
            pair: Trading pair
            start_time: Start timestamp
            end_time: End timestamp
            
        Returns:
            DataFrame with features
        """
        all_data = []
        
        current_date = start_time.date()
        end_date = end_time.date()
        
        while current_date <= end_date:
            file_path = self._get_partition_path(
                self.features_path,
                pair,
                datetime.combine(current_date, datetime.min.time()),
                'features'
            )
            
            if file_path.exists():
                df = pd.read_parquet(file_path)
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                
                df = df[
                    (df['timestamp'] >= start_time) &
                    (df['timestamp'] <= end_time)
                ]
                
                if not df.empty:
                    all_data.append(df)
            
            current_date += timedelta(days=1)
        
        if all_data:
            result = pd.concat(all_data, ignore_index=True)
            result = result.sort_values('timestamp')
            return result
        
        return pd.DataFrame()
    
    def cleanup_old_data(self, retention_days: int = 90):
        """
        Remove data older than retention period.
        
        Args:
            retention_days: Number of days to keep
        """
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        
        removed_count = 0
        
        for data_path in [self.raw_path, self.features_path]:
            for pair_dir in data_path.iterdir():
                if not pair_dir.is_dir():
                    continue
                
                for year_dir in pair_dir.iterdir():
                    if not year_dir.is_dir():
                        continue
                    
                    for month_dir in year_dir.iterdir():
                        if not month_dir.is_dir():
                            continue
                        
                        for day_dir in month_dir.iterdir():
                            if not day_dir.is_dir():
                                continue
                            
                            # Parse date from path
                            try:
                                date_str = f"{year_dir.name}-{month_dir.name}-{day_dir.name}"
                                file_date = datetime.strptime(date_str, "%Y-%m-%d")
                                
                                if file_date < cutoff_date:
                                    shutil.rmtree(day_dir)
                                    removed_count += 1
                            except Exception as e:
                                logger.warning(f"Error cleaning up {day_dir}: {e}")
        
        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} old data partitions")
    
    def get_storage_stats(self) -> Dict:
        """
        Get storage statistics.
        
        Returns:
            Dictionary with storage metrics
        """
        def get_dir_size(path: Path) -> int:
            """Get total size of directory"""
            total = 0
            for item in path.rglob('*'):
                if item.is_file():
                    total += item.stat().st_size
            return total
        
        raw_size = get_dir_size(self.raw_path)
        features_size = get_dir_size(self.features_path)
        models_size = get_dir_size(self.models_path)
        
        return {
            'raw_data_mb': raw_size / (1024 * 1024),
            'features_mb': features_size / (1024 * 1024),
            'models_mb': models_size / (1024 * 1024),
            'total_mb': (raw_size + features_size + models_size) / (1024 * 1024)
        }
