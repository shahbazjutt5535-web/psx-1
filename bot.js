// -------------------- CONFIG --------------------
const TELEGRAM_BOT_TOKEN = "8493857966:AAE1b9-ZF0-8XarEBGtehHF07vlQrOCHzKQ"; // Replace with your token
const PSX_BASE_URL = "https://psxterminal.com/api/ticks/";
const PORT = process.env.PORT || 10000;

const SYMBOLS = ["FFC", "HUBC", "PTL", "MZNPETF", "NITETF", "ENGRO", "NBPGETF", "MEZNETF"];
const SYMBOL_MARKET = {
  "FFC": "REG",
  "HUBC": "REG",
  "PTL": "REG",
  "MZNPETF": "IDX",
  "NITETF": "IDX",
  "ENGRO": "REG",
  "NBPGETF": "REG",
  "MEZNETF": "REG"
};

const COMMANDS_TEXT = SYMBOLS.map(s => `/${s.toLowerCase()}`).join(" ");

// -------------------- MODULES --------------------
const express = require("express");
const bodyParser = require("body-parser");
const axios = require("axios");
const TelegramBot = require("node-telegram-bot-api");

// -------------------- APP & BOT --------------------
const app = express();
app.use(bodyParser.json());

const bot = new TelegramBot(TELEGRAM_BOT_TOKEN, { polling: true });

// -------------------- TELEGRAM COMMANDS --------------------
bot.onText(/\/start/, (msg) => {
  const chatId = msg.chat.id;
  bot.sendMessage(chatId, `Welcome to PSX Bot 🤖\n\nCommands:\n${COMMANDS_TEXT}`);
});

// Dynamically handle each symbol command
SYMBOLS.forEach(symbol => {
  bot.onText(new RegExp(`/${symbol.toLowerCase()}`), async (msg) => {
    const chatId = msg.chat.id;
    try {
      const data = await fetchPSX(symbol);
      if (!data) {
        return bot.sendMessage(chatId, `❌ Data for ${symbol} is currently unavailable.\n\nCommands:\n${COMMANDS_TEXT}`);
      }

      const message = `
symbol: ${data.symbol}
price: ${data.price}
high: ${data.high || "N/A"}
low: ${data.low || "N/A"}
open price: ${data.open || "N/A"}
change: ${data.change}
change percent: ${data.changePercent}
volume: ${data.volume}
trades: ${data.trades}
value: ${data.value || "N/A"}
date&time: ${new Date().toLocaleString()}

Commands:
${COMMANDS_TEXT}
      `;
      bot.sendMessage(chatId, message);
    } catch (err) {
      bot.sendMessage(chatId, `❌ Cannot fetch data: ${err.message}\n\nCommands:\n${COMMANDS_TEXT}`);
    }
  });
});

// -------------------- FETCH PSX DATA --------------------
async function fetchPSX(symbol) {
  try {
    const market = SYMBOL_MARKET[symbol] || "REG";
    const res = await axios.get(`${PSX_BASE_URL}${market}/${symbol}`);
    if (!res.data || !res.data.success || !res.data.data || !res.data.data.price) return null;
    return res.data.data;
  } catch (err) {
    return null; // Return null if API fails
  }
}

// -------------------- START SERVER --------------------
app.listen(PORT, () => {
  console.log(`Bot ready ✅`);
  console.log(`Server running on port ${PORT}`);
});
