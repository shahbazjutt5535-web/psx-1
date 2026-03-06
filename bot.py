"""
PSX Stock Indicator Telegram Bot
FINAL VERSION - Sirf PSX, No Emoji, Clean Output
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

# Import PSX Sentiment
from psx_sentiment import PSXSentiment

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
NEWS_API_KEY = "pub_57d11436088e4e8b980721f19cb48762"  # Aapki API key

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable not set")

# Initialize PSX Sentiment
psx_sentiment = PSXSentiment(NEWS_API_KEY)

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
# Interval Mapping
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

# PSX Stocks - Complete List
stocks = [
    {"symbol": "FFC", "name": "Fauji Fertilizer Company", "tv_symbol": "PSX:FFC", "sector": "Fertilizer"},
    {"symbol": "ENGROH", "name": "Engro Holdings", "tv_symbol": "PSX:ENGROH", "sector": "Conglomerate"},
    {"symbol": "OGDC", "name": "Oil & Gas Development Company", "tv_symbol": "PSX:OGDC", "sector": "Energy"},
    {"symbol": "HUBC", "name": "Hub Power Company", "tv_symbol": "PSX:HUBC", "sector": "Energy"},
    {"symbol": "PPL", "name": "Pakistan Petroleum Limited", "tv_symbol": "PSX:PPL", "sector": "Energy"},
    {"symbol": "NBP", "name": "National Bank of Pakistan", "tv_symbol": "PSX:NBP", "sector": "Banking"},
    {"symbol": "UBL", "name": "United Bank Limited", "tv_symbol": "PSX:UBL", "sector": "Banking"},
    {"symbol": "MZNPETF", "name": "Meezan Pakistan ETF", "tv_symbol": "PSX:MZNPETF", "sector": "ETF"},
    {"symbol": "NBPGETF", "name": "NBP Pakistan Growth ETF", "tv_symbol": "PSX:NBPGETF", "sector": "ETF"},
    {"symbol": "KEL", "name": "K-Electric", "tv_symbol": "PSX:KEL", "sector": "Energy"},
    {"symbol": "SYS", "name": "Systems Limited", "tv_symbol": "PSX:SYS", "sector": "Technology"},
    {"symbol": "LUCK", "name": "Lucky Cement", "tv_symbol": "PSX:LUCK", "sector": "Cement"},
    {"symbol": "PSO", "name": "Pakistan State Oil", "tv_symbol": "PSX:PSO", "sector": "Energy"},
]

# Gold symbol
gold = {"symbol": "GOLD", "name": "Gold", "tv_symbol": "TVC:GOLD", "sector": "Commodity"}

# Combine all symbols
all_symbols = stocks + [gold]

# -------------------------
# TIME FRAME OPTIMIZED INDICATORS
# -------------------------
def calculate_indicators_by_timeframe(df, timeframe):
    """Calculate indicators with settings optimized for specific timeframe"""
    
    # ===== 5 MINUTE / 15 MINUTE (Scalping - Fast) =====
    if timeframe in ["5m", "15m"]:
        df['SMA_20'] = SMA(df, 20)
        df['EMA_9'] = EMA(df, 9)
        df['EMA_21'] = EMA(df, 21)
        df['HMA_9'] = HMA(df, 9)
        df['ICHIMOKU_CONVERSION'], df['ICHIMOKU_BASE'], df['ICHIMOKU_SPAN_A'], df['ICHIMOKU_SPAN_B'] = Ichimoku(df)
        df['SUPERTREND'] = SuperTrend(df, period=7, multiplier=3)
        df['PSAR'] = ParabolicSAR(df)
        df['MACD'], df['MACD_SIGNAL'], df['MACD_HIST'] = MACD(df)
        df['RSI'] = RSI(df, 14)
        df['STOCH_K'], df['STOCH_D'] = Stochastic(df, 10, 3)
        df['KDJ_K'], df['KDJ_D'] = KDJ(df, 9, 3, 3)
        df['WILLIAMS'] = WilliamsR(df, 25)
        df['CCI'] = CCI(df, 14)
        df['ROC'] = ROC(df, 14)
        df['ADX'], df['PLUS_DI'], df['MINUS_DI'] = ADX(df, 14)
        df['UO'] = UltimateOscillator(df)
        df['OBV'] = OBV(df)
        df['MFI'] = MFI(df, 10)
        df['VWAP'] = VWAP(df)
        df['AROON_UP'], df['AROON_DOWN'] = Aroon(df, 10)
        df['BB_UPPER'], df['BB_MIDDLE'], df['BB_LOWER'] = Bollinger_Bands(df, 15, 2)
        df['ATR'] = ATR(df, 7)
        df['HA_CLOSE'] = HeikinAshi(df)
        df['DC_UPPER'], df['DC_MIDDLE'], df['DC_LOWER'] = DonchianChannel(df, 15)
    
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
        df['RSI'] = RSI(df, 14)
        df['STOCH_K'], df['STOCH_D'] = Stochastic(df, 14, 3)
        df['KDJ_K'], df['KDJ_D'] = KDJ(df)
        df['WILLIAMS'] = WilliamsR(df, 25)
        df['CCI'] = CCI(df, 14)
        df['ROC'] = ROC(df, 14)
        df['ADX'], df['PLUS_DI'], df['MINUS_DI'] = ADX(df, 14)
        df['UO'] = UltimateOscillator(df)
        df['OBV'] = OBV(df)
        df['MFI'] = MFI(df, 14)
        df['VWAP'] = VWAP(df)
        df['AROON_UP'], df['AROON_DOWN'] = Aroon(df, 14)
        df['BB_UPPER'], df['BB_MIDDLE'], df['BB_LOWER'] = Bollinger_Bands(df)
        df['ATR'] = ATR(df, 14)
        df['HA_CLOSE'] = HeikinAshi(df)
        df['DC_UPPER'], df['DC_MIDDLE'], df['DC_LOWER'] = DonchianChannel(df, 20)
    
    # ===== 4 HOUR / DAILY / WEEKLY (Swing/Position) =====
    else:
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
        df['RSI'] = RSI(df, 14)
        df['STOCH_K'], df['STOCH_D'] = Stochastic(df, 14, 3)
        df['KDJ_K'], df['KDJ_D'] = KDJ(df)
        df['WILLIAMS'] = WilliamsR(df, 25)
        df['CCI'] = CCI(df, 20)
        df['ROC'] = ROC(df, 14)
        df['ADX'], df['PLUS_DI'], df['MINUS_DI'] = ADX(df, 14)
        df['UO'] = UltimateOscillator(df)
        df['OBV'] = OBV(df)
        df['MFI'] = MFI(df, 14)
        df['VWAP'] = VWAP(df)
        df['AROON_UP'], df['AROON_DOWN'] = Aroon(df, 14)
        df['BB_UPPER'], df['BB_MIDDLE'], df['BB_LOWER'] = Bollinger_Bands(df)
        df['ATR'] = ATR(df, 14)
        df['HA_CLOSE'] = HeikinAshi(df)
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
# Create stock command - NO EMOJI, NO SIGNALS
# -------------------------
def create_stock_command(stock_info, interval_key):
    
    async def command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        symbol = stock_info['symbol']
        name = stock_info['name']
        tv_symbol = stock_info['tv_symbol']
        
        await update.message.reply_text(f"Fetching {name} ({interval_key}) data...")
        
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
                await update.message.reply_text(f"Request timed out.")
                return
            
            if df is None or df.empty:
                await update.message.reply_text(f"No data found for {name}.")
                return
            
            # Calculate indicators
            df = calculate_indicators_by_timeframe(df, interval_key)
            
            # Get sentiment for PSX stock
            sentiment = psx_sentiment.get_company_news_sentiment(name, symbol)
            
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
            
            # Build message - NO EMOJIS
            message = (
                f"📊 {name} - PSX ({interval_key})\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n\n"
                
                f"1️⃣ Market Overview\n"
                f"Price: {format_value(last['close'])}\n"
                f"Open: {format_value(last['open'])}\n"
                f"High: {format_value(last['high'])}\n"
                f"Low: {format_value(last['low'])}\n"
                f"Change: {change_sign}{format_value(abs(change_points))} ({format_value(change_percent)}%)\n"
                f"Volume: {format_value(last['volume'], 0)}\n"
                f"Close Time: {close_time}\n\n"
                
                f"2️⃣ Trend Direction\n\n"
            )
            
            # SMA
            sma_section = "Simple Moving Averages (SMA):\n"
            if 'SMA_20' in last.index:
                sma_section += f"  SMA 20: {format_value(last['SMA_20'])}\n"
            if 'SMA_50' in last.index:
                sma_section += f"  SMA 50: {format_value(last['SMA_50'])}\n"
            if 'SMA_200' in last.index:
                sma_section += f"  SMA 200: {format_value(last['SMA_200'])}\n"
            message += sma_section + "\n"
            
            # EMA
            ema_section = "Exponential Moving Averages (EMA):\n"
            if 'EMA_9' in last.index:
                ema_section += f"  EMA 9: {format_value(last['EMA_9'])}\n"
            if 'EMA_21' in last.index:
                ema_section += f"  EMA 21: {format_value(last['EMA_21'])}\n"
            if 'EMA_50' in last.index:
                ema_section += f"  EMA 50: {format_value(last['EMA_50'])}\n"
            if 'EMA_200' in last.index:
                ema_section += f"  EMA 200: {format_value(last['EMA_200'])}\n"
            message += ema_section + "\n"
            
            # Hull MA
            hma_section = "Hull Moving Average:\n"
            if 'HMA_9' in last.index:
                hma_section += f"  HMA 9: {format_value(last['HMA_9'])}\n"
            if 'HMA_14' in last.index:
                hma_section += f"  HMA 14: {format_value(last['HMA_14'])}\n"
            if 'HMA_21' in last.index:
                hma_section += f"  HMA 21: {format_value(last['HMA_21'])}\n"
            if hma_section != "Hull Moving Average:\n":
                message += hma_section + "\n"
            
            # Ichimoku
            if 'ICHIMOKU_CONVERSION' in last.index:
                message += (
                    f"Ichimoku Cloud:\n"
                    f"  Conversion Line (9): {format_value(last['ICHIMOKU_CONVERSION'])}\n"
                    f"  Base Line (26): {format_value(last['ICHIMOKU_BASE'])}\n"
                    f"  Leading Span A: {format_value(last['ICHIMOKU_SPAN_A'])}\n"
                    f"  Leading Span B: {format_value(last['ICHIMOKU_SPAN_B'])}\n\n"
                )
            
            # SuperTrend
            st_section = "SuperTrend:\n"
            if 'SUPERTREND' in last.index:
                st_section += f"  Value: {format_value(last['SUPERTREND'])}\n"
            if 'SUPERTREND_7' in last.index:
                st_section += f"  Value(7): {format_value(last['SUPERTREND_7'])}\n"
            if 'SUPERTREND_10' in last.index:
                st_section += f"  Value(10): {format_value(last['SUPERTREND_10'])}\n"
            if 'SUPERTREND_14' in last.index:
                st_section += f"  Value(14): {format_value(last['SUPERTREND_14'])}\n"
            if st_section != "SuperTrend:\n":
                message += st_section + "\n"
            
            # Parabolic SAR
            if 'PSAR' in last.index:
                message += f"Parabolic SAR: {format_value(last['PSAR'])}\n\n"
            
            # 3️⃣ Momentum Strength
            message += f"3️⃣ Momentum Strength\n\n"
            
            # MACD
            if 'MACD' in last.index:
                message += (
                    f"MACD (12,26,9):\n"
                    f"  MACD: {format_value(last['MACD'])}\n"
                    f"  Signal: {format_value(last['MACD_SIGNAL'])}\n"
                    f"  Histogram: {format_value(last['MACD_HIST'])}\n\n"
                )
            
            # RSI
            if 'RSI' in last.index:
                message += f"RSI (14): {format_value(last['RSI'])}\n\n"
            
            # Stochastic
            if 'STOCH_K' in last.index:
                message += f"Stochastic (14,3,3): %K={format_value(last['STOCH_K'])} %D={format_value(last['STOCH_D'])}\n\n"
            
            # KDJ
            if 'KDJ_K' in last.index:
                message += f"KDJ (9,3,3): K={format_value(last['KDJ_K'])} D={format_value(last['KDJ_D'])}\n\n"
            
            # Williams %R
            if 'WILLIAMS' in last.index:
                message += f"Williams %R (25): {format_value(last['WILLIAMS'])}\n\n"
            
            # CCI
            if 'CCI' in last.index:
                message += f"CCI (14): {format_value(last['CCI'])}\n\n"
            
            # ROC
            if 'ROC' in last.index:
                message += f"ROC (14): {format_value(last['ROC'])}%\n\n"
            
            # Ultimate Oscillator
            if 'UO' in last.index:
                message += f"Ultimate Oscillator (7,14,28): {format_value(last['UO'])}\n\n"
            
            # ADX
            if 'ADX' in last.index:
                message += (
                    f"ADX (14): {format_value(last['ADX'])}\n"
                    f"  +DI: {format_value(last['PLUS_DI'])}\n"
                    f"  -DI: {format_value(last['MINUS_DI'])}\n\n"
                )
            
            # 4️⃣ Volume & Money Flow
            message += f"4️⃣ Volume & Money Flow\n\n"
            
            if 'OBV' in last.index:
                message += f"OBV: {format_value(last['OBV'], 0)}\n\n"
            
            if 'MFI' in last.index:
                message += f"MFI (14): {format_value(last['MFI'])}\n\n"
            
            if 'AROON_UP' in last.index:
                message += f"Aroon (14): Up={format_value(last['AROON_UP'])} Down={format_value(last['AROON_DOWN'])}\n\n"
            
            if 'VWAP' in last.index:
                message += f"VWAP: {format_value(last['VWAP'])}\n\n"
            
            # 5️⃣ Volatility & Range
            message += f"5️⃣ Volatility & Range\n\n"
            
            if 'BB_UPPER' in last.index:
                message += (
                    f"Bollinger Bands (20,2):\n"
                    f"  Upper: {format_value(last['BB_UPPER'])}\n"
                    f"  Middle: {format_value(last['BB_MIDDLE'])}\n"
                    f"  Lower: {format_value(last['BB_LOWER'])}\n\n"
                )
            
            if 'ATR' in last.index:
                message += f"ATR (14): {format_value(last['ATR'])}\n\n"
            
            if 'HA_CLOSE' in last.index:
                message += f"Heikin Ashi Close: {format_value(last['HA_CLOSE'])}\n\n"
            
            if 'DC_UPPER' in last.index:
                message += (
                    f"Donchian Channel (20):\n"
                    f"  Upper: {format_value(last['DC_UPPER'])}\n"
                    f"  Middle: {format_value(last['DC_MIDDLE'])}\n"
                    f"  Lower: {format_value(last['DC_LOWER'])}\n\n"
                )
            
            # 6️⃣ Market Sentiment (NEW)
            message += (
                f"6️⃣ Market Sentiment\n\n"
                f"News Sentiment:\n"
                f"  Positive: {sentiment.get('positive', 0)}%\n"
                f"  Negative: {sentiment.get('negative', 0)}%\n"
                f"  Neutral: {sentiment.get('neutral', 0)}%\n"
                f"  Overall: {sentiment.get('overall', 'Neutral')}\n"
                f"  Articles: {sentiment.get('article_count', 0)}\n\n"
            )
            
            # Final Signal Summary (just text)
            message += f"📍 Final Signal Summary"
            
            # Send message
            if len(message) > 4096:
                parts = [message[i:i+4096] for i in range(0, len(message), 4096)]
                for part in parts:
                    await update.message.reply_text(part)
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
        f"Your PSX Bot is working!\n"
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

# Add all stock commands
for stock in stocks + [gold]:
    for interval_key in interval_map.keys():
        cmd_name = f"{stock['symbol'].lower()}_{interval_key}"
        telegram_app.add_handler(
            CommandHandler(
                cmd_name, 
                create_stock_command(stock, interval_key)
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
# Flask App for Render
# -------------------------
flask_app = Flask(__name__)

@flask_app.route("/")
def home():
    return "PSX Bot is Running!"

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
