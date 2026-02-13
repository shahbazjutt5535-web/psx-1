// -------------------- CONFIG --------------------
const TELEGRAM_BOT_TOKEN = "8493857966:AAFURe8TIedYov8XnKzM1L9g_724QQe8LS8"; // Replace with your token
const PSX_BASE_URL = "https://psxterminal.com/api/ticks/";
const PSX_WS_URL = "wss://psxterminal.com/";
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
const BUFFER_SIZE = 50; // number of last prices stored

// -------------------- MODULES --------------------
const axios = require("axios");
const express = require("express");
const bodyParser = require("body-parser");
const TelegramBot = require("node-telegram-bot-api");
const ti = require("technicalindicators");
const WebSocket = require("ws");

// -------------------- APP & BOT --------------------
const app = express();
app.use(bodyParser.json());

const bot = new TelegramBot(TELEGRAM_BOT_TOKEN);
bot.setWebHook(`${DOMAIN}/bot${TELEGRAM_BOT_TOKEN}`);

// -------------------- PRICE BUFFER --------------------
const priceBuffer = {}; // priceBuffer[symbol][interval] = [prices]

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
    return bot.sendMessage(chatId, `❌ Invalid symbol or interval.\nSupported symbols: ${SYMBOLS.join(", ")}\nIntervals: ${INTERVALS.join(", ")}`);
  }

  bot.sendMessage(chatId, `Fetching ${symbol} (${interval})...`);

  try {
    const tick = await fetchPSX(symbol);
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
    const price = parseFloat(res.data.price);
    const volume = parseFloat(res.data.volume || 1);

    if (!price) throw new Error("No price returned");

    return { price, volume };
  } catch (err) {
    console.log(`PSX API error (${symbol}):`, err.message);
    return { price: null, volume: null };
  }
}

// -------------------- CALCULATE INDICATORS --------------------
function calculateIndicators(symbol, interval, tick) {
  const buf = priceBuffer[symbol][interval];

  // Add latest price to buffer
  const price = tick.price || (buf[buf.length - 1] || 100);
  buf.push(price);

  // Keep buffer size
  if (buf.length > BUFFER_SIZE) buf.shift();

  // Prepare series for indicators
  const series = buf.slice(); // copy of buffer
  const volumeSeries = new Array(series.length).fill(tick.volume || 1);

  return {
    price: price.toFixed(2),
    sma: ti.SMA.calculate({ period: 5, values: series }).pop()?.toFixed(2) || price,
    ema: ti.EMA.calculate({ period: 5, values: series }).pop()?.toFixed(2) || price,
    rsi: ti.RSI.calculate({ values: series, period: 5 }).pop()?.toFixed(2) || 50,
    macd: (() => {
      const macdRes = ti.MACD.calculate({
        values: series,
        fastPeriod: 12,
        slowPeriod: 26,
        signalPeriod: 9
      }).pop();
      return macdRes || { MACD: 0, signal: 0, histogram: 0 };
    })(),
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
  ws.on("error", (e) => console.log("WebSocket error:", e.message));
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
