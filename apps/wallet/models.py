import uuid
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

import base64
import hashlib
import hmac

from django.conf import settings
from django.core.cache import cache
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.utils import timezone
from django_countries.fields import CountryField


class Currency(models.Model):
    TYPE_CHOICES = [
        ("fiat", "Фиатная"),
        ("crypto", "Криптовалюта"),
    ]

    code = models.CharField(max_length=10, primary_key=True)
    name = models.CharField(max_length=100)
    symbol = models.CharField(max_length=10)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    decimal_places = models.IntegerField()
    rate_to_usd = models.DecimalField(max_digits=20, decimal_places=10)
    rate_updated_at = models.DateTimeField(null=True, blank=True)
    min_deposit = models.DecimalField(max_digits=18, decimal_places=8, default=Decimal("0"))
    min_withdrawal = models.DecimalField(max_digits=18, decimal_places=8, default=Decimal("0"))
    max_withdrawal_daily = models.DecimalField(max_digits=18, decimal_places=8, default=Decimal("0"))
    withdrawal_fee_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0"))
    withdrawal_fee_fixed = models.DecimalField(max_digits=18, decimal_places=8, default=Decimal("0"))
    conversion_fee_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("1.0"))
    is_active = models.BooleanField(default=True)
    is_deposit_enabled = models.BooleanField(default=True)
    is_withdrawal_enabled = models.BooleanField(default=True)
    icon = models.CharField(max_length=50, blank=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Валюта"
        verbose_name_plural = "Валюты"
        ordering = ["sort_order", "code"]
        indexes = [models.Index(fields=["is_active"])]

    def __str__(self) -> str:
        return f"{self.code} ({self.symbol})"

    def format_amount(self, amount: Decimal) -> str:
        q = Decimal(1) / (Decimal(10) ** self.decimal_places)
        value = amount.quantize(q, rounding=ROUND_HALF_UP)
        return f"{self.symbol}{value}" if self.symbol else str(value)

    def convert_to_usd(self, amount: Decimal) -> Decimal:
        return (amount * self.rate_to_usd).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def convert_from_usd(self, usd_amount: Decimal) -> Decimal:
        if self.rate_to_usd == 0:
            return Decimal("0")
        q = Decimal(1) / (Decimal(10) ** self.decimal_places)
        return (usd_amount / self.rate_to_usd).quantize(q, rounding=ROUND_HALF_UP)


class Wallet(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wallet")
    primary_currency = models.ForeignKey(Currency, on_delete=models.PROTECT, default="USD")
    total_deposited = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))
    total_withdrawn = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))
    total_wagered = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))
    total_won = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))
    is_frozen = models.BooleanField(default=False)
    frozen_reason = models.TextField(null=True, blank=True)
    frozen_at = models.DateTimeField(null=True, blank=True)
    frozen_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="frozen_wallets")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Кошелёк"
        verbose_name_plural = "Кошельки"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["is_frozen"]),
        ]

    def get_balance(self, currency_code: str) -> Decimal:
        try:
            balance = self.balances.get(currency_id=currency_code)
            return balance.available
        except WalletBalance.DoesNotExist:
            return Decimal("0")

    def get_total_balance_usd(self) -> Decimal:
        total = Decimal("0")
        for b in self.balances.select_related("currency"):
            total += b.total * b.currency.rate_to_usd
        return total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def get_primary_balance(self) -> Decimal:
        return self.get_balance(self.primary_currency_id)

    def get_primary_balance_display(self) -> str:
        return self.primary_currency.format_amount(self.get_primary_balance())

    def has_sufficient_balance(self, currency_code: str, amount: Decimal) -> bool:
        return self.get_balance(currency_code) >= amount


class WalletBalance(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name="balances")
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT)
    available = models.DecimalField(max_digits=18, decimal_places=8, default=Decimal("0"), validators=[MinValueValidator(0)])
    frozen = models.DecimalField(max_digits=18, decimal_places=8, default=Decimal("0"), validators=[MinValueValidator(0)])
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Баланс валюты"
        verbose_name_plural = "Балансы валют"
        unique_together = ["wallet", "currency"]
        constraints = [
            models.CheckConstraint(check=models.Q(available__gte=0), name="wallet_balance_available_non_negative"),
            models.CheckConstraint(check=models.Q(frozen__gte=0), name="wallet_balance_frozen_non_negative"),
        ]
        indexes = [models.Index(fields=["wallet", "currency"])]

    @property
    def total(self) -> Decimal:
        return self.available + self.frozen

    # The following helpers should be called only via services, not directly from views.
    def credit(self, amount: Decimal) -> None:
        if amount <= 0:
            raise ValueError("Amount must be positive")
        self.available = (self.available + amount).quantize(Decimal("0.00000001"))

    def debit(self, amount: Decimal) -> None:
        if amount <= 0:
            raise ValueError("Amount must be positive")
        if self.available < amount:
            raise ValueError("Insufficient funds")
        self.available = (self.available - amount).quantize(Decimal("0.00000001"))

    def freeze(self, amount: Decimal) -> None:
        if amount <= 0:
            raise ValueError("Amount must be positive")
        if self.available < amount:
            raise ValueError("Insufficient funds to freeze")
        self.available = (self.available - amount).quantize(Decimal("0.00000001"))
        self.frozen = (self.frozen + amount).quantize(Decimal("0.00000001"))

    def unfreeze(self, amount: Decimal) -> None:
        if amount <= 0:
            raise ValueError("Amount must be positive")
        if self.frozen < amount:
            raise ValueError("Not enough frozen funds")
        self.frozen = (self.frozen - amount).quantize(Decimal("0.00000001"))
        self.available = (self.available + amount).quantize(Decimal("0.00000001"))

    def settle_frozen(self, amount: Decimal) -> None:
        if amount <= 0:
            raise ValueError("Amount must be positive")
        if self.frozen < amount:
            raise ValueError("Not enough frozen funds to settle")
        self.frozen = (self.frozen - amount).quantize(Decimal("0.00000001"))


def _generate_txn_id() -> str:
    return f"TXN-{timezone.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"


class Transaction(models.Model):
    TYPE_CHOICES = [
        ("deposit", "Пополнение"),
        ("withdrawal", "Вывод"),
        ("bet", "Ставка"),
        ("win", "Выигрыш"),
        ("refund", "Возврат"),
        ("bonus", "Бонус"),
        ("referral", "Реферальная комиссия"),
        ("conversion_debit", "Конвертация (списание)"),
        ("conversion_credit", "Конвертация (зачисление)"),
        ("freeze", "Заморозка"),
        ("unfreeze", "Разморозка"),
        ("fee", "Комиссия"),
        ("adjustment", "Корректировка (админ)"),
    ]

    STATUS_CHOICES = [
        ("pending", "В обработке"),
        ("completed", "Завершена"),
        ("failed", "Ошибка"),
        ("cancelled", "Отменена"),
        ("rejected", "Отклонена"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    transaction_id = models.CharField(max_length=50, unique=True, default=_generate_txn_id)
    wallet = models.ForeignKey(Wallet, on_delete=models.PROTECT)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=18, decimal_places=8)
    amount_usd = models.DecimalField(max_digits=18, decimal_places=2)
    fee_amount = models.DecimalField(max_digits=18, decimal_places=8, default=Decimal("0"))
    balance_before = models.DecimalField(max_digits=18, decimal_places=8)
    balance_after = models.DecimalField(max_digits=18, decimal_places=8)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="completed")
    reference_type = models.CharField(max_length=50, null=True, blank=True)
    reference_id = models.CharField(max_length=100, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="created_transactions")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Транзакция"
        verbose_name_plural = "Транзакции"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["wallet", "created_at"]),
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["type"]),
            models.Index(fields=["status"]),
            models.Index(fields=["reference_type", "reference_id"]),
            models.Index(fields=["transaction_id"]),
        ]
        constraints = [
            models.CheckConstraint(check=models.Q(amount__gt=0), name="transaction_amount_positive"),
            models.CheckConstraint(check=models.Q(amount_usd__gte=0), name="transaction_amount_usd_non_negative"),
        ]

    def __str__(self) -> str:
        sign = "+" if self.is_credit else "-"
        return f"{self.transaction_id}: {self.type} {sign}{self.amount} {self.currency_id}"

    @property
    def is_credit(self) -> bool:
        return self.type in {
            "deposit",
            "win",
            "refund",
            "bonus",
            "referral",
            "conversion_credit",
            "unfreeze",
        }

    @property
    def is_debit(self) -> bool:
        return not self.is_credit

    def get_signed_amount(self) -> Decimal:
        return self.amount if self.is_credit else -self.amount

    def get_type_icon(self) -> str:
        mapping = {
            "deposit": "📥",
            "withdrawal": "📤",
            "bet": "🎯",
            "win": "🏆",
            "refund": "↩️",
            "bonus": "🎁",
            "referral": "🤝",
            "conversion_debit": "🔄",
            "conversion_credit": "🔄",
            "freeze": "🧊",
            "unfreeze": "🔥",
            "fee": "💸",
            "adjustment": "⚙️",
        }
        return mapping.get(self.type, "❔")


def _withdrawal_expires_default():
    return timezone.now() + timedelta(hours=72)


def _generate_withdrawal_id() -> str:
    return f"WD-{timezone.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"


class WithdrawalRequest(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ("card", "Банковская карта"),
        ("crypto", "Криптовалюта"),
        ("ewallet", "Электронный кошелёк"),
    ]

    STATUS_CHOICES = [
        ("pending", "Ожидает обработки"),
        ("auto_approved", "Автоматически одобрена"),
        ("manual_review", "На ручной проверке"),
        ("approved", "Одобрена"),
        ("processing", "Обрабатывается"),
        ("completed", "Выполнена"),
        ("rejected", "Отклонена"),
        ("cancelled", "Отменена пользователем"),
    ]

    RISK_CHOICES = [
        ("low", "🟢 Низкий"),
        ("medium", "🟡 Средний"),
        ("high", "🔴 Высокий"),
        ("critical", "⛔ Критический"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    request_id = models.CharField(max_length=50, unique=True, default=_generate_withdrawal_id)
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=18, decimal_places=8)
    fee_amount = models.DecimalField(max_digits=18, decimal_places=8, default=Decimal("0"))
    net_amount = models.DecimalField(max_digits=18, decimal_places=8, default=Decimal("0"))
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    payment_details = models.JSONField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    risk_level = models.CharField(max_length=10, choices=RISK_CHOICES, default="low")
    risk_factors = models.JSONField(default=list, blank=True)
    auto_withdrawal_limit = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="reviewed_withdrawals")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_comment = models.TextField(null=True, blank=True)
    rejection_reason = models.CharField(max_length=100, null=True, blank=True)
    transaction = models.OneToOneField(Transaction, null=True, blank=True, on_delete=models.SET_NULL, related_name="withdrawal_request")
    external_id = models.CharField(max_length=100, null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(default=_withdrawal_expires_default)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Заявка на вывод"
        verbose_name_plural = "Заявки на вывод"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["risk_level"]),
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["wallet", "status"]),
        ]
        constraints = [
            models.CheckConstraint(check=models.Q(amount__gt=0), name="withdrawal_amount_positive"),
            models.CheckConstraint(check=models.Q(net_amount__gte=0), name="withdrawal_net_amount_non_negative"),
        ]

    def calculate_risk_level(
        self,
        account_age_hours: int | None = None,
        recent_withdrawals_count: int = 0,
        kyc_required_amount: Decimal | None = None,
        usual_country: str | None = None,
        current_country: str | None = None,
        unknown_device: bool = False,
        last_deposit_at=None,
    ) -> None:
        """Расчёт факторов риска согласно ТЗ.

        Факторы:
          - новый аккаунт < 24ч
          - сумма > 0.5 * max_daily_withdrawal_usd
          - нет ставок после последнего депозита
          - смена IP vs registration_ip
          - kyc не пройдена при сумме > порога
          - 3+ выводов за последний час
          - неизвестное устройство
          - необычная страна
          - выводы ~= депозитам
        """

        risk_factors: list[str] = []
        now = timezone.now()
        if account_age_hours is None and self.user.created_at:
            account_age_hours = int((now - self.user.created_at).total_seconds() // 3600)
        if account_age_hours is not None and account_age_hours < 24:
            risk_factors.append("new_account")

        amount_usd = self.amount * self.currency.rate_to_usd
        settings_obj = WalletSettings.get_settings()
        kyc_required_amount = kyc_required_amount or settings_obj.kyc_required_amount
        if amount_usd > settings_obj.max_daily_withdrawal_usd * Decimal("0.5"):
            risk_factors.append("large_amount")

        if last_deposit_at:
            from apps.wallet.models import Transaction

            has_bets = Transaction.objects.filter(
                user=self.user,
                type="bet",
                created_at__gte=last_deposit_at,
            ).exists()
            if not has_bets:
                risk_factors.append("no_bets")

        if self.user.registration_ip and self.ip_address and self.ip_address != self.user.registration_ip:
            risk_factors.append("ip_changed")

        if self.user.kyc_status != "approved" and amount_usd > kyc_required_amount:
            risk_factors.append("kyc_not_passed")

        if recent_withdrawals_count >= 3:
            risk_factors.append("multiple_withdrawals")

        if usual_country and current_country and usual_country != current_country:
            risk_factors.append("unusual_country")

        if unknown_device:
            risk_factors.append("unknown_device")

        if self.wallet.total_withdrawn and self.wallet.total_deposited and self.wallet.total_withdrawn > self.wallet.total_deposited * Decimal("0.9"):
            risk_factors.append("withdrawal_exceeds_deposits")

        self.risk_factors = risk_factors
        if len(risk_factors) == 0:
            self.risk_level = "low"
        elif len(risk_factors) <= 2:
            self.risk_level = "medium"
        elif len(risk_factors) <= 4:
            self.risk_level = "high"
        else:
            self.risk_level = "critical"

    def can_auto_approve(self) -> bool:
        settings_obj = WalletSettings.get_settings()
        limit = self.auto_withdrawal_limit or settings_obj.auto_withdrawal_limit_default
        if self.user.trust_level >= 4:
            limit = settings_obj.auto_withdrawal_limit_trusted
        elif self.user.kyc_status == "approved":
            limit = settings_obj.auto_withdrawal_limit_verified
        return (
            self.risk_level == "low"
            and self.amount * self.currency.rate_to_usd <= limit
            and self.user.trust_level >= 2
            and (self.user.kyc_status == "approved" or self.amount * self.currency.rate_to_usd <= settings_obj.kyc_required_amount)
            and not self.wallet.is_frozen
        )


class ConversionOrder(models.Model):
    STATUS_CHOICES = [
        ("completed", "Завершена"),
        ("failed", "Ошибка"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    from_currency = models.ForeignKey(Currency, on_delete=models.PROTECT, related_name="conversions_from")
    to_currency = models.ForeignKey(Currency, on_delete=models.PROTECT, related_name="conversions_to")
    from_amount = models.DecimalField(max_digits=18, decimal_places=8)
    to_amount = models.DecimalField(max_digits=18, decimal_places=8)
    exchange_rate = models.DecimalField(max_digits=20, decimal_places=10)
    fee_percent = models.DecimalField(max_digits=5, decimal_places=2)
    fee_amount = models.DecimalField(max_digits=18, decimal_places=8)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="completed")
    debit_transaction = models.ForeignKey(Transaction, on_delete=models.PROTECT, related_name="conversion_debit")
    credit_transaction = models.ForeignKey(Transaction, on_delete=models.PROTECT, related_name="conversion_credit")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Конвертация"
        verbose_name_plural = "Конвертации"
        ordering = ["-created_at"]


class KYCVerification(models.Model):
    STATUS_CHOICES = [
        ("not_submitted", "Не подана"),
        ("pending", "На проверке"),
        ("approved", "Одобрена"),
        ("rejected", "Отклонена"),
    ]

    DOCUMENT_CHOICES = [
        ("passport", "Паспорт"),
        ("national_id", "ID карта"),
        ("drivers_license", "Водительское удостоверение"),
    ]

    REJECTION_CHOICES = [
        ("blurry", "Нечёткое фото"),
        ("expired", "Документ просрочен"),
        ("mismatch", "Данные не совпадают"),
        ("fake", "Подозрение на подделку"),
        ("other", "Другое"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="kyc")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="not_submitted")
    document_type = models.CharField(max_length=20, choices=DOCUMENT_CHOICES, null=True, blank=True)
    def _document_upload_path(instance, filename: str, kind: str) -> str:
        user_id = instance.user_id or "anon"
        return f"kyc/{user_id}/{kind}_{timezone.now().strftime('%Y%m%d%H%M%S')}_{filename}"

    def document_front_path(instance, filename: str) -> str:
        return KYCVerification._document_upload_path(instance, filename, "front")

    def document_back_path(instance, filename: str) -> str:
        return KYCVerification._document_upload_path(instance, filename, "back")

    def selfie_upload_path(instance, filename: str) -> str:
        return KYCVerification._document_upload_path(instance, filename, "selfie")

    document_front = models.ImageField(upload_to=document_front_path, null=True, blank=True)
    document_back = models.ImageField(upload_to=document_back_path, null=True, blank=True)
    selfie_with_document = models.ImageField(upload_to=selfie_upload_path, null=True, blank=True)
    full_name = models.CharField(max_length=200)
    document_number = models.CharField(max_length=50, help_text="Хранится в зашифрованном виде")
    document_number_encrypted = models.BinaryField(null=True, blank=True, editable=False)
    date_of_birth = models.DateField()
    country_of_issue = CountryField()
    expiry_date = models.DateField(null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="reviewed_kyc")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_comment = models.TextField(null=True, blank=True)
    rejection_reason = models.CharField(max_length=20, choices=REJECTION_CHOICES, null=True, blank=True)
    attempts = models.IntegerField(default=0)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "KYC Верификация"
        verbose_name_plural = "KYC Верификации"
        ordering = ["-created_at"]

    def is_expired(self) -> bool:
        return bool(self.expiry_date and timezone.now().date() > self.expiry_date)

    def can_resubmit(self) -> bool:
        return self.attempts < 3 and self.status == "rejected"

    def _derive_key(self) -> bytes:
        # Simple HMAC-based key derivation to avoid external deps
        secret = settings.SECRET_KEY.encode("utf-8")
        return hmac.new(secret, b"kyc-doc", hashlib.sha256).digest()

    def set_document_number(self, value: str) -> None:
        if not value:
            self.document_number = ""
            self.document_number_encrypted = None
            return
        key = self._derive_key()
        data = value.encode("utf-8")
        cipher = bytes([b ^ key[i % len(key)] for i, b in enumerate(data)])
        self.document_number_encrypted = cipher
        self.document_number = "enc::" + base64.b64encode(cipher).decode("utf-8")

    def get_document_number_decrypted(self) -> str:
        if not self.document_number_encrypted:
            return ""
        key = self._derive_key()
        cipher = self.document_number_encrypted
        data = bytes([b ^ key[i % len(key)] for i, b in enumerate(cipher)])
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError:
            return ""


class WalletSettings(models.Model):
    singleton_id = models.IntegerField(default=1, unique=True, editable=False)
    auto_withdrawal_limit_default = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("100"))
    auto_withdrawal_limit_verified = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("5000"))
    auto_withdrawal_limit_trusted = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("10000"))
    kyc_required_amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("1000"))
    max_daily_withdrawal_usd = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("50000"))
    new_account_withdrawal_delay_hours = models.IntegerField(default=24)
    min_bets_before_withdrawal = models.IntegerField(default=0)
    conversion_enabled = models.BooleanField(default=True)
    registration_bonus_amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))
    registration_bonus_currency = models.CharField(max_length=10, default="USD")

    class Meta:
        verbose_name = "Настройки кошелька"
        indexes = [models.Index(fields=["singleton_id"])]

    @classmethod
    def get_settings(cls):
        cache_key = "wallet_settings_singleton"
        settings_obj = cache.get(cache_key)
        if settings_obj:
            return settings_obj
        with transaction.atomic():
            settings_obj, _ = cls.objects.get_or_create(singleton_id=1)
        cache.set(cache_key, settings_obj, 300)
        return settings_obj
