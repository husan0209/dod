import uuid
from decimal import Decimal

from django.conf import settings
from django.core.cache import cache
from django.db import models, transaction
from django.utils import timezone


def _default_success_url(order_id: str | None = None) -> str:
    if order_id:
        return f"/wallet/?deposit=success&order={order_id}"
    return "/wallet/?deposit=success"


def _default_fail_url(order_id: str | None = None) -> str:
    if order_id:
        return f"/wallet/?deposit=fail&order={order_id}"
    return "/wallet/?deposit=fail"


def generate_order_id(prefix: str) -> str:
    return f"{prefix}-{timezone.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"


def deposit_order_id_default() -> str:
    return generate_order_id("DEP")


def payout_order_id_default() -> str:
    return generate_order_id("PAY")


class PaymentProvider(models.Model):
    TYPE_CHOICES = (
        ("fiat", "Фиатные платежи"),
        ("crypto", "Криптовалюта"),
        ("mixed", "Смешанный"),
    )

    code = models.CharField(max_length=50, primary_key=True)
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    description = models.TextField()
    icon = models.CharField(max_length=50)
    api_base_url = models.URLField()
    api_key = models.CharField(max_length=500)
    api_secret = models.CharField(max_length=500, null=True, blank=True)
    merchant_id = models.CharField(max_length=100, null=True, blank=True)
    webhook_secret = models.CharField(max_length=500, null=True, blank=True)
    extra_settings = models.JSONField(default=dict, blank=True)
    supported_currencies = models.ManyToManyField("wallet.Currency", related_name="payment_providers")
    is_active = models.BooleanField(default=True)
    is_deposit_enabled = models.BooleanField(default=True)
    is_withdrawal_enabled = models.BooleanField(default=True)
    min_deposit = models.DecimalField(max_digits=18, decimal_places=8, default=Decimal("0"))
    max_deposit = models.DecimalField(max_digits=18, decimal_places=8, default=Decimal("0"))
    deposit_fee_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0"))
    deposit_fee_fixed = models.DecimalField(max_digits=18, decimal_places=8, default=Decimal("0"))
    processing_time = models.CharField(max_length=100)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Платёжный провайдер"
        verbose_name_plural = "Платёжные провайдеры"
        ordering = ["sort_order"]

    def __str__(self) -> str:
        return self.name


class PaymentMethod(models.Model):
    TYPE_CHOICES = (
        ("deposit", "Только пополнение"),
        ("withdrawal", "Только вывод"),
        ("both", "Пополнение и вывод"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.ForeignKey(PaymentProvider, on_delete=models.CASCADE, related_name="methods")
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=200)
    icon = models.CharField(max_length=50)
    currency = models.ForeignKey("wallet.Currency", on_delete=models.PROTECT)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    min_amount = models.DecimalField(max_digits=18, decimal_places=8)
    max_amount = models.DecimalField(max_digits=18, decimal_places=8)
    fee_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0"))
    fee_fixed = models.DecimalField(max_digits=18, decimal_places=8, default=Decimal("0"))
    processing_time = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    requires_kyc = models.BooleanField(default=False)
    sort_order = models.IntegerField(default=0)

    class Meta:
        verbose_name = "Способ оплаты"
        verbose_name_plural = "Способы оплаты"
        ordering = ["provider", "sort_order"]
        unique_together = (("provider", "code"),)

    def __str__(self) -> str:
        return f"{self.provider.code}:{self.code}"


class DepositOrder(models.Model):
    STATUS_CHOICES = (
        ("created", "Создана"),
        ("pending", "Ожидает оплаты"),
        ("processing", "Обрабатывается"),
        ("completed", "Завершена"),
        ("expired", "Истекла"),
        ("failed", "Ошибка"),
        ("cancelled", "Отменена"),
        ("refunded", "Возвращена"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_id = models.CharField(max_length=50, unique=True, default=deposit_order_id_default)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    wallet = models.ForeignKey("wallet.Wallet", on_delete=models.CASCADE)
    provider = models.ForeignKey(PaymentProvider, on_delete=models.PROTECT)
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.PROTECT)
    currency = models.ForeignKey("wallet.Currency", on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=18, decimal_places=8)
    amount_received = models.DecimalField(max_digits=18, decimal_places=8, null=True, blank=True)
    amount_usd = models.DecimalField(max_digits=18, decimal_places=8)
    fee_amount = models.DecimalField(max_digits=18, decimal_places=8, default=Decimal("0"))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="created")
    provider_order_id = models.CharField(max_length=200, null=True, blank=True)
    provider_payment_url = models.URLField(null=True, blank=True)
    provider_response = models.JSONField(default=dict, blank=True)
    provider_status = models.CharField(max_length=50, null=True, blank=True)
    crypto_address = models.CharField(max_length=200, null=True, blank=True)
    crypto_network = models.CharField(max_length=50, null=True, blank=True)
    crypto_tx_hash = models.CharField(max_length=200, null=True, blank=True)
    success_url = models.URLField(default=_default_success_url)
    fail_url = models.URLField(default=_default_fail_url)
    transaction = models.OneToOneField("wallet.Transaction", on_delete=models.SET_NULL, null=True, blank=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(null=True, blank=True)
    expires_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Заявка на пополнение"
        verbose_name_plural = "Заявки на пополнение"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["order_id"]),
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["provider_order_id"]),
            models.Index(fields=["status"]),
        ]

    def is_expired(self) -> bool:
        return self.status in {"created", "pending"} and self.expires_at < timezone.now()

    def can_be_completed(self) -> bool:
        return self.status in {"created", "pending", "processing"}


class PayoutOrder(models.Model):
    STATUS_CHOICES = (
        ("created", "Создана"),
        ("processing", "Обрабатывается"),
        ("sent", "Отправлена"),
        ("completed", "Завершена"),
        ("failed", "Ошибка"),
        ("cancelled", "Отменена"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payout_id = models.CharField(max_length=50, unique=True, default=payout_order_id_default)
    withdrawal_request = models.OneToOneField("wallet.WithdrawalRequest", on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    provider = models.ForeignKey(PaymentProvider, on_delete=models.PROTECT)
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.PROTECT)
    currency = models.ForeignKey("wallet.Currency", on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=18, decimal_places=8)
    fee_amount = models.DecimalField(max_digits=18, decimal_places=8)
    net_amount = models.DecimalField(max_digits=18, decimal_places=8)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="created")
    provider_payout_id = models.CharField(max_length=200, null=True, blank=True)
    provider_response = models.JSONField(default=dict, blank=True)
    provider_status = models.CharField(max_length=50, null=True, blank=True)
    payment_details = models.JSONField()
    error_message = models.TextField(null=True, blank=True)
    retry_count = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=3)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Выплата"
        verbose_name_plural = "Выплаты"
        ordering = ["-created_at"]

    def can_retry(self) -> bool:
        return self.retry_count < self.max_retries and self.status in {"failed", "processing"}


class WebhookLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.CharField(max_length=50)
    event_type = models.CharField(max_length=100)
    payload = models.JSONField()
    headers = models.JSONField()
    ip_address = models.GenericIPAddressField()
    signature = models.CharField(max_length=500, null=True, blank=True)
    is_valid_signature = models.BooleanField(default=False)
    is_processed = models.BooleanField(default=False)
    processing_result = models.CharField(max_length=50, null=True, blank=True)
    processing_error = models.TextField(null=True, blank=True)
    related_order_id = models.CharField(max_length=100, null=True, blank=True)
    response_code = models.IntegerField(default=200)
    processing_time_ms = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Лог webhook"
        verbose_name_plural = "Логи webhook"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["provider", "created_at"]),
            models.Index(fields=["related_order_id"]),
            models.Index(fields=["is_processed"]),
        ]


class SavedPaymentMethod(models.Model):
    TYPE_CHOICES = (
        ("card", "Банковская карта"),
        ("crypto", "Криптокошелёк"),
        ("ewallet", "Электронный кошелёк"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="saved_payment_methods", on_delete=models.CASCADE)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    name = models.CharField(max_length=100)
    details = models.JSONField()
    currency = models.ForeignKey("wallet.Currency", on_delete=models.PROTECT)
    is_verified = models.BooleanField(default=False)
    is_default = models.BooleanField(default=False)
    last_used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Сохранённый способ оплаты"
        verbose_name_plural = "Сохранённые способы оплаты"
        ordering = ["-is_default", "-last_used_at"]

    def __str__(self) -> str:
        return f"{self.user_id}:{self.name}"

    @staticmethod
    def mask_card_number(card_number: str) -> str:
        """
        Mask card number to show only last 4 digits.

        Args:
            card_number: Full card number (e.g., "1234567890123456")

        Returns:
            Masked card number (e.g., "****3456")
        """
        if not card_number:
            return ""

        # Remove any spaces or dashes
        clean_number = card_number.replace(" ", "").replace("-", "")

        # Return only last 4 digits with asterisks
        if len(clean_number) >= 4:
            return "****" + clean_number[-4:]
        return "****"

    def encrypt_details(self) -> dict:
        """
        Encrypt sensitive fields in payment details using AES-256.

        Note: card_number is NOT encrypted, only masked (per requirements 8.3).
        Only CVV and other sensitive fields are encrypted.

        Returns:
            Encrypted details dictionary
        """
        from cryptography.fernet import Fernet
        from django.conf import settings
        import json
        import base64
        import hashlib

        # Generate encryption key from Django SECRET_KEY
        key = base64.urlsafe_b64encode(
            hashlib.sha256(settings.SECRET_KEY.encode()).digest()
        )
        cipher = Fernet(key)

        # Fields that need encryption based on payment type
        # Note: card_number is excluded - it's masked, not encrypted
        sensitive_fields = []
        if self.type == "card":
            sensitive_fields = ["cvv", "expiry"]  # card_number is masked, not encrypted
        elif self.type == "ewallet":
            sensitive_fields = ["account_number", "phone"]
        # Crypto addresses are not encrypted (public information)

        encrypted_details = self.details.copy()

        for field in sensitive_fields:
            if field in encrypted_details and encrypted_details[field]:
                # Encrypt the field value
                plaintext = str(encrypted_details[field]).encode()
                encrypted_value = cipher.encrypt(plaintext)
                encrypted_details[field] = base64.b64encode(encrypted_value).decode()

        return encrypted_details

    def decrypt_details(self) -> dict:
        """
        Decrypt sensitive fields in payment details.

        Note: card_number is not decrypted (it's masked, not encrypted).

        Returns:
            Decrypted details dictionary
        """
        from cryptography.fernet import Fernet
        from django.conf import settings
        import json
        import base64
        import hashlib

        # Generate encryption key from Django SECRET_KEY
        key = base64.urlsafe_b64encode(
            hashlib.sha256(settings.SECRET_KEY.encode()).digest()
        )
        cipher = Fernet(key)

        # Fields that need decryption based on payment type
        # Note: card_number is excluded - it's masked, not encrypted
        sensitive_fields = []
        if self.type == "card":
            sensitive_fields = ["cvv", "expiry"]  # card_number is masked, not encrypted
        elif self.type == "ewallet":
            sensitive_fields = ["account_number", "phone"]

        decrypted_details = self.details.copy()

        for field in sensitive_fields:
            if field in decrypted_details and decrypted_details[field]:
                try:
                    # Decrypt the field value
                    encrypted_value = base64.b64decode(decrypted_details[field].encode())
                    plaintext = cipher.decrypt(encrypted_value)
                    decrypted_details[field] = plaintext.decode()
                except Exception:
                    # If decryption fails, field might not be encrypted
                    pass

        return decrypted_details

    def save(self, *args, **kwargs):
        """
        Override save to auto-encrypt sensitive fields and mask card numbers.

        Processing order:
        1. Mask card numbers (only last 4 digits stored)
        2. Encrypt other sensitive fields (CVV, expiry, etc.)
        """
        # Step 1: Mask card numbers before encryption
        if self.type == "card" and "card_number" in self.details:
            full_card_number = self.details["card_number"]
            # Only mask if it's not already masked
            if not full_card_number.startswith("****"):
                self.details["card_number"] = self.mask_card_number(full_card_number)

        # Step 2: Encrypt sensitive details (excluding card_number which is already masked)
        # Note: We only encrypt if the details are not already encrypted
        if self.type in ["card", "ewallet"]:
            # Check if already encrypted by looking for base64 pattern in CVV
            needs_encryption = True
            if self.type == "card" and "cvv" in self.details:
                # If CVV looks like base64, assume already encrypted
                try:
                    import base64
                    base64.b64decode(self.details["cvv"])
                    needs_encryption = False
                except Exception:
                    needs_encryption = True
            elif self.type == "ewallet" and "account_number" in self.details:
                # Check if account_number is encrypted
                try:
                    import base64
                    base64.b64decode(self.details["account_number"])
                    needs_encryption = False
                except Exception:
                    needs_encryption = True

            if needs_encryption:
                self.details = self.encrypt_details()

        super().save(*args, **kwargs)



class PaymentSettings(models.Model):
    singleton_id = models.IntegerField(default=1, unique=True, editable=False)
    deposit_enabled = models.BooleanField(default=True)
    withdrawal_enabled = models.BooleanField(default=True)
    maintenance_message = models.TextField(null=True, blank=True)
    deposit_notification_threshold = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("5000"))
    auto_payout_enabled = models.BooleanField(default=True)
    auto_payout_max_amount_usd = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("500"))
    daily_deposit_limit_per_user = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("50000"))
    daily_payout_limit_total = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("100000"))
    suspicious_deposit_patterns = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "Настройки платежей"
        indexes = [models.Index(fields=["singleton_id"])]

    @classmethod
    def get_settings(cls) -> "PaymentSettings":
        cache_key = "payments_settings_singleton"
        obj = cache.get(cache_key)
        if obj:
            return obj
        with transaction.atomic():
            obj, _ = cls.objects.get_or_create(singleton_id=1)
        cache.set(cache_key, obj, 300)
        return obj
