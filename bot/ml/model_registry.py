"""
Model registry for storing and loading ML models.
"""
import pickle
import json
from pathlib import Path
from typing import Optional, Dict
from datetime import datetime
from loguru import logger

from bot.config.settings import settings


class ModelRegistry:
    """Manages ML model storage and retrieval."""
    
    def __init__(self):
        """Initialize model registry."""
        self.models_dir = settings.system.models_dir
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.loaded_models: Dict[str, Dict] = {}  # pair -> model info
    
    def save_model(self, pair: str, model, metadata: Dict):
        """
        Save trained model.
        
        Args:
            pair: Trading pair
            model: Trained model object
            metadata: Model metadata (performance, timestamp, etc.)
        """
        pair_dir = self.models_dir / pair.replace("/", "_")
        pair_dir.mkdir(parents=True, exist_ok=True)
        
        # Save model
        model_path = pair_dir / "model.pkl"
        with open(model_path, 'wb') as f:
            pickle.dump(model, f)
        
        # Save metadata
        metadata['saved_at'] = datetime.utcnow().isoformat()
        metadata_path = pair_dir / "metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Saved model for {pair}")
    
    def load_model(self, pair: str):
        """
        Load model for a pair.
        
        Args:
            pair: Trading pair
            
        Returns:
            Model object and metadata, or (None, None) if not found
        """
        if pair in self.loaded_models:
            return self.loaded_models[pair]['model'], self.loaded_models[pair]['metadata']
        
        pair_dir = self.models_dir / pair.replace("/", "_")
        model_path = pair_dir / "model.pkl"
        metadata_path = pair_dir / "metadata.json"
        
        if not model_path.exists():
            return None, None
        
        try:
            with open(model_path, 'rb') as f:
                model = pickle.load(f)
            
            metadata = {}
            if metadata_path.exists():
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
            
            self.loaded_models[pair] = {'model': model, 'metadata': metadata}
            logger.info(f"Loaded model for {pair}")
            return model, metadata
        except Exception as e:
            logger.error(f"Failed to load model for {pair}: {e}")
            return None, None
    
    def has_model(self, pair: str) -> bool:
        """Check if model exists for a pair."""
        pair_dir = self.models_dir / pair.replace("/", "_")
        return (pair_dir / "model.pkl").exists()
