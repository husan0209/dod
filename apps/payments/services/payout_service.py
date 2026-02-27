from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.payments.models import PayoutOrder, PaymentMethod, PaymentProvider, PaymentSettings
from apps.payments.providers import get_provider_instance
from apps.wallet.models import WithdrawalRequest, Currency
from apps.wallet.services.transaction_service import TransactionService


class PayoutService:
    @staticmethod
    def create_payout(withdrawal_request: WithdrawalRequest, provider_code: str, method_code: str) -> PayoutOrder:
        settings_obj = PaymentSettings.get_settings()
        if not settings_obj.withdrawal_enabled:
            raise ValueError("Выплаты отключены")

        provider = PaymentProvider.objects.get(code=provider_code, is_active=True, is_withdrawal_enabled=True)
        payment_method = PaymentMethod.objects.get(provider=provider, code=method_code, is_active=True)
        currency: Currency = withdrawal_request.currency

        with transaction.atomic():
            payout = PayoutOrder.objects.create(
                withdrawal_request=withdrawal_request,
                user=withdrawal_request.user,
                provider=provider,
                payment_method=payment_method,
                currency=currency,
                amount=withdrawal_request.amount,
                fee_amount=withdrawal_request.fee_amount,
                net_amount=withdrawal_request.net_amount,
                status="created",
                payment_details=withdrawal_request.payment_details,
            )

            provider_client = get_provider_instance(provider)
            result = provider_client.create_payout(
                payout_id=payout.payout_id,
                amount=payout.net_amount,
                currency=currency.code,
                payment_details=payout.payment_details,
            )

            payout.provider_payout_id = result.get("provider_payout_id")
            payout.provider_response = result.get("raw_response", {})
            payout.provider_status = result.get("status")
            payout.status = "processing"
            payout.save(update_fields=["provider_payout_id", "provider_response", "provider_status", "status", "updated_at"])

        return payout

    @staticmethod
    def complete_payout(payout_id: str) -> str:
        with transaction.atomic():
            payout = PayoutOrder.objects.select_for_update().get(payout_id=payout_id)
            if payout.status == "completed":
                return "duplicate"
            if payout.status in {"failed", "cancelled"}:
                return "invalid_state"

            txn = TransactionService.complete_withdrawal(
                payout.withdrawal_request.wallet,
                currency_code=payout.currency.code,
                amount=payout.amount,
                reference_id=payout.payout_id,
                ip_address=payout.withdrawal_request.ip_address,
            )
            payout.status = "completed"
            payout.completed_at = timezone.now()
            payout.provider_status = "completed"
            payout.withdrawal_request.status = "completed"
            payout.withdrawal_request.transaction = txn
            payout.withdrawal_request.completed_at = payout.completed_at
            payout.withdrawal_request.save(update_fields=["status", "transaction", "completed_at", "updated_at"])
            payout.save(update_fields=["status", "provider_status", "completed_at", "updated_at"])
        return "completed"
