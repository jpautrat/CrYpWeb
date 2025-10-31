"""
Audit logger for regulatory compliance.
Logs all trading decisions and actions for audit trail.
"""
import json
from typing import Dict, List
from datetime import datetime
from pathlib import Path
from loguru import logger


class AuditLogger:
    """Logs all trading activities for audit purposes"""
    
    def __init__(self, logs_dir: Path):
        self.logs_dir = Path(logs_dir)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.audit_file = self.logs_dir / "audit_log.jsonl"
    
    def log_decision(self, pair: str, decision: Dict, market_data: Dict, features: Dict):
        """Log trading decision"""
        audit_record = {
            'timestamp': datetime.now().isoformat(),
            'type': 'decision',
            'pair': pair,
            'decision': decision,
            'market_data': market_data,
            'features_summary': {k: float(v) for k, v in features.items() if isinstance(v, (int, float))}
        }
        
        self._write_record(audit_record)
    
    def log_order(self, order_id: str, order_details: Dict, result: Dict):
        """Log order placement"""
        audit_record = {
            'timestamp': datetime.now().isoformat(),
            'type': 'order',
            'order_id': order_id,
            'order_details': order_details,
            'result': result
        }
        
        self._write_record(audit_record)
    
    def log_trade(self, trade_details: Dict):
        """Log completed trade"""
        audit_record = {
            'timestamp': datetime.now().isoformat(),
            'type': 'trade',
            'trade': trade_details
        }
        
        self._write_record(audit_record)
    
    def log_compliance_check(self, pair: str, is_compliant: bool, reason: str):
        """Log compliance check"""
        audit_record = {
            'timestamp': datetime.now().isoformat(),
            'type': 'compliance',
            'pair': pair,
            'is_compliant': is_compliant,
            'reason': reason
        }
        
        self._write_record(audit_record)
    
    def _write_record(self, record: Dict):
        """Write audit record to file"""
        try:
            with open(self.audit_file, 'a') as f:
                f.write(json.dumps(record) + '\n')
        except Exception as e:
            logger.error(f"Failed to write audit record: {e}")
    
    def query_audit_log(self, start_date: datetime = None, end_date: datetime = None,
                        pair: str = None, log_type: str = None) -> List[Dict]:
        """Query audit log"""
        records = []
        
        try:
            with open(self.audit_file, 'r') as f:
                for line in f:
                    try:
                        record = json.loads(line.strip())
                        timestamp = datetime.fromisoformat(record['timestamp'])
                        
                        # Apply filters
                        if start_date and timestamp < start_date:
                            continue
                        if end_date and timestamp > end_date:
                            continue
                        if pair and record.get('pair') != pair:
                            continue
                        if log_type and record.get('type') != log_type:
                            continue
                        
                        records.append(record)
                    except json.JSONDecodeError:
                        continue
        except FileNotFoundError:
            pass
        
        return records
