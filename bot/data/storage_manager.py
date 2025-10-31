"""
Data storage manager for Parquet file I/O.
Handles raw tick data and feature storage with partitioning.
"""
import pandas as pd
import pyarrow.parquet as pq
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List
from loguru import logger

from bot.config.settings import settings


class StorageManager:
    """Manages data storage in Parquet format."""
    
    def __init__(self):
        """Initialize storage manager."""
        self.raw_dir = settings.system.raw_data_dir
        self.features_dir = settings.system.features_dir
        
        # Create directories
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.features_dir.mkdir(parents=True, exist_ok=True)
    
    def store_tick_data(self, pair: str, data: pd.DataFrame):
        """
        Store tick data (trades) to Parquet file.
        
        Args:
            pair: Trading pair
            data: DataFrame with columns: timestamp, price, volume, side
        """
        if data.empty:
            return
        
        # Create partition path: data/raw/{pair}/{YYYY}/{MM}/{DD}/
        now = datetime.utcnow()
        partition_path = (
            self.raw_dir / pair.replace("/", "_") / 
            str(now.year) / f"{now.month:02d}" / f"{now.day:02d}"
        )
        partition_path.mkdir(parents=True, exist_ok=True)
        
        # Append to daily file
        file_path = partition_path / "trades.parquet"
        
        try:
            if file_path.exists():
                # Read existing data
                existing = pd.read_parquet(file_path)
                # Combine and deduplicate
                combined = pd.concat([existing, data]).drop_duplicates(subset=['timestamp'], keep='last')
                combined = combined.sort_values('timestamp')
                # Write back
                combined.to_parquet(file_path, compression='snappy', index=False)
            else:
                data.to_parquet(file_path, compression='snappy', index=False)
        except Exception as e:
            logger.error(f"Failed to store tick data: {e}")
    
    def store_orderbook_snapshot(self, pair: str, snapshot: Dict):
        """
        Store order book snapshot.
        
        Args:
            pair: Trading pair
            snapshot: Order book data
        """
        # Similar implementation for order book snapshots
        now = datetime.utcnow()
        partition_path = (
            self.raw_dir / pair.replace("/", "_") / 
            str(now.year) / f"{now.month:02d}" / f"{now.day:02d}"
        )
        partition_path.mkdir(parents=True, exist_ok=True)
        
        file_path = partition_path / "orderbook.parquet"
        
        try:
            # Convert snapshot to DataFrame
            df = pd.DataFrame([{
                'timestamp': now,
                'bids': snapshot.get('bids', []),
                'asks': snapshot.get('asks', []),
            }])
            
            if file_path.exists():
                existing = pd.read_parquet(file_path)
                combined = pd.concat([existing, df])
                combined.to_parquet(file_path, compression='snappy', index=False)
            else:
                df.to_parquet(file_path, compression='snappy', index=False)
        except Exception as e:
            logger.error(f"Failed to store orderbook snapshot: {e}")
    
    def store_features(self, pair: str, features: pd.DataFrame):
        """
        Store computed features.
        
        Args:
            pair: Trading pair
            features: Feature DataFrame
        """
        if features.empty:
            return
        
        now = datetime.utcnow()
        partition_path = (
            self.features_dir / pair.replace("/", "_") / 
            str(now.year) / f"{now.month:02d}" / f"{now.day:02d}"
        )
        partition_path.mkdir(parents=True, exist_ok=True)
        
        file_path = partition_path / "features.parquet"
        
        try:
            if file_path.exists():
                existing = pd.read_parquet(file_path)
                combined = pd.concat([existing, features]).drop_duplicates(keep='last')
                combined = combined.sort_index()
                combined.to_parquet(file_path, compression='snappy', index=False)
            else:
                features.to_parquet(file_path, compression='snappy', index=False)
        except Exception as e:
            logger.error(f"Failed to store features: {e}")
    
    def load_historical_data(self, pair: str, days: int = 30) -> Optional[pd.DataFrame]:
        """
        Load historical tick data.
        
        Args:
            pair: Trading pair
            days: Number of days to load
            
        Returns:
            DataFrame with historical data
        """
        # Load data from last N days
        pair_dir = self.raw_dir / pair.replace("/", "_")
        if not pair_dir.exists():
            return None
        
        dataframes = []
        end_date = datetime.utcnow()
        
        for i in range(days):
            date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
            date = date.replace(day=date.day - i)
            
            file_path = (
                pair_dir / str(date.year) / f"{date.month:02d}" / 
                f"{date.day:02d}" / "trades.parquet"
            )
            
            if file_path.exists():
                try:
                    df = pd.read_parquet(file_path)
                    dataframes.append(df)
                except Exception as e:
                    logger.warning(f"Failed to load {file_path}: {e}")
        
        if dataframes:
            return pd.concat(dataframes, ignore_index=True).sort_values('timestamp')
        return None
