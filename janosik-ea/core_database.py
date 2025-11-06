"""PostgreSQL Database Module for Janosik EA."""
import psycopg2
from psycopg2 import sql
from datetime import datetime, timedelta
import pandas as pd
from config import Config
import logging

logger = logging.getLogger(__name__)


class Database:
    """PostgreSQL connection and operations."""

    def __init__(self):
        """Initialize database connection."""
        self.conn = None
        self.cursor = None
        self.connect()

    def connect(self):
        """Connect to PostgreSQL."""
        try:
            self.conn = psycopg2.connect(Config.DATABASE_URL)
            self.cursor = self.conn.cursor()
            logger.info(f"✅ Connected to PostgreSQL: {Config.DB_NAME}")
        except psycopg2.Error as e:
            logger.error(f"❌ Database connection failed: {e}")
            raise

    def close(self):
        """Close database connection."""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
            logger.info("✅ Database connection closed")

    def execute(self, query, params=None):
        """Execute query."""
        try:
            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)
            self.conn.commit()
            return self.cursor
        except psycopg2.Error as e:
            self.conn.rollback()
            logger.error(f"❌ Query execution failed: {e}")
            raise

    def fetch_one(self, query, params=None):
        """Fetch one row."""
        self.execute(query, params)
        return self.cursor.fetchone()

    def fetch_all(self, query, params=None):
        """Fetch all rows."""
        self.execute(query, params)
        return self.cursor.fetchall()

    def fetch_df(self, query, params=None):
        """Fetch as pandas DataFrame."""
        self.execute(query, params)
        columns = [desc[0] for desc in self.cursor.description]
        data = self.cursor.fetchall()
        return pd.DataFrame(data, columns=columns)

    # ========== MARKET DATA ==========

    def insert_candle(self, symbol: str, timeframe: int, ohlcv: dict):
        """Insert market candle data."""
        query = """
            INSERT INTO market_data
            (symbol, timeframe, open, high, low, close, volume, timestamp)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (timestamp) DO NOTHING
        """
        params = (
            symbol,
            timeframe,
            ohlcv['open'],
            ohlcv['high'],
            ohlcv['low'],
            ohlcv['close'],
            ohlcv['volume'],
            datetime.fromtimestamp(ohlcv['time'])
        )
        self.execute(query, params)

    def get_candles(self, symbol: str, timeframe: int, limit: int = 500):
        """Get last N candles for symbol."""
        query = """
            SELECT timestamp, open, high, low, close, volume
            FROM market_data
            WHERE symbol = %s AND timeframe = %s
            ORDER BY timestamp DESC
            LIMIT %s
        """
        df = self.fetch_df(query, (symbol, timeframe, limit))
        return df.iloc[::-1]  # Reverse to get chronological order

    # ========== TRADES ==========

    def insert_trade(self, trade_data: dict):
        """Insert new trade record."""
        query = """
            INSERT INTO trades
            (strategy_id, symbol, direction, entry_price, entry_time,
             lot_size, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        params = (
            trade_data.get('strategy_id'),
            trade_data.get('symbol'),
            trade_data.get('direction'),  # BUY/SELL
            trade_data.get('entry_price'),
            datetime.now(),
            trade_data.get('lot_size'),
            'OPEN'
        )
        result = self.fetch_one(query, params)
        return result[0] if result else None

    def close_trade(self, trade_id: int, exit_price: float):
        """Close a trade."""
        query = """
            UPDATE trades
            SET exit_price = %s,
                exit_time = %s,
                profit_loss = (exit_price - entry_price) * lot_size,
                profit_pct = ((exit_price - entry_price) / entry_price * 100),
                status = 'CLOSED'
            WHERE id = %s
        """
        self.execute(query, (exit_price, datetime.now(), trade_id))

    def get_open_trades(self, strategy_id: int = None):
        """Get all open trades."""
        if strategy_id:
            query = "SELECT * FROM trades WHERE status = 'OPEN' AND strategy_id = %s"
            return self.fetch_df(query, (strategy_id,))
        else:
            return self.fetch_df("SELECT * FROM trades WHERE status = 'OPEN'")

    def get_daily_trades(self, date=None):
        """Get trades for a specific date."""
        if not date:
            date = datetime.now().date()

        query = """
            SELECT * FROM trades
            WHERE DATE(entry_time) = %s
            ORDER BY entry_time DESC
        """
        return self.fetch_df(query, (date,))

    # ========== STATISTICS ==========

    def insert_daily_stats(self, stats: dict):
        """Insert daily trading statistics."""
        query = """
            INSERT INTO daily_stats
            (date, trades_count, total_pl, win_rate, max_drawdown, daily_loss_pct)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (date) DO UPDATE SET
                trades_count = EXCLUDED.trades_count,
                total_pl = EXCLUDED.total_pl,
                win_rate = EXCLUDED.win_rate,
                max_drawdown = EXCLUDED.max_drawdown,
                daily_loss_pct = EXCLUDED.daily_loss_pct
        """
        params = (
            stats.get('date', datetime.now().date()),
            stats.get('trades_count'),
            stats.get('total_pl'),
            stats.get('win_rate'),
            stats.get('max_drawdown'),
            stats.get('daily_loss_pct')
        )
        self.execute(query, params)

    def get_performance_stats(self, days: int = 30):
        """Get performance stats for last N days."""
        query = """
            SELECT *
            FROM daily_stats
            WHERE date >= NOW() - INTERVAL '%s days'
            ORDER BY date DESC
        """
        return self.fetch_df(query, (days,))

    # ========== STRATEGIES ==========

    def get_active_strategies(self):
        """Get all active strategies."""
        query = "SELECT * FROM strategies WHERE active = TRUE"
        return self.fetch_df(query)

    def get_strategy_by_id(self, strategy_id: int):
        """Get strategy details."""
        query = "SELECT * FROM strategies WHERE id = %s"
        return self.fetch_df(query, (strategy_id,))

    # ========== RL TRAINING ==========

    def log_rl_training(self, episode: int, reward: float, total_profit: float,
                        model_version: str = "v1"):
        """Log RL model training metrics."""
        query = """
            INSERT INTO rl_training
            (episode, reward, total_profit, model_version, timestamp)
            VALUES (%s, %s, %s, %s, %s)
        """
        params = (episode, reward, total_profit, model_version, datetime.now())
        self.execute(query, params)

    def get_rl_history(self, limit: int = 100):
        """Get RL training history."""
        query = """
            SELECT * FROM rl_training
            ORDER BY episode DESC
            LIMIT %s
        """
        return self.fetch_df(query, (limit,))


# ========== SCHEMA CREATION ==========

CREATE_TABLES = """
-- Market Data
CREATE TABLE IF NOT EXISTS market_data (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    timeframe INTEGER NOT NULL,
    open DECIMAL(20, 8) NOT NULL,
    high DECIMAL(20, 8) NOT NULL,
    low DECIMAL(20, 8) NOT NULL,
    close DECIMAL(20, 8) NOT NULL,
    volume INTEGER,
    timestamp TIMESTAMP UNIQUE NOT NULL,
    CONSTRAINT unique_candle UNIQUE (symbol, timeframe, timestamp),
    INDEX (symbol, timeframe, timestamp)
);

-- Strategies
CREATE TABLE IF NOT EXISTS strategies (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    type VARCHAR(50) NOT NULL,
    parameters JSONB,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Trades
CREATE TABLE IF NOT EXISTS trades (
    id SERIAL PRIMARY KEY,
    strategy_id INTEGER REFERENCES strategies(id),
    symbol VARCHAR(20) NOT NULL,
    direction VARCHAR(10) NOT NULL,
    entry_price DECIMAL(20, 8) NOT NULL,
    exit_price DECIMAL(20, 8),
    lot_size DECIMAL(20, 8) NOT NULL,
    profit_loss DECIMAL(20, 8),
    profit_pct DECIMAL(10, 2),
    entry_time TIMESTAMP NOT NULL,
    exit_time TIMESTAMP,
    status VARCHAR(20) DEFAULT 'OPEN',
    INDEX (strategy_id, entry_time)
);

-- Daily Stats
CREATE TABLE IF NOT EXISTS daily_stats (
    id SERIAL PRIMARY KEY,
    date DATE UNIQUE NOT NULL,
    trades_count INTEGER,
    total_pl DECIMAL(20, 8),
    win_rate DECIMAL(5, 2),
    max_drawdown DECIMAL(5, 2),
    daily_loss_pct DECIMAL(5, 2)
);

-- RL Training Log
CREATE TABLE IF NOT EXISTS rl_training (
    id SERIAL PRIMARY KEY,
    episode INTEGER,
    reward DECIMAL(20, 8),
    total_profit DECIMAL(20, 8),
    model_version VARCHAR(50),
    timestamp TIMESTAMP DEFAULT NOW()
);
"""


def setup_database():
    """Initialize database schema."""
    try:
        db = Database()
        db.execute(CREATE_TABLES)
        logger.info("✅ Database schema created/verified")
        db.close()
    except Exception as e:
        logger.error(f"❌ Failed to setup database: {e}")
        raise


if __name__ == "__main__":
    setup_database()
