import os
import sys

from celery import Celery
from celery.schedules import crontab
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

# Force in-memory broker for tests if not explicitly provided
if 'test' in sys.argv:
    os.environ.setdefault('CELERY_BROKER_URL', 'memory://')
    os.environ.setdefault('CELERY_RESULT_BACKEND', 'cache+memory://')

app = Celery('config')
app.config_from_object('django.conf:settings', namespace='CELERY')

if 'test' in sys.argv or settings.CELERY_BROKER_URL.startswith('memory'):
    app.conf.update(
        broker_url=os.environ.get('CELERY_BROKER_URL', 'memory://'),
        result_backend=os.environ.get('CELERY_RESULT_BACKEND', 'cache+memory://'),
        task_always_eager=True,
        task_eager_propagates=True,
    )

# Celery Beat Schedule
app.conf.beat_schedule = {
    # Market Management
    'close-expired-markets': {
        'task': 'apps.predictions.tasks.close_expired_markets',
        'schedule': crontab(minute=0),  # Каждый час
    },
    'update-market-statistics': {
        'task': 'apps.predictions.tasks.update_market_statistics',
        'schedule': crontab(minute='*/30'),  # Каждые 30 минут
    },
    'calculate-trending-markets': {
        'task': 'apps.predictions.tasks.calculate_trending_markets',
        'schedule': crontab(minute=0),  # Каждый час
    },
    
    # Price Recording
    'record-periodic-prices': {
        'task': 'apps.predictions.tasks.record_periodic_prices',
        'schedule': crontab(minute='*/5'),  # Каждые 5 минут
    },
    'update-volume-24h': {
        'task': 'apps.predictions.tasks.update_volume_24h',
        'schedule': crontab(minute='*/30'),  # Каждые 30 минут
    },
    
    # Cleanup Tasks (в ночное время)
    'cleanup-expired-positions': {
        'task': 'apps.predictions.tasks.cleanup_expired_positions',
        'schedule': crontab(hour=2, minute=0),  # 2:00 AM
    },
    'delete-old-comments': {
        'task': 'apps.predictions.tasks.delete_old_comments',
        'schedule': crontab(hour=3, minute=0),  # 3:00 AM
    },
    
    # Notifications (каждый час)
    'send-market-closing-notifications': {
        'task': 'apps.predictions.tasks.send_market_closing_notifications',
        'schedule': crontab(minute=0),  # Каждый час
    },
    
    # Payment System Tasks
    'check-pending-deposits': {
        'task': 'apps.payments.tasks.check_pending_deposits',
        'schedule': 300.0,  # Every 5 minutes
    },
    'check-pending-payouts': {
        'task': 'apps.payments.tasks.check_pending_payouts',
        'schedule': 300.0,  # Every 5 minutes
    },
    'expire-old-deposits': {
        'task': 'apps.payments.tasks.expire_old_deposits',
        'schedule': 600.0,  # Every 10 minutes
    },
    'retry-failed-payouts': {
        'task': 'apps.payments.tasks.retry_failed_payouts',
        'schedule': 60.0,  # Every minute
    },
    'generate-daily-reports': {
        'task': 'apps.payments.tasks.generate_daily_reports',
        'schedule': crontab(hour=0, minute=5),  # Daily at 00:05
    },
    'provider-health-checks': {
        'task': 'apps.payments.tasks.provider_health_checks',
        'schedule': 900.0,  # Every 15 minutes
    },
    'reconciliation-check': {
        'task': 'apps.payments.tasks.reconciliation_check',
        'schedule': crontab(hour=2, minute=0),  # Daily at 02:00
    },
    'cleanup-old-webhook-logs': {
        'task': 'apps.payments.tasks.cleanup_old_webhook_logs',
        'schedule': crontab(hour=3, minute=0),  # Daily at 03:00
    },
}

# Часовой пояс для Celery Beat
app.conf.timezone = 'UTC'

app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

