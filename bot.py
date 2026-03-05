from telegram.ext import ApplicationBuilder,CommandHandler
from telegram import Update
from telegram.ext import ContextTypes

from tvDatafeed import TvDatafeed, Interval

import indicators
import pandas as pd
import time

BOT_TOKEN="8476710135:AAFx1X-G_7HE_OsSGMu6GgVk8TtQvHkWAQc"

tv=TvDatafeed()

interval_map={
"15m":Interval.in_15_minute,
"30m":Interval.in_30_minute,
"1h":Interval.in_1_hour,
"2h":Interval.in_2_hour,
"4h":Interval.in_4_hour,
"1d":Interval.in_daily,
"1w":Interval.in_weekly
}

stocks={
"ffc":"FFC",
"engroh":"ENGROH",
"ogdc":"OGDC",
"hubco":"HUBC",
"ppl":"PPL",
"nbp":"NBP",
"ubl":"UBL",
"meznpetf":"MEZNPETF",
"nbpgetf":"NBPGETF",
"kel":"KEL",
"sys":"SYS",
"luck":"LUCK",
"pso":"PSO",
"gold":"XAUUSD"
}

# --------------------------------
# START COMMAND
# --------------------------------

async def start(update:Update,context:ContextTypes.DEFAULT_TYPE):

    start_time=time.time()

    msg="Checking..."

    end=time.time()

    ping=round((end-start_time)*1000)

    text=f"""
🔥 PSX Stock Indicator Bot
━━━━━━━━━━━━━━━━━━━━━

Your Bot is working! ✅
Ping response time: {ping} ms

Available Stocks:

FFC
ENGROH
OGDC
HUBC
PPL
NBP
UBL
MEZNPETF
NBPGETF
KEL
SYS
LUCK
PSO
GOLD

Timeframes

15m
30m
1h
2h
4h
1d
1w

Example Commands

/ffc_15m
/ogdc_1h
/hubco_4h
/engroh_1d

⏳ First request may take 10-15 seconds
"""

    await update.message.reply_text(text)

# --------------------------------
# STOCK COMMAND
# --------------------------------

def stock_command(symbol,tf):

    async def command(update:Update,context:ContextTypes.DEFAULT_TYPE):

        df=tv.get_hist(symbol=symbol,exchange="PSX",interval=interval_map[tf],n_bars=200)

        close=df["close"].iloc[-1]

        sma10=indicators.SMA(df["close"],10).iloc[-1]
        sma20=indicators.SMA(df["close"],20).iloc[-1]
        sma50=indicators.SMA(df["close"],50).iloc[-1]
        sma200=indicators.SMA(df["close"],200).iloc[-1]

        ema9=indicators.EMA(df["close"],9).iloc[-1]
        ema21=indicators.EMA(df["close"],21).iloc[-1]
        ema50=indicators.EMA(df["close"],50).iloc[-1]
        ema200=indicators.EMA(df["close"],200).iloc[-1]

        rsi14=indicators.RSI(df["close"],14).iloc[-1]

        macd,signal,hist=indicators.MACD(df["close"])

        atr=indicators.ATR(df).iloc[-1]

        upper,mid,lower=indicators.bollinger(df["close"])

        obv=indicators.OBV(df).iloc[-1]

        text=f"""
📊 {symbol} - PSX ({tf})

1️⃣ Market Overview

💰 Price: {close}
🔓 Open Price: {df['open'].iloc[-1]}
🔓 Close Price: {close}
📈 24h High: {df['high'].iloc[-1]}
📉 24h Low: {df['low'].iloc[-1]}
🧮 Volume: {df['volume'].iloc[-1]}

2️⃣ Trend Direction

SMA10 {sma10}
SMA20 {sma20}
SMA50 {sma50}
SMA200 {sma200}

EMA9 {ema9}
EMA21 {ema21}
EMA50 {ema50}
EMA200 {ema200}

3️⃣ Momentum

RSI14 {rsi14}

MACD {macd.iloc[-1]}
Signal {signal.iloc[-1]}
Histogram {hist.iloc[-1]}

4️⃣ Volume

OBV {obv}

5️⃣ Volatility

ATR {atr}

Bollinger

Upper {upper.iloc[-1]}
Middle {mid.iloc[-1]}
Lower {lower.iloc[-1]}
"""

        await update.message.reply_text(text)

    return command

# --------------------------------
# BOT INIT
# --------------------------------

app=ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start",start))

for s in stocks:

    for tf in interval_map:

        cmd=f"{s}_{tf}"

        app.add_handler(CommandHandler(cmd,stock_command(stocks[s],tf)))

print("BOT RUNNING")

app.run_polling()
