import uuid
from decimal import Decimal
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.validators import MinValueValidator
from django.conf import settings

User = get_user_model()


class Category(models.Model):
    """Категория маркетов предсказаний."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    name_en = models.CharField(max_length=100, blank=True)
    slug = models.SlugField(unique=True)
    icon = models.CharField(max_length=10)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=7)
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
        return self.name


class Market(models.Model):

    # Основная информация
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=300)
    title_en = models.CharField(max_length=300, blank=True)
    slug = models.SlugField(max_length=350, unique=True)
    description = models.TextField()
    description_en = models.TextField(blank=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='markets')
    tags = models.JSONField(default=list)

    # Изображение
    image = models.ImageField(upload_to='predictions/markets/', blank=True, null=True)
    image_thumbnail = models.ImageField(upload_to='predictions/markets/thumbnails/', blank=True, null=True)

    # Тип маркета
    market_type = models.CharField(
        max_length=20,
        choices=(
            ('binary', 'Бинарный (YES/NO)'),
            ('multiple', 'Множественный выбор')
        ),
        default='binary'
    )

    # Временные рамки
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    opens_at = models.DateTimeField()
    closes_at = models.DateTimeField()
    resolved_at = models.DateTimeField(blank=True, null=True)

    # Статус
    status = models.CharField(
        max_length=20,
        choices=(
            ('draft', 'Черновик'),
            ('pending', 'На модерации'),
            ('active', 'Активный'),
            ('closed', 'Торги закрыты'),
            ('resolved', 'Разрешён'),
            ('cancelled', 'Отменён'),
            ('disputed', 'Оспаривается')
        ),
        default='draft'
    )

    # Результат
    resolution_source = models.TextField(blank=True)
    resolution_details = models.TextField(blank=True)

    # Финансы
    initial_liquidity = models.DecimalField(max_digits=18, decimal_places=2, default=1000)
    total_volume = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    total_traders = models.IntegerField(default=0)
    total_shares = models.IntegerField(default=0)

    # Комиссия
    fee_percent = models.DecimalField(max_digits=5, decimal_places=2, default=2.00)

    # Создатель и модерация
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, related_name='created_markets')
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, related_name='resolved_markets')

    # Видимость
    is_featured = models.BooleanField(default=False)
    is_hot = models.BooleanField(default=False)
    views_count = models.IntegerField(default=0)

    # Комментарии
    comments_enabled = models.BooleanField(default=True)
    comments_count = models.IntegerField(default=0)

    class Meta:
        verbose_name = 'Маркет предсказаний'
        verbose_name_plural = 'Маркеты предсказаний'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['status', 'closes_at']),
            models.Index(fields=['category', 'status']),
            models.Index(fields=['is_featured', 'status']),
            models.Index(fields=['is_hot', 'status']),
            models.Index(fields=['total_volume']),
            models.Index(fields=['slug']),
        ]

    def __str__(self):
        return self.title

    def is_open(self):
        return (
            self.status == 'active'
            and self.opens_at <= timezone.now()
            and self.closes_at > timezone.now()
        )

    def is_trading_allowed(self):
        return self.is_open()

    def time_until_close(self):
        if self.closes_at > timezone.now():
            return self.closes_at - timezone.now()
        return None

    def get_outcomes_with_prices(self):
        # Вернуть все исходы с текущими ценами.
        # Кешировать в Redis на 5 секунд.
        pass  # TODO: implement

    def get_price_history(self, outcome_id, period='24h'):
        # Вернуть историю цен исхода за период.
        pass  # TODO: implement


class Outcome(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    market = models.ForeignKey(Market, on_delete=models.CASCADE, related_name='outcomes')
    title = models.CharField(max_length=200)
    title_en = models.CharField(max_length=200, blank=True)
    slug = models.SlugField()
    sort_order = models.IntegerField(default=0)

    # AMM Pool
    pool_shares = models.DecimalField(max_digits=18, decimal_places=8, default=0)

    # Текущая цена
    current_price = models.DecimalField(max_digits=10, decimal_places=4, default=0.5000)

    # Результат
    is_winner = models.BooleanField(blank=True, null=True)

    # Статистика
    total_shares_sold = models.DecimalField(max_digits=18, decimal_places=8, default=0)
    total_volume = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    holders_count = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Исход'
        verbose_name_plural = 'Исходы'
        ordering = ['sort_order']
        unique_together = ['market', 'slug']

    def implied_probability(self):
        """Подразумеваемая вероятность в %."""
        return round(self.current_price * 100, 1)

    def payout_per_share(self):
        """Выплата за долю при выигрыше."""
        return Decimal('1.00')

    def potential_profit(self, buy_price):
        """Потенциальная прибыль."""
        return self.payout_per_share() - buy_price


class AMMPool(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    market = models.OneToOneField(Market, on_delete=models.CASCADE, related_name='amm_pool')

    # Состояние пула
    liquidity = models.DecimalField(max_digits=18, decimal_places=8)
    constant_product = models.DecimalField(max_digits=30, decimal_places=8)

    # Для бинарного маркета
    pool_yes = models.DecimalField(max_digits=18, decimal_places=8, default=0)
    pool_no = models.DecimalField(max_digits=18, decimal_places=8, default=0)

    # Общие
    total_fees_collected = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    last_trade_at = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'AMM Пул'

    def get_price_yes(self):
        """Текущая цена YES доли."""
        total = self.pool_yes + self.pool_no
        if total == 0:
            return Decimal('0.5')
        return self.pool_no / total

    def get_price_no(self):
        """Текущая цена NO доли."""
        return 1 - self.get_price_yes()

    def calculate_buy_cost(self, outcome, shares_amount):
        """
        Рассчитать стоимость покупки N долей.
        CPMM формула:
          cost = pool_opposite - (k / (pool_target + shares_amount))
        """
        pass  # TODO: implement

    def calculate_sell_return(self, outcome, shares_amount):
        """
        Рассчитать возврат при продаже N долей.
        Обратная формула.
        """
        pass  # TODO: implement


class UserPosition(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='prediction_positions')
    market = models.ForeignKey(Market, on_delete=models.CASCADE)
    outcome = models.ForeignKey(Outcome, on_delete=models.CASCADE)

    # Количество долей
    shares = models.DecimalField(max_digits=18, decimal_places=8, default=0)

    # Средняя цена покупки
    avg_buy_price = models.DecimalField(max_digits=10, decimal_places=4, default=0)

    # Инвестировано
    total_invested = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    total_fees_paid = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    # P&L
    realized_pnl = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    # Статусы
    is_settled = models.BooleanField(default=False)
    settlement_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Позиция пользователя'
        unique_together = ['user', 'outcome']
        indexes = [
            models.Index(fields=['user', 'market']),
            models.Index(fields=['user', 'is_settled']),
            models.Index(fields=['market', 'outcome']),
        ]

    def current_value(self):
        """Текущая стоимость позиции."""
        return self.shares * self.outcome.current_price

    def unrealized_pnl(self):
        """Нереализованная прибыль/убыток."""
        return self.current_value() - self.total_invested

    def unrealized_pnl_percent(self):
        """Нереализованная P&L в %."""
        if self.total_invested == 0:
            return 0
        return (self.unrealized_pnl() / self.total_invested) * 100

    def potential_payout(self):
        """Потенциальная выплата если исход выиграет."""
        return self.shares * Decimal('1.00')  # $1 за долю


class Trade(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='prediction_trades')
    market = models.ForeignKey(Market, on_delete=models.CASCADE)
    outcome = models.ForeignKey(Outcome, on_delete=models.CASCADE)

    # Тип сделки
    trade_type = models.CharField(
        max_length=4,
        choices=(
            ('buy', 'Покупка'),
            ('sell', 'Продажа')
        )
    )

    # Количество
    shares = models.DecimalField(max_digits=18, decimal_places=8)

    # Цены
    price_per_share = models.DecimalField(max_digits=10, decimal_places=4)
    total_cost = models.DecimalField(max_digits=18, decimal_places=2)
    fee_amount = models.DecimalField(max_digits=18, decimal_places=2)
    total_amount = models.DecimalField(max_digits=18, decimal_places=2)

    # Состояние пула после сделки
    price_before = models.DecimalField(max_digits=10, decimal_places=4)
    price_after = models.DecimalField(max_digits=10, decimal_places=4)

    # Мета
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Сделка'
        verbose_name_plural = 'Сделки'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['market', 'created_at']),
            models.Index(fields=['outcome', 'created_at']),
            models.Index(fields=['market', 'outcome', 'created_at']),
        ]


class PriceHistory(models.Model):

    id = models.BigAutoField(primary_key=True)
    outcome = models.ForeignKey(Outcome, on_delete=models.CASCADE, related_name='price_history')
    price = models.DecimalField(max_digits=10, decimal_places=4)
    volume = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    trades_count = models.IntegerField(default=0)
    timestamp = models.DateTimeField()

    # Период снимка
    interval = models.CharField(
        max_length=2,
        choices=(
            ('1m', '1 минута'),
            ('5m', '5 минут'),
            ('1h', '1 час'),
            ('1d', '1 день')
        ),
        default='1m'
    )

    class Meta:
        verbose_name = 'История цены'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['outcome', 'interval', 'timestamp']),
        ]
        unique_together = ['outcome', 'interval', 'timestamp']


class Comment(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    market = models.ForeignKey(Market, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')

    text = models.TextField(max_length=2000)
    # Markdown НЕ поддерживается (безопасность), HTML экранируется

    # Позиция автора на момент комментария
    user_position = models.CharField(max_length=50, blank=True)
    # Пример: "YES: 150 долей" или "Нет позиции"

    # Модерация
    is_hidden = models.BooleanField(default=False)
    hidden_reason = models.CharField(max_length=200, blank=True)
    hidden_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='hidden_comments')

    # Лайки
    likes_count = models.IntegerField(default=0)

    # Прочее
    is_pinned = models.BooleanField(default=False)
    is_edited = models.BooleanField(default=False)
    edited_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Комментарий'
        ordering = ['-is_pinned', '-created_at']
        indexes = [
            models.Index(fields=['market', 'created_at']),
            models.Index(fields=['user', 'created_at']),
        ]


class CommentLike(models.Model):

    comment = models.ForeignKey(Comment, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['comment', 'user']


class MarketActivity(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    market = models.ForeignKey(Market, on_delete=models.CASCADE, related_name='activities')
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    activity_type = models.CharField(
        max_length=10,
        choices=(
            ('buy', 'Купил'),
            ('sell', 'Продал'),
            ('comment', 'Комментарий')
        )
    )

    description = models.CharField(max_length=200)

    # Ссылка на объект
    trade = models.ForeignKey(Trade, on_delete=models.CASCADE, null=True, blank=True)
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['market', 'created_at']),
        ]
