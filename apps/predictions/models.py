import uuid
from decimal import Decimal
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings
from django.core.cache import cache

User = get_user_model()


class MarketCategory(models.Model):
    """Категория маркетов предсказаний."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    name_en = models.CharField(max_length=100, blank=True, null=True)
    slug = models.SlugField(unique=True)
    icon = models.CharField(max_length=10)
    description = models.TextField(blank=True, null=True)
    color = models.CharField(max_length=7, default='#4ECDC4')
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    # Статистика (кэшированная)
    markets_count = models.IntegerField(default=0)
    total_volume = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Категория предсказаний'
        verbose_name_plural = 'Категории предсказаний'
        ordering = ['sort_order', 'name']

    def __str__(self):
        return f"{self.icon} {self.name}"


class PredictionMarket(models.Model):
    """Маркет предсказания. Центральная модель."""

    # Основная информация
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    market_id = models.CharField(max_length=50, unique=True)  # PM-20250315-A7B3C2

    question = models.CharField(max_length=500)  # RU
    question_en = models.CharField(max_length=500, blank=True, null=True)

    description = models.TextField()  # Подробное описание и правила резолвинга
    description_en = models.TextField(blank=True, null=True)

    category = models.ForeignKey(MarketCategory, on_delete=models.PROTECT, related_name='markets')

    # Изображение
    thumbnail = models.ImageField(upload_to='predictions/markets/', blank=True, null=True)

    source_url = models.URLField(blank=True, null=True)  # Ссылка для проверки результата
    resolution_source = models.TextField(blank=True, null=True)  # Описание источника для резолвинга
    resolution_evidence = models.TextField(blank=True, null=True)  # Доказательства при резолвинге
    resolution_evidence_url = models.URLField(blank=True, null=True)

    tags = models.JSONField(default=list)  # ["bitcoin", "crypto", "price"]

    # Временные рамки
    close_date = models.DateTimeField()  # Дата закрытия торгов
    resolution_date = models.DateTimeField()  # Ожидаемая дата резолвинга
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Статус
    status = models.CharField(
        max_length=20,
        choices=(
            ('draft', 'Черновик'),
            ('pending_review', 'На модерации'),
            ('active', 'Активный'),
            ('trading_halted', 'Торги приостановлены'),
            ('pending_resolution', 'Ожидает резолвинга'),
            ('resolved', 'Разрешён'),
            ('voided', 'Аннулирован'),
            ('disputed', 'Оспаривается')
        ),
        default='draft'
    )

    # Результат
    resolution = models.CharField(
        max_length=10,
        choices=(('yes', 'YES'), ('no', 'NO')),
        blank=True,
        null=True
    )
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, related_name='resolved_markets')
    resolved_at = models.DateTimeField(blank=True, null=True)

    # AMM Пулы
    yes_pool = models.DecimalField(max_digits=18, decimal_places=8, default=0)
    no_pool = models.DecimalField(max_digits=18, decimal_places=8, default=0)
    constant_k = models.DecimalField(max_digits=36, decimal_places=16, default=0)  # K = yes_pool × no_pool

    # Цены (кешированные)
    yes_price = models.DecimalField(max_digits=10, decimal_places=4, default=0.5000)
    no_price = models.DecimalField(max_digits=10, decimal_places=4, default=0.5000)

    initial_liquidity = models.DecimalField(max_digits=18, decimal_places=2, default=10000)

    # Финансы и статистика
    volume_usd = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    volume_24h_usd = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    trades_count = models.IntegerField(default=0)
    unique_traders = models.IntegerField(default=0)
    yes_holders = models.IntegerField(default=0)
    no_holders = models.IntegerField(default=0)
    total_yes_shares = models.DecimalField(max_digits=18, decimal_places=8, default=0)
    total_no_shares = models.DecimalField(max_digits=18, decimal_places=8, default=0)
    liquidity_usd = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    # Видимость и популярность
    is_featured = models.BooleanField(default=False)
    is_trending = models.BooleanField(default=False)
    views_count = models.IntegerField(default=0)
    comments_count = models.IntegerField(default=0)
    likes_count = models.IntegerField(default=0)
    sort_order = models.IntegerField(default=0)

    # Создатель
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, related_name='created_prediction_markets')

    class Meta:
        verbose_name = 'Маркет предсказания'
        verbose_name_plural = 'Маркеты предсказаний'
        ordering = ['-is_featured', '-volume_24h_usd', '-created_at']
        indexes = [
            models.Index(fields=['status', 'close_date']),
            models.Index(fields=['category', 'status']),
            models.Index(fields=['is_featured']),
            models.Index(fields=['is_trending']),
            models.Index(fields=['created_at']),
            models.Index(fields=['volume_24h_usd']),
        ]

    def __str__(self):
        return self.question[:80]

    def is_tradeable(self):
        """Можно ли торговать?"""
        return self.status == 'active' and self.close_date > timezone.now()

    def is_trading_allowed(self):
        """Торговля разрешена?"""
        return self.is_tradeable()

    def is_closed(self):
        """Торги закрыты?"""
        return self.close_date <= timezone.now() or self.status != 'active'

    def is_resolved(self):
        """Маркет разрешён?"""
        return self.status == 'resolved'

    def is_open(self):
        """Маркет открыт для торговли?"""
        return self.status == 'active' and self.close_date > timezone.now()

    def get_time_until_close(self):
        """Времени до закрытия."""
        if self.close_date > timezone.now():
            return self.close_date - timezone.now()
        return None

    def get_yes_probability(self):
        """Вероятность YES в %."""
        return float(self.yes_price) * 100

    def get_no_probability(self):
        """Вероятность NO в %."""
        return float(self.no_price) * 100

    def get_implied_odds(self):
        """Букмекерские коэффициенты."""
        yes_price = float(self.yes_price)
        no_price = float(self.no_price)
        return {
            "yes": round(1 / yes_price, 2) if yes_price > 0 else 0,
            "no": round(1 / no_price, 2) if no_price > 0 else 0
        }

    def get_outcomes_with_prices(self):
        """Вернуть все исходы с текущими ценами."""
        cache_key = f'market_{self.id}_outcomes'
        outcomes = cache.get(cache_key)
        
        if outcomes is None:
            outcomes = list(self.outcomes.all())
            cache.set(cache_key, outcomes, 300)  # 5 minutes
        
        return outcomes

    def get_price_history(self, period='24h'):
        """Вернуть историю цен за период."""
        if period == '24h':
            since = timezone.now() - timezone.timedelta(hours=24)
        elif period == '7d':
            since = timezone.now() - timezone.timedelta(days=7)
        elif period == '30d':
            since = timezone.now() - timezone.timedelta(days=30)
        else:  # all
            since = None

        qs = self.price_history.all()
        if since:
            qs = qs.filter(timestamp__gte=since)
        
        return qs.order_by('timestamp')

    def recalculate_prices(self):
        """Пересчитать цены на основе пулов."""
        total = self.yes_pool + self.no_pool
        if total > 0:
            self.yes_price = self.no_pool / total
            self.no_price = self.yes_pool / total
        else:
            self.yes_price = Decimal('0.5')
            self.no_price = Decimal('0.5')

    def is_closed(self):
        """Торги закрыты?"""
        return self.close_date <= timezone.now() or self.status != 'active'

    def is_resolved(self):
        """Разрешён?"""
        return self.status == 'resolved'

    def get_yes_probability(self):
        """Вероятность YES в %."""
        return float(self.yes_price) * 100

    def get_no_probability(self):
        """Вероятность NO в %."""
        return float(self.no_price) * 100

    def get_time_until_close(self):
        """Времени до закрытия."""
        if self.close_date > timezone.now():
            return self.close_date - timezone.now()
        return None

    def get_implied_odds(self):
        """Букмекерские коэффициенты."""
        yes_price = float(self.yes_price)
        no_price = float(self.no_price)
        return {
            "yes": round(1 / yes_price, 2) if yes_price > 0 else 0,
            "no": round(1 / no_price, 2) if no_price > 0 else 0
        }

    def recalculate_prices(self):
        """Пересчитать цены на основе пулов."""
        total = self.yes_pool + self.no_pool
        if total > 0:
            self.yes_price = self.no_pool / total
            self.no_price = self.yes_pool / total
        else:
            self.yes_price = Decimal('0.5')
            self.no_price = Decimal('0.5')


class Position(models.Model):
    """Позиция пользователя в маркете."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='prediction_positions')
    market = models.ForeignKey(PredictionMarket, on_delete=models.CASCADE, related_name='positions')

    side = models.CharField(max_length=10, choices=[('yes', 'YES'), ('no', 'NO')])
    shares = models.DecimalField(max_digits=18, decimal_places=8, default=0)
    avg_price = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    total_invested = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    total_returned = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    realized_pnl = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    is_settled = models.BooleanField(default=False)
    settlement_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Позиция'
        unique_together = ['user', 'market', 'side']
        indexes = [
            models.Index(fields=['user', 'market']),
            models.Index(fields=['user', 'is_settled']),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.market.question[:30]} - {self.side.upper()}"

    def current_value(self):
        """Текущая стоимость позиции."""
        if self.side == 'yes':
            return self.shares * self.market.yes_price
        else:
            return self.shares * self.market.no_price

    def unrealized_pnl(self):
        """Нереализованная прибыль."""
        return self.current_value() - self.total_invested + self.total_returned

    def total_pnl(self):
        """Общая прибыль/убыток."""
        return self.realized_pnl + self.unrealized_pnl()

    def pnl_percent(self):
        """P&L в %."""
        if self.total_invested == 0:
            return 0
        return (self.total_pnl() / self.total_invested) * 100

    def potential_payout(self):
        """Потенциальная выплата если исход выиграет."""
        return self.shares * Decimal('1.00')


class Trade(models.Model):
    """Сделка в маркете."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    trade_id = models.CharField(max_length=50, unique=True)  # TRD-{timestamp}-{random6}

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='prediction_trades')
    market = models.ForeignKey(PredictionMarket, on_delete=models.CASCADE, related_name='trades')
    position = models.ForeignKey(Position, on_delete=models.SET_NULL, blank=True, null=True)

    action = models.CharField(max_length=10, choices=[('buy', 'Покупка'), ('sell', 'Продажа')])
    side = models.CharField(max_length=10, choices=[('yes', 'YES'), ('no', 'NO')])

    shares = models.DecimalField(max_digits=18, decimal_places=8)
    price = models.DecimalField(max_digits=10, decimal_places=4)  # Цена за акцию
    total_cost = models.DecimalField(max_digits=18, decimal_places=2)  # Сделка стоимость (buy: потрачено, sell: получено)
    fee_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    price_before = models.DecimalField(max_digits=10, decimal_places=4)
    price_after = models.DecimalField(max_digits=10, decimal_places=4)
    yes_price_after = models.DecimalField(max_digits=10, decimal_places=4)
    no_price_after = models.DecimalField(max_digits=10, decimal_places=4)

    transaction = models.ForeignKey('wallet.Transaction', on_delete=models.SET_NULL, blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Сделка'
        verbose_name_plural = 'Сделки'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['market', 'created_at']),
        ]

    def __str__(self):
        return f"{self.trade_id}"


class PriceHistory(models.Model):
    """История цен для графиков."""

    id = models.BigAutoField(primary_key=True)
    market = models.ForeignKey(PredictionMarket, on_delete=models.CASCADE, related_name='price_history')

    yes_price = models.DecimalField(max_digits=10, decimal_places=4)
    no_price = models.DecimalField(max_digits=10, decimal_places=4)
    volume = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    source = models.CharField(
        max_length=20,
        choices=[('trade', 'Сделка'), ('periodic', 'Периодическая запись')],
        default='periodic'
    )

    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'История цены'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['market', 'timestamp']),
        ]


class MarketComment(models.Model):
    """Комментарии под маркетом."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    market = models.ForeignKey(PredictionMarket, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='market_comments')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')

    text = models.TextField(max_length=2000)
    side_prediction = models.CharField(
        max_length=10,
        choices=[('yes', 'YES'), ('no', 'NO')],
        blank=True,
        null=True
    )

    likes_count = models.IntegerField(default=0)
    is_pinned = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Комментарий маркета'
        ordering = ['-is_pinned', '-likes_count', '-created_at']
        indexes = [
            models.Index(fields=['market', 'created_at']),
        ]

    def __str__(self):
        return f"{self.user.email}: {self.text[:50]}"


class MarketLike(models.Model):
    """Лайки маркета."""

    market = models.ForeignKey(PredictionMarket, on_delete=models.CASCADE, related_name='liked_by')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['market', 'user']


class CommentLike(models.Model):
    """Лайки комментариев."""

    comment = models.ForeignKey(MarketComment, on_delete=models.CASCADE, related_name='liked_by')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['comment', 'user']


class MarketDispute(models.Model):
    """Оспаривание результата маркета."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    market = models.ForeignKey(PredictionMarket, on_delete=models.CASCADE, related_name='disputes')
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    reason = models.TextField()
    evidence_url = models.URLField(blank=True, null=True)

    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'На рассмотрении'),
            ('accepted', 'Принято'),
            ('rejected', 'Отклонено')
        ],
        default='pending'
    )

    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, related_name='reviewed_disputes')
    review_comment = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Оспаривание'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} - {self.market.question[:30]}"


class PredictionSettings(models.Model):
    """Глобальные настройки Prediction Market. Singleton."""

    is_enabled = models.BooleanField(default=True)

    trading_fee_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=1.0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )

    min_trade_amount_usd = models.DecimalField(
        max_digits=18, decimal_places=2, default=1.00,
        validators=[MinValueValidator(0)]
    )

    max_trade_amount_usd = models.DecimalField(
        max_digits=18, decimal_places=2, default=10000,
        validators=[MinValueValidator(0)]
    )

    default_initial_liquidity = models.DecimalField(
        max_digits=18, decimal_places=2, default=10000,
        validators=[MinValueValidator(0)]
    )

    max_position_usd = models.DecimalField(
        max_digits=18, decimal_places=2, default=50000,
        validators=[MinValueValidator(0)]
    )

    resolution_dispute_window_hours = models.IntegerField(default=24)
    min_market_duration_hours = models.IntegerField(default=24)
    auto_close_before_resolution_hours = models.IntegerField(default=1)

    allow_user_market_proposals = models.BooleanField(default=False)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Настройки Prediction Market'

    def __str__(self):
        return "Prediction Market Settings"

    @classmethod
    def get_settings(cls):
        """Получить или создать единственный объект настроек."""
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

    def save(self, *args, **kwargs):
        """Переопределение save для сохранения только одного объекта."""
        self.pk = 1
        super().save(*args, **kwargs)
        cache.delete('prediction_settings')  # Очистить кэш при изменении

    def delete(self, *args, **kwargs):
        """Запретить удаление."""
        pass
