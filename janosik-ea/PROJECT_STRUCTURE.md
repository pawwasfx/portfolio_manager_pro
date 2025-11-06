# 🤖 Janosik EA - Professional Forex Trading Bot

## 📊 Project Specs

- **Name**: Janosik EA (Expert Advisor)
- **Assets**: XAUUSD (Gold), NASDAQ
- **Platform**: MetaTrader 5 (Demo 100k$)
- **Database**: PostgreSQL (Ubuntu)
- **RL Strategy**: Continuous learning (bierząco)
- **Max Trades/Day**: 3 best trades
- **Drawdown Range**: 4%-8%-12% (adjustable)
- **Daily Loss Limit**: 5% max
- **Architecture**: Hybrid (Python Intelligence + MQL5 Execution)

---

## 🏗️ Project Structure

```
janosik-ea/
├── config/
│   ├── settings.py              # Global configuration
│   ├── db_config.py             # PostgreSQL connection
│   ├── mt5_config.py            # MT5 credentials
│   └── trading_params.py        # RL, risk, strategy params
│
├── data/
│   ├── strategies.json          # Strategy definitions
│   ├── backtest_results/        # Historical backtest data
│   └── market_data/             # Downloaded OHLC data
│
├── core/
│   ├── __init__.py
│   ├── mt5_integration.py       # MT5 API wrapper
│   ├── database.py              # PostgreSQL ORM/queries
│   ├── strategy_loader.py       # Load strategies from DB
│   └── position_manager.py      # Track open positions
│
├── trading/
│   ├── __init__.py
│   ├── strategy_engine.py       # Execute all strategies
│   ├── risk_manager.py          # Drawdown, position sizing, limits
│   ├── order_executor.py        # Send orders to MT5
│   └── portfolio.py             # Multi-strategy portfolio logic
│
├── ml/
│   ├── __init__.py
│   ├── environment.py           # Gym environment for RL
│   ├── rl_agent.py             # Stable-Baselines3 (DQN/PPO)
│   ├── reward_shaper.py        # Reward function design
│   └── model_manager.py         # Train/load/save models
│
├── simulator/
│   ├── __init__.py
│   ├── backtest_engine.py      # Run historical backtests
│   ├── paper_trading.py         # Dry-run mode
│   └── performance_metrics.py  # Sharpe, Sortino, Calmar, etc.
│
├── monitoring/
│   ├── __init__.py
│   ├── dashboard.py             # Real-time monitoring
│   ├── logger.py               # Trade logging
│   ├── alerts.py               # Telegram/Email alerts
│   └── performance_tracker.py  # Daily/Weekly P&L
│
├── mql5/
│   ├── Janosik_EA.mq5          # Main Expert Advisor
│   ├── Janosik_Library.mqh     # Include library
│   └── signals/                 # Strategy signal modules
│
├── tests/
│   ├── test_mt5.py
│   ├── test_rl.py
│   ├── test_risk_manager.py
│   └── test_backtest.py
│
├── scripts/
│   ├── setup_db.py             # Initialize PostgreSQL
│   ├── download_history.py     # Get OHLC from MT5
│   ├── train_rl_model.py       # Train RL agent
│   ├── backtest_strategies.py  # Run backtests
│   └── live_trading.py         # Start live trading
│
├── requirements.txt            # Python dependencies
├── README.md                   # Project documentation
├── .env.example               # Environment template
└── janosik_main.py            # Entry point (Coding Agent compatible)
```

---

## 🔄 Data Flow

```
MT5 Terminal
    ↓
(XAUUSD/NASDAQ prices)
    ↓
MT5 Integration Module
    ↓
PostgreSQL
(store candles, trades, results)
    ↓
Strategy Engine (Execute All Strategies)
    ↓
├─→ Traditional Strategies (RSI, MA, etc)
├─→ RL Model (Continuous Learning)
└─→ Ensemble (Portfolio approach)
    ↓
Risk Manager
(Check: drawdown, position size, daily loss limit)
    ↓
Order Executor
    ↓
MT5 Terminal (Place Orders)
    ↓
Monitoring/Dashboard
(Track performance, P&L)
```

---

## 🎯 Key Components

### 1. **PostgreSQL Database Schema**
```sql
-- Strategies table
CREATE TABLE strategies (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    type VARCHAR(50),      -- 'RL', 'MA_Cross', 'RSI', etc
    parameters JSONB,      -- Strategy params
    active BOOLEAN,
    created_at TIMESTAMP
);

-- Market data (OHLC)
CREATE TABLE market_data (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20),    -- XAUUSD, NASDAQ
    timeframe INTEGER,     -- 1 (1M), 5, 15, 60, 1440 (1D)
    open DECIMAL,
    high DECIMAL,
    low DECIMAL,
    close DECIMAL,
    volume INTEGER,
    timestamp TIMESTAMP UNIQUE,
    INDEX (symbol, timeframe, timestamp)
);

-- Trades log
CREATE TABLE trades (
    id SERIAL PRIMARY KEY,
    strategy_id INTEGER,
    symbol VARCHAR(20),
    direction VARCHAR(10),  -- BUY, SELL
    entry_price DECIMAL,
    exit_price DECIMAL,
    lot_size DECIMAL,
    profit_loss DECIMAL,
    profit_pct DECIMAL,
    entry_time TIMESTAMP,
    exit_time TIMESTAMP,
    status VARCHAR(20),     -- OPEN, CLOSED, CANCELLED
    INDEX (strategy_id, entry_time)
);

-- Daily statistics
CREATE TABLE daily_stats (
    id SERIAL PRIMARY KEY,
    date DATE,
    trades_count INTEGER,
    total_pl DECIMAL,
    win_rate DECIMAL,
    max_drawdown DECIMAL,
    daily_loss_pct DECIMAL,
    INDEX (date)
);

-- RL Model training log
CREATE TABLE rl_training (
    id SERIAL PRIMARY KEY,
    episode INTEGER,
    reward DECIMAL,
    total_profit DECIMAL,
    model_version VARCHAR(50),
    timestamp TIMESTAMP
);
```

### 2. **RL Environment (Gym-compatible)**
- **State Space**: [current_price, RSI, MACD, volume, portfolio_balance, open_positions]
- **Action Space**: [BUY_SMALL, BUY_MEDIUM, BUY_LARGE, SELL_SMALL, SELL_MEDIUM, SELL_LARGE, HOLD, CLOSE_ALL]
- **Reward Function**: Profit/Loss + Drawdown penalty + Win rate bonus

### 3. **Risk Manager Logic**
```
Daily Process:
├─ Check daily loss limit (5% max)
├─ Calculate current drawdown vs limits (4-8-12%)
├─ Validate position sizing (Kelly Criterion or fixed %)
├─ Check max 3 good trades/day
├─ Hedge positions (both sides strategy)
└─ Adjust leverage if drawdown approaching limits
```

### 4. **Strategy Portfolio**
- **Traditional**: RSI Crossover, Moving Average, Support/Resistance
- **RL Model**: Learns from rewards, updates daily
- **Ensemble**: Vote-based (majority wins)

---

## 📦 Dependencies

```
# Core
python-dotenv>=1.0.0
psycopg2-binary>=2.9.0     # PostgreSQL
MetaTrader5>=5.0.30         # MT5 API

# ML & RL
stable-baselines3>=1.8.0    # PPO, DQN agents
gymnasium>=0.27.0           # RL environment
numpy>=1.24.0
pandas>=1.5.0
scikit-learn>=1.2.0

# Backtesting & Analysis
backtrader>=1.9.74
ta-lib>=0.4.28              # Technical indicators
plotly>=5.13.0              # Interactive charts

# Monitoring & Logging
python-telegram-bot>=20.0   # Alerts
dash>=2.9.0                 # Dashboard
plotly-dash>=2.9.0
logging-json>=0.2           # Structured logs
```

---

## 🚀 Implementation Phases

### Phase 1: Foundation (Week 1)
- [ ] PostgreSQL setup & schema
- [ ] MT5 integration (read market data)
- [ ] Strategy loader from DB
- [ ] Basic order executor

### Phase 2: RL & Learning (Week 2)
- [ ] Gym environment
- [ ] RL agent (DQN/PPO)
- [ ] Reward function tuning
- [ ] Daily learning loop

### Phase 3: Risk & Execution (Week 3)
- [ ] Risk manager (drawdown, limits)
- [ ] Position sizing (Kelly/Fixed)
- [ ] Order validation & execution
- [ ] Backtester

### Phase 4: Monitoring & Optimization (Week 4)
- [ ] Dashboard (Plotly-Dash)
- [ ] Trade logging
- [ ] Performance analytics
- [ ] Live trading (Demo first)

### Phase 5: MQL5 EA (Week 5)
- [ ] Expert Advisor script
- [ ] Signal communication (Python→MT5)
- [ ] Order placement in MT5
- [ ] Production deployment

---

## 🔐 Security & Best Practices

- ✅ Environment variables for credentials (.env)
- ✅ Paper trading first (no real money)
- ✅ Strict risk limits (drawdown, daily loss)
- ✅ Position sizing by account equity
- ✅ Emergency stop-loss mechanisms
- ✅ Trade logging for audit trail
- ✅ Model versioning & rollback capability
- ✅ Telegram alerts for critical events

---

## 📝 Next Steps

1. **PostgreSQL Configuration** (waiting for your setup)
   - Provide: host, port, user, pass, database name

2. **MT5 Account Setup**
   - Demo account with 100k$ ✅
   - Access to historical data (XAUUSD, NASDAQ)

3. **Strategy Details**
   - Export current strategies from MT5 reports
   - Define RL state/action/reward specs

4. **Start Implementation**
   - Begin with core modules (MT5 integration, DB)
   - Build RL environment
   - Backtest & optimize

---

## 💡 Questions for You

1. **PostgreSQL**: Host, port, user, password, database name?
2. **MT5 Data**: Can we pull minute candles? 1H? 4H? What timeframes for RL?
3. **RL Learning**: How often to retrain? (Daily? Weekly? Each trade?)
4. **Position Sizing**: Fixed % of equity? Or Kelly Criterion?
5. **Traditional Strategies**: What exact parameters? (RSI levels, MA periods, S/R methods?)

Czekam na PostgreSQL access! 🚀
