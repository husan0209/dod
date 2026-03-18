from decimal import Decimal
from typing import Dict, List

from django.db import transaction
from django.utils import timezone

from apps.wallet.models import Currency, Wallet, WalletBalance, WalletSettings
from apps.wallet.services.transaction_service import TransactionService


class WalletService:
    @staticmethod
    def create_wallet(user) -> Wallet:
        try:
            usd_currency, _ = Currency.objects.get_or_create(
                code="USD",
                defaults={
                    "name": "US Dollar",
                    "symbol": "$",
                    "type": "fiat",
                    "decimal_places": 2,
                    "rate_to_usd": Decimal("1.0"),
                },
            )
        except Exception:
            usd_currency = None
        
        wallet, created = Wallet.objects.get_or_create(
            user=user,
            defaults={
                "primary_currency": usd_currency,
            },
        )
        if created and usd_currency:
            WalletService.get_or_create_balance(wallet, "USD")
            try:
                settings_obj = WalletSettings.get_settings()
                if settings_obj.registration_bonus_amount > 0:
                    TransactionService.deposit(
                        wallet,
                        currency_code=settings_obj.registration_bonus_currency,
                        amount=settings_obj.registration_bonus_amount,
                        description="Registration bonus",
                        txn_type="bonus",
                        created_by=user,
                    )
            except Exception:
                pass
        return wallet

    @staticmethod
    def get_or_create_balance(wallet: Wallet, currency_code: str) -> WalletBalance:
        currency = Currency.objects.get(code=currency_code)
        balance, _ = WalletBalance.objects.get_or_create(wallet=wallet, currency=currency)
        return balance

    @staticmethod
    def get_all_balances(wallet: Wallet) -> List[Dict]:
        balances = []
        for balance in wallet.balances.select_related("currency"):
            if balance.total <= 0:
                continue
            usd_eq = balance.total * balance.currency.rate_to_usd
            balances.append(
                {
                    "currency": balance.currency.code,
                    "symbol": balance.currency.symbol,
                    "available": balance.available,
                    "frozen": balance.frozen,
                    "total": balance.total,
                    "usd_equivalent": usd_eq,
                }
            )
        return balances

    @staticmethod
    def get_total_balance_usd(wallet: Wallet) -> Decimal:
        return wallet.get_total_balance_usd()

    @staticmethod
    def change_primary_currency(wallet: Wallet, currency_code: str) -> Wallet:
        currency = Currency.objects.get(code=currency_code)
        wallet.primary_currency = currency
        wallet.updated_at = timezone.now()
        wallet.save(update_fields=["primary_currency", "updated_at"])
        return wallet
