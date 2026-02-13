const TelegramBot = require("node-telegram-bot-api");
const axios = require("axios");
const ti = require("technicalindicators");

// ================= CONFIG =================
const TOKEN = "8493857966:AAGZqy8FH3Pvdw1uCs2lhakKRCrv6n_h83E";

const bot = new TelegramBot(TOKEN, { polling: true });

const BASE_URL = "https://psxterminal.com/api/ticks/REG/";

// Supported symbols
const SYMBOLS = {
  MZNPETF: "Meezan ETF",
  NITETF: "National ETF",
  FFC: "Fauji Fertilizer",
  ENGRO: "Engro Corp",
  PTL: "Panther Tyre",
  HUBC: "Hubco"
};

// timeframe seconds
const TIMEFRAMES = {
  "10m": 600,
  "15m": 900,
  "30m": 1800,
  "1h": 3600,
  "4h": 14400,
  "12h": 43200,
  "1d": 86400
};

// price storage
const priceStore = {};

// initialize storage
Object.keys(SYMBOLS).forEach(s => priceStore[s] = []);

// ================= FETCH PRICE =================
async function fetchPrice(symbol) {
  try {
    const res = await axios.get(BASE_URL + symbol);
    return {
      price: parseFloat(res.data.price || 0),
      volume: parseFloat(res.data.volume || 0),
      time: Math.floor(Date.now() / 1000)
    };
  } catch {
    return null;
  }
}

// ================= COLLECT DATA =================
setInterval(async () => {

  for (const symbol of Object.keys(SYMBOLS)) {

    const tick = await fetchPrice(symbol);
    if (!tick) continue;

    priceStore[symbol].push(tick);

    // keep last 5000 ticks
    if (priceStore[symbol].length > 5000)
      priceStore[symbol] = priceStore[symbol].slice(-5000);
  }

}, 30000); // every 30 sec


// ================= BUILD CANDLES =================
function buildCandles(data, timeframe) {

  const grouped = {};

  data.forEach(t => {
    const bucket = Math.floor(t.time / timeframe) * timeframe;

    if (!grouped[bucket])
      grouped[bucket] = {
        open: t.price,
        high: t.price,
        low: t.price,
        close: t.price,
        volume: 0
      };

    grouped[bucket].high = Math.max(grouped[bucket].high, t.price);
    grouped[bucket].low = Math.min(grouped[bucket].low, t.price);
    grouped[bucket].close = t.price;
    grouped[bucket].volume += t.volume;
  });

  return Object.values(grouped);
}

// ================= INDICATORS =================
function calculateIndicators(candles) {

  const closes = candles.map(c => c.close);
  const volumes = candles.map(c => c.volume);

  if (closes.length < 50) return null;

  const rsi = ti.RSI.calculate({ values: closes, period: 14 });
  const ema = ti.EMA.calculate({ values: closes, period: 20 });
  const sma = ti.SMA.calculate({ values: closes, period: 20 });

  const macd = ti.MACD.calculate({
    values: closes,
    fastPeriod: 12,
    slowPeriod: 26,
    signalPeriod: 9
  });

  const obv = ti.OBV.calculate({
    close: closes,
    volume: volumes
  });

  return {
    price: closes.at(-1).toFixed(2),
    rsi: rsi.at(-1)?.toFixed(2),
    ema: ema.at(-1)?.toFixed(2),
    sma: sma.at(-1)?.toFixed(2),
    macd: macd.at(-1)?.MACD?.toFixed(2),
    obv: obv.at(-1)?.toFixed(2)
  };
}

// ================= BOT COMMAND =================
bot.onText(/\/analyze (.+) (.+)/, async (msg, match) => {

  const chatId = msg.chat.id;

  const symbol = match[1].toUpperCase();
  const tf = match[2];

  if (!SYMBOLS[symbol])
    return bot.sendMessage(chatId, "❌ Symbol not supported");

  if (!TIMEFRAMES[tf])
    return bot.sendMessage(chatId, "❌ Invalid timeframe");

  const candles = buildCandles(priceStore[symbol], TIMEFRAMES[tf]);

  if (!candles || candles.length < 50)
    return bot.sendMessage(chatId, "⏳ Collecting data... try again in few minutes");

  const result = calculateIndicators(candles);

  const rsiSignal =
    result.rsi > 70 ? "Overbought" :
    result.rsi < 30 ? "Oversold" : "Neutral";

  bot.sendMessage(chatId, `
📊 ${SYMBOLS[symbol]} (${symbol})
⏱ Timeframe: ${tf}

💰 Price: ${result.price}

RSI: ${result.rsi}
EMA20: ${result.ema}
SMA20: ${result.sma}
MACD: ${result.macd}
OBV: ${result.obv}

Signal: ${rsiSignal}
`);
});

// ================= START =================
bot.onText(/\/start/, msg => {
  bot.sendMessage(msg.chat.id,
`PSX Indicator Bot Ready

Usage:
/analyze HUBC 15m
/analyze ENGRO 1h
/analyze MZNPETF 4h

Supported:
MZNPETF, NITETF, FFC, ENGRO, PTL, HUBC
`);
});

console.log("Bot running...");
