"""
Клавиатуры для Telegram бота.
"""

from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton


def get_main_keyboard():
    """Главная клавиатура для привязанного пользователя."""
    keyboard = [
        ['💰 Баланс', '🎰 Казино'],
        ['📋 Поддержка', '🤝 Рефералы'],
        ['⚙️ Настройки', '❓ Помощь'],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_settings_keyboard():
    """Клавиатура настроек уведомлений."""
    keyboard = [
        [InlineKeyboardButton("Безопасность ✅", callback_data="settings_security")],
        [InlineKeyboardButton("Финансы ✅", callback_data="settings_finance")],
        [InlineKeyboardButton("Результаты ставок ❌", callback_data="settings_bets")],
        [InlineKeyboardButton("Промо-акции ❌", callback_data="settings_promo")],
        [InlineKeyboardButton("💾 Сохранить", callback_data="settings_save")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_link_keyboard():
    """Клавиатура для привязки аккаунта."""
    keyboard = [
        [InlineKeyboardButton("🔗 Привязать аккаунт", url="https://dod.com/settings/telegram/")],
    ]
    return InlineKeyboardMarkup(keyboard)
