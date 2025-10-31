"""Main entrypoint for ML Kraken Live Trader."""
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from loguru import logger

# Add bot to path
sys.path.insert(0, str(Path(__file__).parent))

from bot.config.settings import settings
from bot.core.key_pool import KeyPool
from bot.core.websocket_manager import KrakenWebSocketManager
from bot.core.rest_client import KrakenRESTClient
from bot.core.time_sync import TimeSync
from bot.data.market_data import MarketDataManager
from bot.data.feature_engineer import FeatureEngineer
from bot.data.storage_manager import StorageManager
from bot.ml.model_registry import ModelRegistry
from bot.ml.model_trainer import ModelTrainer
from bot.execution.order_manager import OrderManager
from bot.execution.position_sizer import PositionSizer
from bot.execution.risk_manager import RiskManager
from bot.strategy.ml_strategy import MLStrategy
from bot.compliance.asset_filter import AssetFilter
from bot.compliance.compliance_checker import ComplianceChecker
from bot.compliance.audit_logger import AuditLogger
from bot.config.universe_manager import UniverseManager
from bot.ops.kill_switch import KillSwitch


def setup_logging():
    """Configure logging."""
    log_dir = settings.system.logs_dir
    log_dir.mkdir(parents=True, exist_ok=True)
    
    logger.add(
        log_dir / "trader_{time}.log",
        rotation="100 MB",
        retention="30 days",
        level=settings.system.log_level,
    )


def main():
    """Main trading loop."""
    # Setup
    setup_logging()
    logger.info("=" * 60)
    logger.info("ML Kraken Pro Live Trader - Starting")
    logger.info("=" * 60)
    
    # Validate configuration
    errors = settings.validate()
    for error in errors:
        logger.error(error)
    
    if not settings.trading.live_trading:
        logger.warning("LIVE_TRADING is disabled - orders will not be placed")
    
    # Initialize components
    logger.info("Initializing components...")
    
    # Core infrastructure
    time_sync = TimeSync()
    time_sync.sync()
    
    key_pool = KeyPool()
    rest_client, _ = key_pool.get_key()
    
    ws_manager = KrakenWebSocketManager()
    
    # Data pipeline
    market_data = MarketDataManager(settings.performance.feature_lookback_seconds)
    feature_engineer = FeatureEngineer(settings.performance.feature_lookback_seconds)
    storage_manager = StorageManager()
    
    # ML pipeline
    model_registry = ModelRegistry()
    model_trainer = ModelTrainer(model_registry)
    
    # Execution
    order_manager = OrderManager(key_pool)
    position_sizer = PositionSizer()
    risk_manager = RiskManager()
    
    # Strategy
    ml_strategy = MLStrategy(model_registry, feature_engineer)
    
    # Compliance
    asset_filter = AssetFilter()
    compliance_checker = ComplianceChecker(asset_filter)
    audit_logger = AuditLogger()
    
    # Universe management
    universe_manager = UniverseManager(rest_client, asset_filter)
    
    # Operations
    kill_switch = KillSwitch()
    
    # Start WebSocket
    logger.info("Starting WebSocket connections...")
    ws_manager.start()
    time.sleep(2)  # Allow connection to establish
    
    # Get trading universe
    logger.info("Loading trading universe...")
    universe = universe_manager.get_universe(force_refresh=True)
    logger.info(f"Universe: {universe}")
    
    # Subscribe to market data
    for pair in universe:
        ws_manager.subscribe(pair, ["trades", "book"], 
                           lambda p, d, t: market_data.add_trade(p, d.get('price', 0), 
                                                                  d.get('volume', 0), 
                                                                  'buy', t))
    
    logger.info("Trading system initialized. Starting main loop...")
    
    # Main trading loop
    try:
        while True:
            # Check kill switch
            if kill_switch.is_active():
                logger.warning("Kill switch active - trading halted")
                time.sleep(10)
                continue
            
            # Process each pair in universe
            for pair in universe:
                try:
                    # Get market data
                    trades_df = market_data.get_trades_dataframe(pair)
                    if trades_df.empty:
                        continue
                    
                    # Compute features
                    features = feature_engineer.compute_features(
                        pair, trades_df, market_data.get_orderbook(pair)
                    )
                    
                    if features.empty:
                        continue
                    
                    # Generate signal
                    current_price = market_data.get_latest_price(pair)
                    if not current_price:
                        continue
                    
                    signal = ml_strategy.generate_signal(pair, features, current_price)
                    
                    if signal['side'] == 'hold':
                        continue
                    
                    # Check compliance
                    is_compliant, error = compliance_checker.check_order(
                        pair, 0, "limit"  # Size will be calculated
                    )
                    if not is_compliant:
                        logger.warning(f"Compliance check failed for {pair}: {error}")
                        continue
                    
                    # Calculate position size
                    size_usd = position_sizer.calculate_size(
                        pair, signal['confidence'], signal.get('expected_return', 0),
                        0.02, current_price  # Approximate volatility
                    )
                    
                    if size_usd == 0:
                        continue
                    
                    # Check risk limits
                    can_trade, risk_error = risk_manager.can_trade(pair, size_usd)
                    if not can_trade:
                        logger.warning(f"Risk check failed: {risk_error}")
                        continue
                    
                    # Submit order
                    volume = size_usd / current_price
                    limit_price = current_price * (1.0001 if signal['side'] == 'buy' else 0.9999)
                    
                    order_result = order_manager.submit_order(
                        pair, signal['side'], volume, limit_price, post_only=True
                    )
                    
                    if order_result.get('status') == 'pending':
                        risk_manager.record_trade(pair, size_usd)
                        audit_logger.log_order({
                            'pair': pair,
                            'side': signal['side'],
                            'size_usd': size_usd,
                            'price': limit_price,
                            'signal': signal,
                        })
                
                except Exception as e:
                    logger.error(f"Error processing {pair}: {e}", exc_info=True)
            
            # Sleep between iterations
            time.sleep(1)
    
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        ws_manager.stop()
        logger.info("Trading system stopped")


if __name__ == "__main__":
    main()
