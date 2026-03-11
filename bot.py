"""
PSX Stock Indicator Telegram Bot
UPDATED VERSION - Clean Output, No Emojis, No Overbought Labels, Day Range Added
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
builtins.input = lambda prompt='': 'y\n'  # Auto-answer with 'y' and newline

# Import tvDatafeed
try:
    from tvDatafeed import TvDatafeed, Interval
    print("tvDatafeed imported successfully")
except Exception as e:
    print(f"Failed to import tvDatafeed: {e}")
    raise

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
    raise ValueError("BOT_TOKEN environment variable not set")

# -------------------------
# TradingView Initialization
# -------------------------
def init_tvdatafeed():
    """Initialize TvDatafeed with proper handling for headless environment"""
    
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

# Initialize TvDatafeed
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
# Interval Mapping - ALL TIMEFRAMES (5min to 1week)
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

# -------------------------
# PSX Stocks - UPDATED with KSE100 Index
# -------------------------
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

# NEW: KSE-100 Index
kse100 = {"symbol": "KSE100", "name": "KSE-100 Index", "tv_symbol": "PSX:KSE100"}

# Alternative Meezan ETF symbols if the above doesn't work
meezan_alternatives = [
    "PSX:MZNPETF",
    "PSX:MEZNPETF", 
    "PSX:MEEZAN",
    "PSX:MZNP",
]

# Gold symbol
gold = {"symbol": "GOLD", "name": "Gold", "tv_symbol": "TVC:GOLD"}

# Combine all symbols (including KSE100)
all_symbols = stocks + [kse100] + [gold]

# -------------------------
# TIME FRAME OPTIMIZED INDICATORS - NO DUPLICATES
# -------------------------
def calculate_indicators_by_timeframe(df, timeframe):
    """Calculate indicators with settings optimized for specific timeframe - No duplicates"""
    
    # ===== 5 MINUTE / 15 MINUTE (Scalping - Fast) =====
    if timeframe in ["5m", "15m"]:
        # EXISTING INDICATORS
        df['SMA_20'] = SMA(df, 20)
        df['EMA_9'] = EMA(df, 9)
        df['EMA_21'] = EMA(df, 21)
        df['HMA_9'] = HMA(df, 9)
        df['ICHIMOKU_CONVERSION'], df['ICHIMOKU_BASE'], df['ICHIMOKU_SPAN_A'], df['ICHIMOKU_SPAN_B'] = Ichimoku(df)
        df['SUPERTREND'] = SuperTrend(df, period=7, multiplier=3)
        df['PSAR'] = ParabolicSAR(df)
        df['MACD'], df['MACD_SIGNAL'], df['MACD_HIST'] = MACD(df)
        df['RSI_14'] = RSI(df, 14)
        df['RSI_7'] = RSI(df, 7)
        df['STOCH_14_3_K'], df['STOCH_14_3_D'] = Stochastic(df, 14, 3)
        df['STOCH_9_6_3_K'], df['STOCH_9_6_3_D'] = Stochastic_9_6_3(df)
        df['KDJ_K'], df['KDJ_D'], df['KDJ_J'] = KDJ(df, 9, 3, 3)
        df['WILLIAMS'] = WilliamsR(df, 25)
        df['CCI'] = CCI(df, 14)
        df['ROC'] = ROC(df, 14)
        df['ADX'], df['PLUS_DI'], df['MINUS_DI'] = ADX(df, 14)
        df['UO'] = UltimateOscillator(df)
        df['OBV'] = OBV(df)
        df['MFI'] = MFI(df, 10)
        df['AROON_UP'], df['AROON_DOWN'] = Aroon(df, 10)
        df['BB_UPPER'], df['BB_MIDDLE'], df['BB_LOWER'] = Bollinger_Bands(df, 15, 2)
        df['ATR'] = ATR(df, 7)
        df['HA_CLOSE'] = HeikinAshi(df)
        df['DC_UPPER'], df['DC_MIDDLE'], df['DC_LOWER'] = DonchianChannel(df, 15)
        
        # NEW INDICATORS
        df['STOCH_RSI_K'], df['STOCH_RSI_D'] = Stochastic_RSI(df, 14, 3, 3)
        df['VWAP_HLC3'] = VWAP_HLC3(df)
        vwap, upper1, lower1, upper2, lower2 = VWAP_Bands(df, 1, 2)
        df['VWAP'] = vwap
        df['VWAP_UPPER_1'] = upper1
        df['VWAP_LOWER_1'] = lower1
        df['VWAP_UPPER_2'] = upper2
        df['VWAP_LOWER_2'] = lower2
        df['VOLUME_MA_20'] = Volume_MA(df, 20)
        df['VOLUME_OSC'] = Volume_Oscillator(df, 5, 20)
        df['VOLT_10'] = VOLT(df, 10)
        
        tdi_result = TDI(df, 13, 34, 34)
        if len(tdi_result) == 5:
            df['TDI_RSI'], df['TDI_UPPER'], df['TDI_LOWER'], df['TDI_SIGNAL'], df['TDI_MARKET_BASE'] = tdi_result
    
    # ===== 30 MINUTE / 1 HOUR (Intraday - Medium) =====
    elif timeframe in ["30m", "1h"]:
        df['SMA_20'] = SMA(df, 20)
        df['SMA_50'] = SMA(df, 50)
        df['EMA_9'] = EMA(df, 9)
        df['EMA_21'] = EMA(df, 21)
        df['EMA_50'] = EMA(df, 50)
        df['HMA_14'] = HMA(df, 14)
        df['ICHIMOKU_CONVERSION'], df['ICHIMOKU_BASE'], df['ICHIMOKU_SPAN_A'], df['ICHIMOKU_SPAN_B'] = Ichimoku(df)
        df['SUPERTREND'] = SuperTrend(df, period=10, multiplier=3)
        df['PSAR'] = ParabolicSAR(df)
        df['MACD'], df['MACD_SIGNAL'], df['MACD_HIST'] = MACD(df)
        df['RSI_14'] = RSI(df, 14)
        df['RSI_7'] = RSI(df, 7)
        df['STOCH_14_3_K'], df['STOCH_14_3_D'] = Stochastic(df, 14, 3)
        df['STOCH_9_6_3_K'], df['STOCH_9_6_3_D'] = Stochastic_9_6_3(df)
        df['KDJ_K'], df['KDJ_D'], df['KDJ_J'] = KDJ(df)
        df['WILLIAMS'] = WilliamsR(df, 25)
        df['CCI'] = CCI(df, 14)
        df['ROC'] = ROC(df, 14)
        df['UO'] = UltimateOscillator(df)
        df['ADX'], df['PLUS_DI'], df['MINUS_DI'] = ADX(df, 14)
        df['OBV'] = OBV(df)
        df['MFI'] = MFI(df, 14)
        df['AROON_UP'], df['AROON_DOWN'] = Aroon(df, 14)
        df['BB_UPPER'], df['BB_MIDDLE'], df['BB_LOWER'] = Bollinger_Bands(df)
        df['ATR'] = ATR(df, 14)
        df['HA_CLOSE'] = HeikinAshi(df)
        df['DC_UPPER'], df['DC_MIDDLE'], df['DC_LOWER'] = DonchianChannel(df, 20)
        
        # NEW INDICATORS
        df['STOCH_RSI_K'], df['STOCH_RSI_D'] = Stochastic_RSI(df, 14, 3, 3)
        df['VWAP_HLC3'] = VWAP_HLC3(df)
        vwap, upper1, lower1, upper2, lower2 = VWAP_Bands(df, 1, 2)
        df['VWAP'] = vwap
        df['VWAP_UPPER_1'] = upper1
        df['VWAP_LOWER_1'] = lower1
        df['VWAP_UPPER_2'] = upper2
        df['VWAP_LOWER_2'] = lower2
        df['VOLUME_MA_20'] = Volume_MA(df, 20)
        df['VOLUME_OSC'] = Volume_Oscillator(df, 5, 20)
        df['VOLT_10'] = VOLT(df, 10)
        
        tdi_result = TDI(df, 13, 34, 34)
        if len(tdi_result) == 5:
            df['TDI_RSI'], df['TDI_UPPER'], df['TDI_LOWER'], df['TDI_SIGNAL'], df['TDI_MARKET_BASE'] = tdi_result
        
        try:
            fib_high, fib_low, fib_levels, current_level = Fibonacci_Retracement(df, 50)
            if fib_high is not None:
                df['FIB_HIGH'] = fib_high
                df['FIB_LOW'] = fib_low
                df.attrs['fib_levels'] = fib_levels
        except:
            pass
    
    # ===== 4 HOUR (Swing Trading - Slow) =====
    elif timeframe == "4h":
        df['SMA_20'] = SMA(df, 20)
        df['SMA_50'] = SMA(df, 50)
        df['SMA_200'] = SMA(df, 200)
        df['EMA_9'] = EMA(df, 9)
        df['EMA_21'] = EMA(df, 21)
        df['EMA_50'] = EMA(df, 50)
        df['EMA_200'] = EMA(df, 200)
        df['HMA_21'] = HMA(df, 21)
        df['ICHIMOKU_CONVERSION'], df['ICHIMOKU_BASE'], df['ICHIMOKU_SPAN_A'], df['ICHIMOKU_SPAN_B'] = Ichimoku(df)
        df['SUPERTREND'] = SuperTrend(df, period=14, multiplier=3)
        df['PSAR'] = ParabolicSAR(df)
        df['MACD'], df['MACD_SIGNAL'], df['MACD_HIST'] = MACD(df)
        df['RSI_14'] = RSI(df, 14)
        df['RSI_7'] = RSI(df, 7)
        df['STOCH_14_3_K'], df['STOCH_14_3_D'] = Stochastic(df, 14, 3)
        df['STOCH_9_6_3_K'], df['STOCH_9_6_3_D'] = Stochastic_9_6_3(df)
        df['KDJ_K'], df['KDJ_D'], df['KDJ_J'] = KDJ(df)
        df['WILLIAMS'] = WilliamsR(df, 25)
        df['CCI'] = CCI(df, 20)
        df['ROC'] = ROC(df, 14)
        df['ADX'], df['PLUS_DI'], df['MINUS_DI'] = ADX(df, 14)
        df['OBV'] = OBV(df)
        df['MFI'] = MFI(df, 14)
        df['AROON_UP'], df['AROON_DOWN'] = Aroon(df, 14)
        df['BB_UPPER'], df['BB_MIDDLE'], df['BB_LOWER'] = Bollinger_Bands(df)
        df['ATR'] = ATR(df, 14)
        df['HA_CLOSE'] = HeikinAshi(df)
        df['DC_UPPER'], df['DC_MIDDLE'], df['DC_LOWER'] = DonchianChannel(df, 20)
        
        # NEW INDICATORS
        df['STOCH_RSI_K'], df['STOCH_RSI_D'] = Stochastic_RSI(df, 14, 3, 3)
        df['VWAP_HLC3'] = VWAP_HLC3(df)
        vwap, upper1, lower1, upper2, lower2 = VWAP_Bands(df, 1, 2)
        df['VWAP'] = vwap
        df['VWAP_UPPER_1'] = upper1
        df['VWAP_LOWER_1'] = lower1
        df['VWAP_UPPER_2'] = upper2
        df['VWAP_LOWER_2'] = lower2
        df['VOLUME_MA_20'] = Volume_MA(df, 20)
        df['VOLUME_OSC'] = Volume_Oscillator(df, 5, 20)
        df['VOLT_10'] = VOLT(df, 10)
        
        tdi_result = TDI(df, 13, 34, 34)
        if len(tdi_result) == 5:
            df['TDI_RSI'], df['TDI_UPPER'], df['TDI_LOWER'], df['TDI_SIGNAL'], df['TDI_MARKET_BASE'] = tdi_result
        
        try:
            fib_high, fib_low, fib_levels, current_level = Fibonacci_Retracement(df, 100)
            if fib_high is not None:
                df['FIB_HIGH'] = fib_high
                df['FIB_LOW'] = fib_low
                df.attrs['fib_levels'] = fib_levels
                
            ext_low, ext_high, retrace_low, extensions = Fibonacci_Extension(df, 100)
            if ext_low is not None:
                df['FIB_EXT_LOW'] = ext_low
                df['FIB_EXT_HIGH'] = ext_high
                df.attrs['fib_extensions'] = extensions
        except:
            pass
    
    # ===== DAILY / WEEKLY (Position Trading) =====
    else:  # "1d", "1w"
        df['SMA_20'] = SMA(df, 20)
        df['SMA_50'] = SMA(df, 50)
        df['SMA_200'] = SMA(df, 200)
        df['EMA_9'] = EMA(df, 9)
        df['EMA_21'] = EMA(df, 21)
        df['EMA_50'] = EMA(df, 50)
        df['EMA_200'] = EMA(df, 200)
        df['HMA_21'] = HMA(df, 21)
        df['ICHIMOKU_CONVERSION'], df['ICHIMOKU_BASE'], df['ICHIMOKU_SPAN_A'], df['ICHIMOKU_SPAN_B'] = Ichimoku(df)
        df['SUPERTREND_7'] = SuperTrend(df, period=7, multiplier=3)
        df['SUPERTREND_10'] = SuperTrend(df, period=10, multiplier=3)
        df['SUPERTREND_14'] = SuperTrend(df, period=14, multiplier=3)
        df['PSAR'] = ParabolicSAR(df)
        df['MACD'], df['MACD_SIGNAL'], df['MACD_HIST'] = MACD(df)
        df['RSI_14'] = RSI(df, 14)
        df['RSI_7'] = RSI(df, 7)
        df['STOCH_14_3_K'], df['STOCH_14_3_D'] = Stochastic(df, 14, 3)
        df['STOCH_9_6_3_K'], df['STOCH_9_6_3_D'] = Stochastic_9_6_3(df)
        df['KDJ_K'], df['KDJ_D'], df['KDJ_J'] = KDJ(df)
        df['WILLIAMS'] = WilliamsR(df, 25)
        df['CCI'] = CCI(df, 20)
        df['ROC'] = ROC(df, 14)
        df['ADX'], df['PLUS_DI'], df['MINUS_DI'] = ADX(df, 14)
        df['UO'] = UltimateOscillator(df)
        df['OBV'] = OBV(df)
        df['MFI'] = MFI(df, 14)
        df['AROON_UP'], df['AROON_DOWN'] = Aroon(df, 14)
        df['BB_UPPER'], df['BB_MIDDLE'], df['BB_LOWER'] = Bollinger_Bands(df)
        df['ATR'] = ATR(df, 14)
        df['HA_CLOSE'] = HeikinAshi(df)
        df['DC_UPPER'], df['DC_MIDDLE'], df['DC_LOWER'] = DonchianChannel(df, 20)
        
        # NEW INDICATORS
        df['STOCH_RSI_K'], df['STOCH_RSI_D'] = Stochastic_RSI(df, 14, 3, 3)
        df['VWAP_HLC3'] = VWAP_HLC3(df)
        vwap, upper1, lower1, upper2, lower2 = VWAP_Bands(df, 1, 2)
        df['VWAP'] = vwap
        df['VWAP_UPPER_1'] = upper1
        df['VWAP_LOWER_1'] = lower1
        df['VWAP_UPPER_2'] = upper2
        df['VWAP_LOWER_2'] = lower2
        df['VOLUME_MA_20'] = Volume_MA(df, 20)
        df['VOLUME_OSC'] = Volume_Oscillator(df, 5, 20)
        df['VOLT_10'] = VOLT(df, 10)
        
        tdi_result = TDI(df, 13, 34, 34)
        if len(tdi_result) == 5:
            df['TDI_RSI'], df['TDI_UPPER'], df['TDI_LOWER'], df['TDI_SIGNAL'], df['TDI_MARKET_BASE'] = tdi_result
        
        try:
            fib_high, fib_low, fib_levels, current_level = Fibonacci_Retracement(df, 200)
            if fib_high is not None:
                df['FIB_HIGH'] = fib_high
                df['FIB_LOW'] = fib_low
                df.attrs['fib_levels'] = fib_levels
                
            ext_low, ext_high, retrace_low, extensions = Fibonacci_Extension(df, 200)
            if ext_low is not None:
                df['FIB_EXT_LOW'] = ext_low
                df['FIB_EXT_HIGH'] = ext_high
                df.attrs['fib_extensions'] = extensions
        except:
            pass
        
        try:
            mp_poc, mp_levels = Market_Profile(df, 20)
            if mp_poc is not None:
                df['MARKET_PROFILE_POC'] = mp_poc
        except:
            pass
    
    return df

# -------------------------
# Format indicator values
# -------------------------
def format_value(value, decimals=2):
    """Format numeric value, handling NaN"""
    if pd.isna(value):
        return "N/A"
    if isinstance(value, (int, float)):
        return f"{value:.{decimals}f}"
    return str(value)

# -------------------------
# Create stock command with clean output format (no emojis)
# -------------------------
def create_stock_command(symbol, name, tv_symbol, interval_key):
    """Create a command handler with clean indicator output - no emojis, step by step format"""
    
    async def command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Send immediate acknowledgment
        await update.message.reply_text(f"Fetching {name} ({interval_key}) data... This may take 15-20 seconds.")
        
        try:
            # Run in thread pool with timeout
            loop = asyncio.get_event_loop()
            
            # Parse exchange and symbol
            if ':' in tv_symbol:
                exchange, sym = tv_symbol.split(':')
            else:
                exchange = "PSX"
                sym = tv_symbol
            
            # Use asyncio.wait_for to set a timeout
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
                    timeout=30.0
                )
            except asyncio.TimeoutError:
                logger.error(f"Timeout fetching {symbol} {interval_key}")
                await update.message.reply_text(f"Request timed out. Please try again.")
                return
            
            # Validate data
            if df is None or df.empty:
                if symbol == "MZNPETF":
                    await update.message.reply_text(f"Trying alternative symbol for {name}...")
                    for alt_sym in meezan_alternatives:
                        try:
                            if ':' in alt_sym:
                                alt_exchange, alt_symbol = alt_sym.split(':')
                            else:
                                alt_exchange = "PSX"
                                alt_symbol = alt_sym
                            
                            df = tv.get_hist(
                                symbol=alt_symbol,
                                exchange=alt_exchange,
                                interval=interval_map[interval_key],
                                n_bars=500
                            )
                            if df is not None and not df.empty:
                                await update.message.reply_text(f"Found data using symbol: {alt_sym}")
                                break
                        except:
                            continue
                
                if df is None or df.empty:
                    await update.message.reply_text(f"No data found for {name}.")
                    return
            
            # Calculate indicators based on timeframe
            df = calculate_indicators_by_timeframe(df, interval_key)
            
            # Get latest values
            last = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else last
            
            # Calculate Day's Range (current day's high and low)
            if interval_key in ["5m", "15m", "30m", "1h", "4h"]:
                # For intraday timeframes, find today's high and low
                today = pd.Timestamp.now().date()
                today_data = df[df.index.date == today]
                
                if not today_data.empty:
                    day_high = today_data['high'].max()
                    day_low = today_data['low'].min()
                else:
                    # If no data for today, use last 24 hours
                    day_high = df['high'].iloc[-min(24, len(df)):].max()
                    day_low = df['low'].iloc[-min(24, len(df)):].min()
            else:
                # For daily/weekly, the current candle itself is the day
                day_high = last['high']
                day_low = last['low']
            
            # Format close time
            close_time = df.index[-1].strftime('%Y-%m-%d %H:%M:%S')
            
            # Calculate change from previous close
            change_points = last['close'] - prev['close']
            change_percent = (change_points / prev['close']) * 100 if prev['close'] != 0 else 0
            
            # Determine change sign
            if change_points > 0:
                change_sign = "+"
            elif change_points < 0:
                change_sign = "-"
            else:
                change_sign = "="
            
            # START BUILDING MESSAGE - CLEAN FORMAT
            message_lines = []
            
            # Header
            message_lines.append(f"{name} - {tv_symbol} ({interval_key})")
            message_lines.append("=" * 40)
            message_lines.append("")
            
            # 1. MARKET OVERVIEW
            message_lines.append("1. MARKET OVERVIEW")
            message_lines.append("-" * 20)
            message_lines.append(f"Current Price    : {format_value(last['close'])}")
            message_lines.append(f"Open Price       : {format_value(last['open'])}")
            message_lines.append(f"Previous Close   : {format_value(prev['close'])}")
            message_lines.append(f"Day Range High   : {format_value(day_high)}")
            message_lines.append(f"Day Range Low    : {format_value(day_low)}")
            message_lines.append(f"Change           : {change_sign} {format_value(change_points)} ({format_value(change_percent)}%)")
            message_lines.append(f"Volume           : {format_value(last['volume'], 0)}")
            message_lines.append(f"Close Time       : {close_time}")
            message_lines.append("")
            
            # 2. TREND INDICATORS
            message_lines.append("2. TREND INDICATORS")
            message_lines.append("-" * 20)
            
            # Moving Averages
            ma_lines = []
            if 'SMA_20' in last.index:
                ma_lines.append(f"SMA 20           : {format_value(last['SMA_20'])}")
            if 'SMA_50' in last.index:
                ma_lines.append(f"SMA 50           : {format_value(last['SMA_50'])}")
            if 'SMA_200' in last.index:
                ma_lines.append(f"SMA 200          : {format_value(last['SMA_200'])}")
            if 'EMA_9' in last.index:
                ma_lines.append(f"EMA 9            : {format_value(last['EMA_9'])}")
            if 'EMA_21' in last.index:
                ma_lines.append(f"EMA 21           : {format_value(last['EMA_21'])}")
            if 'EMA_50' in last.index:
                ma_lines.append(f"EMA 50           : {format_value(last['EMA_50'])}")
            if 'EMA_200' in last.index:
                ma_lines.append(f"EMA 200          : {format_value(last['EMA_200'])}")
            if 'HMA_9' in last.index:
                ma_lines.append(f"HMA 9            : {format_value(last['HMA_9'])}")
            if 'HMA_14' in last.index:
                ma_lines.append(f"HMA 14           : {format_value(last['HMA_14'])}")
            if 'HMA_21' in last.index:
                ma_lines.append(f"HMA 21           : {format_value(last['HMA_21'])}")
            
            if ma_lines:
                message_lines.extend(ma_lines)
                message_lines.append("")
            
            # Ichimoku Cloud
            if 'ICHIMOKU_CONVERSION' in last.index:
                message_lines.append("Ichimoku Cloud:")
                message_lines.append(f"  Conversion (9) : {format_value(last['ICHIMOKU_CONVERSION'])}")
                message_lines.append(f"  Base (26)      : {format_value(last['ICHIMOKU_BASE'])}")
                message_lines.append(f"  Span A         : {format_value(last['ICHIMOKU_SPAN_A'])}")
                message_lines.append(f"  Span B         : {format_value(last['ICHIMOKU_SPAN_B'])}")
                message_lines.append("")
            
            # SuperTrend
            st_lines = []
            if 'SUPERTREND' in last.index:
                st_lines.append(f"SuperTrend       : {format_value(last['SUPERTREND'])}")
            if 'SUPERTREND_7' in last.index:
                st_lines.append(f"SuperTrend(7)    : {format_value(last['SUPERTREND_7'])}")
            if 'SUPERTREND_10' in last.index:
                st_lines.append(f"SuperTrend(10)   : {format_value(last['SUPERTREND_10'])}")
            if 'SUPERTREND_14' in last.index:
                st_lines.append(f"SuperTrend(14)   : {format_value(last['SUPERTREND_14'])}")
            
            if st_lines:
                message_lines.extend(st_lines)
                message_lines.append("")
            
            # Parabolic SAR
            if 'PSAR' in last.index:
                message_lines.append(f"Parabolic SAR    : {format_value(last['PSAR'])}")
                message_lines.append("")
            
            # 3. MOMENTUM OSCILLATORS
            message_lines.append("3. MOMENTUM OSCILLATORS")
            message_lines.append("-" * 20)
            
            # MACD
            if 'MACD' in last.index:
                message_lines.append("MACD (12,26,9):")
                message_lines.append(f"  MACD Line      : {format_value(last['MACD'])}")
                message_lines.append(f"  Signal Line    : {format_value(last['MACD_SIGNAL'])}")
                message_lines.append(f"  Histogram      : {format_value(last['MACD_HIST'])}")
                message_lines.append("")
            
            # RSI
            rsi_lines = []
            if 'RSI_14' in last.index:
                rsi_lines.append(f"RSI (14)         : {format_value(last['RSI_14'])}")
            if 'RSI_7' in last.index:
                rsi_lines.append(f"RSI (7)          : {format_value(last['RSI_7'])}")
            
            if rsi_lines:
                message_lines.extend(rsi_lines)
                message_lines.append("")
            
            # Stochastic 14,3
            if 'STOCH_14_3_K' in last.index:
                message_lines.append("Stochastic (14,3):")
                message_lines.append(f"  %K             : {format_value(last['STOCH_14_3_K'])}")
                message_lines.append(f"  %D             : {format_value(last['STOCH_14_3_D'])}")
                message_lines.append("")
            
            # Stochastic 9,6,3
            if 'STOCH_9_6_3_K' in last.index:
                message_lines.append("Stochastic (9,6,3):")
                message_lines.append(f"  %K             : {format_value(last['STOCH_9_6_3_K'])}")
                message_lines.append(f"  %D             : {format_value(last['STOCH_9_6_3_D'])}")
                message_lines.append("")
            
            # Stochastic RSI
            if 'STOCH_RSI_K' in last.index:
                message_lines.append("Stochastic RSI (14,3,3):")
                message_lines.append(f"  Stoch RSI %K   : {format_value(last['STOCH_RSI_K'])}")
                message_lines.append(f"  Stoch RSI %D   : {format_value(last['STOCH_RSI_D'])}")
                message_lines.append("")
            
            # KDJ
            if 'KDJ_K' in last.index:
                message_lines.append("KDJ (9,3,3):")
                message_lines.append(f"  K              : {format_value(last['KDJ_K'])}")
                message_lines.append(f"  D              : {format_value(last['KDJ_D'])}")
                message_lines.append(f"  J              : {format_value(last['KDJ_J'])}")
                message_lines.append("")
            
            # Williams %R
            if 'WILLIAMS' in last.index:
                message_lines.append(f"Williams %R (25) : {format_value(last['WILLIAMS'])}")
                message_lines.append("")
            
            # CCI
            if 'CCI' in last.index:
                message_lines.append(f"CCI (14)         : {format_value(last['CCI'])}")
                message_lines.append("")
            
            # ROC
            if 'ROC' in last.index:
                message_lines.append(f"ROC (14)         : {format_value(last['ROC'])}%")
                message_lines.append("")
            
            # TDI
            if 'TDI_RSI' in last.index:
                message_lines.append("TDI (13,34,34):")
                message_lines.append(f"  TDI RSI        : {format_value(last['TDI_RSI'])}")
                message_lines.append(f"  Upper Band     : {format_value(last['TDI_UPPER'])}")
                message_lines.append(f"  Lower Band     : {format_value(last['TDI_LOWER'])}")
                message_lines.append(f"  Signal Line    : {format_value(last['TDI_SIGNAL'])}")
                message_lines.append(f"  Market Base    : {format_value(last['TDI_MARKET_BASE'])}")
                message_lines.append("")
            
            # Ultimate Oscillator
            if 'UO' in last.index:
                message_lines.append(f"Ultimate Osc     : {format_value(last['UO'])}")
                message_lines.append("")
            
            # ADX
            if 'ADX' in last.index:
                message_lines.append("ADX (14):")
                message_lines.append(f"  ADX            : {format_value(last['ADX'])}")
                message_lines.append(f"  +DI            : {format_value(last['PLUS_DI'])}")
                message_lines.append(f"  -DI            : {format_value(last['MINUS_DI'])}")
                message_lines.append("")
            
            # 4. VOLUME & MONEY FLOW
            message_lines.append("4. VOLUME & MONEY FLOW")
            message_lines.append("-" * 20)
            
            # OBV
            if 'OBV' in last.index:
                message_lines.append(f"OBV              : {format_value(last['OBV'], 0)}")
                message_lines.append("")
            
            # MFI
            if 'MFI' in last.index:
                message_lines.append(f"MFI (14)         : {format_value(last['MFI'])}")
                message_lines.append("")
            
            # Volume Analysis
            vol_lines = []
            if 'VOLUME_MA_20' in last.index:
                volume_ratio = last['volume'] / last['VOLUME_MA_20'] if last['VOLUME_MA_20'] > 0 else 0
                vol_lines.append(f"Volume MA(20)    : {format_value(last['VOLUME_MA_20'], 0)}")
                vol_lines.append(f"Volume Ratio     : {format_value(volume_ratio, 2)}x")
            
            if 'VOLUME_OSC' in last.index:
                vol_lines.append(f"Volume Oscillator: {format_value(last['VOLUME_OSC'], 2)}%")
            
            if vol_lines:
                message_lines.extend(vol_lines)
                message_lines.append("")
            
            # VWAP
            vwap_lines = []
            if 'VWAP' in last.index:
                vwap_lines.append(f"VWAP (HLC3)      : {format_value(last['VWAP'])}")
            if 'VWAP_UPPER_1' in last.index:
                vwap_lines.append(f"VWAP +1σ         : {format_value(last['VWAP_UPPER_1'])}")
                vwap_lines.append(f"VWAP -1σ         : {format_value(last['VWAP_LOWER_1'])}")
            if 'VWAP_UPPER_2' in last.index:
                vwap_lines.append(f"VWAP +2σ         : {format_value(last['VWAP_UPPER_2'])}")
                vwap_lines.append(f"VWAP -2σ         : {format_value(last['VWAP_LOWER_2'])}")
            
            if vwap_lines:
                message_lines.extend(vwap_lines)
                message_lines.append("")
            
            # VOLT
            if 'VOLT_10' in last.index:
                message_lines.append(f"VOLT(10)         : {format_value(last['VOLT_10'])}")
                message_lines.append("")
            
            # Aroon
            if 'AROON_UP' in last.index:
                message_lines.append("Aroon (14):")
                message_lines.append(f"  Aroon Up       : {format_value(last['AROON_UP'])}")
                message_lines.append(f"  Aroon Down     : {format_value(last['AROON_DOWN'])}")
                message_lines.append("")
            
            # 5. VOLATILITY & RANGE
            message_lines.append("5. VOLATILITY & RANGE")
            message_lines.append("-" * 20)
            
            # Bollinger Bands
            if 'BB_UPPER' in last.index:
                bb_width = (last['BB_UPPER'] - last['BB_LOWER']) / last['BB_MIDDLE'] * 100
                message_lines.append("Bollinger Bands (20,2):")
                message_lines.append(f"  Upper          : {format_value(last['BB_UPPER'])}")
                message_lines.append(f"  Middle         : {format_value(last['BB_MIDDLE'])}")
                message_lines.append(f"  Lower          : {format_value(last['BB_LOWER'])}")
                message_lines.append(f"  Band Width     : {format_value(bb_width, 2)}%")
                message_lines.append("")
            
            # ATR
            if 'ATR' in last.index:
                message_lines.append(f"ATR (14)         : {format_value(last['ATR'])}")
                message_lines.append("")
            
            # Heikin Ashi
            if 'HA_CLOSE' in last.index:
                message_lines.append(f"Heikin Ashi Close: {format_value(last['HA_CLOSE'])}")
                message_lines.append("")
            
            # Donchian Channel
            if 'DC_UPPER' in last.index:
                message_lines.append("Donchian Channel (20):")
                message_lines.append(f"  Upper          : {format_value(last['DC_UPPER'])}")
                message_lines.append(f"  Middle         : {format_value(last['DC_MIDDLE'])}")
                message_lines.append(f"  Lower          : {format_value(last['DC_LOWER'])}")
                message_lines.append("")
            
            # Fibonacci (if available)
            if 'FIB_HIGH' in last.index:
                message_lines.append("Fibonacci Levels:")
                message_lines.append(f"  Swing High     : {format_value(last['FIB_HIGH'])}")
                message_lines.append(f"  Swing Low      : {format_value(last['FIB_LOW'])}")
                
                if hasattr(df, 'attrs') and 'fib_levels' in df.attrs:
                    fib_levels = df.attrs['fib_levels']
                    for level, price in sorted(fib_levels.items()):
                        message_lines.append(f"  Fib {level*100:.1f}%     : {format_value(price)}")
                message_lines.append("")
            
            # Join all lines
            message = "\n".join(message_lines)
            
            # Split message if too long
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
# Text Command - Returns the analysis template
# -------------------------
async def text_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /text command - returns the analysis template for copying"""
    try:
        template = get_analysis_template()
        await update.message.reply_text(template)
        logger.info(f"Text command used by user {update.effective_user.id}")
    except Exception as e:
        logger.error(f"Error in text command: {e}")
        await update.message.reply_text("Error retrieving analysis template. Please try again.")

# -------------------------
# Start/Ping Commands
# -------------------------
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command with simple response"""
    
    start_time = time.time()
    msg = await update.message.reply_text("Checking...")
    end_time = time.time()
    ping_time = round((end_time - start_time) * 1000, 2)
    
    await msg.edit_text(
        f"Your PSX Bot is working! ✅\n"
        f"Ping response time: {ping_time}ms"
    )

async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Simple ping command"""
    start_time = time.time()
    msg = await update.message.reply_text("Pong!")
    end_time = time.time()
    latency = round((end_time - start_time) * 1000, 2)
    await msg.edit_text(f"Pong! Response time: {latency}ms")

# -------------------------
# Commands List Feature
# -------------------------
async def list_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /commands - show all available commands"""
    
    message = "📋 Available Commands 📋\n\n"
    
    for stock in stocks + [kse100] + [gold]:
        message += f"{stock['symbol']}\n"
        
        timeframes = ['5m', '15m', '30m', '1h', '4h', '1d', '1w']
        commands_list = []
        
        for tf in timeframes:
            cmd = f"/{stock['symbol'].lower()}_{tf}"
            commands_list.append(cmd)
    
        message += f"{' ,  '.join(commands_list)}\n\n"
    
    message += "━━━━━━━━━━━━━━━━━━━━━\n"
    message += "Other Commands:\n"
    message += "/start  /ping  /text\n\n"
    message += "Tip: Click on any command above to execute it!"
    
    await update.message.reply_text(message, parse_mode='Markdown')

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
telegram_app.add_handler(CommandHandler("commands", list_commands))
logger.info("Added commands: /start, /ping, /text, /commands")

# Add all stock commands for all timeframes
for stock in stocks + [kse100] + [gold]:
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
    """Handle errors gracefully"""
    logger.error(f"Error: {context.error}", exc_info=True)
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "An error occurred. Please try again.\n"
                "If the problem persists, try a different timeframe or contact support."
            )
    except Exception as e:
        logger.error(f"Error in error handler: {e}")

telegram_app.add_error_handler(error_handler)

# -------------------------
# Flask App for Render
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
        # Start Flask
        flask_thread = threading.Thread(target=run_flask, daemon=True)
        flask_thread.start()
        logger.info(f"Flask server started on port {os.environ.get('PORT', 10000)}")
        
        # Small delay
        time.sleep(2)
        
        # Start Telegram bot
        logger.info("Starting Telegram bot...")
        telegram_app.run_polling(drop_pending_updates=True)
        
    except KeyboardInterrupt:
        logger.info("Bot stopped")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        raise
