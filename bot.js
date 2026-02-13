// -------------------- CONFIG --------------------
const TELEGRAM_BOT_TOKEN = "8493857966:AAFURe8TIedYov8XnKzM1L9g_724QQe8LS8"; // your bot token
const ALPHA_KEY = "FTU5JQAPPOGPU3LN"; // your Alpha Vantage key
const PORT = process.env.PORT || 10000;

const SYMBOLS = ["FFC", "ENGRO", "HUBC"]; // your symbols
const INTERVALS = ["15min", "30min", "60min"]; // Alpha Vantage intervals
const BUFFER_SIZE = 50;

// -------------------- MODULES --------------------
const axios = require("axios");
const express = require("express");
const TelegramBot = require("node-telegram-bot-api");
const ti = require("technicalindicators");

// -------------------- APP & BOT --------------------
const app = express();
const bot = new TelegramBot(TELEGRAM_BOT_TOKEN, { polling: true });

// -------------------- PRICE BUFFER --------------------
const priceBuffer = {};
SYMBOLS.forEach(sym => {
  priceBuffer[sym] = {};
  INTERVALS.forEach(intv => priceBuffer[sym][intv] = []);
});

// -------------------- TELEGRAM COMMANDS --------------------
bot.onText(/\/start/, (msg) => {
  bot.sendMessage(msg.chat.id, `PSX Indicator Bot 🤖\nUse: /price SYMBOL INTERVAL\nExample: /price FFC 15min`);
});

bot.onText(/\/price (.+) (.+)/, async (msg, match) => {
  const chatId = msg.chat.id;
  const symbol = match[1].toUpperCase();
  const interval = match[2].toLowerCase();

  if (!SYMBOLS.includes(symbol) || !INTERVALS.includes(interval)) {
    return bot.sendMessage(chatId, `❌ Invalid symbol or interval.\nSupported symbols: ${SYMBOLS.join(", ")}\nIntervals: ${INTERVALS.join(", ")}`);
  }

  bot.sendMessage(chatId, `Fetching ${symbol} (${interval})...`);

  try {
    const series = await fetchAlphaSeries(symbol, interval);
    const indicators = calculateIndicators(series);
    const message = formatIndicatorMessage(symbol, interval, indicators);
    bot.sendMessage(chatId, message);
  } catch (err) {
    bot.sendMessage(chatId, `❌ Cannot fetch data: ${err.message}`);
  }
});

// -------------------- FETCH ALPHA VANTAGE DATA --------------------
async function fetchAlphaSeries(symbol, interval) {
  try {
    const res = await axios.get(`https://www.alphavantage.co/query`, {
      params: {
        function: "TIME_SERIES_INTRADAY",
        symbol: symbol,
        interval: interval,
        outputsize: "compact",
        apikey: ALPHA_KEY
      }
    });

    const data = res.data[`Time Series (${interval})`];
    if (!data) throw new Error("No time series data returned");

    const prices = Object.values(data).map(d => parseFloat(d["4. close"])).reverse(); // oldest -> newest
    return prices.slice(-BUFFER_SIZE); // last BUFFER_SIZE points
  } catch (err) {
    throw new Error(err.response?.data || err.message);
  }
}

// -------------------- CALCULATE INDICATORS --------------------
function calculateIndicators(series) {
  const price = series[series.length - 1];
  return {
    price: price.toFixed(2),
    sma: ti.SMA.calculate({ period: 5, values: series }).pop()?.toFixed(2) || price,
    ema: ti.EMA.calculate({ period: 5, values: series }).pop()?.toFixed(2) || price,
    rsi: ti.RSI.calculate({ values: series, period: 5 }).pop()?.toFixed(2) || 50,
    macd: (() => {
      const macdRes = ti.MACD.calculate({ values: series, fastPeriod: 12, slowPeriod: 26, signalPeriod: 9 }).pop();
      return macdRes || { MACD: 0, signal: 0, histogram: 0 };
    })()
  };
}

// -------------------- FORMAT MESSAGE --------------------
function formatIndicatorMessage(symbol, interval, ind) {
  return `
📊 ${symbol} (${interval})
Price: ${ind.price}
SMA: ${ind.sma}
EMA: ${ind.ema}
RSI: ${ind.rsi}
MACD: ${ind.macd.MACD.toFixed(2)}, Signal: ${ind.macd.signal.toFixed(2)}
`;
}

// -------------------- START SERVER --------------------
app.listen(PORT, () => {
  console.log("Bot ready ✅");
  console.log(`Server running on port ${PORT}`);
});
