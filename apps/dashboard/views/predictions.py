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
from apps.predictions.models import PredictionMarket, Position, Trade


@require_permission('predictions', 'view')
def predictions_overview(request):
    """Predictions management overview with real data."""
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Active markets
    active_markets = PredictionMarket.objects.filter(
        status='active'
    ).count()

    # Awaiting resolution
    awaiting_resolution = PredictionMarket.objects.filter(
        status__in=['active', 'pending_resolution'],
        close_date__lt=now,
    ).count()

    # Today's trades
    today_trades = Trade.objects.filter(
        created_at__gte=today_start
    ).aggregate(
        count=models.Count('id'),
        volume=models.Sum('amount_usd'),
    )

    # Recently resolved
    recently_resolved = PredictionMarket.objects.filter(
        status='resolved',
        resolved_at__gte=now - timedelta(days=7),
    ).count()

    # Total volume
    total_volume = PredictionMarket.objects.filter(
        status__in=['active', 'resolved']
    ).aggregate(total=models.Sum('volume_usd'))['total'] or Decimal('0')

    # Market categories breakdown
    category_stats = PredictionMarket.objects.filter(
        status='active'
    ).values('category__name').annotate(
        count=models.Count('id'),
        total_volume=models.Sum('volume_usd'),
    ).order_by('-count')

    # Active markets list
    markets = PredictionMarket.objects.filter(
        status__in=['active', 'trading_halted', 'pending_resolution']
    ).select_related('category', 'created_by').order_by('-created_at')[:15]

    # Markets needing resolution
    needs_resolution = PredictionMarket.objects.filter(
        status__in=['active', 'pending_resolution'],
        close_date__lt=now,
    ).select_related('category').order_by('close_date')[:10]

    context = {
        'active_markets': active_markets,
        'awaiting_resolution': awaiting_resolution,
        'trades_today': today_trades['count'] or 0,
        'volume_today': today_trades['volume'] or Decimal('0'),
        'recently_resolved': recently_resolved,
        'category_stats': category_stats,
        'markets': markets,
        'needs_resolution': needs_resolution,
    }

    return render(request, 'dashboard/predictions/overview.html', context)


@require_permission('predictions', 'view')
def markets_list(request):
    """All prediction markets with filters."""
    status = request.GET.get('status', '')
    category = request.GET.get('category', '')
    search = request.GET.get('q', '').strip()

    qs = PredictionMarket.objects.select_related(
        'category', 'created_by'
    ).order_by('-created_at')

    if status:
        qs = qs.filter(status=status)
    if category:
        qs = qs.filter(category_id=category)
    if search:
        qs = qs.filter(
            models.Q(question__icontains=search) |
            models.Q(description__icontains=search)
        )

    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'page_obj': page_obj,
        'status_filter': status,
        'category_filter': category,
        'search_query': search,
    }

    return render(request, 'dashboard/predictions/markets.html', context)


@require_permission('predictions', 'resolve_markets')
def market_detail(request, market_id):
    """Market detail for admin review and resolution."""
    market = get_object_or_404(
        PredictionMarket.objects.select_related('category', 'created_by'),
        id=market_id,
    )

    positions = Position.objects.filter(
        market=market
    ).select_related('user').order_by('-amount')[:50]

    recent_trades = Trade.objects.filter(
        market=market
    ).select_related('user').order_by('-created_at')[:30]

    trade_stats = Trade.objects.filter(market=market).aggregate(
        total_volume=models.Sum('total_cost'),
        total_trades=models.Count('id'),
        unique_traders=models.Count('user', distinct=True),
    )

    context = {
        'market': market,
        'positions': positions,
        'recent_trades': recent_trades,
        'total_volume': trade_stats['total_volume'] or 0,
        'total_trades': trade_stats['total_trades'] or 0,
        'unique_traders': trade_stats['unique_traders'] or 0,
    }

    return render(request, 'dashboard/predictions/market_detail.html', context)


@require_permission('predictions', 'resolve_markets')
@require_POST
def market_resolve(request, market_id):
    """Resolve a prediction market."""
    market = get_object_or_404(PredictionMarket, id=market_id)
    outcome = request.POST.get('outcome')
    comment = request.POST.get('comment', '')

    if not outcome:
        messages.error(request, 'Выберите исход для резолюции')
        return redirect('dashboard:predictions_market_detail', market_id=market_id)

    data_before = {
        'status': market.status,
    }

    market.status = 'resolved'
    market.resolution = outcome
    market.resolved_at = timezone.now()
    market.resolved_by = request.user
    market.resolution_evidence = comment
    market.save()

    AdminActionLog.objects.create(
        admin_user=request.user,
        action_type='market_resolved',
        module='predictions',
        action_category='resolution',
        description=f'Resolved market "{market.question[:50]}" → {outcome}',
        ip_address=request.META.get('REMOTE_ADDR'),
        data_before=data_before,
        data_after={
            'status': 'resolved',
            'outcome': outcome,
        },
        is_successful=True,
    )

    messages.success(request, f'Маркет "{market.question[:50]}" резолвлен: {outcome}')
    return redirect('dashboard:predictions_market_detail', market_id=market_id)
