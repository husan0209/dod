from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
import uuid

User = get_user_model()


class PartnerTier(models.Model):

    name = models.CharField(max_length=50)
    name_en = models.CharField(max_length=50, blank=True)
    slug = models.SlugField(unique=True)
    icon = models.CharField(max_length=10)
    color = models.CharField(max_length=7)

    # Условия получения уровня
    min_referrals = models.IntegerField(default=0)
    min_monthly_ggr = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    # Комиссионные ставки (% от GGR)
    commission_rate_month_1 = models.DecimalField(max_digits=5, decimal_places=2)
    commission_rate_month_2_3 = models.DecimalField(max_digits=5, decimal_places=2)
    commission_rate_month_4_plus = models.DecimalField(max_digits=5, decimal_places=2)

    # Комиссия 2-го уровня (от рефералов рефералов)
    level2_commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    # Минимальный вывод
    min_payout_amount = models.DecimalField(max_digits=18, decimal_places=2, default=50)

    # Бонусы
    signup_bonus = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    first_deposit_bonus_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    # Привилегии
    has_custom_links = models.BooleanField(default=False)
    has_promo_materials = models.BooleanField(default=True)
    has_api_access = models.BooleanField(default=False)
    has_dedicated_manager = models.BooleanField(default=False)

    # Порядок
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Уровень партнёра'
        verbose_name_plural = 'Уровни партнёров'
        ordering = ['sort_order']

    def __str__(self):
        return self.name


class PartnerProfile(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='partner_profile')
    tier = models.ForeignKey(PartnerTier, on_delete=models.PROTECT)

    # Партнёрский баланс (отдельно от игрового)
    balance = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    total_earned = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    total_withdrawn = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    # Статистика (кэшированная, обновляется Celery)
    total_referrals = models.IntegerField(default=0)
    active_referrals = models.IntegerField(default=0)
    referrals_with_deposit = models.IntegerField(default=0)
    total_referral_deposits = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    total_referral_ggr = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    # 2-й уровень
    total_level2_referrals = models.IntegerField(default=0)
    total_level2_earned = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    # Текущий месяц
    monthly_ggr = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    monthly_earned = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    monthly_referrals = models.IntegerField(default=0)

    # Лучшие показатели
    best_month_earnings = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    best_month_date = models.DateField(blank=True, null=True)

    # Статус
    is_partner_active = models.BooleanField(default=True)
    is_suspended = models.BooleanField(default=False)
    suspension_reason = models.TextField(blank=True)

    # Пользовательские ссылки
    custom_slug = models.SlugField(blank=True, null=True, unique=True)

    # Промо
    bio = models.TextField(max_length=500, blank=True)
    website_url = models.URLField(blank=True, null=True)
    telegram_channel = models.CharField(max_length=100, blank=True)

    # Даты
    partner_since = models.DateTimeField(auto_now_add=True)
    tier_changed_at = models.DateTimeField(blank=True, null=True)
    last_payout_at = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Профиль партнёра'
        verbose_name_plural = 'Профили партнёров'

    def get_commission_rate(self, referral_age_months):
        """Получить текущий % комиссии по возрасту реферала."""
        if referral_age_months <= 1:
            return self.tier.commission_rate_month_1
        elif referral_age_months <= 3:
            return self.tier.commission_rate_month_2_3
        else:
            return self.tier.commission_rate_month_4_plus

    def get_referral_link(self):
        """Полная реферальная ссылка."""
        code = self.custom_slug or self.user.referral_code
        return f'{settings.SITE_URL}/r/{code}'

    def available_for_payout(self):
        """Доступно для вывода."""
        return self.balance >= self.tier.min_payout_amount


class Referral(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    partner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='referred_users')
    referral = models.OneToOneField(User, on_delete=models.CASCADE, related_name='referral_record')

    # Как пришёл
    referral_code_used = models.CharField(max_length=20)
    source = models.CharField(max_length=50, blank=True)
    promo_link = models.ForeignKey('PromoLink', blank=True, null=True, on_delete=models.SET_NULL)

    # Регистрация
    registration_ip = models.GenericIPAddressField(blank=True, null=True)
    registration_country = models.CharField(max_length=100, blank=True)
    registration_device = models.CharField(max_length=50, blank=True)
    registered_at = models.DateTimeField(auto_now_add=True)

    # Статус реферала
    status = models.CharField(
        max_length=20,
        choices=(
            ('registered', 'Зарегистрирован'),
            ('deposited', 'Сделал депозит'),
            ('active', 'Активный'),
            ('churned', 'Ушёл'),
            ('blocked', 'Заблокирован'),
            ('fraud', 'Фрод')
        ),
        default='registered'
    )

    # Финансы реферала
    total_deposits = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    first_deposit_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    first_deposit_at = models.DateTimeField(blank=True, null=True)
    total_bets = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    total_ggr = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    total_winnings = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    # Комиссия с этого реферала
    total_commission_earned = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    # Активность
    last_active_at = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    # Уровень (для многоуровневой)
    level = models.IntegerField(default=1)

    # Антифрод
    is_suspicious = models.BooleanField(default=False)
    fraud_flags = models.JSONField(default=list)
    is_qualified = models.BooleanField(default=False)
    qualified_at = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Реферал'
        verbose_name_plural = 'Рефералы'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['partner', 'status']),
            models.Index(fields=['partner', 'created_at']),
            models.Index(fields=['partner', 'is_qualified']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['level']),
        ]

    def __str__(self):
        return f"{self.referral.username} → {self.partner.username}"

    def get_level_display(self):
        """Вернуть красивое название уровня."""
        if self.level == 1:
            return "Прямой реферал"
        elif self.level == 2:
            return "Реферал 2-го уровня"
        else:
            return f"Уровень {self.level}"


class Commission(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    partner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='commissions')
    referral = models.ForeignKey(Referral, on_delete=models.CASCADE, related_name='commissions')

    # Тип комиссии
    commission_type = models.CharField(
        max_length=20,
        choices=(
            ('ggr', 'Комиссия от GGR'),
            ('signup_bonus', 'Бонус за регистрацию'),
            ('first_deposit', 'Бонус за первый депозит'),
            ('level2_ggr', 'Комиссия 2-го уровня'),
            ('manual', 'Ручное начисление (админ)'),
            ('bonus', 'Бонус от платформы')
        )
    )

    # Период
    period_start = models.DateField()
    period_end = models.DateField()

    # Расчёт
    referral_ggr = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2)

    # Суммы
    gross_amount = models.DecimalField(max_digits=18, decimal_places=2)
    adjustments = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    net_amount = models.DecimalField(max_digits=18, decimal_places=2)

    # Статус
    status = models.CharField(
        max_length=20,
        choices=(
            ('pending', 'Ожидает'),
            ('approved', 'Одобрена'),
            ('paid', 'Выплачена'),
            ('cancelled', 'Отменена'),
            ('held', 'Задержана (проверка)')
        ),
        default='pending'
    )

    # Выплата
    payout = models.ForeignKey('PartnerPayout', blank=True, null=True, on_delete=models.SET_NULL)

    # Мета
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, blank=True, null=True, on_delete=models.SET_NULL, related_name='created_commissions')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Комиссия'
        verbose_name_plural = 'Комиссии'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['partner', 'created_at']),
            models.Index(fields=['partner', 'status']),
            models.Index(fields=['referral', 'period_start']),
            models.Index(fields=['commission_type']),
            models.Index(fields=['status', 'created_at']),
        ]


class PartnerPayout(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    partner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='partner_payouts')

    # Суммы
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    fee = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    net_amount = models.DecimalField(max_digits=18, decimal_places=2)

    # Куда выводить
    payout_method = models.CharField(
        max_length=20,
        choices=(
            ('game_balance', 'На игровой баланс'),
            ('wallet', 'На кошелёк DOD (далее вывод)'),
            ('usdt', 'USDT напрямую'),
            ('bank_card', 'На банковскую карту')
        ),
        default='game_balance'
    )

    payout_details = models.JSONField(blank=True, null=True)

    # Статус
    status = models.CharField(
        max_length=20,
        choices=(
            ('pending', 'Ожидает'),
            ('processing', 'Обрабатывается'),
            ('completed', 'Выполнена'),
            ('rejected', 'Отклонена'),
            ('cancelled', 'Отменена')
        ),
        default='pending'
    )

    rejection_reason = models.TextField(blank=True)

    # Обработка
    processed_by = models.ForeignKey(User, blank=True, null=True, on_delete=models.SET_NULL, related_name='processed_payouts')
    processed_at = models.DateTimeField(blank=True, null=True)

    # Мета
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Выплата партнёру'
        verbose_name_plural = 'Выплаты партнёрам'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['partner', 'status']),
            models.Index(fields=['status', 'created_at']),
        ]


class PromoLink(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    partner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='promo_links')

    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=50, unique=True)

    # Статистика
    clicks = models.IntegerField(default=0)
    registrations = models.IntegerField(default=0)
    deposits = models.IntegerField(default=0)
    total_deposit_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    total_ggr = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    total_earned = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    # Конверсия
    conversion_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    deposit_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    # Настройки
    is_active = models.BooleanField(default=True)

    # UTM
    utm_source = models.CharField(max_length=100, blank=True)
    utm_medium = models.CharField(max_length=100, blank=True)
    utm_campaign = models.CharField(max_length=100, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Промо-ссылка'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['partner', 'is_active']),
        ]

    def get_full_url(self):
        return f'{settings.SITE_URL}/r/{self.slug}'

    def get_qr_code(self):
        # TODO: implement
        pass


class PromoLinkClick(models.Model):

    id = models.BigAutoField(primary_key=True)
    promo_link = models.ForeignKey(PromoLink, on_delete=models.CASCADE)
    ip_address = models.GenericIPAddressField()
    country = models.CharField(max_length=100, blank=True)
    user_agent = models.TextField(blank=True)
    device_type = models.CharField(max_length=20)
    referer = models.URLField(blank=True)
    is_unique = models.BooleanField(default=True)
    resulted_in_registration = models.BooleanField(default=False)
    user_registered = models.ForeignKey(User, blank=True, null=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class NegativeCarryover(models.Model):

    partner = models.ForeignKey(User, on_delete=models.CASCADE)
    referral = models.ForeignKey(Referral, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    class Meta:
        unique_together = ['partner', 'referral']


class ReferralSettings(models.Model):

    # Квалификация реферала
    min_deposit_to_qualify = models.DecimalField(max_digits=18, decimal_places=2, default=10)
    min_bets_to_qualify = models.IntegerField(default=3)
    min_wagered_to_qualify = models.DecimalField(max_digits=18, decimal_places=2, default=20)

    # Периоды расчёта
    commission_period = models.CharField(
        max_length=20,
        choices=(
            ('daily', 'Ежедневно'),
            ('weekly', 'Еженедельно'),
            ('monthly', 'Ежемесячно')
        ),
        default='daily'
    )

    # Ограничения
    max_referrals_per_ip = models.IntegerField(default=3)
    max_referrals_per_day = models.IntegerField(default=50)

    # Антифрод
    min_time_between_registrations = models.IntegerField(default=60)
    suspicious_patterns_enabled = models.BooleanField(default=True)
    auto_block_on_fraud = models.BooleanField(default=True)

    # 2-й уровень
    level2_enabled = models.BooleanField(default=True)

    # Метод вывода
    payout_to_game_balance = models.BooleanField(default=True)
    payout_to_wallet = models.BooleanField(default=True)
    payout_direct_crypto = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Настройки реферальной программы'

    @classmethod
    def get_settings(cls):
        return cls.objects.first() or cls.objects.create()
