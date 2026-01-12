from freqtrade.strategy import IStrategy
from pandas import DataFrame
import talib.abstract as ta


class VolumeMomentumEMA(IStrategy):

    # ===== PARAMÈTRES GÉNÉRAUX =====
    timeframe = '1m'

    # Aucun stop-loss
    stoploss = -1

    # ROI désactivé
    minimal_roi = {
        "0": 100
    }

    # Pas de trailing
    trailing_stop = False

    # Utiliser 100 % du capital
    stake_amount = "unlimited"

    # Pas de protections
    use_exit_signal = False
    exit_profit_only = False
    ignore_roi_if_entry_signal = True

    # Nombre minimum de bougies
    startup_candle_count = 1500

    # ===== INDICATEURS =====
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:

        # EMA prix
        dataframe['ema_60'] = ta.EMA(dataframe['close'], timeperiod=60)
        dataframe['ema_1440'] = ta.EMA(dataframe['close'], timeperiod=1440)

        # EMA volume
        dataframe['ema_volume_1400'] = ta.EMA(dataframe['volume'], timeperiod=1400)

        return dataframe

    # ===== CONDITIONS LONG =====
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:

        dataframe.loc[
            (
                # 1️⃣ Bougie haussière
                (dataframe['close'] > dataframe['open']) &

                # 2️⃣ Explosion de volume
                (dataframe['volume'] > dataframe['ema_volume_1400'] * 10) &

                # 3️⃣ EMA 60 > EMA 1440
                (dataframe['ema_60'] > dataframe['ema_1440']) &

                # 4️⃣ Prix au-dessus EMA 1440
                (dataframe['close'] > dataframe['ema_1440'])
            ),
            'enter_long'
        ] = 1

        # ===== CONDITIONS SHORT =====
        dataframe.loc[
            (
                # 1️⃣ Bougie baissière
                (dataframe['close'] < dataframe['open']) &

                # 2️⃣ Explosion de volume
                (dataframe['volume'] > dataframe['ema_volume_1400'] * 10) &

                # 3️⃣ EMA 60 < EMA 1440
                (dataframe['ema_60'] < dataframe['ema_1440']) &

                # 4️⃣ Prix sous EMA 1440
                (dataframe['close'] < dataframe['ema_1440'])
            ),
            'enter_short'
        ] = 1

        return dataframe

    # ===== AUCUNE SORTIE =====
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        return dataframe
