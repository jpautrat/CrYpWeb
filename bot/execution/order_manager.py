"""
Order Manager - Handles order lifecycle and tracking
"""

import time
import uuid
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass
from loguru import logger


class OrderStatus(str, Enum):
    """Order status states"""
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIAL = "partial"
    FILLED = "filled"
    CANCELED = "canceled"
    REJECTED = "rejected"
    FAILED = "failed"


class OrderType(str, Enum):
    """Order types"""
    MARKET = "market"
    LIMIT = "limit"
    POST_ONLY = "post"


@dataclass
class Order:
    """Order data structure"""
    order_id: str
    pair: str
    side: str  # 'buy' or 'sell'
    order_type: str
    size: float  # Volume in base currency
    price: Optional[float]
    status: OrderStatus
    created_at: datetime
    submitted_at: Optional[datetime] = None
    filled_at: Optional[datetime] = None
    fill_price: Optional[float] = None
    fill_size: Optional[float] = None
    fees: float = 0.0
    exchange_order_id: Optional[str] = None
    key_id: Optional[int] = None
    error_message: Optional[str] = None


class OrderManager:
    """
    Manages order lifecycle from creation to completion.
    Tracks all orders, handles timeouts, and provides order status.
    """
    
    def __init__(self, order_timeout_seconds: int = 30):
        """
        Initialize order manager.
        
        Args:
            order_timeout_seconds: Timeout for limit orders
        """
        self.order_timeout_seconds = order_timeout_seconds
        
        self.orders: Dict[str, Order] = {}
        self.active_orders: Dict[str, Order] = {}
        
        logger.info(f"OrderManager initialized: timeout={order_timeout_seconds}s")
    
    def create_order(
        self,
        pair: str,
        side: str,
        size: float,
        order_type: str = "limit",
        price: Optional[float] = None
    ) -> Order:
        """
        Create a new order.
        
        Args:
            pair: Trading pair
            side: 'buy' or 'sell'
            size: Order size in base currency
            order_type: 'market', 'limit', or 'post'
            price: Limit price (required for limit/post orders)
            
        Returns:
            Created order object
        """
        order_id = str(uuid.uuid4())
        
        order = Order(
            order_id=order_id,
            pair=pair,
            side=side,
            order_type=order_type,
            size=size,
            price=price,
            status=OrderStatus.PENDING,
            created_at=datetime.now()
        )
        
        self.orders[order_id] = order
        self.active_orders[order_id] = order
        
        logger.info(
            f"Order created: {order_id} | {side} {size:.8f} {pair} @ "
            f"{price if price else 'market'}"
        )
        
        return order
    
    def mark_submitted(
        self,
        order_id: str,
        exchange_order_id: str,
        key_id: int
    ):
        """Mark order as submitted to exchange"""
        if order_id not in self.orders:
            logger.error(f"Order {order_id} not found")
            return
        
        order = self.orders[order_id]
        order.status = OrderStatus.SUBMITTED
        order.submitted_at = datetime.now()
        order.exchange_order_id = exchange_order_id
        order.key_id = key_id
        
        logger.info(f"Order {order_id} submitted: exchange_id={exchange_order_id}")
    
    def mark_filled(
        self,
        order_id: str,
        fill_price: float,
        fill_size: float,
        fees: float
    ):
        """Mark order as filled"""
        if order_id not in self.orders:
            logger.error(f"Order {order_id} not found")
            return
        
        order = self.orders[order_id]
        order.status = OrderStatus.FILLED
        order.filled_at = datetime.now()
        order.fill_price = fill_price
        order.fill_size = fill_size
        order.fees = fees
        
        # Remove from active orders
        if order_id in self.active_orders:
            del self.active_orders[order_id]
        
        logger.info(
            f"Order {order_id} filled: {fill_size:.8f} @ ${fill_price:.2f} | "
            f"fees=${fees:.4f}"
        )
    
    def mark_canceled(self, order_id: str, reason: str = ""):
        """Mark order as canceled"""
        if order_id not in self.orders:
            logger.error(f"Order {order_id} not found")
            return
        
        order = self.orders[order_id]
        order.status = OrderStatus.CANCELED
        order.error_message = reason
        
        if order_id in self.active_orders:
            del self.active_orders[order_id]
        
        logger.info(f"Order {order_id} canceled: {reason}")
    
    def mark_rejected(self, order_id: str, reason: str):
        """Mark order as rejected"""
        if order_id not in self.orders:
            logger.error(f"Order {order_id} not found")
            return
        
        order = self.orders[order_id]
        order.status = OrderStatus.REJECTED
        order.error_message = reason
        
        if order_id in self.active_orders:
            del self.active_orders[order_id]
        
        logger.warning(f"Order {order_id} rejected: {reason}")
    
    def mark_failed(self, order_id: str, error: str):
        """Mark order as failed"""
        if order_id not in self.orders:
            logger.error(f"Order {order_id} not found")
            return
        
        order = self.orders[order_id]
        order.status = OrderStatus.FAILED
        order.error_message = error
        
        if order_id in self.active_orders:
            del self.active_orders[order_id]
        
        logger.error(f"Order {order_id} failed: {error}")
    
    def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID"""
        return self.orders.get(order_id)
    
    def get_active_orders(self) -> List[Order]:
        """Get all active orders"""
        return list(self.active_orders.values())
    
    def check_timeouts(self) -> List[Order]:
        """
        Check for timed out orders.
        
        Returns:
            List of timed out orders
        """
        timed_out = []
        now = datetime.now()
        timeout_delta = timedelta(seconds=self.order_timeout_seconds)
        
        for order in list(self.active_orders.values()):
            # Only check submitted limit/post orders
            if order.status == OrderStatus.SUBMITTED and order.order_type in ['limit', 'post']:
                if order.submitted_at and now - order.submitted_at > timeout_delta:
                    timed_out.append(order)
                    logger.warning(
                        f"Order {order.order_id} timed out after {self.order_timeout_seconds}s"
                    )
        
        return timed_out
    
    def get_order_summary(self) -> Dict:
        """Get order statistics"""
        total_orders = len(self.orders)
        active_orders = len(self.active_orders)
        
        status_counts = {}
        for order in self.orders.values():
            status_counts[order.status.value] = status_counts.get(order.status.value, 0) + 1
        
        return {
            'total_orders': total_orders,
            'active_orders': active_orders,
            'status_counts': status_counts
        }
