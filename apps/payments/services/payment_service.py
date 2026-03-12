from __future__ import annotations

import logging
from decimal import Decimal
from typing import Dict, List, Any, Optional
from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from django.conf import settings

from apps.payments.models import DepositOrder, PaymentMethod, PaymentProvider, PaymentSettings
from apps.payments.services.antifraud_service import AntiFraudService
from apps.payments.providers import get_provider_instance
from apps.wallet.models import Currency, Wallet
from apps.wallet.services.transaction_service import TransactionService

logger = logging.getLogger(__name__)


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

        # Validate amount against limits
        if amount < payment_method.min_amount:
            raise ValueError(f"Amount below minimum: {payment_method.min_amount}")
        if amount > payment_method.max_amount:
            raise ValueError(f"Amount exceeds maximum: {payment_method.max_amount}")

        # Anti-fraud checks
        if AntiFraudService.is_deposit_blocked(user=user, amount=amount, currency=currency):
            raise ValueError("Платёж отклонён антифродом")

        amount_usd = currency.convert_to_usd(amount)
        expires_minutes = 60 if currency.type == "crypto" else 30
        expires_at = timezone.now() + timedelta(minutes=expires_minutes)

        with transaction.atomic():
            deposit = DepositOrder.objects.create(
                user=user,
                wallet=wallet,
                provider=provider,
                payment_method=payment_method,
                currency=currency,
                amount=amount,
                amount_usd=amount_usd,
                fee_amount=PaymentService._calculate_fee(amount, payment_method),
                status="created",
                expires_at=expires_at,
                ip_address=ip_address,
                user_agent=user_agent,
                success_url=PaymentService._build_success_url(""),  # Will be updated with actual order_id
                fail_url=PaymentService._build_fail_url(""),
            )
            
            # Update URLs with actual order_id
            deposit.success_url = PaymentService._build_success_url(deposit.order_id)
            deposit.fail_url = PaymentService._build_fail_url(deposit.order_id)
            deposit.save(update_fields=["success_url", "fail_url"])

            # Call provider SDK
            provider_client = get_provider_instance(provider)
            result = provider_client.create_deposit(
                order_id=deposit.order_id,
                amount=amount,
                currency=currency.code,
                payment_method_code=method_code,
                user_email=user.email,
                success_url=deposit.success_url,
                fail_url=deposit.fail_url,
                webhook_url=PaymentService._build_webhook_url(provider_code),
            )

            # Update deposit with provider response
            if result.success:
                deposit.provider_order_id = result.provider_order_id
                deposit.provider_payment_url = result.payment_url
                deposit.crypto_address = result.crypto_address
                deposit.crypto_network = result.crypto_network
                deposit.provider_response = result.raw_response
                deposit.status = "pending"
            else:
                deposit.status = "failed"
                deposit.provider_response = {"error": result.error_message}
            
            deposit.save()

        return {
            "deposit_id": deposit.order_id,
            "payment_url": deposit.provider_payment_url,
            "crypto_address": deposit.crypto_address,
            "crypto_network": deposit.crypto_network,
            "expires_at": deposit.expires_at,
            "status": deposit.status,
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

    @staticmethod
    def process_webhook_confirmation(
        provider_code: str,
        webhook_data: Dict[str, Any]
    ) -> bool:
        """
        Process webhook confirmation from provider.
        
        Steps:
        1. Find the DepositOrder by order_id
        2. Check idempotency (already completed?)
        3. Validate status transition
        4. Credit wallet atomically
        5. Update order status
        
        Returns True if processed, False if duplicate/invalid
        """
        order_id = webhook_data.get("order_id")
        if not order_id:
            logger.error(f"Webhook missing order_id: {webhook_data}")
            return False
        
        try:
            with transaction.atomic():
                # Lock the order row for idempotency
                deposit = DepositOrder.objects.select_for_update().get(order_id=order_id)
                
                # Idempotency check
                if deposit.status == "completed":
                    logger.info(f"Deposit {order_id} already completed, skipping webhook")
                    return False  # Already processed
                
                # Validate status transition
                if not deposit.can_be_completed():
                    logger.warning(f"Deposit {order_id} cannot be completed from status {deposit.status}")
                    raise ValueError(f"Order {order_id} cannot be completed from status {deposit.status}")
                
                # Update order with webhook data
                new_status = webhook_data.get("status", "completed")
                deposit.provider_status = webhook_data.get("provider_status", "")
                amount_received = webhook_data.get("amount", deposit.amount)
                
                if new_status == "completed":
                    # Credit wallet
                    txn = TransactionService.deposit(
                        deposit.wallet,
                        currency_code=deposit.currency.code,
                        amount=amount_received,
                        description=f"Deposit via {deposit.provider.name}",
                        metadata={
                            "provider": deposit.provider.code,
                            "method": deposit.payment_method.code,
                            "deposit_order_id": deposit.order_id,
                            "provider_order_id": deposit.provider_order_id,
                        },
                        ip_address=deposit.ip_address,
                        reference_type="deposit_order",
                        reference_id=str(deposit.id),
                    )
                    
                    deposit.transaction = txn
                    deposit.amount_received = amount_received
                    deposit.completed_at = timezone.now()
                    deposit.status = "completed"
                    
                    logger.info(f"Deposit {order_id} completed successfully, amount: {amount_received}")
                elif new_status == "failed":
                    deposit.status = "failed"
                    logger.info(f"Deposit {order_id} marked as failed")
                else:
                    deposit.status = new_status
                    logger.info(f"Deposit {order_id} status updated to {new_status}")
                
                deposit.save()
                
            return True
            
        except DepositOrder.DoesNotExist:
            logger.error(f"Deposit order {order_id} not found for webhook")
            return False
        except Exception as e:
            logger.error(f"Error processing webhook for deposit {order_id}: {e}", exc_info=True)
            raise

    @staticmethod
    def check_pending_deposits():
        """
        Background task: Check status of pending deposits.
        Called every 5 minutes as backup if webhook fails.
        """
        pending_orders = DepositOrder.objects.filter(
            status__in=["pending", "processing"],
            expires_at__gt=timezone.now()
        ).select_related('provider', 'currency', 'wallet')
        
        logger.info(f"Checking {pending_orders.count()} pending deposits")
        
        for order in pending_orders:
            try:
                provider_instance = get_provider_instance(order.provider)
                status_response = provider_instance.check_deposit_status(order.provider_order_id)
                
                if status_response.status == "completed":
                    # Process as if webhook arrived
                    PaymentService.process_webhook_confirmation(
                        order.provider.code,
                        {
                            "order_id": order.order_id,
                            "status": "completed",
                            "provider_status": status_response.provider_status,
                            "amount": status_response.amount_received or order.amount
                        }
                    )
                    logger.info(f"Deposit {order.order_id} completed via status check")
                elif status_response.status in ["failed", "expired", "cancelled"]:
                    order.status = status_response.status
                    order.provider_status = status_response.provider_status
                    order.save(update_fields=["status", "provider_status", "updated_at"])
                    logger.info(f"Deposit {order.order_id} marked as {status_response.status}")
                    
            except Exception as e:
                logger.error(f"Error checking deposit {order.order_id}: {e}", exc_info=True)

    @staticmethod
    def expire_old_deposits():
        """
        Background task: Expire deposits that haven't been paid.
        """
        expired_orders = DepositOrder.objects.filter(
            status__in=["created", "pending"],
            expires_at__lte=timezone.now()
        )
        
        count = expired_orders.count()
        if count > 0:
            expired_orders.update(status="expired", updated_at=timezone.now())
            logger.info(f"Expired {count} old deposits")

    @staticmethod
    def _calculate_fee(amount: Decimal, payment_method: PaymentMethod) -> Decimal:
        """
        Calculate fee for a payment method.
        Fee calculation order: fee_fixed first, then fee_percent on the original amount.

        Formula: fee = fee_fixed + (amount * fee_percent / 100)

        Args:
            amount: The payment amount
            payment_method: The payment method with fee configuration

        Returns:
            Calculated fee with proper decimal precision
        """
        # Apply fee_fixed first, then fee_percent on the original amount
        fee = payment_method.fee_fixed + (amount * payment_method.fee_percent / Decimal("100"))
        return fee.quantize(Decimal("0.00000001"))

    @staticmethod
    def calculate_deposit_total(
        amount: Decimal,
        payment_method: PaymentMethod
    ) -> Dict[str, Decimal]:
        """
        Calculate total deposit amount including fees for UI display.

        This method is used to show users the total amount they will pay
        when making a deposit, including all fees.

        Args:
            amount: The base deposit amount
            payment_method: The payment method with fee configuration

        Returns:
            Dictionary with:
                - amount: Original amount
                - fee: Calculated fee
                - total: Total amount (amount + fee)
                - formatted_total: Total formatted with currency decimal places

        Example:
            >>> calculate_deposit_total(Decimal("100"), payment_method)
            {
                'amount': Decimal('100.00'),
                'fee': Decimal('3.50'),
                'total': Decimal('103.50'),
                'formatted_total': Decimal('103.50')
            }
        """
        fee = PaymentService._calculate_fee(amount, payment_method)
        total = amount + fee

        # Format total with currency's decimal places
        currency = payment_method.currency
        quantizer = Decimal(1) / (Decimal(10) ** currency.decimal_places)
        formatted_total = total.quantize(quantizer)

        return {
            "amount": amount,
            "fee": fee,
            "total": total,
            "formatted_total": formatted_total
        }

    @staticmethod
    def calculate_withdrawal_net(
        amount: Decimal,
        payment_method: PaymentMethod
    ) -> Dict[str, Decimal]:
        """
        Calculate net withdrawal amount after fees for UI display.

        This method is used to show users the actual amount they will receive
        when making a withdrawal, after deducting all fees.

        Args:
            amount: The requested withdrawal amount
            payment_method: The payment method with fee configuration

        Returns:
            Dictionary with:
                - amount: Original requested amount
                - fee: Calculated fee
                - net: Net amount user will receive (amount - fee)
                - formatted_net: Net formatted with currency decimal places

        Example:
            >>> calculate_withdrawal_net(Decimal("100"), payment_method)
            {
                'amount': Decimal('100.00'),
                'fee': Decimal('3.50'),
                'net': Decimal('96.50'),
                'formatted_net': Decimal('96.50')
            }
        """
        fee = PaymentService._calculate_fee(amount, payment_method)
        net = amount - fee

        # Ensure net amount is not negative
        if net < Decimal("0"):
            net = Decimal("0")

        # Format net with currency's decimal places
        currency = payment_method.currency
        quantizer = Decimal(1) / (Decimal(10) ** currency.decimal_places)
        formatted_net = net.quantize(quantizer)

        return {
            "amount": amount,
            "fee": fee,
            "net": net,
            "formatted_net": formatted_net
        }


    @staticmethod
    def _build_success_url(order_id: str) -> str:
        """Build success redirect URL."""
        site_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')
        return f"{site_url}/wallet/?deposit=success&order={order_id}"

    @staticmethod
    def _build_fail_url(order_id: str) -> str:
        """Build failure redirect URL."""
        site_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')
        return f"{site_url}/wallet/?deposit=fail&order={order_id}"

    @staticmethod
    def _build_webhook_url(provider_code: str) -> str:
        """Build webhook callback URL."""
        site_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')
        return f"{site_url}/webhooks/payments/{provider_code}/"
