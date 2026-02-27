from celery import shared_task
from django.utils import timezone
from django.db.models import Sum

from .models import PredictionMarket, PriceHistory
from .services import MarketService


@shared_task
def close_expired_markets():
    """Close markets where close_date < now and status == 'active'."""
    expired_count = MarketService.close_expired_markets()
    return f"Closed {expired_count} expired markets"


@shared_task
def update_volume_24h():
    """Update volume_24h for all active markets."""
    from django.db.models import Sum
    from django.utils import timezone

    one_day_ago = timezone.now() - timezone.timedelta(days=1)

    markets = PredictionMarket.objects.filter(status='active')
    for market in markets:
        volume_24h = PriceHistory.objects.filter(
            market=market,
            timestamp__gte=one_day_ago
        ).aggregate(total=Sum('volume'))['total'] or 0

        market.volume_24h_usd = volume_24h
        market.save(update_fields=['volume_24h_usd'])

    return f"Updated 24h volume for {markets.count()} markets"


@shared_task
def record_periodic_prices():
    """Record current prices every 15 minutes."""
    markets = PredictionMarket.objects.filter(status='active')
    for market in markets:
        PriceHistory.objects.create(
            market=market,
            yes_price=market.yes_price,
            no_price=market.no_price,
            volume=0,
            source='periodic'
        )

    return f"Recorded periodic prices for {markets.count()} markets"


@shared_task
def update_trending():
    """Update is_trending flag based on volume_24h."""
    # Reset all trending flags
    PredictionMarket.objects.filter(is_trending=True).update(is_trending=False)

    # Set top 10 by volume_24h as trending
    top_markets = PredictionMarket.objects.filter(
        status='active'
    ).order_by('-volume_24h_usd')[:10]

    for market in top_markets:
        market.is_trending = True
        market.save(update_fields=['is_trending'])

    return f"Updated trending status for {top_markets.count()} markets"


@shared_task
def notify_closing_soon():
    """Notify users with positions in markets closing in 24 hours."""
    soon = timezone.now() + timezone.timedelta(hours=24)
    markets = PredictionMarket.objects.filter(
        status='active',
        close_date__lte=soon,
        close_date__gt=timezone.now()
    )

    notifications_sent = 0
    for market in markets:
        positions = market.positions.filter(shares__gt=0)
        for position in positions:
            # Placeholder: send notification
            # notify_user(position.user, f"Market '{market.question[:50]}' closes soon!")
            notifications_sent += 1

    return f"Sent {notifications_sent} closing soon notifications"


@shared_task
def daily_prediction_report():
    """Generate daily report."""
    today = timezone.now().date()
    yesterday = today - timezone.timedelta(days=1)

    # Stats
    new_markets = PredictionMarket.objects.filter(created_at__date=today).count()
    resolved_markets = PredictionMarket.objects.filter(
        resolved_at__date=today
    ).count()
    total_volume = PriceHistory.objects.filter(
        timestamp__date=today
    ).aggregate(total=Sum('volume'))['total'] or 0

    # Placeholder: send report to admins
    report = f"""
    Daily Prediction Market Report - {today}

    New Markets: {new_markets}
    Resolved Markets: {resolved_markets}
    Total Volume: ${total_volume:.2f}

    Top Markets:
    """
    # Add top markets logic

    return report


@shared_task
def cleanup_old_price_history():
    """Delete PriceHistory older than 365 days."""
    cutoff = timezone.now() - timezone.timedelta(days=365)
    deleted, _ = PriceHistory.objects.filter(timestamp__lt=cutoff).delete()
    return f"Deleted {deleted} old price history records"


@shared_task
def check_resolution_overdue():
    """Check for markets pending resolution > 24 hours."""
    cutoff = timezone.now() - timezone.timedelta(hours=24)
    overdue = PredictionMarket.objects.filter(
        status='pending_resolution',
        close_date__lt=cutoff
    )

    alerts_sent = 0
    for market in overdue:
        # Placeholder: alert moderators
        # alert_moderators(f"Market {market.market_id} is overdue for resolution!")
        alerts_sent += 1

    return f"Sent {alerts_sent} overdue alerts"
