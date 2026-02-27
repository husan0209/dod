# apps/miniapp/bot/handlers.py

import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from django.conf import settings
from apps.miniapp.services.auth_service import TelegramAuthService

logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    user = update.effective_user
    args = context.args

    # Check for deeplink
    deeplink = None
    if args and args[0].startswith('ref_'):
        deeplink = args[0]

    # Get or create Telegram user
    try:
        validated_data = {
            'user': {
                'id': user.id,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'username': user.username,
                'photo_url': user.photo_url,
                'language_code': user.language_code,
                'is_premium': getattr(user, 'is_premium', False),
            },
            'auth_date': update.message.date.timestamp(),
            'hash': 'telegram_webapp_hash',  # Would be validated in production
        }

        django_user, tg_user, is_new = TelegramAuthService.get_or_create_user(validated_data)

        if deeplink:
            tg_user.referred_by_deeplink = deeplink
            tg_user.save()

    except Exception as e:
        logger.error(f"Error creating user: {e}")

    # Create keyboard
    keyboard = [
        [InlineKeyboardButton("🎮 Открыть DOD", web_app={"url": settings.TELEGRAM_WEBAPP_URL})]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    welcome_text = f"""
🎮 Добро пожаловать в DOD!

Ставки на спорт ⚽ | Казино 🎰
Маркеты предсказаний 📊

👇 Нажми кнопку ниже чтобы начать!
"""

    await update.message.reply_text(
        welcome_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /balance command."""
    user = update.effective_user

    try:
        # Get user balance (mock data)
        balance_text = """
💰 Ваш баланс:

🇺🇸 USD: $1,234.56
₿ BTC: 0.01234
💎 USDT: $500.00

[🎮 Открыть кошелёк](web_app_url/wallet)
[➕ Пополнить](web_app_url/wallet/deposit)
"""

        keyboard = [
            [InlineKeyboardButton("🎮 Открыть кошелёк", web_app={"url": f"{settings.TELEGRAM_WEBAPP_URL}/wallet"})],
            [InlineKeyboardButton("➕ Пополнить", web_app={"url": f"{settings.TELEGRAM_WEBAPP_URL}/wallet/deposit"})]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            balance_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    except Exception as e:
        logger.error(f"Error in balance command: {e}")
        await update.message.reply_text("❌ Ошибка получения баланса")


async def deposit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /deposit command."""
    keyboard = [
        [InlineKeyboardButton("💳 Пополнить", web_app={"url": f"{settings.TELEGRAM_WEBAPP_URL}/wallet/deposit"})]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "💰 Пополните баланс через Mini App:",
        reply_markup=reply_markup
    )


async def referral_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /referral command."""
    user = update.effective_user

    # Mock referral data
    referral_link = f"t.me/{settings.TELEGRAM_BOT_USERNAME}?start=ref_DOD-{user.id}"
    referral_count = 23  # Mock
    earnings = 890.12  # Mock

    referral_text = f"""
🤝 Партнёрская программа

Твоя ссылка:
{referral_link}

👥 Рефералов: {referral_count}
💰 Заработано: ${earnings:.2f}
"""

    keyboard = [
        [InlineKeyboardButton("📋 Копировать ссылку", callback_data="copy_referral")],
        [InlineKeyboardButton("📤 Поделиться", switch_inline_query="ref_DOD-X7K9M2")],
        [InlineKeyboardButton("📊 Подробная статистика", web_app={"url": f"{settings.TELEGRAM_WEBAPP_URL}/profile/referral"})]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        referral_text,
        reply_markup=reply_markup
    )


async def support_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /support command."""
    keyboard = [
        [InlineKeyboardButton("💬 Создать тикет", web_app={"url": f"{settings.TELEGRAM_WEBAPP_URL}/support/new"})],
        [InlineKeyboardButton("📋 Мои тикеты", web_app={"url": f"{settings.TELEGRAM_WEBAPP_URL}/support"})],
        [InlineKeyboardButton("❓ FAQ", web_app={"url": f"{settings.TELEGRAM_WEBAPP_URL}/support/faq"})]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🎧 Поддержка DOD\n\nВыберите действие:",
        reply_markup=reply_markup
    )


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /settings command."""
    settings_text = """
⚙️ Настройки уведомлений:

✅ Результаты ставок
✅ Депозиты
✅ Выводы
❌ Промо-акции
✅ Резолюция маркетов
✅ Реферальная активность
✅ Безопасность
"""

    keyboard = [
        [InlineKeyboardButton("Изменить настройки", web_app={"url": f"{settings.TELEGRAM_WEBAPP_URL}/profile/settings"})]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        settings_text,
        reply_markup=reply_markup
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    help_text = """
❓ Справка по командам:

/start - Запустить приложение
/balance - Посмотреть баланс
/deposit - Пополнить баланс
/referral - Партнёрская программа
/support - Поддержка
/settings - Настройки уведомлений
/help - Эта справка

Для игры откройте Mini App через кнопку меню или /start
"""

    await update.message.reply_text(help_text)


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callback queries."""
    query = update.callback_query
    data = query.data

    if data == "copy_referral":
        referral_link = f"t.me/{settings.TELEGRAM_BOT_USERNAME}?start=ref_DOD-{query.from_user.id}"
        await query.answer(f"Ссылка скопирована: {referral_link}")
    else:
        await query.answer("Неизвестная команда")


async def handle_inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline queries."""
    query = update.inline_query.query

    results = []

    if query.startswith('ref'):
        # Referral link
        referral_link = f"t.me/{settings.TELEGRAM_BOT_USERNAME}?start={query}"
        results.append(
            InlineQueryResultArticle(
                id='referral',
                title='🎮 DOD — Ставки и Казино',
                description='Присоединяйся к DOD!',
                input_message_content=InputTextMessageContent(
                    '🎮 DOD — Ставки и Казино\n\n'
                    '⚽ Ставки на спорт | 🎰 Казино | 📊 Predictions\n\n'
                    f'Присоединяйся: {referral_link}'
                ),
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🎮 Открыть DOD", web_app={"url": settings.TELEGRAM_WEBAPP_URL})
                ]])
            )
        )
    elif query.startswith('market'):
        # Market search
        results.append(
            InlineQueryResultArticle(
                id='market',
                title='📊 BTC > $150k к 01.06?',
                description='YES: 78% | NO: 22%',
                input_message_content=InputTextMessageContent(
                    '📊 BTC > $150k к 01.06?\n'
                    'YES: 78% | NO: 22%\n'
                    'Объём: $45,678'
                ),
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("📊 Торговать", web_app={"url": f"{settings.TELEGRAM_WEBAPP_URL}/predictions"})
                ]])
            )
        )
    elif query.startswith('match'):
        # Match search
        results.append(
            InlineQueryResultArticle(
                id='match',
                title='⚽ Реал Мадрид — Барселона',
                description='Сегодня 21:00 | 1: 2.10 X: 3.40 2: 3.80',
                input_message_content=InputTextMessageContent(
                    '⚽ Реал Мадрид — Барселона\n'
                    'Сегодня 21:00\n'
                    '1: 2.10 | X: 3.40 | 2: 3.80'
                ),
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("⚽ Сделать ставку", web_app={"url": f"{settings.TELEGRAM_WEBAPP_URL}/sports"})
                ]])
            )
        )

    await update.inline_query.answer(results, cache_time=30)
