from celery import shared_task
from django.utils import timezone
from django.db.models import Sum, Count
from decimal import Decimal

from .models import PredictionMarket, PriceHistory, MarketComment, MarketLike, Position, Trade
from .services import MarketService, ResolutionService


@shared_task(bind=True)
def close_expired_markets(self):
    """
    Закрыть маркеты, у которых close_date < now.
    Запускается каждый час.
    """
    try:
        expired_count = MarketService.close_expired_markets()
        return {
            "status": "success",
            "closed_count": expired_count,
            "timestamp": timezone.now().isoformat()
        }
    except Exception as e:
        self.retry(exc=e, countdown=60)


@shared_task(bind=True)
def update_volume_24h(self):
    """
    Обновить volume_24h для всех активных маркетов.
    Запускается каждые 30 минут.
    """
    try:
        one_day_ago = timezone.now() - timezone.timedelta(days=1)
        updated = 0

        markets = PredictionMarket.objects.filter(status='active')
        for market in markets:
            volume_24h = PriceHistory.objects.filter(
                market=market,
                timestamp__gte=one_day_ago
            ).aggregate(total=Sum('volume'))['total'] or Decimal('0')

            if market.volume_24h_usd != volume_24h:
                market.volume_24h_usd = volume_24h
                market.save(update_fields=['volume_24h_usd'])
                updated += 1

        return {
            "status": "success",
            "updated_count": updated,
            "total_markets": markets.count()
        }
    except Exception as e:
        self.retry(exc=e, countdown=60)


@shared_task(bind=True)
def record_periodic_prices(self):
    """
    Записать текущие цены каждые 5 минут.
    Для истории графиков.
    """
    try:
        markets = PredictionMarket.objects.filter(status='active')
        recorded = 0

        for market in markets:
            PriceHistory.objects.create(
                market=market,
                yes_price=market.yes_price,
                no_price=market.no_price,
                volume=Decimal('0'),
                source='periodic'
            )
            recorded += 1

        return {
            "status": "success",
            "recorded_count": recorded
        }
    except Exception as e:
        self.retry(exc=e, countdown=60)


@shared_task(bind=True)
def calculate_trending_markets(self):
    """
    Пересчитать трендовые маркеты.
    Запускается каждый час в фоне.
    """
    try:
        # Маркеты с наибольшим volume за последние 24 часа
        one_day_ago = timezone.now() - timezone.timedelta(days=1)
        
        trending = PredictionMarket.objects.filter(
            status='active'
        ).annotate(
            volume_24h_sum=Sum('prichistory__volume', 
                             filter=Trade.objects.filter(created_at__gte=one_day_ago))
        ).order_by('-volume_24h_sum')[:20]

        for market in trending:
            market.is_trending = True
            market.save(update_fields=['is_trending'])

        # Очистить старые трендовые маркеты
        PredictionMarket.objects.filter(
            status='active',
            is_trending=True
        ).exclude(id__in=[m.id for m in trending]).update(is_trending=False)

        return {
            "status": "success",
            "trending_count": len(trending)
        }
    except Exception as e:
        self.retry(exc=e, countdown=60)


@shared_task(bind=True)
def cleanup_expired_positions(self):
    """
    Очистить старые закрытые позиции (архив).
    Запускается раз в день в 2 ночи.
    """
    try:
        # Позиции которые:
        # - settled (разрешены)
        # - старше 90 дней
        # - нулевой баланс
        old_date = timezone.now() - timezone.timedelta(days=90)
        
        old_positions = Position.objects.filter(
            is_settled=True,
            shares=Decimal('0'),
            updated_at__lt=old_date
        )
        
        count = old_positions.count()
        # old_positions.delete()  # Можно архивировать вместо удаления
        
        return {
            "status": "success",
            "cleaned_count": count
        }
    except Exception as e:
        self.retry(exc=e, countdown=60)


@shared_task(bind=True)
def delete_old_comments(self):
    """
    Удалить помеченные как deleted комментарии старше 30 дней.
    Запускается раз в день.
    """
    try:
        old_date = timezone.now() - timezone.timedelta(days=30)
        
        old_comments = MarketComment.objects.filter(
            is_deleted=True,
            updated_at__lt=old_date
        )
        
        count = old_comments.count()
        old_comments.delete()
        
        return {
            "status": "success",
            "deleted_count": count
        }
    except Exception as e:
        self.retry(exc=e, countdown=60)


@shared_task(bind=True)
def send_market_closing_notifications(self):
    """
    Отправить уведомления за 24 часа до закрытия маркета.
    Запускается каждый час.
    """
    try:
        # Маркеты которые закрываются через 24 часа ±1 час
        now = timezone.now()
        one_day_ahead = now + timezone.timedelta(hours=24)
        margin = timezone.timedelta(hours=1)

        markets = PredictionMarket.objects.filter(
            status='active',
            close_date__gte=one_day_ahead - margin,
            close_date__lte=one_day_ahead + margin,
        )

        notified = 0
        for market in markets:
            # Найти всех трейдеров с позициями на этом маркете
            traders = Position.objects.filter(
                market=market, shares__gt=0
            ).values('user').distinct()

            for trader_dict in traders:
                # send_notification(trader_dict['user'], 
                #   f"Market '{market.question}' closes in 24 hours")
                notified += 1

        return {
            "status": "success",
            "notified_count": notified,
            "market_count": markets.count()
        }
    except Exception as e:
        self.retry(exc=e, countdown=60)


@shared_task(bind=True)
def update_market_statistics(self):
    """
    Пересчитать статистику маркета.
    Запускается каждые 30 минут.
    """
    try:
        updated = 0
        
        for market in PredictionMarket.objects.filter(status='active'):
            # Пересчитать количество трейдов и объём
            trades = Trade.objects.filter(market=market)
            positions = Position.objects.filter(market=market, shares__gt=0)
            
            market.trades_count = trades.count()
            market.volume_usd = trades.aggregate(Sum('total_cost'))['total_cost__sum'] or Decimal('0')
            
            market.save(update_fields=['trades_count', 'volume_usd'])
            updated += 1

        return {
            "status": "success",
            "updated_count": updated
        }
    except Exception as e:
        self.retry(exc=e, countdown=60)


@shared_task(bind=True)
def generate_market_report(self, market_id):
    """
    Генерировать отчёт по маркету.
    Запускается по требованию или по расписанию для трендовых маркетов.
    """
    try:
        market = PredictionMarket.objects.get(id=market_id)
        
        report = {
            "market_id": str(market.id),
            "question": market.question,
            "status": market.status,
            "yes_price": float(market.yes_price),
            "no_price": float(market.no_price),
            "volume_usd": float(market.volume_usd),
            "volume_24h_usd": float(market.volume_24h_usd or 0),
            "trades_count": market.trades_count,
            "positions_count": Position.objects.filter(market=market, shares__gt=0).count(),
            "traders_count": Position.objects.filter(market=market, shares__gt=0).values('user').distinct().count(),
            "comments_count": MarketComment.objects.filter(market=market, is_deleted=False).count(),
            "likes_count": MarketLike.objects.filter(market=market).count(),
            "created_at": market.created_at.isoformat(),
            "close_date": market.close_date.isoformat() if market.close_date else None,
            "resolution": market.resolution if market.resolution else None,
        }
        
        return {
            "status": "success",
            "report": report
        }
    except PredictionMarket.DoesNotExist:
        return {
            "status": "error",
            "message": f"Market {market_id} not found"
        }
    except Exception as e:
        self.retry(exc=e, countdown=60)


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
