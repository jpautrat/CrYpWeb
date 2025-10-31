"""
Execution Router - Routes orders across API keys with intelligent selection
"""

import time
from typing import Dict, Optional, Tuple
from loguru import logger

from ..core.key_pool import KeyPool, KeyStatus
from ..compliance.compliance_checker import ComplianceChecker
from .order_manager import OrderManager, Order, OrderStatus


class ExecutionRouter:
    """
    Routes order execution across multiple API keys.
    Implements maker-biased strategy with smart order routing.
    """
    
    def __init__(
        self,
        key_pool: KeyPool,
        order_manager: OrderManager,
        compliance_checker: ComplianceChecker,
        maker_price_improvement_bps: float = 1.0
    ):
        """
        Initialize execution router.
        
        Args:
            key_pool: Pool of API keys
            order_manager: Order manager
            compliance_checker: Compliance checker
            maker_price_improvement_bps: Price improvement for limit orders
        """
        self.key_pool = key_pool
        self.order_manager = order_manager
        self.compliance_checker = compliance_checker
        self.maker_price_improvement_bps = maker_price_improvement_bps
        
        logger.info("ExecutionRouter initialized")
    
    def execute_order(
        self,
        pair: str,
        side: str,
        size: float,
        price: float,
        strategy: str = "maker"
    ) -> Tuple[bool, str, Optional[Order]]:
        """
        Execute an order with maker-biased strategy.
        
        Args:
            pair: Trading pair
            side: 'buy' or 'sell'
            size: Order size in base currency
            price: Current market price
            strategy: 'maker' or 'taker'
            
        Returns:
            Tuple of (success, message, order)
        """
        # Pre-trade compliance check
        is_compliant, reason = self.compliance_checker.check_order(
            pair=pair,
            side=side,
            size=size,
            price=price
        )
        
        if not is_compliant:
            logger.error(f"Compliance check failed: {reason}")
            return False, reason, None
        
        # Get best API key
        key_status = self.key_pool.get_best_key()
        if not key_status:
            return False, "No API keys available", None
        
        # Execute based on strategy
        if strategy == "maker":
            return self._execute_maker_order(pair, side, size, price, key_status)
        else:
            return self._execute_taker_order(pair, side, size, price, key_status)
    
    def _execute_maker_order(
        self,
        pair: str,
        side: str,
        size: float,
        market_price: float,
        key_status: KeyStatus
    ) -> Tuple[bool, str, Optional[Order]]:
        """
        Execute maker (post-only limit) order.
        
        Args:
            pair: Trading pair
            side: 'buy' or 'sell'
            size: Order size
            market_price: Current market price
            key_status: API key to use
            
        Returns:
            Tuple of (success, message, order)
        """
        # Calculate limit price with small improvement
        improvement_mult = self.maker_price_improvement_bps / 10000
        
        if side == 'buy':
            # Bid slightly below market for maker rebate
            limit_price = market_price * (1 - improvement_mult)
        else:  # sell
            # Ask slightly above market for maker rebate
            limit_price = market_price * (1 + improvement_mult)
        
        # Create order
        order = self.order_manager.create_order(
            pair=pair,
            side=side,
            size=size,
            order_type="post",
            price=limit_price
        )
        
        start_time = time.time()
        
        try:
            # Submit to exchange
            result = key_status.rest_client.add_order(
                pair=pair,
                side=side,
                order_type="limit",
                volume=size,
                price=limit_price,
                oflags="post"  # Post-only flag
            )
            
            latency_ms = (time.time() - start_time) * 1000
            
            if 'txid' in result and result['txid']:
                exchange_order_id = result['txid'][0] if isinstance(result['txid'], list) else result['txid']
                
                self.order_manager.mark_submitted(
                    order.order_id,
                    exchange_order_id,
                    key_status.key_id
                )
                
                self.key_pool.record_success(key_status.key_id, latency_ms)
                
                logger.info(
                    f"Maker order submitted: {side} {size:.8f} {pair} @ {limit_price:.2f} | "
                    f"latency={latency_ms:.1f}ms | key={key_status.key_id}"
                )
                
                return True, "Order submitted", order
            else:
                error = result.get('error', 'Unknown error')
                self.order_manager.mark_rejected(order.order_id, str(error))
                self.key_pool.record_failure(key_status.key_id, str(error))
                return False, str(error), order
                
        except Exception as e:
            logger.error(f"Order submission failed: {e}", exc_info=True)
            self.order_manager.mark_failed(order.order_id, str(e))
            self.key_pool.record_failure(key_status.key_id, str(e))
            return False, str(e), order
    
    def _execute_taker_order(
        self,
        pair: str,
        side: str,
        size: float,
        price: float,
        key_status: KeyStatus
    ) -> Tuple[bool, str, Optional[Order]]:
        """
        Execute taker (market) order.
        Only used when edge exceeds taker fees.
        
        Args:
            pair: Trading pair
            side: 'buy' or 'sell'
            size: Order size
            price: Reference price
            key_status: API key to use
            
        Returns:
            Tuple of (success, message, order)
        """
        # Create order
        order = self.order_manager.create_order(
            pair=pair,
            side=side,
            size=size,
            order_type="market",
            price=None
        )
        
        start_time = time.time()
        
        try:
            # Submit market order
            result = key_status.rest_client.add_order(
                pair=pair,
                side=side,
                order_type="market",
                volume=size
            )
            
            latency_ms = (time.time() - start_time) * 1000
            
            if 'txid' in result and result['txid']:
                exchange_order_id = result['txid'][0] if isinstance(result['txid'], list) else result['txid']
                
                self.order_manager.mark_submitted(
                    order.order_id,
                    exchange_order_id,
                    key_status.key_id
                )
                
                # Market orders typically fill immediately
                self.order_manager.mark_filled(
                    order.order_id,
                    fill_price=price,  # Approximate
                    fill_size=size,
                    fees=size * price * 0.0026  # Approximate taker fee
                )
                
                self.key_pool.record_success(key_status.key_id, latency_ms)
                
                logger.info(
                    f"Market order executed: {side} {size:.8f} {pair} @ ~{price:.2f} | "
                    f"latency={latency_ms:.1f}ms | key={key_status.key_id}"
                )
                
                return True, "Market order filled", order
            else:
                error = result.get('error', 'Unknown error')
                self.order_manager.mark_rejected(order.order_id, str(error))
                self.key_pool.record_failure(key_status.key_id, str(error))
                return False, str(error), order
                
        except Exception as e:
            logger.error(f"Market order failed: {e}", exc_info=True)
            self.order_manager.mark_failed(order.order_id, str(e))
            self.key_pool.record_failure(key_status.key_id, str(e))
            return False, str(e), order
    
    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an active order.
        
        Args:
            order_id: Internal order ID
            
        Returns:
            True if canceled successfully
        """
        order = self.order_manager.get_order(order_id)
        
        if not order or order.status != OrderStatus.SUBMITTED:
            logger.warning(f"Cannot cancel order {order_id}: not in submitted state")
            return False
        
        if not order.exchange_order_id or order.key_id is None:
            logger.error(f"Order {order_id} missing exchange ID or key ID")
            return False
        
        # Get the key that was used
        key_status = self.key_pool.get_key_by_id(order.key_id)
        if not key_status:
            logger.error(f"Key {order.key_id} not available for cancellation")
            return False
        
        try:
            result = key_status.rest_client.cancel_order(order.exchange_order_id)
            
            self.order_manager.mark_canceled(order_id, "User canceled")
            
            logger.info(f"Order {order_id} canceled successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            return False
    
    def check_and_cancel_timeouts(self):
        """Check for and cancel timed out orders"""
        timed_out = self.order_manager.check_timeouts()
        
        for order in timed_out:
            logger.warning(f"Canceling timed out order: {order.order_id}")
            self.cancel_order(order.order_id)
