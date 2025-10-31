"""
Time Synchronization for accurate timestamps
Ensures system time is synchronized with Kraken servers.
"""

import time
import ntplib
from datetime import datetime
from typing import Optional
from loguru import logger


class TimeSync:
    """
    Time synchronization manager.
    Tracks offset between local time and NTP/Kraken time.
    """
    
    NTP_SERVERS = [
        'time.google.com',
        'time.cloudflare.com',
        'pool.ntp.org',
        'time.nist.gov'
    ]
    
    def __init__(self):
        self.time_offset_ms: float = 0.0
        self.last_sync: Optional[datetime] = None
        self.ntp_client = ntplib.NTPClient()
        
        logger.info("TimeSync initialized")
        
        # Perform initial sync
        self.sync()
    
    def sync(self) -> bool:
        """
        Synchronize time with NTP servers.
        
        Returns:
            True if sync successful
        """
        for ntp_server in self.NTP_SERVERS:
            try:
                response = self.ntp_client.request(ntp_server, timeout=5, version=3)
                
                # Calculate offset in milliseconds
                self.time_offset_ms = response.offset * 1000
                self.last_sync = datetime.now()
                
                logger.info(
                    f"Time synchronized with {ntp_server}: "
                    f"offset={self.time_offset_ms:.2f}ms"
                )
                
                return True
                
            except Exception as e:
                logger.warning(f"Failed to sync with {ntp_server}: {e}")
                continue
        
        logger.error("Failed to sync with any NTP server")
        return False
    
    def get_current_time_ms(self) -> int:
        """
        Get current time in milliseconds with offset applied.
        
        Returns:
            Corrected timestamp in milliseconds
        """
        local_ms = int(time.time() * 1000)
        corrected_ms = int(local_ms + self.time_offset_ms)
        return corrected_ms
    
    def get_current_time_seconds(self) -> float:
        """
        Get current time in seconds with offset applied.
        
        Returns:
            Corrected timestamp in seconds
        """
        return self.get_current_time_ms() / 1000.0
    
    def should_resync(self, interval_hours: int = 1) -> bool:
        """
        Check if time should be re-synchronized.
        
        Args:
            interval_hours: Hours between syncs
            
        Returns:
            True if resync needed
        """
        if self.last_sync is None:
            return True
        
        hours_since_sync = (datetime.now() - self.last_sync).total_seconds() / 3600
        return hours_since_sync >= interval_hours
    
    def get_sync_status(self) -> dict:
        """Get synchronization status"""
        return {
            'time_offset_ms': self.time_offset_ms,
            'last_sync': self.last_sync.isoformat() if self.last_sync else None,
            'is_synced': self.last_sync is not None
        }
