"""
Model registry for storing and loading trained ML models.
"""
import pickle
import joblib
from pathlib import Path
from typing import Optional, Dict
from datetime import datetime
from loguru import logger
import pandas as pd
import numpy as np


class ModelRegistry:
    """Manages ML model storage and retrieval"""
    
    def __init__(self, models_dir: Path):
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        # In-memory model cache
        self.model_cache: Dict[str, Dict] = {}
    
    def save_model(self, pair: str, model, model_type: str, version: str = "latest",
                   metadata: Optional[Dict] = None):
        """
        Save trained model to disk.
        
        Args:
            pair: Trading pair symbol
            model: Trained model object
            model_type: 'xgboost', 'lightgbm', 'lstm', etc.
            version: Model version identifier
            metadata: Additional metadata (metrics, training date, etc.)
        """
        pair_dir = self.models_dir / pair
        pair_dir.mkdir(parents=True, exist_ok=True)
        
        # Save model
        model_file = pair_dir / f"{model_type}_{version}.pkl"
        joblib.dump(model, model_file)
        
        # Save metadata
        if metadata is None:
            metadata = {}
        
        metadata['pair'] = pair
        metadata['model_type'] = model_type
        metadata['version'] = version
        metadata['saved_at'] = datetime.now().isoformat()
        
        metadata_file = pair_dir / f"{model_type}_{version}_metadata.pkl"
        with open(metadata_file, 'wb') as f:
            pickle.dump(metadata, f)
        
        logger.info(f"Saved {model_type} model for {pair} (version {version})")
    
    def load_model(self, pair: str, model_type: str, version: str = "latest"):
        """
        Load model from disk.
        
        Returns:
            Model object or None if not found
        """
        cache_key = f"{pair}_{model_type}_{version}"
        
        # Check cache
        if cache_key in self.model_cache:
            return self.model_cache[cache_key]['model']
        
        # Load from disk
        pair_dir = self.models_dir / pair
        model_file = pair_dir / f"{model_type}_{version}.pkl"
        
        if not model_file.exists():
            logger.warning(f"Model not found: {model_file}")
            return None
        
        try:
            model = joblib.load(model_file)
            
            # Load metadata
            metadata_file = pair_dir / f"{model_type}_{version}_metadata.pkl"
            metadata = {}
            if metadata_file.exists():
                with open(metadata_file, 'rb') as f:
                    metadata = pickle.load(f)
            
            # Cache
            self.model_cache[cache_key] = {
                'model': model,
                'metadata': metadata
            }
            
            logger.info(f"Loaded {model_type} model for {pair} (version {version})")
            return model
        
        except Exception as e:
            logger.error(f"Failed to load model {model_file}: {e}")
            return None
    
    def get_model_metadata(self, pair: str, model_type: str, version: str = "latest") -> Optional[Dict]:
        """Get metadata for a model"""
        cache_key = f"{pair}_{model_type}_{version}"
        
        if cache_key in self.model_cache:
            return self.model_cache[cache_key].get('metadata')
        
        pair_dir = self.models_dir / pair
        metadata_file = pair_dir / f"{model_type}_{version}_metadata.pkl"
        
        if metadata_file.exists():
            try:
                with open(metadata_file, 'rb') as f:
                    return pickle.load(f)
            except Exception as e:
                logger.error(f"Failed to load metadata: {e}")
        
        return None
    
    def list_models(self, pair: Optional[str] = None) -> Dict:
        """List all available models"""
        models = {}
        
        if pair:
            pair_dir = self.models_dir / pair
            if pair_dir.exists():
                models[pair] = self._list_pair_models(pair_dir)
        else:
            for pair_dir in self.models_dir.iterdir():
                if pair_dir.is_dir():
                    pair_name = pair_dir.name
                    models[pair_name] = self._list_pair_models(pair_dir)
        
        return models
    
    def _list_pair_models(self, pair_dir: Path) -> List[str]:
        """List models for a specific pair"""
        models = []
        for file in pair_dir.glob("*.pkl"):
            if "_metadata" not in file.name:
                models.append(file.stem)
        return models
    
    def get_latest_version(self, pair: str, model_type: str) -> Optional[str]:
        """Get latest version of a model type for a pair"""
        pair_dir = self.models_dir / pair
        if not pair_dir.exists():
            return None
        
        versions = []
        for file in pair_dir.glob(f"{model_type}_*.pkl"):
            if "_metadata" not in file.name:
                version = file.stem.replace(f"{model_type}_", "")
                if version != "latest":
                    versions.append(version)
        
        if versions:
            # Sort by version (assuming timestamp-based or numeric)
            versions.sort(reverse=True)
            return versions[0]
        
        return None
    
    def clear_cache(self):
        """Clear in-memory model cache"""
        self.model_cache.clear()
        logger.info("Model cache cleared")
