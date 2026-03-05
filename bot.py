"""
PSX Stock Indicator Telegram Bot
UPDATED VERSION - Complete indicators with formatted output
"""

import os
import logging
import threading
import pandas as pd
import numpy as np
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import nest_asyncio
import asyncio
import time
from datetime import datetime
import functools

# Apply nest_asyncio for Render deployment
nest_asyncio.apply()

# -------------------------
# FIX: Patch input() before importing tvDatafeed
# -------------------------
import builtins
original_input = builtins.input
builtins.input = lambda prompt='': 'y'

# Import tvDatafeed
try:
    from tvDatafeed import TvDatafeed, Interval
    print("✅ tvDatafeed imported successfully")
except Exception as e:
    print(f"❌ Failed to import tvDatafeed: {e}")
    raise

# Import all indicators
from indicators import *

# Restore input
builtins.input = original_input

# -------------------------
# Logging Setup
# -------------------------
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# -------------------------
# Environment Variables
# -------------------------
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN environment variable not set")

# -------------------------
# TradingView Initialization
# -------------------------
def init_tvdatafeed():
    """Initialize TvDatafeed with multiple fallback methods"""
    
    # Method 1: Simple initialization
    try:
        tv = TvDatafeed()
        logger.info("✅ TvDatafeed initialized successfully")
        return tv
    except Exception as e:
        logger.warning(f"Method 1 failed: {e}")
    
    # Method 2: With auto_login=False
    try:
        tv = TvDatafeed(auto_login=False)
        logger.info("✅ TvDatafeed initialized with auto_login=False")
        return tv
    except Exception as e:
        logger.warning(f"Method 2 failed: {e}")
    
    # Method 3: Explicit None credentials
    try:
        tv = TvDatafeed(username=None, password=None)
        logger.info("✅ TvDatafeed initialized with None credentials")
        return tv
    except Exception as e:
        logger.warning(f"Method 3 failed: {e}")
    
    # If all methods fail
    raise Exception("❌ All TvDatafeed initialization methods failed")

# Initialize TvDatafeed
try:
    tv = init_tvdatafeed()
except Exception as e:
    logger.error(f"Fatal: Could not initialize TvDatafeed: {e}")
    raise

# -------------------------
# Interval Mapping
# -------------------------
interval_map = {
    "15m": Interval.in_15_minute,
    "30m": Interval.in_30_minute,
    "1h": Interval.in_1_hour,
    "2h": Interval.in_2_hour,
    "4h": Interval.in_4_hour,
    "1d": Interval.in_daily,
    "1w": Interval.in_weekly,
}

# Expanded PSX Stocks with TradingView symbols
stocks = [
    {"symbol": "FFC", "name": "Fauji Fertilizer Company", "tv_symbol": "PSX:FFC"},
    {"symbol": "ENGROH", "name": "Engro Holdings", "tv_symbol": "PSX:ENGROH"},
    {"symbol": "OGDC", "name": "Oil & Gas Development Company", "tv_symbol": "PSX:OGDC"},
    {"symbol": "HUBC", "name": "Hub Power Company", "tv_symbol": "PSX:HUBC"},
    {"symbol": "PPL", "name": "Pakistan Petroleum Limited", "tv_symbol": "PSX:PPL"},
    {"symbol": "NBP", "name": "National Bank of Pakistan", "tv_symbol": "PSX:NBP"},
    {"symbol": "UBL", "name": "United Bank Limited", "tv_symbol": "PSX:UBL"},
    {"symbol": "MEZNPETF", "name": "Meezan Pakistan ETF", "tv_symbol": "PSX:MEZNPETF"},
    {"symbol": "NBPGETF", "name": "NBP Pakistan Growth ETF", "tv_symbol": "PSX:NBPGETF"},
    {"symbol": "KEL", "name": "K-Electric", "tv_symbol": "PSX:KEL"},
    {"symbol": "SYS", "name": "Systems Limited", "tv_symbol": "PSX:SYS"},
    {"symbol": "LUCK", "name": "Lucky Cement", "tv_symbol": "PSX:LUCK"},
    {"symbol": "PSO", "name": "Pakistan State Oil", "tv_symbol": "PSX:PSO"},
    {"symbol": "GOLD", "name": "Gold", "tv_symbol": "TVC:GOLD"},
]

# -------------------------
# Format number helper
# -------------------------
def format_number(value):
    """Format number to 2 decimal places if not NaN"""
    if pd.isna(value):
        return "N/A"
    if isinstance(value, (int, float)):
        if abs(value) > 1000000:
            return f"{value/1000000:.2f}M"
        elif abs(value) > 1000:
            return f"{value/1000:.2f}K"
        return f"{value:.2f}"
    return str(value)

def format_price(value):
    """Format price to 2 decimal places"""
    return f"{value:.2f}" if not pd.isna(value) else "N/A"

def format_percent(value):
    """Format percentage"""
    return f"{value:.2f}%" if not pd.isna(value) else "N/A"

# -------------------------
# UPDATED: Command Generator with Complete Indicators
# -------------------------
def create_stock_command(stock_info, interval_key):
    """Create a command handler with complete indicators"""
    symbol = stock_info["symbol"]
    tv_symbol = stock_info["tv_symbol"]
    company_name = stock_info["name"]
    
    async def command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Send immediate acknowledgment
        await update.message.reply_text(f"⏳ Fetching {company_name} ({interval_key}) data... This may take 10-15 seconds.")
        
        try:
            # Run in thread pool with timeout
            loop = asyncio.get_event_loop()
            
            try:
                # Fetch data with timeout
                df = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        lambda: tv.get_hist(
                            symbol=tv_symbol,
                            interval=interval_map[interval_key],
                            n_bars=300  # Get more bars for accurate indicators
                        )
                    ),
                    timeout=25.0
                )
            except asyncio.TimeoutError:
                logger.error(f"Timeout fetching {symbol} {interval_key}")
                await update.message.reply_text(f"❌ Request timed out. TradingView is taking too long to respond. Please try again.")
                return
            
            # Validate data
            if df is None or df.empty:
                await update.message.reply_text(f"❌ No data found for {company_name}.")
                return
            
            if len(df) < 100:
                await update.message.reply_text(f"⚠️ Insufficient data for {company_name}. Only {len(df)} bars available.")
                return
            
            # Calculate all indicators
            # Market Overview
            current_price = df['close'].iloc[-1]
            open_price = df['open'].iloc[-1]
            high_24h = df['high'].iloc[-1]
            low_24h = df['low'].iloc[-1]
            volume = df['volume'].iloc[-1]
            prev_close = df['close'].iloc[-2] if len(df) > 1 else current_price
            change_points = current_price - prev_close
            change_percent = (change_points / prev_close) * 100
            
            # Moving Averages
            sma_10 = SMA(df, 10).iloc[-1]
            sma_20 = SMA(df, 20).iloc[-1]
            sma_50 = SMA(df, 50).iloc[-1]
            sma_200 = SMA(df, 200).iloc[-1] if len(df) >= 200 else np.nan
            
            ema_9 = EMA(df, 9).iloc[-1]
            ema_21 = EMA(df, 21).iloc[-1]
            ema_50 = EMA(df, 50).iloc[-1]
            ema_200 = EMA(df, 200).iloc[-1] if len(df) >= 200 else np.nan
            
            wma_8 = WMA(df, 8).iloc[-1]
            wma_20 = WMA(df, 20).iloc[-1]
            wma_50 = WMA(df, 50).iloc[-1]
            wma_100 = WMA(df, 100).iloc[-1] if len(df) >= 100 else np.nan
            
            hma_9 = HMA(df, 9).iloc[-1]
            hma_14 = HMA(df, 14).iloc[-1]
            hma_21 = HMA(df, 21).iloc[-1]
            
            # Ichimoku
            conv_line, base_line, span_a, span_b = Ichimoku(df)
            
            # SuperTrend
            supertrend_7 = SuperTrend(df, 7, 3).iloc[-1]
            supertrend_10 = SuperTrend(df, 10, 3).iloc[-1]
            supertrend_14 = SuperTrend(df, 14, 3).iloc[-1]
            
            # Parabolic SAR
            psar = Parabolic_SAR(df, 0.02, 0.2).iloc[-1]
            
            # MACD
            macd_6_13_5, macd_signal_6_13_5, macd_hist_6_13_5 = MACD(df, 6, 13, 5)
            macd_12_26_9, macd_signal_12_26_9, macd_hist_12_26_9 = MACD(df, 12, 26, 9)
            
            # VW-MACD
            vw_macd, vw_signal, vw_hist = VW_MACD(df)
            
            # RSI
            rsi_3 = RSI(df, 3).iloc[-1]
            rsi_10 = RSI(df, 10).iloc[-1]
            rsi_14 = RSI(df, 14).iloc[-1]
            
            # RVI
            rvi_14, rvi_signal_4 = RVI(df, 14)
            rvi_10, _ = RVI(df, 10)
            
            # Stochastic RSI
            stoch_k_14, stoch_d_14 = Stochastic_RSI(df, 14, 3, 3)
            
            # KDJ
            kdj_k, kdj_d, kdj_j = KDJ(df, 9, 3, 3)
            
            # Williams %R
            williams_12 = Williams_R(df, 12).iloc[-1]
            williams_25 = Williams_R(df, 25).iloc[-1]
            
            # CCI
            cci_14 = CCI(df, 14).iloc[-1]
            cci_20 = CCI(df, 20).iloc[-1]
            
            # ROC
            roc_14 = ROC(df, 14).iloc[-1]
            roc_25 = ROC(df, 25).iloc[-1]
            
            # Momentum
            mom_10 = MOM(df, 10).iloc[-1]
            mom_20 = MOM(df, 20).iloc[-1]
            
            # Ultimate Oscillator
            uo = Ultimate_Oscillator(df).iloc[-1]
            
            # ADX
            adx_14, plus_di_14, minus_di_14 = ADX(df, 14)
            
            # TDI
            tdi_rsi, tdi_vol, tdi_signal = TDI(df)
            
            # OBV
            obv = OBV(df).iloc[-1]
            
            # ADOSC
            adosc = ADOSC(df).iloc[-1]
            
            # MFI
            mfi_14 = MFI(df, 14).iloc[-1]
            
            # Aroon
            aroon_up_14, aroon_down_14 = Aroon(df, 14)
            
            # VWAP
            vwap = VWAP(df).iloc[-1]
            vwap_3 = (df['close'] * df['volume']).rolling(3).sum() / df['volume'].rolling(3).sum()
            vwap_4 = (df['close'] * df['volume']).rolling(4).sum() / df['volume'].rolling(4).sum()
            
            # Bollinger Bands
            bb_upper, bb_middle, bb_lower = Bollinger_Bands(df, 20, 2)
            
            # Fibonacci Bollinger Bands
            fib_bb = Fib_Bollinger_Bands(df, 20)
            
            # Keltner Channel
            kc_upper, kc_middle, kc_lower = Keltner_Channel(df, 20, 10, 2)
            
            # ATR
            atr_14 = ATR(df, 14).iloc[-1]
            
            # Heikin Ashi
            ha_close, ha_open, ha_high, ha_low = Heikin_Ashi(df)
            
            # Choppiness Index
            chop_14 = Choppiness_Index(df, 14).iloc[-1]
            chop_21 = Choppiness_Index(df, 21).iloc[-1]
            
            # TRIX
            trix_10, trix_signal_7 = TRIX(df, 10)
            trix_14, trix_signal_9 = TRIX(df, 14)
            
            # Donchian Channel
            donchian_upper, donchian_middle, donchian_lower = Donchian_Channel(df, 20)
            
            # Format the complete message
            message = (
                f"📊 *{company_name} - {tv_symbol} ({interval_key})*\n\n"
                
                f"1️⃣ *Market Overview*\n"
                f"💰 Price: `{format_price(current_price)}`\n"
                f"🔓 Open Price: `{format_price(open_price)}`\n"
                f"📈 24h High: `{format_price(high_24h)}`\n"
                f"📉 24h Low: `{format_price(low_24h)}`\n"
                f"🔁 Change: `{format_price(change_points)} ({format_percent(change_percent)})`\n"
                f"🧮 Volume: `{format_number(volume)}`\n"
                f"⏰ Close Time: `{df.index[-1].strftime('%Y-%m-%d %H:%M')}`\n\n"
                
                f"2️⃣ *Trend Direction*\n\n"
                f"📊 *Simple Moving Averages (SMA):*\n"
                f" - SMA 10: `{format_price(sma_10)}`\n"
                f" - SMA 20: `{format_price(sma_20)}`\n"
                f" - SMA 50: `{format_price(sma_50)}`\n"
                f" - SMA 200: `{format_price(sma_200)}`\n\n"
                
                f"📈 *Exponential Moving Averages (EMA):*\n"
                f" - EMA 9: `{format_price(ema_9)}`\n"
                f" - EMA 21: `{format_price(ema_21)}`\n"
                f" - EMA 50: `{format_price(ema_50)}`\n"
                f" - EMA 200: `{format_price(ema_200)}`\n\n"
                
                f"⚖️ *Weighted Moving Averages (WMA):*\n"
                f" - WMA 8: `{format_price(wma_8)}`\n"
                f" - WMA 20: `{format_price(wma_20)}`\n"
                f" - WMA 50: `{format_price(wma_50)}`\n"
                f" - WMA 100: `{format_price(wma_100)}`\n\n"
                
                f"📈 *Hull Moving Average:*\n"
                f"  (HMA 9): `{format_price(hma_9)}`\n"
                f"  (HMA 14): `{format_price(hma_14)}`\n"
                f"  (HMA 21): `{format_price(hma_21)}`\n\n"
                
                f"📊 *Ichimoku Cloud:*\n"
                f" - Conversion Line (9): `{format_price(conv_line.iloc[-1])}`\n"
                f" - Base Line (26): `{format_price(base_line.iloc[-1])}`\n"
                f" - Leading Span A: `{format_price(span_a.iloc[-1])}`\n"
                f" - Leading Span B: `{format_price(span_b.iloc[-1])}`\n\n"
                
                f"📈 *SuperTrend:*\n"
                f" - Value(7): `{format_price(supertrend_7)}`\n"
                f" - Value(10): `{format_price(supertrend_10)}`\n"
                f" - Value(14): `{format_price(supertrend_14)}`\n\n"
                
                f"📈 *Parabolic SAR:*\n"
                f" - Step AF Value(0.02): `{format_price(psar)}`\n"
                f" - Max AF Value(0.20): `{format_price(psar)}`\n\n"
                
                f"3️⃣ *Momentum Strength*\n\n"
                f"📉 *MACD: 6,13,5*\n"
                f" - MACD: `{format_price(macd_6_13_5.iloc[-1])}`\n"
                f" - Signal: `{format_price(macd_signal_6_13_5.iloc[-1])}`\n"
                f" - Histogram: `{format_price(macd_hist_6_13_5.iloc[-1])}`\n\n"
                
                f"📉 *MACD: 12,26,9*\n"
                f" - MACD: `{format_price(macd_12_26_9.iloc[-1])}`\n"
                f" - Signal: `{format_price(macd_signal_12_26_9.iloc[-1])}`\n"
                f" - Histogram: `{format_price(macd_hist_12_26_9.iloc[-1])}`\n\n"
                
                f"📊 *Volume-Weighted MACD (VW-MACD):*\n"
                f" - VW-MACD: `{format_price(vw_macd.iloc[-1])}`\n"
                f" - VW-Signal: `{format_price(vw_signal.iloc[-1])}`\n"
                f" - VW-Histogram: `{format_price(vw_hist.iloc[-1])}`\n\n"
                
                f"⚡ *Relative Strength Index (RSI):*\n"
                f" - RSI (3): `{format_price(rsi_3)}`\n"
                f" - RSI (10): `{format_price(rsi_10)}`\n"
                f" - RSI (14): `{format_price(rsi_14)}`\n\n"
                
                f"📊 *Relative Volatility Index (RVI):*\n"
                f" - RVI (14): `{format_price(rvi_14.iloc[-1])}`\n"
                f" - RVI (10): `{format_price(rvi_10.iloc[-1])}`\n"
                f" - Signal Line(4): `{format_price(rvi_signal_4.iloc[-1])}`\n\n"
                
                f"📉 *Stochastic RSI (14,3,3)(0.8)level):*\n"
                f" - %K: `{format_price(stoch_k_14.iloc[-1])}`\n"
                f" - %D: `{format_price(stoch_d_14.iloc[-1])}`\n\n"
                
                f"📊 *KDJ (9,3,3):*\n"
                f" - K: `{format_price(kdj_k.iloc[-1])}`\n"
                f" - D: `{format_price(kdj_d.iloc[-1])}`\n"
                f" - J: `{format_price(kdj_j.iloc[-1])}`\n\n"
                
                f"📉 *Williams %R Indicator:*\n"
                f" - Williams %R (12): `{format_price(williams_12)}`\n"
                f" - Williams %R (25): `{format_price(williams_25)}`\n\n"
                
                f"📘 *Commodity Channel Index (CCI):*\n"
                f" - CCI (14): `{format_price(cci_14)}`\n"
                f" - CCI (20): `{format_price(cci_20)}`\n\n"
                
                f"📊 *Rate of Change (ROC):*\n"
                f" - ROC (14): `{format_percent(roc_14)}`\n"
                f" - ROC (25): `{format_percent(roc_25)}`\n\n"
                
                f"📈 *Momentum (MTM):*\n"
                f" - MTM (10): `{format_price(mom_10)}`\n"
                f" - MTM (20): `{format_price(mom_20)}`\n\n"
                
                f"🧭 *Ultimate Oscillator:*\n"
                f" - UO (7,14,28): `{format_price(uo)}`\n\n"
                
                f"📊 *ADX (Trend Strength):*\n"
                f" - ADX (14): `{format_price(adx_14.iloc[-1])}`\n"
                f" - +DI (14): `{format_price(plus_di_14.iloc[-1])}`\n"
                f" - -DI (14): `{format_price(minus_di_14.iloc[-1])}`\n\n"
                
                f"📊 *Traders Dynamic Index (TDI):*\n"
                f" - RSI (13): `{format_price(tdi_rsi.iloc[-1])}`\n"
                f" - Volatility Bands(34): `{format_price(tdi_vol.iloc[-1])}`\n"
                f" - Trade Signal Line (34): `{format_price(tdi_signal.iloc[-1])}`\n\n"
                
                f"4️⃣ *Volume & Money Flow*\n\n"
                f"📊 *On-Balance Volume (OBV):*\n"
                f" - OBV: `{format_number(obv)}`\n\n"
                
                f"📊 *ADOSC:* `{format_price(adosc)}`\n\n"
                
                f"💧 *Money Flow Index (MFI):*\n"
                f" - MFI (14): `{format_price(mfi_14)}`\n\n"
                
                f"📊 *Aroon Indicator (14):*\n"
                f" - Aroon Up: `{format_price(aroon_up_14.iloc[-1])}`\n"
                f" - Aroon Down: `{format_price(aroon_down_14.iloc[-1])}`\n\n"
                
                f"🔹 *VWAP:*\n"
                f" - VWAP(1): `{format_price(vwap)}`\n"
                f" - VWAP(3): `{format_price(vwap_3.iloc[-1])}`\n"
                f" - VWAP(4): `{format_price(vwap_4.iloc[-1])}`\n\n"
                
                f"5️⃣ *Volatility & Range*\n\n"
                f"🎯 *Bollinger Bands (20, 2 StdDev):*\n"
                f" - Upper Band: `{format_price(bb_upper.iloc[-1])}`\n"
                f" - Middle Band: `{format_price(bb_middle.iloc[-1])}`\n"
                f" - Lower Band: `{format_price(bb_lower.iloc[-1])}`\n\n"
                
                f"📊 *Fibonacci Bollinger Bands:*\n"
                f" - Upper (1.0): `{format_price(fib_bb['fib_1.0'].iloc[-1])}`\n"
                f" - Fib 0.618: `{format_price(fib_bb['fib_0.618'].iloc[-1])}`\n"
                f" - Fib 0.382: `{format_price(fib_bb['fib_0.382'].iloc[-1])}`\n"
                f" - Middle: `{format_price(fib_bb['fib_0'].iloc[-1])}`\n"
                f" - Fib -0.382: `{format_price(fib_bb['fib_neg0.382'].iloc[-1])}`\n"
                f" - Fib -0.618: `{format_price(fib_bb['fib_neg0.618'].iloc[-1])}`\n"
                f" - Lower (-1.0): `{format_price(fib_bb['fib_neg1.0'].iloc[-1])}`\n\n"
                
                f"📐 *Keltner Channel (20 EMA, 2 ATR):*\n"
                f" - Upper Band: `{format_price(kc_upper.iloc[-1])}`\n"
                f" - Middle EMA: `{format_price(kc_middle.iloc[-1])}`\n"
                f" - Lower Band: `{format_price(kc_lower.iloc[-1])}`\n\n"
                
                f"📏 *Average True Range (ATR):*\n"
                f" - ATR (14): `{format_price(atr_14)}`\n\n"
                
                f"🕯 *Heikin Ashi:*\n"
                f" - Close: `{format_price(ha_close.iloc[-1])}`\n\n"
                
                f"🌀 *Choppiness Index:*\n"
                f" - Value (14): `{format_price(chop_14)}`\n"
                f" - Value (21): `{format_price(chop_21)}`\n"
                f" - Upper Band(61.8): `61.80`\n"
                f" - Lower Band(38.2): `38.20`\n\n"
                
                f"📊 *TRIX:*\n"
                f" - TRIX(10): `{format_percent(trix_10.iloc[-1])}`\n"
                f" - TRIX(14): `{format_percent(trix_14.iloc[-1])}`\n"
                f" - Signal EMA(7): `{format_percent(trix_signal_7.iloc[-1])}`\n"
                f" - Signal EMA(9): `{format_percent(trix_signal_9.iloc[-1])}`\n\n"
                
                f"📊 *Donchian Channel (20):*\n"
                f" - Upper: `{format_price(donchian_upper.iloc[-1])}`\n"
                f" - Middle: `{format_price(donchian_middle.iloc[-1])}`\n"
                f" - Lower: `{format_price(donchian_lower.iloc[-1])}`\n\n"
                
                f"📍 *Final Signal Summary*\n"
            )
            
            # Add final signal summary based on indicators
            signals = []
            
            # Trend signals
            if current_price > sma_200 and sma_20 > sma_50:
                signals.append("✅ Strong Uptrend")
            elif current_price < sma_200 and sma_20 < sma_50:
                signals.append("❌ Strong Downtrend")
            
            # RSI signals
            if rsi_14 > 70:
                signals.append("⚠️ Overbought - Caution")
            elif rsi_14 < 30:
                signals.append("🎯 Oversold - Potential Buy")
            
            # MACD signals
            if macd_12_26_9.iloc[-1] > macd_signal_12_26_9.iloc[-1]:
                signals.append("✅ MACD Bullish")
            else:
                signals.append("❌ MACD Bearish")
            
            # Stochastic signals
            if stoch_k_14.iloc[-1] < 20 and stoch_k_14.iloc[-1] > stoch_d_14.iloc[-1]:
                signals.append("🎯 Stochastic Oversold Crossover")
            elif stoch_k_14.iloc[-1] > 80 and stoch_k_14.iloc[-1] < stoch_d_14.iloc[-1]:
                signals.append("⚠️ Stochastic Overbought Crossover")
            
            # ADX trend strength
            if adx_14.iloc[-1] > 25:
                signals.append(f"📊 Strong Trend (ADX: {adx_14.iloc[-1]:.1f})")
            
            message += "\n".join([f" - {s}" for s in signals])
            
            # Split message if too long (Telegram has 4096 char limit)
            if len(message) > 4000:
                # Send first part
                part1 = message[:4000]
                part1 = part1[:part1.rfind('\n')]  # Cut at last newline
                await update.message.reply_text(part1, parse_mode='Markdown')
                
                # Send second part
                part2 = message[len(part1):]
                if part2:
                    await update.message.reply_text(part2, parse_mode='Markdown')
            else:
                await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
            await update.message.reply_text(f"❌ Error fetching {company_name}. Please try again later.")
    
    return command

# -------------------------
# Start Command with Updated Format
# -------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command with complete stock list"""
    
    # Calculate ping response time
    start_time = time.time()
    msg = await update.message.reply_text("⚡")
    end_time = time.time()
    latency = round((end_time - start_time) * 1000, 2)
    await msg.delete()
    
    # Create stock table
    stock_table = ""
    for stock in stocks:
        stock_table += f"| {stock['name']:<30} | {stock['tv_symbol']:<18} |\n"
    
    # Create timeframe list
    timeframes = "15m, 30m, 1h, 2h, 4h, 1d, 1w"
    
    # Create example commands
    example_commands = ""
    for stock in stocks[:5]:  # First 5 stocks as examples
        symbol_lower = stock['symbol'].lower()
        example_commands += f"/{symbol_lower}_15m - {stock['name']} 15min\n"
    
    help_text = (
        f"🔥 *PSX Stock Indicator Bot*\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        f"Bot is working! ✅\n"
        f"Ping response time: {latency}ms\n\n"
        
        f"*Available Stocks:*\n"
        f"| Company                       | TradingView Symbol |\n"
        f"| ----------------------------- | ------------------ |\n"
        f"{stock_table}"
        f"also GOLD\n\n"
        
        f"*Timeframes:* {timeframes}\n\n"
        
        f"*Example Commands:*\n"
        f"{example_commands}"
        f"/engroh_1d - ENGRO Daily\n\n"
        
        f"*Indicators:*\n"
        f"All Major Indicators (SMA, EMA, WMA, HMA, Ichimoku, SuperTrend, Parabolic SAR, MACD, VW-MACD, RSI, RVI, Stochastic RSI, KDJ, Williams %R, CCI, ROC, Momentum, Ultimate Oscillator, ADX, TDI, OBV, ADOSC, MFI, Aroon, VWAP, Bollinger Bands, Fibonacci BB, Keltner, ATR, Heikin Ashi, Choppiness Index, TRIX, Donchian Channel)\n\n"
        
        f"⏳ *Note:* First request may take 10-15 seconds"
    )
    
    await update.message.reply_text(help_text, parse_mode='Markdown')

# -------------------------
# Test Commands
# -------------------------
async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ping command to check latency"""
    start_time = time.time()
    msg = await update.message.reply_text("🏓 Pong!")
    end_time = time.time()
    latency = round((end_time - start_time) * 1000, 2)
    await msg.edit_text(f"🏓 Pong! Response time: {latency}ms")

# -------------------------
# Build Telegram Application
# -------------------------
telegram_app = ApplicationBuilder()\
    .token(BOT_TOKEN)\
    .concurrent_updates(True)\
    .build()

# Add test commands
telegram_app.add_handler(CommandHandler("ping", ping_command))
logger.info(f"✅ Added test command: /ping")

# Add all stock commands
for stock in stocks:
    for interval_key in interval_map.keys():
        cmd_name = f"{stock['symbol'].lower()}_{interval_key}"
        telegram_app.add_handler(CommandHandler(cmd_name, create_stock_command(stock, interval_key)))
        logger.info(f"✅ Added command: /{cmd_name}")

# Add start command
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("help", start))
logger.info("✅ Added commands: /start, /help")

# -------------------------
# Error Handler
# -------------------------
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Error: {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text("⚠️ An error occurred. Please try again.")

telegram_app.add_error_handler(error_handler)

# -------------------------
# Flask App for Render
# -------------------------
flask_app = Flask(__name__)

@flask_app.route("/")
def home():
    return "✅ PSX Indicator Bot is Running with Complete Indicators!"

@flask_app.route("/health")
def health():
    return {"status": "healthy", "bot": "running", "indicators": "complete"}, 200

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    flask_app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

# -------------------------
# Main Execution
# -------------------------
if __name__ == "__main__":
    try:
        # Start Flask
        flask_thread = threading.Thread(target=run_flask, daemon=True)
        flask_thread.start()
        logger.info(f"✅ Flask server started on port {os.environ.get('PORT', 5000)}")
        
        # Small delay
        time.sleep(2)
        
        # Start Telegram bot
        logger.info("🚀 Starting Telegram bot with complete indicators...")
        telegram_app.run_polling(drop_pending_updates=True)
        
    except KeyboardInterrupt:
        logger.info("👋 Bot stopped")
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}", exc_info=True)
        raise
