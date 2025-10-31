"""
Main application entry point for Kraken Live Trading System.
Orchestrates all components for live trading.
"""
import asyncio
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from loguru import logger
import sys

# Load environment variables from .env file
try:
    from load_env import load_env_file
    load_env_file(".env")
except ImportError:
    # If load_env not available, try python-dotenv
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass  # Environment variables must be set manually

# Configure logging
logger.add(
    "logs/trading_{time:YYYY-MM-DD}.log",
    rotation="00:00",
    retention="90 days",
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
)

from config.settings import Settings
from config.universe_manager import UniverseManager
from config.thresholds import ThresholdManager

from core.key_pool import KeyPool
from core.rest_client import KrakenRESTClient
from core.websocket_manager import KrakenWebSocketManager
from core.time_sync import TimeSync

from data.storage_manager import StorageManager
from data.feature_engineer import FeatureEngineer
from data.data_validator import DataValidator
from data.market_data import MarketDataManager

from ml.model_registry import ModelRegistry
from ml.model_trainer import ModelTrainer

from execution.order_manager import OrderManager
from execution.position_sizer import PositionSizer
from execution.execution_router import ExecutionRouter
from execution.risk_manager import RiskManager

from strategy.ml_strategy import MLStrategy
from strategy.signal_generator import SignalGenerator
from strategy.decision_engine import DecisionEngine

from compliance.asset_filter import AssetFilter
from compliance.compliance_checker import ComplianceChecker
from compliance.audit_logger import AuditLogger

from ops.health_monitor import HealthMonitor
from ops.circuit_breaker import CircuitBreaker
from ops.kill_switch import KillSwitch
from ops.alert_manager import AlertManager, AlertLevel


class TradingBot:
    """Main trading bot orchestrator"""
    
    def __init__(self):
        logger.info("Initializing Kraken Live Trading System...")
        
        # Load configuration
        self.settings = Settings()
        
        if not self.settings.trading.live_trading:
            logger.error("System must run in live mode. Exiting.")
            sys.exit(1)
        
        # Initialize components
        self._initialize_components()
        
        logger.info("Trading bot initialized successfully")
    
    def _initialize_components(self):
        """Initialize all system components"""
        # Core infrastructure
        self.time_sync = TimeSync()
        self.time_sync.sync()
        
        self.key_pool = KeyPool(self.settings.api)
        self.rest_client = KrakenRESTClient(self.key_pool, self.time_sync)
        self.websocket = KrakenWebSocketManager(self.settings.api.websocket_url)
        
        # Configuration
        self.universe_manager = UniverseManager(self.settings, self.rest_client)
        self.thresholds = ThresholdManager(self.settings.trading.risk_mode)
        
        # Data infrastructure
        self.storage = StorageManager(self.settings.data_dir, self.settings.system.data_retention_days)
        self.validator = DataValidator(tolerance_pct=5.0)
        self.feature_engineer = FeatureEngineer()
        self.market_data = MarketDataManager(self.storage, self.validator)
        
        # ML infrastructure
        self.model_registry = ModelRegistry(self.settings.models_dir)
        self.model_trainer = ModelTrainer(self.storage, self.feature_engineer)
        
        # Execution infrastructure
        self.order_manager = OrderManager(self.rest_client, self.settings.system)
        self.position_sizer = PositionSizer(self.settings.trading)
        self.risk_manager = RiskManager(self.settings.trading)
        self.execution_router = ExecutionRouter(self.key_pool, self.order_manager)
        
        # Strategy
        ml_strategy = MLStrategy(
            self.model_registry,
            self.settings.ml,
            self.settings.trading,
            self.thresholds
        )
        self.signal_generator = SignalGenerator([ml_strategy])
        self.decision_engine = DecisionEngine(
            self.signal_generator,
            self.position_sizer,
            self.risk_manager,
            self.universe_manager,
            self.rest_client
        )
        
        # Compliance
        asset_filter = AssetFilter(self.settings.universe)
        self.compliance_checker = ComplianceChecker(asset_filter, self.universe_manager)
        self.audit_logger = AuditLogger(self.settings.logs_dir)
        
        # Operations
        self.health_monitor = HealthMonitor()
        self.circuit_breaker = CircuitBreaker()
        self.kill_switch = KillSwitch(
            password=self.settings.system.kill_switch_password,
            config_file=Path("kill_switch.flag")
        )
        self.alert_manager = AlertManager()
        
        # Setup WebSocket callbacks
        self._setup_websocket_callbacks()
        
        # Initialize universe
        logger.info("Refreshing trading universe...")
        self.universe = self.universe_manager.refresh_universe()
        
        # Train/load models for universe pairs
        self._initialize_models()
        
        logger.info(f"Trading universe: {len(self.universe)} pairs")
        logger.info(f"Pairs: {', '.join(self.universe)}")
    
    def _setup_websocket_callbacks(self):
        """Setup WebSocket event handlers"""
        def on_trade(trade_data):
            pair = self._extract_pair_from_channel(trade_data.get('channel_id', 0))
            if pair:
                self.market_data.add_trade(pair, trade_data)
        
        def on_book(book_data):
            pair = self._extract_pair_from_channel(book_data.get('channel_id', 0))
            if pair:
                self.market_data.add_orderbook(pair, book_data)
        
        def on_heartbeat():
            if not self.websocket.check_heartbeat():
                self.alert_manager.send_alert(
                    AlertLevel.WARNING,
                    "WebSocket heartbeat timeout"
                )
        
        self.websocket.register_callback('trade', on_trade)
        self.websocket.register_callback('book', on_book)
        self.websocket.register_callback('heartbeat', on_heartbeat)
    
    def _extract_pair_from_channel(self, channel_id: int) -> str:
        """Extract pair from channel ID (simplified - would need actual mapping)"""
        # This is a placeholder - in real implementation, would track channel->pair mapping
        return ""
    
    def _initialize_models(self):
        """Initialize ML models for all universe pairs"""
        logger.info("Initializing ML models...")
        
        for pair in self.universe:
            # Try to load existing model
            model = self.model_registry.load_model(pair, "xgboost", "latest")
            
            if not model:
                logger.info(f"No model found for {pair}, training new model...")
                try:
                    result = self.model_trainer.train_pair_model(
                        pair,
                        target_horizon="medium",
                        model_type="xgboost",
                        use_ensemble=self.settings.ml.ensemble_models
                    )
                    
                    if result and 'models' in result:
                        # Save models
                        for model_type, trained_model in result['models'].items():
                            self.model_registry.save_model(
                                pair,
                                trained_model,
                                model_type,
                                version="latest",
                                metadata=result.get('metrics', {}).get(model_type)
                            )
                        logger.info(f"Trained and saved model for {pair}")
                except Exception as e:
                    logger.error(f"Failed to train model for {pair}: {e}")
                    self.alert_manager.send_alert(
                        AlertLevel.WARNING,
                        f"Failed to train model for {pair}",
                        {'error': str(e)}
                    )
    
    def start(self):
        """Start the trading bot"""
        logger.info("Starting trading bot...")
        
        # Check kill switch
        if self.kill_switch.check():
            logger.critical("Kill switch is ACTIVE. System cannot start.")
            self.alert_manager.send_alert(
                AlertLevel.CRITICAL,
                "Kill switch active - system startup blocked"
            )
            return
        
        # Start WebSocket
        self.websocket.start()
        time.sleep(2)  # Wait for connection
        
        # Subscribe to market data
        for pair in self.universe:
            self.websocket.subscribe_trades(pair)
            self.websocket.subscribe_book(pair)
            time.sleep(0.1)  # Rate limit
        
        logger.info("WebSocket subscriptions active")
        
        # Start monitoring threads
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.trading_thread = threading.Thread(target=self._trading_loop, daemon=True)
        
        self.monitor_thread.start()
        self.trading_thread.start()
        
        logger.info("Trading bot started successfully")
        
        # Main loop
        try:
            while self.running:
                time.sleep(1)
                
                # Check kill switch
                if self.kill_switch.check():
                    logger.critical("Kill switch activated. Stopping trading.")
                    self.stop()
                    break
                
                # Health check
                health = self.health_monitor.get_health_status()
                if not health['overall']:
                    self.alert_manager.send_alert(
                        AlertLevel.WARNING,
                        "System health degraded",
                        health
                    )
        
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
            self.stop()
    
    def _monitor_loop(self):
        """Background monitoring loop"""
        while self.running:
            try:
                # Monitor pending orders
                self.order_manager.monitor_pending_orders()
                
                # Check circuit breakers
                # (would check market conditions here)
                
                # Update health metrics
                # (would record various metrics here)
                
                # Flush data periodically
                if datetime.now().second % 60 == 0:
                    self.market_data.flush_all()
                
                time.sleep(5)
            
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
                time.sleep(5)
    
    def _trading_loop(self):
        """Main trading decision loop"""
        while self.running:
            try:
                # Check kill switch
                if self.kill_switch.check():
                    time.sleep(10)
                    continue
                
                # Check circuit breaker
                if self.circuit_breaker.is_active():
                    time.sleep(10)
                    continue
                
                # Process each pair in universe
                for pair in self.universe:
                    try:
                        # Get recent market data
                        trades = self.market_data.get_recent_trades(pair, seconds=300)
                        orderbook = self.market_data.get_recent_orderbook(pair, seconds=60)
                        
                        if trades.empty:
                            continue
                        
                        # Compute features
                        features = self.feature_engineer.compute_all_features(
                            trades,
                            orderbook if not orderbook.empty else None,
                            pair,
                            datetime.now()
                        )
                        
                        if features.empty:
                            continue
                        
                        # Get market data snapshot
                        current_price = trades['price'].iloc[-1]
                        spread_bps = 0.0
                        if not orderbook.empty and 'spread_bps' in orderbook.columns:
                            spread_bps = orderbook['spread_bps'].iloc[-1]
                        
                        market_data = {
                            'price': current_price,
                            'spread_bps': spread_bps
                        }
                        
                        # Make trading decision
                        decision_start = time.time()
                        order = self.decision_engine.process_signal(
                            features,
                            pair,
                            datetime.now(),
                            market_data
                        )
                        decision_latency = (time.time() - decision_start) * 1000
                        self.health_monitor.record_metric('decision_latency', decision_latency)
                        
                        if order:
                            # Compliance check
                            is_compliant, compliance_error = self.compliance_checker.check_order(
                                pair,
                                order
                            )
                            
                            if not is_compliant:
                                logger.warning(f"Compliance check failed for {pair}: {compliance_error}")
                                self.audit_logger.log_compliance_check(pair, False, compliance_error)
                                continue
                            
                            # Submit order
                            result = self.execution_router.submit_order(
                                pair=order['pair'],
                                side=order['side'],
                                size=order['size'],
                                price=order['price'],
                                order_type=order['order_type'],
                                post_only=order.get('post_only', True)
                            )
                            
                            if result.get('success'):
                                logger.info(f"Order submitted: {order['side']} {order['size']} {pair}")
                                self.audit_logger.log_order(
                                    result['order_id'],
                                    order,
                                    result
                                )
                            else:
                                logger.error(f"Order submission failed for {pair}: {result.get('error')}")
                        
                        time.sleep(1)  # Rate limit between pairs
                    
                    except Exception as e:
                        logger.error(f"Error processing {pair}: {e}")
                        continue
                
                # Wait before next iteration
                time.sleep(10)  # Check every 10 seconds
            
            except Exception as e:
                logger.error(f"Error in trading loop: {e}")
                time.sleep(10)
    
    def stop(self):
        """Stop the trading bot"""
        logger.info("Stopping trading bot...")
        
        self.running = False
        
        # Cancel all pending orders
        self.order_manager.cancel_all_orders()
        
        # Close WebSocket
        self.websocket.stop()
        
        # Flush data
        self.market_data.flush_all()
        
        logger.info("Trading bot stopped")


def main():
    """Main entry point"""
    try:
        bot = TradingBot()
        bot.start()
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
