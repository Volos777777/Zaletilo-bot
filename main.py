import telebot
import os

TOKEN = os.getenv("8453481822:AAGHuaRfVgQSSHq_0iPkmlp1gK8q83rPyN0")
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привіт! Це бот для креаторів!")

bot.polling()
