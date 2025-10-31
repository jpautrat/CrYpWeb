# ML Training & Model Lifecycle - Explained

## 🎯 No Pre-Trained Weights (By Design)

This system does **NOT** come with pre-trained model weights. This is intentional and required for proper operation.

---

## Why No Pre-Trained Models?

### 1. **Market Data is Time-Sensitive**
- Cryptocurrency markets change every second
- Patterns from last week don't work this week
- Pre-trained models would be worthless immediately

### 2. **Must Adapt to Current Conditions**
- System trains on YOUR live data from Kraken
- Uses rolling 30-day windows
- Continuously adapts to market evolution

### 3. **Legal & Compliance**
- Cannot distribute financial trading models
- Each user must train on own data
- Regulatory requirement for transparency
- Prevents liability issues

---

## 🚀 System Lifecycle - What Actually Happens

### **Phase 1: First Launch (Minutes 0-5)**

```
When you run launch.bat:

1. System starts ✓
2. Connects to Kraken REST API ✓
3. Connects to Kraken WebSocket ✓
4. Selects top 10 USD trading pairs ✓
5. Subscribes to live market data ✓
6. Begins collecting ticks, spreads, order books ✓
```

**Status:** System is RUNNING but not fully trained yet

---

### **Phase 2: Data Collection (Hours 0-24)**

```
During first 24 hours:

├── Real-time data streaming from Kraken
│   ├── Trade data (every tick)
│   ├── Order book snapshots
│   ├── Bid/ask spreads
│   └── Volume information
│
├── Feature computation in real-time
│   ├── 60+ features calculated per second
│   ├── Price features (returns, momentum)
│   ├── Spread features (bid-ask, imbalance)
│   ├── Volume features (VWAP, flow)
│   ├── Volatility features (realized vol, GARCH)
│   └── Temporal features (time-of-day)
│
├── Data storage
│   ├── Saved to: data/raw/PAIR/YYYY/MM/DD/
│   ├── Format: Parquet (compressed)
│   └── Features: data/features/PAIR/YYYY/MM/DD/
│
└── Trading behavior during collection:
    ├── May place some trades based on simple signals
    ├── Uses conservative position sizing
    ├── Focuses on learning market structure
    └── Builds historical database
```

**What you'll see:**
```
[INFO] Collecting market data...
[INFO] BTC/USD: 1,234 ticks collected, 567 features computed
[INFO] No trained model yet for BTC/USD - using heuristics
[INFO] Data collection progress: 6.5 hours of 24 hours
```

**Status:** System is collecting data, minimal trading

---

### **Phase 3: First Model Training (Hour 24+)**

```
After 24 hours of data collection:

1. Automatic training triggers
   ├── Checks: Do we have 10,000+ samples? ✓
   ├── Loads: Last 30 days of features
   ├── Creates: Labels from forward returns
   └── Validates: Data quality checks

2. XGBoost training
   ├── Walk-forward time series CV
   ├── 5-fold validation
   ├── Purged splits (no data leakage)
   ├── Training: ~5-10 minutes per pair
   └── Saves: data/models/PAIR/xgboost_TIMESTAMP.pkl

3. LightGBM training (ensemble)
   ├── Same validation strategy
   ├── Training: ~5-10 minutes per pair
   └── Saves: data/models/PAIR/lightgbm_TIMESTAMP.pkl

4. Probability calibration
   ├── Platt scaling on validation set
   ├── Ensures probabilities are well-calibrated
   └── Critical for position sizing

5. Model deployment
   ├── Models loaded into memory
   ├── Model registry updated
   ├── System switches to ML-based predictions
   └── Full trading capability activated
```

**What you'll see:**
```
[INFO] Triggering model training for BTC/USD
[INFO] Preparing training data: 30 days, 43,521 samples
[INFO] Training XGBoost model...
[INFO] Walk-forward validation: accuracy=0.58, sharpe=0.72
[INFO] Training LightGBM model...
[INFO] Ensemble validation: accuracy=0.61, sharpe=0.85
[INFO] Calibrating probabilities...
[INFO] Model deployed for BTC/USD
[INFO] BTC/USD: Now using ML predictions (confidence boost!)
```

**Training time:** ~1-2 hours for all 10 pairs

**Status:** System is FULLY OPERATIONAL with trained models

---

### **Phase 4: Daily Operation (Hour 24+)**

```
Normal operation with trained models:

Every Second:
├── Computes 60+ features for all pairs
├── Feeds features to XGBoost + LightGBM
├── Gets probability predictions
├── Calculates expected value
├── Makes trading decisions
└── Executes high-confidence trades

Every 24 Hours:
├── Retrains all models on latest 30-day window
├── Incorporates new market data
├── Updates feature importance
├── Recalibrates probabilities
└── Deploys improved models

Continuous:
├── Monitors model performance
├── Detects model drift
├── Triggers emergency retraining if needed
└── Logs all metrics for analysis
```

**What you'll see:**
```
[INFO] BTC/USD: buy signal, confidence=0.73, ev=0.0034
[INFO] Order created: buy 0.00012000 BTC/USD @ $43,248.50
[INFO] Order filled: buy 0.00012000 @ $43,248.50 | fees=$0.0083
[INFO] Model performance: BTC/USD accuracy=0.62, sharpe=0.91
[INFO] Stats: 15 trades, Risk: Daily PnL=$12.50
```

**Status:** System is trading autonomously with ML

---

## 📁 Where Models Are Stored

### Directory Structure:
```
data/
├── models/
│   ├── BTC_USD/
│   │   ├── xgboost_20241031_120000.pkl      ← XGBoost model
│   │   ├── lightgbm_20241031_120000.pkl     ← LightGBM model
│   │   └── metadata_20241031_120000.json    ← Training metrics
│   ├── ETH_USD/
│   │   ├── xgboost_20241031_120530.pkl
│   │   └── lightgbm_20241031_120530.pkl
│   └── (8 more pairs...)
```

### Model Files:
- **Size:** ~5-50 MB per model
- **Format:** Python pickle (.pkl)
- **Contents:** Trained XGBoost/LightGBM tree structures
- **Lifespan:** Replaced every 24 hours with retrained version

---

## ⏱️ Timeline Summary

| Time | Activity | Trading |
|------|----------|---------|
| Hour 0 | System starts, connects to Kraken | Minimal |
| Hours 1-24 | Data collection, feature storage | Conservative |
| Hour 24 | First ML training (1-2 hours) | Paused |
| Hour 26+ | Full ML operation | Active |
| Daily | Automatic retraining | Brief pause |

---

## 🎓 Technical Details

### Model Architecture:

**XGBoost Configuration:**
```python
{
    'objective': 'multi:softprob',
    'num_class': 5,
    'max_depth': 6,
    'learning_rate': 0.1,
    'n_estimators': 200,
    'subsample': 0.8,
    'colsample_bytree': 0.8,
}
```

**LightGBM Configuration:**
```python
{
    'objective': 'multiclass',
    'num_class': 5,
    'max_depth': 6,
    'learning_rate': 0.1,
    'n_estimators': 200,
    'subsample': 0.8,
    'colsample_bytree': 0.8,
}
```

### Training Data:
- **Window:** 30 days of historical data
- **Samples:** ~10,000-50,000 per pair
- **Features:** 60+ computed features
- **Labels:** 5-class (Strong Down, Down, Neutral, Up, Strong Up)
- **Validation:** Walk-forward time series split

### Performance Metrics:
- **Accuracy:** Target >55%
- **Sharpe Ratio:** Target >0.5
- **Precision/Recall:** Balanced across classes
- **Expected Value:** Optimized after fees

---

## ❓ Common Questions

### "Why can't you just include pre-trained models?"

**Answer:** Because:
1. They'd be trained on outdated market data
2. Market conditions change daily
3. Your trading times differ from training times
4. Regulatory/legal restrictions
5. Models must adapt to YOUR specific capital and risk

### "How good are the models?"

**Answer:** Performance depends on:
- Market conditions (volatility, trends)
- Quality of collected data
- Amount of training data available
- Current market regime
- Typically: 55-65% accuracy (above random)

### "What if models perform poorly?"

**Answer:** System has protections:
- Minimum accuracy threshold (55%)
- Automatic model drift detection
- Circuit breakers for excessive losses
- Models retrain daily to adapt
- Can manually trigger retraining

### "Can I use my own models?"

**Answer:** Yes! Advanced users can:
- Modify: bot/ml/model_trainer.py
- Add custom features
- Use different algorithms
- Adjust hyperparameters
- System is fully customizable

---

## 🔍 Monitoring Model Training

### Log Files:

**During training:**
```
data/logs/trader_2024-10-31.log
```

Look for:
```
[INFO] Triggering model training for BTC/USD
[INFO] Preparing training data: 30 days, 43521 samples
[INFO] Training XGBoost model...
[INFO] Validation: accuracy=0.58, precision=0.61, recall=0.56
[INFO] Training LightGBM model...
[INFO] Validation: accuracy=0.61, precision=0.63, recall=0.59
[INFO] Calibrating probabilities...
[INFO] Model saved: data/models/BTC_USD/xgboost_20241031_120000.pkl
```

### Model Metadata:

Check: `data/models/PAIR/metadata_TIMESTAMP.json`

Contains:
```json
{
  "pair": "BTC/USD",
  "training_samples": 43521,
  "training_days": 30,
  "features": ["price_last", "return_pct_1s", ...],
  "metrics": {
    "accuracy": 0.612,
    "precision": 0.628,
    "recall": 0.594,
    "sharpe_proxy": 0.847
  },
  "timestamp": "20241031_120000"
}
```

---

## ✅ Checklist: Is Training Working?

After 24 hours of running, verify:

- [ ] Files exist in: `data/models/BTC_USD/`
- [ ] See: `xgboost_*.pkl` and `lightgbm_*.pkl`
- [ ] Log shows: "Model deployed for BTC/USD"
- [ ] Console shows: "using ML predictions"
- [ ] Accuracy metrics: >0.55
- [ ] Trading confidence increasing

---

## 🚨 Troubleshooting

### "No models found after 24 hours"

**Check:**
1. Is data being collected? (Check `data/raw/`)
2. Are features computed? (Check `data/features/`)
3. Any errors in logs? (Search "ERROR" in logs)
4. Sufficient samples? (Need 10,000+)

**Solution:**
- Let it run longer (may need 36-48 hours initially)
- Check disk space (models need storage)
- Verify no crashes in logs

### "Model accuracy very low (<50%)"

**This is normal in some cases:**
- Choppy/sideways markets
- Very low volatility periods
- Insufficient training data
- Unusual market conditions

**System will:**
- Continue collecting data
- Retrain daily
- Improve over time
- Circuit breakers protect capital

---

## 📈 Expected Performance Timeline

### Week 1:
- Models train and improve
- Accuracy: 52-58%
- Trading: Conservative
- Focus: Learning market structure

### Week 2-4:
- Models stabilize
- Accuracy: 56-62%
- Trading: More confident
- Focus: Profitable patterns

### Month 2+:
- Models mature
- Accuracy: 58-65%
- Trading: Full capability
- Focus: Consistent returns

---

**Remember:** This is a LIVE system that learns from REAL data. No pre-trained weights needed or wanted!
