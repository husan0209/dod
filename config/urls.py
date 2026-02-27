from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache

from apps.referral.services.referral_service import ReferralService

def health_check(request):
    """
    Health check endpoint для Docker и мониторинга.
    Проверяет: DB, Redis, Celery.
    """
    status = {'status': 'healthy'}
    checks = {}

    # Database
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        checks['database'] = 'ok'
    except Exception as e:
        checks['database'] = f'error: {str(e)}'
        status['status'] = 'unhealthy'

    # Redis
    try:
        cache.set('health_check', 'ok', 10)
        checks['redis'] = 'ok' if cache.get('health_check') == 'ok' else 'error'
    except Exception as e:
        checks['redis'] = f'error: {str(e)}'
        status['status'] = 'unhealthy'

    # Celery (проверка через Redis)
    try:
        from django_celery_beat.models import PeriodicTask
        checks['celery_beat'] = 'ok' if PeriodicTask.objects.exists() else 'no tasks'
    except Exception:
        checks['celery_beat'] = 'unavailable'

    status['checks'] = checks

    http_status = 200 if status['status'] == 'healthy' else 503
    return JsonResponse(status, status=http_status)

def referral_redirect_view(request, code):
    return ReferralService.process_referral_click(request, code)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('dashboard/', include('apps.dashboard.urls')),
    path('wallet/', include('apps.wallet.urls')),
    path('payments/', include('apps.payments.urls')),
    path('casino/', include('apps.casino.urls')),
    path('predictions/', include('apps.predictions.urls')),
    path('partners/', include('apps.referral.urls')),
    path('support/', include('apps.support.urls')),
    path('telegram/', include('apps.telegram_bot.urls')),
    path('admin-panel/', include('apps.dashboard.urls')),
    path('tg/', include('apps.miniapp.urls')),
    path('r/<str:code>/', referral_redirect_view, name='referral-redirect'),
]

urlpatterns += [
    path('health/', health_check, name='health-check'),
]

# Monitoring (optional if package installed)
if 'django_prometheus' in settings.INSTALLED_APPS:
    urlpatterns.insert(0, path('', include('django_prometheus.urls')))

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
