from __future__ import annotations

from decimal import Decimal
from typing import Dict, List

from django.db import transaction
from django.utils import timezone

from apps.payments.models import DepositOrder, PaymentMethod, PaymentProvider, PaymentSettings
from apps.payments.services.antifraud_service import AntiFraudService
from apps.payments.providers import get_provider_instance
from apps.wallet.models import Currency, Wallet
from apps.wallet.services.transaction_service import TransactionService


class PaymentService:
    @staticmethod
    def get_available_deposit_methods(user, currency_code: str | None = None) -> List[Dict]:
        methods = PaymentMethod.objects.select_related("provider", "currency").filter(
            is_active=True, type__in=["deposit", "both"], provider__is_active=True, provider__is_deposit_enabled=True
        )
        if currency_code:
            methods = methods.filter(currency__code=currency_code)

        grouped: Dict[str, Dict] = {}
        for m in methods.order_by("provider__sort_order", "sort_order"):
            provider_code = m.provider.code
            grouped.setdefault(
                provider_code,
                {
                    "provider": provider_code,
                    "provider_name": m.provider.name,
                    "methods": [],
                },
            )
            grouped[provider_code]["methods"].append(
                {
                    "code": m.code,
                    "name": m.name,
                    "icon": m.icon,
                    "currency": m.currency.code,
                    "min": m.min_amount,
                    "max": m.max_amount,
                    "fee": f"{m.fee_percent}%",
                    "processing_time": m.processing_time,
                }
            )
        return list(grouped.values())

    @staticmethod
    def create_deposit(
        user,
        currency_code: str,
        amount: Decimal,
        provider_code: str,
        method_code: str,
        ip_address: str,
        user_agent: str | None = None,
    ) -> Dict:
        settings_obj = PaymentSettings.get_settings()
        if not settings_obj.deposit_enabled:
            raise ValueError("Платежи временно недоступны")

        provider = PaymentProvider.objects.get(code=provider_code, is_active=True, is_deposit_enabled=True)
        payment_method = PaymentMethod.objects.get(provider=provider, code=method_code, is_active=True)
        currency = Currency.objects.get(code=currency_code)
        wallet = Wallet.objects.get(user=user)

        if amount < payment_method.min_amount or amount > payment_method.max_amount:
            raise ValueError("Сумма вне допустимого диапазона")

        if AntiFraudService.is_deposit_blocked(user=user, amount=amount, currency=currency):
            raise ValueError("Платёж отклонён антифродом")

        amount_usd = currency.convert_to_usd(amount)
        expires_minutes = 60 if currency.type == "crypto" else 30
        expires_at = timezone.now() + timezone.timedelta(minutes=expires_minutes)

        with transaction.atomic():
            deposit = DepositOrder.objects.create(
                user=user,
                wallet=wallet,
                provider=provider,
                payment_method=payment_method,
                currency=currency,
                amount=amount,
                amount_usd=amount_usd,
                fee_amount=payment_method.fee_fixed + (amount * payment_method.fee_percent / Decimal("100")),
                status="created",
                expires_at=expires_at,
                ip_address=ip_address,
                user_agent=user_agent,
            )

            provider_client = get_provider_instance(provider)
            result = provider_client.create_deposit(
                order_id=deposit.order_id,
                amount=amount,
                currency=currency.code,
                description=f"DOD пополнение {deposit.order_id}",
                success_url=deposit.success_url,
                fail_url=deposit.fail_url,
                customer_email=user.email,
            )

            deposit.provider_order_id = result.get("provider_order_id")
            deposit.provider_payment_url = result.get("payment_url")
            deposit.provider_response = result.get("raw_response", {})
            deposit.provider_status = result.get("status")
            deposit.status = "pending"
            deposit.save()

        return {
            "deposit_id": deposit.order_id,
            "payment_url": deposit.provider_payment_url,
            "expires_at": deposit.expires_at,
        }

    @staticmethod
    def complete_deposit(order_id: str, amount_received: Decimal | None = None) -> str:
        with transaction.atomic():
            deposit = DepositOrder.objects.select_for_update().get(order_id=order_id)
            if not deposit.can_be_completed():
                return "duplicate" if deposit.status == "completed" else "invalid_state"

            actual_amount = amount_received or deposit.amount
            txn = TransactionService.deposit(
                deposit.wallet,
                currency_code=deposit.currency.code,
                amount=actual_amount,
                description=f"Пополнение {deposit.payment_method.name}",
                metadata={
                    "provider": deposit.provider.code,
                    "method": deposit.payment_method.code,
                    "deposit_order_id": deposit.order_id,
                    "provider_order_id": deposit.provider_order_id,
                },
                ip_address=deposit.ip_address,
            )

            deposit.status = "completed"
            deposit.amount_received = actual_amount
            deposit.transaction = txn
            deposit.completed_at = timezone.now()
            deposit.save(update_fields=["status", "amount_received", "transaction", "completed_at", "updated_at"])
        return "completed"
