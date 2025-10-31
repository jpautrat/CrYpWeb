"""
Kill switch for emergency trading halt.
"""
from typing import Optional, Dict
from datetime import datetime
from pathlib import Path
from loguru import logger


class KillSwitch:
    """Emergency kill switch for trading"""
    
    def __init__(self, password: Optional[str] = None, config_file: Optional[Path] = None):
        self.password = password
        self.config_file = config_file or Path("kill_switch.flag")
        self.active = False
        self.activated_at: Optional[datetime] = None
        self.reason: str = ""
    
    def activate(self, password: Optional[str] = None, reason: str = "") -> bool:
        """Activate kill switch"""
        if self.password and password != self.password:
            logger.warning("Incorrect kill switch password")
            return False
        
        self.active = True
        self.activated_at = datetime.now()
        self.reason = reason or "Manual activation"
        
        # Create flag file
        try:
            with open(self.config_file, 'w') as f:
                f.write(f"KILL_SWITCH_ACTIVE=1\n")
                f.write(f"ACTIVATED_AT={self.activated_at.isoformat()}\n")
                f.write(f"REASON={self.reason}\n")
            logger.critical(f"KILL SWITCH ACTIVATED: {self.reason}")
            return True
        except Exception as e:
            logger.error(f"Failed to write kill switch flag: {e}")
            return False
    
    def deactivate(self, password: Optional[str] = None) -> bool:
        """Deactivate kill switch"""
        if self.password and password != self.password:
            return False
        
        self.active = False
        self.activated_at = None
        self.reason = ""
        
        # Remove flag file
        try:
            if self.config_file.exists():
                self.config_file.unlink()
            logger.info("Kill switch deactivated")
            return True
        except Exception as e:
            logger.error(f"Failed to remove kill switch flag: {e}")
            return False
    
    def check(self) -> bool:
        """Check if kill switch is active"""
        # Check flag file
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    content = f.read()
                    if 'KILL_SWITCH_ACTIVE=1' in content:
                        self.active = True
                        return True
            except Exception as e:
                logger.error(f"Error reading kill switch flag: {e}")
        
        return self.active
    
    def get_status(self) -> Dict:
        """Get kill switch status"""
        is_active = self.check()
        return {
            'active': is_active,
            'activated_at': self.activated_at.isoformat() if self.activated_at else None,
            'reason': self.reason
        }
