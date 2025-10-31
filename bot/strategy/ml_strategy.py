"""ML-based trading strategy."""
from typing import Dict, Optional
import pandas as pd
from datetime import datetime
from loguru import logger

from bot.ml.model_registry import ModelRegistry
from bot.data.feature_engineer import FeatureEngineer
from bot.config.settings import settings


class MLStrategy:
    """ML-based trading strategy."""
    
    def __init__(self, model_registry: ModelRegistry, feature_engineer: FeatureEngineer):
        self.registry = model_registry
        self.feature_engineer = feature_engineer
    
    def generate_signal(self, pair: str, features: pd.Series, 
                       current_price: float) -> Dict:
        """Generate trading signal from ML model."""
        model, metadata = self.registry.load_model(pair)
        
        if model is None:
            return {
                'side': 'hold',
                'confidence': 0.0,
                'reason': 'No model available',
            }
        
        try:
            # Predict
            X = features.values.reshape(1, -1)
            proba = model.predict_proba(X)[0]
            prediction = model.predict(X)[0]
            
            # Get confidence
            confidence = max(proba)
            
            # Map prediction to signal
            if prediction >= 1 and confidence >= settings.model.confidence_threshold:
                side = 'buy'
                expected_return = 0.5  # Approximate from prediction class
            elif prediction <= -1 and confidence >= settings.model.confidence_threshold:
                side = 'sell'
                expected_return = -0.5
            else:
                side = 'hold'
                expected_return = 0.0
            
            return {
                'side': side,
                'confidence': float(confidence),
                'expected_return': expected_return,
                'reason': f'ML prediction: {prediction}, confidence: {confidence:.2%}',
            }
        
        except Exception as e:
            logger.error(f"Error generating signal: {e}")
            return {'side': 'hold', 'confidence': 0.0, 'reason': str(e)}
