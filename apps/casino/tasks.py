from celery import shared_task
from django.core.cache import cache
from django.utils import timezone
from decimal import Decimal
from .models import GameSession, CrashGame, CasinoSettings
from .services import CasinoService
from .games import CrashGame as CrashGameLogic
import logging

logger = logging.getLogger(__name__)


@shared_task
def update_live_feed():
    """Обновить живую ленту ставок и выигрышей каждые 5 секунд"""
    # Последние ставки
    recent_bets = GameSession.objects.filter(
        started_at__gte=timezone.now() - timezone.timedelta(minutes=5)
    ).order_by('-started_at')[:50].values(
        'game_id', 'user__username', 'game_type__name', 'bet_amount', 'win_amount', 'started_at'
    )
    
    # Большие выигрыши
    big_wins = GameSession.objects.filter(
        win_amount__gte=Decimal('100'),  # Настраиваемый порог
        started_at__gte=timezone.now() - timezone.timedelta(hours=24)
    ).order_by('-win_amount')[:20].values(
        'user__username', 'win_amount', 'game_type__name', 'started_at'
    )
    
    # Кэшировать в Redis
    cache.set('casino_recent_bets', list(recent_bets), 300)  # 5 мин
    cache.set('casino_big_wins', list(big_wins), 300)


@shared_task
def crash_game_loop():
    """Основной цикл Crash игр"""
    settings = CasinoSettings.get_settings()
    if not settings.is_enabled or not settings.crash_enabled:
        return
    
    # Проверить активные раунды
    active_rounds = CrashGame.objects.filter(status__in=['waiting', 'running'])
    
    # Если нет активных, создать новый
    if not active_rounds.exists():
        try:
            CrashGameLogic.create_round()
        except Exception as e:
            logger.error(f"Failed to create crash round: {e}")
    
    # Обработать завершившиеся раунды
    crashed_rounds = CrashGame.objects.filter(status='crashed', crashed_at__isnull=True)
    for round_obj in crashed_rounds:
        try:
            CrashGameLogic.end_round(str(round_obj.id))
        except Exception as e:
            logger.error(f"Failed to end crash round {round_obj.round_id}: {e}")


@shared_task
def update_game_statistics():
    """Обновить статистику игр каждые 30 минут"""
    from django.db.models import Sum, Count
    
    game_types = GameType.objects.all()
    for game_type in game_types:
        stats = GameSession.objects.filter(game_type=game_type).aggregate(
            total_bets=Count('id'),
            total_wagered=Sum('bet_amount_usd'),
            total_won=Sum('win_amount')
        )
        
        game_type.total_bets = stats['total_bets'] or 0
        game_type.total_wagered_usd = stats['total_wagered'] or Decimal('0')
        game_type.total_won_usd = stats['total_won'] or Decimal('0')
        game_type.save()


@shared_task
def daily_casino_report():
    """Ежедневный отчёт казино"""
    yesterday = timezone.now().date() - timezone.timedelta(days=1)
    
    sessions = GameSession.objects.filter(started_at__date=yesterday)
    
    total_bets = sessions.count()
    total_wagered = sessions.aggregate(Sum('bet_amount_usd'))['bet_amount_usd__sum'] or 0
    total_won = sessions.aggregate(Sum('win_amount'))['win_amount__sum'] or 0
    ggr = Decimal(total_wagered) - Decimal(total_won)
    
    biggest_win = sessions.order_by('-win_amount').first()
    
    unique_players = sessions.values('user').distinct().count()
    
    # RTP по играм
    rtp_data = {}
    for game_type in GameType.objects.all():
        game_sessions = sessions.filter(game_type=game_type)
        if game_sessions.exists():
            game_wagered = game_sessions.aggregate(Sum('bet_amount_usd'))['bet_amount_usd__sum'] or 0
            game_won = game_sessions.aggregate(Sum('win_amount'))['win_amount__sum'] or 0
            if game_wagered > 0:
                actual_rtp = (game_won / game_wagered) * 100
                expected_rtp = game_type.rtp
                rtp_data[game_type.name] = {
                    'actual': actual_rtp,
                    'expected': expected_rtp,
                    'diff': abs(actual_rtp - expected_rtp)
                }
    
    # Отправить отчёт (email, лог, etc.)
    logger.info(f"Daily casino report for {yesterday}: GGR={ggr}, Bets={total_bets}, Players={unique_players}")


@shared_task
def cleanup_inactive_mines_games():
    """Очистить зависшие Mines игры"""
    one_hour_ago = timezone.now() - timezone.timedelta(hours=1)
    
    inactive_games = GameSession.objects.filter(
        game_type__code='mines',
        status='active',
        started_at__lt=one_hour_ago
    )
    
    for game in inactive_games:
        try:
            # Авто-кэшаут если есть открытые клетки
            game_data = game.game_data
            if game_data.get('revealed'):
                win_amount = game.bet_amount * game_data.get('current_multiplier', 1)
                CasinoService.complete_game(game, win_amount, game_data)
            else:
                # Проигрыш
                CasinoService.complete_game(game, 0, game_data)
        except Exception as e:
            logger.error(f"Failed to cleanup mines game {game.game_id}: {e}")


@shared_task
def verify_rtp_integrity():
    """Проверить RTP integrity"""
    last_24h = timezone.now() - timezone.timedelta(hours=24)
    
    for game_type in GameType.objects.all():
        sessions = GameSession.objects.filter(
            game_type=game_type,
            started_at__gte=last_24h
        )
        
        if sessions.count() < 100:  # Минимальный объём для проверки
            continue
        
        total_wagered = sessions.aggregate(Sum('bet_amount_usd'))['bet_amount_usd__sum'] or 0
        total_won = sessions.aggregate(Sum('win_amount'))['win_amount__sum'] or 0
        
        if total_wagered > 0:
            actual_rtp = (total_won / total_wagered) * 100
            expected_rtp = game_type.rtp
            
            if abs(actual_rtp - expected_rtp) > 5:  # 5% отклонение
                logger.warning(f"RTP anomaly for {game_type.name}: expected {expected_rtp}%, actual {actual_rtp}%")
