// -------------------- CONFIG --------------------
const TELEGRAM_BOT_TOKEN = "8493857966:AAFURe8TIedYov8XnKzM1L9g_724QQe8LS8"; 
const PSX_BASE_URL = "https://psxterminal.com/api/ticks/";
const PORT = process.env.PORT || 10000;

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
const BUFFER_SIZE = 50; // last prices stored per symbol/interval
const FETCH_INTERVAL = 60 * 1000; // fetch every 1 minute

// -------------------- MODULES --------------------
const axios = require("axios");
const TelegramBot = require("node-telegram-bot-api");
const ti = require("technicalindicators");

// -------------------- BOT --------------------
const bot = new TelegramBot(TELEGRAM_BOT_TOKEN, { polling: true });

// -------------------- PRICE BUFFER --------------------
const priceBuffer = {};
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
    bot.sendMessage(chatId, formatIndicatorMessage(symbol, interval, indicators));
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
    return { price, volume };
  } catch (err) {
    console.log(`PSX API error (${symbol}):`, err.message);
    return { price: null, volume: null };
  }
}

// -------------------- CALCULATE INDICATORS --------------------
function calculateIndicators(symbol, interval, tick) {
  const buf = priceBuffer[symbol][interval];

  if (tick.price) buf.push(tick.price);
  if (buf.length > BUFFER_SIZE) buf.shift();

  const series = buf.slice();
  const volumeSeries = new Array(series.length).fill(tick.volume || 1);

  const sma = series.length >= 5 ? ti.SMA.calculate({ period: 5, values: series }).pop() : tick.price;
  const ema = series.length >= 5 ? ti.EMA.calculate({ period: 5, values: series }).pop() : tick.price;
  const rsi = series.length >= 5 ? ti.RSI.calculate({ values: series, period: 5 }).pop() : 50;
  const macd = series.length >= 26 ? ti.MACD.calculate({ values: series, fastPeriod: 12, slowPeriod: 26, signalPeriod: 9 }).pop() : { MACD: 0, signal: 0, histogram: 0 };
  const obv = series.length >= 2 ? ti.OBV.calculate({ close: series, volume: volumeSeries }).pop() : 0;

  return {
    price: tick.price.toFixed(2),
    sma: sma?.toFixed(2) || tick.price.toFixed(2),
    ema: ema?.toFixed(2) || tick.price.toFixed(2),
    rsi: rsi?.toFixed(2) || 50,
    macd,
    obv
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

// -------------------- AUTO FETCH LOOP --------------------
async function autoFetch() {
  for (const symbol of SYMBOLS) {
    for (const interval of INTERVALS) {
      const tick = await fetchPSX(symbol);
      if (!tick.price) continue; // skip if price not available
      calculateIndicators(symbol, interval, tick);
    }
  }
  setTimeout(autoFetch, FETCH_INTERVAL);
}
autoFetch();

// -------------------- START SERVER --------------------
const express = require("express");
const app = express();
app.use(express.json());
app.get("/", (req, res) => res.send("PSX Indicator Bot Running ✅"));
app.listen(PORT, () => console.log(`Server running on port ${PORT}`));
