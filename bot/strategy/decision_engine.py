"""
Decision Engine - Final trade decision and execution orchestration
"""

from typing import Dict, Optional
from loguru import logger

from .signal_generator import SignalGenerator
from ..execution.position_sizer import PositionSizer
from ..execution.risk_manager import RiskManager
from ..execution.execution_router import ExecutionRouter
from ..compliance.audit_logger import AuditLogger


class DecisionEngine:
    """
    Makes final trading decisions and orchestrates execution.
    Integrates signals, risk management, position sizing, and execution.
    """
    
    def __init__(
        self,
        signal_generator: SignalGenerator,
        position_sizer: PositionSizer,
        risk_manager: RiskManager,
        execution_router: ExecutionRouter,
        audit_logger: AuditLogger
    ):
        """
        Initialize decision engine.
        
        Args:
            signal_generator: Signal generation system
            position_sizer: Position sizing calculator
            risk_manager: Risk management system
            execution_router: Order execution router
            audit_logger: Audit logging system
        """
        self.signal_generator = signal_generator
        self.position_sizer = position_sizer
        self.risk_manager = risk_manager
        self.execution_router = execution_router
        self.audit_logger = audit_logger
        
        self.decisions_made = 0
        self.trades_executed = 0
        
        logger.info("DecisionEngine initialized")
    
    def process_pair(self, pair: str, current_price: float, min_order_size: float) -> Optional[Dict]:
        """
        Process a trading pair and execute if signal is strong.
        
        Args:
            pair: Trading pair
            current_price: Current market price
            min_order_size: Minimum order size for pair
            
        Returns:
            Execution result dictionary or None
        """
        self.decisions_made += 1
        
        # Generate signal
        signal = self.signal_generator.generate_signal(pair)
        
        # Log decision
        self.audit_logger.log_trade_decision(
            pair=pair,
            signal=signal['side'],
            confidence=signal['confidence'],
            expected_return=signal['expected_return'],
            reason=signal['reason']
        )
        
        # Check if signal is actionable
        if signal['side'] == 'hold':
            logger.debug(f"No trade signal for {pair}: {signal['reason']}")
            return None
        
        # Check risk constraints
        size_usd = self.position_sizer.portfolio_size_usd * (signal['size'] / 100)
        
        risk_allowed, risk_reason = self.risk_manager.check_trade_allowed(
            pair=pair,
            size_usd=size_usd,
            side=signal['side']
        )
        
        if not risk_allowed:
            logger.warning(f"Trade blocked by risk manager: {risk_reason}")
            self.audit_logger.log_compliance_check(
                pair=pair,
                check_type='risk_management',
                passed=False,
                reason=risk_reason
            )
            return None
        
        # Calculate position size
        position_params = self.position_sizer.calculate_position_size(
            pair=pair,
            confidence=signal['confidence'],
            price=current_price,
            min_order_size=min_order_size,
            available_balance=self.position_sizer.portfolio_size_usd,  # Simplified
            risk_multiplier=signal['size']
        )
        
        if not position_params:
            logger.info(f"Position size calculation rejected trade for {pair}")
            return None
        
        # Execute order
        success, message, order = self.execution_router.execute_order(
            pair=pair,
            side=signal['side'],
            size=position_params['volume'],
            price=current_price,
            strategy="maker"
        )
        
        if success:
            self.trades_executed += 1
            
            # Record trade with position sizer
            self.position_sizer.record_trade(
                pair=pair,
                size_usd=position_params['size_usd'],
                side=signal['side']
            )
            
            # Log order submission
            if order:
                self.audit_logger.log_order_submitted(
                    order_id=order.order_id,
                    pair=pair,
                    side=signal['side'],
                    order_type=order.order_type,
                    size=position_params['volume'],
                    price=signal['limit_price'],
                    key_id=order.key_id or 0
                )
            
            logger.info(
                f"Trade executed: {signal['side']} {position_params['volume']:.8f} {pair} | "
                f"confidence={signal['confidence']:.3f}"
            )
            
            return {
                'pair': pair,
                'signal': signal,
                'position_params': position_params,
                'order': order,
                'success': True
            }
        else:
            logger.warning(f"Order execution failed: {message}")
            
            if order:
                self.audit_logger.log_order_rejected(
                    order_id=order.order_id,
                    pair=pair,
                    side=signal['side'],
                    size=position_params['volume'],
                    reason=message
                )
            
            return None
    
    def get_statistics(self) -> Dict:
        """Get decision engine statistics"""
        return {
            'decisions_made': self.decisions_made,
            'trades_executed': self.trades_executed,
            'execution_rate': self.trades_executed / self.decisions_made if self.decisions_made > 0 else 0,
            'signal_stats': self.signal_generator.get_statistics(),
            'risk_status': self.risk_manager.get_risk_status(),
            'capacity': self.position_sizer.get_available_capacity()
        }
