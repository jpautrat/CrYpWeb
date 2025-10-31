"""
Kraken API authentication manager.
Handles signature generation and authentication for REST API calls.
"""
import base64
import hashlib
import hmac
import time
from urllib.parse import urlencode
from typing import Dict, Optional


class KrakenAuthManager:
    """Manages Kraken API authentication and signature generation"""
    
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret
    
    def generate_signature(self, urlpath: str, data: Dict) -> str:
        """
        Generate Kraken API signature.
        
        Args:
            urlpath: API endpoint path (e.g., '/0/private/Balance')
            data: Request parameters dictionary
        
        Returns:
            Base64-encoded signature string
        """
        postdata = urlencode(data)
        encoded = (str(data['nonce']) + postdata).encode()
        message = urlpath.encode() + hashlib.sha256(encoded).digest()
        mac = hmac.new(
            base64.b64decode(self.api_secret),
            message,
            hashlib.sha512
        )
        sigdigest = base64.b64encode(mac.digest())
        return sigdigest.decode()
    
    def get_headers(self, urlpath: str, data: Dict) -> Dict[str, str]:
        """
        Get headers for authenticated API request.
        
        Args:
            urlpath: API endpoint path
            data: Request parameters dictionary
        
        Returns:
            Dictionary of HTTP headers
        """
        # Add nonce to data if not present
        if 'nonce' not in data:
            data['nonce'] = int(time.time() * 1000)
        
        signature = self.generate_signature(urlpath, data)
        
        return {
            'API-Key': self.api_key,
            'API-Sign': signature,
            'Content-Type': 'application/x-www-form-urlencoded'
        }
    
    def get_api_key(self) -> str:
        """Get API key"""
        return self.api_key
