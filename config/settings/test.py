import os
from .base import *

DEBUG = False
SECRET_KEY = 'test-secret-key-not-for-production'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'dod_test'),
        'USER': os.getenv('DB_USER', 'dod_test'),
        'PASSWORD': os.getenv('DB_PASSWORD', 'test'),
        'HOST': os.getenv('DB_HOST', 'localhost'),
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
