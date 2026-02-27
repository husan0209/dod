"""
Celery задачи для отправки сообщений в Telegram.
"""

from celery import shared_task
import telegram
from django.conf import settings
from django.contrib.auth import get_user_model

User = get_user_model()


@shared_task(bind=True, max_retries=3)
def send_telegram_message_task(self, chat_id, text, buttons=None, parse_mode='HTML'):
    """
    Celery задача отправки сообщения в Telegram.
    """
    try:
        bot = telegram.Bot(token=settings.TELEGRAM_BOT_TOKEN)
    except Exception as exc:
        self.retry(exc=exc, countdown=30)

    reply_markup = None
    if buttons:
        keyboard = []
        for btn in buttons:
            keyboard.append([
                telegram.InlineKeyboardButton(
                    text=btn['text'],
                    url=btn.get('url'),
                    callback_data=btn.get('callback_data'),
                )
            ])
        reply_markup = telegram.InlineKeyboardMarkup(keyboard)

    try:
        bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=parse_mode,
            reply_markup=reply_markup,
        )
    except telegram.error.Forbidden:
        # Пользователь заблокировал бота
        User.objects.filter(telegram_id=chat_id).update(
            telegram_id=None,
        )
    except Exception as exc:
        self.retry(exc=exc, countdown=30)


@shared_task
def send_link_code_task(chat_id, code):
    """
    Отправить код привязки аккаунта.
    """
    text = f"""
Привет! 👋

Для привязки аккаунта DOD перейдите на сайт и введите этот код:

🔑 <code>{code}</code>

Код действителен 10 минут.
    """.strip()

    send_telegram_message_task.delay(
        chat_id=chat_id,
        text=text,
    )
