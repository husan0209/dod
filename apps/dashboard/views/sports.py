from datetime import timedelta
from decimal import Decimal

from django.contrib import messages
from django.core.paginator import Paginator
from django.db import models
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.accounts.models import AdminActionLog
from apps.dashboard.decorators import require_permission
from apps.sports.models import (
    Sport, League, Event, Market, Outcome, Bet, BetItem, BetSettings
)


@require_permission('sports', 'view')
def sports_overview(request):
    """Sports management overview with real data."""
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Real metrics
    active_events = Event.objects.filter(
        status__in=['prematch', 'live', 'scheduled']
    ).count()

    live_matches = Event.objects.filter(status='live').count()

    bets_today_stats = Bet.objects.filter(
        created_at__gte=today_start
    ).aggregate(
        count=models.Count('id'),
        total_stake=models.Sum('stake_usd'),
        total_win=models.Sum('actual_win', filter=models.Q(status='won')),
    )

    bets_count = bets_today_stats['count'] or 0
    bets_stake = bets_today_stats['total_stake'] or Decimal('0')
    bets_wins = bets_today_stats['total_win'] or Decimal('0')
    ggr_sports = bets_stake - bets_wins

    # Pending settlement
    pending_settlement = Event.objects.filter(
        status='finished', settled_at__isnull=True
    ).count()

    # Recent events
    recent_events = Event.objects.select_related(
        'sport', 'league', 'home_team', 'away_team'
    ).order_by('-start_time')[:10]

    # Sports summary
    sports_list = Sport.objects.filter(is_active=True).annotate(
        active_events=models.Count(
            'events',
            filter=models.Q(events__status__in=['prematch', 'live'])
        ),
        today_bets=models.Count(
            'events__bet_items__bet',
            filter=models.Q(events__bet_items__bet__created_at__gte=today_start),
            distinct=True,
        ),
    ).order_by('-active_events')[:8]

    # Recent bets
    recent_bets = Bet.objects.select_related(
        'user', 'currency'
    ).order_by('-created_at')[:10]

    context = {
        'active_events': active_events,
        'live_matches': live_matches,
        'bets_today': bets_count,
        'bets_stake_today': bets_stake,
        'ggr_sports': ggr_sports,
        'pending_settlement': pending_settlement,
        'recent_events': recent_events,
        'sports_list': sports_list,
        'recent_bets': recent_bets,
    }

    return render(request, 'dashboard/sports/overview.html', context)


@require_permission('sports', 'view')
def events_list(request):
    """All sports events with filters."""
    status = request.GET.get('status', '')
    sport_id = request.GET.get('sport', '')
    search = request.GET.get('q', '').strip()

    qs = Event.objects.select_related(
        'sport', 'league', 'home_team', 'away_team'
    ).order_by('-start_time')

    if status:
        qs = qs.filter(status=status)
    if sport_id:
        qs = qs.filter(sport_id=sport_id)
    if search:
        qs = qs.filter(
            models.Q(name__icontains=search) |
            models.Q(home_team__name__icontains=search) |
            models.Q(away_team__name__icontains=search)
        )

    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))
    sports = Sport.objects.filter(is_active=True)

    context = {
        'page_obj': page_obj,
        'status_filter': status,
        'sport_filter': sport_id,
        'search_query': search,
        'sports': sports,
    }

    return render(request, 'dashboard/sports/events.html', context)


@require_permission('sports', 'view')
def event_detail(request, event_id):
    """Detailed view of a single event with markets and bets."""
    event = get_object_or_404(
        Event.objects.select_related(
            'sport', 'league', 'home_team', 'away_team'
        ),
        id=event_id,
    )

    markets = Market.objects.filter(event=event).prefetch_related('outcomes')
    bets = BetItem.objects.filter(event=event).select_related(
        'bet__user', 'bet__currency'
    ).order_by('-bet__created_at')[:50]

    bet_stats = bets.aggregate(
        total_stake=models.Sum('bet__stake_usd'),
        count=models.Count('id'),
    )

    context = {
        'event': event,
        'markets': markets,
        'bets': bets,
        'total_stake': bet_stats['total_stake'] or 0,
        'bets_count': bet_stats['count'] or 0,
    }

    return render(request, 'dashboard/sports/event_detail.html', context)


@require_permission('sports', 'settle_bets')
@require_POST
def event_settle(request, event_id):
    """Set event result and settle bets."""
    event = get_object_or_404(Event, id=event_id)
    home_score = request.POST.get('home_score')
    away_score = request.POST.get('away_score')

    if home_score is None or away_score is None:
        messages.error(request, 'Укажите счет обеих команд')
        return redirect('dashboard:sports_event_detail', event_id=event_id)

    data_before = {
        'status': event.status,
        'home_score': event.home_score,
        'away_score': event.away_score,
    }

    event.home_score = int(home_score)
    event.away_score = int(away_score)
    event.status = 'finished'
    event.settled_at = timezone.now()
    event.settled_by = request.user
    event.save()

    # Log action
    AdminActionLog.objects.create(
        admin_user=request.user,
        action_type='event_settled',
        module='sports',
        action_category='settlement',
        description=f'Settled event {event.name}: {home_score}-{away_score}',
        ip_address=request.META.get('REMOTE_ADDR'),
        data_before=data_before,
        data_after={
            'status': 'finished',
            'home_score': int(home_score),
            'away_score': int(away_score),
        },
        is_successful=True,
    )

    messages.success(request, f'Событие "{event.name}" завершено. Счёт: {home_score}-{away_score}')
    return redirect('dashboard:sports_event_detail', event_id=event_id)


@require_permission('sports', 'view')
def bets_list(request):
    """All sports bets with filters."""
    status = request.GET.get('status', '')
    bet_type = request.GET.get('type', '')
    search = request.GET.get('q', '').strip()
    period = request.GET.get('period', 'today')

    qs = Bet.objects.select_related('user', 'currency').order_by('-created_at')

    now = timezone.now()
    if period == 'today':
        qs = qs.filter(created_at__date=now.date())
    elif period == 'week':
        qs = qs.filter(created_at__gte=now - timedelta(days=7))
    elif period == 'month':
        qs = qs.filter(created_at__gte=now - timedelta(days=30))

    if status:
        qs = qs.filter(status=status)
    if bet_type:
        qs = qs.filter(bet_type=bet_type)
    if search:
        qs = qs.filter(
            models.Q(bet_id__icontains=search) |
            models.Q(user__username__icontains=search) |
            models.Q(user__email__icontains=search)
        )

    paginator = Paginator(qs, 50)
    page_obj = paginator.get_page(request.GET.get('page'))

    summary = qs.aggregate(
        total_stake=models.Sum('stake_usd'),
        total_win=models.Sum('actual_win'),
        count=models.Count('id'),
    )

    context = {
        'page_obj': page_obj,
        'status_filter': status,
        'type_filter': bet_type,
        'period_filter': period,
        'search_query': search,
        'total_stake': summary['total_stake'] or 0,
        'total_win': summary['total_win'] or 0,
        'total_count': summary['count'] or 0,
    }

    return render(request, 'dashboard/sports/bets.html', context)
