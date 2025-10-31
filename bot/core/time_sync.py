"""
Time synchronization with NTP servers for accurate timestamping.
"""
import time
import socket
import struct
from datetime import datetime, timezone
from typing import Optional
from loguru import logger


class TimeSync:
    """Synchronizes system time with NTP servers."""
    
    NTP_SERVERS = [
        "pool.ntp.org",
        "time.google.com",
        "time.windows.com",
        "time.cloudflare.com",
    ]
    
    NTP_PACKET_FORMAT = "!12I"
    NTP_DELTA = 2208988800  # 1970-01-01 00:00:00
    
    def __init__(self):
        """Initialize time sync."""
        self.offset_seconds: float = 0.0
        self.last_sync: Optional[datetime] = None
        self.sync_interval_seconds = 3600  # Sync every hour
    
    def sync(self) -> bool:
        """
        Sync with NTP server.
        
        Returns:
            True if sync successful
        """
        for server in self.NTP_SERVERS:
            try:
                offset = self._query_ntp(server)
                if offset is not None:
                    self.offset_seconds = offset
                    self.last_sync = datetime.now(timezone.utc)
                    logger.info(f"Time synchronized with {server}, offset: {offset:.3f}s")
                    return True
            except Exception as e:
                logger.warning(f"Failed to sync with {server}: {e}")
                continue
        
        logger.error("Failed to sync with any NTP server")
        return False
    
    def _query_ntp(self, server: str) -> Optional[float]:
        """
        Query NTP server for time offset.
        
        Args:
            server: NTP server hostname
            
        Returns:
            Time offset in seconds, or None if failed
        """
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            client.settimeout(3.0)
            
            # NTP request packet
            data = b'\x1b' + 47 * b'\0'
            client.sendto(data, (server, 123))
            
            # Receive response
            response, _ = client.recvfrom(48)
            client.close()
            
            # Parse response
            unpacked = struct.unpack(self.NTP_PACKET_FORMAT, response[0:48])
            server_time = unpacked[10] + float(unpacked[11]) / 2**32
            server_time -= self.NTP_DELTA
            
            # Calculate offset
            client_time = time.time()
            offset = server_time - client_time
            
            return offset
        except Exception as e:
            logger.debug(f"NTP query error for {server}: {e}")
            return None
    
    def get_synced_time(self) -> datetime:
        """
        Get current time adjusted for NTP offset.
        
        Returns:
            Synchronized datetime
        """
        # Auto-sync if needed
        if (
            self.last_sync is None
            or (datetime.now(timezone.utc) - self.last_sync).total_seconds() > self.sync_interval_seconds
        ):
            self.sync()
        
        now = datetime.now(timezone.utc)
        if self.offset_seconds != 0:
            from datetime import timedelta
            now += timedelta(seconds=self.offset_seconds)
        
        return now
    
    def get_timestamp_ms(self) -> int:
        """Get synchronized timestamp in milliseconds."""
        return int(self.get_synced_time().timestamp() * 1000)
