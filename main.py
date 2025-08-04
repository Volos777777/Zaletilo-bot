import os
import telebot
from openai import OpenAI
from flask import Flask, request
import logging
import sqlite3
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

# Налаштування логування
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Перевірка змінних середовища
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
APP_URL = os.getenv("APP_URL")
PORT = os.getenv("PORT", "5000")

if not BOT_TOKEN:
    logging.error("BOT_TOKEN не встановлено")
    raise ValueError("Помилка: BOT_TOKEN не встановлено")
if not OPENAI_API_KEY:
    logging.error("OPENAI_API_KEY не встановлено")
    raise ValueError("Помилка: OPENAI_API_KEY не встановлено")
if not APP_URL:
    logging.error("APP_URL не встановлено")
    raise ValueError("Помилка: APP_URL не встановлено")

logging.info(f"APP_URL: {APP_URL}, PORT: {PORT}")

# Ініціалізація бота
bot = telebot.TeleBot(BOT_TOKEN)

# Ініціалізація OpenAI
client = OpenAI(api_key=OPENAI_API_KEY)

# Ініціалізація Flask
app = Flask(__name__)

# Зчитування інструкцій із файлу
try:
    with open("instructions.txt", "r", encoding="utf-8") as file:
        system_prompt = file.read()
    logging.info("Інструкції успішно завантажено з instructions.txt")
except FileNotFoundError:
    system_prompt = (
        "Ти ШІ-консультант для креаторів контенту, який відповідає українською. "
        "Спілкуйся дружньо, як досвідчений друг, який допомагає з маркетингом, створенням контенту для YouTube, Instagram, TikTok та монетизацією. "
        "Використовуй покрокові інструкції, приклади та легкий гумор. "
        "Якщо користувач питає, хто ти, нагадуй, що ти ШІ.
