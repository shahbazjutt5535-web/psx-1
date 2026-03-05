"""
PSX Stock Indicator Bot - Indicators Module
Compatible with:
- Python 3.11.9
- pandas==2.1.4
- numpy==1.24.4
- tvdatafeed from git
"""

import pandas as pd
import numpy as np
from tvDatafeed import TvDatafeed, Interval
import warnings
warnings.filterwarnings('ignore')

# ---------------------------
# Helper indicator functions
# ---------------------------
def EMA(data, period=14):
    """Exponential Moving Average"""
    return data['close'].ewm(span=period, adjust=False).mean()

def WMA(data, period=14):
    """Weighted Moving Average"""
    weights = np.arange(1, period + 1)
    def wma(arr):
        if len(arr) < period or np.any(pd.isna(arr)):
            return np.nan
        return np.sum(weights * arr) / weights.sum()
    return data['close'].rolling(period, min_periods=period).apply(wma, raw=True)

def HMA(data, period=14):
    """Hull Moving Average"""
    half_length = int(period / 2)
    sqrt_length = int(np.sqrt(period))
    wma_half = WMA(data, half_length)
    wma_full = WMA(data, period)
    hma_raw = 2 * wma_half - wma_full
    return hma_raw.rolling(sqrt_length, min_periods=sqrt_length).mean()

def SMA(data, period=14):
    """Simple Moving Average"""
    return data['close'].rolling(window=period, min_periods=period).mean()

def RSI(data, period=14):
    """Relative Strength Index"""
    delta = data['close'].diff()
    gain = delta.clip(lower=0)
    loss = -1 * delta.clip(upper=0)
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
    # Avoid division by zero
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi

def MACD(data, fast=12, slow=26, signal=9):
    """MACD Indicator"""
    exp1 = data['close'].ewm(span=fast, adjust=False).mean()
    exp2 = data['close'].ewm(span=slow, adjust=False).mean()
    macd = exp1 - exp2
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    histogram = macd - signal_line
    return macd, signal_line, histogram

def VW_MACD(data, fast=12, slow=26, signal=9):
    """Volume-Weighted MACD"""
    # Calculate typical price
    typ_price = (data['high'] + data['low'] + data['close']) / 3
    # Volume-weighted close
    vw_close = (typ_price * data['volume']).rolling(window=1).mean() / data['volume'].rolling(window=1).mean()
    vw_close = vw_close.fillna(typ_price)
    exp1 = vw_close.ewm(span=fast, adjust=False).mean()
    exp2 = vw_close.ewm(span=slow, adjust=False).mean()
    vw_macd = exp1 - exp2
    vw_signal = vw_macd.ewm(span=signal, adjust=False).mean()
    vw_histogram = vw_macd - vw_signal
    return vw_macd, vw_signal, vw_histogram

def Bollinger_Bands(data, period=20, std_dev=2):
    """Bollinger Bands"""
    sma = SMA(data, period)
    std = data['close'].rolling(period, min_periods=period).std()
    upper = sma + (std_dev * std)
    lower = sma - (std_dev * std)
    return upper, sma, lower

def Fib_Bollinger_Bands(data, period=20):
    """Fibonacci Bollinger Bands"""
    sma = SMA(data, period)
    std = data['close'].rolling(period, min_periods=period).std()
    
    fib_levels = [1.0, 0.618, 0.382, 0, -0.382, -0.618, -1.0]
    bands = {}
    
    for level in fib_levels:
        # Create safe key name
        if level >= 0:
            key = f'fib_{str(level).replace(".", "_")}'
        else:
            key = f'fib_neg{str(abs(level)).replace(".", "_")}'
        bands[key] = sma + (level * std * 2)
    
    return bands

def ATR(data, period=14):
    """Average True Range"""
    high_low = data['high'] - data['low']
    high_close = np.abs(data['high'] - data['close'].shift())
    low_close = np.abs(data['low'] - data['close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = tr.rolling(window=period, min_periods=period).mean()
    return atr

def Stochastic(data, k_period=14, d_period=3):
    """Stochastic Oscillator"""
    low_min = data['low'].rolling(k_period, min_periods=k_period).min()
    high_max = data['high'].rolling(k_period, min_periods=k_period).max()
    k = 100 * ((data['close'] - low_min) / (high_max - low_min))
    d = k.rolling(d_period, min_periods=d_period).mean()
    return k, d

def Stochastic_RSI(data, period=14, k_period=3, d_period=3):
    """Stochastic RSI"""
    rsi = RSI(data, period)
    min_rsi = rsi.rolling(window=period, min_periods=period).min()
    max_rsi = rsi.rolling(window=period, min_periods=period).max()
    stoch_k = 100 * (rsi - min_rsi) / (max_rsi - min_rsi)
    stoch_d = stoch_k.rolling(window=d_period, min_periods=d_period).mean()
    return stoch_k, stoch_d

def KDJ(data, period=9, k_period=3, d_period=3):
    """KDJ Indicator"""
    low_min = data['low'].rolling(period, min_periods=period).min()
    high_max = data['high'].rolling(period, min_periods=period).max()
    rsv = 100 * ((data['close'] - low_min) / (high_max - low_min))
    rsv = rsv.fillna(50)
    k = rsv.ewm(span=k_period, adjust=False).mean()
    d = k.ewm(span=d_period, adjust=False).mean()
    j = 3 * k - 2 * d
    return k, d, j

def Williams_R(data, period=14):
    """Williams %R"""
    high_max = data['high'].rolling(period, min_periods=period).max()
    low_min = data['low'].rolling(period, min_periods=period).min()
    williams_r = -100 * ((high_max - data['close']) / (high_max - low_min))
    return williams_r

def CCI(data, period=20):
    """Commodity Channel Index"""
    tp = (data['high'] + data['low'] + data['close']) / 3
    sma_tp = tp.rolling(period, min_periods=period).mean()
    mad = tp.rolling(period, min_periods=period).apply(lambda x: np.abs(x - x.mean()).mean())
    cci = (tp - sma_tp) / (0.015 * mad)
    return cci

def ROC(data, period=12):
    """Rate of Change"""
    return ((data['close'] - data['close'].shift(period)) / data['close'].shift(period)) * 100

def MOM(data, period=10):
    """Momentum"""
    return data['close'] - data['close'].shift(period)

def Ultimate_Oscillator(data, period1=7, period2=14, period3=28):
    """Ultimate Oscillator"""
    bp = data['close'] - np.minimum(data['low'], data['close'].shift())
    tr = np.maximum(data['high'], data['close'].shift()) - np.minimum(data['low'], data['close'].shift())
    
    avg7 = bp.rolling(period1, min_periods=period1).sum() / tr.rolling(period1, min_periods=period1).sum()
    avg14 = bp.rolling(period2, min_periods=period2).sum() / tr.rolling(period2, min_periods=period2).sum()
    avg28 = bp.rolling(period3, min_periods=period3).sum() / tr.rolling(period3, min_periods=period3).sum()
    
    uo = 100 * (4 * avg7 + 2 * avg14 + avg28) / 7
    return uo

def ADX(data, period=14):
    """Average Directional Index"""
    high, low, close = data['high'], data['low'], data['close']
    
    plus_dm = high.diff()
    minus_dm = low.diff()
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm > 0] = 0
    
    tr = pd.concat([high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
    atr = tr.rolling(period, min_periods=period).mean()
    
    plus_di = 100 * (plus_dm.ewm(alpha=1/period, adjust=False).mean() / atr)
    minus_di = 100 * (abs(minus_dm).ewm(alpha=1/period, adjust=False).mean() / atr)
    
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    adx = dx.ewm(alpha=1/period, adjust=False).mean()
    
    return adx, plus_di, minus_di

def TDI(data):
    """Traders Dynamic Index"""
    rsi = RSI(data, 13)
    volatility_band = rsi.rolling(34, min_periods=34).mean()
    trade_signal = volatility_band.rolling(34, min_periods=34).mean()
    return rsi, volatility_band, trade_signal

def Ichimoku(data, conversion=9, base=26, span=52):
    """Ichimoku Cloud"""
    high = data['high']
    low = data['low']
    
    conversion_line = (high.rolling(conversion, min_periods=conversion).max() + 
                      low.rolling(conversion, min_periods=conversion).min()) / 2
    base_line = (high.rolling(base, min_periods=base).max() + 
                low.rolling(base, min_periods=base).min()) / 2
    leading_span_a = ((conversion_line + base_line) / 2).shift(base)
    leading_span_b = ((high.rolling(span, min_periods=span).max() + 
                      low.rolling(span, min_periods=span).min()) / 2).shift(base)
    
    return conversion_line, base_line, leading_span_a, leading_span_b

def SuperTrend(data, period=10, multiplier=3):
    """SuperTrend Indicator"""
    atr = ATR(data, period)
    hl_avg = (data['high'] + data['low']) / 2
    
    upper_band = hl_avg + (multiplier * atr)
    lower_band = hl_avg - (multiplier * atr)
    
    supertrend = pd.Series(index=data.index, dtype=float)
    
    for i in range(1, len(data)):
        if i == 1:
            supertrend.iloc[i] = lower_band.iloc[i]
            continue
        
        prev_close = data['close'].iloc[i-1]
        curr_close = data['close'].iloc[i]
        
        if prev_close > supertrend.iloc[i-1]:
            if curr_close > lower_band.iloc[i]:
                supertrend.iloc[i] = lower_band.iloc[i]
            else:
                supertrend.iloc[i] = upper_band.iloc[i]
        else:
            if curr_close < upper_band.iloc[i]:
                supertrend.iloc[i] = upper_band.iloc[i]
            else:
                supertrend.iloc[i] = lower_band.iloc[i]
    
    return supertrend

def Parabolic_SAR(data, step=0.02, max_step=0.2):
    """Parabolic SAR"""
    high, low = data['high'], data['low']
    sar = pd.Series(index=data.index, dtype=float)
    
    if len(data) < 2:
        return sar
    
    # Initialize
    sar.iloc[0] = low.iloc[0]
    ep = high.iloc[0]
    af = step
    trend = 1  # 1 for uptrend, -1 for downtrend
    
    for i in range(1, len(data)):
        if trend == 1:
            # Uptrend
            sar.iloc[i] = sar.iloc[i-1] + af * (ep - sar.iloc[i-1])
            
            if high.iloc[i] > ep:
                ep = high.iloc[i]
                af = min(af + step, max_step)
            
            if low.iloc[i] < sar.iloc[i]:
                trend = -1
                sar.iloc[i] = ep
                ep = low.iloc[i]
                af = step
        else:
            # Downtrend
            sar.iloc[i] = sar.iloc[i-1] - af * (sar.iloc[i-1] - ep)
            
            if low.iloc[i] < ep:
                ep = low.iloc[i]
                af = min(af + step, max_step)
            
            if high.iloc[i] > sar.iloc[i]:
                trend = 1
                sar.iloc[i] = ep
                ep = high.iloc[i]
                af = step
    
    return sar

def Keltner_Channel(data, period=20, atr_period=10, multiplier=2):
    """Keltner Channel"""
    ema = EMA(data, period)
    atr = ATR(data, atr_period)
    upper = ema + (multiplier * atr)
    lower = ema - (multiplier * atr)
    return upper, ema, lower

def Choppiness_Index(data, period=14):
    """Choppiness Index"""
    high, low, close = data['high'], data['low'], data['close']
    
    tr = pd.concat([high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
    high_period = high.rolling(period, min_periods=period).max()
    low_period = low.rolling(period, min_periods=period).min()
    
    ci = 100 * np.log10(tr.rolling(period, min_periods=period).sum() / (high_period - low_period)) / np.log10(period)
    return ci

def TRIX(data, period=14):
    """TRIX Indicator"""
    ema1 = EMA(data, period)
    ema2 = ema1.ewm(span=period, adjust=False).mean()
    ema3 = ema2.ewm(span=period, adjust=False).mean()
    trix = 100 * (ema3 - ema3.shift()) / ema3.shift()
    signal = trix.ewm(span=9, adjust=False).mean()
    return trix, signal

def Donchian_Channel(data, period=20):
    """Donchian Channel"""
    upper = data['high'].rolling(period, min_periods=period).max()
    lower = data['low'].rolling(period, min_periods=period).min()
    middle = (upper + lower) / 2
    return upper, middle, lower

def RVI(data, period=10):
    """Relative Volatility Index"""
    std = data['close'].rolling(period, min_periods=period).std()
    std_up = std.where(std > std.shift(), 0).rolling(period, min_periods=period).mean()
    std_down = -std.where(std < std.shift(), 0).rolling(period, min_periods=period).mean()
    rvi = 100 * std_up / (std_up + std_down)
    signal = rvi.rolling(4, min_periods=4).mean()
    return rvi, signal

def VWAP(data):
    """Volume Weighted Average Price"""
    return (data['close'] * data['volume']).cumsum() / data['volume'].cumsum()

def ADOSC(data, fast=3, slow=10):
    """Accumulation/Distribution Oscillator"""
    clv = ((data['close'] - data['low']) - (data['high'] - data['close'])) / (data['high'] - data['low'])
    clv = clv.fillna(0)
    ad = clv * data['volume']
    ad = ad.cumsum()
    ad_ema_fast = ad.ewm(span=fast, adjust=False).mean()
    ad_ema_slow = ad.ewm(span=slow, adjust=False).mean()
    adosc = ad_ema_fast - ad_ema_slow
    return adosc

def MFI(data, period=14):
    """Money Flow Index"""
    typical_price = (data['high'] + data['low'] + data['close']) / 3
    money_flow = typical_price * data['volume']
    
    positive_flow = money_flow.where(typical_price > typical_price.shift(), 0).rolling(period, min_periods=period).sum()
    negative_flow = money_flow.where(typical_price < typical_price.shift(), 0).rolling(period, min_periods=period).sum()
    
    money_ratio = positive_flow / negative_flow.replace(0, np.nan)
    mfi = 100 - (100 / (1 + money_ratio))
    return mfi

def Aroon(data, period=14):
    """Aroon Indicator"""
    def aroon_up_func(x):
        if len(x) < period:
            return np.nan
        return 100 * (period - 1 - np.argmax(x)) / period
    
    def aroon_down_func(x):
        if len(x) < period:
            return np.nan
        return 100 * (period - 1 - np.argmin(x)) / period
    
    aroon_up = data['high'].rolling(period, min_periods=period).apply(aroon_up_func, raw=True)
    aroon_down = data['low'].rolling(period, min_periods=period).apply(aroon_down_func, raw=True)
    return aroon_up, aroon_down

def OBV(data):
    """On-Balance Volume"""
    obv = (data['volume'] * (~data['close'].diff().le(0) * 2 - 1)).cumsum()
    return obv

def Heikin_Ashi(data):
    """Heikin Ashi candles"""
    ha_close = (data['open'] + data['high'] + data['low'] + data['close']) / 4
    return ha_close

def calculate_all(tv: TvDatafeed, symbol="PSX:KSE100", interval=Interval.in_daily, n=200):
    """
    Fetch latest n candles from TradingView and calculate signals
    """
    try:
        df = tv.get_hist(symbol=symbol, interval=interval, n_bars=n)
        if df.empty:
            return "No data available for symbol."

        signals = []

        # EMA & SMA signals
        ema20 = EMA(df, 20).iloc[-1]
        ema50 = EMA(df, 50).iloc[-1]
        sma20 = SMA(df, 20).iloc[-1]

        if not pd.isna(ema20) and not pd.isna(ema50):
            if ema20 > ema50:
                signals.append("EMA20 > EMA50 ✅")
            else:
                signals.append("EMA20 < EMA50 ❌")

        if not pd.isna(sma20) and not pd.isna(df['close'].iloc[-1]):
            if df['close'].iloc[-1] > sma20:
                signals.append("Price above SMA20 ✅")
            else:
                signals.append("Price below SMA20 ❌")

        # MACD
        macd, signal_line, histogram = MACD(df)
        if not pd.isna(macd.iloc[-1]) and not pd.isna(signal_line.iloc[-1]):
            if macd.iloc[-1] > signal_line.iloc[-1]:
                signals.append("MACD bullish crossover ✅")
            else:
                signals.append("MACD bearish crossover ❌")

        # RSI
        rsi_val = RSI(df).iloc[-1]
        if not pd.isna(rsi_val):
            if rsi_val > 70:
                signals.append(f"RSI: {rsi_val:.2f} 🔴")
            elif rsi_val < 30:
                signals.append(f"RSI: {rsi_val:.2f} 🟢")
            else:
                signals.append(f"RSI: {rsi_val:.2f} ⚪")

        # Bollinger Bands
        upper, middle, lower = Bollinger_Bands(df)
        close_price = df['close'].iloc[-1]
        if not pd.isna(upper.iloc[-1]) and not pd.isna(lower.iloc[-1]):
            if close_price > upper.iloc[-1]:
                signals.append(f"Price above upper BB 🔴")
            elif close_price < lower.iloc[-1]:
                signals.append(f"Price below lower BB 🟢")
            else:
                signals.append("Price within BB ⚪")

        # ATR
        atr_val = ATR(df).iloc[-1]
        if not pd.isna(atr_val):
            signals.append(f"ATR(14): {atr_val:.2f}")

        # Stochastic
        k, d = Stochastic(df)
        if not pd.isna(k.iloc[-1]) and not pd.isna(d.iloc[-1]):
            if k.iloc[-1] > d.iloc[-1]:
                signals.append("Stochastic bullish ✅")
            else:
                signals.append("Stochastic bearish ❌")

        return "\n".join(signals)

    except Exception as e:
        return f"Error calculating indicators: {e}"
