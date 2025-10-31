"""
Model Registry - Management and versioning of trained models
"""

import pickle
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from loguru import logger


class ModelRegistry:
    """
    Manages trained models with versioning and metadata.
    Handles model loading, deployment, and performance tracking.
    """
    
    def __init__(self, model_dir: str = "data/models"):
        """
        Initialize model registry.
        
        Args:
            model_dir: Directory containing trained models
        """
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        self.loaded_models: Dict[str, Dict] = {}
        
        logger.info(f"ModelRegistry initialized: {self.model_dir}")
    
    def get_latest_model(
        self,
        pair: str,
        model_type: str = 'xgboost'
    ) -> Optional[Tuple]:
        """
        Get the latest trained model for a pair.
        
        Args:
            pair: Trading pair
            model_type: 'xgboost' or 'lightgbm'
            
        Returns:
            Tuple of (model, metadata) or None
        """
        pair_dir = self.model_dir / pair.replace('/', '_')
        
        if not pair_dir.exists():
            logger.warning(f"No models found for {pair}")
            return None
        
        # Find latest model file
        model_files = list(pair_dir.glob(f"{model_type}_*.pkl"))
        
        if not model_files:
            logger.warning(f"No {model_type} models found for {pair}")
            return None
        
        # Sort by timestamp (newest first)
        model_files.sort(reverse=True)
        latest_model_file = model_files[0]
        
        # Load model
        try:
            with open(latest_model_file, 'rb') as f:
                model = pickle.load(f)
            
            # Load metadata
            timestamp = latest_model_file.stem.split('_')[1]
            metadata_file = pair_dir / f"metadata_{timestamp}.json"
            
            metadata = {}
            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
            
            logger.info(f"Loaded {model_type} model for {pair}: {timestamp}")
            
            return model, metadata
            
        except Exception as e:
            logger.error(f"Failed to load model {latest_model_file}: {e}")
            return None
    
    def load_model(
        self,
        pair: str,
        use_ensemble: bool = True
    ) -> Optional[Dict]:
        """
        Load model(s) for a pair into registry.
        
        Args:
            pair: Trading pair
            use_ensemble: Load both XGBoost and LightGBM if available
            
        Returns:
            Dictionary with loaded models or None
        """
        if pair in self.loaded_models:
            logger.debug(f"Model for {pair} already loaded")
            return self.loaded_models[pair]
        
        # Load XGBoost model
        xgb_result = self.get_latest_model(pair, 'xgboost')
        if not xgb_result:
            return None
        
        xgb_model, metadata = xgb_result
        
        models = {
            'pair': pair,
            'xgboost': xgb_model,
            'lightgbm': None,
            'metadata': metadata,
            'loaded_at': datetime.now().isoformat()
        }
        
        # Load LightGBM if ensemble requested
        if use_ensemble:
            lgb_result = self.get_latest_model(pair, 'lightgbm')
            if lgb_result:
                lgb_model, _ = lgb_result
                models['lightgbm'] = lgb_model
        
        # Cache in registry
        self.loaded_models[pair] = models
        
        logger.info(f"Model loaded for {pair} (ensemble={use_ensemble})")
        
        return models
    
    def predict(
        self,
        pair: str,
        features: 'pd.Series',
        use_ensemble: bool = True
    ) -> Optional[Tuple]:
        """
        Make prediction using loaded model(s).
        
        Args:
            pair: Trading pair
            features: Feature series
            use_ensemble: Use both models if available
            
        Returns:
            Tuple of (probabilities, confidence, predicted_class) or None
        """
        models = self.loaded_models.get(pair)
        
        if not models:
            # Try to load model
            models = self.load_model(pair, use_ensemble)
            
        if not models:
            logger.warning(f"No model available for {pair}")
            return None
        
        try:
            # Convert features to DataFrame
            import pandas as pd
            features_df = pd.DataFrame([features])
            
            # Get predictions from XGBoost
            xgb_proba = models['xgboost'].predict_proba(features_df)[0]
            
            # If ensemble, average with LightGBM
            if use_ensemble and models['lightgbm'] is not None:
                lgb_proba = models['lightgbm'].predict_proba(features_df)[0]
                probabilities = (xgb_proba + lgb_proba) / 2
            else:
                probabilities = xgb_proba
            
            # Get confidence and predicted class
            confidence = float(np.max(probabilities))
            predicted_class = int(np.argmax(probabilities)) - 2  # Shift back to -2..2
            
            return probabilities, confidence, predicted_class
            
        except Exception as e:
            logger.error(f"Prediction failed for {pair}: {e}", exc_info=True)
            return None
    
    def get_model_info(self, pair: str) -> Optional[Dict]:
        """Get metadata for loaded model"""
        models = self.loaded_models.get(pair)
        if not models:
            return None
        
        return {
            'pair': pair,
            'has_xgboost': models['xgboost'] is not None,
            'has_lightgbm': models['lightgbm'] is not None,
            'loaded_at': models['loaded_at'],
            'metadata': models['metadata']
        }
    
    def unload_model(self, pair: str):
        """Remove model from registry to free memory"""
        if pair in self.loaded_models:
            del self.loaded_models[pair]
            logger.info(f"Model unloaded for {pair}")
    
    def list_available_models(self) -> List[str]:
        """List all pairs with trained models"""
        pairs = []
        
        for pair_dir in self.model_dir.iterdir():
            if pair_dir.is_dir():
                # Check if any model files exist
                if list(pair_dir.glob("*.pkl")):
                    pair = pair_dir.name.replace('_', '/')
                    pairs.append(pair)
        
        return sorted(pairs)
    
    def get_registry_status(self) -> Dict:
        """Get status of model registry"""
        return {
            'loaded_models': len(self.loaded_models),
            'available_models': len(self.list_available_models()),
            'loaded_pairs': list(self.loaded_models.keys())
        }


# Import numpy for predict method
import numpy as np
