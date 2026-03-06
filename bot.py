"""
PSX Stock Indicator Telegram Bot
COMPLETE VERSION - All timeframes (5min to 1week) with optimized settings
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

# Import indicators
from indicators import *

# Import analysis template
from analysis_template import get_analysis_template

# Apply nest_asyncio for Render deployment
nest_asyncio.apply()

# -------------------------
# FIX: Patch input() before importing tvDatafeed
# -------------------------
import builtins
original_input = builtins.input
builtins.input = lambda prompt='': 'y\n'
builtins.input = original_input

# Import tvDatafeed
try:
    from tvDatafeed import TvDatafeed, Interval
    print("tvDatafeed imported successfully")
except Exception as e:
    print(f"Failed to import tvDatafeed: {e}")
    raise

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
    raise ValueError("BOT_TOKEN environment variable not set")

# -------------------------
# TradingView Initialization
# -------------------------
def init_tvdatafeed():
    try:
        tv = TvDatafeed(auto_login=False)
        logger.info("TvDatafeed initialized with auto_login=False")
        return tv
    except Exception as e:
        logger.warning(f"Method 1 failed: {e}")
    
    try:
        tv = TvDatafeed()
        logger.info("TvDatafeed initialized successfully")
        return tv
    except Exception as e:
        logger.warning(f"Method 2 failed: {e}")
    
    try:
        tv = TvDatafeed(username=None, password=None)
        logger.info("TvDatafeed initialized with None credentials")
        return tv
    except Exception as e:
        logger.warning(f"Method 3 failed: {e}")
    
    raise Exception("All TvDatafeed initialization methods failed")

try:
    tv = init_tvdatafeed()
    test_data = tv.get_hist(symbol="FFC", exchange="PSX", interval=Interval.in_daily, n_bars=1)
    if test_data is not None and not test_data.empty:
        logger.info("TvDatafeed connection test successful")
    else:
        logger.warning("TvDatafeed connection test returned no data")
except Exception as e:
    logger.error(f"Fatal: Could not initialize TvDatafeed: {e}")
    raise

# -------------------------
# Interval Mapping - ALL TIMEFRAMES
# -------------------------
interval_map = {
    "5m": Interval.in_5_minute,
    "15m": Interval.in_15_minute,
    "30m": Interval.in_30_minute,
    "1h": Interval.in_1_hour,
    "4h": Interval.in_4_hour,
    "1d": Interval.in_daily,
    "1w": Interval.in_weekly,
}

# PSX Stocks
stocks = [
    {"symbol": "FFC", "name": "Fauji Fertilizer Company", "tv_symbol": "PSX:FFC"},
    {"symbol": "ENGROH", "name": "Engro Holdings", "tv_symbol": "PSX:ENGROH"},
    {"symbol": "OGDC", "name": "Oil & Gas Development Company", "tv_symbol": "PSX:OGDC"},
    {"symbol": "HUBC", "name": "Hub Power Company", "tv_symbol": "PSX:HUBC"},
    {"symbol": "PPL", "name": "Pakistan Petroleum Limited", "tv_symbol": "PSX:PPL"},
    {"symbol": "NBP", "name": "National Bank of Pakistan", "tv_symbol": "PSX:NBP"},
    {"symbol": "UBL", "name": "United Bank Limited", "tv_symbol": "PSX:UBL"},
    {"symbol": "MZNPETF", "name": "Meezan Pakistan ETF", "tv_symbol": "PSX:MZNPETF"},
    {"symbol": "NBPGETF", "name": "NBP Pakistan Growth ETF", "tv_symbol": "PSX:NBPGETF"},
    {"symbol": "KEL", "name": "K-Electric", "tv_symbol": "PSX:KEL"},
    {"symbol": "SYS", "name": "Systems Limited", "tv_symbol": "PSX:SYS"},
    {"symbol": "LUCK", "name": "Lucky Cement", "tv_symbol": "PSX:LUCK"},
    {"symbol": "PSO", "name": "Pakistan State Oil", "tv_symbol": "PSX:PSO"},
]

# Gold symbol
gold = {"symbol": "GOLD", "name": "Gold", "tv_symbol": "TVC:GOLD"}

# Combine all symbols
all_symbols = stocks + [gold]

# -------------------------
# TIME FRAME OPTIMIZED INDICATORS
# -------------------------
def calculate_indicators_by_timeframe(df, timeframe):
    """Calculate indicators with settings optimized for specific timeframe"""
    
    # Get latest close for trend calculations
    last_close = df['close'].iloc[-1] if len(df) > 0 else 0
    
    # ===== 5 MINUTE / 15 MINUTE (Scalping) =====
    if timeframe in ["5m", "15m"]:
        # Fast Moving Averages
        df['SMA_10'] = SMA(df, 10)
        df['SMA_20'] = SMA(df, 20)
        df['EMA_9'] = EMA(df, 9)
        df['EMA_21'] = EMA(df, 21)
        df['WMA_8'] = WMA(df, 8)
        df['WMA_20'] = WMA(df, 20)
        df['HMA_9'] = HMA(df, 9)
        
        # Ichimoku (Standard)
        df['ICHIMOKU_CONVERSION'], df['ICHIMOKU_BASE'], df['ICHIMOKU_SPAN_A'], df['ICHIMOKU_SPAN_B'] = Ichimoku(df)
        
        # SuperTrend - Fast
        df['SUPERTREND_7'] = SuperTrend(df, period=7, multiplier=3)
        
        # Parabolic SAR
        df['PSAR'] = ParabolicSAR(df)
        
        # MACD - Fast settings
        df['MACD_6_13_5'], df['MACD_SIGNAL_6_13_5'], df['MACD_HIST_6_13_5'] = MACD(df, fast=6, slow=13, signal=5)
        df['MACD_12_26_9'], df['MACD_SIGNAL_12_26_9'], df['MACD_HIST_12_26_9'] = MACD(df)
        
        # RSI - Multiple periods
        df['RSI_7'] = RSI(df, 7)
        df['RSI_14'] = RSI(df, 14)
        
        # Stochastic - Fast
        df['STOCH_K'], df['STOCH_D'] = Stochastic(df, 10, 3)
        
        # Williams %R - Fast
        df['WILLIAMS_10'] = WilliamsR(df, 10)
        
        # CCI - Fast
        df['CCI_10'] = CCI(df, 10)
        
        # ROC - Fast
        df['ROC_7'] = ROC(df, 7)
        
        # ADX
        df['ADX_14'], df['PLUS_DI_14'], df['MINUS_DI_14'] = ADX(df, 14)
        
        # Volume indicators
        df['OBV'] = OBV(df)
        df['MFI_10'] = MFI(df, 10)
        df['VWAP'] = VWAP(df)
        
        # Bollinger Bands - Fast
        df['BB_UPPER'], df['BB_MIDDLE'], df['BB_LOWER'] = Bollinger_Bands(df, 15, 2)
        
        # ATR - Fast
        df['ATR_7'] = ATR(df, 7)
        
        # Heikin Ashi
        df['HA_CLOSE'] = HeikinAshi(df)
        
        # Choppiness Index
        df['CHOP_10'] = ChoppinessIndex(df, 10)
        
        # Donchian Channel
        df['DC_UPPER'], df['DC_MIDDLE'], df['DC_LOWER'] = DonchianChannel(df, 15)
    
    # ===== 30 MINUTE / 1 HOUR (Intraday) =====
    elif timeframe in ["30m", "1h"]:
        # Moving Averages
        df['SMA_10'] = SMA(df, 10)
        df['SMA_20'] = SMA(df, 20)
        df['SMA_50'] = SMA(df, 50)
        df['EMA_9'] = EMA(df, 9)
        df['EMA_21'] = EMA(df, 21)
        df['EMA_50'] = EMA(df, 50)
        df['WMA_8'] = WMA(df, 8)
        df['WMA_20'] = WMA(df, 20)
        df['HMA_9'] = HMA(df, 9)
        df['HMA_14'] = HMA(df, 14)
        
        # Ichimoku
        df['ICHIMOKU_CONVERSION'], df['ICHIMOKU_BASE'], df['ICHIMOKU_SPAN_A'], df['ICHIMOKU_SPAN_B'] = Ichimoku(df)
        
        # SuperTrend - Medium
        df['SUPERTREND_10'] = SuperTrend(df, period=10, multiplier=3)
        
        # Parabolic SAR
        df['PSAR'] = ParabolicSAR(df)
        
        # MACD
        df['MACD_12_26_9'], df['MACD_SIGNAL_12_26_9'], df['MACD_HIST_12_26_9'] = MACD(df)
        df['VW_MACD'], df['VW_MACD_SIGNAL'], df['VW_MACD_HIST'] = VW_MACD(df)
        
        # RSI
        df['RSI_10'] = RSI(df, 10)
        df['RSI_14'] = RSI(df, 14)
        
        # RVI
        df['RVI_14'], df['RVI_SIGNAL'] = RVI(df, 14)
        
        # Stochastic
        df['STOCH_K'], df['STOCH_D'] = Stochastic(df, 14, 3)
        df['STOCH_RSI_K'], df['STOCH_RSI_D'] = Stochastic(df, 14, 3)
        
        # KDJ
        df['KDJ_K'], df['KDJ_D'], df['KDJ_J'] = KDJ(df)
        
        # Williams %R
        df['WILLIAMS_14'] = WilliamsR(df, 14)
        
        # CCI
        df['CCI_14'] = CCI(df, 14)
        
        # ROC
        df['ROC_12'] = ROC(df, 12)
        
        # Ultimate Oscillator
        df['UO'] = UltimateOscillator(df)
        
        # ADX
        df['ADX_14'], df['PLUS_DI_14'], df['MINUS_DI_14'] = ADX(df, 14)
        
        # TDI
        df['TDI_RSI'], df['TDI_UPPER'], df['TDI_LOWER'], df['TDI_SIGNAL'] = TDI(df)
        
        # Volume
        df['OBV'] = OBV(df)
        df['ADOSC'] = ADOSC(df)
        df['MFI_14'] = MFI(df, 14)
        df['AROON_UP'], df['AROON_DOWN'] = Aroon(df)
        df['VWAP'] = VWAP(df)
        
        # Bollinger Bands
        df['BB_UPPER'], df['BB_MIDDLE'], df['BB_LOWER'] = Bollinger_Bands(df)
        
        # Keltner Channel
        df['KC_UPPER'], df['KC_MIDDLE'], df['KC_LOWER'] = KeltnerChannel(df)
        
        # ATR
        df['ATR_14'] = ATR(df, 14)
        
        # Heikin Ashi
        df['HA_CLOSE'] = HeikinAshi(df)
        
        # Choppiness Index
        df['CHOP_14'] = ChoppinessIndex(df, 14)
        
        # TRIX
        df['TRIX_14'] = TRIX(df, 14)
        df['TRIX_SIGNAL'] = df['TRIX_14'].ewm(span=7).mean()
        
        # Donchian Channel
        df['DC_UPPER'], df['DC_MIDDLE'], df['DC_LOWER'] = DonchianChannel(df, 20)
    
    # ===== 4 HOUR (Swing) =====
    elif timeframe == "4h":
        # Moving Averages
        df['SMA_20'] = SMA(df, 20)
        df['SMA_50'] = SMA(df, 50)
        df['SMA_200'] = SMA(df, 200)
        df['EMA_9'] = EMA(df, 9)
        df['EMA_21'] = EMA(df, 21)
        df['EMA_50'] = EMA(df, 50)
        df['EMA_200'] = EMA(df, 200)
        df['WMA_20'] = WMA(df, 20)
        df['WMA_50'] = WMA(df, 50)
        df['HMA_14'] = HMA(df, 14)
        df['HMA_21'] = HMA(df, 21)
        
        # Ichimoku
        df['ICHIMOKU_CONVERSION'], df['ICHIMOKU_BASE'], df['ICHIMOKU_SPAN_A'], df['ICHIMOKU_SPAN_B'] = Ichimoku(df)
        
        # SuperTrend
        df['SUPERTREND_10'] = SuperTrend(df, period=10, multiplier=3)
        df['SUPERTREND_14'] = SuperTrend(df, period=14, multiplier=3)
        
        # Parabolic SAR
        df['PSAR'] = ParabolicSAR(df)
        
        # MACD
        df['MACD_12_26_9'], df['MACD_SIGNAL_12_26_9'], df['MACD_HIST_12_26_9'] = MACD(df)
        
        # RSI
        df['RSI_14'] = RSI(df, 14)
        
        # Stochastic
        df['STOCH_K'], df['STOCH_D'] = Stochastic(df, 14, 3)
        
        # KDJ
        df['KDJ_K'], df['KDJ_D'], df['KDJ_J'] = KDJ(df)
        
        # Williams %R
        df['WILLIAMS_14'] = WilliamsR(df, 14)
        df['WILLIAMS_25'] = WilliamsR(df, 25)
        
        # CCI
        df['CCI_14'] = CCI(df, 14)
        df['CCI_20'] = CCI(df, 20)
        
        # ROC
        df['ROC_14'] = ROC(df, 14)
        df['ROC_25'] = ROC(df, 25)
        
        # Momentum
        df['MTM_10'] = Momentum(df, 10)
        df['MTM_20'] = Momentum(df, 20)
        
        # ADX
        df['ADX_14'], df['PLUS_DI_14'], df['MINUS_DI_14'] = ADX(df, 14)
        
        # Volume
        df['OBV'] = OBV(df)
        df['MFI_14'] = MFI(df, 14)
        df['AROON_UP'], df['AROON_DOWN'] = Aroon(df)
        df['VWAP'] = VWAP(df)
        
        # Bollinger Bands
        df['BB_UPPER'], df['BB_MIDDLE'], df['BB_LOWER'] = Bollinger_Bands(df)
        
        # Fibonacci Bollinger Bands
        fib_bands = FibBollingerBands(df)
        df['FIB_BB_UPPER_1'] = fib_bands[0]
        df['FIB_BB_UPPER_0618'] = fib_bands[1]
        df['FIB_BB_UPPER_0382'] = fib_bands[2]
        df['FIB_BB_MIDDLE'] = fib_bands[3]
        df['FIB_BB_LOWER_0382'] = fib_bands[4]
        df['FIB_BB_LOWER_0618'] = fib_bands[5]
        df['FIB_BB_LOWER_1'] = fib_bands[6]
        
        # ATR
        df['ATR_14'] = ATR(df, 14)
        
        # Heikin Ashi
        df['HA_CLOSE'] = HeikinAshi(df)
        
        # Choppiness Index
        df['CHOP_14'] = ChoppinessIndex(df, 14)
        df['CHOP_21'] = ChoppinessIndex(df, 21)
        
        # TRIX
        df['TRIX_10'] = TRIX(df, 10)
        df['TRIX_14'] = TRIX(df, 14)
        df['TRIX_SIGNAL_7'] = df['TRIX_14'].ewm(span=7).mean()
        df['TRIX_SIGNAL_9'] = df['TRIX_14'].ewm(span=9).mean()
        
        # Donchian Channel
        df['DC_UPPER'], df['DC_MIDDLE'], df['DC_LOWER'] = DonchianChannel(df, 20)
    
    # ===== DAILY / WEEKLY (Position Trading) =====
    else:  # "1d", "1w"
        # All Moving Averages
        df['SMA_10'] = SMA(df, 10)
        df['SMA_20'] = SMA(df, 20)
        df['SMA_50'] = SMA(df, 50)
        df['SMA_200'] = SMA(df, 200)
        df['EMA_9'] = EMA(df, 9)
        df['EMA_21'] = EMA(df, 21)
        df['EMA_50'] = EMA(df, 50)
        df['EMA_200'] = EMA(df, 200)
        df['WMA_8'] = WMA(df, 8)
        df['WMA_20'] = WMA(df, 20)
        df['WMA_50'] = WMA(df, 50)
        df['WMA_100'] = WMA(df, 100)
        df['HMA_9'] = HMA(df, 9)
        df['HMA_14'] = HMA(df, 14)
        df['HMA_21'] = HMA(df, 21)
        
        # Ichimoku
        df['ICHIMOKU_CONVERSION'], df['ICHIMOKU_BASE'], df['ICHIMOKU_SPAN_A'], df['ICHIMOKU_SPAN_B'] = Ichimoku(df)
        
        # SuperTrend
        df['SUPERTREND_7'] = SuperTrend(df, period=7, multiplier=3)
        df['SUPERTREND_10'] = SuperTrend(df, period=10, multiplier=3)
        df['SUPERTREND_14'] = SuperTrend(df, period=14, multiplier=3)
        
        # Parabolic SAR
        df['PSAR'] = ParabolicSAR(df)
        
        # MACD - All variations
        df['MACD_6_13_5'], df['MACD_SIGNAL_6_13_5'], df['MACD_HIST_6_13_5'] = MACD(df, fast=6, slow=13, signal=5)
        df['MACD_12_26_9'], df['MACD_SIGNAL_12_26_9'], df['MACD_HIST_12_26_9'] = MACD(df)
        df['VW_MACD'], df['VW_MACD_SIGNAL'], df['VW_MACD_HIST'] = VW_MACD(df)
        
        # RSI - All periods
        df['RSI_3'] = RSI(df, 3)
        df['RSI_10'] = RSI(df, 10)
        df['RSI_14'] = RSI(df, 14)
        
        # RVI
        df['RVI_14'], df['RVI_SIGNAL'] = RVI(df, 14)
        df['RVI_10'], _ = RVI(df, 10)
        
        # Stochastic RSI
        df['STOCH_RSI_K'], df['STOCH_RSI_D'] = Stochastic(df, 14, 3)
        
        # KDJ
        df['KDJ_K'], df['KDJ_D'], df['KDJ_J'] = KDJ(df)
        
        # Williams %R
        df['WILLIAMS_R_12'] = WilliamsR(df, 12)
        df['WILLIAMS_R_25'] = WilliamsR(df, 25)
        
        # CCI
        df['CCI_14'] = CCI(df, 14)
        df['CCI_20'] = CCI(df, 20)
        
        # ROC
        df['ROC_14'] = ROC(df, 14)
        df['ROC_25'] = ROC(df, 25)
        
        # Momentum
        df['MTM_10'] = Momentum(df, 10)
        df['MTM_20'] = Momentum(df, 20)
        
        # Ultimate Oscillator
        df['UO'] = UltimateOscillator(df)
        
        # ADX
        df['ADX_14'], df['PLUS_DI_14'], df['MINUS_DI_14'] = ADX(df, 14)
        
        # TDI
        df['TDI_RSI'], df['TDI_UPPER'], df['TDI_LOWER'], df['TDI_SIGNAL'] = TDI(df)
        
        # Volume indicators
        df['OBV'] = OBV(df)
        df['ADOSC'] = ADOSC(df)
        df['MFI_14'] = MFI(df, 14)
        df['AROON_UP'], df['AROON_DOWN'] = Aroon(df)
        df['VWAP_1'] = VWAP(df)
        df['VWAP_3'] = VWAP(df)
        df['VWAP_4'] = VWAP(df)
        
        # Bollinger Bands
        df['BB_UPPER'], df['BB_MIDDLE'], df['BB_LOWER'] = Bollinger_Bands(df)
        
        # Fibonacci Bollinger Bands
        fib_bands = FibBollingerBands(df)
        df['FIB_BB_UPPER_1'] = fib_bands[0]
        df['FIB_BB_UPPER_0618'] = fib_bands[1]
        df['FIB_BB_UPPER_0382'] = fib_bands[2]
        df['FIB_BB_MIDDLE'] = fib_bands[3]
        df['FIB_BB_LOWER_0382'] = fib_bands[4]
        df['FIB_BB_LOWER_0618'] = fib_bands[5]
        df['FIB_BB_LOWER_1'] = fib_bands[6]
        
        # Keltner Channel
        df['KC_UPPER'], df['KC_MIDDLE'], df['KC_LOWER'] = KeltnerChannel(df)
        
        # ATR
        df['ATR_14'] = ATR(df, 14)
        
        # Heikin Ashi
        df['HA_CLOSE'] = HeikinAshi(df)
        
        # Choppiness Index
        df['CHOP_14'] = ChoppinessIndex(df, 14)
        df['CHOP_21'] = ChoppinessIndex(df, 21)
        df['CHOP_UPPER'] = 61.8
        df['CHOP_LOWER'] = 38.2
        
        # TRIX
        df['TRIX_10'] = TRIX(df, 10)
        df['TRIX_14'] = TRIX(df, 14)
        df['TRIX_SIGNAL_7'] = df['TRIX_14'].ewm(span=7).mean()
        df['TRIX_SIGNAL_9'] = df['TRIX_14'].ewm(span=9).mean()
        
        # Donchian Channel
        df['DC_UPPER'], df['DC_MIDDLE'], df['DC_LOWER'] = DonchianChannel(df, 20)
    
    return df

# -------------------------
# Format indicator values
# -------------------------
def format_value(value, decimals=2):
    if pd.isna(value):
        return "N/A"
    if isinstance(value, (int, float)):
        return f"{value:.{decimals}f}"
    return str(value)

# -------------------------
# Create stock command
# -------------------------
def create_stock_command(symbol, name, tv_symbol, interval_key):
    
    async def command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(f"Fetching {name} ({interval_key}) data... This may take 10-15 seconds.")
        
        try:
            loop = asyncio.get_event_loop()
            
            if ':' in tv_symbol:
                exchange, sym = tv_symbol.split(':')
            else:
                exchange = "PSX"
                sym = tv_symbol
            
            try:
                df = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        lambda: tv.get_hist(
                            symbol=sym,
                            exchange=exchange,
                            interval=interval_map[interval_key],
                            n_bars=500
                        )
                    ),
                    timeout=25.0
                )
            except asyncio.TimeoutError:
                await update.message.reply_text(f"Request timed out. Please try again.")
                return
            
            if df is None or df.empty:
                await update.message.reply_text(f"No data found for {name}.")
                return
            
            # Calculate indicators based on timeframe
            df = calculate_indicators_by_timeframe(df, interval_key)
            
            last = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else last
            
            close_time = df.index[-1].strftime('%Y-%m-%d %H:%M:%S')
            
            change_points = last['close'] - prev['close']
            change_percent = (change_points / prev['close']) * 100 if prev['close'] != 0 else 0
            
            if change_points > 0:
                change_sign = "+"
            elif change_points < 0:
                change_sign = "-"
            else:
                change_sign = "="
            
            # START BUILDING MESSAGE - EXACT FORMAT AS REQUESTED
            message = (
                f"📊 {name} - {tv_symbol} ({interval_key})\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n\n"
                
                f"1️⃣ Market Overview\n"
                f"💰 Price: {format_value(last['close'])}\n"
                f"🔓 Open Price: {format_value(last['open'])}\n"
                f"📈 24h High: {format_value(last['high'])}\n"
                f"📉 24h Low: {format_value(last['low'])}\n"
                f"🔁 Change: {change_sign} {format_value(change_points)} ({format_value(change_percent)}%)\n"
                f"🧮 Volume: {format_value(last['volume'], 0)}\n"
                f"⏰ Close Time: {close_time}\n\n"
                
                f"2️⃣ Trend Direction\n\n"
            )
            
            # Add available SMA values
            sma_section = "📊 Simple Moving Averages (SMA):\n"
            if 'SMA_10' in last.index:
                sma_section += f" - SMA 10: {format_value(last['SMA_10'])}\n"
            if 'SMA_20' in last.index:
                sma_section += f" - SMA 20: {format_value(last['SMA_20'])}\n"
            if 'SMA_50' in last.index:
                sma_section += f" - SMA 50: {format_value(last['SMA_50'])}\n"
            if 'SMA_200' in last.index:
                sma_section += f" - SMA 200: {format_value(last['SMA_200'])}\n"
            message += sma_section + "\n"
            
            # EMA section
            ema_section = "📈 Exponential Moving Averages (EMA):\n"
            if 'EMA_9' in last.index:
                ema_section += f" - EMA 9: {format_value(last['EMA_9'])}\n"
            if 'EMA_21' in last.index:
                ema_section += f" - EMA 21: {format_value(last['EMA_21'])}\n"
            if 'EMA_50' in last.index:
                ema_section += f" - EMA 50: {format_value(last['EMA_50'])}\n"
            if 'EMA_200' in last.index:
                ema_section += f" - EMA 200: {format_value(last['EMA_200'])}\n"
            message += ema_section + "\n"
            
            # WMA section
            wma_section = "⚖️ Weighted Moving Averages (WMA):\n"
            if 'WMA_8' in last.index:
                wma_section += f" - WMA 8: {format_value(last['WMA_8'])}\n"
            if 'WMA_20' in last.index:
                wma_section += f" - WMA 20: {format_value(last['WMA_20'])}\n"
            if 'WMA_50' in last.index:
                wma_section += f" - WMA 50: {format_value(last['WMA_50'])}\n"
            if 'WMA_100' in last.index:
                wma_section += f" - WMA 100: {format_value(last['WMA_100'])}\n"
            message += wma_section + "\n"
            
            # HMA section
            hma_section = "📈 Hull Moving Average:\n"
            if 'HMA_9' in last.index:
                hma_section += f"  (HMA 9): {format_value(last['HMA_9'])}\n"
            if 'HMA_14' in last.index:
                hma_section += f"  (HMA 14): {format_value(last['HMA_14'])}\n"
            if 'HMA_21' in last.index:
                hma_section += f"  (HMA 21): {format_value(last['HMA_21'])}\n"
            message += hma_section + "\n"
            
            # Ichimoku
            if 'ICHIMOKU_CONVERSION' in last.index:
                message += (
                    f"📊 Ichimoku Cloud:\n"
                    f" - Conversion Line (9): {format_value(last['ICHIMOKU_CONVERSION'])}\n"
                    f" - Base Line (26): {format_value(last['ICHIMOKU_BASE'])}\n"
                    f" - Leading Span A: {format_value(last['ICHIMOKU_SPAN_A'])}\n"
                    f" - Leading Span B: {format_value(last['ICHIMOKU_SPAN_B'])}\n\n"
                )
            
            # SuperTrend
            st_section = "📈 SuperTrend:\n"
            if 'SUPERTREND_7' in last.index:
                st_section += f" - Value(7): {format_value(last['SUPERTREND_7'])}\n"
            if 'SUPERTREND_10' in last.index:
                st_section += f" - Value(10): {format_value(last['SUPERTREND_10'])}\n"
            if 'SUPERTREND_14' in last.index:
                st_section += f" - Value(14): {format_value(last['SUPERTREND_14'])}\n"
            message += st_section + "\n"
            
            # Parabolic SAR
            if 'PSAR' in last.index:
                message += f"📈 Parabolic SAR:\n - Step AF Value(0.02): {format_value(last['PSAR'])}\n\n"
            
            # 3️⃣ Momentum Strength
            message += f"3️⃣ Momentum Strength\n\n"
            
            # MACD 6,13,5
            if 'MACD_6_13_5' in last.index:
                message += (
                    f"📉 MACD: 6,13,5\n"
                    f" - MACD: {format_value(last['MACD_6_13_5'])}\n"
                    f" - Signal: {format_value(last['MACD_SIGNAL_6_13_5'])}\n"
                    f" - Histogram: {format_value(last['MACD_HIST_6_13_5'])}\n\n"
                )
            
            # MACD 12,26,9
            if 'MACD_12_26_9' in last.index:
                message += (
                    f"📉 MACD: 12,26,9\n"
                    f" - MACD: {format_value(last['MACD_12_26_9'])}\n"
                    f" - Signal: {format_value(last['MACD_SIGNAL_12_26_9'])}\n"
                    f" - Histogram: {format_value(last['MACD_HIST_12_26_9'])}\n\n"
                )
            
            # VW-MACD
            if 'VW_MACD' in last.index:
                message += (
                    f"📊 Volume-Weighted MACD (VW-MACD):\n"
                    f" - VW-MACD: {format_value(last['VW_MACD'])}\n"
                    f" - VW-Signal: {format_value(last['VW_MACD_SIGNAL'])}\n"
                    f" - VW-Histogram: {format_value(last['VW_MACD_HIST'])}\n\n"
                )
            
            # RSI
            rsi_section = "⚡ Relative Strength Index (RSI):\n"
            if 'RSI_3' in last.index:
                rsi_section += f" - RSI (3): {format_value(last['RSI_3'])}\n"
            if 'RSI_7' in last.index:
                rsi_section += f" - RSI (7): {format_value(last['RSI_7'])}\n"
            if 'RSI_10' in last.index:
                rsi_section += f" - RSI (10): {format_value(last['RSI_10'])}\n"
            if 'RSI_14' in last.index:
                rsi_section += f" - RSI (14): {format_value(last['RSI_14'])}\n"
            message += rsi_section + "\n"
            
            # RVI
            if 'RVI_14' in last.index:
                message += (
                    f"📊 Relative Volatility Index (RVI):\n"
                    f" - RVI (14): {format_value(last['RVI_14'])}\n"
                    f" - RVI (10): {format_value(last['RVI_10'])}\n"
                    f" - Signal Line(4): {format_value(last['RVI_SIGNAL'])}\n\n"
                )
            
            # Stochastic RSI
            if 'STOCH_RSI_K' in last.index:
                message += (
                    f"📉 Stochastic RSI (14,3,3):\n"
                    f" - %K: {format_value(last['STOCH_RSI_K'])}\n"
                    f" - %D: {format_value(last['STOCH_RSI_D'])}\n\n"
                )
            
            # KDJ
            if 'KDJ_K' in last.index:
                message += (
                    f"📊 KDJ (9,3,3):\n"
                    f" - K: {format_value(last['KDJ_K'])}\n"
                    f" - D: {format_value(last['KDJ_D'])}\n"
                    f" - J: {format_value(last['KDJ_J'])}\n\n"
                )
            
            # Williams %R
            will_section = "📉 Williams %R Indicator:\n"
            if 'WILLIAMS_10' in last.index:
                will_section += f" - Williams %R (10): {format_value(last['WILLIAMS_10'])}\n"
            if 'WILLIAMS_12' in last.index:
                will_section += f" - Williams %R (12): {format_value(last['WILLIAMS_12'])}\n"
            if 'WILLIAMS_14' in last.index:
                will_section += f" - Williams %R (14): {format_value(last['WILLIAMS_14'])}\n"
            if 'WILLIAMS_25' in last.index:
                will_section += f" - Williams %R (25): {format_value(last['WILLIAMS_25'])}\n"
            message += will_section + "\n"
            
            # CCI
            cci_section = "📘 Commodity Channel Index (CCI):\n"
            if 'CCI_10' in last.index:
                cci_section += f" - CCI (10): {format_value(last['CCI_10'])}\n"
            if 'CCI_14' in last.index:
                cci_section += f" - CCI (14): {format_value(last['CCI_14'])}\n"
            if 'CCI_20' in last.index:
                cci_section += f" - CCI (20): {format_value(last['CCI_20'])}\n"
            message += cci_section + "\n"
            
            # ROC
            roc_section = "📊 Rate of Change (ROC):\n"
            if 'ROC_7' in last.index:
                roc_section += f" - ROC (7): {format_value(last['ROC_7'])}\n"
            if 'ROC_12' in last.index:
                roc_section += f" - ROC (12): {format_value(last['ROC_12'])}\n"
            if 'ROC_14' in last.index:
                roc_section += f" - ROC (14): {format_value(last['ROC_14'])}\n"
            if 'ROC_25' in last.index:
                roc_section += f" - ROC (25): {format_value(last['ROC_25'])}\n"
            message += roc_section + "\n"
            
            # Momentum
            if 'MTM_10' in last.index:
                message += (
                    f"📈 Momentum (MTM):\n"
                    f" - MTM (10): {format_value(last['MTM_10'])}\n"
                    f" - MTM (20): {format_value(last['MTM_20'])}\n\n"
                )
            
            # Ultimate Oscillator
            if 'UO' in last.index:
                message += f"🧭 Ultimate Oscillator:\n - UO (7,14,28): {format_value(last['UO'])}\n\n"
            
            # ADX
            if 'ADX_14' in last.index:
                message += (
                    f"📊 ADX (Trend Strength):\n"
                    f" - ADX (14): {format_value(last['ADX_14'])}\n"
                    f" - +DI (14): {format_value(last['PLUS_DI_14'])}\n"
                    f" - -DI (14): {format_value(last['MINUS_DI_14'])}\n\n"
                )
            
            # TDI
            if 'TDI_RSI' in last.index:
                message += (
                    f"📊 Traders Dynamic Index (TDI):\n"
                    f" - RSI (13): {format_value(last['TDI_RSI'])}\n"
                    f" - Volatility Bands(34): {format_value(last['TDI_UPPER'])}\n"
                    f" - Trade Signal Line (34): {format_value(last['TDI_SIGNAL'])}\n\n"
                )
            
            # 4️⃣ Volume & Money Flow
            message += f"4️⃣ Volume & Money Flow\n\n"
            
            # OBV
            if 'OBV' in last.index:
                message += f"📊 On-Balance Volume (OBV):\n - OBV: {format_value(last['OBV'], 0)}\n\n"
            
            # ADOSC
            if 'ADOSC' in last.index:
                message += f"📊 ADOSC: {format_value(last['ADOSC'])}\n\n"
            
            # MFI
            mfi_section = "💧 Money Flow Index (MFI):\n"
            if 'MFI_10' in last.index:
                mfi_section += f" - MFI (10): {format_value(last['MFI_10'])}\n"
            if 'MFI_14' in last.index:
                mfi_section += f" - MFI (14): {format_value(last['MFI_14'])}\n"
            message += mfi_section + "\n"
            
            # Aroon
            if 'AROON_UP' in last.index:
                message += (
                    f"📊 Aroon Indicator (14):\n"
                    f" - Aroon Up: {format_value(last['AROON_UP'])}\n"
                    f" - Aroon Down: {format_value(last['AROON_DOWN'])}\n\n"
                )
            
            # VWAP
            vwap_section = "🔹 VWAP:\n"
            if 'VWAP_1' in last.index:
                vwap_section += f" - VWAP(1): {format_value(last['VWAP_1'])}\n"
            if 'VWAP_3' in last.index:
                vwap_section += f" - VWAP(3): {format_value(last['VWAP_3'])}\n"
            if 'VWAP_4' in last.index:
                vwap_section += f" - VWAP(4): {format_value(last['VWAP_4'])}\n"
            if 'VWAP' in last.index and 'VWAP_1' not in last.index:
                vwap_section += f" - VWAP: {format_value(last['VWAP'])}\n"
            message += vwap_section + "\n"
            
            # 5️⃣ Volatility & Range
            message += f"5️⃣ Volatility & Range\n\n"
            
            # Bollinger Bands
            if 'BB_UPPER' in last.index:
                message += (
                    f"🎯 Bollinger Bands (20, 2 StdDev):\n"
                    f" - Upper Band: {format_value(last['BB_UPPER'])}\n"
                    f" - Middle Band: {format_value(last['BB_MIDDLE'])}\n"
                    f" - Lower Band: {format_value(last['BB_LOWER'])}\n\n"
                )
            
            # Fibonacci Bollinger Bands
            if 'FIB_BB_UPPER_1' in last.index:
                message += (
                    f"📊 Fibonacci Bollinger Bands:\n"
                    f" - Upper (1.0): {format_value(last['FIB_BB_UPPER_1'])}\n"
                    f" - Fib 0.618: {format_value(last['FIB_BB_UPPER_0618'])}\n"
                    f" - Fib 0.382: {format_value(last['FIB_BB_UPPER_0382'])}\n"
                    f" - Middle: {format_value(last['FIB_BB_MIDDLE'])}\n"
                    f" - Fib -0.382: {format_value(last['FIB_BB_LOWER_0382'])}\n"
                    f" - Fib -0.618: {format_value(last['FIB_BB_LOWER_0618'])}\n"
                    f" - Lower (-1.0): {format_value(last['FIB_BB_LOWER_1'])}\n\n"
                )
            
            # Keltner Channel
            if 'KC_UPPER' in last.index:
                message += (
                    f"📐 Keltner Channel (20 EMA, 2 ATR):\n"
                    f" - Upper Band: {format_value(last['KC_UPPER'])}\n"
                    f" - Middle EMA: {format_value(last['KC_MIDDLE'])}\n"
                    f" - Lower Band: {format_value(last['KC_LOWER'])}\n\n"
                )
            
            # ATR
            atr_section = "📏 Average True Range (ATR):\n"
            if 'ATR_7' in last.index:
                atr_section += f" - ATR (7): {format_value(last['ATR_7'])}\n"
            if 'ATR_14' in last.index:
                atr_section += f" - ATR (14): {format_value(last['ATR_14'])}\n"
            message += atr_section + "\n"
            
            # Heikin Ashi
            if 'HA_CLOSE' in last.index:
                message += f"🕯 Heikin Ashi:\n - Close: {format_value(last['HA_CLOSE'])}\n\n"
            
            # Choppiness Index
            chop_section = "🌀 Choppiness Index:\n"
            if 'CHOP_10' in last.index:
                chop_section += f" - Value (10): {format_value(last['CHOP_10'])}\n"
            if 'CHOP_14' in last.index:
                chop_section += f" - Value (14): {format_value(last['CHOP_14'])}\n"
            if 'CHOP_21' in last.index:
                chop_section += f" - Value (21): {format_value(last['CHOP_21'])}\n"
            if 'CHOP_UPPER' in last.index:
                chop_section += f" - Upper Band(61.8): {format_value(last['CHOP_UPPER'])}\n"
                chop_section += f" - Lower Band(38.2): {format_value(last['CHOP_LOWER'])}\n"
            message += chop_section + "\n"
            
            # TRIX
            trix_section = "📊 TRIX:\n"
            if 'TRIX_10' in last.index:
                trix_section += f" - TRIX(10): {format_value(last['TRIX_10'])}\n"
            if 'TRIX_14' in last.index:
                trix_section += f" - TRIX(14): {format_value(last['TRIX_14'])}\n"
            if 'TRIX_SIGNAL_7' in last.index:
                trix_section += f" - Signal EMA(7): {format_value(last['TRIX_SIGNAL_7'])}\n"
            if 'TRIX_SIGNAL_9' in last.index:
                trix_section += f" - Signal EMA(9): {format_value(last['TRIX_SIGNAL_9'])}\n"
            message += trix_section + "\n"
            
            # Donchian Channel
            if 'DC_UPPER' in last.index:
                message += (
                    f"📊 Donchian Channel (20):\n"
                    f" - Upper: {format_value(last['DC_UPPER'])}\n"
                    f" - Middle: {format_value(last['DC_MIDDLE'])}\n"
                    f" - Lower: {format_value(last['DC_LOWER'])}\n\n"
                )
            
            # Final Signal Summary (just text, no emoji)
            message += f"📍 Final Signal Summary"
            
            # Send message
            if len(message) > 4096:
                await update.message.reply_text(message[:4096])
                await update.message.reply_text(message[4096:])
            else:
                await update.message.reply_text(message)
            
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
            await update.message.reply_text(f"Error fetching {name}. Please try again later.")
    
    return command

# -------------------------
# Text Command
# -------------------------
async def text_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        template = get_analysis_template()
        await update.message.reply_text(template)
    except Exception as e:
        logger.error(f"Error in text command: {e}")
        await update.message.reply_text("Error retrieving analysis template.")

# -------------------------
# Start/Ping Commands
# -------------------------
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_time = time.time()
    msg = await update.message.reply_text("Checking...")
    end_time = time.time()
    ping_time = round((end_time - start_time) * 1000, 2)
    
    await msg.edit_text(
        f"Your PSX Bot is working! ✅\n"
        f"Ping response time: {ping_time}ms"
    )

async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_time = time.time()
    msg = await update.message.reply_text("Pong!")
    end_time = time.time()
    latency = round((end_time - start_time) * 1000, 2)
    await msg.edit_text(f"Pong! Response time: {latency}ms")

# -------------------------
# Build Telegram Application
# -------------------------
telegram_app = ApplicationBuilder()\
    .token(BOT_TOKEN)\
    .concurrent_updates(True)\
    .build()

# Add commands
telegram_app.add_handler(CommandHandler("start", start_command))
telegram_app.add_handler(CommandHandler("ping", ping_command))
telegram_app.add_handler(CommandHandler("text", text_command))
logger.info("Added commands: /start, /ping, /text")

# Add all stock commands for all timeframes
for stock in stocks + [gold]:
    for interval_key in interval_map.keys():
        cmd_name = f"{stock['symbol'].lower()}_{interval_key}"
        telegram_app.add_handler(
            CommandHandler(
                cmd_name, 
                create_stock_command(
                    stock['symbol'], 
                    stock['name'], 
                    stock['tv_symbol'], 
                    interval_key
                )
            )
        )
        logger.info(f"Added command: /{cmd_name}")

# -------------------------
# Error Handler
# -------------------------
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Error: {context.error}", exc_info=True)
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "An error occurred. Please try again."
        )

telegram_app.add_error_handler(error_handler)

# -------------------------
# Flask App
# -------------------------
flask_app = Flask(__name__)

@flask_app.route("/")
def home():
    return "PSX Indicator Bot is Running!"

@flask_app.route("/health")
def health():
    return {"status": "healthy", "bot": "running"}, 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

# -------------------------
# Main Execution
# -------------------------
if __name__ == "__main__":
    try:
        flask_thread = threading.Thread(target=run_flask, daemon=True)
        flask_thread.start()
        logger.info(f"Flask server started on port {os.environ.get('PORT', 10000)}")
        
        time.sleep(2)
        
        logger.info("Starting Telegram bot...")
        telegram_app.run_polling(drop_pending_updates=True)
        
    except KeyboardInterrupt:
        logger.info("Bot stopped")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        raise
