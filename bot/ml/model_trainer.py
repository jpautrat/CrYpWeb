"""
Model training pipeline for XGBoost, LightGBM, and optional LSTM models.
Implements purged walk-forward validation and model calibration.
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from loguru import logger
import xgboost as xgb
import lightgbm as lgb
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import classification_report, confusion_matrix

from .feature_definitions import FeatureDefinitions
from ..data.storage_manager import StorageManager
from ..data.feature_engineer import FeatureEngineer


class ModelTrainer:
    """Trains and validates ML models for trading signals"""
    
    def __init__(self, storage: StorageManager, feature_engineer: FeatureEngineer):
        self.storage = storage
        self.feature_engineer = feature_engineer
        self.feature_defs = FeatureDefinitions()
    
    def prepare_labels(self, features: pd.DataFrame, target_horizon: str = "medium",
                      transaction_cost_bps: float = 5.0) -> pd.Series:
        """
        Prepare labels from forward-looking returns.
        
        Args:
            features: DataFrame with price features
            target_horizon: 'short' (5-15s), 'medium' (30-60s), 'long' (5-15m)
            transaction_cost_bps: Transaction cost in basis points
        
        Returns:
            Series with labels: 2 (strong up), 1 (weak up), 0 (neutral), -1 (weak down), -2 (strong down)
        """
        if features.empty or 'price_current' not in features.columns:
            return pd.Series(dtype=int)
        
        # Determine lookahead period
        if target_horizon == "short":
            lookahead_seconds = 10  # 10 seconds
        elif target_horizon == "medium":
            lookahead_seconds = 45  # 45 seconds
        elif target_horizon == "long":
            lookahead_seconds = 600  # 10 minutes
        else:
            lookahead_seconds = 45
        
        labels = pd.Series(index=features.index, dtype=int)
        
        prices = features['price_current'].values
        timestamps = pd.to_datetime(features.index)
        
        for i in range(len(features) - 1):
            current_price = prices[i]
            current_time = timestamps[i]
            
            # Find future price at lookahead
            target_time = current_time + timedelta(seconds=lookahead_seconds)
            
            # Find closest future price
            future_idx = None
            for j in range(i + 1, len(features)):
                if timestamps[j] >= target_time:
                    future_idx = j
                    break
            
            if future_idx is None:
                labels.iloc[i] = 0  # Neutral if no future data
                continue
            
            future_price = prices[future_idx]
            
            # Calculate return
            if current_price > 0:
                return_pct = ((future_price - current_price) / current_price) * 100
                
                # Adjust for transaction costs
                net_return = return_pct - (transaction_cost_bps / 100)
                
                # Classify
                if net_return > 0.5:
                    labels.iloc[i] = 2  # Strong up
                elif net_return > 0.1:
                    labels.iloc[i] = 1  # Weak up
                elif net_return < -0.5:
                    labels.iloc[i] = -2  # Strong down
                elif net_return < -0.1:
                    labels.iloc[i] = -1  # Weak down
                else:
                    labels.iloc[i] = 0  # Neutral
            else:
                labels.iloc[i] = 0
        
        # Fill remaining NaNs
        labels = labels.fillna(0)
        
        return labels
    
    def prepare_training_data(self, pair: str, days: int = 30,
                              target_horizon: str = "medium") -> Tuple[pd.DataFrame, pd.Series]:
        """
        Prepare training data for a pair.
        
        Returns:
            (features_df, labels_series)
        """
        logger.info(f"Preparing training data for {pair} ({days} days)")
        
        # Load historical data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        trades = self.storage.load_trades(pair, start_date, end_date)
        
        if trades.empty:
            logger.warning(f"No historical data for {pair}")
            return pd.DataFrame(), pd.Series()
        
        # Compute features
        features = self.feature_engineer.compute_batch_features(trades, pair=pair)
        
        if features.empty:
            logger.warning(f"No features computed for {pair}")
            return pd.DataFrame(), pd.Series()
        
        # Prepare labels
        labels = self.prepare_labels(features, target_horizon)
        
        # Align features and labels
        common_idx = features.index.intersection(labels.index)
        features = features.loc[common_idx]
        labels = labels.loc[common_idx]
        
        # Remove rows with missing features
        valid_mask = ~features.isna().any(axis=1)
        features = features[valid_mask]
        labels = labels[valid_mask]
        
        logger.info(f"Prepared {len(features)} samples for {pair}")
        
        return features, labels
    
    def purged_walk_forward_split(self, features: pd.DataFrame, labels: pd.Series,
                                  purge_hours: int = 24, embargo_hours: int = 48) -> List[Tuple]:
        """
        Create purged walk-forward splits for validation.
        
        Returns:
            List of (train_idx, test_idx) tuples
        """
        splits = []
        timestamps = pd.to_datetime(features.index)
        
        # Use 7-day training, 1-day validation windows
        train_days = 7
        val_days = 1
        
        current_date = timestamps.min()
        end_date = timestamps.max()
        
        while current_date + timedelta(days=train_days + val_days) <= end_date:
            train_start = current_date
            train_end = train_start + timedelta(days=train_days)
            
            # Purge and embargo periods
            purge_start = train_end
            purge_end = purge_start + timedelta(hours=purge_hours + embargo_hours)
            
            val_start = purge_end
            val_end = val_start + timedelta(days=val_days)
            
            if val_end > end_date:
                break
            
            # Get indices
            train_mask = (timestamps >= train_start) & (timestamps < train_end)
            val_mask = (timestamps >= val_start) & (timestamps < val_end)
            
            train_idx = features.index[train_mask]
            val_idx = features.index[val_mask]
            
            if len(train_idx) > 100 and len(val_idx) > 10:
                splits.append((train_idx, val_idx))
            
            # Move forward by validation window
            current_date = val_end
        
        logger.info(f"Created {len(splits)} walk-forward splits")
        return splits
    
    def train_xgboost(self, X_train: pd.DataFrame, y_train: pd.Series,
                     X_val: Optional[pd.DataFrame] = None, y_val: Optional[pd.Series] = None) -> xgb.XGBClassifier:
        """Train XGBoost model"""
        logger.info(f"Training XGBoost model on {len(X_train)} samples")
        
        # Prepare data
        X_train_vals = X_train.values
        y_train_vals = y_train.values
        
        # XGBoost parameters optimized for small datasets
        params = {
            'objective': 'multi:softprob',
            'num_class': 5,  # 5 classes: -2, -1, 0, 1, 2
            'max_depth': 6,
            'learning_rate': 0.1,
            'n_estimators': 100,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'min_child_weight': 3,
            'gamma': 0.1,
            'reg_alpha': 0.1,
            'reg_lambda': 1.0,
            'random_state': 42,
            'n_jobs': -1
        }
        
        # Adjust labels for multi-class (0-4 instead of -2 to 2)
        y_train_adjusted = y_train_vals + 2
        
        # Prepare validation set
        eval_set = []
        if X_val is not None and y_val is not None:
            X_val_vals = X_val.values
            y_val_adjusted = y_val.values + 2
            eval_set = [(X_train_vals, y_train_adjusted), (X_val_vals, y_val_adjusted)]
            params['eval_metric'] = 'mlogloss'
        
        # Train model
        model = xgb.XGBClassifier(**params)
        model.fit(
            X_train_vals,
            y_train_adjusted,
            eval_set=eval_set if eval_set else None,
            verbose=False
        )
        
        logger.info("XGBoost model training completed")
        return model
    
    def train_lightgbm(self, X_train: pd.DataFrame, y_train: pd.Series,
                       X_val: Optional[pd.DataFrame] = None, y_val: Optional[pd.Series] = None) -> lgb.LGBMClassifier:
        """Train LightGBM model"""
        logger.info(f"Training LightGBM model on {len(X_train)} samples")
        
        X_train_vals = X_train.values
        y_train_vals = y_train.values
        
        params = {
            'objective': 'multiclass',
            'num_class': 5,
            'max_depth': 6,
            'learning_rate': 0.1,
            'n_estimators': 100,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'min_child_samples': 10,
            'reg_alpha': 0.1,
            'reg_lambda': 1.0,
            'random_state': 42,
            'n_jobs': -1,
            'verbose': -1
        }
        
        y_train_adjusted = y_train_vals + 2
        
        train_data = lgb.Dataset(X_train_vals, label=y_train_adjusted)
        
        valid_sets = [train_data]
        if X_val is not None and y_val is not None:
            X_val_vals = X_val.values
            y_val_adjusted = y_val.values + 2
            val_data = lgb.Dataset(X_val_vals, label=y_val_adjusted)
            valid_sets.append(val_data)
        
        model = lgb.train(
            params,
            train_data,
            valid_sets=valid_sets,
            valid_names=['train', 'valid'] if len(valid_sets) > 1 else None,
            callbacks=[lgb.log_evaluation(period=0)]
        )
        
        # Wrap in sklearn interface
        sklearn_model = lgb.LGBMClassifier(**params)
        sklearn_model.fit(X_train_vals, y_train_adjusted)
        
        logger.info("LightGBM model training completed")
        return sklearn_model
    
    def calibrate_model(self, model, X_val: pd.DataFrame, y_val: pd.Series) -> CalibratedClassifierCV:
        """Calibrate model probabilities using Platt scaling"""
        logger.info("Calibrating model probabilities")
        
        # Adjust labels
        y_val_adjusted = y_val.values + 2
        
        # Calibrate
        calibrated = CalibratedClassifierCV(model, method='isotonic', cv='prefit')
        calibrated.fit(X_val.values, y_val_adjusted)
        
        logger.info("Model calibration completed")
        return calibrated
    
    def evaluate_model(self, model, X_test: pd.DataFrame, y_test: pd.Series) -> Dict:
        """Evaluate model performance"""
        X_test_vals = X_test.values
        y_test_adjusted = y_test.values + 2
        
        # Predictions
        y_pred = model.predict(X_test_vals)
        y_proba = model.predict_proba(X_test_vals)
        
        # Metrics
        accuracy = (y_pred == y_test_adjusted).mean()
        
        # Classification report
        report = classification_report(y_test_adjusted, y_pred, output_dict=True)
        
        metrics = {
            'accuracy': accuracy,
            'classification_report': report,
            'predictions': y_pred,
            'probabilities': y_proba,
            'true_labels': y_test_adjusted
        }
        
        return metrics
    
    def train_pair_model(self, pair: str, target_horizon: str = "medium",
                        model_type: str = "xgboost", use_ensemble: bool = True) -> Dict:
        """
        Train model for a specific pair.
        
        Returns:
            Dictionary with trained models and metrics
        """
        logger.info(f"Training {model_type} model for {pair}")
        
        # Prepare data
        X, y = self.prepare_training_data(pair, days=30, target_horizon=target_horizon)
        
        if X.empty or y.empty:
            logger.error(f"Insufficient data for {pair}")
            return {}
        
        # Create walk-forward splits
        splits = self.purged_walk_forward_split(X, y)
        
        if not splits:
            logger.warning(f"No valid splits for {pair}, using simple train/test")
            # Simple 80/20 split
            split_idx = int(len(X) * 0.8)
            train_idx = X.index[:split_idx]
            test_idx = X.index[split_idx:]
            splits = [(train_idx, test_idx)]
        
        # Train on most recent split
        train_idx, test_idx = splits[-1]
        
        X_train = X.loc[train_idx]
        y_train = y.loc[train_idx]
        X_test = X.loc[test_idx]
        y_test = y.loc[test_idx]
        
        # Train models
        models = {}
        
        if model_type == "xgboost" or use_ensemble:
            xgb_model = self.train_xgboost(X_train, y_train, X_test, y_test)
            xgb_calibrated = self.calibrate_model(xgb_model, X_test, y_test)
            models['xgboost'] = xgb_calibrated
            
            # Evaluate
            xgb_metrics = self.evaluate_model(xgb_calibrated, X_test, y_test)
            logger.info(f"XGBoost accuracy: {xgb_metrics['accuracy']:.3f}")
        
        if model_type == "lightgbm" or use_ensemble:
            lgb_model = self.train_lightgbm(X_train, y_train, X_test, y_test)
            lgb_calibrated = self.calibrate_model(lgb_model, X_test, y_test)
            models['lightgbm'] = lgb_calibrated
            
            # Evaluate
            lgb_metrics = self.evaluate_model(lgb_calibrated, X_test, y_test)
            logger.info(f"LightGBM accuracy: {lgb_metrics['accuracy']:.3f}")
        
        return {
            'models': models,
            'metrics': {
                'xgboost': xgb_metrics if 'xgboost' in models else None,
                'lightgbm': lgb_metrics if 'lightgbm' in models else None
            },
            'features': X.columns.tolist()
        }
