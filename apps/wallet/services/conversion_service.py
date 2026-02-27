from decimal import Decimal
from typing import Dict

from django.db import transaction

from apps.wallet.models import ConversionOrder, Currency, Wallet, WalletSettings
from apps.wallet.services.transaction_service import InsufficientFundsError, TransactionService


class ConversionService:
    @staticmethod
    def get_conversion_rate(from_currency: Currency, to_currency: Currency) -> Decimal:
        from_rate = from_currency.rate_to_usd
        to_rate = to_currency.rate_to_usd
        if to_rate == 0:
            raise ZeroDivisionError("Target currency rate_to_usd is zero")
        return from_rate / to_rate

    @staticmethod
    def preview_conversion(wallet: Wallet, from_code: str, to_code: str, amount: Decimal) -> Dict:
        if amount <= 0:
            raise ValueError("Amount must be positive")
        from_currency = Currency.objects.get(code=from_code)
        to_currency = Currency.objects.get(code=to_code)
        settings_obj = WalletSettings.get_settings()
        if not settings_obj.conversion_enabled:
            raise ValueError("Conversion disabled")
        if not (from_currency.is_active and to_currency.is_active):
            raise ValueError("Currency inactive")
        rate = ConversionService.get_conversion_rate(from_currency, to_currency)
        fee_percent = from_currency.conversion_fee_percent if from_currency.conversion_fee_percent is not None else Decimal("1.0")
        fee_amount = amount * fee_percent / Decimal("100")
        net_from_amount = amount - fee_amount
        to_amount = net_from_amount * rate
        return {
            "from_currency": from_code,
            "to_currency": to_code,
            "from_amount": amount,
            "exchange_rate": rate,
            "fee_percent": fee_percent,
            "fee_amount": fee_amount,
            "net_from_amount": net_from_amount,
            "to_amount": to_amount,
            "rate_expires_in": 30,
        }

    @staticmethod
    def execute_conversion(wallet: Wallet, from_code: str, to_code: str, amount: Decimal) -> ConversionOrder:
        if amount <= 0:
            raise ValueError("Amount must be positive")
        if from_code == to_code:
            raise ValueError("Cannot convert the same currency")
        from_currency = Currency.objects.get(code=from_code)
        to_currency = Currency.objects.get(code=to_code)
        settings_obj = WalletSettings.get_settings()
        if not settings_obj.conversion_enabled:
            raise ValueError("Conversion disabled")
        if not (from_currency.is_active and to_currency.is_active):
            raise ValueError("Currency inactive")
        rate = ConversionService.get_conversion_rate(from_currency, to_currency)
        fee_percent = from_currency.conversion_fee_percent if from_currency.conversion_fee_percent is not None else Decimal("1.0")
        fee_amount = amount * fee_percent / Decimal("100")
        net_from_amount = amount - fee_amount
        to_amount = net_from_amount * rate
        with transaction.atomic():
            debit_txn = TransactionService.withdraw(
                wallet,
                currency_code=from_code,
                amount=amount,
                txn_type="conversion_debit",
                reference_type="conversion",
                reference_id=f"{from_code}->{to_code}",
            )
            credit_txn = TransactionService.deposit(
                wallet,
                currency_code=to_code,
                amount=to_amount,
                txn_type="conversion_credit",
                reference_type="conversion",
                reference_id=str(debit_txn.id),
            )
            order = ConversionOrder.objects.create(
                wallet=wallet,
                user=wallet.user,
                from_currency=from_currency,
                to_currency=to_currency,
                from_amount=amount,
                to_amount=to_amount,
                exchange_rate=rate,
                fee_percent=fee_percent,
                fee_amount=fee_amount,
                status="completed",
                debit_transaction=debit_txn,
                credit_transaction=credit_txn,
            )
        return order
