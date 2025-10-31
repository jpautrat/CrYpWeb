"""Kill switch for emergency trading halt."""
import os
from pathlib import Path
from typing import Optional
from loguru import logger

from bot.config.settings import settings


class KillSwitch:
    """Emergency kill switch system."""
    
    def __init__(self):
        self.enabled = False
        self.kill_file = Path("data/.kill_switch")
        self.password = settings.system.kill_switch_password
    
    def is_active(self) -> bool:
        """Check if kill switch is active."""
        return self.enabled or self.kill_file.exists()
    
    def activate(self, password: Optional[str] = None) -> bool:
        """Activate kill switch."""
        if self.password and password != self.password:
            return False
        
        self.enabled = True
        self.kill_file.touch()
        logger.critical("KILL SWITCH ACTIVATED - Trading halted")
        return True
    
    def deactivate(self, password: Optional[str] = None) -> bool:
        """Deactivate kill switch."""
        if self.password and password != self.password:
            return False
        
        self.enabled = False
        if self.kill_file.exists():
            self.kill_file.unlink()
        logger.info("Kill switch deactivated")
        return True
