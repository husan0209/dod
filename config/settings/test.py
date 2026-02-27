from .base import *

DEBUG = False
SECRET_KEY = 'test-secret-key-not-for-production'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env('DB_NAME', default='dod_test'),
        'USER': env('DB_USER', default='dod_test'),
        'PASSWORD': env('DB_PASSWORD', default='test'),
        'HOST': env('DB_HOST', default='localhost'),
        'PORT': '5432',
        'TEST': {
            'NAME': 'dod_test_db',
        },
    }
}

# Быстрые пароли для тестов
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Отключить Celery для тестов
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Email
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# Cache
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# Channels
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    }
}

# Отключить throttling в тестах
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [],
}
