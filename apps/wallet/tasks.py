from celery import shared_task
from django.utils import timezone

from apps.wallet.services.withdrawal_service import WithdrawalService
from apps.wallet.services.rate_service import RateService
from apps.wallet.models import WithdrawalRequest


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def process_withdrawal_task(self, request_id: str):
    try:
        WithdrawalService.process_withdrawal(request_id)
    except Exception as exc:  # noqa: BLE001
        raise self.retry(exc=exc)


@shared_task
def update_exchange_rates():
    # Placeholder: will call external APIs; for now no-op
    RateService.update_all_rates()


@shared_task
def check_expired_withdrawals():
    now = timezone.now()
    expired = WithdrawalRequest.objects.filter(status="pending", expires_at__lt=now)
    for req in expired:
        WithdrawalService.cancel_withdrawal(req.id, req.user)


@shared_task
def notify_admins_pending_withdrawals():
    # Placeholder: add admin notification (email/telegram) when implemented
    pass


@shared_task
def daily_wallet_reconciliation():
    # Placeholder: implement reconciliation logic comparing balances vs transactions
    pass
