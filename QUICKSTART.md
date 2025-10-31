# Quick Start Guide - ML Kraken Pro Live Trader

## ⚡ 5-Minute Setup (Windows)

### Step 1: Install (2 minutes)
```batch
Double-click: install.bat
Wait for installation to complete
```

### Step 2: Configure (2 minutes)
```batch
1. Open .env in Notepad
2. Add your 5 Kraken API key pairs:
   KRAKEN_KEY_1=your_key_here
   KRAKEN_SECRET_1=your_secret_here
   (repeat for keys 2-5)
3. Set KILL_SWITCH_PASSWORD=your_secure_password
4. Save and close
```

### Step 3: Validate (30 seconds)
```batch
Double-click: configure.bat
Choose option 6: Validate configuration
Verify ✓ Configuration is valid
```

### Step 4: Start Trading (30 seconds)
```batch
Double-click: start_bot.bat
Type: START
Press Enter
```

**Done! System is now live trading.**

---

## 📊 What Happens Next?

### First 5 Minutes
- System connects to Kraken
- Subscribes to market data for top 10 pairs
- Begins collecting tick data
- Generates signals every second
- Executes high-confidence trades

### First Hour
- 60+ features computed in real-time
- ML models make predictions
- Trades placed when edge > 3x fees
- All decisions logged to `data/logs/`
- Risk management actively protecting capital

### First Day
- Models train on collected data
- Performance metrics tracked
- Daily limits enforced
- Circuit breakers ready to protect

---

## 🛑 Emergency Stop

**Need to stop immediately?**

Method 1: **Keyboard**
```
Press Ctrl+C in the terminal window
```

Method 2: **Kill Switch File**
```
Create file: data/.kill_switch
```

Method 3: **Password**
```
Use KILL_SWITCH_PASSWORD from .env
```

---

## 📈 Monitoring

### Real-Time
Watch the console output for:
- Signal generation
- Trade execution
- Risk status
- System health

### Log Files
Check `data/logs/trader_YYYY-MM-DD.log` for:
- Detailed system operations
- Error messages
- Performance statistics
- Circuit breaker activations

### Audit Trail
Review `data/logs/audit/audit_YYYYMMDD.jsonl` for:
- Every trade decision
- Order submissions and fills
- Compliance checks
- Model updates

---

## ⚙️ Configuration Options

### Risk Modes

**Conservative** (Safest)
```ini
RISK_MODE=conservative
# 1% per trade, 5% daily, 70% confidence
```

**Balanced** (Default)
```ini
RISK_MODE=balanced
# 3% per trade, 15% daily, 65% confidence
```

**Aggressive** (Risky)
```ini
RISK_MODE=aggressive
# 5% per trade, 25% daily, 55% confidence
```

### Portfolio Size
```ini
PORTFOLIO_SIZE_USD=500  # Your total capital
```

---

## 🎯 Key Metrics to Watch

### Daily
- **Daily P&L**: Should be positive more often than negative
- **Daily Drawdown**: Should stay below 10%
- **Trades Executed**: Varies, typically 5-20 per day
- **Circuit Breakers**: Should rarely trigger

### Weekly
- **Weekly P&L**: Target positive
- **Weekly Drawdown**: Should stay below 20%
- **Win Rate**: Target 55-60%
- **Avg Trade P&L**: Should be positive after fees

### Monthly
- **Total Return**: Goal is consistent growth
- **Sharpe Ratio**: Higher is better (>1.0 good)
- **Max Drawdown**: Lower is better
- **Model Accuracy**: Should stay >55%

---

## ⚠️ Important Reminders

### Before You Start
- [x] All 5 API keys configured
- [x] Portfolio size set correctly
- [x] Kill switch password set
- [x] Configuration validated
- [x] Risk mode selected
- [x] You understand this uses REAL MONEY

### During Operation
- [ ] Monitor logs regularly (at least daily)
- [ ] Check for circuit breaker activations
- [ ] Review trades and decisions
- [ ] Watch for API errors
- [ ] Verify model performance metrics

### If Something Goes Wrong
1. **Stop the bot** (Ctrl+C or kill switch)
2. **Check logs** in data/logs/
3. **Review configuration** with configure.bat
4. **Test API** connectivity
5. **Restart** if issue resolved

---

## 📞 Common Questions

### "How long until profitable?"
- No guarantees
- Depends on market conditions
- Model quality improves with more data
- Expect volatility in first weeks

### "How much can I make?"
- Cannot predict returns
- System designed for steady growth
- Risk management prevents large losses
- Fee optimization critical for small capital

### "Is it safe?"
- Multiple safety layers implemented
- Circuit breakers protect capital
- No trading system is risk-free
- You can still lose money

### "Can I customize it?"
- Yes, all parameters in .env
- Risk mode selection available
- Advanced users can modify code
- Default settings are well-tested

---

## 🚀 Success Tips

1. **Start Small**
   - Use minimum capital first ($200-300)
   - Monitor closely for first week
   - Increase capital only after verification

2. **Monitor Actively**
   - Check logs daily
   - Review all circuit breaker activations
   - Understand why trades were made
   - Track model performance

3. **Be Patient**
   - Models improve with data
   - Don't panic on small losses
   - Circuit breakers are protective, not failures
   - Consistent execution > short-term results

4. **Stay Informed**
   - Read README.md thoroughly
   - Understand risk management
   - Know your emergency controls
   - Keep system updated

5. **Manage Expectations**
   - This is not guaranteed profit
   - Losses will happen
   - Circuit breakers will trigger
   - Models will have losing periods

---

## 📋 Pre-Flight Checklist

Before going live, verify:

- [ ] Python 3.10+ installed
- [ ] All dependencies installed (ran install.bat)
- [ ] .env file created and configured
- [ ] All 5 Kraken API keys added
- [ ] Portfolio size set correctly
- [ ] Risk mode selected
- [ ] Kill switch password set
- [ ] Configuration validated (configure.bat)
- [ ] API connectivity tested
- [ ] You understand the risks
- [ ] You can afford to lose this capital
- [ ] You know how to emergency stop
- [ ] You will monitor the system

**All checked? You're ready to trade!**

---

## 🎓 Learning Path

### Week 1: Observation
- Run system with minimum capital
- Watch how signals are generated
- Observe trade execution
- Learn the logs and metrics
- Understand circuit breakers

### Week 2: Understanding
- Review all trades made
- Analyze model decisions
- Study feature importance
- Check risk metrics
- Verify compliance

### Week 3: Optimization
- Adjust risk mode if needed
- Fine-tune parameters
- Monitor model performance
- Analyze profitability
- Plan for scaling

### Week 4+: Scaling
- Increase capital gradually
- Add more pairs (increase UNIVERSE_SIZE)
- Optimize based on results
- Continue monitoring
- Stay disciplined

---

**Remember: Start small, monitor closely, and never risk more than you can afford to lose.**

**This is your live trading system. Use it wisely! 🚀**
