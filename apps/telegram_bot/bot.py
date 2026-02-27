"""
Основной Telegram бот для DOD.
"""

import logging
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from django.conf import settings
from .handlers import (
    start_handler,
    link_handler,
    unlink_handler,
    balance_handler,
    bets_handler,
    support_handler,
    settings_handler,
    help_handler,
    referral_handler,
    handle_message,
    handle_callback,
)

logger = logging.getLogger(__name__)

# Глобальная переменная для приложения
application = None


def get_application():
    """
    Получить или создать экземпляр Application.
    """
    global application
    if application is None:
        if not settings.TELEGRAM_BOT_TOKEN:
            raise ValueError("TELEGRAM_BOT_TOKEN not configured")

        application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()

        # Добавляем обработчики
        application.add_handler(CommandHandler('start', start_handler))
        application.add_handler(CommandHandler('link', link_handler))
        application.add_handler(CommandHandler('unlink', unlink_handler))
        application.add_handler(CommandHandler('balance', balance_handler))
        application.add_handler(CommandHandler('bets', bets_handler))
        application.add_handler(CommandHandler('support', support_handler))
        application.add_handler(CommandHandler('settings', settings_handler))
        application.add_handler(CommandHandler('help', help_handler))
        application.add_handler(CommandHandler('referral', referral_handler))

        # Обработчик callback запросов
        application.add_handler(CallbackQueryHandler(handle_callback))

        # Обработчик текстовых сообщений
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    return application


def run_bot():
    """
    Запуск бота в polling режиме.
    """
    app = get_application()
    logger.info("Starting Telegram bot in polling mode...")
    app.run_polling()
