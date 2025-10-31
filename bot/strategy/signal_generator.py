"""
Signal Generator - Orchestrates signal generation across all pairs
"""

from typing import Dict, List
from datetime import datetime
from loguru import logger
import pandas as pd

from .base_strategy import StrategyInterface
from ..data.feature_engineer import FeatureEngineer


class SignalGenerator:
    """
    Generates trading signals for multiple pairs using a strategy.
    Coordinates feature computation and signal generation.
    """
    
    def __init__(
        self,
        strategy: StrategyInterface,
        feature_engineer: FeatureEngineer,
        max_decision_latency_ms: int = 100
    ):
        """
        Initialize signal generator.
        
        Args:
            strategy: Trading strategy implementation
            feature_engineer: Feature computation engine
            max_decision_latency_ms: Maximum allowed decision time
        """
        self.strategy = strategy
        self.feature_engineer = feature_engineer
        self.max_decision_latency_ms = max_decision_latency_ms
        
        self.signal_count = 0
        self.signals_by_side = {'buy': 0, 'sell': 0, 'hold': 0}
        
        logger.info("SignalGenerator initialized")
    
    def generate_signal(
        self,
        pair: str,
        timestamp: datetime = None
    ) -> Dict:
        """
        Generate signal for a single pair.
        
        Args:
            pair: Trading pair
            timestamp: Timestamp for signal (defaults to now)
            
        Returns:
            Signal dictionary
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        start_time = datetime.now()
        
        try:
            # Compute features
            features = self.feature_engineer.compute_features(
                pair=pair,
                timestamp=timestamp,
                lookback_seconds=300
            )
            
            if features.empty:
                logger.warning(f"No features computed for {pair}")
                return self._empty_signal(pair, "No features")
            
            # Generate signal from strategy
            signal = self.strategy.signal(features, pair, timestamp)
            
            # Check latency
            latency_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            if latency_ms > self.max_decision_latency_ms:
                logger.warning(
                    f"Signal generation exceeded latency limit: {latency_ms:.1f}ms > "
                    f"{self.max_decision_latency_ms}ms for {pair}"
                )
            
            # Track statistics
            self.signal_count += 1
            self.signals_by_side[signal['side']] += 1
            
            signal['pair'] = pair
            signal['timestamp'] = timestamp.isoformat()
            signal['latency_ms'] = latency_ms
            
            return signal
            
        except Exception as e:
            logger.error(f"Signal generation failed for {pair}: {e}", exc_info=True)
            return self._empty_signal(pair, f"Error: {str(e)}")
    
    def generate_signals_batch(
        self,
        pairs: List[str],
        timestamp: datetime = None
    ) -> Dict[str, Dict]:
        """
        Generate signals for multiple pairs.
        
        Args:
            pairs: List of trading pairs
            timestamp: Timestamp for signals
            
        Returns:
            Dictionary mapping pairs to signals
        """
        signals = {}
        
        for pair in pairs:
            signal = self.generate_signal(pair, timestamp)
            signals[pair] = signal
        
        return signals
    
    def _empty_signal(self, pair: str, reason: str) -> Dict:
        """Generate empty/hold signal"""
        return {
            'pair': pair,
            'side': 'hold',
            'size': 0.0,
            'limit_price': None,
            'ttl': 0,
            'confidence': 0.0,
            'reason': reason,
            'expected_return': 0.0,
            'risk_score': 1.0,
            'timestamp': datetime.now().isoformat(),
            'latency_ms': 0.0
        }
    
    def get_statistics(self) -> Dict:
        """Get signal generation statistics"""
        return {
            'total_signals': self.signal_count,
            'signals_by_side': self.signals_by_side.copy(),
            'strategy_status': self.strategy.get_status()
        }
