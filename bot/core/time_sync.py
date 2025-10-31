"""
Time synchronization with NTP servers for accurate timestamping.
Ensures market data timestamps are synchronized with Kraken server time.
"""
import time
import ntplib
from datetime import datetime, timedelta
from typing import Optional
from loguru import logger


class TimeSync:
    """Manages time synchronization with NTP servers"""
    
    NTP_SERVERS = [
        'pool.ntp.org',
        'time.google.com',
        'time.cloudflare.com',
        'time.windows.com'
    ]
    
    def __init__(self):
        self.offset_ms: Optional[float] = None
        self.last_sync: Optional[datetime] = None
        self.sync_interval = timedelta(hours=1)  # Re-sync every hour
    
    def sync(self) -> bool:
        """
        Synchronize time with NTP server.
        Returns True if successful, False otherwise.
        """
        client = ntplib.NTPClient()
        
        for server in self.NTP_SERVERS:
            try:
                response = client.request(server, version=3, timeout=5)
                # Calculate offset in milliseconds
                self.offset_ms = response.offset * 1000
                self.last_sync = datetime.now()
                logger.info(f"Time synced with {server}: offset = {self.offset_ms:.2f}ms")
                return True
            except Exception as e:
                logger.warning(f"Failed to sync with {server}: {e}")
                continue
        
        logger.error("Failed to sync with all NTP servers")
        return False
    
    def get_synced_time(self) -> datetime:
        """
        Get current time adjusted for NTP offset.
        Returns local time if sync unavailable.
        """
        if self.offset_ms is None:
            return datetime.now()
        
        return datetime.now() + timedelta(milliseconds=self.offset_ms)
    
    def get_unix_timestamp(self) -> float:
        """Get Unix timestamp adjusted for offset"""
        if self.offset_ms is None:
            return time.time()
        
        return time.time() + (self.offset_ms / 1000.0)
    
    def should_sync(self) -> bool:
        """Check if time should be re-synced"""
        if self.last_sync is None:
            return True
        
        return datetime.now() - self.last_sync > self.sync_interval
    
    def get_offset_ms(self) -> float:
        """Get current time offset in milliseconds"""
        return self.offset_ms if self.offset_ms is not None else 0.0
    
    def sync_if_needed(self):
        """Sync with NTP if needed"""
        if self.should_sync():
            self.sync()
