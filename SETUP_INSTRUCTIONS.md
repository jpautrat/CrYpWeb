# Setup Instructions - Quick Reference

## Your Questions Answered

### ✅ 1. Setup Batch File - CREATED

**File:** `setup.bat`

**What it does:**
- Interactive wizard walks you through EVERYTHING
- Prompts for all 5 API keys (you paste them in)
- Asks for portfolio size, risk mode, preferences
- Automatically creates .env file with your settings
- Installs all dependencies
- Creates all directories
- Validates configuration

**How to use:**
```batch
Double-click: setup.bat
Follow the prompts
Enter your 5 API key pairs when asked
Done!
```

**No manual .env editing required!**

---

### ✅ 2. Launch Batch File - CREATED

**File:** `launch.bat`

**What it does:**
- Pre-flight checks (Python, dependencies, config)
- Validates your configuration
- Shows your settings summary
- Safety warnings
- Starts the trading system
- Handles errors gracefully

**How to use:**
```batch
Double-click: launch.bat
Type: START
System launches!
```

**Uses the configuration from setup.bat automatically.**

---

### ✅ 3. ML Weights & Training - EXPLAINED

**Answer: NO pre-trained weights (by design)**

**Why?**
- Market data changes every second
- Pre-trained models would be worthless
- Must train on YOUR live data from Kraken
- Legal/regulatory requirements
- Each user's data is unique

**What happens instead:**

#### **Hour 0-24: Data Collection**
```
System runs and collects live market data:
✓ Tick data from Kraken
✓ Order book snapshots
✓ Computed features
✓ Some conservative trading
✓ Building training dataset
```

#### **Hour 24-26: First Training**
```
Automatic ML training triggers:
✓ XGBoost model trained (10 min per pair)
✓ LightGBM model trained (10 min per pair)
✓ Probability calibration
✓ Models deployed
✓ System switches to ML predictions
```

#### **Hour 26+: Full Operation**
```
Trading with trained models:
✓ Real-time ML predictions
✓ High-confidence trades
✓ Daily retraining (adapts to market)
✓ Continuous improvement
```

**Timeline:**
- **Start** → System launches, collects data
- **+24 hours** → Models train automatically (~2 hours)
- **+26 hours** → Full ML operation

**No action required from you! It's automatic.**

---

## Complete Setup Process

### Step 1: Run Setup Wizard (5 minutes)
```batch
setup.bat
```

**You'll be asked for:**
1. Portfolio size ($200-10,000)
2. Risk mode (Conservative/Balanced/Aggressive)
3. Number of trading pairs (5-20)
4. Kill switch password
5. **Your 5 Kraken API key pairs** ← Just paste them when prompted
6. Advanced options (or use defaults)

**Output:** 
- `.env` file created with your settings
- All directories created
- Dependencies installed
- Configuration validated

### Step 2: Launch Trading System (30 seconds)
```batch
launch.bat
```

**System will:**
1. Check everything is configured
2. Show your settings
3. Ask for final confirmation (type START)
4. Begin trading

### Step 3: Monitor Operation (Ongoing)
```
Watch console window for:
- Data collection progress (first 24h)
- Model training (hour 24-26)
- Live trading (hour 26+)
- Statistics every 60 seconds
```

### Step 4: Let Models Train (Automatic)
```
After 24 hours of data collection:
- Models train automatically
- Takes ~2 hours for all 10 pairs
- System logs progress
- Switches to ML predictions when ready
```

---

## Files Overview

| File | Purpose |
|------|---------|
| `setup.bat` | **NEW** - Interactive setup wizard |
| `launch.bat` | **NEW** - Start trading with validation |
| `install.bat` | Simple dependency installer |
| `configure.bat` | Configuration helper/validator |
| `start_bot.bat` | Original launch script |
| `.env` | Your configuration (auto-created by setup.bat) |

**Recommended workflow:**
1. Use `setup.bat` (one-time setup)
2. Use `launch.bat` (every time you want to trade)

---

## Quick Start (5 Minutes Total)

### Option A: Interactive Setup (EASIEST)

```batch
1. Double-click: setup.bat
2. Answer the questions
3. Paste your 5 API keys when asked
4. Wait for "SETUP COMPLETE"
5. Double-click: launch.bat
6. Type: START
7. Done!
```

### Option B: Manual Setup

```batch
1. Double-click: install.bat
2. Edit .env in Notepad (add 5 API keys)
3. Double-click: configure.bat → option 6 (validate)
4. Double-click: start_bot.bat → type START
5. Done!
```

**Both methods work perfectly!**

---

## What You'll See

### During Setup (setup.bat):
```
[1/10] Checking Python installation...
[2/10] Installing dependencies...
[3/10] Creating data directories...
[4/10] Trading Parameters:
  Enter portfolio size: 500
  Select risk mode: 2 (Balanced)
[5/10] Security:
  Enter kill switch password: ********
[6/10] API Keys:
  Enter Key 1: [paste your key]
  Enter Secret 1: [paste your secret]
  ... (repeat for 5 keys)
[7/10] Advanced options: [defaults OK]
[8/10] Creating .env file...
[9/10] Validating...
[10/10] SETUP COMPLETE!
```

### During Launch (launch.bat):
```
[Pre-Flight Checks]
  Python: OK
  Dependencies: OK
  Configuration: OK
  Data directories: OK

[Configuration Summary]
  Portfolio: $500
  Risk Mode: balanced
  Trading Pairs: 10

⚠️  WARNING: Live trading with real money

Type 'START' to launch: START

[Launching...]
System starts, connects to Kraken...
```

### During Operation:
```
[Hour 0-24] Data Collection
  Collecting market data...
  BTC/USD: 5,432 ticks collected
  
[Hour 24] Model Training (automatic)
  Training XGBoost for BTC/USD...
  Training LightGBM for BTC/USD...
  Models deployed!
  
[Hour 26+] Live Trading
  BTC/USD: buy signal, confidence=0.73
  Order filled: $43,248.50
  Stats: 15 trades, Daily PnL=$12.50
```

---

## Troubleshooting

### "Can't find setup.bat"
**Solution:** You're in the wrong folder. Navigate to where you extracted the system.

### "Python not found"
**Solution:** Install Python 3.10+ from python.org, check "Add to PATH"

### "Invalid API key"
**Solution:** 
1. Go to Kraken website
2. Verify keys are active
3. Check permissions (need Orders + Query)
4. Re-run setup.bat and re-enter keys

### "No models after 24 hours"
**This is normal!** Models need:
- 24 hours of data collection
- Then 2 hours to train
- Total: 26 hours from first launch
- Check logs for "Training model for..."

---

## Important Notes

### About API Keys:
- You MUST have 5 separate key pairs
- All 5 needed for optimal performance
- System balances load across them
- Automatic failover if one fails

### About Training:
- **First 24 hours:** System collects data
- **Hour 24-26:** Models train automatically
- **Hour 26+:** Full ML operation
- **Daily:** Models retrain on latest data

### About Capital:
- Start small: $200-500 recommended
- Monitor closely first week
- Scale up gradually
- Never risk more than you can lose

### About Monitoring:
- Keep console window open
- Check logs daily: `data/logs/`
- Review trades and decisions
- Circuit breakers protect you

---

## Emergency Stop

**Three methods:**

1. **Keyboard:** Press Ctrl+C
2. **File:** Create `data\.kill_switch`
3. **Password:** Use password from .env

**All three work instantly!**

---

## Next Steps After Setup

1. ✅ Verify setup.bat completed successfully
2. ✅ Check .env file exists
3. ✅ Run launch.bat
4. ✅ Watch first hour of operation
5. ✅ Check back after 24 hours (models training)
6. ✅ Monitor daily P&L and logs
7. ✅ Review performance after first week

---

## Support Files

| Document | Contents |
|----------|----------|
| `SETUP_INSTRUCTIONS.md` | This file |
| `ML_TRAINING_EXPLAINED.md` | Detailed ML training process |
| `README.md` | Complete system manual |
| `QUICKSTART.md` | 5-minute guide |
| `SYSTEM_OVERVIEW.md` | Technical architecture |

---

**You're all set! Run setup.bat and start trading in 5 minutes! 🚀**
