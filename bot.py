"""
PSX Stock Indicator Telegram Bot
FIXED VERSION - Better TvDatafeed initialization and error handling
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
    print("✅ tvDatafeed imported successfully")
except Exception as e:
    print(f"❌ Failed to import tvDatafeed: {e}")
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
    raise ValueError("❌ BOT_TOKEN environment variable not set")

# -------------------------
# TradingView Initialization - FIXED VERSION
# -------------------------
def init_tvdatafeed():
    """Initialize TvDatafeed with proper handling for headless environment"""
    
    # Method 1: Try with auto_login=False first (best for headless)
    try:
        tv = TvDatafeed(auto_login=False)
        logger.info("✅ TvDatafeed initialized with auto_login=False")
        return tv
    except Exception as e:
        logger.warning(f"Method 1 failed: {e}")
    
    # Method 2: Simple initialization (might prompt for input)
    try:
        tv = TvDatafeed()
        logger.info("✅ TvDatafeed initialized successfully")
        return tv
    except Exception as e:
        logger.warning(f"Method 2 failed: {e}")
    
    # Method 3: Explicit None credentials (fallback)
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
    # Test the connection with a simple request
    test_data = tv.get_hist(symbol="FFC", exchange="PSX", interval=Interval.in_daily, n_bars=1)
    if test_data is not None and not test_data.empty:
        logger.info("✅ TvDatafeed connection test successful")
    else:
        logger.warning("⚠️ TvDatafeed connection test returned no data")
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

# PSX Stocks - Updated with TradingView symbols
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
]

# Gold symbol
gold = {"symbol": "GOLD", "name": "Gold", "tv_symbol": "TVC:GOLD"}

# Combine all symbols
all_symbols = stocks + [gold]

# [Rest of your indicator functions and command handlers remain the same...]
# (Keep all the calculate_all_indicators, format_value, create_stock_command functions as they are)

# -------------------------
# Start/Ping Commands
# -------------------------
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command with comprehensive help"""
    
    # Calculate ping response time
    start_time = time.time()
    msg = await update.message.reply_text("⏳ Checking bot status...")
    end_time = time.time()
    ping_time = round((end_time - start_time) * 1000, 2)
    
    # Create stocks table
    stocks_table = "| Company | TradingView Symbol |\n"
    stocks_table += "| ------- | ------------------ |\n"
    for stock in stocks:
        stocks_table += f"| {stock['name']} | {stock['tv_symbol']} |\n"
    stocks_table += f"| {gold['name']} | {gold['tv_symbol']} |\n"
    
    help_text = (
        f"Your Bot is working! ✅\n"
        f"Ping response time: {ping_time}ms\n\n"
        
        f"🔥 *PSX Stock Indicator Bot*\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        f"*TEST COMMANDS (Verify bot works):*\n"
        f"/start - Check if bot is responding and check response time\n\n"
        
        f"*Available Stocks:*\n"
        f"```\n{stocks_table}```\n\n"
        
        f"*Timeframes:* 15m, 30m, 1h, 2h, 4h, 1d, 1w\n\n"
        
        f"*Example Commands:*\n"
        f"`/ffc_15m` - FFC 15min\n"
        f"`/ogdc_1h` - OGDC 1hour\n"
        f"`/hubc_4h` - HUBC 4hour\n"
        f"`/engroh_1d` - ENGROH Daily\n"
        f"`/gold_1d` - Gold Daily\n\n"
        
        f"*Indicators:*\n"
        f"All Major Indicators (50+ indicators including RSI, MACD, Bollinger Bands, Ichimoku, Fibonacci, etc.)\n\n"
        
        f"⏳ *Note:* First request may take 10-15 seconds due to data fetching.\n"
        f"📊 Each command returns comprehensive technical analysis with 50+ indicators."
    )
    
    await msg.edit_text(help_text, parse_mode='Markdown')

async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Simple ping command"""
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

# Add start and ping commands
telegram_app.add_handler(CommandHandler("start", start_command))
telegram_app.add_handler(CommandHandler("ping", ping_command))
logger.info(f"✅ Added commands: /start, /ping")

# Add all stock commands
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
        logger.info(f"✅ Added command: /{cmd_name}")

# -------------------------
# Error Handler - FIXED
# -------------------------
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors gracefully"""
    logger.error(f"Error: {context.error}", exc_info=True)
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "⚠️ An error occurred. Please try again.\n"
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
    return "✅ PSX Indicator Bot is Running!"

@flask_app.route("/health")
def health():
    return {"status": "healthy", "bot": "running"}, 200

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
        logger.info(f"✅ Flask server started on port {os.environ.get('PORT', 10000)}")
        
        # Small delay
        time.sleep(2)
        
        # Start Telegram bot
        logger.info("🚀 Starting Telegram bot...")
        telegram_app.run_polling(drop_pending_updates=True)
        
    except KeyboardInterrupt:
        logger.info("👋 Bot stopped")
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}", exc_info=True)
        raise
