import os
import telebot
from openai import OpenAI

# Налаштування токенів
TOKEN = os.getenv("BOT_TOKEN")  # Переконайся, що змінна називається BOT_TOKEN на Railway
bot = telebot.TeleBot(TOKEN)

# Ініціалізація OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Обробник команди /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привіт! Це бот для креаторів! Задавай свої питання, і я допоможу.")

# Обробник текстових повідомлень
@bot.message_handler(content_types=['text'])
def handle_message(message):
    user_message = message.text
    
    try:
        # Запит до ChatGPT
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # або "gpt-4", якщо є доступ
            messages=[
                {"role": "system", "content": "Ти ввічливий консультант для креаторів, який відповідає українською. Допомагай із питаннями про творчість, контент і бізнес."},
                {"role": "user", "content": user_message}
            ]
        )
        
        # Отримання відповіді
        bot_response = response.choices[0].message.content
        
        # Відправка відповіді користувачу
        bot.reply_to(message, bot_response)
    
    except Exception as e:
        # Обробка помилок
        bot.reply_to(message, f"Виникла помилка: {str(e)}. Спробуй ще раз!")
        print(f"Помилка: {e}")

# Запуск бота
if __name__ == '__main__':
    bot.polling(none_stop=True)
