// -------------------- CONFIG --------------------
const TELEGRAM_BOT_TOKEN = "8493857966:AAFURe8TIedYov8XnKzM1L9g_724QQe8LS8"; // Your token
const PSX_BASE_URL = "https://psxterminal.com/api/ticks/";
const PSX_WS_URL = "wss://psxterminal.com/";
const PORT = process.env.PORT || 10000;
const DOMAIN = "https://psx-1.onrender.com"; // Your deployed URL

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
const BUFFER_SIZE = 50;

// -------------------- MODULES --------------------
const axios = require("axios");
const express = require("express");
const TelegramBot = require("node-telegram-bot-api");
const ti = require("technicalindicators");
const WebSocket = require("ws");

// -------------------- APP & BOT --------------------
const app = express();
const bot = new TelegramBot(TELEGRAM_BOT_TOKEN, { polling: true });

// -------------------- PRICE BUFFER --------------------
const priceBuffer = {};
SYMBOLS.forEach(sym => {
  priceBuffer[sym] = {};
  INTERVALS.forEach(intv => {
    priceBuffer[sym][intv] = [];
  });
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
    return bot.sendMessage(chatId, `❌ Invalid symbol or interval.\nSymbols: ${SYMBOLS.join(", ")}\nIntervals: ${INTERVALS.join(", ")}`);
  }

  bot.sendMessage(chatId, `Fetching ${symbol} (${interval})...`);

  try {
    const tick = await fetchPSX(symbol);
    if (!tick.price) throw new Error("No price available");
    const indicators = calculateIndicators(symbol, interval, tick);
    const response = formatIndicatorMessage(symbol, interval, indicators);
    bot.sendMessage(chatId, response);
  } catch (err) {
    bot.sendMessage(chatId, `❌ Cannot fetch data currently: ${err.message}`);
  }
});

// -------------------- FETCH PSX --------------------
async function fetchPSX(symbol) {
  try {
    const market = SYMBOL_MARKET[symbol] || "REG";
    const res = await axios.get(`${PSX_BASE_URL}${market}/${symbol}`);
    const data = res.data.data;
    if (!data || !data.price) return { price: null, volume: null };
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

  const macdRes = ti.MACD.calculate({
    values: series,
    fastPeriod: 12,
    slowPeriod: 26,
    signalPeriod: 9,
    SimpleMAOscillator: false,
    SimpleMASignal: false
  }).pop() || { MACD: 0, signal: 0, histogram: 0 };

  return {
    price: price.toFixed(2),
    sma: ti.SMA.calculate({ period: 5, values: series }).pop()?.toFixed(2) || price.toFixed(2),
    ema: ti.EMA.calculate({ period: 5, values: series }).pop()?.toFixed(2) || price.toFixed(2),
    rsi: ti.RSI.calculate({ values: series, period: 5 }).pop()?.toFixed(2) || "50",
    macd: macdRes,
    obv: ti.OBV.calculate({ close: series, volume: volumeSeries }).pop() || 0
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

// -------------------- OPTIONAL WEBSOCKET --------------------
function initWebSocket() {
  const ws = new WebSocket(PSX_WS_URL);
  ws.on("open", () => console.log("WebSocket connected"));
  ws.on("error", e => console.log("WebSocket error:", e.message));
  ws.on("close", () => {
    console.log("WebSocket disconnected, reconnecting in 5s...");
    setTimeout(initWebSocket, 5000);
  });
}
initWebSocket();

// -------------------- START SERVER --------------------
app.listen(PORT, () => {
  console.log("Bot ready ✅");
  console.log(`Server running on port ${PORT}`);
});
