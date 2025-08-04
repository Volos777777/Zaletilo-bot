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

# Додаємо https:// до APP_URL, якщо відсутнє
if not APP_URL.startswith("https://"):
    APP_URL = f"https://{APP_URL}"
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
        "Якщо користувач питає, хто ти, нагадуй, що ти ШІ. "
        "Якщо запит не стосується тем креаторів, ввічливо перенаправ до релевантних питань."
    )
    logging.warning("instructions.txt не знайдено, використовується стандартна підказка")

# Ініціалізація SQLite
def init_db():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            phone_number TEXT
        )
    """)
    conn.commit()
    conn.close()
    logging.info("База даних users.db ініціалізована")

init_db()

# Збереження контактів у базу
def save_contact(user_id, username, phone_number):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO users (user_id, username, phone_number) VALUES (?, ?, ?)",
        (user_id, username, phone_number)
    )
    conn.commit()
    conn.close()
    logging.info(f"Збережено контакт: user_id={user_id}, username={username}, phone_number={phone_number}")

# Історія чатів
chat_history = {}

# Обробник Webhook
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    try:
        update = telebot.types.Update.de_json(request.get_json())
        bot.process_new_updates([update])
        logging.info("Отримано та оброблено Webhook-запит")
        return "OK", 200
    except Exception as e:
        logging.error(f"Помилка обробки Webhook: {e}")
        return "Error", 500

# Обробник команди /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    button = KeyboardButton("Поділитися контактом", request_contact=True)
    keyboard.add(button)
    bot.reply_to(
        message,
        "Привіт! Я ШІ-консультант для креаторів, твій помічник із YouTube, Instagram і TikTok. 😎 "
        "Ми збережемо твій номер для персоналізованих консультацій. Твої дані в безпеці! Поділися контактом!",
        reply_markup=keyboard
    )
    logging.info(f"Надіслано /start для user_id={message.from_user.id}")

# Обробник контактів
@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    user_id = message.from_user.id
    username = message.from_user.username
    phone_number = message.contact.phone_number

    save_contact(user_id, username, phone_number)
    
    bot.reply_to(
        message,
        f"Дякую, {message.from_user.first_name}! Твій номер збережено. 😊 "
        "Тепер можеш питати про створення контенту, маркетинг чи монетизацію!"
    )
    bot.reply_to(message, "Клавіатура прибрана.", reply_markup=telebot.types.ReplyKeyboardRemove())
    logging.info(f"Оброблено контакт для user_id={user_id}")

# Обробник текстових повідомлень
@bot.message_handler(content_types=['text'])
def handle_message(message):
    user_id = message.from_user.id
    user_message = message.text

    if user_id not in chat_history:
        chat_history[user_id] = [{"role": "system", "content": system_prompt}]

    chat_history[user_id].append({"role": "user", "content": user_message})

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=chat_history[user_id],
            max_tokens=150
        )

        bot_response = response.choices[0].message.content
        chat_history[user_id].append({"role": "assistant", "content": bot_response})

        if len(chat_history[user_id]) > 10:
            chat_history[user_id] = chat_history[user_id][-10:]

        if len(chat_history[user_id]) % 5 == 0:
            bot_response += "\nДо речі, я ШІ, але стараюся бути максимально корисним! 😊"

        bot.reply_to(message, bot_response)
        logging.info(f"Надіслано відповідь для user_id={user_id}: {bot_response[:50]}...")

    except Exception as e:
        bot.reply_to(message, f"Виникла помилка: {str(e)}. Спробуй ще раз!")
        logging.error(f"Помилка OpenAI для user_id={user_id}: {e}")

# Обробник для перевірки статусу сервера
@app.route("/")
def index():
    try:
        bot.remove_webhook()
        bot.set_webhook(url=f"{APP_URL}/{BOT_TOKEN}")
        logging.info(f"Webhook встановлено: {APP_URL}/{BOT_TOKEN}")
        return "Webhook set", 200
    except Exception as e:
        logging.error(f"Помилка налаштування Webhook: {e}")
        return "Webhook setup failed", 500

# Запуск сервера (для локального тестування, Railway використовує gunicorn)
if __name__ == '__main__':
    logging.info("Запуск сервера для локального тестування...")
    bot.remove_webhook()
    bot.set_webhook(url=f"{APP_URL}/{BOT_TOKEN}")
    app.run(host="0.0.0.0", port=int(PORT))
