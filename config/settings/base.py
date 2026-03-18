import os
import sys
import dotenv
from pathlib import Path
from datetime import timedelta
from celery.schedules import crontab

dotenv.load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = os.getenv('SECRET_KEY', 'change-me')
DEBUG = os.getenv('DEBUG', 'False') == 'True'
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1,localhost:9000,127.0.0.1:9000,0.0.0.0').split(',')

# Server port - hardcoded to 9000
SERVER_PORT = 9000

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',

    # Third-party
    'channels',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'django_otp',
    'django_otp.plugins.otp_totp',
    'corsheaders',
    'django_celery_results',
    'import_export',
    'phonenumber_field',
    'django_countries',

    # Monitoring
    'django_prometheus',

    # Local apps
    'apps.accounts',
    'apps.wallet',
    'apps.payments',
    'apps.sports',
    'apps.casino',
    'apps.predictions',
    'apps.referral',
    'apps.support',
    'apps.dashboard',
    'apps.miniapp',
    # 'apps.telegram_bot',
]

SITE_ID = 1

MIDDLEWARE = [
    'django_prometheus.middleware.PrometheusBeforeMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'django_otp.middleware.OTPMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'apps.accounts.middleware.LastActivityMiddleware',
    'apps.accounts.middleware.DeviceTrackingMiddleware',
    'apps.dashboard.middleware.AdminAccessMiddleware',
    'apps.dashboard.middleware.AdminActionLogMiddleware',
    'apps.miniapp.middleware.TelegramMiniAppMiddleware',
    'django_prometheus.middleware.PrometheusAfterMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.dashboard.context_processors.dashboard_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

from typing import Any

DATABASES: dict[str, dict[str, Any]] = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

if 'test' in sys.argv:
    DATABASES['default'] = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': str(BASE_DIR / 'test_db.sqlite3'),
    }

    # Убираем monitoring-зависимости для тестов, если пакет не установлен
    INSTALLED_APPS = [
        app for app in INSTALLED_APPS
        if app != 'django_prometheus'
    ]
    MIDDLEWARE = [
        m for m in MIDDLEWARE
        if 'django_prometheus' not in m
    ]

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'django-cache',
    }
}

if 'test' in sys.argv:
    os.environ.setdefault('CELERY_BROKER_URL', 'memory://')
    os.environ.setdefault('CELERY_RESULT_BACKEND', 'cache+memory://')
    CELERY_BROKER_URL = 'memory://'
    CELERY_RESULT_BACKEND = 'cache+memory://'
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = True
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels.layers.InMemoryChannelLayer',
        }
    }

SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'
SESSION_CACHE_ALIAS = 'default'
SESSION_COOKIE_AGE = int(os.getenv('SESSION_COOKIE_AGE', 1800))
SESSION_SAVE_EVERY_REQUEST = True

AUTH_USER_MODEL = 'accounts.User'

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

ACCOUNT_AUTHENTICATION_METHOD = 'email'
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = 'mandatory'
ACCOUNT_LOGIN_ATTEMPTS_LIMIT = 5
ACCOUNT_LOGIN_ATTEMPTS_TIMEOUT = 900
SOCIALACCOUNT_AUTO_SIGNUP = True

ACCOUNT_ADAPTER = 'apps.accounts.adapters.CustomAccountAdapter'

LANGUAGE_CODE = 'ru'
LANGUAGES = [('ru', 'Русский'), ('en', 'English')]
USE_I18N = True
USE_L10N = True
LOCALE_PATHS = [BASE_DIR / 'locale']

FIXTURE_DIRS = [BASE_DIR / 'fixtures']

TIME_ZONE = 'UTC'
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ... existing code ...

CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/1')
CELERY_RESULT_BACKEND = 'django-db'
CELERY_TASK_ALWAYS_EAGER = False
CELERY_TASK_EAGER_PROPAGATES = True

CELERY_BEAT_SCHEDULE = {
    # Support tasks
    'process-chat-queue': {
        'task': 'apps.support.tasks.process_chat_queue',
        'schedule': 10.0,  # каждые 10 секунд
    },
    'check-sla': {
        'task': 'apps.support.tasks.check_sla_violations',
        'schedule': crontab(minute='*/5'),  # каждые 5 минут
    },
    'auto-close-idle-chats': {
        'task': 'apps.support.tasks.auto_close_idle_chats',
        'schedule': crontab(minute='*/5'),  # каждые 5 минут
    },
    'auto-close-resolved': {
        'task': 'apps.support.tasks.auto_close_resolved_tickets',
        'schedule': crontab(hour='3', minute='0'),  # ежедневно в 3:00 UTC
    },
    'support-daily-report': {
        'task': 'apps.support.tasks.generate_support_daily_report',
        'schedule': crontab(hour='7', minute='0'),  # ежедневно в 7:00 UTC
    },
    'update-faq-stats': {
        'task': 'apps.support.tasks.update_faq_stats',
        'schedule': crontab(hour='2', minute='0'),  # ежедневно в 2:00 UTC
    },
    'cleanup-old-attachments': {
        'task': 'apps.support.tasks.cleanup_old_attachments',
        'schedule': crontab(hour='4', minute='0'),  # ежедневно в 4:00 UTC
    },
    # Payments tasks
    'payments-check-pending-deposits': {
        'task': 'apps.payments.tasks.check_pending_deposits',
        'schedule': crontab(minute='*/5'),
    },
    'payments-check-pending-payouts': {
        'task': 'apps.payments.tasks.check_pending_payouts',
        'schedule': crontab(minute='*/5'),
    },
    'payments-expire-old-deposits': {
        'task': 'apps.payments.tasks.expire_old_deposits',
        'schedule': crontab(minute='*/10'),
    },
    'payments-retry-failed-payouts': {
        'task': 'apps.payments.tasks.retry_failed_payouts',
        'schedule': crontab(minute='*/15'),
    },
    # Miniapp analytics and notifications
    'miniapp-update-analytics': {
        'task': 'apps.miniapp.tasks.update_miniapp_analytics',
        'schedule': crontab(minute='*/5'),
    },
    'miniapp-cleanup-sessions': {
        'task': 'apps.miniapp.tasks.cleanup_expired_sessions',
        'schedule': crontab(minute='0', hour='*'),
    },
    'miniapp-daily-digest': {
        'task': 'apps.miniapp.tasks.send_daily_digest',
        'schedule': crontab(hour='8', minute='0'),
    },
    'miniapp-daily-report': {
        'task': 'apps.miniapp.tasks.generate_miniapp_report',
        'schedule': crontab(hour='9', minute='0'),
    },
    'miniapp-sync-telegram-data': {
        'task': 'apps.miniapp.tasks.sync_telegram_user_data',
        'schedule': crontab(hour='3', minute='30'),
    },
}

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [os.getenv('REDIS_URL', 'redis://redis:6379/0')],
        },
    },
}

# Placeholder for OTP device settings
OTP_TOTP_ISSUER = 'DOD'

CORS_ALLOW_ALL_ORIGINS = True

# CSRF Configuration
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:8000',
    'http://127.0.0.1:8000',
    'http://0.0.0.0:8000',
    'https://localhost:8000',
    'https://127.0.0.1:8000',
    'http://localhost:9000',
    'http://127.0.0.1:9000',
    'http://0.0.0.0:9000',
    'https://localhost:9000',
    'https://127.0.0.1:9000',
]
csrf_trusted_origins_env = os.getenv('CSRF_TRUSTED_ORIGINS')
if csrf_trusted_origins_env:
    CSRF_TRUSTED_ORIGINS.extend(csrf_trusted_origins_env.split(','))

CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SECURE = False if DEBUG else True

# Email
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True') == 'True'
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'DOD <noreply@dod.com>')

# User and security settings
RATE_LIMIT_LOGIN = os.getenv('RATE_LIMIT_LOGIN', '5/15m')
RATE_LIMIT_REGISTER = os.getenv('RATE_LIMIT_REGISTER', '3/1h')
RATE_LIMIT_SMS = os.getenv('RATE_LIMIT_SMS', '3/10m')

# Phone field
PHONENUMBER_DEFAULT_REGION = 'RU'
PHONENUMBER_DB_FORMAT = 'E164'

# Internationalization options
PHONENUMBER_DEFAULT_FORMAT = 'E164'

# Telegram Bot
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')

# Site URL (used for webhooks, success/fail redirects)
SITE_URL = os.getenv('SITE_URL', 'http://localhost:9000')

# NOWPayments (Crypto)
NOWPAYMENTS_API_KEY = os.getenv('NOWPAYMENTS_API_KEY', '')
NOWPAYMENTS_IPN_SECRET = os.getenv('NOWPAYMENTS_IPN_SECRET', '')
NOWPAYMENTS_API_URL = os.getenv('NOWPAYMENTS_API_URL', 'https://api.nowpayments.io')
