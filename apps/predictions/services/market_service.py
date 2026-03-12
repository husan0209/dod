import random
from decimal import Decimal

from django.db.models import Q, Count, Sum
from django.utils import timezone

from ..models import PredictionMarket, MarketCategory, PredictionSettings, PriceHistory


def generate_id(prefix):
    """Генерировать уникальный ID."""
    timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
    random6 = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=6))
    return f"{prefix}-{timestamp}-{random6}"


class MarketService:
    """
    Создание, управление маркетами.
    """

    @staticmethod
    def create_market(question, description, category_id, close_date, resolution_date,
                      initial_liquidity, created_by, thumbnail=None, source_url=None,
                      resolution_source=None, tags=None, question_en=None, description_en=None):
        """
        Создать новый маркет.
        """
        # Валидация
        if not question or len(question) > 500:
            raise ValueError("Invalid question")

        try:
            category = MarketCategory.objects.get(id=category_id)
        except MarketCategory.DoesNotExist:
            raise ValueError("Category not found")

        settings = PredictionSettings.get_settings()
        min_duration = timezone.timedelta(hours=settings.min_market_duration_hours)
        if close_date <= timezone.now() + min_duration:
            raise ValueError("Close date too soon")

        if resolution_date <= close_date:
            raise ValueError("Resolution date must be after close date")

        if initial_liquidity < 1:
            raise ValueError("Initial liquidity too low")

        # Создать маркет
        yes_pool = Decimal(str(initial_liquidity))
        no_pool = Decimal(str(initial_liquidity))
        constant_k = yes_pool * no_pool
        yes_price = Decimal('0.5000')
        no_price = Decimal('0.5000')

        market = PredictionMarket.objects.create(
            market_id=generate_id("PM"),
            question=question,
            question_en=question_en,
            description=description,
            description_en=description_en,
            category=category,
            thumbnail=thumbnail,
            source_url=source_url,
            resolution_source=resolution_source,
            tags=tags or [],
            created_by=created_by,
            status='active',
            close_date=close_date,
            resolution_date=resolution_date,
            yes_pool=yes_pool,
            no_pool=no_pool,
            constant_k=constant_k,
            initial_liquidity=initial_liquidity,
            yes_price=yes_price,
            no_price=no_price,
            liquidity_usd=initial_liquidity * 2
        )

        # Обновить category.markets_count
        category.markets_count = PredictionMarket.objects.filter(category=category).count()
        category.save()

        # Записать начальную PriceHistory
        PriceHistory.objects.create(
            market=market,
            yes_price=yes_price,
            no_price=no_price,
            volume=Decimal(str(initial_liquidity)),
            source='creation'
        )

        return market

    @staticmethod
    def get_trending_markets(limit=10):
        """
        Трендовые маркеты.
        """
        return PredictionMarket.objects.filter(
            status='active'
        ).order_by('-volume_usd')[:limit]

    @staticmethod
    def get_closing_soon(limit=10):
        """
        Маркеты которые скоро закрываются.
        """
        soon = timezone.now() + timezone.timedelta(hours=48)
        return PredictionMarket.objects.filter(
            status='active',
            close_date__lte=soon,
            close_date__gt=timezone.now()
        ).order_by('close_date')[:limit]

    @staticmethod
    def get_recently_resolved(limit=10):
        """
        Недавно разрешённые.
        """
        week_ago = timezone.now() - timezone.timedelta(days=7)
        return PredictionMarket.objects.filter(
            status='resolved',
            resolved_at__gte=week_ago
        ).order_by('-resolved_at')[:limit]

    @staticmethod
    def search_markets(query, category=None, status=None):
        """
        Поиск по вопросу, тегам, описанию.
        """
        queryset = PredictionMarket.objects.all()

        if query:
            queryset = queryset.filter(
                Q(question__icontains=query) |
                Q(description__icontains=query) |
                Q(question_en__icontains=query) |
                Q(description_en__icontains=query) |
                Q(tags__icontains=query)
            )

        if category:
            queryset = queryset.filter(category_id=category)

        if status:
            queryset = queryset.filter(status=status)

        return queryset.order_by('-created_at')

    @staticmethod
    def close_expired_markets():
        """
        Закрыть просроченные маркеты.
        """
        now = timezone.now()
        expired = PredictionMarket.objects.filter(
            status='active',
            close_date__lte=now
        ).update(status='pending_resolution')

        return expired

    @staticmethod
    def get_market_stats(market_id):
        """
        Получить статистику маркета.
        """
        try:
            market = PredictionMarket.objects.get(id=market_id)
        except PredictionMarket.DoesNotExist:
            return None

        from ..models import Position, Trade, MarketComment
        
        positions_count = Position.objects.filter(market=market, shares__gt=0).count()
        traders_count = Position.objects.filter(market=market, shares__gt=0).values('user').distinct().count()
        trade_count = Trade.objects.filter(market=market).count()
        comments_count = MarketComment.objects.filter(market=market, is_deleted=False).count()

        return {
            "market_id": str(market.id),
            "question": market.question,
            "status": market.status,
            "volume_usd": float(market.volume_usd),
            "positions_count": positions_count,
            "traders_count": traders_count,
            "trade_count": trade_count,
            "comments_count": comments_count,
            "yes_price": float(market.yes_price),
            "no_price": float(market.no_price),
            "created_at": market.created_at.isoformat(),
            "close_date": market.close_date.isoformat()
        }
