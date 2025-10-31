"""
Model Calibration - Probability calibration for trading decisions
Implements Platt scaling and isotonic regression for better probability estimates.
"""

import numpy as np
import pandas as pd
from typing import Tuple
from sklearn.calibration import CalibratedClassifierCV
from sklearn.isotonic import IsotonicRegression
from loguru import logger


class ModelCalibrator:
    """
    Calibrates model probabilities for better decision-making.
    Essential for converting model outputs to reliable trading signals.
    """
    
    def __init__(self):
        self.calibrators = {}
        logger.info("ModelCalibrator initialized")
    
    def calibrate_probabilities(
        self,
        model,
        X_cal: pd.DataFrame,
        y_cal: pd.Series,
        method: str = 'sigmoid'
    ):
        """
        Calibrate model probabilities using calibration set.
        
        Args:
            model: Trained model
            X_cal: Calibration features
            y_cal: Calibration labels
            method: 'sigmoid' (Platt scaling) or 'isotonic'
            
        Returns:
            Calibrated model
        """
        logger.info(f"Calibrating model using {method} method")
        
        # Shift labels for sklearn compatibility (0-4)
        y_cal_shifted = y_cal + 2
        
        calibrated_model = CalibratedClassifierCV(
            model,
            method=method,
            cv='prefit'
        )
        
        calibrated_model.fit(X_cal, y_cal_shifted)
        
        # Test calibration quality
        y_pred_before = model.predict_proba(X_cal)
        y_pred_after = calibrated_model.predict_proba(X_cal)
        
        # Calculate calibration improvement (Brier score)
        brier_before = np.mean((y_pred_before.max(axis=1) - (model.predict(X_cal) == y_cal_shifted)) ** 2)
        brier_after = np.mean((y_pred_after.max(axis=1) - (calibrated_model.predict(X_cal) == y_cal_shifted)) ** 2)
        
        logger.info(f"Calibration: Brier score {brier_before:.4f} → {brier_after:.4f}")
        
        return calibrated_model
    
    def compute_expected_value(
        self,
        probabilities: np.ndarray,
        returns: np.ndarray = None,
        fees: float = 0.0026,
        spread: float = 0.001
    ) -> float:
        """
        Compute expected value of a trade given probabilities.
        
        Args:
            probabilities: Array of class probabilities [P(-2), P(-1), P(0), P(1), P(2)]
            returns: Expected returns for each class
            fees: Trading fees (as decimal)
            spread: Bid-ask spread (as decimal)
            
        Returns:
            Expected value after costs
        """
        if returns is None:
            # Default returns for each class
            # Class -2: -0.75%, -1: -0.3%, 0: 0%, 1: 0.3%, 2: 0.75%
            returns = np.array([-0.0075, -0.003, 0.0, 0.003, 0.0075])
        
        # Expected return before costs
        expected_return = np.dot(probabilities, returns)
        
        # Subtract fees and spread
        total_cost = fees + (spread / 2)
        
        # Expected value after costs
        expected_value = expected_return - total_cost
        
        return expected_value
    
    def should_trade(
        self,
        probabilities: np.ndarray,
        confidence_threshold: float = 0.65,
        min_edge_bps: float = 20.0,
        fees: float = 0.0026,
        spread: float = 0.001
    ) -> Tuple[bool, str, float]:
        """
        Determine if a trade should be placed based on probabilities.
        
        Args:
            probabilities: Class probabilities
            confidence_threshold: Minimum confidence to trade
            min_edge_bps: Minimum edge required (basis points)
            fees: Trading fees
            spread: Bid-ask spread
            
        Returns:
            Tuple of (should_trade, direction, expected_value)
        """
        # Get max probability and predicted class
        max_prob = np.max(probabilities)
        pred_class = np.argmax(probabilities) - 2  # Shift back to -2..2
        
        # Check confidence threshold
        if max_prob < confidence_threshold:
            return False, 'hold', 0.0
        
        # Compute expected value
        ev = self.compute_expected_value(probabilities, fees=fees, spread=spread)
        
        # Check minimum edge requirement
        min_edge_decimal = min_edge_bps / 10000
        if ev < min_edge_decimal:
            return False, 'hold', ev
        
        # Determine direction
        if pred_class > 0:
            direction = 'buy'
        elif pred_class < 0:
            direction = 'sell'
        else:
            direction = 'hold'
        
        return True, direction, ev
    
    def compute_optimal_size(
        self,
        probabilities: np.ndarray,
        confidence: float,
        max_size: float = 1.0,
        kelly_fraction: float = 0.25
    ) -> float:
        """
        Compute optimal position size using Kelly-like criterion.
        
        Args:
            probabilities: Class probabilities
            confidence: Model confidence
            max_size: Maximum position size
            kelly_fraction: Fraction of Kelly to use (for safety)
            
        Returns:
            Position size multiplier (0-1)
        """
        # Conservative sizing based on confidence
        if confidence >= 0.90:
            size_mult = 1.0
        elif confidence >= 0.80:
            size_mult = 0.75
        elif confidence >= 0.70:
            size_mult = 0.50
        elif confidence >= 0.65:
            size_mult = 0.25
        else:
            size_mult = 0.0
        
        # Apply Kelly fraction for additional safety
        size_mult *= kelly_fraction
        
        # Cap at max size
        size_mult = min(size_mult, max_size)
        
        return size_mult
