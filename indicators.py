import pandas as pd
import numpy as np

# -----------------------------
# Moving Averages
# -----------------------------

def SMA(series, period):
    return series.rolling(period).mean()

def EMA(series, period):
    return series.ewm(span=period, adjust=False).mean()

def WMA(series, period):
    weights = np.arange(1, period+1)
    return series.rolling(period).apply(lambda prices: np.dot(prices, weights)/weights.sum(), raw=True)

def HMA(series, period):
    half = int(period/2)
    sqrt = int(np.sqrt(period))
    wma1 = WMA(series, half)
    wma2 = WMA(series, period)
    return WMA(2*wma1 - wma2, sqrt)

# -----------------------------
# RSI
# -----------------------------

def RSI(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()

    rs = avg_gain / avg_loss
    return 100 - (100/(1+rs))

# -----------------------------
# MACD
# -----------------------------

def MACD(series, fast=12, slow=26, signal=9):
    ema_fast = EMA(series, fast)
    ema_slow = EMA(series, slow)

    macd = ema_fast - ema_slow
    signal_line = EMA(macd, signal)

    hist = macd - signal_line

    return macd, signal_line, hist

# -----------------------------
# ATR
# -----------------------------

def ATR(df, period=14):

    high_low = df['high'] - df['low']
    high_close = abs(df['high'] - df['close'].shift())
    low_close = abs(df['low'] - df['close'].shift())

    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)

    return tr.rolling(period).mean()

# -----------------------------
# Bollinger Bands
# -----------------------------

def bollinger(series, period=20):

    mid = SMA(series, period)
    std = series.rolling(period).std()

    upper = mid + 2*std
    lower = mid - 2*std

    return upper, mid, lower

# -----------------------------
# Stochastic RSI
# -----------------------------

def stochastic_rsi(series, period=14, smoothK=3, smoothD=3):

    rsi = RSI(series, period)

    min_rsi = rsi.rolling(period).min()
    max_rsi = rsi.rolling(period).max()

    stoch = (rsi - min_rsi)/(max_rsi-min_rsi)

    K = stoch.rolling(smoothK).mean()*100
    D = K.rolling(smoothD).mean()

    return K, D

# -----------------------------
# Williams %R
# -----------------------------

def williams_r(df, period=14):

    high = df['high'].rolling(period).max()
    low = df['low'].rolling(period).min()

    return -100 * (high - df['close'])/(high-low)

# -----------------------------
# CCI
# -----------------------------

def CCI(df, period=20):

    tp = (df['high'] + df['low'] + df['close'])/3

    sma = tp.rolling(period).mean()

    mad = tp.rolling(period).apply(lambda x: np.mean(np.abs(x-np.mean(x))))

    return (tp-sma)/(0.015*mad)

# -----------------------------
# ROC
# -----------------------------

def ROC(series, period=12):

    return ((series-series.shift(period))/series.shift(period))*100

# -----------------------------
# Momentum
# -----------------------------

def MOM(series, period=10):

    return series-series.shift(period)

# -----------------------------
# OBV
# -----------------------------

def OBV(df):

    obv=[0]

    for i in range(1,len(df)):

        if df['close'][i]>df['close'][i-1]:
            obv.append(obv[-1]+df['volume'][i])

        elif df['close'][i]<df['close'][i-1]:
            obv.append(obv[-1]-df['volume'][i])

        else:
            obv.append(obv[-1])

    return pd.Series(obv,index=df.index)

# -----------------------------
# Money Flow Index
# -----------------------------

def MFI(df, period=14):

    tp=(df['high']+df['low']+df['close'])/3
    mf=tp*df['volume']

    positive=[]
    negative=[]

    for i in range(1,len(tp)):

        if tp[i]>tp[i-1]:
            positive.append(mf[i])
            negative.append(0)

        else:
            positive.append(0)
            negative.append(mf[i])

    pos=pd.Series(positive).rolling(period).sum()
    neg=pd.Series(negative).rolling(period).sum()

    mfr=pos/neg

    return 100-(100/(1+mfr))

# -----------------------------
# VWAP
# -----------------------------

def VWAP(df):

    tp=(df['high']+df['low']+df['close'])/3

    vwap=(tp*df['volume']).cumsum()/df['volume'].cumsum()

    return vwap
