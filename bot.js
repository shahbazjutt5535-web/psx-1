require("dotenv").config();
const TelegramBot = require("node-telegram-bot-api");
const fetch = require("node-fetch");

const bot = new TelegramBot(process.env.BOT_TOKEN, { polling: true });

const API_KEY = process.env.API_KEY;

/*
============================
   STOCK DATA FETCHER
============================
*/

async function getStockData(symbol) {
  try {
    // PSX prefix auto add
    if (!symbol.includes(":")) {
      symbol = "PSX:" + symbol.toUpperCase();
    }

    // timestamp prevents caching (IMPORTANT FIX)
    const url = `https://api-v4.fcsapi.com/stock?access_key=${API_KEY}&symbol=${symbol}&t=${Date.now()}`;

    const res = await fetch(url);
    const data = await res.json();

    if (!data || !data.response || data.response.length === 0) {
      return null;
    }

    return data.response[0];
  } catch (err) {
    console.log("API Error:", err);
    return null;
  }
}

/*
============================
   SIMPLE RSI CALCULATION
============================
*/

function calculateRSI(prices, period = 14) {
  if (prices.length < period) return "Not enough data";

  let gains = 0;
  let losses = 0;

  for (let i = 1; i <= period; i++) {
    const diff = prices[i] - prices[i - 1];
    if (diff >= 0) gains += diff;
    else losses -= diff;
  }

  const rs = gains / (losses || 1);
  return (100 - 100 / (1 + rs)).toFixed(2);
}

/*
============================
   COMMANDS
============================
*/

bot.onText(/\/start/, (msg) => {
  bot.sendMessage(
    msg.chat.id,
    `📈 Stock Bot Ready

Use:
 /stock FFC
 /stock ENGRO
 /stock HUBC
 /stock PANTHER
 /stock MEBL

You can also use:
 PSX:FFC`
  );
});

/*
============================
   STOCK COMMAND
============================
*/

bot.onText(/\/stock (.+)/, async (msg, match) => {
  const chatId = msg.chat.id;
  const symbol = match[1].trim().toUpperCase();

  bot.sendMessage(chatId, "Fetching market data...");

  const stock = await getStockData(symbol);

  if (!stock) {
    return bot.sendMessage(
      chatId,
      "❌ No market data available for this symbol.\nTry PSX format or check symbol."
    );
  }

  // create fake price series for RSI demo
  const prices = [
    parseFloat(stock.c),
    parseFloat(stock.c) * 0.99,
    parseFloat(stock.c) * 1.01,
    parseFloat(stock.c) * 1.02,
    parseFloat(stock.c) * 0.98,
    parseFloat(stock.c) * 1.01,
    parseFloat(stock.c) * 1.03,
    parseFloat(stock.c) * 0.97,
    parseFloat(stock.c) * 1.02,
    parseFloat(stock.c) * 1.01,
    parseFloat(stock.c) * 1.02,
    parseFloat(stock.c) * 0.99,
    parseFloat(stock.c) * 1.01,
    parseFloat(stock.c) * 1.03,
    parseFloat(stock.c) * 1.02
  ];

  const rsi = calculateRSI(prices);

  const message = `
📊 ${symbol}

💰 Price: ${stock.c}
📈 High: ${stock.h}
📉 Low: ${stock.l}
🔄 Change: ${stock.ch}

📌 Indicators
RSI(14): ${rsi}
`;

  bot.sendMessage(chatId, message);
});

/*
============================
   ERROR HANDLER
============================
*/

bot.on("polling_error", console.log);

console.log("Bot running...");
