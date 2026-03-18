from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.utils import timezone
from decimal import Decimal
import json

from .models import GameType, GameSession, CrashGame, UserSeed, CasinoSettings
from .services import ProvablyFairService, CasinoService
from .games.crash import CrashGameImpl as CrashGameLogic
from .games.slots import SlotsGame
from .games.roulette import RouletteGame
from .games.mines import MinesGame
from .games.dice import DiceGame
from .games.plinko import PlinkoGame


@login_required
def index(request):
    """Главная страница казино"""
    game_types = GameType.objects.filter(is_active=True).order_by('sort_order')
    settings = CasinoSettings.get_settings()
    
    context = {
        'game_types': game_types,
        'settings': settings,
    }
    return render(request, 'casino/index.html', context)


@login_required
def crash(request):
    """Страница Crash"""
    settings = CasinoSettings.get_settings()
    if not settings.crash_enabled:
        messages.error(request, "Crash временно недоступен")
        return redirect('casino:index')
    
    # Получить текущий активный раунд
    current_round = CrashGame.objects.filter(status='waiting').first()
    if not current_round:
        current_round = CrashGameLogic.create_round()
    
    context = {
        'current_round': current_round,
        'settings': settings,
    }
    return render(request, 'casino/crash.html', context)


@require_POST
@login_required
def crash_play(request):
    """Сыграть в Crash"""
    try:
        bet_amount = Decimal(request.POST.get('bet_amount', 0))
        auto_cashout = request.POST.get('auto_cashout')
        if auto_cashout:
            auto_cashout = Decimal(auto_cashout)
        
        currency_code = request.POST.get('currency', 'USD')
        
        # Валидация
        if bet_amount <= 0:
            return JsonResponse({'error': 'Неверная сумма ставки'}, status=400)
        
        # Сыграть
        result = CrashGameLogic.place_bet(
            user=request.user,
            bet_amount=bet_amount,
            currency_code=currency_code,
            auto_cashout=auto_cashout
        )
        
        return JsonResponse(result)
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def slots(request):
    """Страница Slots"""
    settings = CasinoSettings.get_settings()
    if not settings.slots_enabled:
        messages.error(request, "Slots временно недоступен")
        return redirect('casino:index')
    
    context = {
        'settings': settings,
    }
    return render(request, 'casino/slots.html', context)


@require_POST
@login_required
def slots_play(request):
    """Сыграть в Slots"""
    try:
        bet_amount = Decimal(request.POST.get('bet_amount', 0))
        currency_code = request.POST.get('currency', 'USD')
        
        if bet_amount <= 0:
            return JsonResponse({'error': 'Неверная сумма ставки'}, status=400)
        
        game = SlotsGame()
        session = game.play(request.user, bet_amount, currency_code)
        
        return JsonResponse({
            'game_id': session.game_id,
            'result': session.game_data,
            'win_amount': str(session.win_amount),
            'multiplier': str(session.win_multiplier),
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def roulette(request):
    """Страница Roulette"""
    settings = CasinoSettings.get_settings()
    if not settings.roulette_enabled:
        messages.error(request, "Roulette временно недоступен")
        return redirect('casino:index')
    
    context = {
        'settings': settings,
    }
    return render(request, 'casino/roulette.html', context)


@require_POST
@login_required
def roulette_play(request):
    """Сыграть в Roulette"""
    try:
        bets_data = json.loads(request.POST.get('bets', '[]'))
        currency_code = request.POST.get('currency', 'USD')
        
        if not bets_data:
            return JsonResponse({'error': 'Нет ставок'}, status=400)
        
        game = RouletteGame()
        session = game.play(request.user, bets_data, currency_code)
        
        return JsonResponse({
            'game_id': session.game_id,
            'result': session.game_data,
            'win_amount': str(session.win_amount),
            'multiplier': str(session.win_multiplier),
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def mines(request):
    """Страница Mines"""
    settings = CasinoSettings.get_settings()
    if not settings.mines_enabled:
        messages.error(request, "Mines временно недоступен")
        return redirect('casino:index')
    
    context = {
        'settings': settings,
    }
    return render(request, 'casino/mines.html', context)


@require_POST
@login_required
def mines_start(request):
    """Начать игру Mines"""
    try:
        bet_amount = Decimal(request.POST.get('bet_amount', 0))
        mines_count = int(request.POST.get('mines_count', 5))
        currency_code = request.POST.get('currency', 'USD')
        
        if bet_amount <= 0 or not (1 <= mines_count <= 24):
            return JsonResponse({'error': 'Неверные параметры'}, status=400)
        
        game = MinesGame()
        session = game.start_game(request.user, bet_amount, mines_count, currency_code)
        
        return JsonResponse({
            'game_session_id': str(session.id),
            'field_size': session.game_data['field_size'],
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@require_POST
@login_required
def mines_reveal(request):
    """Открыть клетку в Mines"""
    try:
        game_session_id = request.POST.get('game_session_id')
        cell_index = int(request.POST.get('cell', 0))
        
        game = MinesGame()
        result = game.reveal_cell(game_session_id, cell_index, request.user)
        
        return JsonResponse(result)
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@require_POST
@login_required
def mines_cashout(request):
    """Забрать деньги в Mines"""
    try:
        game_session_id = request.POST.get('game_session_id')
        
        game = MinesGame()
        session = game.cashout_mines(game_session_id, request.user)
        
        return JsonResponse({
            'win_amount': str(session.win_amount),
            'multiplier': str(session.win_multiplier),
            'mines_positions': session.game_data.get('mines_positions', []),
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def dice(request):
    """Страница Dice"""
    settings = CasinoSettings.get_settings()
    if not settings.dice_enabled:
        messages.error(request, "Dice временно недоступен")
        return redirect('casino:index')
    
    context = {
        'settings': settings,
    }
    return render(request, 'casino/dice.html', context)


@require_POST
@login_required
def dice_calculate(request):
    """Пересчитать множитель для Dice"""
    try:
        target = Decimal(request.POST.get('target', 50))
        condition = request.POST.get('condition', 'over')
        bet_amount = Decimal(request.POST.get('bet_amount', 0))
        
        # Расчёт
        win_chance = (99.99 - target) if condition == 'over' else target
        multiplier = Decimal('98.0') / win_chance
        win_amount = bet_amount * multiplier
        
        return JsonResponse({
            'win_chance': f"{win_chance:.2f}",
            'multiplier': f"{multiplier:.2f}",
            'win_amount': f"{win_amount:.2f}",
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@require_POST
@login_required
def dice_play(request):
    """Сыграть в Dice"""
    try:
        bet_amount = Decimal(request.POST.get('bet_amount', 0))
        target = Decimal(request.POST.get('target', 50))
        condition = request.POST.get('condition', 'over')
        currency_code = request.POST.get('currency', 'USD')
        
        if bet_amount <= 0 or not (0.01 <= target <= 99.98):
            return JsonResponse({'error': 'Неверные параметры'}, status=400)
        
        game = DiceGame()
        session = game.play(request.user, bet_amount, target, condition, currency_code)
        
        return JsonResponse({
            'game_id': session.game_id,
            'result': session.game_data,
            'win_amount': str(session.win_amount),
            'multiplier': str(session.win_multiplier),
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def plinko(request):
    """Страница Plinko"""
    settings = CasinoSettings.get_settings()
    if not settings.plinko_enabled:
        messages.error(request, "Plinko временно недоступен")
        return redirect('casino:index')
    
    context = {
        'settings': settings,
    }
    return render(request, 'casino/plinko.html', context)


@require_POST
@login_required
def plinko_play(request):
    """Сыграть в Plinko"""
    try:
        bet_amount = Decimal(request.POST.get('bet_amount', 0))
        rows = int(request.POST.get('rows', 16))
        risk = request.POST.get('risk', 'medium')
        currency_code = request.POST.get('currency', 'USD')
        
        if bet_amount <= 0 or rows not in (8, 12, 16) or risk not in ('low', 'medium', 'high'):
            return JsonResponse({'error': 'Неверные параметры'}, status=400)
        
        game = PlinkoGame()
        session = game.play(request.user, bet_amount, rows, risk, currency_code)
        
        return JsonResponse({
            'game_id': session.game_id,
            'result': session.game_data,
            'win_amount': str(session.win_amount),
            'multiplier': str(session.win_multiplier),
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def fairness(request):
    """Страница проверки честности"""
    user_seed = ProvablyFairService.get_or_create_user_seed(request.user)
    sessions = GameSession.objects.filter(user=request.user, status__in=['won', 'lost']).order_by('-started_at')[:20]
    
    context = {
        'user_seed': user_seed,
        'sessions': sessions,
    }
    return render(request, 'casino/fairness.html', context)


@require_POST
@login_required
def fairness_verify(request):
    """Проверить честность игры"""
    try:
        server_seed = request.POST.get('server_seed')
        client_seed = request.POST.get('client_seed')
        nonce = int(request.POST.get('nonce'))
        game_type = request.POST.get('game_type')
        game_data = json.loads(request.POST.get('game_data', '{}'))
        
        result = ProvablyFairService.verify_game(server_seed, '', client_seed, nonce, game_type, game_data)
        
        return JsonResponse(result)
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@require_POST
@login_required
def fairness_change_seed(request):
    """Сменить серверный seed"""
    try:
        result = ProvablyFairService.rotate_server_seed(request.user)
        return JsonResponse(result)
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@require_POST
@login_required
def fairness_change_client_seed(request):
    """Сменить клиентский seed"""
    try:
        new_client_seed = request.POST.get('client_seed')
        if not new_client_seed:
            return JsonResponse({'error': 'Seed не может быть пустым'}, status=400)
        
        ProvablyFairService.change_client_seed(request.user, new_client_seed)
        return JsonResponse({'success': True})
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def history(request):
    """История игр"""
    game_type_filter = request.GET.get('game_type')
    period_filter = request.GET.get('period', '7d')
    result_filter = request.GET.get('result')
    
    queryset = GameSession.objects.filter(user=request.user)
    
    if game_type_filter:
        queryset = queryset.filter(game_type__code=game_type_filter)
    
    if result_filter == 'won':
        queryset = queryset.filter(status='won')
    elif result_filter == 'lost':
        queryset = queryset.filter(status='lost')
    
    # Период
    from datetime import timedelta
    if period_filter == '1d':
        since = timezone.now() - timedelta(days=1)
    elif period_filter == '7d':
        since = timezone.now() - timedelta(days=7)
    elif period_filter == '30d':
        since = timezone.now() - timedelta(days=30)
    else:
        since = timezone.now() - timedelta(days=7)
    
    queryset = queryset.filter(started_at__gte=since)
    
    sessions = queryset.order_by('-started_at')[:100]
    
    context = {
        'sessions': sessions,
        'game_type_filter': game_type_filter,
        'period_filter': period_filter,
        'result_filter': result_filter,
    }
    return render(request, 'casino/history.html', context)


import uuid
import requests
from django.core.cache import cache
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse

@login_required
def local_game_play(request, game_id):
    """Страница локальной игры (ViperPro/Canada)"""
    game = get_object_or_404(GameType, code=game_id)
    
    # 1. Generate SSO Token for the PHP backend
    sso_token = str(uuid.uuid4())
    cache.set(f"casino_sso_{sso_token}", request.user.id, timeout=300) # 5 mins
    
    # 2. Determine base static path
    from django.conf import settings
    import os, json
    config_path = r"D:\casino-full_stack\frontend\public\games-config.json"
    game_url = ""
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            games_data = json.load(f)
            for g in games_data:
                if g['id'] == game.code:
                    game_url = f"/static/{g['gamePath']}"
                    break
    except Exception:
        pass
    
    if not game_url:
        if game.code.startswith('viperpro-'):
            folder = game.code.replace('viperpro-', '')
            game_url = f"/static/games/viperpro-games/{folder}/index.html"
        elif game.code.startswith('canada-'):
            folder = game.code.replace('canada-', '')
            game_url = f"/static/games/canada-games/{folder}/index.html"
    
    # 3. Add SSO token and user mapping to context
    # We will pass these to the wrapper so it can set them in the session/cookies of the iframe if needed
    # or just pass it in the URL if the PHP engine expects it.
    game_url_with_token = f"{game_url}?sessionId={sso_token}&user_id={request.user.id}"
    
    context = {
        'game': game,
        'game_url': game_url_with_token,
        'sso_token': sso_token,
        'user_id': request.user.id
    }
    return render(request, 'casino/local_game_wrapper.html', context)

@csrf_exempt
@login_required
def game_proxy(request, game):
    """
    Proxies requests from the frontend game to the PHP Math Engine.
    E.g. POST /game/Africa/server -> http://localhost:8001/game/Africa/server
    """
    engine_url = f"http://localhost:8001/game/{game}/server"
    
    # Forward the session ID (SSO Token)
    session_id = request.GET.get('sessionId')
    
    try:
        # Re-post to PHP engine
        response = requests.post(
            engine_url,
            params=request.GET,
            data=request.body,
            headers={
                'Content-Type': request.headers.get('Content-Type'),
                'X-DOD-Proxy': 'true'
            },
            timeout=10
        )
        
        return HttpResponse(
            content=response.content,
            status=response.status_code,
            content_type=response.headers.get('Content-Type')
        )
    except Exception as e:
        return JsonResponse({'error': f"Math Engine connection failed: {e}"}, status=502)

