# Kraken Live Trading System

**ML-Augmented Multi-Asset Live Trading System for Small Capital Accounts**

This repository contains a complete, production-grade trading system for Kraken cryptocurrency exchange, optimized for small capital accounts ($200-$800) with US-NC compliance.

## ⚠️ CRITICAL WARNING

**THIS SYSTEM TRADES WITH REAL MONEY ON LIVE MARKETS**

- No sandbox/simulation mode
- All trades use actual funds from your Kraken account
- Start with minimum capital and monitor closely
- Always know how to use the kill switch

## Quick Start

1. **Install Dependencies**
   ```batch
   cd bot
   install.bat
   ```

2. **Configure System**
   ```batch
   configure.bat
   ```
   Edit the `.env` file with your Kraken API keys and settings.

3. **Start Trading** (⚠️ LIVE TRADING)
   ```batch
   start_bot.bat
   ```

## Documentation

See `bot/README.md` for comprehensive documentation including:
- Complete feature list
- Configuration guide
- Risk management details
- Emergency procedures
- Troubleshooting
- Performance expectations

## System Architecture

```
bot/
├── core/           # API integration, WebSocket, key pooling
├── data/           # Storage, features, validation
├── ml/             # Model training, prediction, calibration
├── execution/      # Order management, routing, risk
├── strategy/       # Signal generation, decision engine
├── compliance/     # Asset filtering, compliance checks
├── ops/            # Monitoring, alerts, circuit breakers
├── config/          # Settings, universe management
└── main.py          # Main entry point
```

## Key Features

- **Live Trading Only**: No simulation mode
- **Multi-Asset**: Top 10 USD pairs by volume
- **US-NC Compliant**: Hard-coded exclusion list
- **ML-Powered**: XGBoost + LightGBM ensemble
- **5 API Key Pooling**: Round-robin with failover
- **Risk Management**: Comprehensive limits and circuit breakers
- **Small Capital Optimized**: Designed for $200-$800 accounts

## Requirements

- Windows 11 (Windows 10 compatible)
- Python 3.10+
- 8 GB RAM minimum (32 GB recommended)
- Stable internet connection
- Kraken account with API keys

## License & Disclaimer

**THIS SOFTWARE IS PROVIDED "AS IS" WITHOUT WARRANTY.**

Trading cryptocurrencies involves substantial risk. You may lose some or all of your capital. Always test with minimum capital first and monitor closely.

See `bot/README.md` for complete documentation and disclaimers.
