"""
Обработчики команд Telegram бота.
"""

import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from .services import TelegramNotificationService
from .keyboards import get_main_keyboard, get_settings_keyboard

logger = logging.getLogger(__name__)
User = get_user_model()


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик команды /start.
    """
    user = update.effective_user

    if await check_user_linked(update):
        # Показать меню
        keyboard = get_main_keyboard()
        text = f"""
Привет, {user.first_name}! 👋

Ваш аккаунт привязан. Выберите действие:
        """.strip()
    else:
        # Предложить привязать
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔗 Привязать аккаунт", callback_data="link_account")]
        ])
        text = f"""
Привет, {user.first_name}! 👋

Для использования бота DOD необходимо привязать ваш аккаунт.

Нажмите кнопку ниже и следуйте инструкциям.
        """.strip()

    await update.message.reply_text(text, reply_markup=keyboard)


async def link_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик команды /link.
    """
    user = update.effective_user

    if await check_user_linked(update):
        await update.message.reply_text("Ваш аккаунт уже привязан!")
        return

    # Генерируем код
    code = await generate_link_code(user.id)

    text = f"""
Для привязки аккаунта DOD:

1. Откройте сайт dod.com
2. Перейдите в Настройки → Telegram
3. Введите код: `{code}`

Код действителен 10 минут.
    """.strip()

    await update.message.reply_text(text, parse_mode='Markdown')


async def unlink_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик команды /unlink.
    """
    user = update.effective_user

    if not await check_user_linked(update):
        await update.message.reply_text("Ваш аккаунт не привязан!")
        return

    # Отвязываем
    User.objects.filter(telegram_id=user.id).update(telegram_id=None)

    await update.message.reply_text("Аккаунт отвязан. Используйте /link для повторной привязки.")


async def balance_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик команды /balance.
    """
    if not await check_user_linked(update):
        return

    user = await get_dod_user(update.effective_user.id)
    if not user:
        await update.message.reply_text("Пользователь не найден.")
        return

    # Получить баланс (предполагаем, что есть wallet)
    balance = getattr(user, 'balance', 0)  # TODO: implement

    await update.message.reply_text(f"💰 Ваш баланс: ${balance}")


async def bets_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик команды /bets.
    """
    if not await check_user_linked(update):
        return

    user = await get_dod_user(update.effective_user.id)
    if not user:
        await update.message.reply_text("Пользователь не найден.")
        return

    # Получить последние ставки (TODO: implement)
    bets_text = "Последние ставки:\n\nНет активных ставок."

    await update.message.reply_text(bets_text)


async def support_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик команды /support.
    """
    if not await check_user_linked(update):
        return

    user = await get_dod_user(update.effective_user.id)
    if not user:
        await update.message.reply_text("Пользователь не найден.")
        return

    # Получить тикеты (TODO: implement)
    tickets_text = "Ваши тикеты:\n\nНет активных обращений."

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Создать тикет", url="https://dod.com/support/new/")]
    ])

    await update.message.reply_text(tickets_text, reply_markup=keyboard)


async def settings_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик команды /settings.
    """
    if not await check_user_linked(update):
        return

    keyboard = get_settings_keyboard()
    text = "Настройки уведомлений:"

    await update.message.reply_text(text, reply_markup=keyboard)


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик команды /help.
    """
    text = """
Доступные команды:

/start - Главное меню
/link - Привязать аккаунт
/unlink - Отвязать аккаунт
/balance - Проверить баланс
/bets - Последние ставки
/support - Ваши тикеты
/settings - Настройки уведомлений
/referral - Реферальная ссылка
/help - Эта справка
    """.strip()

    await update.message.reply_text(text)


async def referral_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик команды /referral.
    """
    if not await check_user_linked(update):
        return

    user = await get_dod_user(update.effective_user.id)
    if not user:
        await update.message.reply_text("Пользователь не найден.")
        return

    # TODO: implement referral system
    referral_text = "🤝 Ваша реферальная ссылка:\nhttps://dod.com/r/DOD-X7K9M2\n\nРефералов: 0 | Заработано: $0"

    await update.message.reply_text(referral_text)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик текстовых сообщений.
    """
    text = update.message.text.strip()

    # Проверяем, является ли сообщение кодом привязки
    if await try_link_account(update, text):
        return

    # Если не код и не команда, игнорируем
    pass


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик callback запросов.
    """
    query = update.callback_query
    data = query.data

    if data == "link_account":
        await link_handler(update, context)
    elif data.startswith("settings_"):
        # Обработка настроек
        pass

    await query.answer()


# Вспомогательные функции

async def check_user_linked(update: Update):
    """Проверить, привязан ли пользователь."""
    user = await get_dod_user(update.effective_user.id)
    if not user:
        await update.message.reply_text("Сначала привяжите аккаунт с помощью /link")
        return False
    return True


async def get_dod_user(telegram_id):
    """Получить пользователя DOD по telegram_id."""
    try:
        return await User.objects.aget(telegram_id=telegram_id)
    except User.DoesNotExist:
        return None


async def generate_link_code(telegram_id):
    """Генерировать код для привязки."""
    import random
    import string

    code = ''.join(random.choices(string.digits, k=6))

    # Сохраняем код в кэше на 10 минут
    from django.core.cache import cache
    cache.set(f'telegram_link_{code}', telegram_id, 600)

    return code


async def try_link_account(update, code):
    """Попытаться привязать аккаунт по коду."""
    from django.core.cache import cache

    telegram_id = cache.get(f'telegram_link_{code}')
    if telegram_id and telegram_id == update.effective_user.id:
        # Код верный, но нужно получить user_id от сайта
        # В реальности это делается через сайт
        await update.message.reply_text("Код принят! Теперь введите его на сайте.")
        return True

    return False
