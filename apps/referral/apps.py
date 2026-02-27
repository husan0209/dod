from django.apps import AppConfig


class ReferralConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.referral'
    verbose_name = 'Реферальная программа'

    def ready(self):
        import apps.referral.signals
