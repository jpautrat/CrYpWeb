"""
Execution router for intelligent order routing across API keys.
"""
from typing import Dict, Optional
from datetime import datetime
from loguru import logger

from ..core.key_pool import KeyPool
from .order_manager import OrderManager


class ExecutionRouter:
    """Routes orders through optimal API keys"""
    
    def __init__(self, key_pool: KeyPool, order_manager: OrderManager):
        self.key_pool = key_pool
        self.order_manager = order_manager
        self.routing_strategy = "health_based"  # health_based, round_robin, least_used
    
    def submit_order(self, pair: str, side: str, size: float, price: Optional[float] = None,
                    order_type: str = "limit", post_only: bool = True,
                    key_id: Optional[int] = None) -> Dict:
        """
        Submit order with intelligent routing.
        
        Args:
            pair: Trading pair
            side: 'buy' or 'sell'
            size: Order size
            price: Limit price
            order_type: 'limit' or 'market'
            post_only: Post-only flag
            key_id: Specific API key to use (optional)
        
        Returns:
            Order result dictionary
        """
        # If specific key requested, validate it's available
        if key_id:
            key = next((k for k in self.key_pool.keys if k["id"] == key_id), None)
            if not key:
                logger.warning(f"Requested key {key_id} not found, using pool routing")
                key_id = None
        
        # Route through order manager (which uses REST client with key pool)
        # The REST client automatically handles key routing
        result = self.order_manager.place_order(
            pair=pair,
            side=side,
            size=size,
            price=price,
            order_type=order_type,
            post_only=post_only
        )
        
        return result
    
    def get_routing_health(self) -> Dict:
        """Get health status of routing system"""
        return self.key_pool.get_all_health_status()
    
    def set_routing_strategy(self, strategy: str):
        """Set routing strategy"""
        if strategy in ["health_based", "round_robin", "least_used"]:
            self.routing_strategy = strategy
            logger.info(f"Routing strategy set to: {strategy}")
        else:
            logger.warning(f"Invalid routing strategy: {strategy}")
