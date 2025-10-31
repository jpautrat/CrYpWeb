"""
ML Strategy Implementation
Uses ML models to generate trading signals with comprehensive decision logic.
"""

import pandas as pd
from typing import Dict, Any
from datetime import datetime
from loguru import logger

from .base_strategy import StrategyInterface
from ..ml.model_registry import ModelRegistry
from ..ml.calibration import ModelCalibrator
from ..ml.model_trainer import ModelTrainer
from ..data.feature_engineer import FeatureEngineer
from ..data.market_data import MarketDataManager
from ..config.thresholds import ThresholdManager


class MLStrategy(StrategyInterface):
    """
    Machine Learning based trading strategy.
    Uses XGBoost/LightGBM ensemble with calibrated probabilities.
    """
    
    def __init__(
        self,
        model_registry: ModelRegistry,
        model_calibrator: ModelCalibrator,
        model_trainer: ModelTrainer,
        feature_engineer: FeatureEngineer,
        market_data: MarketDataManager,
        threshold_manager: ThresholdManager,
        edge_buffer_bps: float = 20.0,
        fee_multiplier: float = 3.0
    ):
        """
        Initialize ML strategy.
        
        Args:
            model_registry: Model registry for loading models
            model_calibrator: Probability calibrator
            model_trainer: Model trainer for updates
            feature_engineer: Feature computation
            market_data: Market data manager
            threshold_manager: Dynamic threshold management
            edge_buffer_bps: Minimum edge required (basis points)
            fee_multiplier: Expected profit must exceed fees by this factor
        """
        self.model_registry = model_registry
        self.model_calibrator = model_calibrator
        self.model_trainer = model_trainer
        self.feature_engineer = feature_engineer
        self.market_data = market_data
        self.threshold_manager = threshold_manager
        self.edge_buffer_bps = edge_buffer_bps
        self.fee_multiplier = fee_multiplier
        
        logger.info("MLStrategy initialized")
    
    def signal(
        self,
        features: pd.Series,
        pair: str,
        timestamp: datetime
    ) -> Dict[str, Any]:
        """
        Generate trading signal from ML model predictions.
        
        Args:
            features: Feature series
            pair: Trading pair
            timestamp: Current timestamp
            
        Returns:
            Signal dictionary
        """
        # Get model prediction
        prediction = self.model_registry.predict(pair, features, use_ensemble=True)
        
        if not prediction:
            return self._no_trade_signal("No model available")
        
        probabilities, confidence, predicted_class = prediction
        
        # Get current market data
        spread_data = self.market_data.get_current_spread(pair)
        if not spread_data:
            return self._no_trade_signal("No spread data")
        
        mid_price = spread_data['mid']
        spread_pct = spread_data['spread_pct']
        
        # Estimate trading costs
        maker_fee = 0.0016  # 0.16%
        taker_fee = 0.0026  # 0.26%
        total_cost = maker_fee + (spread_pct / 100 / 2)  # Fee + half spread
        
        # Get dynamic confidence threshold
        conf_threshold = self.threshold_manager.get_confidence_threshold(pair)
        
        # Check if model confidence meets threshold
        if confidence < conf_threshold:
            return self._no_trade_signal(
                f"Confidence {confidence:.3f} below threshold {conf_threshold:.3f}"
            )
        
        # Compute expected value
        should_trade, direction, expected_value = self.model_calibrator.should_trade(
            probabilities=probabilities,
            confidence_threshold=conf_threshold,
            min_edge_bps=self.edge_buffer_bps,
            fees=maker_fee,
            spread=spread_pct / 100
        )
        
        if not should_trade or direction == 'hold':
            return self._no_trade_signal(
                f"Expected value {expected_value:.4f} insufficient"
            )
        
        # Check if expected profit exceeds fees by required multiplier
        if expected_value < total_cost * self.fee_multiplier:
            return self._no_trade_signal(
                f"EV {expected_value:.4f} < {self.fee_multiplier}x costs"
            )
        
        # Calculate position size multiplier based on confidence
        size_multiplier = self.threshold_manager.get_position_size_multiplier(
            pair, confidence
        )
        
        # Determine limit price (maker-biased)
        if direction == 'buy':
            limit_price = spread_data['bid']  # Join best bid
        else:
            limit_price = spread_data['ask']  # Join best ask
        
        # Compute risk score (inverse of confidence)
        risk_score = 1.0 - confidence
        
        return {
            'side': direction,
            'size': size_multiplier,  # Multiplier, actual size calculated by position sizer
            'limit_price': limit_price,
            'ttl': 30,  # 30 second timeout
            'confidence': confidence,
            'reason': f"ML signal: class={predicted_class}, ev={expected_value:.4f}",
            'expected_return': expected_value,
            'risk_score': risk_score,
            'probabilities': probabilities.tolist() if hasattr(probabilities, 'tolist') else list(probabilities)
        }
    
    def _no_trade_signal(self, reason: str) -> Dict[str, Any]:
        """Generate a no-trade signal"""
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
    
    def update_model(self, pair: str):
        """
        Trigger model retraining for a pair.
        
        Args:
            pair: Trading pair
        """
        logger.info(f"Triggering model update for {pair}")
        
        try:
            metadata = self.model_trainer.train_and_save_model(
                pair=pair,
                training_days=30,
                validation_splits=5,
                use_ensemble=True
            )
            
            if 'error' in metadata:
                logger.error(f"Model training failed for {pair}: {metadata['error']}")
                return
            
            # Reload model in registry
            self.model_registry.unload_model(pair)
            self.model_registry.load_model(pair, use_ensemble=True)
            
            logger.info(f"Model updated successfully for {pair}")
            
        except Exception as e:
            logger.error(f"Model update failed for {pair}: {e}", exc_info=True)
    
    def get_status(self) -> Dict[str, Any]:
        """Get strategy status"""
        return {
            'type': 'ML Strategy',
            'edge_buffer_bps': self.edge_buffer_bps,
            'fee_multiplier': self.fee_multiplier,
            'registry_status': self.model_registry.get_registry_status(),
            'available_models': self.model_registry.list_available_models()
        }
