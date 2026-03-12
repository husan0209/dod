import secrets
import uuid
from decimal import Decimal
from datetime import timedelta
from typing import Optional

from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinLengthValidator, MinValueValidator
from django.db import models
from django.utils import timezone
from django_countries.fields import CountryField
from phonenumber_field.modelfields import PhoneNumberField
from timezone_field import TimeZoneField

from apps.accounts.managers import UserManager
from apps.accounts.validators import username_validator, validate_avatar_file


def notification_default():
    return {
        "site_notifications": True,
        "email_notifications": True,
        "telegram_notifications": False,
        "bet_results": True,
        "promotions": True,
        "security_alerts": True,
        "referral_activity": True,
    }


def email_token_expires_default():
    return timezone.now() + timedelta(hours=24)


def phone_token_expires_default():
    return timezone.now() + timedelta(minutes=10)


def avatar_upload_path(instance, filename: str) -> str:
    return f"avatars/{instance.id}/{filename}"


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, max_length=255, db_index=True)
    username = models.CharField(
        max_length=30,
        unique=True,
        validators=[
            MinLengthValidator(3),
            username_validator,
        ],
    )
    phone = PhoneNumberField(unique=True, null=True, blank=True, db_index=True)
    password = models.CharField(max_length=128, null=True, blank=True)
    first_name = models.CharField(max_length=50, blank=True)
    last_name = models.CharField(max_length=50, blank=True)
    avatar = models.ImageField(upload_to=avatar_upload_path, null=True, blank=True, validators=[validate_avatar_file])
    date_of_birth = models.DateField(null=True, blank=True)
    country = CountryField(null=True, blank=True)
    language = models.CharField(max_length=2, choices=[('ru', 'Русский'), ('en', 'English')], default='ru')
    timezone = TimeZoneField(default='Europe/Moscow')
    preferred_currency = models.CharField(
        max_length=5,
        choices=[
            ('USD', 'USD'), ('EUR', 'EUR'), ('RUB', 'RUB'), ('UAH', 'UAH'), ('KZT', 'KZT'),
            ('UZS', 'UZS'), ('BYN', 'BYN'), ('BTC', 'BTC'), ('ETH', 'ETH'), ('USDT', 'USDT'),
            ('TON', 'TON'),
        ],
        default='USD',
    )
    balance = models.DecimalField(max_digits=18, decimal_places=8, default=Decimal('0'), validators=[MinValueValidator(0)])
    is_email_verified = models.BooleanField(default=False)
    is_phone_verified = models.BooleanField(default=False)
    is_2fa_enabled = models.BooleanField(default=False)
    two_fa_method = models.CharField(
        max_length=10,
        choices=[('totp', 'Google Authenticator'), ('email', 'Email код')],
        null=True,
        blank=True,
    )
    kyc_status = models.CharField(
        max_length=10,
        choices=[('none', 'Не подана'), ('pending', 'На проверке'), ('approved', 'Одобрена'), ('rejected', 'Отклонена')],
        default='none',
    )
    trust_level = models.IntegerField(
        choices=[(1, 'Новый'), (2, 'Базовый'), (3, 'Проверенный'), (4, 'Доверенный'), (5, 'VIP')],
        default=1,
    )
    is_online = models.BooleanField(default=False)
    last_activity = models.DateTimeField(null=True, blank=True)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    registration_ip = models.GenericIPAddressField(null=True, blank=True)
    registration_method = models.CharField(
        max_length=10,
        choices=[('email', 'Email'), ('google', 'Google'), ('telegram', 'Telegram'), ('phone', 'Телефон')],
        default='email',
    )
    referred_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='referrals')
    referral_code = models.CharField(max_length=20, unique=True, blank=True)
    notification_settings = models.JSONField(default=notification_default)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    objects = UserManager()

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        if not self.referral_code:
            self.referral_code = self.generate_referral_code()
        if self.email:
            self.email = self.email.lower()
        if self.username:
            self.username = self.username.lower()
        super().save(*args, **kwargs)

    def generate_referral_code(self) -> str:
        while True:
            code = f"DOD-{secrets.token_urlsafe(4).replace('-', '').upper()[:6]}"
            if not User.objects.filter(referral_code=code).exists():
                return code

    def has_password(self) -> bool:
        return bool(self.password)

    def is_fully_verified(self) -> bool:
        return self.is_email_verified or self.is_phone_verified

    def get_balance_display(self) -> str:
        return f"{self.balance} {self.preferred_currency}"

    def get_avatar_url(self) -> Optional[str]:
        if self.avatar:
            return self.avatar.url
        initials = ''.join([p[0] for p in f"{self.first_name} {self.last_name}".strip().split() if p]) or self.username[:2]
        return f"https://ui-avatars.com/api/?name={initials}" if initials else None

    def get_trust_level_display_extended(self) -> str:
        mapping = {
            1: "🔵 Новый",
            2: "🟢 Базовый",
            3: "🟡 Проверенный",
            4: "🟠 Доверенный",
            5: "💎 VIP",
        }
        return mapping.get(self.trust_level, "🔵 Новый")

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['username']),
            models.Index(fields=['phone']),
            models.Index(fields=['referral_code']),
            models.Index(fields=['created_at']),
        ]
        constraints = [
            models.CheckConstraint(check=models.Q(balance__gte=0), name='user_balance_non_negative'),
        ]


class LoginHistory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='login_history')
    ip_address = models.GenericIPAddressField()
    country = models.CharField(max_length=100, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    device_type = models.CharField(max_length=20, choices=[('desktop', 'Компьютер'), ('mobile', 'Мобильный'), ('tablet', 'Планшет'), ('unknown', 'Неизвестно')])
    browser = models.CharField(max_length=100)
    os = models.CharField(max_length=100)
    device_name = models.CharField(max_length=200)
    user_agent = models.TextField()
    login_method = models.CharField(
        max_length=20,
        choices=[('email', 'Email + пароль'), ('google', 'Google'), ('telegram', 'Telegram'), ('phone', 'Телефон + SMS')],
    )
    is_successful = models.BooleanField(default=True)
    failure_reason = models.CharField(max_length=50, null=True, blank=True)
    is_suspicious = models.BooleanField(default=False)
    session_key = models.CharField(max_length=40, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'История входов'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['ip_address']),
        ]


class ActiveSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='active_sessions')
    session_key = models.CharField(max_length=40, unique=True)
    ip_address = models.GenericIPAddressField()
    device_type = models.CharField(max_length=20)
    browser = models.CharField(max_length=100)
    os = models.CharField(max_length=100)
    device_name = models.CharField(max_length=200)
    country = models.CharField(max_length=100, null=True, blank=True)
    is_current = models.BooleanField(default=False)
    last_activity = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Активная сессия'
        ordering = ['-last_activity']


class EmailVerification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    email = models.EmailField()
    token = models.CharField(max_length=64, unique=True)
    is_used = models.BooleanField(default=False)
    expires_at = models.DateTimeField(default=email_token_expires_default)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self) -> bool:
        return self.expires_at < timezone.now()

    def is_valid(self) -> bool:
        return not self.is_used and not self.is_expired()

    class Meta:
        ordering = ['-created_at']


class PhoneVerification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    phone = PhoneNumberField()
    code = models.CharField(max_length=6)
    is_used = models.BooleanField(default=False)
    attempts = models.IntegerField(default=0)
    expires_at = models.DateTimeField(default=phone_token_expires_default)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class BackupCode(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='backup_codes')
    code = models.CharField(max_length=128)
    is_used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def set_plain_code(self, plain_code: str):
        self.code = make_password(plain_code)


class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('general', 'Общее'),
        ('bet_result', 'Результат ставки'),
        ('deposit', 'Депозит'),
        ('withdrawal', 'Вывод'),
        ('kyc', 'Верификация'),
        ('security', 'Безопасность'),
        ('referral', 'Рефералы'),
        ('promotion', 'Акции'),
        ('ticket_created', 'Тикет создан'),
        ('ticket_reply', 'Ответ на тикет'),
        ('ticket_resolved', 'Тикет решён'),
        ('ticket_reopened', 'Тикет переоткрыт'),
        ('payout_completed', 'Выплата завершена'),
        ('payout_rejected', 'Выплата отклонена'),
        ('partner_tier_up', 'Повышение уровня партнёра'),
        ('partner_tier_down', 'Понижение уровня партнёра'),
        ('new_referral', 'Новый реферал'),
        ('referral_commission', 'Комиссия от реферала'),
        ('referral_qualified', 'Реферал квалифицирован'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPES, default='general')
    title = models.CharField(max_length=200)
    message = models.TextField()
    icon = models.CharField(max_length=10, blank=True)
    link = models.URLField(blank=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Уведомление'
        verbose_name_plural = 'Уведомления'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read', 'created_at']),
            models.Index(fields=['notification_type']),
        ]

    def __str__(self):
        return f"{self.user.username}: {self.title}"

    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])


class AdminActionLog(models.Model):
    admin_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action_type = models.CharField(max_length=100)
    target_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='admin_actions')
    description = models.TextField()
    details = models.JSONField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # Extended fields for audit
    module = models.CharField(max_length=50)
    action_category = models.CharField(max_length=50)
    data_before = models.JSONField(null=True, blank=True)
    data_after = models.JSONField(null=True, blank=True)
    is_successful = models.BooleanField(default=True)
    error_message = models.TextField(blank=True)
    duration_ms = models.IntegerField(default=0)

    class Meta:
        verbose_name = 'Действие администратора'
        verbose_name_plural = 'Действия администраторов'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['admin_user', 'created_at']),
            models.Index(fields=['target_user']),
            models.Index(fields=['module']),
            models.Index(fields=['action_type']),
        ]


class TOTPDevice(models.Model):
    """
    Модель для хранения TOTP (Time-based One-Time Password) устройств пользователя.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='totp_devices')
    name = models.CharField(max_length=50, default='TOTP')
    secret = models.CharField(max_length=32)  # Base32 encoded secret
    confirmed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'TOTP устройство'
        verbose_name_plural = 'TOTP устройства'
        ordering = ['-created_at']
        unique_together = [['user', 'name']]
        indexes = [
            models.Index(fields=['user', 'confirmed']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.name}"


class LinkedAccount(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='linked_accounts')
    provider = models.CharField(
        max_length=20,
        choices=[('google', 'Google'), ('telegram', 'Telegram'), ('phone', 'Телефон')]
    )
    provider_id = models.CharField(max_length=255)
    provider_email = models.EmailField(null=True, blank=True)
    provider_username = models.CharField(max_length=255, null=True, blank=True)
    provider_avatar = models.URLField(null=True, blank=True)
    is_primary = models.BooleanField(default=False)
    linked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Привязанный аккаунт'
        verbose_name_plural = 'Привязанные аккаунты'
        unique_together = [['provider', 'provider_id']]
        ordering = ['-linked_at']
        indexes = [
            models.Index(fields=['user', 'provider']),
            models.Index(fields=['provider', 'provider_id']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.provider}"
