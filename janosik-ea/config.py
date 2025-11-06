"""Janosik EA Configuration Management."""
import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
load_dotenv()

class Config:
    """Global configuration for Janosik EA."""

    # ========== DATABASE ==========
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", 5432))
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_NAME = os.getenv("DB_NAME", "janosik_trading")

    # PostgreSQL connection string
    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

    # ========== MT5 ==========
    MT5_ACCOUNT = os.getenv("MT5_ACCOUNT", "")
    MT5_PASSWORD = os.getenv("MT5_PASSWORD", "")
    MT5_SERVER = os.getenv("MT5_SERVER", "")

    # Symbols & Timeframes
    SYMBOLS = ["XAUUSD", "NASDAQ"]
    TIMEFRAMES = {
        1: "M1",      # 1 minute
        5: "M5",      # 5 minutes
        15: "M15",    # 15 minutes
        60: "H1",     # 1 hour
        1440: "D1"    # 1 day
    }

    # ========== TRADING ==========
    TRADING_CAPITAL = float(os.getenv("TRADING_CAPITAL", 100000))
    MAX_DAILY_LOSS_PERCENT = float(os.getenv("MAX_DAILY_LOSS_PERCENT", 5))
    DRAWDOWN_SAFE = float(os.getenv("DRAWDOWN_SAFE", 4))
    DRAWDOWN_CAUTION = float(os.getenv("DRAWDOWN_CAUTION", 8))
    DRAWDOWN_CRITICAL = float(os.getenv("DRAWDOWN_CRITICAL", 12))
    MAX_POSITIONS_PER_DAY = int(os.getenv("MAX_POSITIONS_PER_DAY", 3))

    # Position sizing
    POSITION_SIZE_PERCENT = 2  # 2% of capital per trade
    HEDGE_ENABLED = True  # Use both sides strategy

    # ========== RL CONFIGURATION ==========
    RL_LEARNING_RATE = float(os.getenv("RL_LEARNING_RATE", 0.0003))
    RL_BUFFER_SIZE = int(os.getenv("RL_BUFFER_SIZE", 100000))
    RL_BATCH_SIZE = int(os.getenv("RL_BATCH_SIZE", 32))
    RL_MODEL_PATH = os.getenv("RL_MODEL_PATH", "./models/")
    RL_RETRAIN_FREQUENCY = os.getenv("RL_RETRAIN_FREQUENCY", "daily")
    RL_GAMMA = 0.99  # Discount factor
    RL_TAU = 0.005   # Soft update target networks

    # RL Training parameters
    RL_TOTAL_TIMESTEPS = 1_000_000
    RL_LOG_INTERVAL = 10
    RL_SAVE_INTERVAL = 100

    # ========== ALERTS ==========
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
    ALERTS_ENABLED = bool(TELEGRAM_TOKEN and TELEGRAM_CHAT_ID)

    # ========== LOGGING ==========
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_FILE", "./logs/janosik.log")
    LOG_DIR = Path(LOG_FILE).parent
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    # ========== ENVIRONMENT ==========
    ENVIRONMENT = os.getenv("ENVIRONMENT", "demo")  # demo or live
    IS_DEMO = ENVIRONMENT == "demo"
    IS_LIVE = ENVIRONMENT == "live"

    @classmethod
    def validate(cls):
        """Validate critical configuration."""
        errors = []

        if not cls.DB_PASSWORD:
            errors.append("DB_PASSWORD not set in .env")

        if not cls.MT5_ACCOUNT:
            errors.append("MT5_ACCOUNT not set in .env")

        if not cls.IS_DEMO and not cls.IS_LIVE:
            errors.append("ENVIRONMENT must be 'demo' or 'live'")

        if errors:
            raise ValueError(f"Configuration errors:\n" + "\n".join(errors))

        return True

    @classmethod
    def display(cls):
        """Display current configuration."""
        print("\n" + "="*60)
        print("🤖 JANOSIK EA - Configuration")
        print("="*60)
        print(f"Database: {cls.DB_HOST}:{cls.DB_PORT}/{cls.DB_NAME}")
        print(f"MT5 Account: {cls.MT5_ACCOUNT}")
        print(f"Capital: ${cls.TRADING_CAPITAL:,.0f}")
        print(f"Max Daily Loss: {cls.MAX_DAILY_LOSS_PERCENT}%")
        print(f"Drawdown Limits: Safe={cls.DRAWDOWN_SAFE}%, Caution={cls.DRAWDOWN_CAUTION}%, Critical={cls.DRAWDOWN_CRITICAL}%")
        print(f"Max Trades/Day: {cls.MAX_POSITIONS_PER_DAY}")
        print(f"Environment: {cls.ENVIRONMENT.upper()}")
        print(f"RL Model Path: {cls.RL_MODEL_PATH}")
        print("="*60 + "\n")


if __name__ == "__main__":
    Config.display()
