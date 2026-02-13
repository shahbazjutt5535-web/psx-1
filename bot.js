// -------------------- MODULES --------------------
const express = require("express");
const bodyParser = require("body-parser");
const TelegramBot = require("node-telegram-bot-api");
const axios = require("axios");

// -------------------- CONFIG --------------------
const TELEGRAM_BOT_TOKEN = "8493857966:AAE1b9-ZF0-8XarEBGtehHF07vlQrOCHzKQ"; // Replace with your Telegram bot token
const DOMAIN = "https://psx-1.onrender.com"; // Replace with your live URL
const PORT = process.env.PORT || 10000;

const SYMBOLS = {
  FFC: "FFC",
  MEZNETF: "MZNPETF",
  NBPGETF: "NITETF",
  ENGRO: "ENGRO",
  HUBCO: "HUBC",
  PANTHER: "PTL"
};

const COMMANDS = Object.keys(SYMBOLS).map(sym => `/${sym.toLowerCase()}`);

// -------------------- EXPRESS & BOT --------------------
const app = express();
app.use(bodyParser.json());

const bot = new TelegramBot(TELEGRAM_BOT_TOKEN);
bot.setWebHook(`${DOMAIN}/bot${TELEGRAM_BOT_TOKEN}`);

// -------------------- START COMMAND --------------------
bot.onText(/\/start/, (msg) => {
  const chatId = msg.chat.id;
  bot.sendMessage(chatId, `PSX Live Bot 🤖\n\nAvailable Commands:\n${COMMANDS.join(" ")}\n\nUse any command to get live stock data.`);
});

// -------------------- SYMBOL COMMANDS --------------------
COMMANDS.forEach(command => {
  bot.onText(new RegExp(`\\${command}`), async (msg) => {
    const chatId = msg.chat.id;
    const symbol = SYMBOLS[command.replace("/", "").toUpperCase()];

    try {
      const data = await fetchPSX(symbol);
      const message = formatMessage(data);
      bot.sendMessage(chatId, message, { parse_mode: "Markdown" });
    } catch (err) {
      bot.sendMessage(chatId, `❌ Cannot fetch data: ${err.message}`);
    }
  });
});

// -------------------- FETCH PSX DATA --------------------
async function fetchPSX(symbol) {
  const url = `https://psxterminal.com/api/ticks/REG/${symbol}`;
  const res = await axios.get(url);
  const data = res.data;

  if (!data.success || !data.data) throw new Error("No data available");

  // return only the fields you requested
  return {
    symbol: data.data.symbol,
    price: data.data.price,
    high: data.data.high,
    low: data.data.low,
    open: data.data.open || "N/A", // sometimes open price may be missing
    change: data.data.change,
    changePercent: data.data.changePercent,
    volume: data.data.volume,
    trades: data.data.trades,
    value: data.data.value,
    datetime: new Date().toLocaleString()
  };
}

// -------------------- FORMAT MESSAGE --------------------
function formatMessage(d) {
  return `*${d.symbol}*:
Price: ${d.price}
High: ${d.high}
Low: ${d.low}
Open Price: ${d.open}
Change: ${d.change}
Change Percent: ${d.changePercent}
Volume: ${d.volume}
Trades: ${d.trades}
Value: ${d.value}
Date & Time: ${d.datetime}

_Commands:_ ${COMMANDS.join(" ")}`;
}

// -------------------- EXPRESS WEBHOOK --------------------
app.post(`/bot${TELEGRAM_BOT_TOKEN}`, (req, res) => {
  bot.processUpdate(req.body);
  res.sendStatus(200);
});

app.get("/", (req, res) => res.send("PSX Bot Running"));

app.listen(PORT, () => console.log(`Server running on port ${PORT}`));
