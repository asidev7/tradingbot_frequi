from freqtrade.strategy.interface import IStrategy
from pandas import DataFrame

class ShortAllPairsNoCondition(IStrategy):
    """
    🔥 STRATÉGIE FUTURES – SHORT SANS CONDITION 🔥

    - Compatible Freqtrade 2025+
    - Short uniquement
    - Trade toutes les paires disponibles
    - Aucun indicateur
    """

    timeframe = "5m"

    stoploss = -0.04

    minimal_roi = {
        "0": 0.05
    }

    trailing_stop = False
    max_open_trades = 5

    can_short = True   # OBLIGATOIRE POUR FUTURES

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Aucun indicateur
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        🔻 ENTRY SHORT
        Signal permanent → short sur toutes les paires
        """
        dataframe.loc[:, "enter_short"] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        🔺 EXIT SHORT
        Sortie gérée uniquement par :
        - ROI
        - Stoploss
        """
        dataframe.loc[:, "exit_short"] = 0
        return dataframe
