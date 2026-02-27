from decimal import Decimal
from typing import Optional

from django.db import models, transaction
from django.utils import timezone

from apps.wallet.models import Currency, Wallet, WalletSettings, WithdrawalRequest
from apps.wallet.services.transaction_service import InsufficientFundsError, TransactionService


class WithdrawalValidationError(Exception):
    pass


class WithdrawalService:
    @staticmethod
    def _validate_basic(wallet: Wallet, currency: Currency, amount: Decimal) -> None:
        if wallet.is_frozen:
            raise WithdrawalValidationError("Кошелёк заморожен")
        if amount <= 0:
            raise WithdrawalValidationError("Сумма должна быть положительной")
        if amount < currency.min_withdrawal:
            raise WithdrawalValidationError("Сумма меньше минимального вывода")
        if not currency.is_withdrawal_enabled:
            raise WithdrawalValidationError("Вывод по валюте отключен")

    @staticmethod
    def _check_daily_limit(wallet: Wallet, amount_usd: Decimal, settings_obj: WalletSettings) -> None:
        window_start = timezone.now() - timezone.timedelta(days=1)
        from apps.wallet.models import Transaction  # local import to avoid cycle

        daily_total = (
            Transaction.objects.filter(wallet=wallet, type="withdrawal", created_at__gte=window_start)
            .exclude(status__in=["failed", "cancelled", "rejected"])
            .aggregate(total=models.Sum("amount_usd"))
            .get("total")
            or Decimal("0")
        )
        if daily_total + amount_usd > settings_obj.max_daily_withdrawal_usd:
            raise WithdrawalValidationError("Превышен дневной лимит")

    @staticmethod
    def _has_pending_request(wallet: Wallet) -> bool:
        return WithdrawalRequest.objects.filter(
            wallet=wallet,
            status__in={"pending", "manual_review", "auto_approved", "approved", "processing"},
        ).exists()

    @staticmethod
    def create_withdrawal_request(
        wallet: Wallet,
        *,
        currency_code: str,
        amount: Decimal,
        payment_method: str,
        payment_details: dict,
        ip_address: str,
        user_agent: Optional[str] = None,
    ) -> WithdrawalRequest:
        currency = Currency.objects.get(code=currency_code)
        settings_obj = WalletSettings.get_settings()
        WithdrawalService._validate_basic(wallet, currency, amount)
        if WithdrawalService._has_pending_request(wallet):
            raise WithdrawalValidationError("У вас уже есть необработанная заявка")

        amount_usd = currency.convert_to_usd(amount)
        WithdrawalService._check_daily_limit(wallet, amount_usd, settings_obj)
        if payment_method not in dict(WithdrawalRequest.PAYMENT_METHOD_CHOICES):
            raise WithdrawalValidationError("Неверный метод выплаты")

        # new account delay
        account_age_hours = int((timezone.now() - wallet.user.created_at).total_seconds() // 3600) if wallet.user.created_at else None
        if account_age_hours is not None and account_age_hours < settings_obj.new_account_withdrawal_delay_hours:
            raise WithdrawalValidationError("Вывод доступен позже для новых аккаунтов")

        # KYC requirement
        if wallet.user.kyc_status != "approved" and amount_usd > settings_obj.kyc_required_amount:
            raise WithdrawalValidationError("Пройдите KYC для данной суммы")

        # min bets before withdrawal
        if settings_obj.min_bets_before_withdrawal > 0:
            from apps.wallet.models import Transaction

            last_deposit = (
                Transaction.objects.filter(user=wallet.user, type="deposit")
                .order_by("-created_at")
                .first()
            )
            if last_deposit:
                bets_count = Transaction.objects.filter(
                    user=wallet.user,
                    type="bet",
                    created_at__gte=last_deposit.created_at,
                ).count()
                if bets_count < settings_obj.min_bets_before_withdrawal:
                    raise WithdrawalValidationError("Недостаточно ставок перед выводом")

        # fee calculation
        fee_amount = (amount * currency.withdrawal_fee_percent / Decimal("100")) + currency.withdrawal_fee_fixed
        net_amount = amount - fee_amount
        if net_amount <= 0:
            raise WithdrawalValidationError("Комиссия превышает сумму вывода")

        with transaction.atomic():
            req = WithdrawalRequest.objects.create(
                wallet=wallet,
                user=wallet.user,
                currency=currency,
                amount=amount,
                fee_amount=fee_amount,
                net_amount=net_amount,
                payment_method=payment_method,
                payment_details=payment_details,
                ip_address=ip_address,
                user_agent=user_agent,
            )

            TransactionService.freeze_funds(
                wallet,
                currency_code=currency_code,
                amount=amount,
                reference_type="withdrawal_request",
                reference_id=str(req.id),
            )

            # risk factors: withdrawals last hour
            recent_withdrawals_count = WithdrawalRequest.objects.filter(
                user=wallet.user,
                created_at__gte=timezone.now() - timezone.timedelta(hours=1),
            ).count()
            # unknown device: mark true if no active session device_name matches
            unknown_device = False
            from apps.accounts.models import ActiveSession

            if user_agent:
                unknown_device = not ActiveSession.objects.filter(user=wallet.user, user_agent=user_agent).exists() if hasattr(ActiveSession, "user_agent") else False
            usual_country = getattr(wallet.user, "country", None) or None
            current_country = usual_country
            last_deposit_at = last_deposit.created_at if "last_deposit" in locals() and last_deposit else None

            req.calculate_risk_level(
                account_age_hours=account_age_hours,
                recent_withdrawals_count=recent_withdrawals_count,
                usual_country=str(usual_country) if usual_country else None,
                current_country=str(current_country) if current_country else None,
                unknown_device=unknown_device,
                last_deposit_at=last_deposit_at,
            )
            req.save(update_fields=["risk_level", "risk_factors"])

            if req.can_auto_approve():
                req.status = "auto_approved"
                req.save(update_fields=["status"])
                from apps.wallet.tasks import process_withdrawal_task

                process_withdrawal_task.delay(str(req.id))
            else:
                req.status = "manual_review"
                req.save(update_fields=["status"])
            return req

    @staticmethod
    def approve_withdrawal(request_id: str, admin_user, comment: str = "") -> WithdrawalRequest:
        with transaction.atomic():
            req = WithdrawalRequest.objects.select_for_update().get(id=request_id)
            if req.status != "manual_review":
                raise WithdrawalValidationError("Неверный статус для одобрения")
            req.status = "approved"
            req.reviewed_by = admin_user
            req.reviewed_at = timezone.now()
            req.review_comment = comment
            req.save(update_fields=["status", "reviewed_by", "reviewed_at", "review_comment"])
            from apps.wallet.tasks import process_withdrawal_task

            process_withdrawal_task.delay(str(req.id))
            return req

    @staticmethod
    def reject_withdrawal(request_id: str, admin_user, reason: str, comment: str = "") -> WithdrawalRequest:
        with transaction.atomic():
            req = WithdrawalRequest.objects.select_for_update().get(id=request_id)
            req.status = "rejected"
            req.rejection_reason = reason
            req.review_comment = comment
            req.reviewed_by = admin_user
            req.reviewed_at = timezone.now()
            req.save(update_fields=["status", "rejection_reason", "review_comment", "reviewed_by", "reviewed_at"])
            TransactionService.unfreeze_funds(
                req.wallet,
                currency_code=req.currency.code,
                amount=req.amount,
                reference_type="withdrawal_request",
                reference_id=str(req.id),
            )
            return req

    @staticmethod
    def cancel_withdrawal(request_id: str, user) -> WithdrawalRequest:
        with transaction.atomic():
            req = WithdrawalRequest.objects.select_for_update().get(id=request_id, user=user)
            if req.status not in {"pending", "manual_review"}:
                raise WithdrawalValidationError("Нельзя отменить на данном статусе")
            req.status = "cancelled"
            req.save(update_fields=["status"])
            TransactionService.unfreeze_funds(
                req.wallet,
                currency_code=req.currency.code,
                amount=req.amount,
                reference_type="withdrawal_request",
                reference_id=str(req.id),
            )
            return req

    @staticmethod
    def process_withdrawal(request_id: str) -> WithdrawalRequest:
        with transaction.atomic():
            req = WithdrawalRequest.objects.select_for_update().get(id=request_id)
            if req.status not in {"auto_approved", "approved", "processing"}:
                raise WithdrawalValidationError("Неверный статус для обработки")
            req.status = "processing"
            req.save(update_fields=["status"])
            # simulate success payout
            withdrawal_txn = TransactionService.complete_withdrawal(
                req.wallet,
                currency_code=req.currency.code,
                amount=req.amount,
                reference_id=str(req.id),
                ip_address=req.ip_address,
            )
            req.transaction = withdrawal_txn
            req.status = "completed"
            req.completed_at = timezone.now()
            req.save(update_fields=["status", "completed_at", "transaction"])
            return req
