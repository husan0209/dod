"""
Django view для обработки webhook от Telegram.
"""

import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings
from telegram import Update
from .bot import application


@csrf_exempt
@require_POST
def telegram_webhook(request):
    """
    Обработка webhook от Telegram бота.
    """
    if not settings.TELEGRAM_BOT_TOKEN:
        return JsonResponse({'error': 'Bot token not configured'}, status=500)

    try:
        # Парсим update из Telegram
        data = json.loads(request.body.decode('utf-8'))
        update = Update.de_json(data, application.bot)

        # Обрабатываем update асинхронно
        application.update_queue.put_nowait(update)

        return JsonResponse({'ok': True})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
