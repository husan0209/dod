from __future__ import annotations

import logging
from datetime import timedelta
from decimal import Decimal
from typing import Dict, Any

from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.payments.models import PayoutOrder, PaymentMethod, PaymentProvider, PaymentSettings
from apps.payments.providers import get_provider_instance
from apps.wallet.models import WithdrawalRequest, Currency
from apps.wallet.services.transaction_service import TransactionService

logger = logging.getLogger(__name__)


class PayoutService:
    """
    Core service for managing withdrawal/payout lifecycle.
    
    Responsibilities:
    - Create payout orders from approved withdrawals
    - Interact with provider SDK
    - Process webhook confirmations
    - Handle retry logic
    """
    
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

    @staticmethod
    def _initiate_payout(payout: PayoutOrder) -> bool:
        """
        Call provider SDK to initiate payout.
        
        Returns True if successful, False otherwise.
        """
        try:
            provider_instance = get_provider_instance(payout.provider)
            response = provider_instance.create_payout(
                payout_id=payout.payout_id,
                amount=payout.net_amount,
                currency=payout.currency.code,
                payment_details=payout.payment_details,
                webhook_url=PayoutService._build_webhook_url(payout.provider.code)
            )
            
            payout.provider_payout_id = response.provider_payout_id
            payout.provider_response = response.raw_response
            payout.provider_status = response.status
            
            if response.success:
                payout.status = "processing"
            else:
                payout.status = "failed"
                payout.error_message = response.error_message
            
            payout.save()
            return response.success
            
        except Exception as e:
            logger.error(f"Error initiating payout {payout.payout_id}: {e}", exc_info=True)
            payout.status = "failed"
            payout.error_message = str(e)
            payout.save()
            return False

    @staticmethod
    def process_webhook_confirmation(provider_code: str, webhook_data: Dict[str, Any]) -> bool:
        """
        Process payout webhook confirmation.
        
        Steps:
        1. Find the PayoutOrder by payout_id
        2. Update status based on webhook data
        3. Update associated WithdrawalRequest
        
        Returns True if processed, False if duplicate/invalid
        """
        payout_id = webhook_data.get("payout_id") or webhook_data.get("extra_id")
        
        if not payout_id:
            logger.error(f"No payout_id found in webhook data: {webhook_data}")
            return False
        
        try:
            with transaction.atomic():
                payout = PayoutOrder.objects.select_for_update().get(payout_id=payout_id)
                
                # Update provider status
                payout.provider_status = webhook_data.get("provider_status", "")
                
                if webhook_data["status"] == "completed":
                    payout.status = "completed"
                    payout.completed_at = timezone.now()
                    
                    # Update withdrawal request
                    payout.withdrawal_request.status = "completed"
                    payout.withdrawal_request.completed_at = timezone.now()
                    payout.withdrawal_request.save(
                        update_fields=["status", "completed_at", "updated_at"]
                    )
                    
                elif webhook_data["status"] == "failed":
                    payout.status = "failed"
                    payout.error_message = webhook_data.get("error_message", "")
                
                payout.save()
                return True
                
        except PayoutOrder.DoesNotExist:
            logger.error(f"PayoutOrder not found for payout_id: {payout_id}")
            return False
        except Exception as e:
            logger.error(f"Error processing payout webhook: {e}", exc_info=True)
            return False

    @staticmethod
    def retry_failed_payouts():
        """
        Background task: Retry failed payouts with exponential backoff.
        
        Retry delays:
        - Retry 0: 1 minute
        - Retry 1: 5 minutes
        - Retry 2: 15 minutes
        """
        failed_payouts = PayoutOrder.objects.filter(
            status="failed",
            retry_count__lt=F('max_retries')
        ).select_related('provider', 'currency', 'withdrawal_request')
        
        for payout in failed_payouts:
            # Exponential backoff: 1 min, 5 min, 15 min
            delay_minutes = [1, 5, 15][min(payout.retry_count, 2)]
            
            if timezone.now() >= payout.updated_at + timedelta(minutes=delay_minutes):
                logger.info(f"Retrying payout {payout.payout_id}, attempt {payout.retry_count + 1}")
                payout.retry_count += 1
                payout.save(update_fields=["retry_count", "updated_at"])
                
                # Attempt to initiate payout again
                success = PayoutService._initiate_payout(payout)
                
                if not success and payout.retry_count >= payout.max_retries:
                    # Mark as permanently failed
                    logger.error(
                        f"Payout {payout.payout_id} permanently failed after {payout.max_retries} retries"
                    )
                    payout.status = "failed"
                    payout.error_message = (
                        f"Failed after {payout.max_retries} retry attempts. "
                        f"Last error: {payout.error_message}"
                    )
                    payout.save(update_fields=["status", "error_message", "updated_at"])
                    
                    # TODO: Notify administrators
                    PayoutService._notify_admins_failed_payout(payout)

    @staticmethod
    def _select_provider(payment_method: str, currency: Currency) -> PaymentProvider:
        """
        Select appropriate provider based on payment method and currency.
        
        Args:
            payment_method: Type of payment method (crypto, card, ewallet)
            currency: Currency object
            
        Returns:
            PaymentProvider instance
        """
        if payment_method == "crypto":
            return PaymentProvider.objects.get(
                code="nowpayments",
                is_active=True,
                is_withdrawal_enabled=True
            )
        else:
            # For fiat payments (card, ewallet), use RUkassa
            return PaymentProvider.objects.get(
                code="rukassa",
                is_active=True,
                is_withdrawal_enabled=True
            )

    @staticmethod
    def _get_payment_method(provider: PaymentProvider, withdrawal: WithdrawalRequest) -> PaymentMethod:
        """
        Get the appropriate PaymentMethod for the payout.
        
        Args:
            provider: PaymentProvider instance
            withdrawal: WithdrawalRequest instance
            
        Returns:
            PaymentMethod instance or None if not found
        """
        return provider.methods.filter(
            currency=withdrawal.currency,
            type__in=["withdrawal", "both"],
            is_active=True
        ).first()

    @staticmethod
    def _build_webhook_url(provider_code: str) -> str:
        """Build webhook URL for payout confirmations."""
        site_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')
        return f"{site_url}/webhooks/payouts/{provider_code}/"

    @staticmethod
    def _notify_admins_failed_payout(payout: PayoutOrder):
        """
        Send notification to administrators about permanently failed payout.
        
        This should be implemented to send email/telegram notifications.
        """
        # TODO: Implement notification logic
        logger.critical(
            f"ADMIN ALERT: Payout {payout.payout_id} permanently failed. "
            f"User: {payout.user.email}, Amount: {payout.amount} {payout.currency.code}"
        )
