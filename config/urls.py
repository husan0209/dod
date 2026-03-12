from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from django.shortcuts import redirect
from django.db import connection
from django.core.cache import cache

from apps.referral.services.referral_service import ReferralService

def home_view(request):
    """Главная страница - редирект на dashboard или login"""
    if request.user.is_authenticated:
        return redirect('dashboard:dashboard')
    return redirect('accounts:login')

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
    path('', home_view, name='home'),
    path('admin/', admin.site.urls),
    path('accounts/', include('apps.accounts.urls')),
    path('allauth/', include('allauth.urls')),
    path('admin-panel/', include('apps.dashboard.urls')),
    path('wallet/', include('apps.wallet.urls')),
    path('payments/', include('apps.payments.urls')),
    path('casino/', include('apps.casino.urls')),
    path('sports/', include('apps.sports.urls')),
    path('predictions/', include('apps.predictions.urls')),
    path('partners/', include('apps.referral.urls')),
    path('support/', include('apps.support.urls')),
    path('telegram/', include('apps.telegram_bot.urls')),
    path('tg/', include('apps.miniapp.urls')),
    path('r/<str:code>/', referral_redirect_view, name='referral-redirect'),
]

# Webhook URLs at root level for cleaner provider integration
from apps.payments import views as payment_views

urlpatterns += [
    path('webhooks/payments/rukassa/', payment_views.rukassa_webhook, name='webhook-rukassa'),
    path('webhooks/payments/nowpayments/', payment_views.nowpayments_webhook, name='webhook-nowpayments'),
    path('webhooks/payouts/nowpayments/', payment_views.nowpayments_payout_webhook, name='webhook-nowpayments-payout'),
]

urlpatterns += [
    path('health/', health_check, name='health-check'),
]

# Monitoring (optional if package installed)
if 'django_prometheus' in settings.INSTALLED_APPS:
    urlpatterns.append(path('metrics/', include('django_prometheus.urls')))

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
