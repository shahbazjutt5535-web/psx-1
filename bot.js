const TelegramBot = require("node-telegram-bot-api");
const axios = require("axios");
const ti = require("technicalindicators");
const express = require("express");

// ================= CONFIG =================
const TOKEN = "8493857966:AAGZqy8FH3Pvdw1uCs2lhakKRCrv6n_h83E";

const PORT = process.env.PORT || 3000;
const WEBHOOK_URL = "https://psx-1.onrender.com"; // https://yourapp.com

const BASE_URL = "https://psxterminal.com/api/ticks/REG/";

// ================= EXPRESS SERVER (OPEN PORT) =================
const app = express();
app.use(express.json());
app.listen(PORT, () => console.log("Server running on port " + PORT));

// ================= TELEGRAM WEBHOOK =================
const bot = new TelegramBot(TOKEN);
bot.setWebHook(`${WEBHOOK_URL}/bot${TOKEN}`);

app.post(`/bot${TOKEN}`, (req, res) => {
  bot.processUpdate(req.body);
  res.sendStatus(200);
});

// ================= SYMBOLS =================
const SYMBOLS = {
  MZNPETF: "Meezan ETF",
  NITETF: "National ETF",
  FFC: "Fauji Fertilizer",
  ENGRO: "Engro Corp",
  PTL: "Panther Tyre",
  HUBC: "Hubco"
};

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
  } catch {
    return null;
  }
}

// ================= FAST INITIAL DATA (FIXES WAIT ISSUE) =================
async function initialLoad() {
  console.log("Loading initial data...");

  for (let i = 0; i < 60; i++) { // preload 60 ticks

    for (const symbol of Object.keys(SYMBOLS)) {
      const tick = await fetchPrice(symbol);
      if (tick) priceStore[symbol].push(tick);
    }

    await new Promise(r => setTimeout(r, 2000));
  }

  console.log("Initial data ready");
}

initialLoad();

// ================= LIVE COLLECTION =================
setInterval(async () => {

  for (const symbol of Object.keys(SYMBOLS)) {

    const tick = await fetchPrice(symbol);
    if (!tick) continue;

    priceStore[symbol].push(tick);

    if (priceStore[symbol].length > 2000)
      priceStore[symbol] = priceStore[symbol].slice(-2000);
  }

}, 10000); // faster collection (10 sec)

// ================= BUILD CANDLES =================
function buildCandles(data, timeframe) {

  if (!data.length) return null;

  const buckets = {};

  data.forEach(t => {

    const key = Math.floor(t.time / timeframe) * timeframe;

    if (!buckets[key]) {
      buckets[key] = {
        open: t.price,
        high: t.price,
        low: t.price,
        close: t.price,
        volume: 0
      };
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

  if (closes.length < 20) return null;

  return {
    price: closes.at(-1).toFixed(2),
    rsi: ti.RSI.calculate({ values: closes, period: 14 }).at(-1)?.toFixed(2),
    ema: ti.EMA.calculate({ values: closes, period: 20 }).at(-1)?.toFixed(2),
    sma: ti.SMA.calculate({ values: closes, period: 20 }).at(-1)?.toFixed(2),
    macd: ti.MACD.calculate({
      values: closes,
      fastPeriod: 12,
      slowPeriod: 26,
      signalPeriod: 9
    }).at(-1)?.MACD?.toFixed(2),
    obv: ti.OBV.calculate({
      close: closes,
      volume: volumes
    }).at(-1)?.toFixed(2)
  };
}

// ================= BOT COMMAND =================
bot.onText(/\/analyze (.+) (.+)/, async (msg, match) => {

  const chatId = msg.chat.id;

  const symbol = match[1].toUpperCase();
  const tf = match[2];

  if (!SYMBOLS[symbol])
    return bot.sendMessage(chatId, "Symbol not supported");

  if (!TIMEFRAMES[tf])
    return bot.sendMessage(chatId, "Invalid timeframe");

  const candles = buildCandles(priceStore[symbol], TIMEFRAMES[tf]);

  if (!candles)
    return bot.sendMessage(chatId, "Data loading... try again shortly");

  const result = calculateIndicators(candles);

  if (!result)
    return bot.sendMessage(chatId, "Not enough data yet");

  const signal =
    result.rsi > 70 ? "Overbought" :
    result.rsi < 30 ? "Oversold" : "Neutral";

  bot.sendMessage(chatId,
`📊 ${SYMBOLS[symbol]} (${symbol})
⏱ ${tf}

Price: ${result.price}

RSI: ${result.rsi}
EMA20: ${result.ema}
SMA20: ${result.sma}
MACD: ${result.macd}
OBV: ${result.obv}

Signal: ${signal}`);
});

console.log("Bot ready");
