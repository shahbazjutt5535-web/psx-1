"""
Technical Indicators for PSX Stock Bot
All indicators implemented from scratch
"""

import pandas as pd
import numpy as np

# ============================
# EXISTING INDICATORS (Keep all your existing ones)
# ============================

def SMA(data, period):
    """Simple Moving Average"""
    return data['close'].rolling(window=period).mean()

def EMA(data, period):
    """Exponential Moving Average"""
    return data['close'].ewm(span=period, adjust=False).mean()

def HMA(data, period):
    """Hull Moving Average"""
    half_length = int(period / 2)
    sqrt_length = int(np.sqrt(period))
    
    wma_half = (2 * data['close'].rolling(window=half_length).mean() - 
                data['close'].rolling(window=period).mean())
    hma = wma_half.rolling(window=sqrt_length).mean()
    return hma

def WMA(data, period):
    """Weighted Moving Average"""
    weights = np.arange(1, period + 1)
    def wma(arr):
        return np.dot(arr[-period:], weights) / weights.sum()
    return data['close'].rolling(window=period).apply(wma, raw=True)

def Ichimoku(data):
    """Ichimoku Cloud"""
    high9 = data['high'].rolling(window=9).max()
    low9 = data['low'].rolling(window=9).min()
    conversion = (high9 + low9) / 2
    
    high26 = data['high'].rolling(window=26).max()
    low26 = data['low'].rolling(window=26).min()
    base = (high26 + low26) / 2
    
    span_a = ((conversion + base) / 2).shift(26)
    
    high52 = data['high'].rolling(window=52).max()
    low52 = data['low'].rolling(window=52).min()
    span_b = ((high52 + low52) / 2).shift(26)
    
    return conversion, base, span_a, span_b

def SuperTrend(data, period=10, multiplier=3):
    """SuperTrend Indicator"""
    atr = ATR(data, period)
    
    hl_avg = (data['high'] + data['low']) / 2
    
    upper_band = hl_avg + (multiplier * atr)
    lower_band = hl_avg - (multiplier * atr)
    
    supertrend = pd.Series(index=data.index, dtype=float)
    trend = pd.Series(index=data.index, dtype=int)
    
    for i in range(period, len(data)):
        if i == period:
            supertrend.iloc[i] = upper_band.iloc[i]
            trend.iloc[i] = 1
            continue
            
        if data['close'].iloc[i-1] <= supertrend.iloc[i-1]:
            trend.iloc[i] = -1
            supertrend.iloc[i] = max(upper_band.iloc[i], supertrend.iloc[i-1])
        else:
            trend.iloc[i] = 1
            supertrend.iloc[i] = min(lower_band.iloc[i], supertrend.iloc[i-1])
    
    return supertrend

def ParabolicSAR(data, af_start=0.02, af_increment=0.02, af_max=0.2):
    """Parabolic SAR"""
    high = data['high']
    low = data['low']
    
    psar = pd.Series(index=data.index, dtype=float)
    trend = pd.Series(index=data.index, dtype=int)
    af = pd.Series(index=data.index, dtype=float)
    ep = pd.Series(index=data.index, dtype=float)
    
    for i in range(2, len(data)):
        if i == 2:
            if high.iloc[1] > high.iloc[0]:
                trend.iloc[i] = 1
                psar.iloc[i] = min(low.iloc[0], low.iloc[1])
                ep.iloc[i] = max(high.iloc[0], high.iloc[1])
            else:
                trend.iloc[i] = -1
                psar.iloc[i] = max(high.iloc[0], high.iloc[1])
                ep.iloc[i] = min(low.iloc[0], low.iloc[1])
            af.iloc[i] = af_start
            continue
        
        prev_psar = psar.iloc[i-1]
        prev_ep = ep.iloc[i-1]
        prev_af = af.iloc[i-1]
        
        if trend.iloc[i-1] == 1:
            psar.iloc[i] = prev_psar + prev_af * (prev_ep - prev_psar)
            psar.iloc[i] = min(psar.iloc[i], low.iloc[i-1], low.iloc[i])
            
            if high.iloc[i] > prev_ep:
                ep.iloc[i] = high.iloc[i]
                af.iloc[i] = min(prev_af + af_increment, af_max)
            else:
                ep.iloc[i] = prev_ep
                af.iloc[i] = prev_af
                
            if high.iloc[i] > psar.iloc[i]:
                trend.iloc[i] = 1
            else:
                trend.iloc[i] = -1
                psar.iloc[i] = prev_ep
                ep.iloc[i] = low.iloc[i]
                af.iloc[i] = af_start
        else:
            psar.iloc[i] = prev_psar - prev_af * (prev_psar - prev_ep)
            psar.iloc[i] = max(psar.iloc[i], high.iloc[i-1], high.iloc[i])
            
            if low.iloc[i] < prev_ep:
                ep.iloc[i] = low.iloc[i]
                af.iloc[i] = min(prev_af + af_increment, af_max)
            else:
                ep.iloc[i] = prev_ep
                af.iloc[i] = prev_af
                
            if low.iloc[i] < psar.iloc[i]:
                trend.iloc[i] = -1
            else:
                trend.iloc[i] = 1
                psar.iloc[i] = prev_ep
                ep.iloc[i] = high.iloc[i]
                af.iloc[i] = af_start
    
    return psar

def MACD(data, fast=12, slow=26, signal=9):
    """MACD Indicator"""
    ema_fast = EMA(data, fast)
    ema_slow = EMA(data, slow)
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram

def RSI(data, period=14):
    """Relative Strength Index"""
    delta = data['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def Stochastic(data, k_period=14, d_period=3):
    """Stochastic Oscillator"""
    low_min = data['low'].rolling(window=k_period).min()
    high_max = data['high'].rolling(window=k_period).max()
    
    k_fast = 100 * ((data['close'] - low_min) / (high_max - low_min))
    k_slow = k_fast.rolling(window=d_period).mean()
    d_slow = k_slow.rolling(window=d_period).mean()
    
    return k_fast, d_slow  # Return %K and %D (not %K slow)

def KDJ(data, k_period=9, d_period=3, j_period=3):
    """KDJ Indicator"""
    low_min = data['low'].rolling(window=k_period).min()
    high_max = data['high'].rolling(window=k_period).max()
    
    rsv = 100 * ((data['close'] - low_min) / (high_max - low_min))
    k_value = rsv.rolling(window=d_period).mean()
    d_value = k_value.rolling(window=j_period).mean()
    j_value = 3 * k_value - 2 * d_value
    
    return k_value, d_value, j_value

def WilliamsR(data, period=14):
    """Williams %R"""
    high_max = data['high'].rolling(window=period).max()
    low_min = data['low'].rolling(window=period).min()
    williams_r = -100 * ((high_max - data['close']) / (high_max - low_min))
    return williams_r

def CCI(data, period=20):
    """Commodity Channel Index"""
    tp = (data['high'] + data['low'] + data['close']) / 3
    sma_tp = tp.rolling(window=period).mean()
    mad_tp = tp.rolling(window=period).apply(lambda x: np.abs(x - x.mean()).mean())
    cci = (tp - sma_tp) / (0.015 * mad_tp)
    return cci

def ROC(data, period=12):
    """Rate of Change"""
    return data['close'].pct_change(periods=period) * 100

def ADX(data, period=14):
    """Average Directional Index"""
    high = data['high']
    low = data['low']
    close = data['close']
    
    plus_dm = high.diff()
    minus_dm = low.diff()
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm > 0] = 0
    
    tr = pd.concat([high - low, 
                    (high - close.shift()).abs(), 
                    (low - close.shift()).abs()], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    
    plus_di = 100 * (plus_dm.ewm(alpha=1/period).mean() / atr)
    minus_di = abs(100 * (minus_dm.ewm(alpha=1/period).mean() / atr))
    
    dx = (abs(plus_di - minus_di) / (plus_di + minus_di)) * 100
    adx = dx.rolling(window=period).mean()
    
    return adx, plus_di, minus_di

def UltimateOscillator(data, period1=7, period2=14, period3=28):
    """Ultimate Oscillator"""
    high = data['high']
    low = data['low']
    close = data['close']
    
    bp = close - pd.concat([low, close.shift()], axis=1).min(axis=1)
    tr = pd.concat([high - low, 
                    (high - close.shift()).abs(), 
                    (low - close.shift()).abs()], axis=1).max(axis=1)
    
    avg1 = bp.rolling(window=period1).sum() / tr.rolling(window=period1).sum()
    avg2 = bp.rolling(window=period2).sum() / tr.rolling(window=period2).sum()
    avg3 = bp.rolling(window=period3).sum() / tr.rolling(window=period3).sum()
    
    uo = 100 * (4 * avg1 + 2 * avg2 + avg3) / 7
    return uo

def OBV(data):
    """On-Balance Volume"""
    obv = (np.sign(data['close'].diff()) * data['volume']).fillna(0).cumsum()
    return obv

def MFI(data, period=14):
    """Money Flow Index"""
    typical_price = (data['high'] + data['low'] + data['close']) / 3
    money_flow = typical_price * data['volume']
    
    positive_flow = pd.Series(0, index=data.index)
    negative_flow = pd.Series(0, index=data.index)
    
    price_diff = typical_price.diff()
    positive_flow[price_diff > 0] = money_flow[price_diff > 0]
    negative_flow[price_diff < 0] = money_flow[price_diff < 0]
    
    pos_sum = positive_flow.rolling(window=period).sum()
    neg_sum = negative_flow.rolling(window=period).sum()
    
    mfi = 100 - (100 / (1 + (pos_sum / neg_sum)))
    return mfi

def VWAP(data):
    """Volume Weighted Average Price"""
    typical_price = (data['high'] + data['low'] + data['close']) / 3
    vwap = (typical_price * data['volume']).cumsum() / data['volume'].cumsum()
    return vwap

def Aroon(data, period=25):
    """Aroon Indicator"""
    aroon_up = 100 * (period - data['high'].rolling(window=period+1).apply(lambda x: x.argmax())) / period
    aroon_down = 100 * (period - data['low'].rolling(window=period+1).apply(lambda x: x.argmin())) / period
    return aroon_up, aroon_down

def Bollinger_Bands(data, period=20, std_dev=2):
    """Bollinger Bands"""
    middle = SMA(data, period)
    std = data['close'].rolling(window=period).std()
    upper = middle + (std * std_dev)
    lower = middle - (std * std_dev)
    return upper, middle, lower

def ATR(data, period=14):
    """Average True Range"""
    high = data['high']
    low = data['low']
    close = data['close']
    
    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    return atr

def HeikinAshi(data):
    """Heikin Ashi Close"""
    ha_close = (data['open'] + data['high'] + data['low'] + data['close']) / 4
    return ha_close

def DonchianChannel(data, period=20):
    """Donchian Channel"""
    upper = data['high'].rolling(window=period).max()
    lower = data['low'].rolling(window=period).min()
    middle = (upper + lower) / 2
    return upper, middle, lower

# ============================
# NEW INDICATORS TO ADD
# ============================

# 1. RSI 7 (Fast RSI)
def RSI_7(data):
    """Fast RSI with period 7"""
    return RSI(data, period=7)

# 2. Stochastic 9,6,3
def Stochastic_9_6_3(data):
    """Stochastic with custom periods (9,6,3)"""
    low_min = data['low'].rolling(window=9).min()
    high_max = data['high'].rolling(window=9).max()
    
    k_fast = 100 * ((data['close'] - low_min) / (high_max - low_min))
    k_slow = k_fast.rolling(window=6).mean()
    d_slow = k_slow.rolling(window=3).mean()
    
    return k_fast, k_slow, d_slow

# 3. Stochastic RSI
def Stochastic_RSI(data, period=14, smooth_k=3, smooth_d=3):
    """Stochastic RSI"""
    rsi_val = RSI(data, period)
    
    min_rsi = rsi_val.rolling(window=period).min()
    max_rsi = rsi_val.rolling(window=period).max()
    
    stoch_rsi = 100 * ((rsi_val - min_rsi) / (max_rsi - min_rsi))
    
    k = stoch_rsi.rolling(window=smooth_k).mean()
    d = k.rolling(window=smooth_d).mean()
    
    return k, d

# 4. TDI (Traders Dynamic Index)
def TDI(data, rsi_period=13, volatility_band_period=34, signal_line_period=34):
    """Traders Dynamic Index"""
    # RSI Line
    rsi_val = RSI(data, rsi_period)
    
    # Volatility Bands (based on RSI)
    rsi_std = rsi_val.rolling(window=volatility_band_period).std()
    upper_band = rsi_val + rsi_std
    lower_band = rsi_val - rsi_std
    
    # Signal Line (EMA of RSI)
    signal_line = EMA(pd.DataFrame({'close': rsi_val}), signal_line_period)
    
    # Market Base Line
    market_base = EMA(pd.DataFrame({'close': rsi_val}), volatility_band_period)
    
    return rsi_val, upper_band, lower_band, signal_line, market_base

# 5. VWAP with HLC3 source
def VWAP_HLC3(data):
    """VWAP using HLC3 instead of typical price"""
    hlc3 = (data['high'] + data['low'] + data['close']) / 3
    vwap = (hlc3 * data['volume']).cumsum() / data['volume'].cumsum()
    return vwap

# 6. VWAP Bands
def VWAP_Bands(data, std_dev_1=1, std_dev_2=2):
    """VWAP with standard deviation bands"""
    vwap = VWAP_HLC3(data)
    
    # Calculate standard deviation of price from VWAP
    typical_price = (data['high'] + data['low'] + data['close']) / 3
    price_vwap_diff = typical_price - vwap
    sq_diff = price_vwap_diff ** 2
    
    # Rolling standard deviation
    variance = sq_diff.rolling(window=20).mean()
    std_dev = np.sqrt(variance)
    
    # Bands for both standard deviations
    upper_band_1 = vwap + (std_dev * std_dev_1)
    lower_band_1 = vwap - (std_dev * std_dev_1)
    upper_band_2 = vwap + (std_dev * std_dev_2)
    lower_band_2 = vwap - (std_dev * std_dev_2)
    
    return vwap, upper_band_1, lower_band_1, upper_band_2, lower_band_2

# 7. Anchored VWAP (Simplified - Anchor at first bar of data)
def Anchored_VWAP(data, anchor_idx=0):
    """Anchored VWAP - anchor at specified index"""
    hlc3 = (data['high'] + data['low'] + data['close']) / 3
    
    # Create cumulative sums from anchor point
    cum_vol = data['volume'].iloc[anchor_idx:].cumsum()
    cum_vol_price = (hlc3.iloc[anchor_idx:] * data['volume'].iloc[anchor_idx:]).cumsum()
    
    anchored_vwap = pd.Series(index=data.index, dtype=float)
    anchored_vwap.iloc[anchor_idx:] = cum_vol_price / cum_vol
    
    # Forward fill for earlier periods
    anchored_vwap.iloc[:anchor_idx] = np.nan
    
    return anchored_vwap

# 8. Volume Moving Average
def Volume_MA(data, period=20):
    """Volume Moving Average"""
    return data['volume'].rolling(window=period).mean()

# 9. Volume Oscillator
def Volume_Oscillator(data, short_period=5, long_period=20):
    """Volume Oscillator"""
    short_ma = data['volume'].rolling(window=short_period).mean()
    long_ma = data['volume'].rolling(window=long_period).mean()
    
    volume_osc = ((short_ma - long_ma) / long_ma) * 100
    return volume_osc

# 10. VOLT (Volume-Weighted Average True Range) - Simplified
def VOLT(data, period=10):
    """VOLT Indicator - Volume-Weighted ATR"""
    # Calculate True Range
    high = data['high']
    low = data['low']
    close = data['close']
    
    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    # Volume-weighted TR average
    volt = (tr * data['volume']).rolling(window=period).sum() / data['volume'].rolling(window=period).sum()
    
    return volt

# 11. Volume Profile (Simplified - Fixed Range)
def Volume_Profile(data, num_bins=12):
    """Simplified Volume Profile - divides price range into bins"""
    if len(data) < 20:
        return None, None, None
    
    # Use last 20-50 periods for profile
    lookback = min(50, len(data))
    recent_data = data.iloc[-lookback:]
    
    price_min = recent_data['low'].min()
    price_max = recent_data['high'].max()
    
    # Create price bins
    bin_edges = np.linspace(price_min, price_max, num_bins + 1)
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
    
    # Distribute volume across bins
    volume_profile = np.zeros(num_bins)
    
    for i in range(len(recent_data)):
        candle_low = recent_data['low'].iloc[i]
        candle_high = recent_data['high'].iloc[i]
        candle_volume = recent_data['volume'].iloc[i]
        
        # Find bins that overlap with candle range
        for j in range(num_bins):
            bin_low = bin_edges[j]
            bin_high = bin_edges[j + 1]
            
            # Check overlap
            if candle_high > bin_low and candle_low < bin_high:
                overlap_min = max(candle_low, bin_low)
                overlap_max = min(candle_high, bin_high)
                overlap_range = overlap_max - overlap_min
                candle_range = candle_high - candle_low
                
                if candle_range > 0:
                    volume_profile[j] += candle_volume * (overlap_range / candle_range)
    
    # Find POC (Point of Control)
    poc_index = np.argmax(volume_profile)
    poc_price = bin_centers[poc_index]
    poc_volume = volume_profile[poc_index]
    
    # Value Area (70% of volume)
    total_vol = volume_profile.sum()
    target_vol = total_vol * 0.7
    
    # Sort bins by volume for value area
    sorted_indices = np.argsort(volume_profile)[::-1]
    cum_vol = 0
    value_area_bins = []
    
    for idx in sorted_indices:
        value_area_bins.append(idx)
        cum_vol += volume_profile[idx]
        if cum_vol >= target_vol:
            break
    
    if value_area_bins:
        va_low = bin_edges[min(value_area_bins)]
        va_high = bin_edges[max(value_area_bins) + 1]
    else:
        va_low = va_high = poc_price
    
    return poc_price, va_low, va_high, bin_centers, volume_profile

# 12. Market Profile (Simplified - TPO based on 30-min periods)
def Market_Profile(data, time_period=30):
    """Simplified Market Profile using Time Price Opportunities"""
    if len(data) < 10:
        return None, None, None, None
    
    # Group data into time periods (for intraday)
    # For simplicity, we'll use index position as time
    tpo_counts = {}
    price_levels = {}
    
    for i in range(len(data)):
        # Determine time period (group every 'time_period' candles)
        time_group = i // time_period
        
        # Get high and low for this candle
        candle_high = data['high'].iloc[i]
        candle_low = data['low'].iloc[i]
        
        # Round to nearest 0.5 for price levels (simplified)
        price_step = 0.5
        price_min = round(candle_low / price_step) * price_step
        price_max = round(candle_high / price_step) * price_step
        
        # Add TPOs for each price level
        price_level = price_min
        while price_level <= price_max:
            key = (time_group, round(price_level, 2))
            tpo_counts[key] = tpo_counts.get(key, 0) + 1
            price_levels[round(price_level, 2)] = True
            price_level += price_step
    
    # Find POC (most TPOs)
    if tpo_counts:
        poc_price = max(tpo_counts, key=tpo_counts.get)[1]
        return poc_price, sorted(price_levels.keys())
    
    return None, None

# ============================
# FIBONACCI FUNCTIONS
# ============================

def Fibonacci_Retracement(data, lookback=50):
    """Fibonacci Retracement levels from recent swing high/low"""
    if len(data) < lookback:
        return None
    
    recent_data = data.iloc[-lookback:]
    
    # Find swing high and low
    swing_high = recent_data['high'].max()
    swing_low = recent_data['low'].min()
    current_price = data['close'].iloc[-1]
    
    diff = swing_high - swing_low
    
    if diff == 0:
        return None
    
    # Fibonacci levels
    levels = {
        0.236: swing_high - (diff * 0.236),
        0.382: swing_high - (diff * 0.382),
        0.5: swing_high - (diff * 0.5),
        0.618: swing_high - (diff * 0.618),
        0.786: swing_high - (diff * 0.786)
    }
    
    # Determine current level
    current_level = None
    for level, price in sorted(levels.items(), reverse=True):
        if current_price <= price:
            current_level = level
            break
    
    return swing_high, swing_low, levels, current_level

def Fibonacci_Extension(data, lookback=50):
    """Fibonacci Extension levels from recent trend"""
    if len(data) < lookback:
        return None
    
    recent_data = data.iloc[-lookback:]
    
    # Find three points: start of move (low), end of move (high), retracement (low)
    # Simplified: use min, max, and current retracement
    price_min = recent_data['low'].min()
    price_max = recent_data['high'].max()
    price_current = data['close'].iloc[-1]
    
    # Find the retracement point after the high
    high_idx = recent_data['high'].idxmax()
    high_pos = recent_data.index.get_loc(high_idx)
    
    if high_pos < len(recent_data) - 1:
        # Look for retracement low after the high
        after_high = recent_data.iloc[high_pos:]
        retrace_low = after_high['low'].min()
    else:
        retrace_low = price_min
    
    move_ab = price_max - price_min
    move_bc = price_max - retrace_low
    
    if move_ab == 0:
        return None
    
    # Extension levels
    extensions = {
        0.618: price_max + (move_ab * 0.618),
        1.0: price_max + move_ab,
        1.272: price_max + (move_ab * 1.272),
        1.618: price_max + (move_ab * 1.618),
        2.0: price_max + (move_ab * 2.0),
        2.618: price_max + (move_ab * 2.618)
    }
    
    return price_min, price_max, retrace_low, extensions
