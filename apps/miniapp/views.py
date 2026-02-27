from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt

from .decorators import require_telegram_auth, require_linked_account


# Главная страница Mini App
@require_telegram_auth
def home(request):
    """Главная страница Telegram Mini App."""
    return render(request, 'miniapp/app.html')


# Авторизация
@require_telegram_auth
def link_account(request):
    """Страница привязки аккаунта."""
    return HttpResponse("Link Account")


@require_telegram_auth
def link_existing(request):
    """Привязка существующего аккаунта."""
    return HttpResponse("Link Existing")


@require_telegram_auth
def welcome(request):
    """Приветственная страница для новых пользователей."""
    return HttpResponse("Welcome")


# Кошелёк
@require_linked_account
def wallet_home(request):
    """Главная страница кошелька."""
    return render(request, 'miniapp/wallet/home.html')


@require_linked_account
def wallet_deposit(request):
    """Пополнение кошелька."""
    return render(request, 'miniapp/wallet/deposit.html')


@require_linked_account
def wallet_withdraw(request):
    """Вывод средств."""
    return render(request, 'miniapp/wallet/withdraw.html')


@require_linked_account
def wallet_history(request):
    """История транзакций."""
    return HttpResponse("Wallet History")


@require_linked_account
def wallet_convert(request):
    """Конвертация валют."""
    return HttpResponse("Wallet Convert")


# Спорт
@require_linked_account
def sports_home(request):
    """Главная страница ставок на спорт."""
    return render(request, 'miniapp/sports/home.html')


@require_linked_account
def sports_events(request, sport):
    """События по виду спорта."""
    return HttpResponse(f"Sports Events: {sport}")


@require_linked_account
def sports_event(request, event_id):
    """Детали события."""
    return HttpResponse(f"Sports Event: {event_id}")


@require_linked_account
def sports_place_bet(request):
    """Размещение ставки."""
    return HttpResponse("Place Bet")


@require_linked_account
def sports_my_bets(request):
    """Мои ставки."""
    return HttpResponse("My Bets")


# Казино
@require_linked_account
def casino_home(request):
    """Главная страница казино."""
    return render(request, 'miniapp/casino/home.html')


@require_linked_account
def casino_game(request, game):
    """Игра казино."""
    return HttpResponse(f"Casino Game: {game}")


# Predictions
@require_linked_account
def predictions_home(request):
    """Главная страница predictions."""
    return render(request, 'miniapp/predictions/home.html')


@require_linked_account
def predictions_market(request, market_id):
    """Детали рынка."""
    return HttpResponse(f"Predictions Market: {market_id}")


@require_linked_account
def predictions_trade(request):
    """Торговля на рынке."""
    return HttpResponse("Predictions Trade")


@require_linked_account
def predictions_portfolio(request):
    """Портфель predictions."""
    return HttpResponse("Predictions Portfolio")


# Профиль
@require_linked_account
def profile_home(request):
    """Главная страница профиля."""
    return render(request, 'miniapp/profile/home.html')


@require_linked_account
def profile_edit(request):
    """Редактирование профиля."""
    return HttpResponse("Profile Edit")


@require_linked_account
def profile_referral(request):
    """Реферальная система."""
    return HttpResponse("Profile Referral")


@require_linked_account
def profile_settings(request):
    """Настройки профиля."""
    return HttpResponse("Profile Settings")


# Поддержка
@require_linked_account
def support_home(request):
    """Главная страница поддержки."""
    return render(request, 'miniapp/support/home.html')


@require_linked_account
def support_new_ticket(request):
    """Новый тикет поддержки."""
    return HttpResponse("New Ticket")


@require_linked_account
def support_faq(request):
    """FAQ."""
    return HttpResponse("Support FAQ")


@require_linked_account
def api_live_matches(request):
    """API: live матчи для главной страницы."""
    # Mock data - would be from actual sports models
    matches = [
        {
            'id': 1,
            'home_team': 'Реал Мадрид',
            'away_team': 'Барселона',
            'score': '2:1',
            'minute': '67',
            'odds': {'1': 2.10, 'X': 3.40, '2': 3.80}
        },
        {
            'id': 2,
            'home_team': 'МанСити',
            'away_team': 'Ливерпуль',
            'score': '0:0',
            'minute': '23',
            'odds': {'1': 1.90, 'X': 3.60, '2': 4.20}
        }
    ]

    html = ""
    for match in matches:
        html += f'''
        <div class="tg-card">
            <div class="flex items-center justify-between mb-2">
                <div class="flex items-center space-x-2">
                    <span class="text-green-500">🟢</span>
                    <span class="font-medium">{match['home_team']} — {match['away_team']}</span>
                </div>
                <span class="text-sm text-tg-hint">{match['minute']}'</span>
            </div>
            <div class="text-center text-lg font-bold mb-2">{match['score']}</div>
            <div class="grid grid-3 gap-2 text-center text-sm">
                <button class="tg-btn tg-btn-outline py-2" onclick="haptic.light(); placeBet('1', {match['odds']['1']})">
                    1<br><span class="text-xs">{match['odds']['1']}</span>
                </button>
                <button class="tg-btn tg-btn-outline py-2" onclick="haptic.light(); placeBet('X', {match['odds']['X']})">
                    X<br><span class="text-xs">{match['odds']['X']}</span>
                </button>
                <button class="tg-btn tg-btn-outline py-2" onclick="haptic.light(); placeBet('2', {match['odds']['2']})">
                    2<br><span class="text-xs">{match['odds']['2']}</span>
                </button>
            </div>
        </div>
        '''

    return HttpResponse(html)


@require_linked_account
def api_notifications(request):
    """API: уведомления."""
    return JsonResponse({'notifications': []})


@require_linked_account
def api_balance(request):
    """API: баланс пользователя."""
    try:
        from apps.wallet.models import Wallet
        wallet = Wallet.objects.get(user=request.user)
        balance = wallet.get_total_balance_usd()
        return HttpResponse(f"💰 ${balance:.2f}")
    except:
        return HttpResponse("💰 $0.00")


@require_linked_account
def api_theme(request):
    """API: тема Telegram."""
    return JsonResponse({'theme': 'dark'})


# Webhook бота
@csrf_exempt
def bot_webhook(request):
    """Webhook для Telegram бота."""
    return JsonResponse({'status': 'ok'})
