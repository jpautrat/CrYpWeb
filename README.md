# ML Kraken Pro Live Trader

**Production-grade, ML-augmented, multi-asset live trading system for Kraken BTC/USD and cryptocurrency pairs, optimized for small capital accounts ($200-$800 range).**

## ⚠️ CRITICAL WARNING

**This is a LIVE TRADING SYSTEM that places REAL ORDERS with REAL MONEY on Kraken exchange. Use at your own risk. The system is designed for institutional-grade risk management but trading cryptocurrencies involves substantial risk of loss.**

## System Overview

This system provides:

- **Live Trading Only**: No sandbox/test modes - connects directly to Kraken production API
- **ML-Augmented Strategy**: XGBoost/LightGBM models for signal generation
- **Multi-Asset Support**: Top-10 volume USD pairs with US-NC compliance filtering
- **5-Key API Pool**: Load balancing, health monitoring, and automatic failover
- **Small Capital Optimized**: Fee-aware position sizing and conservative risk management
- **Comprehensive Risk Management**: Position limits, drawdown protection, circuit breakers
- **Real-time Data Processing**: WebSocket streams for trades and order book
- **Production-Grade Infrastructure**: Logging, monitoring, audit trails, kill switches

## Architecture

```
/bot
  /core          - WebSocket, REST API, authentication, key pooling, time sync
  /data          - Parquet storage, feature engineering, data validation
  /ml            - Model training, calibration, registry, feature definitions
  /execution     - Order routing, position sizing, order management
  /strategy      - Signal generation, ML strategy, decision engine
  /compliance    - Asset filters, minimum order checks, regulatory constraints
  /ops           - Logging, alerts, health monitoring, circuit breakers
  /config        - Configuration, universe management, thresholds
  main.py        - Application entrypoint
```

## Installation

### Prerequisites

- Windows 11 (or compatible Windows version)
- Python 3.10 or higher
- 32 GB RAM recommended
- 600 Mbps+ network connection
- 5 Kraken API keys with trading permissions

### Quick Start

1. **Install dependencies:**
   ```batch
   install.bat
   ```

2. **Configure system:**
   ```batch
   configure.bat
   ```
   Edit `.env` file and add your 5 Kraken API keys:
   ```
   KRAKEN_KEY_1=your_key_here
   KRAKEN_SECRET_1=your_secret_here
   KRAKEN_KEY_2=your_key_here
   KRAKEN_SECRET_2=your_secret_here
   ... (repeat for all 5 keys)
   ```

3. **Start trading bot:**
   ```batch
   start_bot.bat
   ```

## Configuration

### Trading Parameters

Edit `.env` file to configure:

**Risk Management:**
- `PORTFOLIO_SIZE_USD=500` - Total trading capital
- `RISK_MODE=balanced` - conservative | balanced | aggressive
- `MAX_POSITION_PCT=3` - Maximum % of portfolio per trade
- `MAX_DAILY_VOLUME_PCT=15` - Maximum % traded daily
- `MAX_DAILY_DRAWDOWN_PCT=10` - Circuit breaker threshold

**Model Settings:**
- `CONFIDENCE_THRESHOLD=0.65` - Minimum confidence to trade
- `ENSEMBLE_MODELS=true` - Use XGBoost + LightGBM ensemble
- `MODEL_RETRAIN_HOURS=24` - Retraining frequency

**Universe Configuration:**
- `UNIVERSE_SIZE=10` - Number of pairs to trade
- `BASE_QUOTE=USD` - Base quote currency
- `UNIVERSE_REFRESH_MINUTES=60` - Universe refresh interval

### Risk Modes

**Conservative:**
- Max position: 1% per trade
- Daily volume: 5% of portfolio
- Confidence threshold: 70%

**Balanced (Default):**
- Max position: 3% per trade
- Daily volume: 15% of portfolio
- Confidence threshold: 65%

**Aggressive:**
- Max position: 5% per trade
- Daily volume: 25% of portfolio
- Confidence threshold: 55%

## Compliance

The system enforces US North Carolina compliance with:

- **Hardcoded Exclusion List**: 60+ restricted assets automatically filtered
- **Dynamic Universe Refresh**: Hourly updates from live Kraken API
- **Minimum Order Validation**: Enforces stricter of Kraken minimum or user-defined minimum
- **Audit Logging**: Complete order and decision trail for regulatory review

## Risk Management

### Position Limits
- Maximum 3% of portfolio per single trade (balanced mode)
- Maximum 25% portfolio concentration in any single asset
- Maximum 5 concurrent positions

### Circuit Breakers
- **Daily Drawdown**: Trading halts at 10% daily drawdown
- **Weekly Drawdown**: Trading halts at 20% weekly drawdown
- **Consecutive Losses**: 5 losses in a row triggers 1-hour cooldown
- **Spread Protection**: Halts if spread exceeds 95th percentile
- **Latency Protection**: Pauses if API response time > 500ms

### Fee Optimization
- Only trades when expected profit exceeds 3x trading fees
- Maker-biased orders (post-only) to minimize fees
- Edge buffer of 20 basis points minimum

## Emergency Controls

### Kill Switch

**Activate Kill Switch:**
1. Create file: `data/.kill_switch`
2. Or set environment variable: `KILL_SWITCH=1`
3. Or use password (if configured): API endpoint `/kill` with password

**Deactivate:**
- Remove `data/.kill_switch` file
- Or use API endpoint with password

**Emergency Stop Features:**
- Immediate halt of new orders
- Continues data collection for analysis
- Safe shutdown on critical errors

## Monitoring

### Logs

All logs stored in `data/logs/`:
- `trader_*.log` - Main application logs
- `audit/audit_YYYYMMDD.jsonl` - Regulatory audit trail

### Log Levels
- **ERROR**: Failed trades, system failures, compliance violations
- **WARN**: High latency, unusual market conditions, model degradation
- **INFO**: Successful trades, model predictions, system state changes
- **DEBUG**: Feature calculations, order details, performance metrics

### Health Monitoring

System health available via:
- Key pool status (all 5 API keys)
- WebSocket connection status
- Model performance metrics
- Risk metric tracking

## Data Storage

### Directory Structure

```
data/
  raw/              - Raw tick data (Parquet, 90-day retention)
    {pair}/
      {YYYY}/{MM}/{DD}/
        trades.parquet
        orderbook.parquet
  features/         - Computed features (Parquet)
  models/           - Trained ML models
    {pair}/
      model.pkl
      metadata.json
  logs/             - Application and audit logs
```

### Data Formats

- **Raw Data**: Parquet format with Snappy compression
- **Features**: Pre-computed feature matrices for real-time prediction
- **Models**: Pickle format with JSON metadata

## ML Pipeline

### Feature Engineering

**Price Features:**
- Mid-price returns (1s, 5s, 15s, 30s, 60s, 5m)
- Log returns and percentage returns
- Rolling z-scores (10, 30, 60 periods)

**Spread & Liquidity:**
- Bid-ask spread (absolute and percentage)
- Order book imbalance (L1-L5)
- Order book depth at various price levels

**Volume & Flow:**
- VWAP deviation z-scores
- Volume bursts vs. rolling average
- Trade aggressor direction

**Volatility:**
- Realized volatility (1m, 5m, 15m)
- Parkinson volatility estimator
- Volatility percentile ranks

**Temporal:**
- Time-of-day cyclical encodings
- Day-of-week effects
- Market session indicators

### Model Training

- **Primary Model**: XGBoost with probability calibration
- **Fallback Model**: LightGBM (if ensemble enabled)
- **Training Window**: 30-day rolling window
- **Validation**: Purged walk-forward with 24h purge, 48h embargo
- **Auto-Retraining**: Daily updates, weekly full retrain

### Prediction

- **Horizons**: 5-15s (scalping), 30-60s (momentum), 5-15m (trend)
- **Multi-class Labels**: Strong Up, Weak Up, Neutral, Weak Down, Strong Down
- **Confidence Scaling**: Position size scales with model confidence
- **Latency Target**: <100ms prediction time

## API Key Management

### 5-Key Pool Architecture

The system uses 5 separate Kraken API keys with:

- **Round-Robin Routing**: Even distribution across keys
- **Health Monitoring**: Tracks response times, failure rates, rate limits
- **Automatic Failover**: <1 second reroute on key failure
- **Load Balancing**: Optimizes for lowest response time
- **Rate Limit Awareness**: Automatic cooldown on rate limit hits

### Key Health Status

- **Healthy**: Normal operation
- **Degraded**: Recent failures, monitoring
- **Failed**: Too many consecutive failures, in cooldown
- **Cooldown**: Rate limited, waiting for reset

## Performance Optimization

### Latency Targets
- **Decision Latency**: <100ms average
- **Feature Computation**: <100ms maximum
- **API Response**: <500ms circuit breaker threshold

### Memory Management
- Explicit cleanup for large DataFrames
- Feature cache size: 512 MB (configurable)
- Data retention: 90 days raw, 1 year aggregated

### Network Optimization
- Async I/O for disk operations
- Connection pooling for API requests
- Vectorized feature computation

## Troubleshooting

### Common Issues

**"No API keys configured"**
- Ensure all 5 API keys are set in `.env` file
- Verify keys have trading permissions on Kraken

**"Failed to fetch asset pairs"**
- Check internet connection
- Verify Kraken API is accessible
- Check API key permissions

**"WebSocket connection failed"**
- Check firewall settings
- Verify network connection
- System will automatically reconnect

**"Model not found"**
- System will auto-train on startup if no model exists
- First run may take time to collect historical data
- Ensure sufficient historical data available

### Support

For issues:
1. Check logs in `data/logs/`
2. Verify configuration in `.env`
3. Review error messages in console output
4. Ensure all dependencies installed correctly

## Security

- **API Keys**: Stored only in `.env` file (never in code)
- **Network**: HTTPS only, certificate validation
- **Audit Logging**: Immutable logs for compliance
- **Kill Switch**: Multiple activation methods for safety

## Legal & Disclaimer

This software is provided "as-is" without warranty. Cryptocurrency trading involves substantial risk. The system is designed for experienced traders who understand the risks. Always:

- Test thoroughly with small amounts first
- Monitor the system continuously
- Understand all risk parameters
- Keep emergency stop procedures ready
- Never invest more than you can afford to lose

**The developers assume no liability for trading losses.**

## License

Proprietary software. All rights reserved.

## Version

v1.0.0 - Production Release

---

**Built for small capital accounts with institutional-grade risk management.**
