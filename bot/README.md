# Kraken Live Trading System - ML-Augmented Multi-Asset Trading Bot

## Overview

This is a production-grade, ML-augmented, multi-asset live trading system for Kraken cryptocurrency exchange, specifically optimized for small capital accounts ($200-$800). The system is designed for US North Carolina compliance and implements institutional-grade risk management, machine learning strategies, and comprehensive monitoring.

## ⚠️ CRITICAL WARNINGS

**THIS SYSTEM TRADES WITH REAL MONEY ON KRAKEN PRODUCTION EXCHANGE**

- **NO SANDBOX/SIMULATION MODE**: This system ONLY trades on live markets
- **REAL FUNDS AT RISK**: All trades use actual capital from your Kraken account
- **START WITH MINIMUM CAPITAL**: Begin with the smallest portfolio size ($200) to test
- **MONITOR CLOSELY**: Watch the system closely during initial trading
- **USE KILL SWITCH**: Always know how to activate the emergency kill switch
- **COMPLIANCE**: System is configured for US-NC compliance - verify your jurisdiction

## Features

### Core Capabilities

- **Live Trading Only**: No simulation mode - all trades are real
- **Multi-Asset Support**: Automatically trades top 10 USD pairs by volume
- **US-NC Compliant**: Hard-coded exclusion list for restricted assets
- **5 API Key Pooling**: Round-robin routing with health monitoring and failover
- **Real-Time Data**: WebSocket streams for trades and order book updates
- **ML-Powered**: XGBoost and LightGBM models with ensemble predictions
- **Risk Management**: Comprehensive risk limits and circuit breakers
- **Small Capital Optimized**: Designed for $200-$800 accounts with fee optimization

### Machine Learning

- **Multi-Model System**: XGBoost (primary), LightGBM (ensemble/backup)
- **Comprehensive Features**: Price, spread, volume, volatility, temporal, cross-asset
- **Calibrated Probabilities**: Isotonic regression for accurate confidence scores
- **Auto-Training**: Automatic model training on historical data
- **Walk-Forward Validation**: Purged walk-forward splits for robust evaluation

### Risk Management

- **Position Limits**: Maximum 3% of portfolio per trade (configurable by risk mode)
- **Daily Limits**: Maximum 15% of portfolio traded daily
- **Drawdown Protection**: Circuit breaker at 10% daily or 20% weekly drawdown
- **Fee Optimization**: Only trades when expected profit > 3x trading fees
- **Concentration Limits**: Maximum 25% of portfolio in any single asset
- **Consecutive Loss Protection**: Automatic halt after 5 consecutive losses

### System Architecture

- **Modular Design**: Clean separation of concerns across modules
- **Real-Time Processing**: Sub-100ms decision latency targets
- **Data Storage**: Parquet files with partitioning and compression
- **Comprehensive Logging**: Structured JSON logs with audit trail
- **Health Monitoring**: Real-time system health and performance metrics
- **Circuit Breakers**: Automatic trading halts under adverse conditions

## Installation

### Prerequisites

- Windows 11 (or Windows 10)
- Python 3.10 or higher
- 32 GB RAM recommended (8 GB minimum)
- Stable internet connection (600 Mbps recommended)
- Kraken account with API keys (5 keys recommended)

### Step 1: Install Python Dependencies

Run the installation script:

```batch
install.bat
```

This will:
- Check Python version
- Upgrade pip
- Install all required packages
- Create necessary directories

### Step 2: Configure the System

Run the configuration script:

```batch
configure.bat
```

This will:
- Create a `.env` configuration file
- Open it in Notepad for editing

**You MUST manually edit the `.env` file to add:**

1. **Kraken API Keys** (at least 1, 5 recommended):
   ```
   KRAKEN_KEY_1=your_api_key_here
   KRAKEN_SECRET_1=your_api_secret_here
   KRAKEN_KEY_2=your_api_key_here
   KRAKEN_SECRET_2=your_api_secret_here
   ... (up to 5 keys)
   ```

2. **Portfolio Configuration**:
   ```
   PORTFOLIO_SIZE_USD=500
   RISK_MODE=balanced
   ```

3. **Emergency Kill Switch Password**:
   ```
   KILL_SWITCH_PASSWORD=your_secure_password
   ```

### Step 3: Start Trading

**⚠️ WARNING: This starts LIVE TRADING with real funds!**

```batch
start_bot.bat
```

The system will:
1. Validate configuration
2. Load ML models (train if missing)
3. Connect to Kraken WebSocket
4. Refresh trading universe
5. Begin live trading

**Press Ctrl+C to stop the bot safely.**

## Configuration

### Environment Variables

#### Trading Configuration
- `LIVE_TRADING=1` - Must be 1 (live only, no simulation)
- `PORTFOLIO_SIZE_USD=500` - Your total trading capital ($200-$800)
- `RISK_MODE=balanced` - `conservative`, `balanced`, or `aggressive`

#### API Configuration
- `KRAKEN_KEY_1` through `KRAKEN_KEY_5` - Your Kraken API keys
- `KRAKEN_SECRET_1` through `KRAKEN_SECRET_5` - Your Kraken API secrets

#### Risk Management
- `MAX_POSITION_PCT=3` - Maximum % of portfolio per trade
- `MAX_DAILY_VOLUME_PCT=15` - Maximum % of portfolio traded daily
- `MAX_DAILY_DRAWDOWN_PCT=10` - Circuit breaker threshold
- `MAX_CONSECUTIVE_LOSSES=5` - Automatic halt threshold

#### Model Configuration
- `CONFIDENCE_THRESHOLD=0.65` - Minimum confidence to trade
- `ENSEMBLE_MODELS=true` - Use XGBoost + LightGBM ensemble

#### System Configuration
- `LOG_LEVEL=INFO` - Logging level (DEBUG, INFO, WARNING, ERROR)
- `KILL_SWITCH_PASSWORD` - Password for emergency stop

### Risk Modes

**Conservative**:
- 1% per trade
- 5% daily volume limit
- 5% daily drawdown limit
- 65% confidence threshold

**Balanced** (default):
- 3% per trade
- 15% daily volume limit
- 10% daily drawdown limit
- 60% confidence threshold

**Aggressive**:
- 5% per trade
- 25% daily volume limit
- 15% daily drawdown limit
- 55% confidence threshold

## Trading Universe

The system automatically selects the top 10 USD trading pairs by 24-hour volume, filtered for:

- US-NC compliance (excludes restricted assets)
- Minimum daily volume ($1M USD)
- Minimum order size requirements
- Liquidity thresholds

Universe refreshes every hour automatically.

### Restricted Assets (US-NC)

The following assets are automatically excluded:
ACA, AGLD, ALICE, ANLOG, ASTR, ATLAS, AUDIO, AVAAI, C98, CFG, CLOUD, CSM, DBR, DUCK, FHE, GLMR, GRASS, HDX, INTR, K, KERNEL, KIN, KMNO, L3, LAYER, LMWR, MC, MV, NIL, NMR, NODL, NYM, OMNI, ORCA, OXY, PARA, PERP, PORTAL, PRCL, PSTAKE, RAY, REQ, REZ, ROOK, RSR, SAMO, SDN, SPICE, STEP, SWARMS, SWELL, TEER, TERM, VVV, WAL, WEN, WOO, XRT, YGG, ZEX

## Emergency Procedures

### Kill Switch Activation

**Method 1: Password-Protected API** (if implemented)
```python
kill_switch.activate(password="your_password", reason="Emergency stop")
```

**Method 2: Create Flag File**
Create a file named `kill_switch.flag` in the bot directory with:
```
KILL_SWITCH_ACTIVE=1
ACTIVATED_AT=2024-01-01T12:00:00
REASON=Emergency stop
```

**Method 3: Stop the Bot**
- Press Ctrl+C to stop the bot
- All pending orders will be cancelled automatically

### Circuit Breaker Triggers

The system automatically halts trading if:
- 5 consecutive losses occur
- Daily drawdown exceeds threshold (10% default)
- Spread exceeds 95th percentile
- API latency > 500ms
- Extreme volatility (>10% in 5 minutes)

Circuit breaker automatically resets after cooldown period (60 minutes default).

## Monitoring

### Log Files

Logs are stored in `logs/` directory:
- `trading_YYYY-MM-DD.log` - Daily trading logs
- `audit_log.jsonl` - Complete audit trail (JSON Lines format)

### Health Metrics

Monitor via logs:
- API latency (target: <100ms)
- Decision latency (target: <100ms)
- Order execution time
- Model prediction accuracy
- Risk metrics (drawdown, position concentration)

### Performance Analytics

Track:
- Win rate and average win/loss
- Profit factor
- Sharpe ratio
- Maximum drawdown
- Daily/weekly/monthly performance

## Data Storage

### Directory Structure

```
bot/
├── data/
│   ├── raw/           # Raw market data (Parquet)
│   │   └── {pair}/{YYYY}/{MM}/{DD}/
│   └── features/      # Computed features (Parquet)
│       └── {pair}/{YYYY}/{MM}/{DD}/
├── models/            # Trained ML models
│   └── {pair}/
├── logs/              # System logs
└── main.py            # Entry point
```

### Data Retention

- Raw data: 90 days (configurable)
- Features: 1 year (aggregated)
- Models: Latest version + previous version backup

## Machine Learning

### Model Training

Models are automatically trained on startup if not found:
- Training window: 30 days of historical data
- Validation: Purged walk-forward splits
- Features: Comprehensive price, spread, volume, volatility, temporal
- Target: Forward-looking returns (30-60 second horizon)

### Model Types

1. **XGBoost** (Primary): Tabular data optimized
2. **LightGBM** (Ensemble): Faster training, complementary predictions
3. **Calibration**: Isotonic regression for probability calibration

### Feature Engineering

Comprehensive feature set including:
- **Price**: Returns, log returns, z-scores (1s to 5m horizons)
- **Spread**: Absolute, percentage, percentile ranks
- **Volume**: Ratios, VWAP deviations, trade flow
- **Volatility**: Realized, Parkinson estimator, percentile ranks
- **Temporal**: Hour/day cyclical encodings, session indicators

## API Key Management

### Recommended Setup

Use 5 separate Kraken API keys for:
- Load balancing
- Rate limit distribution
- Automatic failover
- Risk distribution

### Key Pooling

The system automatically:
- Routes requests across keys (round-robin or health-based)
- Monitors key health and latency
- Automatically fails over to healthy keys
- Implements cooldown periods for rate-limited keys

### Rate Limits

- Per key: 20 requests/second
- Automatic throttling
- Exponential backoff on errors

## Compliance & Safety

### US-NC Compliance

- Hard-coded exclusion list enforced
- Runtime asset validation
- Complete audit logging
- Compliance violation alerts

### Safety Features

- Pre-trade validation (minimum order sizes, balance checks)
- Real-time risk monitoring
- Automatic position limits
- Circuit breakers
- Kill switch mechanisms

### Audit Trail

All trading decisions logged:
- Signal generation (features, predictions, confidence)
- Risk checks (pre-trade validation)
- Order placement (size, price, fees)
- Trade execution (fills, P&L)

## Troubleshooting

### Common Issues

**Bot won't start**:
- Check Python version (3.10+)
- Verify dependencies installed (`install.bat`)
- Check `.env` file exists and has API keys

**No trades executing**:
- Check confidence threshold (may be too high)
- Verify sufficient balance in account
- Check circuit breaker status
- Review risk limits (may be too conservative)

**API errors**:
- Verify API keys are correct
- Check API key permissions (needs trading permission)
- Review rate limits (may need more API keys)
- Check internet connection

**Model training failures**:
- Ensure sufficient historical data (30+ days)
- Check data directory permissions
- Verify feature computation working
- Review logs for specific errors

### Getting Help

1. Check log files in `logs/` directory
2. Review audit trail in `audit_log.jsonl`
3. Check health status in logs
4. Verify configuration in `.env` file

## Performance Expectations

### Small Capital ($200-$800)

- Focus: Fee optimization, capital preservation
- Strategy: High-confidence signals only
- Risk: Conservative position sizing
- Expected: Small but consistent gains

### Performance Targets

- Decision latency: <100ms
- Order execution: <500ms
- Win rate: 55%+ (after fees)
- Sharpe ratio: >0.5
- Maximum drawdown: <10% daily

**Note**: Past performance does not guarantee future results. Cryptocurrency trading involves substantial risk.

## License & Disclaimer

**THIS SOFTWARE IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND.**

- Trading cryptocurrencies involves substantial risk
- Past performance does not guarantee future results
- You may lose some or all of your capital
- Always test with minimum capital first
- Monitor the system closely
- Use kill switch if needed
- Comply with all applicable regulations

The authors and contributors are not responsible for any losses incurred from using this software.

## Support & Updates

For issues, questions, or updates:
1. Review the logs for error messages
2. Check configuration settings
3. Verify API key permissions
4. Ensure compliance with your jurisdiction

## System Requirements

- **OS**: Windows 11 (Windows 10 compatible)
- **Python**: 3.10 or higher
- **RAM**: 8 GB minimum (32 GB recommended)
- **Storage**: 50 GB free space (for data storage)
- **Network**: 600 Mbps recommended, <100ms latency to Kraken
- **GPU**: Optional (RTX 3070 or better for faster model training)

---

**⚠️ REMEMBER: This system trades with REAL MONEY. Always test with minimum capital and monitor closely!**
