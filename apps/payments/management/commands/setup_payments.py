"""
Management command to seed PaymentProvider + PaymentMethod records
for NOWPayments crypto integration.

Usage:
    python manage.py setup_payments
"""
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.payments.models import PaymentProvider, PaymentMethod


class Command(BaseCommand):
    help = "Create/update PaymentProvider and PaymentMethod records for NOWPayments"

    def handle(self, *args, **options):
        api_key = getattr(settings, "NOWPAYMENTS_API_KEY", "")
        ipn_secret = getattr(settings, "NOWPAYMENTS_IPN_SECRET", "")
        api_url = getattr(settings, "NOWPAYMENTS_API_URL", "https://api.nowpayments.io")

        if not api_key:
            self.stderr.write(self.style.ERROR(
                "NOWPAYMENTS_API_KEY is not set in settings/.env. Aborting."
            ))
            return

        # --- PaymentProvider: nowpayments ---
        provider, created = PaymentProvider.objects.update_or_create(
            code="nowpayments",
            defaults={
                "name": "NOWPayments",
                "type": "crypto",
                "description": "Криптовалютные платежи через NOWPayments. BTC, ETH, USDT, TON и 200+ монет.",
                "icon": "🪙",
                "api_base_url": api_url,
                "api_key": api_key,
                "api_secret": "",
                "webhook_secret": ipn_secret,
                "is_active": True,
                "is_deposit_enabled": True,
                "is_withdrawal_enabled": True,
                "min_deposit": Decimal("1"),
                "max_deposit": Decimal("100000"),
                "deposit_fee_percent": Decimal("0"),
                "deposit_fee_fixed": Decimal("0"),
                "processing_time": "10-30 мин",
                "sort_order": 1,
                "extra_settings": {},
            },
        )
        action = "Создан" if created else "Обновлён"
        self.stdout.write(self.style.SUCCESS(f"{action} провайдер: nowpayments"))

        # Ensure wallet currencies exist (needed as FK)
        from apps.wallet.models import Currency

        # Define crypto currencies with their codes and supported methods
        crypto_methods = [
            {
                "code": "btc",
                "name": "Bitcoin (BTC)",
                "icon": "₿",
                "currency_code": "BTC",
                "min": Decimal("0.0001"),
                "max": Decimal("10"),
                "processing_time": "10-60 мин",
            },
            {
                "code": "eth",
                "name": "Ethereum (ETH)",
                "icon": "Ξ",
                "currency_code": "ETH",
                "min": Decimal("0.001"),
                "max": Decimal("100"),
                "processing_time": "5-15 мин",
            },
            {
                "code": "usdttrc20",
                "name": "Tether USDT (TRC20)",
                "icon": "₮",
                "currency_code": "USDT",
                "min": Decimal("1"),
                "max": Decimal("100000"),
                "processing_time": "5-10 мин",
            },
            {
                "code": "usdterc20",
                "name": "Tether USDT (ERC20)",
                "icon": "₮",
                "currency_code": "USDT",
                "min": Decimal("10"),
                "max": Decimal("100000"),
                "processing_time": "5-15 мин",
            },
            {
                "code": "ton",
                "name": "Toncoin (TON)",
                "icon": "◎",
                "currency_code": "TON",
                "min": Decimal("1"),
                "max": Decimal("50000"),
                "processing_time": "1-5 мин",
            },
            {
                "code": "trx",
                "name": "TRON (TRX)",
                "icon": "🔷",
                "currency_code": "TRX",
                "min": Decimal("10"),
                "max": Decimal("500000"),
                "processing_time": "1-5 мин",
            },
            {
                "code": "ltc",
                "name": "Litecoin (LTC)",
                "icon": "Ł",
                "currency_code": "LTC",
                "min": Decimal("0.01"),
                "max": Decimal("1000"),
                "processing_time": "10-30 мин",
            },
            {
                "code": "bnbbsc",
                "name": "BNB (BSC)",
                "icon": "🔶",
                "currency_code": "BNB",
                "min": Decimal("0.01"),
                "max": Decimal("1000"),
                "processing_time": "3-5 мин",
            },
        ]

        # Also add fiat-to-crypto methods (pay in USD/EUR/RUB via NOWPayments invoice)
        fiat_via_crypto = [
            {
                "code": "nowpay_usd",
                "name": "Крипта (оплата в USD)",
                "icon": "🪙",
                "currency_code": "USD",
                "min": Decimal("5"),
                "max": Decimal("50000"),
                "processing_time": "10-30 мин",
            },
            {
                "code": "nowpay_eur",
                "name": "Крипта (оплата в EUR)",
                "icon": "🪙",
                "currency_code": "EUR",
                "min": Decimal("5"),
                "max": Decimal("50000"),
                "processing_time": "10-30 мин",
            },
            {
                "code": "nowpay_rub",
                "name": "Крипта (оплата в RUB)",
                "icon": "🪙",
                "currency_code": "RUB",
                "min": Decimal("500"),
                "max": Decimal("5000000"),
                "processing_time": "10-30 мин",
            },
        ]

        all_methods = crypto_methods + fiat_via_crypto
        stats = {"created": 0, "updated": 0}

        for m in all_methods:
            # Ensure currency exists
            currency, _ = Currency.objects.get_or_create(
                code=m["currency_code"],
                defaults={
                    "name": m["currency_code"],
                    "symbol": m["icon"],
                    "type": "crypto" if m["currency_code"] in ("BTC", "ETH", "USDT", "TON", "TRX", "LTC", "BNB") else "fiat",
                    "is_active": True,
                    "is_deposit_enabled": True,
                    "is_withdrawal_enabled": True,
                    "decimal_places": 8 if m["currency_code"] in ("BTC", "ETH", "USDT", "TON", "TRX", "LTC", "BNB") else 2,
                    "rate_to_usd": Decimal("1") if m["currency_code"] == "USD" else Decimal("0"),
                    "min_deposit": m["min"],
                    "sort_order": 0,
                },
            )

            method, was_created = PaymentMethod.objects.update_or_create(
                provider=provider,
                code=m["code"],
                defaults={
                    "name": m["name"],
                    "description": f"Оплата через NOWPayments — {m['name']}",
                    "icon": m["icon"],
                    "currency": currency,
                    "type": "deposit",
                    "min_amount": m["min"],
                    "max_amount": m["max"],
                    "fee_percent": Decimal("0"),
                    "fee_fixed": Decimal("0"),
                    "processing_time": m["processing_time"],
                    "is_active": True,
                    "requires_kyc": False,
                    "sort_order": 0,
                },
            )
            if was_created:
                stats["created"] += 1
            else:
                stats["updated"] += 1

        self.stdout.write(self.style.SUCCESS(
            f"PaymentMethod: {stats['created']} создано, {stats['updated']} обновлено"
        ))
        self.stdout.write(self.style.SUCCESS(
            "\nNOWPayments configured! Now you can see real payment methods "
            "on the /wallet/deposit/ page."
        ))
