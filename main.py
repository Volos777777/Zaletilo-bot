import os
import signal
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.error import TelegramError
from broadcast import broadcast  # Імпорт broadcast з окремого файлу
from database import init_db, load_users, save_user, update_subscription_status, update_blocked_status  # Імпорт з database.py

# Налаштування логування
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Змінні середовища
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = "-1002823366291"
DATABASE_URL = os.getenv("DATABASE_URL")

# Обробник команди /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    save_user(
        user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        language_code=user.language_code
    )
    keyboard = [
        [InlineKeyboardButton("Підписався (лась)", callback_data="subscribe")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
await update.message.reply_text(
    f"Привіт, {user.first_name}! Ласкаво просимо до бота @zaletilo_bot!\n"
    f"Приєднуйтесь до нашого каналу: https://t.me/your_channel",
    reply_markup=reply_markup
)

# Обробник колбека для кнопки підписки та регіонів
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    chat_id = "-1002823366291"  # ID каналу
    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        if member.status in ['member', 'administrator', 'creator']:
            update_subscription_status(user_id, True)
            keyboard = [
                [
                    InlineKeyboardButton("Київ", url="https://t.me/+MAtbwy9ufGAwMzli"),
                    InlineKeyboardButton("Дніпро", url="https://t.me/+YvX-FzQHpU1kNGZi"),
                    InlineKeyboardButton("Харків", url="https://t.me/+kanHOVAz99FlODYy"),
                    InlineKeyboardButton("Одеса", url="https://t.me/+FyKju8C82b43OGEy"),
                    InlineKeyboardButton("Львів", url="https://t.me/+rbesn-FqWKkxMDFi")
                ],
                [
                    InlineKeyboardButton("Інші регіони", callback_data="other_regions")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "Дякуємо за підписку! Тепер ви можете знаходити замовлення та створювати оголошення у вашому регіоні. Оберіть свій регіон:",
                reply_markup=reply_markup
            )
        else:
            await query.edit_message_text("Ви не підписані на канал. Будь ласка, підпишіться, щоб продовжити!")
    except Exception as e:
        await query.edit_message_text("Помилка перевірки підписки. Спробуйте ще раз або зверніться до адміністратора.")
    elif query.data == "other_regions":
        # Клавіатура з рештою регіонів
        keyboard = [
            [
                InlineKeyboardButton("Запоріжжя", url="https://t.me/+XE-XiYnCSOwwYzAy"),
                InlineKeyboardButton("Вінниця", url="https://t.me/+TsEar0CH3z0wYzQy"),
                InlineKeyboardButton("Полтава", url="https://t.me/+cQcCFMOlQ6dkMWQy")
            ],
            [
                InlineKeyboardButton("Чернігів", url="https://t.me/+KPOzzkb_B4RhNjU6"),
                InlineKeyboardButton("Черкаси", url="https://t.me/+6d_cW6rKyrU0MDE6"),
                InlineKeyboardButton("Хмельницький", url="https://t.me/+2ZktT_xJXd81NTJi")
            ],
            [
                InlineKeyboardButton("Житомир", url="https://t.me/+-X78W7iXLkMzZTgy"),
                InlineKeyboardButton("Суми", url="https://t.me/+f0P0ATKrmB5lYTli"),
                InlineKeyboardButton("Рівне", url="https://t.me/+FaswQkcAfw5jNTli")
            ],
            [
                InlineKeyboardButton("Івано-Франківськ", url="https://t.me/+hqOtVtNY41tkYjMy"),
                InlineKeyboardButton("Тернопіль", url="https://t.me/+k2UwXPJrBg9mZjky"),
                InlineKeyboardButton("Ужгород", url="https://t.me/+ZGu30lrloOM1ZWMy")
            ],
            [
                InlineKeyboardButton("Луцьк", url="https://t.me/+wSOX_aMM9oJkZTdi"),
                InlineKeyboardButton("Чернівці", url="https://t.me/+zU3actkWQlwwZjI6"),
                InlineKeyboardButton("Миколаїв", url="https://t.me/+vyd6xO6jZ9o2NWI6")
            ],
            [
                InlineKeyboardButton("Херсон", url="https://t.me/+pNd7r-LabUY5Yzky"),
                InlineKeyboardButton("Кропивницький", url="https://t.me/+CAClUadjBbxhZDI6")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "Ось інші регіони для вибору:",
            reply_markup=reply_markup
        )
# Обробник команди /stats
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    admin_id = 293102975
    if user_id != admin_id:
        await update.message.reply_text("Ця команда доступна лише адміністратору!")
        return
    try:
        conn = psycopg2.connect(
            dbname=os.getenv("PGDATABASE"),
            user=os.getenv("PGUSER"),
            password=os.getenv("PGPASSWORD"),
            host=os.getenv("PGHOST"),
            port=os.getenv("PGPORT")
        )
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM users")
        total_users = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM users WHERE is_subscribed = TRUE AND is_blocked = FALSE")
        subscribed_users = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM users WHERE is_blocked = TRUE")
        blocked_users = cur.fetchone()[0]
        await update.message.reply_text(
            f"Статистика користувачів:\n"
            f"Загальна кількість: {total_users}\n"
            f"Підписані на канал: {subscribed_users}\n"
            f"Заблоковані: {blocked_users}"
        )
    except Exception as e:
        logger.error(f"Помилка при отриманні статистики: {e}")
        await update.message.reply_text(f"Помилка: {e}")
    finally:
        if conn:
            conn.close()

# Обробник сигналів для коректного завершення
def signal_handler(sig, frame):
    logger.info("Отримано сигнал завершення, вимикаю бота...")
    os._exit(0)

# Ініціалізація та запуск бота
if __name__ == "__main__":
    # Налаштування обробки сигналів
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Ініціалізація бази даних
    init_db()

    # Створення додатку
    application = Application.builder().token(TOKEN).build()

    # Додавання обробників команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("broadcast", broadcast))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CallbackQueryHandler(button_callback))

    # Запуск бота
    logger.info("Бот запущено")
    application.run_polling()
