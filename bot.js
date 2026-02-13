// -------------------- CONFIG --------------------
const TELEGRAM_BOT_TOKEN = "8493857966:AAFURe8TIedYov8XnKzM1L9g_724QQe8LS8"; // Replace with your token
const PSX_BASE_URL = "https://psxterminal.com/api/ticks/";
const PORT = process.env.PORT || 10000;
const DOMAIN = "https://psx-1.onrender.com"; // Replace with your deployed URL

const SYMBOLS = ["MZNPETF", "NITETF", "FFC", "ENGRO", "PTL", "HUBC"];
const SYMBOL_MARKET = {
  "FFC": "REG",
  "ENGRO": "REG",
  "HUBC": "REG",
  "PTL": "REG",
  "MZNPETF": "IDX",
  "NITETF": "IDX"
};
const INTERVALS = ["10m", "15m", "30m", "1h", "4h", "12h", "1d"];
const BUFFER_SIZE = 50; // store last 50 prices per interval

// -------------------- MODULES --------------------
const axios = require("axios");
const express = require("express");
const TelegramBot = require("node-telegram-bot-api");
const ti = require("technicalindicators");

// -------------------- APP & BOT --------------------
const app = express();
app.use(express.json());

const bot = new TelegramBot(TELEGRAM_BOT_TOKEN, { polling: true });

// -------------------- PRICE BUFFER --------------------
const priceBuffer = {}; // priceBuffer[symbol][interval] = [prices]
SYMBOLS.forEach(sym => {
  priceBuffer[sym] = {};
  INTERVALS.forEach(intv => priceBuffer[sym][intv] = []);
});

// -------------------- TELEGRAM COMMANDS --------------------
bot.onText(/\/start/, (msg) => {
  bot.sendMessage(msg.chat.id, `PSX Indicator Bot 🤖\nUse: /price SYMBOL INTERVAL\nExample: /price FFC 15m`);
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
    const tick = await fetchPSX(symbol);
    if (!tick.price) throw new Error("No price available");

    const indicators = calculateIndicators(symbol, interval, tick);
    const response = formatIndicatorMessage(symbol, interval, indicators);
    bot.sendMessage(chatId, response);
  } catch (err) {
    bot.sendMessage(chatId, `❌ Cannot fetch data: ${err.message}`);
  }
});

// -------------------- FETCH PSX --------------------
async function fetchPSX(symbol) {
  try {
    const market = SYMBOL_MARKET[symbol] || "REG";
    const res = await axios.get(`${PSX_BASE_URL}${market}/${symbol}`);
    const data = res.data?.data;

    if (!data || !data.price) throw new Error("No price available");

    return { price: parseFloat(data.price), volume: parseFloat(data.volume || 1) };
  } catch (err) {
    console.log(`PSX API error (${symbol}):`, err.message);
    return { price: null, volume: null };
  }
}

// -------------------- CALCULATE INDICATORS --------------------
function calculateIndicators(symbol, interval, tick) {
  const buf = priceBuffer[symbol][interval];
  const price = tick.price;

  buf.push(price);
  if (buf.length > BUFFER_SIZE) buf.shift();

  const series = buf.slice();
  const volumeSeries = new Array(series.length).fill(tick.volume || 1);

  const sma = ti.SMA.calculate({ period: 5, values: series }).pop() || price;
  const ema = ti.EMA.calculate({ period: 5, values: series }).pop() || price;
  const rsi = ti.RSI.calculate({ values: series, period: 5 }).pop() || 50;
  const macdRes = ti.MACD.calculate({ values: series, fastPeriod: 12, slowPeriod: 26, signalPeriod: 9 }).pop() || { MACD: 0, signal: 0 };
  const obv = ti.OBV.calculate({ close: series, volume: volumeSeries }).pop() || 0;

  return {
    price: price.toFixed(2),
    sma: sma.toFixed(2),
    ema: ema.toFixed(2),
    rsi: rsi.toFixed(2),
    macd: macdRes,
    obv: obv
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
OBV: ${ind.obv}
`;
}

// -------------------- START SERVER --------------------
app.listen(PORT, () => {
  console.log("Bot ready ✅");
  console.log(`Server running on port ${PORT}`);
});
