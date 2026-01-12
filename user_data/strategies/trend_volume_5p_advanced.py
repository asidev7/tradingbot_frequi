from freqtrade.strategy.interface import IStrategy
from pandas import DataFrame
import talib.abstract as ta
import numpy as np

class TrendVolume5pAdvanced(IStrategy):
    """
    ╔════════════════════════════════════════════════════════════╗
    ║ STRATÉGIE TRADING AVANCÉE - BYBIT USDT PERPETUAL / SPOT   ║
    ║ Timeframe: 5m                                             ║
    ║ Supports: LONG uniquement pour Spot                       ║
    ║ Max open trades: 10                                       ║
    ║ Stop Loss: -4%, ROI dynamique, trailing stop optional     ║
    ║ Indicateurs: EMA, SMA, RSI, MACD, Bollinger, ADX, ATR    ║
    ╚════════════════════════════════════════════════════════════╝
    """

    INTERFACE_VERSION = 3
    timeframe = '5m'
    can_short = False  # ⚠️ Spot ne supporte pas les shorts
    startup_candle_count = 200

    # Position et risque
    stake_currency = 'USDT'
    stake_amount = 'unlimited'
    max_open_trades = 10

    # Stop loss et trailing
    stoploss = -0.04
    trailing_stop = True
    trailing_stop_positive = 0.02
    trailing_stop_positive_offset = 0.03
    trailing_only_offset_is_reached = True

    # ROI dynamique
    minimal_roi = {
        "0": 0.08,
        "15": 0.05,
        "30": 0.03,
        "60": 0.015,
        "120": 0.01
    }

    use_exit_signal = True
    exit_profit_only = False
    exit_profit_offset = 0.01
    ignore_roi_if_entry_signal = False

    # ─── UTILITAIRES ───
    def crossed_above(self, series1, series2):
        return (series1 > series2) & (series1.shift(1) <= series2.shift(1))

    def crossed_below(self, series1, series2):
        return (series1 < series2) & (series1.shift(1) >= series2.shift(1))

    def bollinger_bands(self, close, window=20, stds=2):
        ma = close.rolling(window=window).mean()
        std = close.rolling(window=window).std()
        return {
            'lower': ma - (std * stds),
            'mid': ma,
            'upper': ma + (std * stds)
        }

    # ─── INDICATEURS ───
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # EMA / SMA
        dataframe['ema5'] = ta.EMA(dataframe, timeperiod=5)
        dataframe['ema10'] = ta.EMA(dataframe, timeperiod=10)
        dataframe['ema20'] = ta.EMA(dataframe, timeperiod=20)
        dataframe['ema50'] = ta.EMA(dataframe, timeperiod=50)
        dataframe['ema100'] = ta.EMA(dataframe, timeperiod=100)
        dataframe['ema200'] = ta.EMA(dataframe, timeperiod=200)
        dataframe['sma20'] = ta.SMA(dataframe, timeperiod=20)
        dataframe['sma50'] = ta.SMA(dataframe, timeperiod=50)

        # RSI
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        dataframe['rsi_fast'] = ta.RSI(dataframe, timeperiod=7)
        dataframe['rsi_slow'] = ta.RSI(dataframe, timeperiod=21)

        # MACD
        macd = ta.MACD(dataframe)
        dataframe['macd'] = macd['macd']
        dataframe['macdsignal'] = macd['macdsignal']
        dataframe['macdhist'] = macd['macdhist']
        dataframe['macd_cross_up'] = self.crossed_above(dataframe['macd'], dataframe['macdsignal'])
        dataframe['macd_cross_down'] = self.crossed_below(dataframe['macd'], dataframe['macdsignal'])

        # Bollinger
        bollinger = self.bollinger_bands(dataframe['close'])
        dataframe['bb_lower'] = bollinger['lower']
        dataframe['bb_middle'] = bollinger['mid']
        dataframe['bb_upper'] = bollinger['upper']
        dataframe['bb_width'] = (dataframe['bb_upper'] - dataframe['bb_lower']) / dataframe['bb_middle']
        dataframe['bb_percent'] = (dataframe['close'] - dataframe['bb_lower']) / (dataframe['bb_upper'] - dataframe['bb_lower'])

        # ADX
        dataframe['adx'] = ta.ADX(dataframe, timeperiod=14)
        dataframe['plus_di'] = ta.PLUS_DI(dataframe, timeperiod=14)
        dataframe['minus_di'] = ta.MINUS_DI(dataframe, timeperiod=14)

        # Stochastic
        stoch = ta.STOCH(dataframe)
        dataframe['slowk'] = stoch['slowk']
        dataframe['slowd'] = stoch['slowd']

        # ATR
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
        dataframe['atr_percent'] = (dataframe['atr'] / dataframe['close']) * 100

        # Volume
        dataframe['volume_mean'] = dataframe['volume'].rolling(20).mean()
        dataframe['volume_std'] = dataframe['volume'].rolling(20).std()
        dataframe['volume_spike'] = dataframe['volume'] > (dataframe['volume_mean'] + 2 * dataframe['volume_std'])
        dataframe['obv'] = ta.OBV(dataframe)
        dataframe['obv_ema'] = ta.EMA(dataframe['obv'], timeperiod=20)

        # Pivot points
        dataframe['pivot'] = (dataframe['high'] + dataframe['low'] + dataframe['close']) / 3
        dataframe['r1'] = 2 * dataframe['pivot'] - dataframe['low']
        dataframe['s1'] = 2 * dataframe['pivot'] - dataframe['high']

        # Price momentum
        dataframe['price_momentum'] = ((dataframe['close'] - dataframe['close'].shift(5)) / dataframe['close'].shift(5)) * 100

        return dataframe

    # ─── SIGNALS LONG ───
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        conditions_long = []

        # Tendance haussière
        conditions_long.append(dataframe['ema10'] > dataframe['ema50'])
        conditions_long.append(dataframe['ema20'] > dataframe['ema50'])
        conditions_long.append(dataframe['adx'] > 25)
        conditions_long.append(dataframe['plus_di'] > dataframe['minus_di'])
        conditions_long.append(dataframe['rsi'] > 40)
        conditions_long.append(dataframe['rsi'] < 75)
        conditions_long.append(dataframe['rsi_fast'] > dataframe['rsi_slow'])
        conditions_long.append((dataframe['macd'] > dataframe['macdsignal']) | dataframe['macd_cross_up'])
        conditions_long.append(dataframe['macdhist'] > 0)
        conditions_long.append(dataframe['volume'] > dataframe['volume_mean'] * 1.2)
        conditions_long.append(dataframe['bb_percent'] > 0.3)
        conditions_long.append(dataframe['bb_percent'] < 0.9)
        conditions_long.append(dataframe['slowk'] > 20)
        conditions_long.append(dataframe['slowk'] < 80)
        conditions_long.append(dataframe['slowk'] > dataframe['slowd'])
        conditions_long.append(dataframe['obv'] > dataframe['obv_ema'])
        conditions_long.append(dataframe['price_momentum'] > -2)
        conditions_long.append(dataframe['close'] > dataframe['s1'])

        if conditions_long:
            dataframe.loc[np.array(conditions_long).all(axis=0), 'enter_long'] = 1

        return dataframe

    # ─── SORTIE LONG ───
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        conditions_exit_long = []

        conditions_exit_long.append(
            (dataframe['ema10'] < dataframe['ema20']) |
            (dataframe['rsi'] > 75) |
            (dataframe['macd_cross_down']) |
            (dataframe['close'] > dataframe['bb_upper']) |
            ((dataframe['slowk'] > 80) & (dataframe['slowk'] < dataframe['slowd'])) |
            ((dataframe['adx'] > 30) & (dataframe['minus_di'] > dataframe['plus_di'])) |
            (dataframe['price_momentum'] < -3)
        )

        if conditions_exit_long:
            dataframe.loc[np.array(conditions_exit_long).any(axis=0), 'exit_long'] = 1

        return dataframe

    # ─── STOP LOSS DYNAMIQUE ATR ───
    def custom_stoploss(self, pair: str, trade, current_time, current_rate: float, current_profit: float, **kwargs) -> float:
        try:
            dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
            last_candle = dataframe.iloc[-1].squeeze()
            atr_sl = last_candle['atr'] * 2
            atr_sl_percent = atr_sl / current_rate
            return max(self.stoploss, -atr_sl_percent)
        except Exception:
            return self.stoploss
