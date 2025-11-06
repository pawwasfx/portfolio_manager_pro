"""Strategy Management Framework - Portfolio Manager Pro."""
import importlib
import pandas as pd
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
import logging
from database import Database

logger = logging.getLogger(__name__)


class BaseStrategy(ABC):
    """Base class for all strategies."""

    def __init__(self, name: str, symbol: str, timeframe: int, config: dict):
        """Initialize strategy."""
        self.name = name
        self.symbol = symbol
        self.timeframe = timeframe
        self.config = config
        self.enabled = True
        self.last_signal = None
        self.db = Database()

    @abstractmethod
    def calculate_indicators(self, candles: pd.DataFrame) -> Dict:
        """Calculate technical indicators."""
        pass

    @abstractmethod
    def generate_signal(self, indicators: Dict) -> tuple:
        """Generate trading signal (signal, confidence)."""
        pass

    def execute(self, candles: pd.DataFrame) -> Optional[tuple]:
        """Execute strategy on current candles."""
        try:
            # Calculate indicators
            indicators = self.calculate_indicators(candles)

            # Generate signal
            signal, confidence = self.generate_signal(indicators)

            if signal and confidence > 0:
                self.last_signal = {
                    'signal': signal,
                    'confidence': confidence,
                    'indicators': indicators
                }
                logger.info(f"📊 {self.name}: {signal} ({confidence:.2%})")

            return signal, confidence

        except Exception as e:
            logger.error(f"❌ Strategy {self.name} failed: {e}")
            return None, 0

    def get_last_signal(self)):
        """Get last generated signal."""
        return self.last_signal


class RSIStrategy(BaseStrategy):
    """RSI Overbought/Oversold Strategy."""

    def calculate_indicators(self, candles: pd.DataFrame) -> Dict:
        """Calculate RSI."""
        import ta
        close = candles['close'].values
        period = self.config.get('period', 14)

        rsi = ta.momentum.rsi(pd.Series(close), length=period).values

        return {
            'rsi': rsi[-1],
            'close': close[-1]
        }

    def generate_signal(self, indicators: Dict) -> tuple:
        """Generate RSI signal."""
        rsi = indicators['rsi']
        overbought = self.config.get('overbought', 70)
        oversold = self.config.get('oversold', 30)

        if rsi > overbought:
            return 'SELL', min((rsi - overbought) / 30, 1.0)  # Confidence
        elif rsi < oversold:
            return 'BUY', min((oversold - rsi) / 30, 1.0)
        else:
            return 'HOLD', 0


class MAStrategyStrategy(BaseStrategy):
    """Moving Average Crossover Strategy."""

    def calculate_indicators(self, candles: pd.DataFrame) -> Dict:
        """Calculate MA."""
        close = candles['close'].values
        fast = self.config.get('fast', 5)
        slow = self.config.get('slow', 20)

        ma_fast = pd.Series(close).rolling(fast).mean().values[-1]
        ma_slow = pd.Series(close).rolling(slow).mean().values[-1]

        return {
            'ma_fast': ma_fast,
            'ma_slow': ma_slow,
            'close': close[-1]
        }

    def generate_signal(self, indicators: Dict) -> tuple:
        """Generate MA crossover signal."""
        ma_fast = indicators['ma_fast']
        ma_slow = indicators['ma_slow']
        close = indicators['close']

        if ma_fast > ma_slow:
            confidence = min((ma_fast - ma_slow) / close * 100, 1.0)
            return 'BUY', confidence
        elif ma_fast < ma_slow:
            confidence = min((ma_slow - ma_fast) / close * 100, 1.0)
            return 'SELL', confidence
        else:
            return 'HOLD', 0


class StrategyRegistry:
    """Registry for managing strategies."""

    def __init__(self):
        """Initialize registry."""
        self.strategies: Dict[int, BaseStrategy] = {}
        self.db = Database()
        self.load_strategies()

    def load_strategies(self):
        """Load active strategies from database."""
        try:
            active_strategies = self.db.get_active_strategies()

            for _, row in active_strategies.iterrows():
                strategy_id = row['id']
                strategy_type = row['type']
                config = row['config']

                # Instantiate strategy based on type
                if strategy_type == 'RSI':
                    strategy = RSIStrategy(
                        name=row['name'],
                        symbol=config.get('symbol', 'XAUUSD'),
                        timeframe=config.get('timeframe', 60),
                        config=config
                    )
                elif strategy_type == 'MA':
                    strategy = MAStrategyStrategy(
                        name=row['name'],
                        symbol=config.get('symbol', 'XAUUSD'),
                        timeframe=config.get('timeframe', 60),
                        config=config
                    )
                else:
                    logger.warning(f"Unknown strategy type: {strategy_type}")
                    continue

                self.strategies[strategy_id] = strategy
                logger.info(f"✅ Loaded strategy: {row['name']} (ID: {strategy_id})")

        except Exception as e:
            logger.error(f"❌ Failed to load strategies: {e}")

    def add_strategy(self, strategy: BaseStrategy) -> int:
        """Register new strategy."""
        # Save to database
        config = strategy.config.copy()
        config['symbol'] = strategy.symbol
        config['timeframe'] = strategy.timeframe

        strategy_id = self.db.register_strategy(
            name=strategy.name,
            strategy_type=strategy.__class__.__name__,
            config=config
        )

        self.strategies[strategy_id] = strategy
        return strategy_id

    def execute_all(self, candles_dict: Dict[str, pd.DataFrame]) -> List[Dict]:
        """Execute all active strategies."""
        signals = []

        for strategy_id, strategy in self.strategies.items():
            try:
                # Get candles for this strategy's symbol
                candles = candles_dict.get(strategy.symbol)
                if candles is None or len(candles) == 0:
                    continue

                # Execute strategy
                signal, confidence = strategy.execute(candles)

                if signal:
                    signals.append({
                        'strategy_id': strategy_id,
                        'strategy_name': strategy.name,
                        'symbol': strategy.symbol,
                        'signal': signal,
                        'confidence': confidence
                    })

            except Exception as e:
                logger.error(f"❌ Error executing strategy {strategy_id}: {e}")

        return signals

    def get_strategy_performance(self, strategy_id: int) -> Dict:
        """Get strategy performance metrics."""
        # Get trades for this strategy
        trades_df = self.db.get_df(
            "SELECT * FROM trades WHERE strategy_id = %s AND status = 'CLOSED' ORDER BY exit_time DESC LIMIT 50",
            (strategy_id,)
        )

        if len(trades_df) == 0:
            return {}

        total_trades = len(trades_df)
        winning_trades = len(trades_df[trades_df['profit_loss'] > 0])
        losing_trades = total_trades - winning_trades

        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': winning_trades / total_trades if total_trades > 0 else 0,
            'total_profit': trades_df['profit_loss'].sum(),
            'avg_profit': trades_df['profit_loss'].mean(),
            'max_profit': trades_df['profit_loss'].max(),
            'max_loss': trades_df['profit_loss'].min()
        }

    def disable_underperformers(self, win_rate_threshold: float = 0.4):
        """Disable strategies with poor performance."""
        for strategy_id, strategy in list(self.strategies.items()):
            perf = self.get_strategy_performance(strategy_id)

            if perf and perf.get('win_rate', 0) < win_rate_threshold:
                logger.warning(f"⚠️  Disabling {strategy.name} (win rate: {perf['win_rate']:.1%})")
                self.db.disable_strategy(strategy_id)
                strategy.enabled = False

    def adjust_allocations(self, performance_scores: Dict[int, float]):
        """Adjust strategy allocations based on performance."""
        # Normalize scores
        total_score = sum(performance_scores.values())
        if total_score <= 0:
            return

        for strategy_id, score in performance_scores.items():
            allocation = (score / total_score) * 100
            self.db.update_strategy_allocation(strategy_id, allocation)
            logger.info(f"✅ {strategy_id} allocation: {allocation:.1f}%")


class StrategyExecutor:
    """Execute strategies and combine signals."""

    def __init__(self):
        """Initialize executor."""
        self.registry = StrategyRegistry()
        self.db = Database()

    def execute_round(self, market_data: Dict[str, pd.DataFrame]) -> Dict:
        """Execute all strategies and combine signals."""
        # Execute all strategies
        signals = self.registry.execute_all(market_data)

        if not signals:
            return {'combined_signal': 'HOLD', 'signals': []}

        # Combine signals using ensemble voting
        combined_signal = self._combine_signals(signals)

        logger.info(f"📊 Combined signal: {combined_signal}")

        return {
            'combined_signal': combined_signal,
            'signals': signals,
            'timestamp': pd.Timestamp.now()
        }

    def _combine_signals(self, signals: List[Dict]) -> str:
        """Combine signals using voting."""
        buy_votes = sum(1 for s in signals if s['signal'] == 'BUY')
        sell_votes = sum(1 for s in signals if s['signal'] == 'SELL')
        hold_votes = sum(1 for s in signals if s['signal'] == 'HOLD')

        total = len(signals)

        # Majority voting
        if buy_votes > total / 2:
            return 'BUY'
        elif sell_votes > total / 2:
            return 'SELL'
        else:
            return 'HOLD'


if __name__ == "__main__":
    # Test
    registry = StrategyRegistry()
    print(f"Loaded {len(registry.strategies)} strategies")
