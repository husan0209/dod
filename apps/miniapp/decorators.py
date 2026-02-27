import functools
from django.http import JsonResponse
from django.shortcuts import redirect


def require_telegram_auth(view_func):
    """
    Декоратор: только авторизованные через Telegram.

    Использование:
    @require_telegram_auth
    def my_view(request):
        tg_user = request.telegram_user
        ...
    """
    @functools.wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.is_telegram_miniapp:
            return JsonResponse(
                {'error': 'Доступно только из Telegram'},
                status=403
            )
        if not request.telegram_user:
            return JsonResponse(
                {'error': 'Авторизация не пройдена'},
                status=401
            )
        if not request.telegram_user.is_linked():
            return redirect('miniapp:link-account')

        return view_func(request, *args, **kwargs)
    return wrapper


def require_linked_account(view_func):
    """
    Требует привязанный аккаунт DOD.
    Если не привязан → редирект на привязку.
    """
    @functools.wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not hasattr(request, 'telegram_user'):
            return redirect('miniapp:home')
        if not request.telegram_user.is_linked():
            return redirect('miniapp:link-account')
        return view_func(request, *args, **kwargs)
    return wrapper
