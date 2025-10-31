"""Order management system."""
import time
from typing import Dict, Optional
from datetime import datetime
from loguru import logger

from bot.core.key_pool import KeyPool
from bot.core.rest_client import KrakenRESTClient


class OrderManager:
    """Manages order lifecycle."""
    
    def __init__(self, key_pool: KeyPool):
        self.key_pool = key_pool
        self.active_orders: Dict[str, Dict] = {}
    
    def submit_order(self, pair: str, side: str, volume: float, 
                    price: Optional[float] = None, post_only: bool = True,
                    key_id: Optional[int] = None) -> Dict:
        start_time = time.time()
        client, used_key_id = self.key_pool.get_key(key_id)
        
        try:
            kraken_pair = pair.replace("BTC", "XBT").replace("/", "")
            order_type = "limit" if price else "market"
            
            result = client.add_order(
                pair=kraken_pair,
                side=side,
                order_type=order_type,
                volume=volume,
                price=price,
                post_only=post_only,
            )
            
            response_time = (time.time() - start_time) * 1000
            
            if result and "result" in result and "txid" in result["result"]:
                txid = result["result"]["txid"]
                order_id = txid[0] if isinstance(txid, list) else txid
                
                self.active_orders[order_id] = {
                    'order_id': order_id,
                    'pair': pair,
                    'side': side,
                    'volume': volume,
                    'price': price,
                    'status': 'pending',
                    'submitted_at': datetime.utcnow(),
                }
                
                self.key_pool.record_request(used_key_id, True, response_time)
                logger.info(f"Order submitted: {side} {volume} {pair} @ {price}")
                
                return {
                    'order_id': order_id,
                    'status': 'pending',
                    'latency_ms': response_time,
                }
            else:
                error = result.get('error', ['Unknown'])[0] if result else 'No response'
                self.key_pool.record_request(used_key_id, False, response_time, error)
                return {'status': 'rejected', 'error': error}
        
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            self.key_pool.record_request(used_key_id, False, response_time, str(e))
            logger.error(f"Order error: {e}")
            return {'status': 'error', 'error': str(e)}
