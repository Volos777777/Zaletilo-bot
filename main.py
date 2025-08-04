import os
import telebot
from openai import OpenAI
from flask import Flask, request
import logging
import sqlite3
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

# Налаштування логування
logging.basicConfig(level=logging.INFO)

# Перевірка змінних середовища
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
APP_URL = os.getenv("APP_URL")  # Наприклад, https://твій-проєкт.railway.app

if not BOT_TOKEN:
    raise ValueError("Помилка: BOT_TOKEN не встановлено")
if not OPENAI_API_KEY:
    raise ValueError("Помилка: OPENAI_API_KEY не встановлено")
if not APP_URL:
    raise ValueError("Помилка: APP_URL не встановлено")

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
except FileNotFoundError:
    system_prompt = (
        "Ти ШІ-консультант для креаторів контенту, який відповідає українською. "
        "Спілкуйся дружньо, як досвідчений друг, який допомагає з маркетингом, створенням контенту для YouTube, Instagram, TikTok та монетизацією. "
        "Використовуй покрокові інструкції, приклади та легкий гумор. "
        "Якщо користувач питає, хто ти, нагадуй, що ти ШІ. "
        "Якщо запит не стосується тем креаторів, ввічливо перенаправ до релевантних питань."
    )

# Історія чатів
chat_history = {}

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

# Обробник Webhook
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = telebot.types.Update.de_json(request.get_json())
    bot.process_new_updates([update])
    return "OK", 200

# Обробник команди /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    # Створення клавіатури з кнопкою для надсилання контакту
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    button = KeyboardButton("Поділитися контактом", request_contact=True)
    keyboard.add(button)
    bot.reply_to(
        message,
        "Привіт! Я ШІ-консультант для креаторів, твій помічник із YouTube, Instagram і TikTok. 😎 "
        "Поділися своїм контактом, щоб я міг зберегти твої дані для персоналізованих консультацій!",
        reply_markup=keyboard
    )

# Обробник контактів
@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    user_id = message.from_user.id
    username = message.from_user.username
    phone_number = message.contact.phone_number

    # Збереження контакту в базу
    save_contact(user_id, username, phone_number)
    
    bot.reply_to(
        message,
        f"Дякую, {message.from_user.first_name}! Твій номер збережено. 😊 "
        "Тепер можеш питати про створення контенту, маркетинг чи монетизацію!"
    )
    # Видаляємо клавіатуру після надсилання контакту
    bot.reply_to(message, "Клавіатура прибрана.", reply_markup=telebot.types.ReplyKeyboardRemove())

# Обробник текстових повідомлень
@bot.message_handler(content_types=['text'])
def handle_message(message):
    user_id = message.from_user.id
    user_message = message.text

    # Ініціалізація історії для користувача
    if user_id not in chat_history:
        chat_history[user_id] = [{"role": "system", "content": system_prompt}]

    # Додай повідомлення користувача до історії
    chat_history[user_id].append({"role": "user", "content": user_message})

    try:
        # Запит до ChatGPT
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=chat_history[user_id],
            max_tokens=150
        )

        # Отримання відповіді
        bot_response = response.choices[0].message.content
        chat_history[user_id].append({"role": "assistant", "content": bot_response})

        # Обмеження історії
        if len(chat_history[user_id]) > 10:
            chat_history[user_id] = chat_history[user_id][-10:]

        # Додай нагадування, що це ШІ (кожні 5 повідомлень)
        if len(chat_history[user_id]) % 5 == 0:
            bot_response += "\nДо речі, я ШІ, але стараюся бути максимально корисним! 😊"

        bot.reply_to(message, bot_response)

    except Exception as e:
        bot.reply_to(message, f"Виникла помилка: {str(e)}. Спробуй ще раз!")
        logging.error(f"Помилка: {e}")

# Налаштування Webhook
@app.route("/")
def index():
    bot.remove_webhook()
    bot.set_webhook(url=f"{APP_URL}/{BOT_TOKEN}")
    return "Webhook set", 200

# Запуск Flask-сервера
if __name__ == '__main__':
    bot.remove_webhook()  # Видалити старий Webhook
    bot.set_webhook(url=f"{APP_URL}/{BOT_TOKEN}")
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
