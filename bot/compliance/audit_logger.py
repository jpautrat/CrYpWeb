"""
Audit Logger - Comprehensive audit trail for regulatory compliance
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from loguru import logger
import hashlib


class AuditLogger:
    """
    Immutable audit logging system for regulatory compliance.
    All trading decisions, orders, and compliance checks are logged.
    """
    
    def __init__(self, audit_log_dir: str = "data/logs/audit"):
        self.audit_log_dir = Path(audit_log_dir)
        self.audit_log_dir.mkdir(parents=True, exist_ok=True)
        
        self.current_log_file = None
        self.previous_hash = "0" * 64  # Genesis hash
        
        self._rotate_log_file()
        
        logger.info(f"AuditLogger initialized: {self.audit_log_dir}")
    
    def _rotate_log_file(self):
        """Create new log file for current day"""
        date_str = datetime.now().strftime("%Y%m%d")
        self.current_log_file = self.audit_log_dir / f"audit_{date_str}.jsonl"
        
        if not self.current_log_file.exists():
            logger.info(f"Created new audit log: {self.current_log_file}")
    
    def _compute_hash(self, entry: Dict[str, Any]) -> str:
        """Compute hash of entry for tamper detection"""
        # Include previous hash to create blockchain-like chain
        entry_with_prev = {**entry, 'previous_hash': self.previous_hash}
        entry_json = json.dumps(entry_with_prev, sort_keys=True)
        return hashlib.sha256(entry_json.encode()).hexdigest()
    
    def _log_entry(self, event_type: str, data: Dict[str, Any]):
        """Write audit log entry with tamper-proof hash"""
        # Rotate log file if day changed
        date_str = datetime.now().strftime("%Y%m%d")
        expected_file = self.audit_log_dir / f"audit_{date_str}.jsonl"
        if expected_file != self.current_log_file:
            self._rotate_log_file()
        
        entry = {
            'timestamp': datetime.now().isoformat(),
            'event_type': event_type,
            'data': data
        }
        
        # Compute hash for tamper detection
        entry_hash = self._compute_hash(entry)
        entry['hash'] = entry_hash
        entry['previous_hash'] = self.previous_hash
        
        # Write to log file
        with open(self.current_log_file, 'a') as f:
            f.write(json.dumps(entry) + '\n')
        
        # Update previous hash
        self.previous_hash = entry_hash
    
    def log_trade_decision(
        self,
        pair: str,
        signal: str,
        confidence: float,
        expected_return: float,
        reason: str,
        features: Optional[Dict] = None
    ):
        """Log a trading decision"""
        self._log_entry('trade_decision', {
            'pair': pair,
            'signal': signal,
            'confidence': confidence,
            'expected_return': expected_return,
            'reason': reason,
            'features': features or {}
        })
        
        logger.info(
            f"AUDIT: Trade decision | {pair} | {signal} | "
            f"confidence={confidence:.3f} | expected_return={expected_return:.4f}"
        )
    
    def log_order_submitted(
        self,
        order_id: str,
        pair: str,
        side: str,
        order_type: str,
        size: float,
        price: Optional[float],
        key_id: int
    ):
        """Log order submission"""
        self._log_entry('order_submitted', {
            'order_id': order_id,
            'pair': pair,
            'side': side,
            'order_type': order_type,
            'size': size,
            'price': price,
            'key_id': key_id
        })
        
        logger.info(
            f"AUDIT: Order submitted | {order_id} | {side} {size} {pair} @ {price}"
        )
    
    def log_order_filled(
        self,
        order_id: str,
        pair: str,
        side: str,
        fill_price: float,
        fill_size: float,
        fees: float,
        profit: Optional[float] = None
    ):
        """Log order fill"""
        self._log_entry('order_filled', {
            'order_id': order_id,
            'pair': pair,
            'side': side,
            'fill_price': fill_price,
            'fill_size': fill_size,
            'fees': fees,
            'profit': profit
        })
        
        logger.info(
            f"AUDIT: Order filled | {order_id} | {side} {fill_size} {pair} @ "
            f"{fill_price} | fees=${fees:.4f}"
        )
    
    def log_order_rejected(
        self,
        order_id: str,
        pair: str,
        side: str,
        size: float,
        reason: str
    ):
        """Log order rejection"""
        self._log_entry('order_rejected', {
            'order_id': order_id,
            'pair': pair,
            'side': side,
            'size': size,
            'reason': reason
        })
        
        logger.warning(
            f"AUDIT: Order rejected | {order_id} | {side} {size} {pair} | {reason}"
        )
    
    def log_compliance_check(
        self,
        pair: str,
        check_type: str,
        passed: bool,
        reason: str
    ):
        """Log compliance check result"""
        self._log_entry('compliance_check', {
            'pair': pair,
            'check_type': check_type,
            'passed': passed,
            'reason': reason
        })
        
        status = "PASSED" if passed else "FAILED"
        logger.info(f"AUDIT: Compliance check {status} | {pair} | {check_type} | {reason}")
    
    def log_circuit_breaker(
        self,
        reason: str,
        trigger_value: float,
        threshold: float,
        duration_minutes: int
    ):
        """Log circuit breaker activation"""
        self._log_entry('circuit_breaker', {
            'reason': reason,
            'trigger_value': trigger_value,
            'threshold': threshold,
            'duration_minutes': duration_minutes
        })
        
        logger.critical(
            f"AUDIT: CIRCUIT BREAKER ACTIVATED | {reason} | "
            f"value={trigger_value:.4f} threshold={threshold:.4f} | "
            f"cooldown={duration_minutes}min"
        )
    
    def log_model_update(
        self,
        pair: str,
        model_type: str,
        metrics: Dict[str, float],
        training_samples: int
    ):
        """Log model training/update"""
        self._log_entry('model_update', {
            'pair': pair,
            'model_type': model_type,
            'metrics': metrics,
            'training_samples': training_samples
        })
        
        logger.info(
            f"AUDIT: Model updated | {pair} | {model_type} | "
            f"samples={training_samples} | metrics={metrics}"
        )
    
    def log_system_event(self, event: str, details: Dict[str, Any]):
        """Log general system event"""
        self._log_entry('system_event', {
            'event': event,
            'details': details
        })
        
        logger.info(f"AUDIT: System event | {event}")
