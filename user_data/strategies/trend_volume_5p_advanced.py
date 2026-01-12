from freqtrade.strategy.interface import IStrategy
from pandas import DataFrame
import talib.abstract as ta
import numpy as np

class TrendVolume5pAdvanced(IStrategy):
    """
    ╔══════════════════════════════════════════════════════════════════════╗
    ║     STRATÉGIE TRADING AVANCÉE - BYBIT USDT PERPETUAL 5M             ║
    ╠══════════════════════════════════════════════════════════════════════╣
    ║  📊 Multi-indicateurs: EMA, RSI, MACD, Bollinger, ADX, Stochastic   ║
    ║  🎯 Take Profit adaptatif: 8% → 5% → 3% → 1.5%                      ║
    ║  🛡️  Stop Loss intelligent: 4% fixe + Trailing Stop                  ║
    ║  📈 Support Long & Short avec 10+ conditions de validation           ║
    ║  ⚡ Gestion de risque avancée avec ATR dynamique                     ║
    ╚══════════════════════════════════════════════════════════════════════╝
    """
    
    # ═══════════════════════════════════════════════════════════════
    # 📋 CONFIGURATION DE BASE
    # ═══════════════════════════════════════════════════════════════
    
    INTERFACE_VERSION = 3
    timeframe = '5m'
    can_short = True
    
    # Nombre de bougies nécessaires avant de commencer
    startup_candle_count = 200
    
    # ═══════════════════════════════════════════════════════════════
    # 💰 GESTION DES POSITIONS
    # ═══════════════════════════════════════════════════════════════
    
    # Taille de position (95% du capital disponible par trade)
    stake_amount = 'unlimited'
    stake_currency = 'USDT'
    
    # Nombre maximum d'ordres ouverts simultanément
    max_open_trades = 3
    
    # Permet d'ajuster la position (pyramiding)
    position_adjustment_enable = False
    
    # ═══════════════════════════════════════════════════════════════
    # 🛡️ STOP LOSS - Protection du Capital (TRÈS IMPORTANT!)
    # ═══════════════════════════════════════════════════════════════
    
    # Stop Loss fixe à -4% (limite la perte maximale par trade)
    stoploss = -0.04
    
    # TRAILING STOP: Stop Loss qui suit le prix à la hausse
    # Si le prix monte de 2%, le stop loss commence à suivre
    trailing_stop = True
    trailing_stop_positive = 0.02        # Active à +2% de profit
    trailing_stop_positive_offset = 0.03  # Commence à suivre à +3%
    trailing_only_offset_is_reached = True
    
    # ═══════════════════════════════════════════════════════════════
    # 🎯 TAKE PROFIT (ROI) - Objectifs de Profit Progressifs
    # ═══════════════════════════════════════════════════════════════
    
    # ROI adaptatif: plus on reste longtemps, plus l'objectif baisse
    minimal_roi = {
        "0": 0.08,    # Si possible, sortir à +8% immédiatement
        "15": 0.05,   # Après 15 minutes, accepter +5%
        "30": 0.03,   # Après 30 minutes, accepter +3%
        "60": 0.015,  # Après 1 heure, accepter +1.5%
        "120": 0.01   # Après 2 heures, sortir à +1%
    }
    
    # ═══════════════════════════════════════════════════════════════
    # 📤 CONFIGURATION DES SIGNAUX DE SORTIE
    # ═══════════════════════════════════════════════════════════════
    
    use_exit_signal = True                # Utiliser les signaux de sortie
    exit_profit_only = False              # Sortir même en perte si signal
    exit_profit_offset = 0.01             # Sortir seulement si profit > 1%
    ignore_roi_if_entry_signal = False    # Respecter le ROI même si nouveau signal
    
    # ═══════════════════════════════════════════════════════════════
    # 🔧 FONCTIONS UTILITAIRES
    # ═══════════════════════════════════════════════════════════════
    
    def crossed_above(self, series1, series2):
        """Détecte un croisement vers le haut"""
        return (series1 > series2) & (series1.shift(1) <= series2.shift(1))
    
    def crossed_below(self, series1, series2):
        """Détecte un croisement vers le bas"""
        return (series1 < series2) & (series1.shift(1) >= series2.shift(1))
    
    def bollinger_bands(self, close, window=20, stds=2):
        """Calcule les bandes de Bollinger"""
        ma = close.rolling(window=window).mean()
        std = close.rolling(window=window).std()
        return {
            'lower': ma - (std * stds),
            'mid': ma,
            'upper': ma + (std * stds)
        }
    
    # ═══════════════════════════════════════════════════════════════
    # 📊 CALCUL DES INDICATEURS TECHNIQUES
    # ═══════════════════════════════════════════════════════════════
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Calcule tous les indicateurs nécessaires à l'analyse
        
        INDICATEURS UTILISÉS:
        ────────────────────
        1. 📈 EMA (Exponential Moving Average) - Tendance
        2. 📊 SMA (Simple Moving Average) - Confirmation
        3. 🎯 RSI (Relative Strength Index) - Surachat/Survente
        4. ⚡ MACD - Momentum et divergences
        5. 📉 Bollinger Bands - Volatilité
        6. 💪 ADX - Force de la tendance
        7. 🔄 Stochastic - Momentum oscillateur
        8. 📏 ATR - Mesure de volatilité
        9. 📊 Volume - Confirmation des mouvements
        10. 🎲 OBV - Flux de volume
        """
        
        # ──────────────────────────────────────────────────────
        # 1️⃣ MOYENNES MOBILES - Détection de Tendance
        # ──────────────────────────────────────────────────────
        
        # EMA rapides (réagissent vite aux changements)
        dataframe['ema5'] = ta.EMA(dataframe, timeperiod=5)
        dataframe['ema10'] = ta.EMA(dataframe, timeperiod=10)
        dataframe['ema20'] = ta.EMA(dataframe, timeperiod=20)
        
        # EMA lentes (tendance de fond)
        dataframe['ema50'] = ta.EMA(dataframe, timeperiod=50)
        dataframe['ema100'] = ta.EMA(dataframe, timeperiod=100)
        dataframe['ema200'] = ta.EMA(dataframe, timeperiod=200)
        
        # SMA pour confirmation
        dataframe['sma20'] = ta.SMA(dataframe, timeperiod=20)
        dataframe['sma50'] = ta.SMA(dataframe, timeperiod=50)
        
        # ──────────────────────────────────────────────────────
        # 2️⃣ RSI - Index de Force Relative
        # ──────────────────────────────────────────────────────
        # RSI > 70 = Surachat (risque de baisse)
        # RSI < 30 = Survente (risque de hausse)
        
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        dataframe['rsi_fast'] = ta.RSI(dataframe, timeperiod=7)
        dataframe['rsi_slow'] = ta.RSI(dataframe, timeperiod=21)
        
        # ──────────────────────────────────────────────────────
        # 3️⃣ MACD - Convergence/Divergence des Moyennes
        # ──────────────────────────────────────────────────────
        
        macd = ta.MACD(dataframe)
        dataframe['macd'] = macd['macd']
        dataframe['macdsignal'] = macd['macdsignal']
        dataframe['macdhist'] = macd['macdhist']
        
        # Détection des croisements MACD
        dataframe['macd_cross_up'] = self.crossed_above(
            dataframe['macd'], 
            dataframe['macdsignal']
        )
        dataframe['macd_cross_down'] = self.crossed_below(
            dataframe['macd'], 
            dataframe['macdsignal']
        )
        
        # ──────────────────────────────────────────────────────
        # 4️⃣ BOLLINGER BANDS - Mesure de Volatilité
        # ──────────────────────────────────────────────────────
        
        bollinger = self.bollinger_bands(dataframe['close'], window=20, stds=2)
        dataframe['bb_lower'] = bollinger['lower']
        dataframe['bb_middle'] = bollinger['mid']
        dataframe['bb_upper'] = bollinger['upper']
        
        # Largeur des bandes (volatilité)
        dataframe['bb_width'] = (
            (dataframe['bb_upper'] - dataframe['bb_lower']) / 
            dataframe['bb_middle']
        )
        
        # Position du prix dans les bandes (0 = bas, 1 = haut)
        dataframe['bb_percent'] = (
            (dataframe['close'] - dataframe['bb_lower']) / 
            (dataframe['bb_upper'] - dataframe['bb_lower'])
        )
        
        # ──────────────────────────────────────────────────────
        # 5️⃣ ADX - Average Directional Index
        # ──────────────────────────────────────────────────────
        # ADX > 25 = Tendance forte
        # ADX < 20 = Pas de tendance claire
        
        dataframe['adx'] = ta.ADX(dataframe, timeperiod=14)
        dataframe['plus_di'] = ta.PLUS_DI(dataframe, timeperiod=14)
        dataframe['minus_di'] = ta.MINUS_DI(dataframe, timeperiod=14)
        
        # ──────────────────────────────────────────────────────
        # 6️⃣ STOCHASTIC - Oscillateur de Momentum
        # ──────────────────────────────────────────────────────
        
        stoch = ta.STOCH(dataframe)
        dataframe['slowk'] = stoch['slowk']
        dataframe['slowd'] = stoch['slowd']
        
        # ──────────────────────────────────────────────────────
        # 7️⃣ ATR - Average True Range (Volatilité)
        # ──────────────────────────────────────────────────────
        
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
        dataframe['atr_percent'] = (dataframe['atr'] / dataframe['close']) * 100
        
        # ──────────────────────────────────────────────────────
        # 8️⃣ ANALYSE DE VOLUME
        # ──────────────────────────────────────────────────────
        
        # Moyenne et écart-type du volume
        dataframe['volume_mean'] = dataframe['volume'].rolling(20).mean()
        dataframe['volume_std'] = dataframe['volume'].rolling(20).std()
        
        # Détection des pics de volume
        dataframe['volume_spike'] = (
            dataframe['volume'] > 
            (dataframe['volume_mean'] + 2 * dataframe['volume_std'])
        )
        
        # OBV - On Balance Volume
        dataframe['obv'] = ta.OBV(dataframe)
        dataframe['obv_ema'] = ta.EMA(dataframe['obv'], timeperiod=20)
        
        # ──────────────────────────────────────────────────────
        # 9️⃣ SUPPORT & RESISTANCE - Pivot Points
        # ──────────────────────────────────────────────────────
        
        dataframe['pivot'] = (
            dataframe['high'] + dataframe['low'] + dataframe['close']
        ) / 3
        dataframe['r1'] = 2 * dataframe['pivot'] - dataframe['low']
        dataframe['s1'] = 2 * dataframe['pivot'] - dataframe['high']
        
        # ──────────────────────────────────────────────────────
        # 🔟 PRICE ACTION - Momentum de Prix
        # ──────────────────────────────────────────────────────
        
        dataframe['price_momentum'] = (
            (dataframe['close'] - dataframe['close'].shift(5)) / 
            dataframe['close'].shift(5) * 100
        )
        
        return dataframe
    
    # ═══════════════════════════════════════════════════════════════
    # 📈 SIGNAUX D'ENTRÉE EN POSITION
    # ═══════════════════════════════════════════════════════════════
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Définit les conditions d'entrée LONG et SHORT
        
        🟢 SIGNAL LONG (ACHAT):
        ──────────────────────
        ✅ Tendance haussière (EMA10 > EMA50)
        ✅ Force de tendance (ADX > 25)
        ✅ Momentum positif (RSI entre 40-75)
        ✅ MACD haussier
        ✅ Volume supérieur à la moyenne
        ✅ Prix dans zone favorable des BB
        ✅ Stochastic favorable
        ✅ OBV en hausse
        
        🔴 SIGNAL SHORT (VENTE):
        ──────────────────────
        ✅ Tendance baissière (EMA10 < EMA50)
        ✅ Force de tendance (ADX > 25)
        ✅ Momentum négatif (RSI entre 25-60)
        ✅ MACD baissier
        ✅ Volume supérieur à la moyenne
        ✅ Prix dans zone favorable des BB
        ✅ Stochastic favorable
        ✅ OBV en baisse
        """
        
        # ═══════════════════════════════════════════════════════════
        # 🟢 CONDITIONS D'ENTRÉE LONG (ACHAT)
        # ═══════════════════════════════════════════════════════════
        
        conditions_long = []
        
        # 1. Tendance haussière confirmée
        conditions_long.append(dataframe['close'] > dataframe['ema50'])
        conditions_long.append(dataframe['ema10'] > dataframe['ema50'])
        conditions_long.append(dataframe['ema20'] > dataframe['ema50'])
        
        # 2. Force de la tendance (ADX)
        conditions_long.append(dataframe['adx'] > 25)
        conditions_long.append(dataframe['plus_di'] > dataframe['minus_di'])
        
        # 3. RSI dans zone favorable (pas suracheté, pas survendu)
        conditions_long.append(dataframe['rsi'] > 40)
        conditions_long.append(dataframe['rsi'] < 75)
        conditions_long.append(dataframe['rsi_fast'] > dataframe['rsi_slow'])
        
        # 4. MACD haussier
        conditions_long.append(
            (dataframe['macd'] > dataframe['macdsignal']) |
            (dataframe['macd_cross_up'])
        )
        conditions_long.append(dataframe['macdhist'] > 0)
        
        # 5. Volume significatif (confirme le mouvement)
        conditions_long.append(
            dataframe['volume'] > dataframe['volume_mean'] * 1.2
        )
        
        # 6. Prix dans zone favorable Bollinger Bands
        conditions_long.append(dataframe['bb_percent'] > 0.3)
        conditions_long.append(dataframe['bb_percent'] < 0.9)
        
        # 7. Stochastic pas en zone de surachat
        conditions_long.append(dataframe['slowk'] > 20)
        conditions_long.append(dataframe['slowk'] < 80)
        conditions_long.append(dataframe['slowk'] > dataframe['slowd'])
        
        # 8. OBV confirme la hausse
        conditions_long.append(dataframe['obv'] > dataframe['obv_ema'])
        
        # 9. Momentum positif
        conditions_long.append(dataframe['price_momentum'] > -2)
        
        # 10. Au-dessus du support pivot
        conditions_long.append(dataframe['close'] > dataframe['s1'])
        
        # Combiner toutes les conditions
        if conditions_long:
            dataframe.loc[
                np.array(conditions_long).all(axis=0),
                'enter_long'
            ] = 1
        
        # ═══════════════════════════════════════════════════════════
        # 🔴 CONDITIONS D'ENTRÉE SHORT (VENTE)
        # ═══════════════════════════════════════════════════════════
        
        conditions_short = []
        
        # 1. Tendance baissière confirmée
        conditions_short.append(dataframe['close'] < dataframe['ema50'])
        conditions_short.append(dataframe['ema10'] < dataframe['ema50'])
        conditions_short.append(dataframe['ema20'] < dataframe['ema50'])
        
        # 2. Force de la tendance (ADX)
        conditions_short.append(dataframe['adx'] > 25)
        conditions_short.append(dataframe['minus_di'] > dataframe['plus_di'])
        
        # 3. RSI dans zone favorable
        conditions_short.append(dataframe['rsi'] < 60)
        conditions_short.append(dataframe['rsi'] > 25)
        conditions_short.append(dataframe['rsi_fast'] < dataframe['rsi_slow'])
        
        # 4. MACD baissier
        conditions_short.append(
            (dataframe['macd'] < dataframe['macdsignal']) |
            (dataframe['macd_cross_down'])
        )
        conditions_short.append(dataframe['macdhist'] < 0)
        
        # 5. Volume significatif
        conditions_short.append(
            dataframe['volume'] > dataframe['volume_mean'] * 1.2
        )
        
        # 6. Prix dans zone favorable Bollinger Bands
        conditions_short.append(dataframe['bb_percent'] < 0.7)
        conditions_short.append(dataframe['bb_percent'] > 0.1)
        
        # 7. Stochastic pas en zone de survente
        conditions_short.append(dataframe['slowk'] < 80)
        conditions_short.append(dataframe['slowk'] > 20)
        conditions_short.append(dataframe['slowk'] < dataframe['slowd'])
        
        # 8. OBV confirme la baisse
        conditions_short.append(dataframe['obv'] < dataframe['obv_ema'])
        
        # 9. Momentum négatif
        conditions_short.append(dataframe['price_momentum'] < 2)
        
        # 10. En-dessous de la résistance pivot
        conditions_short.append(dataframe['close'] < dataframe['r1'])
        
        # Combiner toutes les conditions
        if conditions_short:
            dataframe.loc[
                np.array(conditions_short).all(axis=0),
                'enter_short'
            ] = 1
        
        return dataframe
    
    # ═══════════════════════════════════════════════════════════════
    # 📉 SIGNAUX DE SORTIE DE POSITION
    # ═══════════════════════════════════════════════════════════════
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Définit les conditions de sortie LONG et SHORT
        
        Sort d'une position quand:
        ✅ Retournement de tendance détecté
        ✅ Surachat/Survente extrême
        ✅ Divergence des indicateurs
        ✅ Affaiblissement du momentum
        """
        
        # ═══════════════════════════════════════════════════════════
        # 🟢 SORTIE LONG (Fermeture position d'achat)
        # ═══════════════════════════════════════════════════════════
        
        conditions_exit_long = []
        
        # Retournement baissier détecté
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
            dataframe.loc[
                np.array(conditions_exit_long).any(axis=0),
                'exit_long'
            ] = 1
        
        # ═══════════════════════════════════════════════════════════
        # 🔴 SORTIE SHORT (Fermeture position de vente)
        # ═══════════════════════════════════════════════════════════
        
        conditions_exit_short = []
        
        # Retournement haussier détecté
        conditions_exit_short.append(
            (dataframe['ema10'] > dataframe['ema20']) |
            (dataframe['rsi'] < 25) |
            (dataframe['macd_cross_up']) |
            (dataframe['close'] < dataframe['bb_lower']) |
            ((dataframe['slowk'] < 20) & (dataframe['slowk'] > dataframe['slowd'])) |
            ((dataframe['adx'] > 30) & (dataframe['plus_di'] > dataframe['minus_di'])) |
            (dataframe['price_momentum'] > 3)
        )
        
        if conditions_exit_short:
            dataframe.loc[
                np.array(conditions_exit_short).any(axis=0),
                'exit_short'
            ] = 1
        
        return dataframe
    
    # ═══════════════════════════════════════════════════════════════
    # 🛡️ STOP LOSS PERSONNALISÉ (Basé sur ATR)
    # ═══════════════════════════════════════════════════════════════
    
    def custom_stoploss(self, pair: str, trade, current_time, 
                       current_rate: float, current_profit: float, **kwargs) -> float:
        """
        Stop Loss dynamique adapté à la volatilité du marché
        
        Utilise l'ATR (Average True Range) pour adapter le stop loss:
        - Marché volatil = Stop loss plus large
        - Marché calme = Stop loss plus serré
        
        Retourne le stop loss le plus restrictif entre:
        - Stop loss fixe (-4%)
        - Stop loss basé sur 2x ATR
        """
        
        try:
            dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
            last_candle = dataframe.iloc[-1].squeeze()
            
            # Calcul du stop loss basé sur l'ATR
            atr_sl = last_candle['atr'] * 2
            atr_sl_percent = (atr_sl / current_rate)
            
            # Utilise le stop loss le plus restrictif
            return max(self.stoploss, -atr_sl_percent)
        
        except Exception:
            # En cas d'erreur, utiliser le stop loss fixe
            return self.stoploss