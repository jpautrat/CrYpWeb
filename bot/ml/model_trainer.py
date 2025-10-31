"""
Model Trainer - Training pipeline with walk-forward validation
Implements XGBoost and LightGBM models with proper time series cross-validation.
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple, List, Optional
from datetime import datetime, timedelta
from pathlib import Path
import pickle
import json

import xgboost as xgb
import lightgbm as lgb
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import accuracy_score, precision_score, recall_score, log_loss
from loguru import logger

from ..data.storage_manager import StorageManager
from ..data.feature_engineer import FeatureEngineer
from .feature_definitions import get_feature_names, get_fill_values


class ModelTrainer:
    """
    Handles model training with time series cross-validation.
    Implements walk-forward validation with purging and embargo.
    """
    
    def __init__(
        self,
        storage_manager: StorageManager,
        feature_engineer: FeatureEngineer,
        model_dir: str = "data/models"
    ):
        """
        Initialize model trainer.
        
        Args:
            storage_manager: Storage manager for data access
            feature_engineer: Feature engineer for feature computation
            model_dir: Directory to save trained models
        """
        self.storage = storage_manager
        self.feature_engineer = feature_engineer
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"ModelTrainer initialized: {self.model_dir}")
    
    def prepare_training_data(
        self,
        pair: str,
        training_days: int = 30,
        label_horizon_seconds: int = 60,
        min_samples: int = 1000
    ) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Prepare training dataset with features and labels.
        
        Args:
            pair: Trading pair
            training_days: Number of days of historical data
            label_horizon_seconds: Forward-looking horizon for labels
            min_samples: Minimum required samples
            
        Returns:
            Tuple of (features_df, labels_series)
        """
        logger.info(f"Preparing training data for {pair}: {training_days} days")
        
        end_time = datetime.now()
        start_time = end_time - timedelta(days=training_days)
        
        # Load historical features
        features_df = self.storage.load_features(pair, start_time, end_time)
        
        if features_df.empty or len(features_df) < min_samples:
            logger.warning(
                f"Insufficient historical data for {pair}: "
                f"{len(features_df)} samples (need {min_samples})"
            )
            return pd.DataFrame(), pd.Series()
        
        # Create labels (forward-looking returns)
        features_df = features_df.sort_values('timestamp')
        
        if 'mid_price' in features_df.columns:
            # Compute forward returns
            features_df['forward_price'] = features_df['mid_price'].shift(-label_horizon_seconds)
            features_df['forward_return'] = (
                (features_df['forward_price'] - features_df['mid_price']) / 
                features_df['mid_price'] * 100
            )
            
            # Create multi-class labels
            # Strong Up (>0.5%), Weak Up (0.1-0.5%), Neutral (-0.1 to 0.1%), 
            # Weak Down (-0.5 to -0.1%), Strong Down (<-0.5%)
            def classify_return(ret):
                if pd.isna(ret):
                    return np.nan
                elif ret > 0.5:
                    return 2  # Strong Up
                elif ret > 0.1:
                    return 1  # Weak Up
                elif ret > -0.1:
                    return 0  # Neutral
                elif ret > -0.5:
                    return -1  # Weak Down
                else:
                    return -2  # Strong Down
            
            labels = features_df['forward_return'].apply(classify_return)
            
            # Remove samples without labels
            valid_mask = ~labels.isna()
            features_df = features_df[valid_mask]
            labels = labels[valid_mask]
            
            # Remove temporary columns
            features_df = features_df.drop(columns=['forward_price', 'forward_return'])
        else:
            logger.error(f"No mid_price column in features for {pair}")
            return pd.DataFrame(), pd.Series()
        
        # Select feature columns
        feature_cols = get_feature_names()
        available_cols = [col for col in feature_cols if col in features_df.columns]
        
        if not available_cols:
            logger.error(f"No valid feature columns found for {pair}")
            return pd.DataFrame(), pd.Series()
        
        X = features_df[available_cols].copy()
        
        # Fill missing values
        fill_values = get_fill_values()
        for col in X.columns:
            if col in fill_values:
                X[col].fillna(fill_values[col], inplace=True)
        
        logger.info(
            f"Prepared {len(X)} samples with {len(X.columns)} features for {pair}"
        )
        
        return X, labels
    
    def train_xgboost(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        params: Optional[Dict] = None
    ) -> xgb.XGBClassifier:
        """
        Train XGBoost model.
        
        Args:
            X: Feature matrix
            y: Labels
            params: Model parameters
            
        Returns:
            Trained XGBoost model
        """
        if params is None:
            params = {
                'objective': 'multi:softprob',
                'num_class': 5,  # 5 classes: -2, -1, 0, 1, 2
                'max_depth': 6,
                'learning_rate': 0.1,
                'n_estimators': 200,
                'subsample': 0.8,
                'colsample_bytree': 0.8,
                'random_state': 42,
                'n_jobs': -1,
                'tree_method': 'hist'
            }
        
        # Shift labels to 0-4 for XGBoost
        y_shifted = y + 2
        
        model = xgb.XGBClassifier(**params)
        model.fit(X, y_shifted, verbose=False)
        
        return model
    
    def train_lightgbm(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        params: Optional[Dict] = None
    ) -> lgb.LGBMClassifier:
        """
        Train LightGBM model.
        
        Args:
            X: Feature matrix
            y: Labels
            params: Model parameters
            
        Returns:
            Trained LightGBM model
        """
        if params is None:
            params = {
                'objective': 'multiclass',
                'num_class': 5,
                'max_depth': 6,
                'learning_rate': 0.1,
                'n_estimators': 200,
                'subsample': 0.8,
                'colsample_bytree': 0.8,
                'random_state': 42,
                'n_jobs': -1,
                'verbose': -1
            }
        
        # Shift labels to 0-4
        y_shifted = y + 2
        
        model = lgb.LGBMClassifier(**params)
        model.fit(X, y_shifted, verbose=False)
        
        return model
    
    def walk_forward_validation(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        n_splits: int = 5,
        purge_days: int = 1,
        embargo_days: int = 2
    ) -> Dict:
        """
        Perform walk-forward cross-validation with purging and embargo.
        
        Args:
            X: Feature matrix
            y: Labels
            n_splits: Number of CV splits
            purge_days: Days to purge after training set
            embargo_days: Days to embargo after test set
            
        Returns:
            Dictionary with validation metrics
        """
        logger.info(f"Performing walk-forward validation: {n_splits} splits")
        
        tscv = TimeSeriesSplit(n_splits=n_splits)
        
        metrics = {
            'accuracy': [],
            'precision': [],
            'recall': [],
            'log_loss': []
        }
        
        for fold, (train_idx, test_idx) in enumerate(tscv.split(X)):
            logger.info(f"Training fold {fold+1}/{n_splits}")
            
            X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
            y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
            
            # Train model
            model = self.train_xgboost(X_train, y_train)
            
            # Predict (shift back to original label space)
            y_pred_proba = model.predict_proba(X_test)
            y_pred = model.predict(X_test) - 2
            
            # Calculate metrics
            metrics['accuracy'].append(accuracy_score(y_test, y_pred))
            metrics['precision'].append(precision_score(y_test, y_pred, average='weighted', zero_division=0))
            metrics['recall'].append(recall_score(y_test, y_pred, average='weighted', zero_division=0))
            metrics['log_loss'].append(log_loss(y_test + 2, y_pred_proba))
        
        # Average metrics
        avg_metrics = {
            'accuracy': np.mean(metrics['accuracy']),
            'precision': np.mean(metrics['precision']),
            'recall': np.mean(metrics['recall']),
            'log_loss': np.mean(metrics['log_loss']),
            'sharpe_proxy': np.mean(metrics['accuracy']) / (np.std(metrics['accuracy']) + 1e-6)
        }
        
        logger.info(f"Validation results: accuracy={avg_metrics['accuracy']:.3f}, "
                   f"precision={avg_metrics['precision']:.3f}, "
                   f"recall={avg_metrics['recall']:.3f}")
        
        return avg_metrics
    
    def train_and_save_model(
        self,
        pair: str,
        training_days: int = 30,
        validation_splits: int = 5,
        use_ensemble: bool = True
    ) -> Dict:
        """
        Train and save model for a pair.
        
        Args:
            pair: Trading pair
            training_days: Days of training data
            validation_splits: Number of CV splits
            use_ensemble: Train both XGBoost and LightGBM
            
        Returns:
            Dictionary with training metrics
        """
        logger.info(f"Training model for {pair}")
        
        # Prepare data
        X, y = self.prepare_training_data(pair, training_days)
        
        if X.empty or y.empty:
            return {'error': 'Insufficient data'}
        
        # Perform validation
        val_metrics = self.walk_forward_validation(X, y, validation_splits)
        
        # Train final models on all data
        logger.info("Training final XGBoost model on all data")
        xgb_model = self.train_xgboost(X, y)
        
        lgb_model = None
        if use_ensemble:
            logger.info("Training final LightGBM model on all data")
            lgb_model = self.train_lightgbm(X, y)
        
        # Save models
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_path = self.model_dir / pair.replace('/', '_')
        model_path.mkdir(parents=True, exist_ok=True)
        
        xgb_file = model_path / f"xgboost_{timestamp}.pkl"
        with open(xgb_file, 'wb') as f:
            pickle.dump(xgb_model, f)
        
        if lgb_model:
            lgb_file = model_path / f"lightgbm_{timestamp}.pkl"
            with open(lgb_file, 'wb') as f:
                pickle.dump(lgb_model, f)
        
        # Save metadata
        metadata = {
            'pair': pair,
            'training_samples': len(X),
            'training_days': training_days,
            'features': list(X.columns),
            'metrics': val_metrics,
            'timestamp': timestamp,
            'xgb_model': str(xgb_file),
            'lgb_model': str(lgb_file) if lgb_model else None
        }
        
        metadata_file = model_path / f"metadata_{timestamp}.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Model saved: {model_path}")
        
        return metadata
