from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST

from apps.telegram_bot.services import TelegramBotService


@login_required
def telegram_settings(request):
    """Страница привязки Telegram аккаунта."""
    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'generate_code':
            code = TelegramBotService.generate_link_code(request.user)
            return JsonResponse({'code': code})

        elif action == 'unlink':
            TelegramBotService.unlink_account(request.user)
            messages.success(request, 'Telegram аккаунт отвязан.')
            return redirect('accounts:telegram_settings')

    context = {
        'telegram_linked': bool(request.user.telegram_id),
        'telegram_username': None,  # TODO: get from linked account
    }

    return render(request, 'accounts/telegram_settings.html', context)


@login_required
@require_POST
def link_telegram(request):
    """API для привязки Telegram по коду."""
    code = request.POST.get('code')
    if not code:
        return JsonResponse({'success': False, 'error': 'Код не указан'})

    user, error = TelegramBotService.verify_link_code(code.upper(), None)  # telegram_id will be set in service
    if user:
        return JsonResponse({'success': True})
    else:
        return JsonResponse({'success': False, 'error': error})


def health(request):
    return JsonResponse({"status": "ok"})
