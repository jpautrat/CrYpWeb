"""
ML-based trading strategy using trained models.
"""
import numpy as np
from typing import Dict, Any, Optional
import pandas as pd
from datetime import datetime
from loguru import logger

from .base_strategy import StrategyInterface
from ..ml.model_registry import ModelRegistry
from ..ml.calibration import ProbabilityCalibrator
from ..config.settings import MLConfig, TradingConfig
from ..config.thresholds import ThresholdManager


class MLStrategy(StrategyInterface):
    """ML-based trading strategy"""
    
    def __init__(self, model_registry: ModelRegistry, config: MLConfig,
                 trading_config: TradingConfig, thresholds: ThresholdManager):
        self.model_registry = model_registry
        self.config = config
        self.trading_config = trading_config
        self.thresholds = thresholds
        self.calibrator = ProbabilityCalibrator()
        
        # Loaded models cache
        self.models: Dict[str, Dict] = {}
    
    def _load_model(self, pair: str):
        """Load model for pair"""
        if pair not in self.models:
            # Try to load XGBoost first
            xgb_model = self.model_registry.load_model(pair, "xgboost", "latest")
            lgb_model = None
            
            if self.config.ensemble_models:
                lgb_model = self.model_registry.load_model(pair, "lightgbm", "latest")
            
            self.models[pair] = {
                'xgboost': xgb_model,
                'lightgbm': lgb_model
            }
        
        return self.models[pair]
    
    def signal(self, features: pd.Series, pair: str, timestamp: datetime) -> Dict[str, Any]:
        """Generate ML-based trading signal"""
        try:
            # Load models
            models = self._load_model(pair)
            
            if not models['xgboost']:
                logger.warning(f"No model available for {pair}")
                return self._hold_signal("No model available")
            
            # Prepare features
            feature_values = features.values.reshape(1, -1)
            
            # Get predictions
            xgb_proba = models['xgboost'].predict_proba(feature_values)[0]
            
            # Ensemble with LightGBM if available
            if models['lightgbm']:
                lgb_proba = models['lightgbm'].predict_proba(feature_values)[0]
                # Average probabilities
                ensemble_proba = (xgb_proba + lgb_proba) / 2.0
            else:
                ensemble_proba = xgb_proba
            
            # Get prediction (classes: 0=-2, 1=-1, 2=0, 3=1, 4=2)
            predicted_class = np.argmax(ensemble_proba)
            predicted_label = predicted_class - 2  # Convert back to -2 to 2
            
            # Compute confidence
            confidence = self.calibrator.compute_confidence_score(ensemble_proba)
            
            # Check confidence threshold
            if confidence < self.config.confidence_threshold:
                return self._hold_signal(f"Confidence {confidence:.3f} below threshold")
            
            # Determine side and expected return
            if predicted_label > 0:  # Buy signal
                side = 'buy'
                # Expected return based on predicted label magnitude
                expected_return = predicted_label * 0.001  # Convert to decimal (rough estimate)
            elif predicted_label < 0:  # Sell signal
                side = 'sell'
                expected_return = abs(predicted_label) * 0.001
            else:  # Neutral
                return self._hold_signal("Neutral prediction")
            
            # Get current price from features
            current_price = features.get('price_current', 0.0)
            if current_price <= 0:
                return self._hold_signal("Invalid price")
            
            # Calculate limit price (maker order with small improvement)
            if side == 'buy':
                limit_price = current_price * 0.9995  # Slightly below market
            else:
                limit_price = current_price * 1.0005  # Slightly above market
            
            # Risk score (inverse of confidence for now)
            risk_score = 1.0 - confidence
            
            return {
                'side': side,
                'size': 0.0,  # Will be calculated by position sizer
                'limit_price': limit_price,
                'ttl': 30,  # 30 seconds
                'confidence': confidence,
                'reason': f"ML prediction: {predicted_label} (confidence: {confidence:.3f})",
                'expected_return': expected_return,
                'risk_score': risk_score,
                'predicted_class': predicted_label,
                'probabilities': ensemble_proba.tolist()
            }
        
        except Exception as e:
            logger.error(f"Error generating ML signal for {pair}: {e}")
            return self._hold_signal(f"Error: {str(e)}")
    
    def should_trade(self, signal: Dict[str, Any], market_data: Dict) -> bool:
        """Determine if ML signal should be executed"""
        if signal['side'] == 'hold':
            return False
        
        # Check confidence threshold
        if signal['confidence'] < self.config.confidence_threshold:
            return False
        
        # Check expected return covers costs
        expected_return_bps = signal['expected_return'] * 10000
        edge_buffer = self.thresholds.get_trading_thresholds()['min_edge_bps']
        fee_cost = 16  # 0.16% maker fee in bps
        spread_cost = market_data.get('spread_bps', 0)
        
        total_cost = fee_cost + spread_cost + edge_buffer
        if expected_return_bps <= total_cost:
            logger.debug(f"Expected return {expected_return_bps:.1f} bps < total cost {total_cost:.1f} bps")
            return False
        
        # Check spread is reasonable
        max_spread = self.thresholds.get_trading_thresholds()['max_spread_bps']
        if market_data.get('spread_bps', 0) > max_spread:
            logger.debug(f"Spread {market_data['spread_bps']:.1f} bps exceeds maximum {max_spread:.1f} bps")
            return False
        
        return True
    
    def _hold_signal(self, reason: str) -> Dict[str, Any]:
        """Generate hold signal"""
        return {
            'side': 'hold',
            'size': 0.0,
            'limit_price': None,
            'ttl': 0,
            'confidence': 0.0,
            'reason': reason,
            'expected_return': 0.0,
            'risk_score': 1.0
        }
