"""
ML Kraken Pro Live Trader - Main Application Entry Point
Production-grade, ML-augmented cryptocurrency trading system.

This is the LIVE TRADING system - it places REAL ORDERS with REAL MONEY.
"""

import sys
import time
import signal
from pathlib import Path
from datetime import datetime, timedelta
from loguru import logger

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from bot.config import get_settings
from bot.core import (
    AuthManager, KrakenRestClient, KrakenWebSocketManager,
    KeyPool, TimeSync
)
from bot.data import (
    StorageManager, MarketDataManager,
    DataValidator, FeatureEngineer
)
from bot.ml import ModelRegistry, ModelCalibrator, ModelTrainer
from bot.execution import (
    PositionSizer, RiskManager,
    OrderManager, ExecutionRouter
)
from bot.strategy import MLStrategy, SignalGenerator, DecisionEngine
from bot.compliance import AssetFilter, ComplianceChecker, AuditLogger
from bot.config import UniverseManager, ThresholdManager
from bot.ops import HealthMonitor, AlertManager, CircuitBreaker, KillSwitch, AlertLevel


class MLKrakenProTrader:
    """
    Main trading application orchestrator.
    Coordinates all system components for live trading.
    """
    
    def __init__(self):
        """Initialize the trading system"""
        logger.info("=" * 80)
        logger.info("ML KRAKEN PRO LIVE TRADER - STARTING")
        logger.info("=" * 80)
        logger.info("⚠️  WARNING: This is a LIVE TRADING system")
        logger.info("⚠️  Real orders will be placed with real money")
        logger.info("=" * 80)
        
        # Load configuration
        self.settings = get_settings()
        logger.info(f"Configuration loaded: {self.settings.risk_mode.value} mode")
        
        # Initialize components
        self._init_core()
        self._init_data()
        self._init_ml()
        self._init_execution()
        self._init_strategy()
        self._init_compliance()
        self._init_ops()
        
        self.is_running = False
        
        logger.info("System initialization complete")
    
    def _init_core(self):
        """Initialize core API infrastructure"""
        logger.info("Initializing core API infrastructure...")
        
        # Time synchronization
        self.time_sync = TimeSync()
        
        # Initialize API key pool
        self.key_pool = KeyPool(
            api_keys=self.settings.api_keys,
            rate_limit_cooldown=self.settings.rate_limit_cooldown_seconds,
            max_consecutive_failures=3
        )
        
        # Get primary REST client for system operations
        primary_key = self.key_pool.get_next_key()
        self.rest_client = primary_key.rest_client if primary_key else None
        
        if not self.rest_client:
            raise Exception("Failed to initialize REST client")
        
        # WebSocket manager
        self.ws_manager = KrakenWebSocketManager(
            heartbeat_timeout=self.settings.websocket_heartbeat_timeout
        )
        
        logger.info("Core API infrastructure initialized")
    
    def _init_data(self):
        """Initialize data management"""
        logger.info("Initializing data management...")
        
        self.storage = StorageManager()
        self.market_data = MarketDataManager(self.storage)
        self.data_validator = DataValidator()
        self.feature_engineer = FeatureEngineer(
            market_data=self.market_data,
            enable_cross_asset=self.settings.enable_cross_asset_features,
            enable_temporal=self.settings.enable_temporal_features,
            enable_volatility=self.settings.enable_volatility_regimes
        )
        
        logger.info("Data management initialized")
    
    def _init_ml(self):
        """Initialize ML pipeline"""
        logger.info("Initializing ML pipeline...")
        
        self.model_registry = ModelRegistry()
        self.model_calibrator = ModelCalibrator()
        self.model_trainer = ModelTrainer(
            storage_manager=self.storage,
            feature_engineer=self.feature_engineer
        )
        
        logger.info("ML pipeline initialized")
    
    def _init_execution(self):
        """Initialize execution engine"""
        logger.info("Initializing execution engine...")
        
        risk_params = self.settings.risk_parameters
        
        self.position_sizer = PositionSizer(
            portfolio_size_usd=self.settings.portfolio_size_usd,
            max_position_pct=risk_params['max_position_pct'],
            max_daily_volume_pct=risk_params['max_daily_volume_pct'],
            max_concurrent_positions=risk_params['max_concurrent_positions']
        )
        
        self.risk_manager = RiskManager(
            portfolio_size_usd=self.settings.portfolio_size_usd,
            max_daily_drawdown_pct=self.settings.max_daily_drawdown_pct,
            max_weekly_drawdown_pct=self.settings.max_weekly_drawdown_pct,
            max_consecutive_losses=self.settings.max_consecutive_losses
        )
        
        self.order_manager = OrderManager(
            order_timeout_seconds=self.settings.order_timeout_seconds
        )
        
        logger.info("Execution engine initialized")
    
    def _init_strategy(self):
        """Initialize trading strategy"""
        logger.info("Initializing trading strategy...")
        
        self.threshold_manager = ThresholdManager(
            base_confidence=self.settings.confidence_threshold
        )
        
        self.ml_strategy = MLStrategy(
            model_registry=self.model_registry,
            model_calibrator=self.model_calibrator,
            model_trainer=self.model_trainer,
            feature_engineer=self.feature_engineer,
            market_data=self.market_data,
            threshold_manager=self.threshold_manager,
            edge_buffer_bps=self.settings.edge_buffer_bps,
            fee_multiplier=self.settings.fee_multiplier
        )
        
        self.signal_generator = SignalGenerator(
            strategy=self.ml_strategy,
            feature_engineer=self.feature_engineer,
            max_decision_latency_ms=self.settings.max_decision_latency_ms
        )
        
        logger.info("Trading strategy initialized")
    
    def _init_compliance(self):
        """Initialize compliance systems"""
        logger.info("Initializing compliance systems...")
        
        self.asset_filter = AssetFilter()
        self.compliance_checker = ComplianceChecker(self.asset_filter)
        self.audit_logger = AuditLogger()
        
        self.universe_manager = UniverseManager(
            rest_client=self.rest_client,
            asset_filter=self.asset_filter,
            base_quote=self.settings.base_quote,
            universe_size=self.settings.universe_size,
            min_daily_volume_usd=self.settings.min_daily_volume_usd,
            refresh_minutes=self.settings.universe_refresh_minutes
        )
        
        # Initialize execution router after compliance
        self.execution_router = ExecutionRouter(
            key_pool=self.key_pool,
            order_manager=self.order_manager,
            compliance_checker=self.compliance_checker,
            maker_price_improvement_bps=self.settings.maker_order_price_improvement_bps
        )
        
        # Initialize decision engine
        self.decision_engine = DecisionEngine(
            signal_generator=self.signal_generator,
            position_sizer=self.position_sizer,
            risk_manager=self.risk_manager,
            execution_router=self.execution_router,
            audit_logger=self.audit_logger
        )
        
        logger.info("Compliance systems initialized")
    
    def _init_ops(self):
        """Initialize operations infrastructure"""
        logger.info("Initializing operations infrastructure...")
        
        self.health_monitor = HealthMonitor()
        self.alert_manager = AlertManager()
        self.circuit_breaker = CircuitBreaker(
            spread_percentile_threshold=self.settings.spread_percentile_threshold,
            max_latency_ms=self.settings.max_api_latency_ms
        )
        self.kill_switch = KillSwitch(
            password=self.settings.kill_switch_password
        )
        
        logger.info("Operations infrastructure initialized")
    
    def start(self):
        """Start the trading system"""
        logger.info("=" * 80)
        logger.info("STARTING LIVE TRADING SYSTEM")
        logger.info("=" * 80)
        
        # Final safety check
        if not self.kill_switch.check():
            logger.critical("KILL SWITCH IS ACTIVE - Cannot start trading")
            return
        
        # Connect WebSocket
        logger.info("Connecting to Kraken WebSocket...")
        self.ws_manager.connect()
        
        # Refresh trading universe
        logger.info("Refreshing trading universe...")
        universe = self.universe_manager.refresh_universe()
        logger.info(f"Trading universe: {len(universe)} pairs")
        
        # Subscribe to market data
        if universe:
            logger.info("Subscribing to market data...")
            self.ws_manager.subscribe('trade', universe, self._handle_trade)
            self.ws_manager.subscribe('spread', universe, self._handle_spread)
        
        # Start main trading loop
        self.is_running = True
        logger.info("🚀 Trading system is LIVE")
        logger.info("=" * 80)
        
        try:
            self._trading_loop()
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
            self.stop()
        except Exception as e:
            logger.critical(f"Fatal error in trading loop: {e}", exc_info=True)
            self.stop()
    
    def _trading_loop(self):
        """Main trading loop"""
        last_universe_refresh = datetime.now()
        last_timeout_check = datetime.now()
        last_health_check = datetime.now()
        
        iteration = 0
        
        while self.is_running:
            iteration += 1
            
            try:
                # Check kill switch
                if not self.kill_switch.check():
                    logger.critical("Kill switch activated - halting trading")
                    self.stop()
                    break
                
                # Check circuit breakers
                if not self.circuit_breaker.check_and_reset():
                    time.sleep(10)
                    continue
                
                # Periodic universe refresh
                if datetime.now() - last_universe_refresh > timedelta(minutes=self.settings.universe_refresh_minutes):
                    universe = self.universe_manager.get_universe(force_refresh=True)
                    last_universe_refresh = datetime.now()
                
                # Check order timeouts
                if datetime.now() - last_timeout_check > timedelta(seconds=10):
                    self.execution_router.check_and_cancel_timeouts()
                    last_timeout_check = datetime.now()
                
                # Health check
                if datetime.now() - last_health_check > timedelta(minutes=5):
                    health = self.health_monitor.check_system_health()
                    if not health['is_healthy']:
                        self.alert_manager.alert(
                            AlertLevel.WARNING,
                            "health_monitor",
                            "System health degraded",
                            health
                        )
                    last_health_check = datetime.now()
                
                # Process each pair in universe
                universe = self.universe_manager.get_universe()
                
                for pair in universe:
                    if not self.is_running:
                        break
                    
                    pair_info = self.universe_manager.get_pair_info(pair)
                    if not pair_info:
                        continue
                    
                    # Process trading decision
                    self.decision_engine.process_pair(
                        pair=pair,
                        current_price=pair_info['last_price'],
                        min_order_size=pair_info['ordermin']
                    )
                
                # Sleep briefly
                time.sleep(1)
                
                # Periodic logging
                if iteration % 60 == 0:
                    stats = self.decision_engine.get_statistics()
                    logger.info(
                        f"Stats: {stats['trades_executed']} trades, "
                        f"Risk: Daily PnL=${stats['risk_status']['daily_pnl']:.2f}"
                    )
                
            except Exception as e:
                logger.error(f"Error in trading loop iteration: {e}", exc_info=True)
                time.sleep(5)
    
    def _handle_trade(self, pair, data, channel):
        """Handle trade data from WebSocket"""
        try:
            for trade in data:
                price = float(trade[0])
                volume = float(trade[1])
                timestamp = datetime.fromtimestamp(float(trade[2]))
                side = 'buy' if trade[3] == 'b' else 'sell'
                
                self.market_data.add_tick(pair, timestamp, price, volume, side)
        except Exception as e:
            logger.error(f"Error handling trade data: {e}")
    
    def _handle_spread(self, pair, data, channel):
        """Handle spread data from WebSocket"""
        try:
            if isinstance(data, list) and len(data) >= 3:
                bid_price = float(data[0])
                ask_price = float(data[1])
                timestamp = datetime.fromtimestamp(float(data[2]))
                
                self.market_data.add_orderbook_snapshot(
                    pair, timestamp,
                    [(bid_price, 1.0)],
                    [(ask_price, 1.0)]
                )
        except Exception as e:
            logger.error(f"Error handling spread data: {e}")
    
    def stop(self):
        """Stop the trading system"""
        logger.info("=" * 80)
        logger.info("STOPPING TRADING SYSTEM")
        logger.info("=" * 80)
        
        self.is_running = False
        
        # Disconnect WebSocket
        if self.ws_manager:
            self.ws_manager.disconnect()
        
        # Persist data
        if self.market_data:
            self.market_data.persist_buffers()
        
        # Log final statistics
        if self.decision_engine:
            stats = self.decision_engine.get_statistics()
            logger.info(f"Final Statistics: {stats}")
        
        logger.info("System stopped")


def setup_logging():
    """Configure logging"""
    settings = get_settings()
    
    # Remove default logger
    logger.remove()
    
    # Console logging
    logger.add(
        sys.stderr,
        level=settings.log_level.value,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )
    
    # File logging
    log_dir = Path("data/logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    logger.add(
        log_dir / "trader_{time:YYYY-MM-DD}.log",
        level="DEBUG",
        rotation="1 day",
        retention=f"{settings.log_retention_days} days",
        compression="zip"
    )


def main():
    """Main entry point"""
    setup_logging()
    
    logger.info("ML Kraken Pro Live Trader v1.0.0")
    logger.info(f"Python {sys.version}")
    logger.info(f"Started at {datetime.now().isoformat()}")
    
    try:
        # Initialize and start trader
        trader = MLKrakenProTrader()
        
        # Setup signal handlers
        def signal_handler(sig, frame):
            logger.info(f"Received signal {sig}")
            trader.stop()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Start trading
        trader.start()
        
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
