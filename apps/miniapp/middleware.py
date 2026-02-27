import logging
from django.contrib.auth import login
from django.contrib.auth.models import AnonymousUser
from django.http import JsonResponse
from django.utils import timezone as now
from django.shortcuts import redirect

from apps.miniapp.services.auth_service import TelegramAuthService, generate_session_key, extract_platform
from apps.miniapp.models import MiniAppSession

logger = logging.getLogger(__name__)


class TelegramMiniAppMiddleware:
    """
    Middleware для всех запросов к /tg/.
    Проверяет и валидирует initData.
    Автоматически авторизует пользователя.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.path.startswith('/tg/'):
            return self.get_response(request)

        # Получить initData
        init_data = (
            request.headers.get('X-Telegram-Init-Data')
            or request.GET.get('initData')
            or request.POST.get('initData')
        )

        request.is_telegram_miniapp = bool(init_data)
        request.telegram_user = None

        if init_data:
            try:
                validated = TelegramAuthService.validate_init_data(
                    init_data
                )
                user, tg_user, is_new = (
                    TelegramAuthService.get_or_create_user(validated)
                )

                # Авторизовать в Django
                if user and user.is_active:
                    login(request, user)
                    request.telegram_user = tg_user

                    # Обновить статистику
                    tg_user.app_opens_count += 1
                    tg_user.last_app_open = now()
                    tg_user.save(update_fields=[
                        'app_opens_count', 'last_app_open'
                    ])

                    # Создать сессию Mini App
                    MiniAppSession.objects.create(
                        telegram_user=tg_user,
                        session_key=generate_session_key(),
                        init_data_hash=validated['hash'],
                        platform=extract_platform(request),
                        telegram_version=request.headers.get('X-Telegram-Version', ''),
                    )

            except ValueError as e:
                # Невалидные данные — не авторизуем
                logger.warning(
                    f'Invalid initData: {e}'
                )

        return self.get_response(request)
