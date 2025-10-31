"""
Order management system for placing, tracking, and managing orders.
"""
import time
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from loguru import logger

from ..core.rest_client import KrakenRESTClient
from ..config.settings import SystemConfig


class OrderManager:
    """Manages order lifecycle and execution"""
    
    def __init__(self, rest_client: KrakenRESTClient, system_config: SystemConfig):
        self.rest_client = rest_client
        self.system_config = system_config
        self.pending_orders: Dict[str, Dict] = {}
        self.filled_orders: List[Dict] = []
        self.order_timeout = system_config.order_timeout_seconds
    
    def place_order(self, pair: str, side: str, size: float, price: Optional[float] = None,
                   order_type: str = "limit", post_only: bool = True) -> Dict:
        """
        Place an order.
        
        Args:
            pair: Trading pair
            side: 'buy' or 'sell'
            size: Order size in base currency
            price: Limit price (required for limit orders)
            order_type: 'limit' or 'market'
            post_only: Use post-only (maker) order
        
        Returns:
            Order result dictionary
        """
        start_time = time.time()
        
        try:
            # Place order via REST API
            result = self.rest_client.place_order(
                pair=pair,
                side=side,
                order_type=order_type,
                volume=size,
                price=price,
                post_only=post_only
            )
            
            latency_ms = (time.time() - start_time) * 1000
            
            if result and 'txid' in result:
                txid = result['txid'][0] if isinstance(result['txid'], list) else result['txid']
                
                order_record = {
                    'order_id': txid,
                    'pair': pair,
                    'side': side,
                    'size': size,
                    'price': price,
                    'order_type': order_type,
                    'status': 'pending',
                    'submitted_at': datetime.now(),
                    'latency_ms': latency_ms
                }
                
                self.pending_orders[txid] = order_record
                
                logger.info(f"Order placed: {side} {size} {pair} @ {price} | ID: {txid}")
                
                return {
                    'success': True,
                    'order_id': txid,
                    'status': 'pending',
                    'latency_ms': latency_ms,
                    'order_record': order_record
                }
            else:
                error_msg = result.get('error', ['Unknown error'])[0] if isinstance(result, dict) else str(result)
                logger.error(f"Failed to place order: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg,
                    'latency_ms': latency_ms
                }
        
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error(f"Exception placing order: {e}")
            return {
                'success': False,
                'error': str(e),
                'latency_ms': latency_ms
            }
    
    def check_order_status(self, order_id: str) -> Dict:
        """Check status of an order"""
        try:
            result = self.rest_client.get_order_status(order_id)
            
            if result and order_id in result:
                order_info = result[order_id]
                
                status = order_info.get('status', 'unknown')
                vol_exec = float(order_info.get('vol_exec', 0))
                cost = float(order_info.get('cost', 0))
                fee = float(order_info.get('fee', 0))
                
                # Update pending order
                if order_id in self.pending_orders:
                    self.pending_orders[order_id]['status'] = status
                    self.pending_orders[order_id]['filled_size'] = vol_exec
                    self.pending_orders[order_id]['cost'] = cost
                    self.pending_orders[order_id]['fee'] = fee
                
                # Move to filled if fully executed
                if status == 'closed' or status == 'filled':
                    if order_id in self.pending_orders:
                        order_record = self.pending_orders.pop(order_id)
                        order_record['filled_at'] = datetime.now()
                        order_record['final_status'] = status
                        self.filled_orders.append(order_record)
                        logger.info(f"Order {order_id} filled: {vol_exec} @ {cost}")
                
                return {
                    'order_id': order_id,
                    'status': status,
                    'filled_size': vol_exec,
                    'cost': cost,
                    'fee': fee
                }
            
            return {'order_id': order_id, 'status': 'unknown'}
        
        except Exception as e:
            logger.error(f"Error checking order status: {e}")
            return {'order_id': order_id, 'status': 'error', 'error': str(e)}
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order"""
        try:
            result = self.rest_client.cancel_order(order_id)
            
            if result and 'count' in result and result['count'] > 0:
                if order_id in self.pending_orders:
                    self.pending_orders[order_id]['status'] = 'cancelled'
                    self.pending_orders.pop(order_id)
                logger.info(f"Order {order_id} cancelled")
                return True
            
            return False
        
        except Exception as e:
            logger.error(f"Error cancelling order: {e}")
            return False
    
    def cancel_all_orders(self) -> bool:
        """Cancel all pending orders"""
        try:
            result = self.rest_client.cancel_all_orders()
            
            if result and 'count' in result:
                cancelled_count = result['count']
                self.pending_orders.clear()
                logger.info(f"Cancelled {cancelled_count} orders")
                return True
            
            return False
        
        except Exception as e:
            logger.error(f"Error cancelling all orders: {e}")
            return False
    
    def monitor_pending_orders(self):
        """Monitor and update pending orders"""
        expired_orders = []
        
        for order_id, order in list(self.pending_orders.items()):
            # Check timeout
            elapsed = (datetime.now() - order['submitted_at']).total_seconds()
            
            if elapsed > self.order_timeout:
                # Cancel expired order
                logger.warning(f"Order {order_id} expired after {elapsed:.1f}s, cancelling")
                if self.cancel_order(order_id):
                    expired_orders.append(order_id)
            else:
                # Check status
                self.check_order_status(order_id)
        
        return expired_orders
    
    def get_pending_orders(self) -> Dict[str, Dict]:
        """Get all pending orders"""
        return self.pending_orders.copy()
    
    def get_filled_orders(self, limit: int = 100) -> List[Dict]:
        """Get recent filled orders"""
        return self.filled_orders[-limit:]
    
    def get_order_statistics(self) -> Dict:
        """Get order execution statistics"""
        if not self.filled_orders:
            return {}
        
        recent_fills = self.filled_orders[-100:]
        
        total_orders = len(recent_fills)
        total_latency = sum(o.get('latency_ms', 0) for o in recent_fills)
        avg_latency = total_latency / total_orders if total_orders > 0 else 0.0
        
        return {
            'pending_count': len(self.pending_orders),
            'filled_count': len(self.filled_orders),
            'recent_fills': total_orders,
            'avg_latency_ms': avg_latency
        }
