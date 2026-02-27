from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError
from decimal import Decimal
import uuid


class GameType(models.Model):
    """
    Справочник типов игр.
    """
    code = models.CharField(max_length=50, primary_key=True, unique=True)
    name = models.CharField(max_length=100)
    name_en = models.CharField(max_length=100)
    description = models.TextField()
    icon = models.CharField(max_length=50)
    thumbnail = models.ImageField(null=True, blank=True)
    house_edge = models.DecimalField(max_digits=5, decimal_places=2)
    rtp = models.DecimalField(max_digits=5, decimal_places=2)
    min_bet = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.10'))
    max_bet = models.DecimalField(max_digits=10, decimal_places=2, default=10000)
    max_win_multiplier = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)
    is_popular = models.BooleanField(default=False)
    is_new = models.BooleanField(default=False)
    total_bets = models.BigIntegerField(default=0)
    total_wagered_usd = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    total_won_usd = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Тип игры'
        ordering = ['sort_order']

    def __str__(self):
        return self.name


class GameSession(models.Model):
    """
    Каждая игра = одна GameSession.
    Хранит ВСЕ данные игры.
    Неизменяемый после завершения.
    """
    STATUS_CHOICES = [
        ('active', 'Активна'),
        ('won', 'Выигрыш'),
        ('lost', 'Проигрыш'),
        ('cashout', 'Кэшаут'),
        ('cancelled', 'Отменена'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    game_id = models.CharField(max_length=50, unique=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='casino_games')
    wallet = models.ForeignKey('wallet.Wallet', on_delete=models.CASCADE)
    game_type = models.ForeignKey(GameType, on_delete=models.CASCADE)
    currency = models.ForeignKey('wallet.Currency', on_delete=models.CASCADE)
    bet_amount = models.DecimalField(max_digits=20, decimal_places=8)
    bet_amount_usd = models.DecimalField(max_digits=20, decimal_places=2)
    win_amount = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    win_multiplier = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    profit = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    game_data = models.JSONField(default=dict)
    server_seed = models.CharField(max_length=64)
    server_seed_hash = models.CharField(max_length=64)
    client_seed = models.CharField(max_length=64)
    nonce = models.BigIntegerField()
    is_verified = models.BooleanField(default=False)
    bet_transaction = models.ForeignKey('wallet.Transaction', null=True, blank=True, on_delete=models.SET_NULL, related_name='bet_session')
    win_transaction = models.ForeignKey('wallet.Transaction', null=True, blank=True, on_delete=models.SET_NULL, related_name='win_session')
    ip_address = models.GenericIPAddressField()
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Игровая сессия'
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['user', 'started_at']),
            models.Index(fields=['game_type', 'started_at']),
            models.Index(fields=['status']),
            models.Index(fields=['game_id']),
        ]

    def __str__(self):
        return f"{self.game_id} - {self.user.username}"


class CrashGame(models.Model):
    """
    Общая раунд Crash игры.
    Один раунд = МНОГО игроков.
    Все видят одну и ту же точку краша.
    """
    STATUS_CHOICES = [
        ('waiting', 'Ожидание ставок'),
        ('running', 'Идёт'),
        ('crashed', 'Упал'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    round_id = models.CharField(max_length=50, unique=True)
    crash_point = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='waiting')
    server_seed = models.CharField(max_length=64)
    server_seed_hash = models.CharField(max_length=64)
    previous_game = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL)
    chain_hash = models.CharField(max_length=64)
    players_count = models.IntegerField(default=0)
    total_bet = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    total_payout = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    started_at = models.DateTimeField(null=True, blank=True)
    crashed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Раунд Crash'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.round_id} - {self.crash_point}x"


class CrashBet(models.Model):
    """
    Ставка конкретного игрока в раунде Crash.
    """
    STATUS_CHOICES = [
        ('active', 'В игре'),
        ('cashed_out', 'Забрал'),
        ('busted', 'Не успел'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    crash_game = models.ForeignKey(CrashGame, on_delete=models.CASCADE, related_name='bets')
    game_session = models.OneToOneField(GameSession, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    bet_amount = models.DecimalField(max_digits=20, decimal_places=8)
    currency = models.ForeignKey('wallet.Currency', on_delete=models.CASCADE)
    auto_cashout = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    cashout_at = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    win_amount = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    cashed_out_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Ставка в Crash'

    def __str__(self):
        return f"{self.user.username} - {self.bet_amount}"


class UserSeed(models.Model):
    """
    Текущие seeds пользователя для Provably Fair.
    Каждый пользователь имеет свою пару seeds.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='game_seed')
    server_seed = models.CharField(max_length=64)
    server_seed_hash = models.CharField(max_length=64)
    client_seed = models.CharField(max_length=64)
    nonce = models.BigIntegerField(default=0)
    previous_server_seed = models.CharField(max_length=64, null=True, blank=True)
    previous_server_seed_hash = models.CharField(max_length=64, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Seed пользователя'

    def __str__(self):
        return f"{self.user.username} seed"


class CasinoSettings(models.Model):
    """
    Глобальные настройки казино.
    Singleton.
    """
    is_enabled = models.BooleanField(default=True)
    maintenance_message = models.TextField(null=True, blank=True)

    # Crash settings
    crash_enabled = models.BooleanField(default=True)
    crash_min_bet = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.10'))
    crash_max_bet = models.DecimalField(max_digits=10, decimal_places=2, default=10000)
    crash_house_edge = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('3.00'))
    crash_max_multiplier = models.DecimalField(max_digits=10, decimal_places=2, default=1000000)
    crash_round_wait_time = models.IntegerField(default=10)

    # Slots settings
    slots_enabled = models.BooleanField(default=True)
    slots_min_bet = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.10'))
    slots_max_bet = models.DecimalField(max_digits=10, decimal_places=2, default=5000)
    slots_rtp = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('96.00'))

    # Roulette settings
    roulette_enabled = models.BooleanField(default=True)
    roulette_min_bet = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.10'))
    roulette_max_bet = models.DecimalField(max_digits=10, decimal_places=2, default=10000)

    # Mines settings
    mines_enabled = models.BooleanField(default=True)
    mines_min_bet = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.10'))
    mines_max_bet = models.DecimalField(max_digits=10, decimal_places=2, default=5000)

    # Dice settings
    dice_enabled = models.BooleanField(default=True)
    dice_min_bet = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.10'))
    dice_max_bet = models.DecimalField(max_digits=10, decimal_places=2, default=10000)

    # Plinko settings
    plinko_enabled = models.BooleanField(default=True)
    plinko_min_bet = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.10'))
    plinko_max_bet = models.DecimalField(max_digits=10, decimal_places=2, default=5000)

    max_concurrent_games = models.IntegerField(default=5)
    show_recent_bets = models.BooleanField(default=True)
    show_big_wins = models.BooleanField(default=True)
    big_win_threshold_usd = models.DecimalField(max_digits=10, decimal_places=2, default=100)

    class Meta:
        verbose_name = 'Настройки казино'

    def __str__(self):
        return "Casino Settings"

    @classmethod
    def get_settings(cls):
        return cls.objects.first() or cls.objects.create()
