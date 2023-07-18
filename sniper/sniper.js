const Discord = require('discord.js-selfbot-v13');
const axios = require('axios');

//get config.json
const config = require('./config.json');
//get discord_info.json
const discord_info = require('./discord_info.json');

//get apiKey from config
const apiKey = config.apiKey;
//get captchaService from config
const captchaService = config.captcha_service;
// get Telegram token
const telegramToken = config.bot_token;
// get chatid
const chatId = config.chat_id;

//get toSnipe from discord_info
const toSnipe = discord_info.toSnipe;
//get myPassword from discord_info
const myPassword = discord_info.myPassword;
//get myToken from discord_info
const myToken = discord_info.myToken;



const client = new Discord.Client({
  checkUpdate: false,
  captchaKey: apiKey,
  captchaService: captchaService,
})


client.on('ready', () => {
  console.log(`Logged in as ${client.user.username}\nSniping ${toSnipe}`);
  ChangeUsername();
});

async function ChangeUsername() {
  console.log('Changing username...');
  client.user.setUsername(toSnipe, myPassword)
    .then((user) => {
      console.log(`Username sniped: ${user.username} using token: ${myToken}`);
      sendTelegramMessage(`Username sniped: ${user.username} using token: ${myToken}`);
    })
    .catch((err) => {
      console.log(err);
      sendTelegramMessage(`Error when sniping: ${err}`);
    });
}


function sendTelegramMessage(message) {
  const url = `https://api.telegram.org/bot${telegramToken}/sendMessage`;
  const data = {
    chat_id: chatId,
    text: message
  };

  axios.post(url, data)
    .then(() => {
      console.log('Telegram message sent successfully');
      process.exit();
    })
    .catch((error) => {
      console.error('Failed to send Telegram message:', error);
      process.exit();
    });
}

client.login(myToken);
