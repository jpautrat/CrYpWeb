"""
Model training pipeline for XGBoost and LightGBM.
"""
import pandas as pd
import numpy as np
from typing import Tuple, Dict, Optional
import xgboost as xgb
import lightgbm as lgb
from sklearn.model_selection import TimeSeriesSplit
from sklearn.calibration import CalibratedClassifierCV
from loguru import logger

from bot.ml.model_registry import ModelRegistry
from bot.config.settings import settings


class ModelTrainer:
    """Trains ML models for trading."""
    
    def __init__(self, model_registry: ModelRegistry):
        """
        Initialize model trainer.
        
        Args:
            model_registry: Model registry instance
        """
        self.registry = model_registry
    
    def train_model(self, pair: str, X: pd.DataFrame, y: pd.Series) -> Tuple[Dict, Dict]:
        """
        Train model for a trading pair.
        
        Args:
            pair: Trading pair
            X: Feature matrix
            y: Target labels
            
        Returns:
            Tuple of (model, metadata)
        """
        logger.info(f"Training model for {pair}...")
        
        # Split data with time series cross-validation
        tscv = TimeSeriesSplit(n_splits=5)
        train_idx, val_idx = list(tscv.split(X))[-1]
        
        X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
        y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]
        
        # Train XGBoost
        xgb_model = xgb.XGBClassifier(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            random_state=42,
            eval_metric='mlogloss',
        )
        xgb_model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            verbose=False,
        )
        
        # Calibrate probabilities
        calibrated_xgb = CalibratedClassifierCV(xgb_model, method='isotonic', cv='prefit')
        calibrated_xgb.fit(X_val, y_val)
        
        # Evaluate
        val_pred = calibrated_xgb.predict_proba(X_val)
        accuracy = np.mean(calibrated_xgb.predict(X_val) == y_val)
        
        metadata = {
            'pair': pair,
            'model_type': 'xgboost_calibrated',
            'trained_at': pd.Timestamp.now().isoformat(),
            'accuracy': float(accuracy),
            'n_samples': len(X_train),
            'n_features': X.shape[1],
        }
        
        logger.info(f"Model trained for {pair}, accuracy: {accuracy:.3f}")
        
        return calibrated_xgb, metadata
    
    def prepare_training_data(self, features_df: pd.DataFrame, 
                             prices: pd.Series, 
                             horizon_seconds: int = 60) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Prepare training data with labels.
        
        Args:
            features_df: Feature DataFrame
            prices: Price series
            horizon_seconds: Prediction horizon
            
        Returns:
            Tuple of (X, y) for training
        """
        # Create labels based on forward returns
        labels = []
        
        for i in range(len(features_df) - horizon_seconds):
            current_price = prices.iloc[i]
            future_price = prices.iloc[i + horizon_seconds] if i + horizon_seconds < len(prices) else current_price
            
            return_pct = (future_price - current_price) / current_price * 100
            
            # Multi-class labels
            if return_pct > 0.5:
                label = 2  # Strong Up
            elif return_pct > 0.1:
                label = 1  # Weak Up
            elif return_pct > -0.1:
                label = 0  # Neutral
            elif return_pct > -0.5:
                label = -1  # Weak Down
            else:
                label = -2  # Strong Down
            
            labels.append(label)
        
        # Align with features
        y = pd.Series(labels, index=features_df.index[:len(labels)])
        X = features_df.iloc[:len(y)]
        
        # Remove NaN
        mask = ~(X.isna().any(axis=1) | y.isna())
        X = X[mask]
        y = y[mask]
        
        return X, y
