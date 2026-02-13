// -------------------- CONFIG --------------------
const TELEGRAM_BOT_TOKEN = "8493857966:AAEbHaLyxWy_sAs56Mgd0ZBpn64WY1SKF64"; // <- replace with your token
const PSX_BASE_URL = "https://psxterminal.com/api/ticks/"; 
const PSX_WS_URL = "wss://psxterminal.com/";
const PORT = process.env.PORT || 10000; 
const DOMAIN = "https://psx-1.onrender.com"; // replace with your Render domain

// Symbols and intervals
const SYMBOLS = ["MEZANETF", "NATBANKETF", "FFC", "ENGRO", "PANTHERTYRE", "HUBC"];
const INTERVALS = ["10m","15m","30m","1h","4h","12h","1d"];
// ------------------------------------------------

const axios = require("axios");
const express = require("express");
const bodyParser = require("body-parser");
const TelegramBot = require("node-telegram-bot-api");
const { SMA, EMA, MACD, RSI, OBV } = require("technicalindicators");
const WebSocket = require("ws");

const app = express();
app.use(bodyParser.json());

// Initialize Telegram bot without polling
const bot = new TelegramBot(TELEGRAM_BOT_TOKEN);
bot.setWebHook(`${DOMAIN}/bot${TELEGRAM_BOT_TOKEN}`);

// Webhook endpoint
app.post(`/bot${TELEGRAM_BOT_TOKEN}`, (req, res) => {
  bot.processUpdate(req.body);
  res.sendStatus(200);
});

bot.onText(/\/start/, (msg) => {
  bot.sendMessage(msg.chat.id, "PSX Indicator Bot ✅\nSend /price SYMBOL INTERVAL\nExample: /price ENGRO 15m");
});

bot.onText(/\/price (.+) (.+)/, async (msg, match) => {
  const chatId = msg.chat.id;
  const symbol = match[1].toUpperCase();
  const interval = match[2].toLowerCase();

  if (!SYMBOLS.includes(symbol) || !INTERVALS.includes(interval)) {
    bot.sendMessage(chatId, `Invalid symbol or interval.\nSymbols: ${SYMBOLS.join(", ")}\nIntervals: ${INTERVALS.join(", ")}`);
    return;
  }

  bot.sendMessage(chatId, `Fetching ${symbol} data for ${interval}...`);

  try {
    const data = await fetchPSXData(symbol);
    const indicators = calculateIndicators(data);
    const message = formatIndicators(symbol, interval, indicators);
    bot.sendMessage(chatId, message);
  } catch (err) {
    bot.sendMessage(chatId, `Error fetching data: ${err.message}`);
  }
});

// -------------------- PSX DATA --------------------
async function fetchPSXData(symbol) {
  try {
    const res = await axios.get(`${PSX_BASE_URL}REG/${symbol}`); // REG market type
    if (!res.data || !res.data.price) throw new Error("No price returned");
    return res.data; // customize according to PSX API response
  } catch (err) {
    console.log("PSX API error:", err.message, "Retrying in 5s...");
    await new Promise(r => setTimeout(r, 5000));
    return fetchPSXData(symbol);
  }
}

// -------------------- INDICATORS --------------------
function calculateIndicators(data) {
  const close = [data.price]; // for demo, normally you would collect historical prices
  return {
    sma: SMA.calculate({ period: 14, values: close }).pop() || data.price,
    ema: EMA.calculate({ period: 14, values: close }).pop() || data.price,
    rsi: RSI.calculate({ period: 14, values: close }).pop() || 50,
    macd: MACD.calculate({
      values: close,
      fastPeriod: 12,
      slowPeriod: 26,
      signalPeriod: 9,
      SimpleMAOscillator: false,
      SimpleMASignal: false
    }).pop() || { MACD: 0, signal: 0, histogram: 0 },
    obv: OBV.calculate({ close, volume: [data.volume || 1] }).pop() || 0
  };
}

// -------------------- FORMAT --------------------
function formatIndicators(symbol, interval, ind) {
  return `
📊 ${symbol} - ${interval.toUpperCase()}
Price: ${ind.sma.toFixed(2)}
SMA: ${ind.sma.toFixed(2)}
EMA: ${ind.ema.toFixed(2)}
RSI: ${ind.rsi.toFixed(2)}
MACD: ${ind.macd.MACD.toFixed(2)}, Signal: ${ind.macd.signal.toFixed(2)}, Hist: ${ind.macd.histogram.toFixed(2)}
OBV: ${ind.obv.toFixed(0)}
`;
}

// -------------------- WEBSOCKET --------------------
function connectWS() {
  const ws = new WebSocket(PSX_WS_URL);
  ws.on("open", () => console.log("WebSocket connected"));
  ws.on("close", () => { 
    console.log("WebSocket disconnected, reconnecting in 5s...");
    setTimeout(connectWS, 5000);
  });
  ws.on("error", err => console.log("WebSocket error:", err.message));
}
connectWS();

// -------------------- START SERVER
