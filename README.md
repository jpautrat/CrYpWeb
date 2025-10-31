# ML Kraken Pro Live Trader

**Production-Grade ML-Augmented Cryptocurrency Trading System**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Private-red.svg)]()
[![Status](https://img.shields.io/badge/status-Production-green.svg)]()

---

## ⚠️ CRITICAL WARNING

**THIS IS A LIVE TRADING SYSTEM THAT PLACES REAL ORDERS WITH REAL MONEY**

- Real cryptocurrency trades will be executed on Kraken exchange
- Real money will be used from your account
- Automated trading carries significant financial risk
- Past performance does not guarantee future results
- You are responsible for all trades and losses
- Only use capital you can afford to lose

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Features](#features)
3. [System Requirements](#system-requirements)
4. [Quick Start](#quick-start)
5. [Installation](#installation)
6. [Configuration](#configuration)
7. [Architecture](#architecture)
8. [Usage](#usage)
9. [Risk Management](#risk-management)
10. [Compliance](#compliance)
11. [Monitoring](#monitoring)
12. [Troubleshooting](#troubleshooting)
13. [Advanced Topics](#advanced-topics)

---

## 🎯 Overview

ML Kraken Pro Live Trader is an institutional-grade, ML-augmented cryptocurrency trading system specifically optimized for small capital accounts ($200-$800). The system uses advanced machine learning models (XGBoost + LightGBM ensemble) with comprehensive microstructure features to generate high-probability trading signals.

### Key Capabilities

- **Multi-Model ML Pipeline**: XGBoost/LightGBM ensemble with probability calibration
- **60+ Features**: Microstructure, volatility regimes, temporal patterns, cross-asset correlations
- **Smart Execution**: Maker-biased orders with 5-key routing and automatic failover
- **Risk Management**: Multiple circuit breakers, drawdown protection, position limits
- **US Compliance**: Hard-coded North Carolina restricted assets list
- **Small Capital Optimized**: Fee optimization, conservative position sizing, capital preservation

---

## ✨ Features

### Machine Learning
- XGBoost + LightGBM ensemble models
- Walk-forward time series validation
- Platt scaling probability calibration
- Daily model retraining with 30-day rolling windows
- Real-time feature computation (<100ms latency)
- Model drift detection and automatic retraining

### Feature Engineering (60+ Features)
- **Price Features**: Multi-horizon returns, rolling z-scores, momentum
- **Spread & Liquidity**: Bid-ask spreads, percentile ranks, order book imbalance
- **Volume & Flow**: VWAP deviations, volume bursts, order flow imbalance
- **Volatility Regimes**: Realized vol, Parkinson estimator, GARCH forecasts
- **Temporal Features**: Time-of-day cyclical encoding, market session indicators
- **Cross-Asset Features**: BTC correlation, USD strength indicators

### Execution Engine
- Maker-biased strategy (post-only limit orders)
- 5-key API pool with intelligent routing
- Automatic failover and load balancing
- Sub-second order placement
- Order timeout management (30s default)

### Risk Management
- Per-trade position sizing (3% default)
- Daily volume limits (15% default)
- Drawdown circuit breakers (10% daily, 20% weekly)
- Consecutive loss protection (5 losses → cooldown)
- Position concentration limits (25% per asset)
- Fee optimization (3x edge requirement)

### Compliance
- US North Carolina restricted assets enforcement
- Pre-trade compliance checks
- Immutable audit logging with blockchain-style hashing
- Complete decision trail for regulatory review

### Operations
- System health monitoring
- Multi-level alerting system
- Multiple circuit breakers
- Emergency kill switch (file + password)
- Comprehensive structured logging
- Real-time performance metrics

---

## 💻 System Requirements

### Hardware
- **CPU**: Multi-core processor (4+ cores recommended)
- **RAM**: 32 GB (system uses <8 GB steady state)
- **Storage**: 2 TB SSD (90-day data retention)
- **GPU**: RTX 3070 8GB (optional, for model training acceleration)
- **Network**: 600 Mbps connection with <100ms latency to Kraken

### Software
- **OS**: Windows 11 (tested), Windows 10, or Linux
- **Python**: 3.10 or higher
- **Internet**: Stable connection required for live trading

### Kraken Account Requirements
- Verified Kraken account (US-compliant)
- **5 API Key Pairs** with permissions:
  - Query Funds
  - Query Open Orders & Trades
  - Query Closed Orders & Trades
  - Create & Modify Orders
  - Cancel/Close Orders
- Funded account ($200-$10,000 recommended)

---

## 🚀 Quick Start

### For Windows Users (Recommended)

```batch
# 1. Install dependencies
install.bat

# 2. Configure the system
configure.bat

# 3. Edit .env and add your API keys
notepad .env

# 4. Start the trading bot
start_bot.bat
```

### For Linux/Mac Users

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Create configuration
cp .env.example .env
nano .env  # Edit and add your API keys

# 3. Create directories
mkdir -p data/{raw,features,models,logs,logs/audit}

# 4. Start the bot
python main.py
```

---

## 📦 Installation

### Step 1: Clone or Extract Repository

```bash
# If using git
git clone <repository-url>
cd ml-kraken-pro-trader

# Or extract the provided zip file
```

### Step 2: Run Installation Script

**Windows:**
```batch
install.bat
```

**Linux/Mac:**
```bash
pip install -r requirements.txt
mkdir -p data/{raw,features,models,logs,logs/audit}
cp .env.example .env
```

### Step 3: Verify Installation

```bash
python -c "import pandas, numpy, xgboost, lightgbm; print('✓ All packages installed')"
```

---

## ⚙️ Configuration

### Environment Variables (.env)

The system is configured entirely through the `.env` file. All parameters have safe defaults.

#### Required Configuration

```ini
# Trading Configuration
LIVE_TRADING=1  # MUST be 1 (system validates this)
PORTFOLIO_SIZE_USD=500
RISK_MODE=balanced  # conservative, balanced, or aggressive

# API Keys (ALL 5 REQUIRED)
KRAKEN_KEY_1=your_api_key_here
KRAKEN_SECRET_1=your_api_secret_here
# ... (repeat for keys 2-5)

# Emergency Controls
KILL_SWITCH_PASSWORD=your_secure_password_here
```

#### Risk Modes

| Mode | Per Trade | Daily Limit | Confidence | Max Positions |
|------|-----------|-------------|------------|---------------|
| Conservative | 1% | 5% | 70% | 3 |
| Balanced | 3% | 15% | 65% | 5 |
| Aggressive | 5% | 25% | 55% | 8 |

### Configuration Helper

Use the configuration helper to validate and adjust settings:

```batch
configure.bat
```

Options:
1. View current configuration
2. Test API connectivity
3. Set risk mode
4. Set portfolio size
5. Edit configuration manually
6. Validate configuration

---

## 🏗️ Architecture

### System Components

```
┌─────────────────────────────────────────────────────────┐
│                   Main Application                       │
│                     (main.py)                           │
└─────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Strategy   │    │  Execution   │    │     Data     │
│    Layer     │    │    Engine    │    │  Pipeline    │
└──────────────┘    └──────────────┘    └──────────────┘
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  ML Models   │    │  Risk Mgmt   │    │   Storage    │
│  (XGB+LGB)   │    │  + Position  │    │  (Parquet)   │
└──────────────┘    └──────────────┘    └──────────────┘
        │                   │                   │
        └───────────────────┴───────────────────┘
                            │
                            ▼
                 ┌─────────────────────┐
                 │   Kraken Exchange   │
                 │  (Live Market Data) │
                 └─────────────────────┘
```

### Module Structure

```
bot/
├── core/           # API infrastructure (WebSocket, REST, Auth, Key Pool)
├── data/           # Data management (Storage, Features, Validation)
├── ml/             # ML pipeline (Training, Registry, Calibration)
├── execution/      # Order execution (Position Sizing, Risk, Routing)
├── strategy/       # Trading strategy (Signals, Decisions)
├── compliance/     # Compliance (Asset Filtering, Audit Logging)
├── ops/            # Operations (Monitoring, Alerts, Circuit Breakers)
└── config/         # Configuration (Settings, Universe, Thresholds)
```

---

## 📊 Usage

### Starting the Bot

**Windows:**
```batch
start_bot.bat
```

**Linux/Mac:**
```bash
python main.py
```

### System Startup Sequence

1. **Configuration Loading**: Validates all settings from `.env`
2. **Component Initialization**: Starts all system components
3. **API Connection**: Connects to Kraken REST and WebSocket APIs
4. **Universe Refresh**: Selects top 10 USD pairs by volume (NC-compliant)
5. **Market Data Subscription**: Subscribes to trade and spread data
6. **Trading Loop**: Begins processing signals and executing trades

### Normal Operation

The system operates fully autonomously:

- Generates signals every second for all universe pairs
- Executes trades when high-probability signals detected
- Manages positions and risk automatically
- Logs all decisions and trades for audit
- Monitors system health continuously
- Handles API failures with automatic failover

### Monitoring During Operation

Monitor the system through:

1. **Console Output**: Real-time status updates
2. **Log Files**: `data/logs/trader_YYYY-MM-DD.log`
3. **Audit Logs**: `data/logs/audit/audit_YYYYMMDD.jsonl`
4. **Key Metrics** (logged every 60 seconds):
   - Trades executed
   - Daily P&L
   - Risk status
   - System health

---

## 🛡️ Risk Management

### Multi-Layer Protection

#### Layer 1: Position Sizing
- Maximum 3% of portfolio per trade (balanced mode)
- Confidence-based sizing (25%-100% of max)
- Kelly criterion with conservative fraction

#### Layer 2: Daily Limits
- Maximum 15% of portfolio traded per day
- Maximum 5 concurrent open positions
- Maximum 25% in any single asset

#### Layer 3: Drawdown Protection
- 10% daily drawdown → circuit breaker (60 min cooldown)
- 20% weekly drawdown → circuit breaker (60 min cooldown)
- 5 consecutive losses → cooldown (60 min)

#### Layer 4: Market Condition Protection
- Wide spread detection (>95th percentile)
- High latency protection (>500ms)
- Extreme volatility halt (>10% in 5 min)

#### Layer 5: Emergency Controls
- Kill switch file: Create `data/.kill_switch` to immediately halt
- Kill switch password: Emergency stop via password
- Keyboard interrupt: Press Ctrl+C for graceful shutdown

### Fee Optimization

For small capital accounts, fees are critical:

- Expected profit must exceed fees by 3x
- Maker orders preferred (0.16% vs 0.26% taker)
- Minimum edge requirement: 20 basis points (0.2%)
- Only trade when EV > (fees + spread + buffer)

---

## 📋 Compliance

### US North Carolina Restrictions

The system enforces hard-coded restrictions for 70 assets not available in North Carolina:

```
ACA, AGLD, ALICE, ANLOG, ASTR, ATLAS, AUDIO, AVAAI, C98, CFG, CLOUD, 
CSM, DBR, DUCK, FHE, GLMR, GRASS, HDX, INTR, K, KERNEL, KIN, KMNO, 
L3, LAYER, LMWR, MC, MV, NIL, NMR, NODL, NYM, OMNI, ORCA, OXY, PARA, 
PERP, PORTAL, PRCL, PSTAKE, RAY, REQ, REZ, ROOK, RSR, SAMO, SDN, 
SPICE, STEP, SWARMS, SWELL, TEER, TERM, VVV, WAL, WEN, WOO, XRT, YGG, ZEX
```

Any attempt to trade these assets will be:
1. Blocked immediately
2. Logged as compliance violation
3. Reported in audit logs

### Audit Trail

Every trading decision and order is logged immutably:

- Trade decisions with confidence and expected value
- Order submissions with all parameters
- Order fills with prices and fees
- Compliance checks and violations
- Circuit breaker activations
- Model updates and performance metrics

Audit logs use blockchain-style hashing for tamper detection.

---

## 📈 Monitoring

### Real-Time Monitoring

Monitor system status through multiple channels:

#### Console Output
```
[INFO] Stats: 15 trades, Risk: Daily PnL=$12.50
[INFO] BTC/USD: buy signal, confidence=0.72, ev=0.0032
[INFO] Order filled: buy 0.00050000 BTC/USD @ $43250.00
```

#### Log Files
Located in `data/logs/`:
- `trader_YYYY-MM-DD.log`: Main system log
- `audit/audit_YYYYMMDD.jsonl`: Immutable audit trail

#### Key Metrics

System logs statistics every 60 seconds:
- **Trades Executed**: Total count
- **Execution Rate**: Signals → Trades ratio
- **Daily P&L**: Current day profit/loss
- **Daily Drawdown**: Current drawdown percentage
- **Consecutive Losses**: Current streak
- **Open Positions**: Number and value
- **System Health**: CPU, memory, disk usage

### Performance Metrics

Track model and trading performance:

- **Model Metrics**: Accuracy, precision, recall, Sharpe ratio
- **Execution Metrics**: Fill rates, slippage, latency
- **Risk Metrics**: Drawdowns, win rate, profit factor
- **Capital Efficiency**: ROI, Sharpe, Sortino, Calmar ratios

---

## 🔧 Troubleshooting

### Common Issues

#### Issue: "No API keys available"
**Solution:**
1. Check that all 5 API key pairs are in `.env`
2. Verify keys have correct permissions
3. Test with `configure.bat` → "Test API connectivity"

#### Issue: "Insufficient data for training"
**Solution:**
1. System needs time to collect market data
2. Wait 24 hours for sufficient historical data
3. Or manually download historical data from Kraken

#### Issue: "Circuit breaker activated"
**Cause:** Risk limits exceeded
**Solution:**
1. Check risk status in logs
2. Wait for cooldown period (60 minutes)
3. Review and adjust risk parameters if needed

#### Issue: "Kill switch is active"
**Solution:**
1. Delete `data/.kill_switch` file
2. Or deactivate via password in configuration

#### Issue: High memory usage
**Solution:**
1. Reduce `FEATURE_CACHE_SIZE_MB` in `.env`
2. Reduce `TICK_DATA_BUFFER_SIZE`
3. Increase `DATA_RETENTION_DAYS` cleanup frequency

### Emergency Procedures

#### Emergency Stop (Immediate)
1. **Keyboard**: Press `Ctrl+C`
2. **File**: Create file `data/.kill_switch`
3. **Password**: Use kill switch password from `.env`

#### Recovery After Crash
1. Check logs for error cause
2. Verify system resources (memory, disk)
3. Check API key health
4. Restart with `start_bot.bat`

#### Data Corruption
1. Stop the bot
2. Delete corrupted files in `data/`
3. System will rebuild from live data
4. Or restore from backup if available

### Getting Help

Check logs in this order:
1. Console output (immediate errors)
2. `data/logs/trader_YYYY-MM-DD.log` (detailed system log)
3. `data/logs/audit/audit_YYYYMMDD.jsonl` (trade decisions)

---

## 🚀 Advanced Topics

### Model Retraining

Models automatically retrain every 24 hours. Manual retraining:

```python
from bot.ml import ModelTrainer
from bot.data import StorageManager, FeatureEngineer

trainer = ModelTrainer(storage, feature_engineer)
metadata = trainer.train_and_save_model('BTC/USD', training_days=30)
```

### Custom Features

Add custom features in `bot/data/feature_engineer.py`:

```python
def _compute_custom_features(self, ticks: pd.DataFrame) -> Dict:
    features = {}
    # Your custom feature computation
    features['my_indicator'] = compute_my_indicator(ticks)
    return features
```

### Performance Optimization

For high-frequency operations:

1. **Reduce Latency**:
   - Use `MAX_DECISION_LATENCY_MS=50`
   - Optimize feature computation
   - Use faster storage (NVMe SSD)

2. **Scale Up**:
   - Increase `UNIVERSE_SIZE` for more pairs
   - Add more API keys for higher throughput
   - Use GPU for model training

3. **Memory Optimization**:
   - Reduce `TICK_DATA_BUFFER_SIZE`
   - Lower `FEATURE_CACHE_SIZE_MB`
   - Increase cleanup frequency

### Backtesting

While this is a live-only system, you can analyze historical performance:

```python
from bot.data import StorageManager

storage = StorageManager()
features = storage.load_features('BTC/USD', start_time, end_time)
# Analyze features and labels for strategy validation
```

---

## 📄 File Structure

```
ml-kraken-pro-trader/
├── bot/                    # Main package
│   ├── core/              # API infrastructure
│   ├── data/              # Data management
│   ├── ml/                # ML pipeline
│   ├── execution/         # Order execution
│   ├── strategy/          # Trading strategy
│   ├── compliance/        # Compliance systems
│   ├── ops/               # Operations
│   └── config/            # Configuration
├── data/                   # Data storage (created by system)
│   ├── raw/               # Raw tick data (partitioned)
│   ├── features/          # Computed features (partitioned)
│   ├── models/            # Trained models (versioned)
│   └── logs/              # System and audit logs
├── main.py                # Application entry point
├── requirements.txt       # Python dependencies
├── .env.example           # Configuration template
├── .env                   # Your configuration (DO NOT COMMIT)
├── install.bat            # Windows installation script
├── configure.bat          # Windows configuration helper
├── start_bot.bat          # Windows start script
└── README.md              # This file
```

---

## ⚖️ Legal Disclaimer

THIS SOFTWARE IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED. 

- Use at your own risk
- No guarantees of profitability
- Cryptocurrency trading is extremely risky
- You may lose your entire investment
- Past performance does not indicate future results
- The authors are not responsible for any losses
- You are responsible for complying with all local regulations
- This software is for personal use only

By using this software, you acknowledge and accept these risks.

---

## 🔒 Security

### API Key Security
- Never commit `.env` to version control
- Use API keys with minimum required permissions
- Rotate API keys periodically
- Monitor API key usage on Kraken

### System Security
- Keep Python and packages updated
- Use strong kill switch password
- Monitor system logs for unusual activity
- Run on secure, dedicated hardware

---

## 📞 Support

For issues and questions:

1. Check [Troubleshooting](#troubleshooting) section
2. Review logs in `data/logs/`
3. Verify configuration with `configure.bat`
4. Test API connectivity
5. Check system resources (CPU, RAM, disk)

---

## 🎓 Learning Resources

To understand the system better:

- **ML Fundamentals**: Study XGBoost and LightGBM documentation
- **Market Microstructure**: Learn about order books, spreads, VWAP
- **Risk Management**: Study position sizing, Kelly criterion, drawdowns
- **Time Series**: Understand cross-validation, walk-forward validation
- **Kraken API**: Read official Kraken API documentation

---

## 📊 System Statistics

After running, check your performance:

```python
python -c "from bot.strategy import DecisionEngine; stats = decision_engine.get_statistics(); print(stats)"
```

Key metrics to monitor:
- Execution rate (signals → trades)
- Win rate and profit factor
- Average trade P&L
- Risk-adjusted returns (Sharpe, Sortino)
- Maximum drawdown
- Model accuracy and confidence

---

**Remember: This is live trading with real money. Start small, monitor closely, and never risk more than you can afford to lose.**

**Good luck and trade responsibly! 🚀📈**
