import os
import telebot
from openai import OpenAI

# Перевірка змінних середовища
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not BOT_TOKEN:
    raise ValueError("Помилка: BOT_TOKEN не встановлено")
if not OPENAI_API_KEY:
    raise ValueError("Помилка: OPENAI_API_KEY не встановлено")

# Ініціалізація бота
bot = telebot.TeleBot(BOT_TOKEN)

# Ініціалізація OpenAI
client = OpenAI(api_key=OPENAI_API_KEY)

# Зчитування інструкцій із файлу
try:
    with open("instructions.txt", "r", encoding="utf-8") as file:
        system_prompt = file.read()
except FileNotFoundError:
    system_prompt = "Ти ввічливий консультант, який відповідає українською."

# Історія чатів
chat_history = {}

# Обробник команди /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привіт! Я твій консультант для креаторів. Задавай питання про контент, маркетинг чи монетизацію!")

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

        bot.reply_to(message, bot_response)

    except Exception as e:
        bot.reply_to(message, f"Виникла помилка: {str(e)}. Спробуй ще раз!")
        print(f"Помилка: {e}")

# Запуск бота
if __name__ == '__main__':
    print("Бот запускається...")
    bot.polling(none_stop=True)
