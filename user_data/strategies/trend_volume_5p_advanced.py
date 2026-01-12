from freqtrade.strategy.interface import IStrategy
from pandas import DataFrame
import talib.abstract as ta
import numpy as np

class TrendVolume5pAdvanced(IStrategy):
    """
    STRATÉGIE TRADING AVANCÉE - BYBIT USDT PERPETUAL 5M
    Multi-indicateurs: EMA, RSI, MACD, Bollinger, ADX, Stochastic
    Take Profit adaptatif: 8% → 5% → 3% → 1.5%
    Stop Loss intelligent: 4% fixe + Trailing Stop
    Support Long & Short avec 10+ conditions
    Gestion de risque avancée avec ATR dynamique
    """

    INTERFACE_VERSION = 3
    timeframe = '5m'
    can_short = True
    startup_candle_count = 200

    # GESTION DES POSITIONS
    stake_amount = 'unlimited'
    stake_currency = 'USDT'
    max_open_trades = 3
    position_adjustment_enable = False

    # STOP LOSS
    stoploss = -0.04
    trailing_stop = True
    trailing_stop_positive = 0.02
    trailing_stop_positive_offset = 0.03
    trailing_only_offset_is_reached = True

    # TAKE PROFIT ADAPTATIF
    minimal_roi = {
        "0": 0.08,
        "15": 0.05,
        "30": 0.03,
        "60": 0.015,
        "120": 0.01
    }

    # SIGNAUX DE SORTIE
    use_exit_signal = True
    exit_profit_only = False
    exit_profit_offset = 0.01
    ignore_roi_if_entry_signal = False

    # FONCTIONS UTILITAIRES
    def crossed_above(self, series1, series2):
        return (series1 > series2) & (series1.shift(1) <= series2.shift(1))

    def crossed_below(self, series1, series2):
        return (series1 < series2) & (series1.shift(1) >= series2.shift(1))

    def bollinger_bands(self, close, window=20, stds=2):
        ma = close.rolling(window=window).mean()
        std = close.rolling(window=window).std()
        return {'lower': ma - (std * stds), 'mid': ma, 'upper': ma + (std * stds)}

    # POPULATE INDICATORS
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['ema5'] = ta.EMA(dataframe, timeperiod=5)
        dataframe['ema10'] = ta.EMA(dataframe, timeperiod=10)
        dataframe['ema20'] = ta.EMA(dataframe, timeperiod=20)
        dataframe['ema50'] = ta.EMA(dataframe, timeperiod=50)
        dataframe['ema100'] = ta.EMA(dataframe, timeperiod=100)
        dataframe['ema200'] = ta.EMA(dataframe, timeperiod=200)
        dataframe['sma20'] = ta.SMA(dataframe, timeperiod=20)
        dataframe['sma50'] = ta.SMA(dataframe, timeperiod=50)

        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        dataframe['rsi_fast'] = ta.RSI(dataframe, timeperiod=7)
        dataframe['rsi_slow'] = ta.RSI(dataframe, timeperiod=21)

        macd = ta.MACD(dataframe)
        dataframe['macd'] = macd['macd']
        dataframe['macdsignal'] = macd['macdsignal']
        dataframe['macdhist'] = macd['macdhist']
        dataframe['macd_cross_up'] = self.crossed_above(dataframe['macd'], dataframe['macdsignal'])
        dataframe['macd_cross_down'] = self.crossed_below(dataframe['macd'], dataframe['macdsignal'])

        bollinger = self.bollinger_bands(dataframe['close'])
        dataframe['bb_lower'] = bollinger['lower']
        dataframe['bb_middle'] = bollinger['mid']
        dataframe['bb_upper'] = bollinger['upper']
        dataframe['bb_width'] = (dataframe['bb_upper'] - dataframe['bb_lower']) / dataframe['bb_middle']
        dataframe['bb_percent'] = (dataframe['close'] - dataframe['bb_lower']) / (dataframe['bb_upper'] - dataframe['bb_lower'])

        dataframe['adx'] = ta.ADX(dataframe, timeperiod=14)
        dataframe['plus_di'] = ta.PLUS_DI(dataframe, timeperiod=14)
        dataframe['minus_di'] = ta.MINUS_DI(dataframe, timeperiod=14)

        stoch = ta.STOCH(dataframe)
        dataframe['slowk'] = stoch['slowk']
        dataframe['slowd'] = stoch['slowd']

        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
        dataframe['atr_percent'] = dataframe['atr'] / dataframe['close'] * 100

        dataframe['volume_mean'] = dataframe['volume'].rolling(20).mean()
        dataframe['volume_std'] = dataframe['volume'].rolling(20).std()
        dataframe['volume_spike'] = dataframe['volume'] > (dataframe['volume_mean'] + 2 * dataframe['volume_std'])

        dataframe['obv'] = ta.OBV(dataframe)
        dataframe['obv_ema'] = ta.EMA(dataframe['obv'], timeperiod=20)

        dataframe['pivot'] = (dataframe['high'] + dataframe['low'] + dataframe['close']) / 3
        dataframe['r1'] = 2 * dataframe['pivot'] - dataframe['low']
        dataframe['s1'] = 2 * dataframe['pivot'] - dataframe['high']

        dataframe['price_momentum'] = (dataframe['close'] - dataframe['close'].shift(5)) / dataframe['close'].shift(5) * 100

        return dataframe

    # ENTRY
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # LONG
        conditions_long = [
            dataframe['close'] > dataframe['ema50'],
            dataframe['ema10'] > dataframe['ema50'],
            dataframe['ema20'] > dataframe['ema50'],
            dataframe['adx'] > 25,
            dataframe['plus_di'] > dataframe['minus_di'],
            dataframe['rsi'].between(40,75),
            dataframe['rsi_fast'] > dataframe['rsi_slow'],
            (dataframe['macd'] > dataframe['macdsignal']) | dataframe['macd_cross_up'],
            dataframe['macdhist'] > 0,
            dataframe['volume'] > dataframe['volume_mean']*1.2,
            dataframe['bb_percent'].between(0.3,0.9),
            dataframe['slowk'].between(20,80),
            dataframe['slowk'] > dataframe['slowd'],
            dataframe['obv'] > dataframe['obv_ema'],
            dataframe['price_momentum'] > -2,
            dataframe['close'] > dataframe['s1']
        ]
        dataframe.loc[np.array(conditions_long).all(axis=0), 'enter_long'] = 1

        # SHORT
        conditions_short = [
            dataframe['close'] < dataframe['ema50'],
            dataframe['ema10'] < dataframe['ema50'],
            dataframe['ema20'] < dataframe['ema50'],
            dataframe['adx'] > 25,
            dataframe['minus_di'] > dataframe['plus_di'],
            dataframe['rsi'].between(25,60),
            dataframe['rsi_fast'] < dataframe['rsi_slow'],
            (dataframe['macd'] < dataframe['macdsignal']) | dataframe['macd_cross_down'],
            dataframe['macdhist'] < 0,
            dataframe['volume'] > dataframe['volume_mean']*1.2,
            dataframe['bb_percent'].between(0.1,0.7),
            dataframe['slowk'].between(20,80),
            dataframe['slowk'] < dataframe['slowd'],
            dataframe['obv'] < dataframe['obv_ema'],
            dataframe['price_momentum'] < 2,
            dataframe['close'] < dataframe['r1']
        ]
        dataframe.loc[np.array(conditions_short).all(axis=0), 'enter_short'] = 1
        return dataframe

    # EXIT
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        exit_long_conditions = [
            (dataframe['ema10'] < dataframe['ema20']) |
            (dataframe['rsi'] > 75) |
            dataframe['macd_cross_down'] |
            (dataframe['close'] > dataframe['bb_upper']) |
            ((dataframe['slowk'] > 80) & (dataframe['slowk'] < dataframe['slowd'])) |
            ((dataframe['adx'] > 30) & (dataframe['minus_di'] > dataframe['plus_di'])) |
            (dataframe['price_momentum'] < -3)
        ]
        dataframe.loc[np.array(exit_long_conditions).any(axis=0), 'exit_long'] = 1

        exit_short_conditions = [
            (dataframe['ema10'] > dataframe['ema20']) |
            (dataframe['rsi'] < 25) |
            dataframe['macd_cross_up'] |
            (dataframe['close'] < dataframe['bb_lower']) |
            ((dataframe['slowk'] < 20) & (dataframe['slowk'] > dataframe['slowd'])) |
            ((dataframe['adx'] > 30) & (dataframe['plus_di'] > dataframe['minus_di'])) |
            (dataframe['price_momentum'] > 3)
        ]
        dataframe.loc[np.array(exit_short_conditions).any(axis=0), 'exit_short'] = 1
        return dataframe

    # CUSTOM STOPLOSS
    def custom_stoploss(self, pair: str, trade, current_time, current_rate: float,
                        current_profit: float, **kwargs) -> float:
        try:
            dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
            last_candle = dataframe.iloc[-1]
            atr_sl_percent = (last_candle['atr'] * 2) / current_rate
            return max(self.stoploss, -atr_sl_percent)
        except Exception:
            return self.stoploss
