import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.wallet.models import Wallet, Currency, Transaction

User = get_user_model()

# Create your models here.


class Sport(models.Model):
    name = models.CharField(_('Название'), max_length=100)
    name_en = models.CharField(_('Название (EN)'), max_length=100)
    slug = models.SlugField(_('Слаг'), unique=True)
    icon = models.CharField(_('Иконка'), max_length=50, help_text='Emoji или CSS класс')
    sort_order = models.IntegerField(_('Порядок сортировки'), default=0)
    is_active = models.BooleanField(_('Активен'), default=True)
    is_popular = models.BooleanField(_('Популярный'), default=False)
    events_count = models.IntegerField(_('Количество событий'), default=0)
    external_id = models.CharField(_('Внешний ID'), max_length=50, blank=True, null=True)

    class Meta:
        verbose_name = _('Вид спорта')
        verbose_name_plural = _('Виды спорта')
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name


class Country(models.Model):
    name = models.CharField(_('Название'), max_length=100)
    name_en = models.CharField(_('Название (EN)'), max_length=100)
    code = models.CharField(_('Код'), max_length=5, help_text='ISO код')
    flag = models.CharField(_('Флаг'), max_length=10, help_text='Emoji флаг')
    sort_order = models.IntegerField(_('Порядок сортировки'), default=0)
    is_active = models.BooleanField(_('Активен'), default=True)

    class Meta:
        verbose_name = _('Страна')
        verbose_name_plural = _('Страны')
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name


class League(models.Model):
    sport = models.ForeignKey(Sport, on_delete=models.CASCADE, related_name='leagues', verbose_name=_('Вид спорта'))
    country = models.ForeignKey(Country, on_delete=models.CASCADE, blank=True, null=True, related_name='leagues', verbose_name=_('Страна'))
    name = models.CharField(_('Название'), max_length=200)
    name_en = models.CharField(_('Название (EN)'), max_length=200)
    short_name = models.CharField(_('Короткое название'), max_length=50)
    slug = models.SlugField(_('Слаг'))
    logo = models.ImageField(_('Логотип'), upload_to='leagues/', blank=True, null=True)
    season = models.CharField(_('Сезон'), max_length=20)
    is_active = models.BooleanField(_('Активен'), default=True)
    is_popular = models.BooleanField(_('Популярный'), default=False)
    events_count = models.IntegerField(_('Количество событий'), default=0)
    sort_order = models.IntegerField(_('Порядок сортировки'), default=0)
    external_id = models.CharField(_('Внешний ID'), max_length=50, blank=True, null=True)

    class Meta:
        verbose_name = _('Лига')
        verbose_name_plural = _('Лиги')
        ordering = ['-is_popular', 'sort_order', 'name']
        unique_together = ['sport', 'slug', 'season']

    def __str__(self):
        return self.name


class Team(models.Model):
    sport = models.ForeignKey(Sport, on_delete=models.CASCADE, related_name='teams', verbose_name=_('Вид спорта'))
    name = models.CharField(_('Название'), max_length=200)
    name_en = models.CharField(_('Название (EN)'), max_length=200)
    short_name = models.CharField(_('Короткое название'), max_length=50)
    logo = models.ImageField(_('Логотип'), upload_to='teams/', blank=True, null=True)
    country = models.ForeignKey(Country, on_delete=models.CASCADE, blank=True, null=True, related_name='teams', verbose_name=_('Страна'))
    is_active = models.BooleanField(_('Активен'), default=True)
    external_id = models.CharField(_('Внешний ID'), max_length=50, blank=True, null=True)

    class Meta:
        verbose_name = _('Команда')
        verbose_name_plural = _('Команды')
        ordering = ['name']

    def __str__(self):
        return self.name


class Event(models.Model):
    STATUS_CHOICES = (
        ('scheduled', _('Запланирован')),
        ('prematch', _('Премматч')),
        ('live', _('Идёт')),
        ('suspended', _('Приостановлен')),
        ('finished', _('Завершён')),
        ('cancelled', _('Отменён')),
        ('postponed', _('Перенесён')),
    )

    DATA_SOURCE_CHOICES = (
        ('api_football', _('API-Football')),
        ('the_odds_api', _('TheOddsAPI')),
        ('manual', _('Ручной ввод')),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sport = models.ForeignKey(Sport, on_delete=models.CASCADE, related_name='events', verbose_name=_('Вид спорта'))
    league = models.ForeignKey(League, on_delete=models.CASCADE, related_name='events', verbose_name=_('Лига'))
    home_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='home_events', verbose_name=_('Хозяева'))
    away_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='away_events', verbose_name=_('Гости'))
    name = models.CharField(_('Название'), max_length=300)
    slug = models.SlugField(_('Слаг'), blank=True, null=True)
    start_time = models.DateTimeField(_('Время начала'), db_index=True)
    end_time = models.DateTimeField(_('Время окончания'), blank=True, null=True)
    status = models.CharField(_('Статус'), max_length=20, choices=STATUS_CHOICES, default='scheduled')
    home_score = models.IntegerField(_('Счёт хозяев'), blank=True, null=True)
    away_score = models.IntegerField(_('Счёт гостей'), blank=True, null=True)
    result_details = models.JSONField(_('Детали результата'), default=dict)
    is_featured = models.BooleanField(_('Избранное'), default=False)
    is_boosted = models.BooleanField(_('Повышенные коэффициенты'), default=False)
    views_count = models.IntegerField(_('Просмотры'), default=0)
    bets_count = models.IntegerField(_('Количество ставок'), default=0)
    total_stake = models.DecimalField(_('Общая сумма ставок'), max_digits=15, decimal_places=2, default=0)
    markets_count = models.IntegerField(_('Количество маркетов'), default=0)
    data_source = models.CharField(_('Источник данных'), max_length=20, choices=DATA_SOURCE_CHOICES, default='manual')
    external_id = models.CharField(_('Внешний ID'), max_length=100, blank=True, null=True)
    settled_at = models.DateTimeField(_('Время расчёта'), blank=True, null=True)
    settled_by = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, related_name='settled_events', verbose_name=_('Рассчитал'))
    notes = models.TextField(_('Заметки'), blank=True, null=True)
    created_at = models.DateTimeField(_('Создано'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Обновлено'), auto_now=True)

    class Meta:
        verbose_name = _('Событие')
        verbose_name_plural = _('События')
        ordering = ['start_time']
        indexes = [
            models.Index(fields=['sport', 'status', 'start_time']),
            models.Index(fields=['league', 'start_time']),
            models.Index(fields=['status']),
            models.Index(fields=['start_time']),
            models.Index(fields=['is_featured']),
        ]

    def __str__(self):
        return self.name

    def is_bettable(self):
        return self.status == 'prematch' and self.start_time > timezone.now()

    def is_started(self):
        return self.start_time <= timezone.now()

    def is_settled(self):
        return self.status == 'finished' and self.settled_at is not None

    def get_time_until_start(self):
        if self.start_time > timezone.now():
            delta = self.start_time - timezone.now()
            days = delta.days
            hours, remainder = divmod(delta.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            if days > 0:
                return f"через {days}д {hours}ч {minutes}мин"
            elif hours > 0:
                return f"через {hours}ч {minutes}мин"
            else:
                return f"через {minutes}мин"
        return "Началось"

    def get_formatted_score(self):
        if self.home_score is not None and self.away_score is not None:
            return f"{self.home_score} : {self.away_score}"
        return "— : —"

    def save(self, *args, **kwargs):
        if not self.name:
            self.name = f"{self.home_team.name} — {self.away_team.name}"
        super().save(*args, **kwargs)


class Market(models.Model):
    STATUS_CHOICES = (
        ('open', _('Открыт')),
        ('suspended', _('Приостановлен')),
        ('closed', _('Закрыт')),
        ('settled', _('Рассчитан')),
        ('void', _('Аннулирован')),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='markets', verbose_name=_('Событие'))
    market_type = models.ForeignKey('MarketType', on_delete=models.CASCADE, related_name='markets', verbose_name=_('Тип маркета'))
    name = models.CharField(_('Название'), max_length=200)
    sort_order = models.IntegerField(_('Порядок сортировки'), default=0)
    parameter = models.DecimalField(_('Параметр'), max_digits=10, decimal_places=2, blank=True, null=True)
    status = models.CharField(_('Статус'), max_length=20, choices=STATUS_CHOICES, default='open')
    is_main = models.BooleanField(_('Главный маркет'), default=False)
    settled_at = models.DateTimeField(_('Время расчёта'), blank=True, null=True)
    created_at = models.DateTimeField(_('Создано'), auto_now_add=True)

    class Meta:
        verbose_name = _('Маркет')
        verbose_name_plural = _('Маркеты')
        ordering = ['sort_order']
        indexes = [
            models.Index(fields=['event', 'status']),
            models.Index(fields=['event', 'is_main']),
        ]

    def __str__(self):
        return self.name


class MarketType(models.Model):
    code = models.CharField(_('Код'), max_length=50, unique=True)
    name = models.CharField(_('Название'), max_length=100)
    name_en = models.CharField(_('Название (EN)'), max_length=100)
    description = models.TextField(_('Описание'))
    sport = models.ForeignKey(Sport, on_delete=models.CASCADE, blank=True, null=True, related_name='market_types', verbose_name=_('Вид спорта'))
    has_parameter = models.BooleanField(_('Имеет параметр'), default=False)
    outcomes_template = models.JSONField(_('Шаблон исходов'))
    sort_order = models.IntegerField(_('Порядок сортировки'), default=0)
    is_active = models.BooleanField(_('Активен'), default=True)
    is_popular = models.BooleanField(_('Популярный'), default=False)

    class Meta:
        verbose_name = _('Тип маркета')
        verbose_name_plural = _('Типы маркетов')
        ordering = ['sort_order']

    def __str__(self):
        return self.name


class Outcome(models.Model):
    RESULT_CHOICES = (
        ('pending', _('Ожидает')),
        ('won', _('Выиграл')),
        ('lost', _('Проиграл')),
        ('void', _('Аннулирован')),
        ('half_won', _('Выиграл 50%')),
        ('half_lost', _('Проиграл 50%')),
    )

    ODD_DIRECTION_CHOICES = (
        ('up', _('↑ Вырос')),
        ('down', _('↓ Упал')),
        ('same', _('= Не изменился')),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    market = models.ForeignKey(Market, on_delete=models.CASCADE, related_name='outcomes', verbose_name=_('Маркет'))
    code = models.CharField(_('Код'), max_length=50)
    name = models.CharField(_('Название'), max_length=100)
    odd = models.DecimalField(_('Коэффициент'), max_digits=10, decimal_places=3)
    odd_initial = models.DecimalField(_('Начальный коэффициент'), max_digits=10, decimal_places=3)
    odd_previous = models.DecimalField(_('Предыдущий коэффициент'), max_digits=10, decimal_places=3, blank=True, null=True)
    odd_direction = models.CharField(_('Изменение'), max_length=10, choices=ODD_DIRECTION_CHOICES, default='same')
    result = models.CharField(_('Результат'), max_length=20, choices=RESULT_CHOICES, default='pending')
    is_active = models.BooleanField(_('Активен'), default=True)
    is_suspended = models.BooleanField(_('Приостановлен'), default=False)
    max_stake = models.DecimalField(_('Максимальная ставка'), max_digits=15, decimal_places=2, blank=True, null=True)
    total_stake = models.DecimalField(_('Общая сумма ставок'), max_digits=15, decimal_places=2, default=0)
    bets_count = models.IntegerField(_('Количество ставок'), default=0)
    sort_order = models.IntegerField(_('Порядок сортировки'), default=0)
    settled_at = models.DateTimeField(_('Время расчёта'), blank=True, null=True)

    class Meta:
        verbose_name = _('Исход')
        verbose_name_plural = _('Исходы')
        ordering = ['sort_order']
        indexes = [
            models.Index(fields=['market', 'is_active']),
            models.Index(fields=['result']),
        ]

    def __str__(self):
        return self.name


class Bet(models.Model):
    BET_TYPE_CHOICES = (
        ('single', _('Одиночная')),
        ('combo', _('Экспресс')),
        ('system', _('Система')),
    )

    STATUS_CHOICES = (
        ('pending', _('Ожидает')),
        ('won', _('Выиграла')),
        ('lost', _('Проиграла')),
        ('partial_won', _('Частично выиграла')),
        ('void', _('Аннулирована')),
        ('cashed_out', _('Кэшаут')),
        ('cancelled', _('Отменена')),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bet_id = models.CharField(_('ID ставки'), max_length=50, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bets', verbose_name=_('Пользователь'))
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='bets', verbose_name=_('Кошелёк'))
    bet_type = models.CharField(_('Тип ставки'), max_length=10, choices=BET_TYPE_CHOICES, default='single')
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE, related_name='bets', verbose_name=_('Валюта'))
    stake = models.DecimalField(_('Сумма ставки'), max_digits=15, decimal_places=2)
    stake_usd = models.DecimalField(_('Сумма в USD'), max_digits=15, decimal_places=2)
    total_odd = models.DecimalField(_('Общий коэффициент'), max_digits=15, decimal_places=3)
    potential_win = models.DecimalField(_('Потенциальный выигрыш'), max_digits=15, decimal_places=2)
    actual_win = models.DecimalField(_('Фактический выигрыш'), max_digits=15, decimal_places=2, default=0)
    profit = models.DecimalField(_('Прибыль'), max_digits=15, decimal_places=2, default=0)
    status = models.CharField(_('Статус'), max_length=20, choices=STATUS_CHOICES, default='pending')
    items_count = models.IntegerField(_('Количество позиций'))
    items_won = models.IntegerField(_('Выигравших позиций'), default=0)
    items_lost = models.IntegerField(_('Проигравших позиций'), default=0)
    items_void = models.IntegerField(_('Аннулированных позиций'), default=0)
    items_pending = models.IntegerField(_('Ожидающих позиций'))
    cashout_available = models.BooleanField(_('Кэшаут доступен'), default=True)
    cashout_amount = models.DecimalField(_('Сумма кэшаута'), max_digits=15, decimal_places=2, blank=True, null=True)
    cashout_used_at = models.DateTimeField(_('Время кэшаута'), blank=True, null=True)
    freeze_transaction = models.ForeignKey(Transaction, on_delete=models.SET_NULL, blank=True, null=True, related_name='frozen_bets', verbose_name=_('Транзакция заморозки'))
    win_transaction = models.ForeignKey(Transaction, on_delete=models.SET_NULL, blank=True, null=True, related_name='win_bets', verbose_name=_('Транзакция выигрыша'))
    settled_at = models.DateTimeField(_('Время расчёта'), blank=True, null=True)
    ip_address = models.GenericIPAddressField(_('IP адрес'))
    user_agent = models.TextField(_('User Agent'), blank=True, null=True)
    created_at = models.DateTimeField(_('Создано'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Обновлено'), auto_now=True)

    class Meta:
        verbose_name = _('Ставка')
        verbose_name_plural = _('Ставки')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['status']),
            models.Index(fields=['bet_id']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.bet_id}: ${self.stake} x{self.total_odd} = ${self.potential_win} ({self.status})"

    def is_settled(self):
        return self.status not in ('pending',)

    def is_cashout_available(self):
        return (
            self.cashout_available and
            self.status == 'pending' and
            self.items_pending > 0 and
            self.items_lost == 0
        )

    def calculate_cashout_amount(self):
        """
        Рассчитать текущую сумму кэшаута.
        Формула: base = stake
        Для выигравших исходов: base *= odd_at_placement
        Для ожидающих: base *= current_odd * CASHOUT_FACTOR
        """
        from django.db.models import Q
        from decimal import Decimal
        
        if not self.is_cashout_available():
            return Decimal('0.00')
        
        base = self.stake
        settings = BetSettings.get_settings()
        cashout_factor = Decimal('0.85')  # Коэффициент при кэшауте
        
        # Для каждого выигравшего исхода умножить на его коэффициент
        for item in self.items.filter(result='won'):
            base *= item.odd_at_placement
        
        # Для каждого ожидающего исхода умножить на текущий коэффициент с фактором
        for item in self.items.filter(result='pending'):
            current_odd = item.odd_current or item.odd_at_placement
            base *= (current_odd * cashout_factor)
        
        # Применить маржу кэшаута
        cashout = base * settings.cashout_margin
        
        # Проверить минимум
        if cashout < settings.cashout_min_amount_usd:
            return Decimal('0.00')
        
        return min(cashout, self.potential_win)

    def recalculate(self):
        """
        Пересчитать статус ставки после расчёта одного из событий.
        """
        self.items_won = self.items.filter(result='won').count()
        self.items_lost = self.items.filter(result='lost').count()
        self.items_void = self.items.filter(result='void').count()
        self.items_pending = self.items.filter(result='pending').count()
        
        # Если есть проигравшие исходы в экспрессе, вся ставка проиграла
        if self.items_lost > 0 and self.bet_type in ('combo', 'system'):
            self.status = 'lost'
            self.actual_win = Decimal('0.00')
            self.profit = -self.stake
            self.cashout_available = False
        
        self.save(update_fields=[
            'items_won', 'items_lost', 'items_void', 'items_pending',
            'status', 'actual_win', 'profit', 'cashout_available'
        ])


class BetItem(models.Model):
    RESULT_CHOICES = (
        ('pending', _('Ожидает')),
        ('won', _('Выиграл')),
        ('lost', _('Проиграл')),
        ('void', _('Аннулирован')),
        ('half_won', _('Выиграл 50%')),
        ('half_lost', _('Проиграл 50%')),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bet = models.ForeignKey(Bet, on_delete=models.CASCADE, related_name='items', verbose_name=_('Ставка'))
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='bet_items', verbose_name=_('Событие'))
    market = models.ForeignKey(Market, on_delete=models.CASCADE, related_name='bet_items', verbose_name=_('Маркет'))
    outcome = models.ForeignKey(Outcome, on_delete=models.CASCADE, related_name='bet_items', verbose_name=_('Исход'))
    odd_at_placement = models.DecimalField(_('Коэффициент при ставке'), max_digits=10, decimal_places=3)
    odd_current = models.DecimalField(_('Текущий коэффициент'), max_digits=10, decimal_places=3, blank=True, null=True)
    result = models.CharField(_('Результат'), max_length=20, choices=RESULT_CHOICES, default='pending')
    event_name = models.CharField(_('Название события'), max_length=300)
    market_name = models.CharField(_('Название маркета'), max_length=200)
    outcome_name = models.CharField(_('Название исхода'), max_length=100)
    event_start_time = models.DateTimeField(_('Время начала события'))
    settled_at = models.DateTimeField(_('Время расчёта'), blank=True, null=True)

    class Meta:
        verbose_name = _('Позиция в ставке')
        verbose_name_plural = _('Позиции в ставках')
        ordering = ['event_start_time']

    def __str__(self):
        return f"{self.event_name} - {self.outcome_name}"


class BetSettings(models.Model):
    min_stake_usd = models.DecimalField(_('Минимальная ставка (USD)'), max_digits=10, decimal_places=2, default=0.50)
    max_stake_usd = models.DecimalField(_('Максимальная ставка (USD)'), max_digits=15, decimal_places=2, default=50000)
    max_potential_win_usd = models.DecimalField(_('Максимальный выигрыш (USD)'), max_digits=15, decimal_places=2, default=100000)
    max_combo_items = models.IntegerField(_('Максимум событий в экспрессе'), default=20)
    min_combo_items = models.IntegerField(_('Минимум событий в экспрессе'), default=2)
    min_odd = models.DecimalField(_('Минимальный коэффициент'), max_digits=10, decimal_places=3, default=1.01)
    max_odd = models.DecimalField(_('Максимальный коэффициент'), max_digits=15, decimal_places=3, default=1000.0)
    cashout_enabled = models.BooleanField(_('Кэшаут включён'), default=True)
    cashout_margin = models.DecimalField(_('Маржа кэшаута'), max_digits=5, decimal_places=4, default=0.90)
    cashout_min_amount_usd = models.DecimalField(_('Минимальная сумма кэшаута (USD)'), max_digits=10, decimal_places=2, default=1.00)
    max_bets_per_event_per_user = models.IntegerField(_('Максимум ставок на событие от пользователя'), default=50)
    delay_before_start_minutes = models.IntegerField(_('Задержка перед началом (минуты)'), default=1)
    auto_settle_enabled = models.BooleanField(_('Автоматический расчёт'), default=True)
    odds_change_notification = models.BooleanField(_('Уведомления об изменении коэффициентов'), default=True)

    class Meta:
        verbose_name = _('Настройки ставок')
        verbose_name_plural = _('Настройки ставок')

    def __str__(self):
        return "Настройки ставок"

    @staticmethod
    def get_settings():
        settings, created = BetSettings.objects.get_or_create(id=1)
        return settings


class OddHistory(models.Model):
    CHANGED_BY_CHOICES = (
        ('api', _('API провайдер')),
        ('admin', _('Админ')),
        ('system', _('Система')),
    )

    id = models.BigAutoField(primary_key=True)
    outcome = models.ForeignKey(Outcome, on_delete=models.CASCADE, related_name='history', verbose_name=_('Исход'))
    odd_before = models.DecimalField(_('Коэффициент до'), max_digits=10, decimal_places=3)
    odd_after = models.DecimalField(_('Коэффициент после'), max_digits=10, decimal_places=3)
    changed_by = models.CharField(_('Изменено'), max_length=10, choices=CHANGED_BY_CHOICES)
    changed_at = models.DateTimeField(_('Время изменения'), auto_now_add=True)

    class Meta:
        verbose_name = _('История коэффициентов')
        verbose_name_plural = _('История коэффициентов')
        ordering = ['-changed_at']
        indexes = [
            models.Index(fields=['outcome', 'changed_at']),
        ]

    def __str__(self):
        return f"{self.outcome} {self.odd_before} → {self.odd_after}"
