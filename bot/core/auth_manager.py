"""
Authentication Manager for Kraken API
Handles request signing and authentication for REST and WebSocket APIs.
"""

import hmac
import hashlib
import base64
import urllib.parse
import time
from typing import Dict
from loguru import logger


class AuthManager:
    """
    Manages Kraken API authentication.
    Implements request signing for REST API and WebSocket authentication.
    """
    
    def __init__(self, api_key: str, api_secret: str, key_id: int = 0):
        """
        Initialize authentication manager.
        
        Args:
            api_key: Kraken API key
            api_secret: Kraken API secret
            key_id: Identifier for this key (for logging/tracking)
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.key_id = key_id
        
        logger.debug(f"AuthManager initialized for key_id={key_id}")
    
    def sign_request(self, urlpath: str, data: Dict) -> str:
        """
        Sign a REST API request according to Kraken's authentication scheme.
        
        Args:
            urlpath: API endpoint path (e.g., '/0/private/Balance')
            data: POST data dictionary
            
        Returns:
            Base64-encoded signature
        """
        # Get nonce from data (should be included)
        nonce = data.get('nonce', str(int(time.time() * 1000)))
        
        # Encode POST data
        postdata = urllib.parse.urlencode(data)
        
        # Create message for signing: nonce + postdata
        encoded = (str(nonce) + postdata).encode()
        message = urlpath.encode() + hashlib.sha256(encoded).digest()
        
        # Sign with secret
        secret_decoded = base64.b64decode(self.api_secret)
        signature = hmac.new(secret_decoded, message, hashlib.sha512)
        sigdigest = base64.b64encode(signature.digest())
        
        return sigdigest.decode()
    
    def get_headers(self, urlpath: str, data: Dict) -> Dict[str, str]:
        """
        Get authenticated request headers for REST API.
        
        Args:
            urlpath: API endpoint path
            data: POST data dictionary
            
        Returns:
            Dictionary of HTTP headers
        """
        signature = self.sign_request(urlpath, data)
        
        return {
            'API-Key': self.api_key,
            'API-Sign': signature,
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'ML-Kraken-Pro-Trader/1.0'
        }
    
    def get_websocket_auth_token(self) -> str:
        """
        Get WebSocket authentication token.
        Note: Kraken requires getting a token via REST API first.
        This is handled by the REST client.
        
        Returns:
            WebSocket auth token
        """
        # This will be implemented in the REST client
        # as it requires a REST API call to get the WS token
        return ""
    
    def generate_nonce(self) -> int:
        """
        Generate a unique nonce for API requests.
        Kraken requires monotonically increasing nonces.
        
        Returns:
            Nonce as integer (milliseconds since epoch)
        """
        return int(time.time() * 1000)
