from django.apps import AppConfig


class CasinoConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.casino'
    verbose_name = 'Казино'

    def ready(self):
        import apps.casino.signals  # noqa
