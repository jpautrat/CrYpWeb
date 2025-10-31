"""
Kraken API authentication manager.
Handles signature generation for authenticated requests.
"""
import base64
import hashlib
import hmac
import time
from typing import Dict, Optional
from urllib.parse import urlencode


class KrakenAuthManager:
    """Manages Kraken API authentication."""
    
    def __init__(self, api_key: str, api_secret: str):
        """
        Initialize auth manager.
        
        Args:
            api_key: Kraken API key
            api_secret: Kraken API secret (base64)
        """
        self.api_key = api_key
        self.api_secret = api_secret
    
    def generate_signature(self, urlpath: str, data: Dict) -> str:
        """
        Generate API signature for authenticated requests.
        
        Args:
            urlpath: API endpoint path (e.g., '/0/private/Balance')
            data: Request parameters (nonce will be added)
            
        Returns:
            Base64-encoded signature
        """
        # Decode API secret
        secret = base64.b64decode(self.api_secret)
        
        # Add nonce
        nonce = str(int(time.time() * 1000))
        data['nonce'] = nonce
        
        # Create message
        postdata = urlencode(data)
        message = urlpath + hashlib.sha256(nonce.encode() + postdata.encode()).digest()
        
        # Generate signature
        signature = hmac.new(
            secret,
            message.encode(),
            hashlib.sha512
        ).digest()
        
        return base64.b64encode(signature).decode()
    
    def get_headers(self, urlpath: str, data: Dict) -> Dict[str, str]:
        """
        Get headers for authenticated request.
        
        Args:
            urlpath: API endpoint path
            data: Request parameters
            
        Returns:
            Headers dictionary
        """
        signature = self.generate_signature(urlpath, data)
        nonce = data.get('nonce', str(int(time.time() * 1000)))
        
        return {
            'API-Key': self.api_key,
            'API-Sign': signature,
        }
