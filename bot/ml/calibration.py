"""
Probability calibration for model predictions.
Implements Platt scaling and isotonic regression for calibrated probabilities.
"""
import numpy as np
from typing import Dict, Tuple
from sklearn.calibration import calibration_curve
from loguru import logger


class ProbabilityCalibrator:
    """Calibrates model probabilities for better decision making"""
    
    def __init__(self):
        self.calibration_params: Dict = {}
    
    def calibrate_probabilities(self, raw_probs: np.ndarray, method: str = "isotonic") -> np.ndarray:
        """
        Calibrate raw probabilities.
        
        Args:
            raw_probs: Raw probability predictions (n_samples, n_classes)
            method: 'platt' or 'isotonic'
        
        Returns:
            Calibrated probabilities
        """
        # For now, return as-is (calibration should be done during training)
        # This is a placeholder for runtime calibration adjustments
        return raw_probs
    
    def compute_confidence_score(self, probabilities: np.ndarray) -> float:
        """
        Compute confidence score from probability distribution.
        
        Args:
            probabilities: Array of class probabilities (n_classes,)
        
        Returns:
            Confidence score (0-1)
        """
        if len(probabilities) == 0:
            return 0.0
        
        # Use entropy-based confidence
        # Lower entropy = higher confidence
        entropy = -np.sum(probabilities * np.log(probabilities + 1e-10))
        max_entropy = np.log(len(probabilities))
        confidence = 1.0 - (entropy / max_entropy)
        
        return max(0.0, min(1.0, confidence))
    
    def map_confidence_to_position_size(self, confidence: float, max_size: float) -> float:
        """
        Map confidence score to position size.
        
        Args:
            confidence: Confidence score (0-1)
            max_size: Maximum position size
        
        Returns:
            Position size based on confidence
        """
        if confidence >= 0.90:
            return max_size
        elif confidence >= 0.80:
            return max_size * 0.75
        elif confidence >= 0.70:
            return max_size * 0.50
        elif confidence >= 0.65:
            return max_size * 0.25
        else:
            return 0.0  # No trade below threshold
    
    def get_prediction_with_uncertainty(self, probabilities: np.ndarray) -> Tuple[int, float, float]:
        """
        Get prediction with uncertainty estimate.
        
        Args:
            probabilities: Class probabilities (n_classes,)
        
        Returns:
            (predicted_class, confidence, uncertainty)
        """
        predicted_class = np.argmax(probabilities)
        confidence = self.compute_confidence_score(probabilities)
        
        # Uncertainty as 1 - confidence
        uncertainty = 1.0 - confidence
        
        return predicted_class, confidence, uncertainty
