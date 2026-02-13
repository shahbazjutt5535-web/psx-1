const TelegramBot = require("node-telegram-bot-api");
const axios = require("axios");
const ti = require("technicalindicators");
const express = require("express");
const WebSocket = require("ws");

// ================= CONFIG =================
const TOKEN = process.env.BOT_TOKEN;
const PORT = process.env.PORT || 3000;
const BASE_URL = "https://psxterminal.com/api/ticks/REG/"; // REST fallback
const WS_URL = "wss://psxterminal.com/"; // WebSocket live

// ================= EXPRESS SERVER =================
const app = express();
app.use(express.json());
app.get("/", (req, res) => res.send("✅ PSX Telegram Bot Running"));
app.listen(PORT, () => console.log(`Server running on port ${PORT}`));

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

// ================= REST FETCH =================
async function fetchPrice(symbol) {
  try {
    const res = await axios.get(BASE_URL + symbol);
    if (!res.data?.price) throw new Error("No price returned");
    return {
      price: parseFloat(res.data.price),
      volume: parseFloat(res.data.volume || 1),
      time: Math.floor(Date.now() / 1000)
    };
  } catch (err) {
    console.log("PSX API error:", err.message);
    return null;
  }
}

// ================= WEBSOCKET =================
function initWS() {
  const ws = new WebSocket(WS_URL);
  ws.on("open", () => {
    console.log("WebSocket connected");
    Object.keys(SYMBOLS).forEach(sym => ws.send(JSON.stringify({ subscribe: sym })));
  });

  ws.on("message", data => {
    try {
      const tick = JSON.parse(data);
      if (SYMBOLS[tick.symbol]) {
        priceStore[tick.symbol].push({
          price: parseFloat(tick.price),
          volume: parseFloat(tick.volume || 1),
          time: Math.floor(Date.now() / 1000)
        });
        // Limit stored ticks
        if (priceStore[tick.symbol].length > 2000)
          priceStore[tick.symbol] = priceStore[tick.symbol].slice(-2000);
      }
    } catch {}
  });

  ws.on("close", () => {
    console.log("WebSocket disconnected, reconnecting in 5s...");
    setTimeout(initWS, 5000);
  });

  ws.on("error", () => ws.close());
}
initWS();

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
  const closes = candles.map(c => c.close);
  const volumes = candles.map(c => c.volume);

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

// ================= TELEGRAM COM
