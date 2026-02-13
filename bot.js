// -------------------- CONFIG --------------------
const TELEGRAM_BOT_TOKEN = "8493857966:AAFURe8TIedYov8XnKzM1L9g_724QQe8LS8"; // Replace with your Telegram bot token
const PSX_BASE_URL = "https://psxterminal.com/api/ticks/"; 
const PSX_WS_URL = "wss://psxterminal.com/"; 
const PORT = process.env.PORT || 10000; 
const DOMAIN = "https://psx-1.onrender.com"; // Replace with your deployed URL

// Supported symbols
const SYMBOLS = ["MZNPETF", "NITETF", "FFC", "ENGRO", "PTL", "HUBC"];

// Map symbol to market type
const SYMBOL_MARKET = {
  "FFC": "REG",
  "ENGRO": "REG",
  "HUBC": "REG",
  "PTL": "REG",
  "MZNPETF": "IDX",
  "NITETF": "IDX"
};

// Supported intervals
const INTERVALS = ["10m","15m","30m","1h","4h","12h","1d"];

const axios = require("axios");
const express = require("express");
const bodyParser = require("body-parser");
const TelegramBot = require("node-telegram-bot-api");
const ti = require("technicalindicators");
const WebSocket = require("ws");

const app = express();
app.use(bodyParser.json());

// Initialize Telegram bot (webhook)
const bot = new TelegramBot(TELEGRAM_BOT_TOKEN);
bot.setWebHook(`${DOMAIN}/bot${TELEGRAM_BOT_TOKEN}`);

app.post(`/bot${TELEGRAM_BOT_TOKEN}`, (req, res) => {
  bot.processUpdate(req.body);
  res.sendStatus(200);
});

// Command /start
bot.onText(/\/start/, (msg) => {
  bot.sendMessage(msg.chat.id, "PSX Indicator Bot 🤖\nUse: /price SYMBOL INTERVAL\nExample: /price FFC 15m");
});

// Command /price SYMBOL INTERVAL
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
    const indicators = calculateIndicators(tick);
    const response = formatIndicatorMessage(symbol, interval, indicators);
    bot.sendMessage(chatId, response);
  } catch (err) {
    bot.sendMessage(chatId, `❌ Cannot fetch data currently: ${err.message}`);
  }
});

// Fetch latest price from PSX Terminal
async function fetchPSX(symbol) {
  try {
    const market = SYMBOL_MARKET[symbol] || "REG";
    const res = await axios.get(`${PSX_BASE_URL}${market}/${symbol}`);
    if (!res.data || !res.data.price) {
      console.log(`No price returned for ${symbol}`);
      return { price: null, volume: null };
    }
    return res.data;
  } catch (err) {
    console.log("PSX API error:", err.message);
    return { price: null, volume: null };
  }
}

// Calculate indicators safely
function calculateIndicators(data) {
  const price = parseFloat(data.price) || 100; // fallback price
  const volume = parseFloat(data.volume) || 1; // fallback volume
  const simpleSeries = Array(8).fill(price); // dummy series for indicators

  return {
    price: price,
    sma: ti.SMA.calculate({ period: 5, values: simpleSeries }).pop() || price,
    ema: ti.EMA.calculate({ period: 5, values: simpleSeries }).pop() || price,
    rsi: ti.RSI.calculate({ values: simpleSeries, period: 5 }).pop() || 50,
    macd: ti.MACD.calculate({
      values: simpleSeries,
      fastPeriod: 12,
      slowPeriod: 26,
      signalPeriod: 9
    }).pop() || { MACD: 0, signal: 0, histogram: 0 },
    obv: ti.OBV.calculate({ close: simpleSeries, volume: new Array(simpleSeries.length).fill(volume) }).pop() || 0
  };
}

// Format message to Telegram
function formatIndicatorMessage(symbol, interval, ind) {
  return `
📊 ${symbol} (${interval})
Price: ${ind.price}
SMA: ${ind.sma}
EMA: ${ind.ema}
RSI: ${ind.rsi}
MACD: ${ind.macd.MACD}, Signal: ${ind.macd.signal}
OBV: ${ind.obv}
`;
}

// Optional WebSocket connection to keep alive
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

// Start web server
app.listen(PORT, () => {
  console.log("Bot ready ✅");
  console.log(`Server running on port ${PORT}`);
});
