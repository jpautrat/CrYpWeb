"""
Kill Switch - Emergency trading halt mechanism
"""

import os
from typing import Optional
from datetime import datetime
from loguru import logger
from pathlib import Path


class KillSwitch:
    """
    Emergency kill switch to immediately halt all trading.
    Multiple activation methods for maximum safety.
    """
    
    def __init__(
        self,
        password: str,
        kill_switch_file: str = "data/.kill_switch"
    ):
        """
        Initialize kill switch.
        
        Args:
            password: Emergency password to activate
            kill_switch_file: File path for file-based kill switch
        """
        self.password = password
        self.kill_switch_file = Path(kill_switch_file)
        self.kill_switch_file.parent.mkdir(parents=True, exist_ok=True)
        
        self.is_active = False
        self.activated_at: Optional[datetime] = None
        self.activation_reason = ""
        
        # Check for existing kill switch file on startup
        if self.kill_switch_file.exists():
            self._activate("Kill switch file detected on startup")
        
        logger.info("KillSwitch initialized")
    
    def activate(self, password: str, reason: str = "Manual activation") -> bool:
        """
        Activate kill switch with password.
        
        Args:
            password: Emergency password
            reason: Reason for activation
            
        Returns:
            True if activated successfully
        """
        if password != self.password:
            logger.error("Kill switch activation FAILED: incorrect password")
            return False
        
        self._activate(reason)
        return True
    
    def _activate(self, reason: str):
        """Internal activation method"""
        if not self.is_active:
            self.is_active = True
            self.activated_at = datetime.now()
            self.activation_reason = reason
            
            # Create kill switch file
            with open(self.kill_switch_file, 'w') as f:
                f.write(f"{datetime.now().isoformat()}\n{reason}\n")
            
            logger.critical(f"🛑 KILL SWITCH ACTIVATED: {reason}")
            logger.critical("ALL TRADING HALTED IMMEDIATELY")
    
    def deactivate(self, password: str) -> bool:
        """
        Deactivate kill switch with password.
        
        Args:
            password: Emergency password
            
        Returns:
            True if deactivated successfully
        """
        if password != self.password:
            logger.error("Kill switch deactivation FAILED: incorrect password")
            return False
        
        self.is_active = False
        self.activated_at = None
        self.activation_reason = ""
        
        # Remove kill switch file
        if self.kill_switch_file.exists():
            self.kill_switch_file.unlink()
        
        logger.warning("Kill switch deactivated - trading may resume")
        return True
    
    def check(self) -> bool:
        """
        Check if kill switch is active.
        Also checks for kill switch file.
        
        Returns:
            True if trading is allowed, False if halted
        """
        # Check file-based kill switch
        if self.kill_switch_file.exists() and not self.is_active:
            self._activate("Kill switch file detected")
        
        return not self.is_active
    
    def get_status(self) -> dict:
        """Get kill switch status"""
        return {
            'is_active': self.is_active,
            'activated_at': self.activated_at.isoformat() if self.activated_at else None,
            'activation_reason': self.activation_reason,
            'kill_switch_file_exists': self.kill_switch_file.exists()
        }
