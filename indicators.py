import pandas as pd
import numpy as np
from tvDatafeed import TvDatafeed, Interval

# ---------------------------
# Helper indicator functions
# ---------------------------
def EMA(data, period=14):
    return data['close'].ewm(span=period, adjust=False).mean()

def WMA(data, period=14):
    """Weighted Moving Average"""
    weights = np.arange(1, period + 1)
    def wma(arr):
        return np.sum(weights * arr) / weights.sum()
    return data['close'].rolling(period).apply(wma, raw=True)

def HMA(data, period=14):
    """Hull Moving Average"""
    half_length = int(period / 2)
    sqrt_length = int(np.sqrt(period))
    wma_half = WMA(data, half_length)
    wma_full = WMA(data, period)
    hma_raw = 2 * wma_half - wma_full
    return hma_raw.rolling(sqrt_length).mean()

def SMA(data, period=14):
    return data['close'].rolling(window=period).mean()

def RSI(data, period=14):
    delta = data['close'].diff()
    gain = delta.clip(lower=0)
    loss = -1 * delta.clip(upper=0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def MACD(data, fast=12, slow=26, signal=9):
    exp1 = data['close'].ewm(span=fast, adjust=False).mean()
    exp2 = data['close'].ewm(span=slow, adjust=False).mean()
    macd = exp1 - exp2
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    histogram = macd - signal_line
    return macd, signal_line, histogram

def VW_MACD(data, fast=12, slow=26, signal=9):
    """Volume-Weighted MACD"""
    # Calculate volume-weighted close
    vw_close = (data['close'] * data['volume']).rolling(window=1).mean() / data['volume'].rolling(window=1).mean()
    exp1 = vw_close.ewm(span=fast, adjust=False).mean()
    exp2 = vw_close.ewm(span=slow, adjust=False).mean()
    vw_macd = exp1 - exp2
    vw_signal = vw_macd.ewm(span=signal, adjust=False).mean()
    vw_histogram = vw_macd - vw_signal
    return vw_macd, vw_signal, vw_histogram

def Bollinger_Bands(data, period=20, std_dev=2):
    sma = SMA(data, period)
    std = data['close'].rolling(period).std()
    upper = sma + (std_dev * std)
    lower = sma - (std_dev * std)
    return upper, sma, lower

def Fib_Bollinger_Bands(data, period=20):
    """Fibonacci Bollinger Bands"""
    sma = SMA(data, period)
    std = data['close'].rolling(period).std()
    
    fib_levels = [1.0, 0.618, 0.382, 0, -0.382, -0.618, -1.0]
    bands = {}
    
    for level in fib_levels:
        bands[f'fib_{str(level).replace("-", "neg")}'] = sma + (level * std * 2)
    
    return bands

def ATR(data, period=14):
    high_low = data['high'] - data['low']
    high_close = np.abs(data['high'] - data['close'].shift())
    low_close = np.abs(data['low'] - data['close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()
    return atr

def Stochastic(data, k_period=14, d_period=3):
    low_min = data['low'].rolling(k_period).min()
    high_max = data['high'].rolling(k_period).max()
    k = 100 * ((data['close'] - low_min) / (high_max - low_min))
    d = k.rolling(d_period).mean()
    return k, d

def Stochastic_RSI(data, period=14, k_period=3, d_period=3):
    """Stochastic RSI"""
    rsi = RSI(data, period)
    min_rsi = rsi.rolling(window=period).min()
    max_rsi = rsi.rolling(window=period).max()
    stoch_k = 100 * (rsi - min_rsi) / (max_rsi - min_rsi)
    stoch_d = stoch_k.rolling(window=d_period).mean()
    return stoch_k, stoch_d

def KDJ(data, period=9, k_period=3, d_period=3):
    """KDJ Indicator"""
    low_min = data['low'].rolling(period).min()
    high_max = data['high'].rolling(period).max()
    rsv = 100 * ((data['close'] - low_min) / (high_max - low_min))
    k = rsv.ewm(span=k_period).mean()
    d = k.ewm(span=d_period).mean()
    j = 3 * k - 2 * d
    return k, d, j

def Williams_R(data, period=14):
    """Williams %R"""
    high_max = data['high'].rolling(period).max()
    low_min = data['low'].rolling(period).min()
    williams_r = -100 * ((high_max - data['close']) / (high_max - low_min))
    return williams_r

def CCI(data, period=20):
    """Commodity Channel Index"""
    tp = (data['high'] + data['low'] + data['close']) / 3
    sma_tp = tp.rolling(period).mean()
    mad = tp.rolling(period).apply(lambda x: np.abs(x - x.mean()).mean())
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
    
    avg7 = bp.rolling(period1).sum() / tr.rolling(period1).sum()
    avg14 = bp.rolling(period2).sum() / tr.rolling(period2).sum()
    avg28 = bp.rolling(period3).sum() / tr.rolling(period3).sum()
    
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
    atr = tr.rolling(period).mean()
    
    plus_di = 100 * (plus_dm.ewm(alpha=1/period).mean() / atr)
    minus_di = 100 * (abs(minus_dm).ewm(alpha=1/period).mean() / atr)
    
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    adx = dx.ewm(alpha=1/period).mean()
    
    return adx, plus_di, minus_di

def TDI(data):
    """Traders Dynamic Index"""
    rsi = RSI(data, 13)
    volatility_band = rsi.rolling(34).mean()
    trade_signal = volatility_band.rolling(34).mean()
    return rsi, volatility_band, trade_signal

def Ichimoku(data, conversion=9, base=26, span=52):
    """Ichimoku Cloud"""
    high = data['high']
    low = data['low']
    
    conversion_line = (high.rolling(conversion).max() + low.rolling(conversion).min()) / 2
    base_line = (high.rolling(base).max() + low.rolling(base).min()) / 2
    leading_span_a = ((conversion_line + base_line) / 2).shift(base)
    leading_span_b = ((high.rolling(span).max() + low.rolling(span).min()) / 2).shift(base)
    
    return conversion_line, base_line, leading_span_a, leading_span_b

def SuperTrend(data, period=10, multiplier=3):
    """SuperTrend Indicator"""
    atr = ATR(data, period)
    hl_avg = (data['high'] + data['low']) / 2
    
    upper_band = hl_avg + (multiplier * atr)
    lower_band = hl_avg - (multiplier * atr)
    
    supertrend = [0] * len(data)
    direction = [1] * len(data)
    
    for i in range(1, len(data)):
        if data['close'].iloc[i] > upper_band.iloc[i-1]:
            direction[i] = 1
        elif data['close'].iloc[i] < lower_band.iloc[i-1]:
            direction[i] = -1
        else:
            direction[i] = direction[i-1]
            
        if direction[i] == 1 and lower_band.iloc[i] < lower_band.iloc[i-1]:
            lower_band.iloc[i] = lower_band.iloc[i-1]
        if direction[i] == -1 and upper_band.iloc[i] > upper_band.iloc[i-1]:
            upper_band.iloc[i] = upper_band.iloc[i-1]
            
        supertrend[i] = lower_band.iloc[i] if direction[i] == 1 else upper_band.iloc[i]
    
    return pd.Series(supertrend, index=data.index)

def Parabolic_SAR(data, step=0.02, max_step=0.2):
    """Parabolic SAR"""
    high, low = data['high'], data['low']
    sar = [0] * len(data)
    ep = [0] * len(data)
    af = [0] * len(data)
    trend = [1] * len(data)  # 1 for uptrend, -1 for downtrend
    
    sar[0] = low.iloc[0]
    ep[0] = high.iloc[0]
    af[0] = step
    
    for i in range(1, len(data)):
        # Previous SAR
        sar[i] = sar[i-1] + af[i-1] * (ep[i-1] - sar[i-1])
        
        if trend[i-1] == 1:
            # Uptrend
            if high.iloc[i] > ep[i-1]:
                ep[i] = high.iloc[i]
                af[i] = min(af[i-1] + step, max_step)
            else:
                ep[i] = ep[i-1]
                af[i] = af[i-1]
                
            if low.iloc[i] < sar[i]:
                trend[i] = -1
                sar[i] = ep[i-1]
                ep[i] = low.iloc[i]
                af[i] = step
            else:
                trend[i] = 1
        else:
            # Downtrend
            if low.iloc[i] < ep[i-1]:
                ep[i] = low.iloc[i]
                af[i] = min(af[i-1] + step, max_step)
            else:
                ep[i] = ep[i-1]
                af[i] = af[i-1]
                
            if high.iloc[i] > sar[i]:
                trend[i] = 1
                sar[i] = ep[i-1]
                ep[i] = high.iloc[i]
                af[i] = step
            else:
                trend[i] = -1
    
    return pd.Series(sar, index=data.index)

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
    high_period = high.rolling(period).max()
    low_period = low.rolling(period).min()
    
    ci = 100 * np.log10(tr.rolling(period).sum() / (high_period - low_period)) / np.log10(period)
    return ci

def TRIX(data, period=14):
    """TRIX Indicator"""
    ema1 = EMA(data, period)
    ema2 = ema1.ewm(span=period).mean()
    ema3 = ema2.ewm(span=period).mean()
    trix = 100 * (ema3 - ema3.shift()) / ema3.shift()
    signal = trix.ewm(span=9).mean()
    return trix, signal

def Donchian_Channel(data, period=20):
    """Donchian Channel"""
    upper = data['high'].rolling(period).max()
    lower = data['low'].rolling(period).min()
    middle = (upper + lower) / 2
    return upper, middle, lower

def RVI(data, period=10):
    """Relative Volatility Index"""
    std = data['close'].rolling(period).std()
    std_up = std.where(std > std.shift(), 0).rolling(period).mean()
    std_down = -std.where(std < std.shift(), 0).rolling(period).mean()
    rvi = 100 * std_up / (std_up + std_down)
    signal = rvi.rolling(4).mean()
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
    ad_ema_fast = ad.ewm(span=fast).mean()
    ad_ema_slow = ad.ewm(span=slow).mean()
    adosc = ad_ema_fast - ad_ema_slow
    return adosc

def MFI(data, period=14):
    """Money Flow Index"""
    typical_price = (data['high'] + data['low'] + data['close']) / 3
    money_flow = typical_price * data['volume']
    
    positive_flow = money_flow.where(typical_price > typical_price.shift(), 0).rolling(period).sum()
    negative_flow = money_flow.where(typical_price < typical_price.shift(), 0).rolling(period).sum()
    
    money_ratio = positive_flow / negative_flow
    mfi = 100 - (100 / (1 + money_ratio))
    return mfi

def Aroon(data, period=14):
    """Aroon Indicator"""
    aroon_up = 100 * (period - data['high'].rolling(period).apply(lambda x: period - 1 - x.argmax())) / period
    aroon_down = 100 * (period - data['low'].rolling(period).apply(lambda x: period - 1 - x.argmin())) / period
    return aroon_up, aroon_down

def OBV(data):
    """On-Balance Volume"""
    obv = (data['volume'] * (~data['close'].diff().le(0) * 2 - 1)).cumsum()
    return obv

def Heikin_Ashi(data):
    """Heikin Ashi candles"""
    ha_close = (data['open'] + data['high'] + data['low'] + data['close']) / 4
    ha_open = (data['open'].shift() + data['close'].shift()) / 2
    ha_open.iloc[0] = data['open'].iloc[0]
    ha_high = data[['high', 'low', 'close', 'open']].max(axis=1)
    ha_low = data[['high', 'low', 'close', 'open']].min(axis=1)
    return ha_close, ha_open, ha_high, ha_low

def calculate_all(tv: TvDatafeed, symbol="PSX:KSE100", interval=Interval.in_daily, n=200):
    """
    Fetch latest n candles from TradingView and calculate signals
    """
    try:
        df = tv.get_hist(symbol=symbol, interval=interval, n=n)
        if df.empty:
            return "No data available for symbol."

        signals = []

        # EMA & SMA signals
        ema20 = EMA(df, 20).iloc[-1]
        ema50 = EMA(df, 50).iloc[-1]
        sma20 = SMA(df, 20).iloc[-1]

        if ema20 > ema50:
            signals.append("EMA20 > EMA50 ✅ Bullish")
        else:
            signals.append("EMA20 < EMA50 ❌ Bearish")

        if df['close'].iloc[-1] > sma20:
            signals.append("Price above SMA20 ✅")
        else:
            signals.append("Price below SMA20 ❌")

        # MACD
        macd, signal_line, histogram = MACD(df)
        if macd.iloc[-1] > signal_line.iloc[-1]:
            signals.append("MACD bullish crossover ✅")
        else:
            signals.append("MACD bearish crossover ❌")

        # RSI
        rsi_val = RSI(df).iloc[-1]
        if rsi_val > 70:
            signals.append(f"RSI: {rsi_val:.2f} ❌ Overbought")
        elif rsi_val < 30:
            signals.append(f"RSI: {rsi_val:.2f} ✅ Oversold")
        else:
            signals.append(f"RSI: {rsi_val:.2f} Neutral")

        # Bollinger Bands
        upper, middle, lower = Bollinger_Bands(df)
        close_price = df['close'].iloc[-1]
        if close_price > upper.iloc[-1]:
            signals.append(f"Price above upper BB ❌ Overbought")
        elif close_price < lower.iloc[-1]:
            signals.append(f"Price below lower BB ✅ Oversold")
        else:
            signals.append("Price within Bollinger Bands")

        # ATR
        atr_val = ATR(df).iloc[-1]
        signals.append(f"ATR(14): {atr_val:.2f}")

        # Stochastic
        k, d = Stochastic(df)
        if k.iloc[-1] > d.iloc[-1]:
            signals.append("Stochastic bullish ✅")
        else:
            signals.append("Stochastic bearish ❌")

        # Additional signals for new indicators
        # Stochastic RSI
        stoch_k, stoch_d = Stochastic_RSI(df)
        if stoch_k.iloc[-1] > stoch_d.iloc[-1] and stoch_k.iloc[-1] < 20:
            signals.append("Stoch RSI oversold bullish ✅")
        elif stoch_k.iloc[-1] < stoch_d.iloc[-1] and stoch_k.iloc[-1] > 80:
            signals.append("Stoch RSI overbought bearish ❌")

        # ADX
        adx, plus_di, minus_di = ADX(df)
        if adx.iloc[-1] > 25:
            if plus_di.iloc[-1] > minus_di.iloc[-1]:
                signals.append(f"Strong uptrend (ADX: {adx.iloc[-1]:.1f}) ✅")
            else:
                signals.append(f"Strong downtrend (ADX: {adx.iloc[-1]:.1f}) ❌")
        else:
            signals.append(f"Weak trend (ADX: {adx.iloc[-1]:.1f})")

        # MFI
        mfi_val = MFI(df).iloc[-1]
        if mfi_val > 80:
            signals.append(f"MFI: {mfi_val:.1f} ❌ Overbought")
        elif mfi_val < 20:
            signals.append(f"MFI: {mfi_val:.1f} ✅ Oversold")

        return "\n".join(signals)

    except Exception as e:
        return f"Error calculating indicators: {e}"
