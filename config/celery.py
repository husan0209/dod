import os
import sys

from celery import Celery
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

app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)
