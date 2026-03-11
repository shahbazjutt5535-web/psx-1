"""
PSX Stock Indicator Telegram Bot
PROFESSIONAL VERSION - Optimized Indicators, No Duplicates, Clean Output
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

# KSE-100 Index
kse100 = {"symbol": "KSE100", "name": "KSE-100 Index", "tv_symbol": "PSX:KSE100"}

# Alternative Meezan ETF symbols
meezan_alternatives = [
    "PSX:MZNPETF",
    "PSX:MEZNPETF", 
    "PSX:MEEZAN",
    "PSX:MZNP",
]

# Gold symbol
gold = {"symbol": "GOLD", "name": "Gold", "tv_symbol": "TVC:GOLD"}

# Combine all symbols
all_symbols = stocks + [kse100] + [gold]

# -------------------------
# PROFESSIONAL INDICATORS - Optimized by Timeframe
# -------------------------
def calculate_indicators_by_timeframe(df, timeframe):
    """Calculate indicators - Professional Grade, No Duplicates"""
    
    # ===== BASE INDICATORS (Common for ALL Timeframes) =====
    # These are essential and light enough for all timeframes
    
    # Trend (EMA only - cleaner than SMA)
    df['EMA_9'] = EMA(df, 9)
    df['EMA_21'] = EMA(df, 21)
    df['EMA_50'] = EMA(df, 50)
    
    # Momentum (Single RSI for all timeframes)
    df['RSI'] = RSI(df, 14)  # Clean signals
    
    # MACD (Essential)
    df['MACD'], df['MACD_SIGNAL'], df['MACD_HIST'] = MACD(df)
    
    # Volume
    df['OBV'] = OBV(df)
    df['VOLUME_MA'] = Volume_MA(df, 20)
    df['VOLUME_OSC'] = Volume_Oscillator(df, 5, 20)
    
    # Volatility
    df['ATR'] = ATR(df, 14)
    df['BB_UPPER'], df['BB_MIDDLE'], df['BB_LOWER'] = Bollinger_Bands(df)
    
    # VWAP (Useful for all intraday)
    if timeframe in ["5m", "15m", "30m", "1h", "4h"]:
        df['VWAP'] = VWAP_HLC3(df)
        # VWAP Bands
        vwap, upper1, lower1, upper2, lower2 = VWAP_Bands(df, 1, 2)
        df['VWAP'] = vwap
        df['VWAP_UPPER_1'] = upper1
        df['VWAP_LOWER_1'] = lower1
        df['VWAP_UPPER_2'] = upper2
        df['VWAP_LOWER_2'] = lower2
    
    # ===== SCALPING TIMEFRAMES (5m, 15m) - Fast, Light =====
    if timeframe in ["5m", "15m"]:
        # SuperTrend - Fast
        df['SUPERTREND'] = SuperTrend(df, period=7, multiplier=3)
        
        # Donchian Channel - Fast
        df['DC_UPPER'], df['DC_MIDDLE'], df['DC_LOWER'] = DonchianChannel(df, 10)
        
        # MFI - Money Flow Index
        df['MFI'] = MFI(df, 10)
        
        # Heikin Ashi for trend visualization
        df['HA_CLOSE'] = HeikinAshi(df)
    
    # ===== INTRADAY TIMEFRAMES (30m, 1h) - Medium =====
    elif timeframe in ["30m", "1h"]:
        # Add longer EMAs
        df['EMA_200'] = EMA(df, 200)
        
        # SuperTrend - Medium
        df['SUPERTREND'] = SuperTrend(df, period=10, multiplier=3)
        
        # Donchian Channel
        df['DC_UPPER'], df['DC_MIDDLE'], df['DC_LOWER'] = DonchianChannel(df, 20)
        
        # MFI
        df['MFI'] = MFI(df, 14)
        
        # Aroon
        df['AROON_UP'], df['AROON_DOWN'] = Aroon(df, 14)
        
        # Heikin Ashi
        df['HA_CLOSE'] = HeikinAshi(df)
    
    # ===== SWING TIMEFRAMES (4h) - Slower, More Reliable =====
    elif timeframe == "4h":
        # All EMAs
        df['EMA_200'] = EMA(df, 200)
        
        # Ichimoku (Heavy - only on 4h+)
        df['ICHIMOKU_CONVERSION'], df['ICHIMOKU_BASE'], df['ICHIMOKU_SPAN_A'], df['ICHIMOKU_SPAN_B'] = Ichimoku(df)
        
        # SuperTrend - Slow
        df['SUPERTREND'] = SuperTrend(df, period=14, multiplier=3)
        
        # Donchian Channel
        df['DC_UPPER'], df['DC_MIDDLE'], df['DC_LOWER'] = DonchianChannel(df, 20)
        
        # MFI
        df['MFI'] = MFI(df, 14)
        
        # Aroon
        df['AROON_UP'], df['AROON_DOWN'] = Aroon(df, 14)
        
        # ADX for trend strength
        df['ADX'], df['PLUS_DI'], df['MINUS_DI'] = ADX(df, 14)
        
        # Heikin Ashi
        df['HA_CLOSE'] = HeikinAshi(df)
        
        # Fibonacci Retracement (Heavy - 4h+)
        try:
            fib_high, fib_low, fib_levels, current_level = Fibonacci_Retracement(df, 100)
            if fib_high is not None:
                df['FIB_HIGH'] = fib_high
                df['FIB_LOW'] = fib_low
                df.attrs['fib_levels'] = fib_levels
        except:
            pass
        
        # Fibonacci Extension (Heavy - 4h+)
        try:
            ext_low, ext_high, retrace_low, extensions = Fibonacci_Extension(df, 100)
            if ext_low is not None:
                df['FIB_EXT_LOW'] = ext_low
                df['FIB_EXT_HIGH'] = ext_high
                df.attrs['fib_extensions'] = extensions
        except:
            pass
    
    # ===== POSITION TIMEFRAMES (1d, 1w) - Heaviest, Most Reliable =====
    else:  # "1d", "1w"
        # All EMAs
        df['EMA_200'] = EMA(df, 200)
        
        # Ichimoku
        df['ICHIMOKU_CONVERSION'], df['ICHIMOKU_BASE'], df['ICHIMOKU_SPAN_A'], df['ICHIMOKU_SPAN_B'] = Ichimoku(df)
        
        # Multiple SuperTrends for confirmation
        df['SUPERTREND_7'] = SuperTrend(df, period=7, multiplier=3)
        df['SUPERTREND_14'] = SuperTrend(df, period=14, multiplier=3)
        
        # Donchian Channel
        df['DC_UPPER'], df['DC_MIDDLE'], df['DC_LOWER'] = DonchianChannel(df, 20)
        
        # MFI
        df['MFI'] = MFI(df, 14)
        
        # Aroon
        df['AROON_UP'], df['AROON_DOWN'] = Aroon(df, 14)
        
        # ADX
        df['ADX'], df['PLUS_DI'], df['MINUS_DI'] = ADX(df, 14)
        
        # Ultimate Oscillator
        df['UO'] = UltimateOscillator(df)
        
        # Heikin Ashi
        df['HA_CLOSE'] = HeikinAshi(df)
        
        # Fibonacci (Full analysis)
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
        
        # Market Profile (Heaviest - Only on Daily+)
        try:
            poc, va_low, va_high, bins, profile = Volume_Profile(df, 12)
            if poc is not None:
                df['VOL_PROFILE_POC'] = poc
                df['VOL_PROFILE_VA_LOW'] = va_low
                df['VOL_PROFILE_VA_HIGH'] = va_high
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
# Create stock command with clean output
# -------------------------
def create_stock_command(symbol, name, tv_symbol, interval_key):
    """Create a command handler with professional indicator output"""
    
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
            
            # Calculate indicators
            df = calculate_indicators_by_timeframe(df, interval_key)
            
            # Get latest values
            last = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else last
            
            # Calculate Day's Range
            if interval_key in ["5m", "15m", "30m", "1h", "4h"]:
                today = pd.Timestamp.now().date()
                today_data = df[df.index.date == today]
                
                if not today_data.empty:
                    day_high = today_data['high'].max()
                    day_low = today_data['low'].min()
                else:
                    day_high = df['high'].iloc[-min(24, len(df)):].max()
                    day_low = df['low'].iloc[-min(24, len(df)):].min()
            else:
                day_high = last['high']
                day_low = last['low']
            
            # Format close time
            close_time = df.index[-1].strftime('%Y-%m-%d %H:%M:%S')
            
            # Calculate change
            change_points = last['close'] - prev['close']
            change_percent = (change_points / prev['close']) * 100 if prev['close'] != 0 else 0
            
            if change_points > 0:
                change_sign = "+"
            elif change_points < 0:
                change_sign = "-"
            else:
                change_sign = "="
            
            # BUILD MESSAGE - Professional Format
            message_lines = []
            
            # Header
            message_lines.append(f"{name} - {tv_symbol} ({interval_key})")
            message_lines.append("=" * 50)
            message_lines.append("")
            
            # 1. MARKET OVERVIEW
            message_lines.append("1. MARKET OVERVIEW")
            message_lines.append("-" * 30)
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
            message_lines.append("-" * 30)
            
            # EMAs
            ema_lines = []
            if 'EMA_9' in last.index:
                ema_lines.append(f"EMA 9            : {format_value(last['EMA_9'])}")
            if 'EMA_21' in last.index:
                ema_lines.append(f"EMA 21           : {format_value(last['EMA_21'])}")
            if 'EMA_50' in last.index:
                ema_lines.append(f"EMA 50           : {format_value(last['EMA_50'])}")
            if 'EMA_200' in last.index:
                ema_lines.append(f"EMA 200          : {format_value(last['EMA_200'])}")
            
            if ema_lines:
                message_lines.extend(ema_lines)
                message_lines.append("")
            
            # Ichimoku (Higher timeframes only)
            if 'ICHIMOKU_CONVERSION' in last.index:
                message_lines.append("Ichimoku Cloud:")
                message_lines.append(f"  Conversion Line : {format_value(last['ICHIMOKU_CONVERSION'])}")
                message_lines.append(f"  Base Line       : {format_value(last['ICHIMOKU_BASE'])}")
                message_lines.append(f"  Span A          : {format_value(last['ICHIMOKU_SPAN_A'])}")
                message_lines.append(f"  Span B          : {format_value(last['ICHIMOKU_SPAN_B'])}")
                message_lines.append("")
            
            # SuperTrend
            st_lines = []
            if 'SUPERTREND' in last.index:
                st_lines.append(f"SuperTrend       : {format_value(last['SUPERTREND'])}")
            if 'SUPERTREND_7' in last.index:
                st_lines.append(f"SuperTrend(7)    : {format_value(last['SUPERTREND_7'])}")
            if 'SUPERTREND_14' in last.index:
                st_lines.append(f"SuperTrend(14)   : {format_value(last['SUPERTREND_14'])}")
            
            if st_lines:
                message_lines.extend(st_lines)
                message_lines.append("")
            
            # Heikin Ashi
            if 'HA_CLOSE' in last.index:
                message_lines.append(f"Heikin Ashi Close: {format_value(last['HA_CLOSE'])}")
                message_lines.append("")
            
            # 3. MOMENTUM INDICATORS
            message_lines.append("3. MOMENTUM INDICATORS")
            message_lines.append("-" * 30)
            
            # MACD
            if 'MACD' in last.index:
                message_lines.append("MACD (12,26,9):")
                message_lines.append(f"  MACD Line      : {format_value(last['MACD'])}")
                message_lines.append(f"  Signal Line    : {format_value(last['MACD_SIGNAL'])}")
                message_lines.append(f"  Histogram      : {format_value(last['MACD_HIST'])}")
                message_lines.append("")
            
            # RSI
            if 'RSI' in last.index:
                message_lines.append(f"RSI (14)         : {format_value(last['RSI'])}")
                message_lines.append("")
            
            # ADX (Higher timeframes)
            if 'ADX' in last.index:
                message_lines.append("ADX (14):")
                message_lines.append(f"  ADX            : {format_value(last['ADX'])}")
                message_lines.append(f"  +DI            : {format_value(last['PLUS_DI'])}")
                message_lines.append(f"  -DI            : {format_value(last['MINUS_DI'])}")
                message_lines.append("")
            
            # Ultimate Oscillator (Daily+)
            if 'UO' in last.index:
                message_lines.append(f"Ultimate Osc     : {format_value(last['UO'])}")
                message_lines.append("")
            
            # 4. VOLUME & MONEY FLOW
            message_lines.append("4. VOLUME & MONEY FLOW")
            message_lines.append("-" * 30)
            
            # OBV
            if 'OBV' in last.index:
                message_lines.append(f"OBV              : {format_value(last['OBV'], 0)}")
                message_lines.append("")
            
            # MFI
            if 'MFI' in last.index:
                message_lines.append(f"MFI              : {format_value(last['MFI'])}")
                message_lines.append("")
            
            # Volume Analysis
            if 'VOLUME_MA' in last.index:
                volume_ratio = last['volume'] / last['VOLUME_MA'] if last['VOLUME_MA'] > 0 else 0
                message_lines.append(f"Volume MA(20)    : {format_value(last['VOLUME_MA'], 0)}")
                message_lines.append(f"Volume Ratio     : {format_value(volume_ratio, 2)}x")
                
                if 'VOLUME_OSC' in last.index:
                    message_lines.append(f"Volume Oscillator: {format_value(last['VOLUME_OSC'], 2)}%")
                message_lines.append("")
            
            # VWAP
            if 'VWAP' in last.index:
                message_lines.append(f"VWAP (HLC3)      : {format_value(last['VWAP'])}")
                if 'VWAP_UPPER_1' in last.index:
                    message_lines.append(f"VWAP +1σ         : {format_value(last['VWAP_UPPER_1'])}")
                    message_lines.append(f"VWAP -1σ         : {format_value(last['VWAP_LOWER_1'])}")
                if 'VWAP_UPPER_2' in last.index:
                    message_lines.append(f"VWAP +2σ         : {format_value(last['VWAP_UPPER_2'])}")
                    message_lines.append(f"VWAP -2σ         : {format_value(last['VWAP_LOWER_2'])}")
                message_lines.append("")
            
            # Aroon
            if 'AROON_UP' in last.index:
                message_lines.append("Aroon (14):")
                message_lines.append(f"  Aroon Up       : {format_value(last['AROON_UP'])}")
                message_lines.append(f"  Aroon Down     : {format_value(last['AROON_DOWN'])}")
                message_lines.append("")
            
            # 5. VOLATILITY & SUPPORT/RESISTANCE
            message_lines.append("5. VOLATILITY & SUPPORT/RESISTANCE")
            message_lines.append("-" * 30)
            
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
            
            # Donchian Channel
            if 'DC_UPPER' in last.index:
                message_lines.append("Donchian Channel:")
                message_lines.append(f"  Upper (20)     : {format_value(last['DC_UPPER'])}")
                message_lines.append(f"  Middle (20)    : {format_value(last['DC_MIDDLE'])}")
                message_lines.append(f"  Lower (20)     : {format_value(last['DC_LOWER'])}")
                message_lines.append("")
            
            # Fibonacci Levels (Higher timeframes)
            if 'FIB_HIGH' in last.index:
                message_lines.append("Fibonacci Retracement:")
                message_lines.append(f"  Swing High     : {format_value(last['FIB_HIGH'])}")
                message_lines.append(f"  Swing Low      : {format_value(last['FIB_LOW'])}")
                
                if hasattr(df, 'attrs') and 'fib_levels' in df.attrs:
                    fib_levels = df.attrs['fib_levels']
                    for level, price in sorted(fib_levels.items()):
                        message_lines.append(f"  Fib {level*100:.1f}%     : {format_value(price)}")
                message_lines.append("")
            
            if 'FIB_EXT_LOW' in last.index:
                message_lines.append("Fibonacci Extension:")
                message_lines.append(f"  Start Low      : {format_value(last['FIB_EXT_LOW'])}")
                message_lines.append(f"  Start High     : {format_value(last['FIB_EXT_HIGH'])}")
                
                if hasattr(df, 'attrs') and 'fib_extensions' in df.attrs:
                    extensions = df.attrs['fib_extensions']
                    for level, price in sorted(extensions.items()):
                        message_lines.append(f"  Ext {level*100:.1f}%    : {format_value(price)}")
                message_lines.append("")
            
            # Volume Profile (Daily+)
            if 'VOL_PROFILE_POC' in last.index and not pd.isna(last['VOL_PROFILE_POC']):
                message_lines.append("Volume Profile:")
                message_lines.append(f"  POC            : {format_value(last['VOL_PROFILE_POC'])}")
                if not pd.isna(last['VOL_PROFILE_VA_LOW']):
                    message_lines.append(f"  Value Area Low : {format_value(last['VOL_PROFILE_VA_LOW'])}")
                    message_lines.append(f"  Value Area High: {format_value(last['VOL_PROFILE_VA_HIGH'])}")
                message_lines.append("")
            
            # Join all lines
            message = "\n".join(message_lines)
            
            # Split if too long
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
    """Handle /text command - returns analysis template"""
    try:
        template = get_analysis_template()
        await update.message.reply_text(template)
    except Exception as e:
        logger.error(f"Error in text command: {e}")
        await update.message.reply_text("Error retrieving analysis template. Please try again.")

# -------------------------
# Start/Ping Commands
# -------------------------
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    start_time = time.time()
    msg = await update.message.reply_text("Checking...")
    end_time = time.time()
    ping_time = round((end_time - start_time) * 1000, 2)
    
    await msg.edit_text(
        f"PSX Bot is Working!\n"
        f"Response time: {ping_time}ms\n\n"
        f"Use /commands to see all available symbols and timeframes."
    )

async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Simple ping command"""
    start_time = time.time()
    msg = await update.message.reply_text("Pong!")
    end_time = time.time()
    latency = round((end_time - start_time) * 1000, 2)
    await msg.edit_text(f"Pong! Response time: {latency}ms")

# -------------------------
# Commands List
# -------------------------
async def list_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all available commands"""
    
    message = "AVAILABLE COMMANDS\n"
    message = "=" * 40 + "\n\n"
    
    for stock in stocks + [kse100] + [gold]:
        message += f"{stock['symbol']} - {stock['name']}\n"
        
        timeframes = ['5m', '15m', '30m', '1h', '4h', '1d', '1w']
        commands_list = []
        
        for tf in timeframes:
            cmd = f"/{stock['symbol'].lower()}_{tf}"
            commands_list.append(cmd)
        
        message += f"{'  '.join(commands_list)}\n\n"
    
    message += "OTHER COMMANDS:\n"
    message += "/start  /ping  /text  /commands\n"
    
    await update.message.reply_text(message)

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
logger.info("Added base commands")

# Add all stock commands
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
    """Handle errors"""
    logger.error(f"Error: {context.error}", exc_info=True)
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "An error occurred. Please try again."
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
        
        time.sleep(2)
        
        # Start Telegram bot
        logger.info("Starting Telegram bot...")
        telegram_app.run_polling(drop_pending_updates=True)
        
    except KeyboardInterrupt:
        logger.info("Bot stopped")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        raise
