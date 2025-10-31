"""
Dynamic Threshold Management
Handles adaptive thresholds for trading decisions based on market conditions.
"""

import numpy as np
import pandas as pd
from typing import Dict, Optional
from datetime import datetime, timedelta
from loguru import logger


class ThresholdManager:
    """
    Manages dynamic thresholds for trading decisions.
    Adjusts confidence thresholds, position sizes, and other parameters
    based on recent model performance and market conditions.
    """
    
    def __init__(self, base_confidence: float = 0.65):
        self.base_confidence = base_confidence
        self.performance_history: Dict[str, list] = {}
        self.threshold_adjustments: Dict[str, float] = {}
        
        logger.info(f"ThresholdManager initialized with base_confidence={base_confidence}")
    
    def update_performance(self, pair: str, prediction: float, actual: float, profit: float):
        """
        Update performance history with a new prediction outcome.
        
        Args:
            pair: Trading pair symbol
            prediction: Model prediction (0-1)
            actual: Actual outcome (0-1)
            profit: Realized profit/loss
        """
        if pair not in self.performance_history:
            self.performance_history[pair] = []
        
        self.performance_history[pair].append({
            'timestamp': datetime.now(),
            'prediction': prediction,
            'actual': actual,
            'profit': profit,
            'correct': abs(prediction - actual) < 0.2  # Within 20% is "correct"
        })
        
        # Keep only last 100 predictions per pair
        if len(self.performance_history[pair]) > 100:
            self.performance_history[pair] = self.performance_history[pair][-100:]
        
        # Recalculate threshold adjustment
        self._recalculate_threshold(pair)
    
    def _recalculate_threshold(self, pair: str):
        """Recalculate confidence threshold adjustment based on recent performance"""
        if pair not in self.performance_history:
            return
        
        history = self.performance_history[pair]
        if len(history) < 10:
            return  # Need minimum history
        
        recent_history = history[-20:]  # Last 20 predictions
        
        # Calculate recent accuracy
        accuracy = sum(1 for h in recent_history if h['correct']) / len(recent_history)
        
        # Calculate recent profitability
        avg_profit = np.mean([h['profit'] for h in recent_history])
        
        # Adjust threshold based on performance
        if accuracy > 0.7 and avg_profit > 0:
            # Good performance - can lower threshold slightly
            adjustment = -0.05
        elif accuracy < 0.5 or avg_profit < 0:
            # Poor performance - raise threshold
            adjustment = 0.10
        else:
            # Neutral performance
            adjustment = 0.0
        
        self.threshold_adjustments[pair] = adjustment
        
        logger.debug(
            f"{pair} threshold adjustment: {adjustment:+.3f} "
            f"(accuracy={accuracy:.2%}, avg_profit={avg_profit:.4f})"
        )
    
    def get_confidence_threshold(self, pair: str) -> float:
        """
        Get the current confidence threshold for a pair.
        
        Args:
            pair: Trading pair symbol
            
        Returns:
            Confidence threshold (0-1)
        """
        adjustment = self.threshold_adjustments.get(pair, 0.0)
        threshold = self.base_confidence + adjustment
        
        # Clamp between reasonable bounds
        threshold = max(0.55, min(0.85, threshold))
        
        return threshold
    
    def get_position_size_multiplier(self, pair: str, confidence: float) -> float:
        """
        Get position size multiplier based on confidence level.
        
        Args:
            pair: Trading pair symbol
            confidence: Model confidence (0-1)
            
        Returns:
            Multiplier for position size (0-1)
        """
        threshold = self.get_confidence_threshold(pair)
        
        if confidence >= 0.90:
            return 1.0  # Maximum position
        elif confidence >= 0.80:
            return 0.75
        elif confidence >= 0.70:
            return 0.50
        elif confidence >= threshold:
            return 0.25
        else:
            return 0.0  # Below threshold - no trade
    
    def get_recent_performance(self, pair: str, hours: int = 24) -> Optional[Dict]:
        """
        Get performance statistics for recent period.
        
        Args:
            pair: Trading pair symbol
            hours: Number of hours to look back
            
        Returns:
            Dictionary with performance metrics
        """
        if pair not in self.performance_history:
            return None
        
        cutoff = datetime.now() - timedelta(hours=hours)
        recent = [
            h for h in self.performance_history[pair]
            if h['timestamp'] > cutoff
        ]
        
        if not recent:
            return None
        
        return {
            'trades': len(recent),
            'accuracy': sum(1 for h in recent if h['correct']) / len(recent),
            'avg_profit': np.mean([h['profit'] for h in recent]),
            'total_profit': sum(h['profit'] for h in recent),
            'win_rate': sum(1 for h in recent if h['profit'] > 0) / len(recent),
        }
