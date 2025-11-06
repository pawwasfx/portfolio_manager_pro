"""MT5 Integration Module for Janosik EA."""
import MetaTrader5 as mt5
from datetime import datetime, timedelta
import pandas as pd
import logging
from config import Config

logger = logging.getLogger(__name__)


class MT5Manager:
    """MetaTrader 5 connection and operations."""

    def __init__(self):
        """Initialize MT5 connection."""
        self.connected = False
        self.account_info = None
        self.connect()

    def connect(self):
        """Connect to MT5 terminal."""
        try:
            # Initialize MT5 connection
            if not mt5.initialize():
                raise Exception(f"Initialize failed: {mt5.last_error()}")

            # Login to account
            authorized = mt5.login(
                login=int(Config.MT5_ACCOUNT),
                password=Config.MT5_PASSWORD,
                server=Config.MT5_SERVER
            )

            if not authorized:
                raise Exception(f"Login failed: {mt5.last_error()}")

            self.account_info = mt5.account_info()
            self.connected = True
            logger.info(f"✅ MT5 Connected - Account: {Config.MT5_ACCOUNT}")
            self._log_account_info()

        except Exception as e:
            logger.error(f"❌ MT5 Connection failed: {e}")
            raise

    def _log_account_info(self):
        """Log account information."""
        if self.account_info:
            logger.info(f"  Balance: ${self.account_info.balance:,.2f}")
            logger.info(f"  Equity: ${self.account_info.equity:,.2f}")
            logger.info(f"  Free Margin: ${self.account_info.margin_free:,.2f}")
            logger.info(f"  Used Margin: ${self.account_info.margin:,.2f}")

    def disconnect(self):
        """Disconnect from MT5."""
        if self.connected:
            mt5.shutdown()
            self.connected = False
            logger.info("✅ MT5 Disconnected")

    def refresh_account_info(self):
        """Get updated account info."""
        self.account_info = mt5.account_info()
        return self.account_info

    # ========== MARKET DATA ==========

    def get_candles(self, symbol: str, timeframe: int, num_candles: int = 500):
        """
        Get historical candle data.

        Args:
            symbol: e.g., 'XAUUSD', 'NASDAQ'
            timeframe: 1 (M1), 5 (M5), 15 (M15), 60 (H1), 1440 (D1)
            num_candles: number of candles to retrieve

        Returns:
            DataFrame with OHLCV data
        """
        try:
            # Convert timeframe to MT5 timeframe constant
            timeframe_map = {
                1: mt5.TIMEFRAME_M1,
                5: mt5.TIMEFRAME_M5,
                15: mt5.TIMEFRAME_M15,
                60: mt5.TIMEFRAME_H1,
                1440: mt5.TIMEFRAME_D1
            }

            tf = timeframe_map.get(timeframe, mt5.TIMEFRAME_H1)

            # Get candles
            rates = mt5.copy_rates_from_pos(symbol, tf, 0, num_candles)

            if rates is None:
                logger.error(f"❌ Failed to get candles for {symbol}")
                return None

            # Convert to DataFrame
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            df = df[['time', 'open', 'high', 'low', 'close', 'tick_volume']]
            df.columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']

            logger.info(f"✅ Got {len(df)} candles for {symbol}")
            return df

        except Exception as e:
            logger.error(f"❌ Error getting candles: {e}")
            return None

    def get_current_price(self, symbol: str):
        """Get current bid/ask price."""
        try:
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                logger.error(f"❌ Failed to get tick for {symbol}")
                return None

            return {
                'symbol': symbol,
                'bid': tick.bid,
                'ask': tick.ask,
                'time': datetime.fromtimestamp(tick.time)
            }
        except Exception as e:
            logger.error(f"❌ Error getting price: {e}")
            return None

    # ========== ORDERS ==========

    def place_order(self, symbol: str, action: str, lot_size: float, price: float = 0,
                    take_profit: float = 0, stop_loss: float = 0, comment: str = "Janosik EA"):
        """
        Place an order on MT5.

        Args:
            symbol: 'XAUUSD', 'NASDAQ'
            action: 'BUY' or 'SELL'
            lot_size: volume in lots
            price: entry price (0 = market order)
            take_profit: TP price
            stop_loss: SL price
            comment: order comment

        Returns:
            order ticket or None
        """
        try:
            # Validate account equity before trade
            self.refresh_account_info()
            if self.account_info.equity <= 0:
                logger.error("❌ Insufficient equity")
                return None

            # Get symbol info
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info is None:
                logger.error(f"❌ Symbol not found: {symbol}")
                return None

            # If symbol is not visible in market watch, add it
            if not symbol_info.visible:
                if not mt5.symbol_select(symbol, True):
                    logger.error(f"❌ Cannot select symbol: {symbol}")
                    return None

            # Prepare order request
            tick = mt5.symbol_info_tick(symbol)

            action_type = mt5.ORDER_TYPE_BUY if action.upper() == 'BUY' else mt5.ORDER_TYPE_SELL
            price = tick.ask if action.upper() == 'BUY' else tick.bid if price == 0 else price

            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": lot_size,
                "type": action_type,
                "price": price,
                "sl": stop_loss if stop_loss > 0 else 0,
                "tp": take_profit if take_profit > 0 else 0,
                "deviation": 20,
                "magic": 234000,
                "comment": comment,
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }

            # Send order
            result = mt5.order_send(request)

            if result.retcode != mt5.TRADE_RETCODE_DONE:
                logger.error(f"❌ Order failed: {result.comment}")
                return None

            logger.info(f"✅ Order {action} {lot_size} {symbol} @ {price}")
            logger.info(f"   Ticket: {result.order}")
            return result.order

        except Exception as e:
            logger.error(f"❌ Error placing order: {e}")
            return None

    def close_position(self, symbol: str, action: str = None):
        """Close all positions for a symbol."""
        try:
            # Get open positions
            positions = mt5.positions_get(symbol=symbol)

            if not positions:
                logger.info(f"ℹ️  No open positions for {symbol}")
                return []

            closed_tickets = []
            tick = mt5.symbol_info_tick(symbol)

            for position in positions:
                close_action = mt5.ORDER_TYPE_SELL if position.type == 0 else mt5.ORDER_TYPE_BUY
                close_price = tick.bid if close_action == mt5.ORDER_TYPE_SELL else tick.ask

                request = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": symbol,
                    "volume": position.volume,
                    "type": close_action,
                    "position": position.ticket,
                    "price": close_price,
                    "deviation": 20,
                    "magic": 234000,
                    "comment": "Close by Janosik EA",
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": mt5.ORDER_FILLING_IOC,
                }

                result = mt5.order_send(request)

                if result.retcode == mt5.TRADE_RETCODE_DONE:
                    closed_tickets.append(result.order)
                    logger.info(f"✅ Position closed: {position.ticket} ({position.volume} lots)")
                else:
                    logger.error(f"❌ Failed to close {position.ticket}: {result.comment}")

            return closed_tickets

        except Exception as e:
            logger.error(f"❌ Error closing position: {e}")
            return []

    def get_open_positions(self, symbol: str = None):
        """Get all open positions."""
        try:
            if symbol:
                positions = mt5.positions_get(symbol=symbol)
            else:
                positions = mt5.positions_get()

            if not positions:
                return []

            result = []
            for pos in positions:
                result.append({
                    'ticket': pos.ticket,
                    'symbol': pos.symbol,
                    'type': 'BUY' if pos.type == 0 else 'SELL',
                    'volume': pos.volume,
                    'open_price': pos.price_open,
                    'current_price': mt5.symbol_info_tick(pos.symbol).bid,
                    'profit': pos.profit,
                    'profit_pct': (pos.profit / (pos.volume * pos.price_open * 100)) * 100,
                    'open_time': datetime.fromtimestamp(pos.time)
                })

            return result

        except Exception as e:
            logger.error(f"❌ Error getting positions: {e}")
            return []

    def get_account_balance(self):
        """Get current account balance."""
        self.refresh_account_info()
        return {
            'balance': self.account_info.balance,
            'equity': self.account_info.equity,
            'margin_free': self.account_info.margin_free,
            'margin_used': self.account_info.margin,
            'margin_level': self.account_info.margin_level
        }


if __name__ == "__main__":
    # Test MT5 connection
    mt5_manager = MT5Manager()

    # Get candles
    df = mt5_manager.get_candles('XAUUSD', 60, 100)
    print(df.head())

    # Get current price
    price = mt5_manager.get_current_price('XAUUSD')
    print(price)

    # Get account balance
    balance = mt5_manager.get_account_balance()
    print(balance)

    mt5_manager.disconnect()
