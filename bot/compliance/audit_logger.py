"""
Audit logging for regulatory compliance.
Logs all trading decisions and order executions.
"""
import json
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
from loguru import logger

from bot.config.settings import settings


class AuditLogger:
    """Logs trading activities for audit trail."""
    
    def __init__(self):
        """Initialize audit logger."""
        self.audit_dir = settings.system.logs_dir / "audit"
        self.audit_dir.mkdir(parents=True, exist_ok=True)
        
        # Create daily audit log file
        today = datetime.utcnow().strftime("%Y%m%d")
        self.audit_file = self.audit_dir / f"audit_{today}.jsonl"
    
    def log_order(self, order_data: Dict[str, Any]):
        """
        Log order submission.
        
        Args:
            order_data: Order information including pair, size, price, timestamp, etc.
        """
        audit_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "order_submission",
            "data": order_data,
        }
        self._write_audit_entry(audit_entry)
    
    def log_fill(self, fill_data: Dict[str, Any]):
        """
        Log order fill.
        
        Args:
            fill_data: Fill information including order_id, fill_price, fees, etc.
        """
        audit_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "order_fill",
            "data": fill_data,
        }
        self._write_audit_entry(audit_entry)
    
    def log_decision(self, decision_data: Dict[str, Any]):
        """
        Log trading decision.
        
        Args:
            decision_data: Decision information including signal, confidence, features, etc.
        """
        audit_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "trading_decision",
            "data": decision_data,
        }
        self._write_audit_entry(audit_entry)
    
    def log_compliance_check(self, check_data: Dict[str, Any]):
        """
        Log compliance check.
        
        Args:
            check_data: Compliance check results
        """
        audit_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "compliance_check",
            "data": check_data,
        }
        self._write_audit_entry(audit_entry)
    
    def _write_audit_entry(self, entry: Dict[str, Any]):
        """Write audit entry to log file."""
        try:
            with open(self.audit_file, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logger.error(f"Failed to write audit entry: {e}")
