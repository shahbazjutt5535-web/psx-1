// -------------------- CONFIG --------------------
const TELEGRAM_BOT_TOKEN = "8493857966:AAFURe8TIedYov8XnKzM1L9g_724QQe8LS8"; 
const PORT = process.env.PORT || 10000;

// Symbols with Yahoo format
const SYMBOLS = {
  "HUBC": "HUBC.PA",
  "FFC": "FFC.PA",
  "ENGRO": "ENGRO.PA",
  "MZNPETF": "MZNPETF.PA",
  "NITETF": "NITETF.PA",
  "PTL": "PTL.PA"
};

const INTERVALS = {
  "10m": "10m",
  "15m": "15m",
  "30m": "30m",
  "1h": "60m",
  "4h": "240m",
  "1d": "1d"
};

// -------------------- MODULES --------------------
const axios = require("axios");
const express = require("express");
const TelegramBot = require("node-telegram-bot-api");
const ti = require("technicalindicators");

// -------------------- SETUP --------------------
const app = express();
app.use(express.json());

// Only polling, no webhook
const bot = new TelegramBot(TELEGRAM_BOT_TOKEN, { polling: true });

// -------------------- HELPERS --------------------
async function fetchYahoo(symbol, interval) {
  const url = `https://query1.finance.yahoo.com/v8/finance/chart/${symbol}?interval=${interval}&range=7d`;
  try {
    const res = await axios.get(url);
    const data = res.data.chart.result[0];
    const timestamps = data.timestamp;
    const close = data.indicators.quote[0].close;
    const volume = data.indicators.quote[0].volume;

    let series = [];
    for (let i = 0; i < timestamps.length; i++) {
      if (close[i] !== null) {
        series.push({
          time: timestamps[i],
          close: close[i],
          volume: volume[i]
        });
      }
    }
    if (!series.length) throw new Error("No data returned");
    return series;
  } catch (err) {
    throw new Error("Yahoo fetch error");
  }
}

// -------------------- CALCULATE INDICATORS --------------------
function calculateIndicators(series) {
  const closes = series.map(x => x.close);
  const volumes = series.map(x => x.volume);

  const sma = ti.SMA.calculate({ values: closes, period: 14 }).pop();
  const ema = ti.EMA.calculate({ values: closes, period: 14 }).pop();
  const rsi = ti.RSI.calculate({ values: closes, period: 14 }).pop();
  const macd = ti.MACD.calculate({
    values: closes,
    fastPeriod: 12,
    slowPeriod: 26,
    signalPeriod: 9
  }).pop();
  const obv = ti.OBV.calculate({ close: closes, volume: volumes }).pop();

  return { sma, ema, rsi, macd, obv };
}

// -------------------- TELEGRAM COMMANDS --------------------
bot.onText(/\/start/, (msg) => {
  bot.sendMessage(msg.chat.id,
`Yahoo PSX Bot 🤖
Send:
/price SYMBOL INTERVAL
Example:
/price HUBC 15m`);
});

bot.onText(/\/price (.+) (.+)/, async (msg, match) => {
  const chatId = msg.chat.id;
  const symbol = match[1].toUpperCase();
  const interval = match[2].toLowerCase();

  if (!SYMBOLS[symbol] || !INTERVALS[interval]) {
    return bot.sendMessage(chatId,
`❌ Invalid input.
Symbols: ${Object.keys(SYMBOLS).join(", ")}
Intervals: ${Object.keys(INTERVALS).join(", ")}`);
  }

  bot.sendMessage(chatId, `Fetching ${symbol} (${interval})...`);

  try {
    const series = await fetchYahoo(SYMBOLS[symbol], INTERVALS[interval]);
    const latest = series[series.length - 1];
    const indicators = calculateIndicators(series);

    const msgText = `
📊 ${symbol} (${interval})
Price: ${latest.close.toFixed(2)}

SMA: ${indicators.sma.toFixed(2)}
EMA: ${indicators.ema.toFixed(2)}
RSI: ${indicators.rsi.toFixed(2)}
MACD: ${indicators.macd.MACD.toFixed(2)}, Signal: ${indicators.macd.signal.toFixed(2)}
OBV: ${indicators.obv}
`;
    bot.sendMessage(chatId, msgText);

  } catch (err) {
    bot.sendMessage(chatId, `❌ Cannot fetch data: ${err.message}`);
  }
});

// -------------------- START SERVER --------------------
app.listen(PORT, () => {
  console.log("Bot ready 👍");
  console.log(`Server running on port ${PORT}`);
});
