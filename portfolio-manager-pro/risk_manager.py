"""Risk Management System - Portfolio Level."""
import pandas as pd
from typing import Dict, List, Optional, Tuple
import logging
import numpy as np
from config import settings
from database import Database

logger = logging.getLogger(__name__)


class RiskManager:
    """Portfolio-level risk management."""

    def __init__(self):
        """Initialize risk manager."""
        self.db = Database()
        self.current_equity = settings.INITIAL_CAPITAL
        self.peak_equity = settings.INITIAL_CAPITAL
        self.current_drawdown = 0

    def update_equity(self, new_equity: float):
        """Update current equity."""
        self.current_equity = new_equity

        # Update peak equity
        if new_equity > self.peak_equity:
            self.peak_equity = new_equity

        # Calculate drawdown
        self.current_drawdown = (self.peak_equity - new_equity) / self.peak_equity * 100

    def validate_trade(self, symbol: str, direction: str, lot_size: float,
                      entry_price: float) -> Tuple[bool, str]:
        """Validate if trade can be executed."""
        validations = []

        # 1. Check drawdown limit
        if not self._check_drawdown_limit():
            return False, "❌ Drawdown limit exceeded"

        # 2. Check daily loss limit
        daily_loss = self._get_daily_loss()
        daily_loss_pct = (daily_loss / settings.INITIAL_CAPITAL) * 100
        if daily_loss_pct > settings.MAX_DAILY_LOSS_PCT:
            return False, f"❌ Daily loss limit exceeded ({daily_loss_pct:.2f}%)"

        # 3. Check open positions limit
        open_positions = self.db.fetch_df("SELECT COUNT(*) FROM positions").values[0][0]
        if open_positions >= 10:  # Max 10 open positions
            return False, "❌ Maximum open positions reached"

        # 4. Check correlation with existing positions
        if not self._check_correlation(symbol):
            return False, "❌ Correlation limit exceeded"

        # 5. Check position size
        max_position = self._calculate_max_position_size(entry_price)
        if lot_size > max_position:
            return False, f"❌ Position size too large (max: {max_position:.2f} lots)"

        return True, "✅ Trade validated"

    def _check_drawdown_limit(self) -> bool:
        """Check if drawdown is within limits."""
        if self.current_drawdown > settings.DRAWDOWN_CRITICAL:
            logger.warning(f"🚨 CRITICAL drawdown: {self.current_drawdown:.2f}%")
            return False

        if self.current_drawdown > settings.DRAWDOWN_CAUTION:
            logger.warning(f"⚠️  CAUTION drawdown: {self.current_drawdown:.2f}%")

        return True

    def _get_daily_loss(self) -> float:
        """Get daily P&L."""
        today_trades = self.db.fetch_df("""
            SELECT SUM(profit_loss) as total_pl
            FROM trades
            WHERE DATE(entry_time) = CURRENT_DATE AND status = 'CLOSED'
        """)

        return today_trades['total_pl'].values[0] if len(today_trades) > 0 else 0

    def _check_correlation(self, symbol: str) -> bool:
        """Check if symbol correlation is within limits."""
        positions = self.db.fetch_df("SELECT symbol FROM positions")

        if len(positions) == 0:
            return True

        # Get price series
        current_symbol_prices = self._get_symbol_prices(symbol, 20)

        for _, row in positions.iterrows():
            other_symbol = row['symbol']
            other_prices = self._get_symbol_prices(other_symbol, 20)

            # Calculate correlation
            if len(current_symbol_prices) > 0 and len(other_prices) > 0:
                correlation = np.corrcoef(current_symbol_prices, other_prices)[0, 1]

                if abs(correlation) > settings.MAX_CORRELATION:
                    logger.warning(f"⚠️  High correlation between {symbol} and {other_symbol}: {correlation:.2f}")
                    return False

        return True

    def _get_symbol_prices(self, symbol: str, periods: int = 20) -> np.ndarray:
        """Get last N prices for symbol."""
        df = self.db.fetch_df("""
            SELECT close FROM market_data
            WHERE symbol = %s AND timeframe = %s
            ORDER BY timestamp DESC
            LIMIT %s
        """, (symbol, settings.DEFAULT_TIMEFRAME, periods))

        return df['close'].values[::-1] if len(df) > 0 else np.array([])

    def _calculate_max_position_size(self, entry_price: float) -> float:
        """Calculate maximum position size."""
        if settings.POSITION_SIZING == 'fixed':
            return settings.FIXED_LOT_SIZE

        elif settings.POSITION_SIZING == 'kelly':
            # Kelly Criterion: f = (bp - q) / b
            # Simplified: Kelly % = Win% - Loss% / Win/Loss Ratio
            return self._calculate_kelly_position()

        elif settings.POSITION_SIZING == 'adaptive':
            # Scale down as drawdown increases
            scale = 1 - (self.current_drawdown / settings.DRAWDOWN_CRITICAL)
            return settings.FIXED_LOT_SIZE * max(scale, 0.1)

        return settings.FIXED_LOT_SIZE

    def _calculate_kelly_position(self) -> float:
        """Calculate Kelly Criterion position size."""
        recent_trades = self.db.fetch_df("""
            SELECT profit_loss, ABS(profit_loss) as abs_pl
            FROM trades
            WHERE status = 'CLOSED'
            ORDER BY exit_time DESC
            LIMIT 30
        """)

        if len(recent_trades) < 5:
            return settings.FIXED_LOT_SIZE

        wins = len(recent_trades[recent_trades['profit_loss'] > 0])
        losses = len(recent_trades[recent_trades['profit_loss'] < 0])
        total = wins + losses

        win_rate = wins / total if total > 0 else 0
        loss_rate = losses / total if total > 0 else 0

        if win_rate == 0 or loss_rate == 0:
            return settings.FIXED_LOT_SIZE

        avg_win = recent_trades[recent_trades['profit_loss'] > 0]['profit_loss'].mean()
        avg_loss = abs(recent_trades[recent_trades['profit_loss'] < 0]['profit_loss'].mean())

        if avg_loss == 0:
            return settings.FIXED_LOT_SIZE

        # Kelly formula
        kelly_pct = (win_rate * avg_win - loss_rate * avg_loss) / avg_win

        # Apply Kelly fraction (usually 0.25 for safety)
        kelly_pct = kelly_pct * settings.KELLY_FRACTION

        # Convert to lot size (assume 1 lot = 1% risk)
        lot_size = kelly_pct * 100

        return max(min(lot_size, settings.FIXED_LOT_SIZE * 2), 0.1)

    def get_risk_metrics(self) -> Dict:
        """Get current risk metrics."""
        positions = self.db.fetch_df("SELECT * FROM positions")
        total_position_value = (positions['lot_size'] * positions['entry_price']).sum() if len(positions) > 0 else 0

        return {
            'current_equity': self.current_equity,
            'current_drawdown': self.current_drawdown,
            'drawdown_level': self._get_drawdown_level(),
            'daily_loss_pct': (self._get_daily_loss() / settings.INITIAL_CAPITAL) * 100,
            'open_positions': len(positions),
            'total_position_value': total_position_value,
            'margin_utilization': (total_position_value / self.current_equity * 100) if self.current_equity > 0 else 0
        }

    def _get_drawdown_level(self) -> str:
        """Get drawdown level description."""
        if self.current_drawdown > settings.DRAWDOWN_CRITICAL:
            return "🚨 CRITICAL"
        elif self.current_drawdown > settings.DRAWDOWN_CAUTION:
            return "⚠️  CAUTION"
        elif self.current_drawdown > settings.DRAWDOWN_SAFE:
            return "⚠️  WARNING"
        else:
            return "✅ SAFE"

    def check_stop_conditions(self) -> bool:
        """Check if trading should be stopped."""
        # Check critical drawdown
        if self.current_drawdown > settings.DRAWDOWN_CRITICAL:
            logger.error("🚨 STOPPING: Critical drawdown reached")
            return True

        # Check daily loss
        daily_loss = self._get_daily_loss()
        if daily_loss < -(settings.MAX_DAILY_LOSS_PCT / 100 * settings.INITIAL_CAPITAL):
            logger.error("🚨 STOPPING: Daily loss limit exceeded")
            return True

        return False


class PositionManager:
    """Manage open positions."""

    def __init__(self):
        """Initialize position manager."""
        self.db = Database()
        self.risk_mgr = RiskManager()

    def open_position(self, strategy_id: int, symbol: str, direction: str,
                     lot_size: float, entry_price: float,
                     stop_loss: float = 0, take_profit: float = 0) -> Optional[int]:
        """Open new position."""
        # Validate trade
        is_valid, msg = self.risk_mgr.validate_trade(symbol, direction, lot_size, entry_price)

        if not is_valid:
            logger.error(msg)
            return None

        logger.info(f"✅ {msg}")

        # Insert position
        position_id = self.db.insert_position(strategy_id, symbol, direction, lot_size, entry_price)

        # Insert trade
        trade_id = self.db.insert_trade(strategy_id, symbol, direction, entry_price, lot_size)

        logger.info(f"✅ Position opened: {direction} {lot_size} {symbol} @ {entry_price}")

        return position_id

    def close_position(self, position_id: int, exit_price: float):
        """Close position."""
        # Get position
        pos = self.db.fetch_one("SELECT id FROM positions WHERE id = %s", (position_id,))

        if not pos:
            logger.error(f"Position {position_id} not found")
            return

        # Close associated trade
        self.db.close_trade(position_id, exit_price)

        # Remove position
        self.db.execute("DELETE FROM positions WHERE id = %s", (position_id,))

        logger.info(f"✅ Position {position_id} closed @ {exit_price}")

    def update_positions_prices(self, prices: Dict[str, float]):
        """Update all positions with current prices."""
        positions = self.db.fetch_df("SELECT id, symbol FROM positions")

        for _, pos in positions.iterrows():
            symbol = pos['symbol']
            if symbol in prices:
                self.db.update_position_price(pos['id'], prices[symbol])


if __name__ == "__main__":
    risk_mgr = RiskManager()
    print(risk_mgr.get_risk_metrics())
