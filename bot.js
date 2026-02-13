const TelegramBot = require("node-telegram-bot-api");
const axios = require("axios");
const ti = require("technicalindicators");
const express = require("express");

// ================= CONFIG =================
const TOKEN = process.env.BOT_TOKEN || "YOUR_TELEGRAM_BOT_TOKEN";
const PORT = process.env.PORT || 3000;
const BASE_URL = "https://psxterminal.com/api/ticks/REG/";

// ================= EXPRESS SERVER =================
const app = express();
app.use(express.json());
app.get("/", (req, res) => res.send("PSX Telegram Bot Running"));
app.listen(PORT, () => console.log("Server running on port " + PORT));

// ================= TELEGRAM BOT =================
const bot = new TelegramBot(TOKEN, { polling: true });

// ================= SYMBOLS =================
const SYMBOLS = {
  MZNPETF: "Meezan ETF",
  NITETF: "National ETF",
  FFC: "Fauji Fertilizer",
  ENGRO: "Engro Corp",
  PTL: "Panther Tyre",
  HUBC: "Hubco"
};

// ================= TIMEFRAMES =================
const TIMEFRAMES = {
  "10m": 600,
  "15m": 900,
  "30m": 1800,
  "1h": 3600,
  "4h": 14400,
  "12h": 43200,
  "1d": 86400
};

// ================= STORAGE =================
const priceStore = {};
Object.keys(SYMBOLS).forEach(s => priceStore[s] = []);

// ================= FETCH PRICE =================
async function fetchPrice(symbol) {
  try {
    const res = await axios.get(BASE_URL + symbol);
    return {
      price: parseFloat(res.data.price || 0),
      volume: parseFloat(res.data.volume || 1),
      time: Math.floor(Date.now() / 1000)
    };
  } catch (err) {
    console.log("PSX API error:", err.message);
    return null;
  }
}

// ================= INITIAL DATA LOAD =================
async function initialLoad() {
  console.log("Loading initial data...");
  for (let i = 0; i < 40; i++) {
    for (const symbol of Object.keys(SYMBOLS)) {
      const tick = await fetchPrice(symbol);
      if (tick) priceStore[symbol].push(tick);
    }
    await new Promise(r => setTimeout(r, 1500));
  }
  console.log("Initial data ready");
}
initialLoad();

// ================= LIVE DATA COLLECTION =================
setInterval(async () => {
  for (const symbol of Object.keys(SYMBOLS)) {
    const tick = await fetchPrice(symbol);
    if (!tick) continue;
    priceStore[symbol].push(tick);
    if (priceStore[symbol].length > 2000)
      priceStore[symbol] = priceStore[symbol].slice(-2000);
  }
}, 10000); // every 10 sec

// ================= BUILD CANDLES =================
function buildCandles(data, timeframe) {
  if (!data.length) return null;
  const buckets = {};
  data.forEach(t => {
    const key = Math.floor(t.time / timeframe) * timeframe;
    if (!buckets[key]) {
      buckets[key] = { open: t.price, high: t.price, low: t.price, close: t.price, volume: 0 };
    }
    buckets[key].high = Math.max(buckets[key].high, t.price);
    buckets[key].low = Math.min(buckets[key].low, t.price);
    buckets[key].close = t.price;
    buckets[key].volume += t.volume;
  });
  return Object.values(buckets);
}

// ================= INDICATORS =================
function calculateIndicators(candles) {
  let closes = candles.map(c => c.close);
  let volumes = candles.map(c => c.volume);

  // fake data if small candles to prevent waiting
  if (closes.length < 30) {
    const last = closes.at(-1) || 100;
    while (closes.length < 30) {
      closes.unshift(last);
      volumes.unshift(1);
    }
  }

  try {
    return {
      price: closes.at(-1).toFixed(2),
      rsi: ti.RSI.calculate({ values: closes, period: 14 }).at(-1)?.toFixed(2) || "N/A",
      ema: ti.EMA.calculate({ values: closes, period: 20 }).at(-1)?.toFixed(2) || "N/A",
      sma: ti.SMA.calculate({ values: closes, period: 20 }).at(-1)?.toFixed(2) || "N/A",
      macd: ti.MACD.calculate({ values: closes, fastPeriod: 12, slowPeriod: 26, signalPeriod: 9 }).at(-1)?.MACD?.toFixed(2) || "N/A",
      obv: ti.OBV.calculate({ close: closes, volume: volumes }).at(-1)?.toFixed(2) || "N/A"
    };
  } catch {
    return null;
  }
}

// ================= TELEGRAM COMMAND =================
bot.onText(/\/analyze (.+) (.+)/, async (msg, match) => {
  const chatId = msg.chat.id;
  const symbol = match[1].toUpperCase();
  const tf = match[2];

  if (!SYMBOLS[symbol]) return bot.sendMessage(chatId, "❌ Symbol not supported");
  if (!TIMEFRAMES[tf]) return bot.sendMessage(chatId, "❌ Invalid timeframe");

  const candles = buildCandles(priceStore[symbol], TIMEFRAMES[tf]);
  if (!candles) return bot.sendMessage(chatId, "Loading data... try again shortly");

  const result = calculateIndicators(candles);
  if (!result) return bot.sendMessage(chatId, "Indicator calculation error");

  const signal = result.rsi > 70 ? "Overbought" : result.rsi < 30 ? "Oversold" : "Neutral";

  bot.sendMessage(chatId,
`📊 ${SYMBOLS[symbol]} (${symbol})
⏱ ${tf}

💰 Price: ${result.price}

RSI: ${result.rsi}
EMA20: ${result.ema}
SMA20: ${result.sma}
MACD: ${result.macd}
OBV: ${result.obv}

Signal: ${signal}`);
});

// ================= START COMMAND =================
bot.onText(/\/start/, msg => {
  bot.sendMessage(msg.chat.id,
`PSX Indicator Bot Ready

Usage:
/analyze HUBC 15m
/analyze ENGRO 1h
/analyze MZNPETF 4h

Supported Symbols:
MZNPETF, NITETF, FFC, ENGRO, PTL, HUBC`);
});

console.log("Bot ready");
