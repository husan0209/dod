from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import User


def _create_wallet(instance: User) -> None:
    try:
        from apps.wallet.services.wallet_service import WalletService

        WalletService.create_wallet(instance)
    except Exception:
        # Avoid blocking user creation; should be logged by Sentry/monitoring in real setup
        pass


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_related(sender, instance: User, created: bool, **kwargs):
    if created:
        _create_wallet(instance)
