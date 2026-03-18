from datetime import timedelta
from decimal import Decimal

from django.core.paginator import Paginator
from django.db import models
from django.shortcuts import render, get_object_or_404
from django.utils import timezone

from apps.dashboard.decorators import require_permission
from apps.casino.models import (
    GameType, GameSession, CrashGame, CasinoSettings
)


@require_permission('casino', 'view')
def casino_overview(request):
    """Casino management overview with real data."""
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Active players (played in last 30 min)
    active_players = GameSession.objects.filter(
        started_at__gte=now - timedelta(minutes=30),
        status='active',
    ).values('user').distinct().count()

    # Today's metrics
    today_stats = GameSession.objects.filter(
        started_at__gte=today_start,
        status__in=['won', 'lost', 'cashout'],
    ).aggregate(
        rounds=models.Count('id'),
        total_wagered=models.Sum('bet_amount_usd'),
        total_won=models.Sum(
            'bet_amount_usd',
            filter=models.Q(status='won') | models.Q(status='cashout'),
        ) + models.Sum(
            models.F('win_amount') * models.F('currency__rate_to_usd'),
            output_field=models.DecimalField(max_digits=20, decimal_places=2),
            filter=models.Q(status='won') | models.Q(status='cashout'),
            default=Decimal('0'),
        ),
    )

    rounds_today = today_stats['rounds'] or 0
    total_wagered = today_stats['total_wagered'] or Decimal('0')

    # GGR per game type
    game_types = GameType.objects.filter(is_active=True).annotate(
        today_rounds=models.Count(
            'gamesession',
            filter=models.Q(gamesession__started_at__gte=today_start),
        ),
        today_wagered=models.Sum(
            'gamesession__bet_amount_usd',
            filter=models.Q(gamesession__started_at__gte=today_start),
            default=Decimal('0'),
        ),
    ).order_by('-today_wagered')

    # Recent big wins (>$100)
    big_wins = GameSession.objects.filter(
        status='won',
        win_multiplier__gte=5,
        started_at__gte=today_start,
    ).select_related('user', 'game_type', 'currency').order_by(
        '-win_multiplier'
    )[:10]

    # Recent crash rounds
    recent_crashes = CrashGame.objects.filter(
        status='crashed'
    ).order_by('-crashed_at')[:15]

    # Settings
    settings = CasinoSettings.get_settings()

    context = {
        'active_players': active_players,
        'rounds_today': rounds_today,
        'total_wagered': total_wagered,
        'game_types': game_types,
        'big_wins': big_wins,
        'recent_crashes': recent_crashes,
        'settings': settings,
    }

    return render(request, 'dashboard/casino/overview.html', context)


@require_permission('casino', 'view_rounds')
def rounds_list(request):
    """All casino game rounds with filters."""
    game = request.GET.get('game', '')
    status = request.GET.get('status', '')
    search = request.GET.get('q', '').strip()
    period = request.GET.get('period', 'today')

    qs = GameSession.objects.select_related(
        'user', 'game_type', 'currency'
    ).order_by('-started_at')

    now = timezone.now()
    if period == 'today':
        qs = qs.filter(started_at__date=now.date())
    elif period == 'week':
        qs = qs.filter(started_at__gte=now - timedelta(days=7))
    elif period == 'month':
        qs = qs.filter(started_at__gte=now - timedelta(days=30))

    if game:
        qs = qs.filter(game_type__code=game)
    if status:
        qs = qs.filter(status=status)
    if search:
        qs = qs.filter(
            models.Q(game_id__icontains=search) |
            models.Q(user__username__icontains=search)
        )

    paginator = Paginator(qs, 50)
    page_obj = paginator.get_page(request.GET.get('page'))

    summary = qs.aggregate(
        total_wagered=models.Sum('bet_amount_usd'),
        total_won=models.Sum(
            models.Case(
                models.When(
                    status__in=['won', 'cashout'],
                    then=models.F('bet_amount_usd') * models.F('win_multiplier'),
                ),
                default=Decimal('0'),
                output_field=models.DecimalField(max_digits=20, decimal_places=2),
            )
        ),
        count=models.Count('id'),
    )

    game_types = GameType.objects.filter(is_active=True)

    context = {
        'page_obj': page_obj,
        'game_filter': game,
        'status_filter': status,
        'period_filter': period,
        'search_query': search,
        'total_wagered': summary['total_wagered'] or 0,
        'total_won': summary['total_won'] or 0,
        'total_count': summary['count'] or 0,
        'game_types': game_types,
    }

    return render(request, 'dashboard/casino/rounds.html', context)


@require_permission('casino', 'view')
def crash_history(request):
    """Crash game rounds history."""
    qs = CrashGame.objects.filter(status='crashed').order_by('-crashed_at')

    paginator = Paginator(qs, 50)
    page_obj = paginator.get_page(request.GET.get('page'))

    stats = CrashGame.objects.filter(
        status='crashed',
        crashed_at__date=timezone.now().date(),
    ).aggregate(
        avg_crash=models.Avg('crash_point'),
        max_crash=models.Max('crash_point'),
        min_crash=models.Min('crash_point'),
        total_rounds=models.Count('id'),
        total_bet=models.Sum('total_bet'),
        total_payout=models.Sum('total_payout'),
    )

    context = {
        'page_obj': page_obj,
        'avg_crash': stats['avg_crash'] or 0,
        'max_crash': stats['max_crash'] or 0,
        'min_crash': stats['min_crash'] or 0,
        'total_rounds': stats['total_rounds'] or 0,
        'total_bet': stats['total_bet'] or 0,
        'total_payout': stats['total_payout'] or 0,
    }

    return render(request, 'dashboard/casino/crash_history.html', context)
