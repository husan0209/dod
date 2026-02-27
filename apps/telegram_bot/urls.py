"""
URLs для Telegram бота.
"""

from django.urls import path
from . import webhook

app_name = 'telegram_bot'

urlpatterns = [
    path('webhook/', webhook.telegram_webhook, name='webhook'),
]
