

# 📋 ТЗ ПРОЕКТА DOD — ЭТАП 12

# ДЕПЛОЙ + ТЕСТИРОВАНИЕ + ЗАПУСК

```
╔══════════════════════════════════════════════════════╗
║                                                      ║
║   ПРОЕКТ:    DOD                                    ║
║   ЭТАП:      12 из 12 (ФИНАЛЬНЫЙ)                  ║
║   НАЗВАНИЕ:  Деплой + Тестирование + Запуск         ║
║   ЗАВИСИТ:   Этапы 1-11 (полностью завершены)       ║
║   ЦЕЛЬ:      Развернуть платформу на сервере,       ║
║              покрыть тестами, настроить CI/CD,       ║
║              мониторинг, бэкапы, безопасность,      ║
║              подготовить к production запуску,       ║
║              провести нагрузочное тестирование,     ║
║              документировать всё для команды        ║
║                                                      ║
╚══════════════════════════════════════════════════════╝
```

---

## 📌 КОНТЕКСТ ДЛЯ ИИ-АГЕНТА

```
Этапы 1-11 выполнены. У тебя есть:
  - Полная авторизация + 2FA + KYC
  - Мультивалютный кошелёк + платежи
  - Ставки на спорт
  - Казино (Crash, Mines, Dice, Plinko, Roulette, Slots)
  - Prediction Market
  - Партнёрская программа
  - Чат поддержки + уведомления
  - Полная админ-панель
  - Telegram Mini App + бот

Стек:
  Backend: Django 5.1 + Django Channels (ASGI)
  Database: PostgreSQL 16
  Cache/Broker: Redis 7
  Task Queue: Celery + Celery Beat
  Frontend: HTMX + TailwindCSS
  WebSocket: Django Channels + Daphne
  Контейнеризация: Docker + Docker Compose
  CI/CD: GitHub Actions
  Сервер: Ubuntu 22.04+ (VPS/VDS)
  Веб-сервер: Nginx (reverse proxy)
  SSL: Let's Encrypt (Certbot)
  Мониторинг: Prometheus + Grafana
  Логирование: ELK Stack или Loki + Grafana
  Бэкапы: pg_dump + cron + S3/Object Storage

В этом этапе ты:
  1. Контейнеризируешь всё через Docker
  2. Настраиваешь CI/CD пайплайн
  3. Деплоишь на production сервер
  4. Пишешь тесты (unit, integration, e2e)
  5. Настраиваешь мониторинг и алерты
  6. Проводишь нагрузочное тестирование
  7. Настраиваешь бэкапы и disaster recovery
  8. Проводишь security audit
  9. Документируешь всё
  10. Готовишь к запуску

Этот этап включает 6 шагов.
Каждый шаг — отдельная задача.
Выполняй строго по порядку.
```

---

## ШАГ 12.1 — DOCKER + ИНФРАСТРУКТУРА

### Задача

```
Контейнеризируй все компоненты проекта,
настрой Docker Compose для development
и production, подготовь инфраструктуру.
```

### Структура файлов Docker

```
deploy/
├── docker/
│   ├── Dockerfile              # Основной образ Django
│   ├── Dockerfile.celery       # Celery worker
│   ├── Dockerfile.nginx        # Nginx
│   ├── Dockerfile.channels     # Daphne (WebSocket)
│   └── entrypoint.sh           # Точка входа
├── nginx/
│   ├── nginx.conf              # Основной конфиг
│   ├── conf.d/
│   │   ├── default.conf        # HTTP → HTTPS редирект
│   │   └── dod.conf            # Основной сайт
│   ├── ssl/                    # Сертификаты
│   └── snippets/
│       ├── ssl-params.conf     # SSL параметры
│       └── security.conf       # Security headers
├── monitoring/
│   ├── prometheus/
│   │   └── prometheus.yml      # Конфиг Prometheus
│   ├── grafana/
│   │   ├── provisioning/
│   │   │   ├── dashboards/
│   │   │   │   ├── django.json     # Дашборд Django
│   │   │   │   ├── postgres.json   # Дашборд PostgreSQL
│   │   │   │   ├── redis.json      # Дашборд Redis
│   │   │   │   └── celery.json     # Дашборд Celery
│   │   │   └── datasources/
│   │   │       └── prometheus.yml
│   │   └── grafana.ini
│   └── alertmanager/
│       └── alertmanager.yml
├── backups/
│   ├── backup.sh               # Скрипт бэкапа
│   ├── restore.sh              # Скрипт восстановления
│   └── cron/
│       └── backup-cron         # Cron задача
├── scripts/
│   ├── deploy.sh               # Деплой скрипт
│   ├── rollback.sh             # Откат
│   ├── health-check.sh         # Проверка здоровья
│   ├── init-server.sh          # Инициализация сервера
│   └── ssl-renew.sh            # Обновление SSL
├── .env.production             # Production переменные
├── .env.staging                # Staging переменные
docker-compose.yml              # Development
docker-compose.prod.yml         # Production
docker-compose.staging.yml      # Staging
```

### Dockerfile (Django)

```
# deploy/docker/Dockerfile

FROM python:3.12-slim as builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings.production

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN addgroup --system django && \
    adduser --system --ingroup django django

COPY --from=builder /install /usr/local

COPY . .

RUN python manage.py collectstatic --noinput

RUN chown -R django:django /app

USER django

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

ENTRYPOINT ["sh", "deploy/docker/entrypoint.sh"]
```

### Entrypoint

```
# deploy/docker/entrypoint.sh
#!/bin/sh
set -e

echo "Ожидание PostgreSQL..."
while ! nc -z $DB_HOST $DB_PORT; do
  sleep 0.5
done
echo "PostgreSQL доступен."

echo "Ожидание Redis..."
while ! nc -z $REDIS_HOST 6379; do
  sleep 0.5
done
echo "Redis доступен."

echo "Применение миграций..."
python manage.py migrate --noinput

echo "Загрузка fixtures..."
python manage.py loaddata initial_data || true

echo "Запуск сервера..."
exec "$@"
```

### Docker Compose (Production)

```
# docker-compose.prod.yml

version: '3.9'

services:

  # ── PostgreSQL ──────────────────
  db:
    image: postgres:16-alpine
    restart: always
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./deploy/backups:/backups
    environment:
      POSTGRES_DB: ${DB_NAME}
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    ports:
      - "127.0.0.1:5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5
    deploy:
      resources:
        limits:
          memory: 2G

  # ── Redis ───────────────────────
  redis:
    image: redis:7-alpine
    restart: always
    command: >
      redis-server
      --maxmemory 512mb
      --maxmemory-policy allkeys-lru
      --appendonly yes
      --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    ports:
      - "127.0.0.1:6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD}", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    deploy:
      resources:
        limits:
          memory: 1G

  # ── Django (Gunicorn) ───────────
  web:
    build:
      context: .
      dockerfile: deploy/docker/Dockerfile
    restart: always
    command: >
      gunicorn config.wsgi:application
      --bind 0.0.0.0:8000
      --workers ${GUNICORN_WORKERS:-4}
      --threads 2
      --timeout 120
      --max-requests 1000
      --max-requests-jitter 100
      --access-logfile -
      --error-logfile -
      --log-level info
    volumes:
      - static_volume:/app/staticfiles
      - media_volume:/app/media
    env_file:
      - .env.production
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    deploy:
      resources:
        limits:
          memory: 2G

  # ── Daphne (WebSocket/ASGI) ────
  channels:
    build:
      context: .
      dockerfile: deploy/docker/Dockerfile
    restart: always
    command: >
      daphne config.asgi:application
      --bind 0.0.0.0
      --port 8001
      --verbosity 1
    env_file:
      - .env.production
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    deploy:
      resources:
        limits:
          memory: 1G

  # ── Celery Worker ───────────────
  celery_worker:
    build:
      context: .
      dockerfile: deploy/docker/Dockerfile
    restart: always
    command: >
      celery -A config worker
      --loglevel=info
      --concurrency=${CELERY_CONCURRENCY:-4}
      --max-tasks-per-child=1000
      -Q default,notifications,payments,analytics
    env_file:
      - .env.production
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    deploy:
      resources:
        limits:
          memory: 2G

  # ── Celery Beat ─────────────────
  celery_beat:
    build:
      context: .
      dockerfile: deploy/docker/Dockerfile
    restart: always
    command: >
      celery -A config beat
      --loglevel=info
      --scheduler django_celery_beat.schedulers:DatabaseScheduler
    env_file:
      - .env.production
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    deploy:
      resources:
        limits:
          memory: 512M

  # ── Nginx ───────────────────────
  nginx:
    image: nginx:1.25-alpine
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./deploy/nginx/conf.d:/etc/nginx/conf.d
      - ./deploy/nginx/snippets:/etc/nginx/snippets
      - ./deploy/nginx/ssl:/etc/nginx/ssl
      - static_volume:/var/www/static
      - media_volume:/var/www/media
      - certbot_www:/var/www/certbot
    depends_on:
      - web
      - channels

  # ── Certbot (SSL) ───────────────
  certbot:
    image: certbot/certbot
    volumes:
      - ./deploy/nginx/ssl:/etc/letsencrypt
      - certbot_www:/var/www/certbot
    entrypoint: >
      /bin/sh -c "trap exit TERM;
      while :; do
        certbot renew --webroot
        --webroot-path=/var/www/certbot;
        sleep 12h;
      done"

volumes:
  postgres_data:
  redis_data:
  static_volume:
  media_volume:
  certbot_www:
```

### Nginx конфигурация (production)

```
# deploy/nginx/conf.d/dod.conf

upstream django {
    server web:8000;
}

upstream channels {
    server channels:8001;
}

# HTTP → HTTPS
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 301 https://$host$request_uri;
    }
}

# HTTPS
server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    # SSL
    ssl_certificate /etc/nginx/ssl/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/live/yourdomain.com/privkey.pem;
    include /etc/nginx/snippets/ssl-params.conf;

    # Security headers
    include /etc/nginx/snippets/security.conf;

    # Gzip
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types
        text/plain text/css text/javascript
        application/javascript application/json
        application/xml image/svg+xml;

    # Статика
    location /static/ {
        alias /var/www/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
        access_log off;
    }

    # Медиа
    location /media/ {
        alias /var/www/media/;
        expires 7d;
        add_header Cache-Control "public";
    }

    # WebSocket
    location /ws/ {
        proxy_pass http://channels;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
        proxy_send_timeout 86400;
    }

    # Админ-панель (ограничение по IP, опционально)
    location /admin-panel/ {
        # allow 1.2.3.4;  # IP администратора
        # deny all;       # Раскомментировать в production

        proxy_pass http://django;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Telegram webhook (ограничение по IP)
    location /tg/bot/webhook/ {
        # Telegram IP ranges
        allow 149.154.160.0/20;
        allow 91.108.4.0/22;
        deny all;

        proxy_pass http://django;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Всё остальное
    location / {
        proxy_pass http://django;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300;

        # Rate limiting
        limit_req zone=general burst=20 nodelay;
    }

    # Health check (без логирования)
    location /health/ {
        proxy_pass http://django;
        access_log off;
    }

    # Limit zones
    # (определяются в nginx.conf)
    # limit_req_zone $binary_remote_addr zone=general:10m rate=10r/s;
    # limit_req_zone $binary_remote_addr zone=api:10m rate=30r/s;
    # limit_req_zone $binary_remote_addr zone=auth:10m rate=5r/s;

    # Запрет доступа
    location ~ /\. { deny all; }
    location ~ \.py$ { deny all; }

    client_max_body_size 10M;
}
```

### Security Headers

```
# deploy/nginx/snippets/security.conf

add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;
add_header Content-Security-Policy
  "default-src 'self';
   script-src 'self' 'unsafe-inline' 'unsafe-eval'
     https://telegram.org https://cdn.tailwindcss.com
     https://unpkg.com https://cdn.jsdelivr.net;
   style-src 'self' 'unsafe-inline'
     https://cdn.tailwindcss.com https://fonts.googleapis.com;
   font-src 'self' https://fonts.gstatic.com;
   img-src 'self' data: https:;
   connect-src 'self' wss: https:;
   frame-src 'self' https://telegram.org;
   object-src 'none';
   base-uri 'self';"
  always;
add_header Strict-Transport-Security
  "max-age=31536000; includeSubDomains; preload" always;
```

### SSL параметры

```
# deploy/nginx/snippets/ssl-params.conf

ssl_protocols TLSv1.2 TLSv1.3;
ssl_prefer_server_ciphers on;
ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
ssl_session_timeout 1d;
ssl_session_cache shared:SSL:10m;
ssl_session_tickets off;

ssl_stapling on;
ssl_stapling_verify on;
resolver 8.8.8.8 8.8.4.4 valid=300s;
resolver_timeout 5s;
```

### Production переменные (.env.production)

```
# .env.production

# Django
DJANGO_SETTINGS_MODULE=config.settings.production
SECRET_KEY=<сгенерировать: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())">
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
CSRF_TRUSTED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
SECURE_SSL_REDIRECT=True
SECURE_PROXY_SSL_HEADER=HTTP_X_FORWARDED_PROTO,https

# Database
DB_NAME=dod_production
DB_USER=dod_user
DB_PASSWORD=<strong_password_here>
DB_HOST=db
DB_PORT=5432

# Redis
REDIS_HOST=redis
REDIS_PASSWORD=<strong_password_here>
REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
CELERY_BROKER_URL=redis://:${REDIS_PASSWORD}@redis:6379/1
CACHE_URL=redis://:${REDIS_PASSWORD}@redis:6379/2
CHANNEL_LAYERS_URL=redis://:${REDIS_PASSWORD}@redis:6379/3

# Email (production SMTP)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.yourdomain.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=noreply@yourdomain.com
EMAIL_HOST_PASSWORD=<email_password>

# Telegram
TELEGRAM_BOT_TOKEN=<bot_token>
TELEGRAM_BOT_USERNAME=DODPlatformBot
TELEGRAM_WEBAPP_URL=https://yourdomain.com/tg/
TELEGRAM_WEBHOOK_SECRET=<random_secret>

# Payments
NOWPAYMENTS_API_KEY=<api_key>
NOWPAYMENTS_IPN_SECRET=<ipn_secret>
RUKASSA_SHOP_ID=<shop_id>
RUKASSA_TOKEN=<token>

# OAuth
GOOGLE_CLIENT_ID=<client_id>
GOOGLE_CLIENT_SECRET=<client_secret>

# Sentry (error tracking)
SENTRY_DSN=https://<key>@sentry.io/<project>

# Gunicorn
GUNICORN_WORKERS=4
CELERY_CONCURRENCY=4

# Backups
BACKUP_S3_BUCKET=dod-backups
BACKUP_S3_ACCESS_KEY=<access_key>
BACKUP_S3_SECRET_KEY=<secret_key>
BACKUP_S3_ENDPOINT=<s3_endpoint>
BACKUP_RETENTION_DAYS=30
```

### Django Production Settings

```
# config/settings/production.py

from .base import *

DEBUG = False
ALLOWED_HOSTS = env('ALLOWED_HOSTS', default='').split(',')

# Security
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'SAMEORIGIN'
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# CSRF
CSRF_TRUSTED_ORIGINS = env(
    'CSRF_TRUSTED_ORIGINS', default=''
).split(',')

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env('DB_NAME'),
        'USER': env('DB_USER'),
        'PASSWORD': env('DB_PASSWORD'),
        'HOST': env('DB_HOST', default='db'),
        'PORT': env('DB_PORT', default='5432'),
        'CONN_MAX_AGE': 600,
        'CONN_HEALTH_CHECKS': True,
        'OPTIONS': {
            'connect_timeout': 10,
        },
    }
}

# Cache
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': env('CACHE_URL'),
        'TIMEOUT': 300,
        'OPTIONS': {
            'db': '2',
        },
    }
}

# Static / Media
STATIC_ROOT = '/app/staticfiles'
MEDIA_ROOT = '/app/media'

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} '
                      '{thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'WARNING',
        },
        'apps': {
            'handlers': ['console'],
            'level': 'INFO',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}

# Sentry (error tracking)
SENTRY_DSN = env('SENTRY_DSN', default='')
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.redis import RedisIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            DjangoIntegration(),
            CeleryIntegration(),
            RedisIntegration(),
        ],
        traces_sample_rate=0.1,
        send_default_pii=False,
        environment='production',
    )

# Email
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
```

### Health Check endpoint

```
# config/urls.py (добавить)

from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache

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

urlpatterns += [
    path('health/', health_check, name='health-check'),
]
```

### Критерий готовности шага 12.1

```
□ Dockerfile: multi-stage build, non-root user
□ Dockerfile: HEALTHCHECK директива
□ docker-compose.prod.yml: все сервисы
  □ PostgreSQL 16 (volumes, healthcheck, limits)
  □ Redis 7 (password, appendonly, limits)
  □ Django/Gunicorn (workers, threads, limits)
  □ Daphne/Channels (WebSocket)
  □ Celery Worker (4 очереди)
  □ Celery Beat (DatabaseScheduler)
  □ Nginx (reverse proxy, SSL)
  □ Certbot (autorenewal)
□ Nginx: HTTPS + security headers + gzip
□ Nginx: WebSocket проксирование (/ws/)
□ Nginx: rate limiting
□ Nginx: IP ограничения (admin, webhook)
□ SSL: TLS 1.2+, HSTS, OCSP stapling
□ .env.production: все переменные
□ Django production settings: security hardened
□ Health check endpoint (/health/)
□ entrypoint.sh: ожидание DB + Redis + миграции
□ Volumes: данные персистентны
□ Все контейнеры перезапускаются (restart: always)
```

---

## ШАГ 12.2 — CI/CD + ДЕПЛОЙ

### Задача

```
Настрой GitHub Actions для автоматического
тестирования и деплоя. Скрипты деплоя
и отката. Staging и production окружения.
```

### GitHub Actions Pipeline

```
# .github/workflows/ci.yml

name: CI Pipeline

on:
  push:
    branches: [main, develop, staging]
  pull_request:
    branches: [main]

jobs:

  # ── LINT ────────────────────────
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          pip install flake8 black isort mypy

      - name: Flake8
        run: flake8 apps/ config/ --max-line-length=120

      - name: Black check
        run: black --check apps/ config/

      - name: isort check
        run: isort --check-only apps/ config/

  # ── TESTS ───────────────────────
  test:
    runs-on: ubuntu-latest
    needs: lint

    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_DB: dod_test
          POSTGRES_USER: dod_test
          POSTGRES_PASSWORD: test_password
        ports: ['5432:5432']
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

      redis:
        image: redis:7-alpine
        ports: ['6379:6379']
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Cache pip
        uses: actions/cache@v4
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-pip-${{ hashFiles('requirements.txt') }}

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run tests
        env:
          DB_NAME: dod_test
          DB_USER: dod_test
          DB_PASSWORD: test_password
          DB_HOST: localhost
          REDIS_HOST: localhost
          SECRET_KEY: test-secret-key
          DJANGO_SETTINGS_MODULE: config.settings.test
        run: |
          python manage.py test apps/ \
            --verbosity=2 \
            --parallel \
            --failfast

      - name: Coverage report
        env:
          DB_NAME: dod_test
          DB_USER: dod_test
          DB_PASSWORD: test_password
          DB_HOST: localhost
          REDIS_HOST: localhost
          SECRET_KEY: test-secret-key
          DJANGO_SETTINGS_MODULE: config.settings.test
        run: |
          pip install coverage
          coverage run manage.py test apps/ --parallel
          coverage report --fail-under=70
          coverage xml

  # ── SECURITY ────────────────────
  security:
    runs-on: ubuntu-latest
    needs: lint
    steps:
      - uses: actions/checkout@v4

      - name: Safety check
        run: |
          pip install safety
          safety check -r requirements.txt

      - name: Bandit (security linter)
        run: |
          pip install bandit
          bandit -r apps/ -ll

  # ── BUILD ───────────────────────
  build:
    runs-on: ubuntu-latest
    needs: [test, security]
    if: github.ref == 'refs/heads/main' || github.ref == 'refs/heads/staging'
    steps:
      - uses: actions/checkout@v4

      - name: Build Docker image
        run: |
          docker build -t dod-app:${{ github.sha }} \
            -f deploy/docker/Dockerfile .

      - name: Save image
        run: |
          docker save dod-app:${{ github.sha }} | gzip > image.tar.gz

      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: docker-image
          path: image.tar.gz
          retention-days: 3


# .github/workflows/deploy.yml

name: Deploy

on:
  workflow_run:
    workflows: ['CI Pipeline']
    types: [completed]
    branches: [main, staging]

jobs:
  deploy-staging:
    if: >
      github.event.workflow_run.conclusion == 'success' &&
      github.event.workflow_run.head_branch == 'staging'
    runs-on: ubuntu-latest
    environment: staging
    steps:
      - uses: actions/checkout@v4
      - name: Deploy to staging
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.STAGING_HOST }}
          username: ${{ secrets.DEPLOY_USER }}
          key: ${{ secrets.SSH_KEY }}
          script: |
            cd /opt/dod
            git pull origin staging
            docker compose -f docker-compose.staging.yml \
              pull && \
            docker compose -f docker-compose.staging.yml \
              up -d --build && \
            docker compose -f docker-compose.staging.yml \
              exec web python manage.py migrate --noinput
            echo "Staging deployed: $(date)"

  deploy-production:
    if: >
      github.event.workflow_run.conclusion == 'success' &&
      github.event.workflow_run.head_branch == 'main'
    runs-on: ubuntu-latest
    environment: production
    steps:
      - uses: actions/checkout@v4
      - name: Deploy to production
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.PRODUCTION_HOST }}
          username: ${{ secrets.DEPLOY_USER }}
          key: ${{ secrets.SSH_KEY }}
          script: |
            cd /opt/dod
            # Бэкап перед деплоем
            ./deploy/backups/backup.sh pre-deploy
            # Деплой
            git pull origin main
            docker compose -f docker-compose.prod.yml \
              up -d --build
            docker compose -f docker-compose.prod.yml \
              exec web python manage.py migrate --noinput
            # Health check
            ./deploy/scripts/health-check.sh || \
              ./deploy/scripts/rollback.sh
            echo "Production deployed: $(date)"
```

### Скрипт деплоя

```
# deploy/scripts/deploy.sh
#!/bin/bash
set -e

ENVIRONMENT=${1:-staging}
APP_DIR="/opt/dod"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
COMPOSE_FILE="docker-compose.${ENVIRONMENT}.yml"

echo "═══ Деплой DOD ($ENVIRONMENT) ═══"
echo "Время: $TIMESTAMP"

# 1. Бéкап текущей версии
echo "1. Создание бэкапа..."
cd $APP_DIR
git rev-parse HEAD > /tmp/dod_prev_commit
docker compose -f $COMPOSE_FILE exec -T db \
  pg_dump -U $DB_USER $DB_NAME | gzip > \
  deploy/backups/pre-deploy-${TIMESTAMP}.sql.gz

# 2. Получить новый код
echo "2. Обновление кода..."
git pull origin $(git branch --show-current)

# 3. Собрать и запустить
echo "3. Сборка и запуск..."
docker compose -f $COMPOSE_FILE build --no-cache web
docker compose -f $COMPOSE_FILE up -d

# 4. Миграции
echo "4. Применение миграций..."
docker compose -f $COMPOSE_FILE exec -T web \
  python manage.py migrate --noinput

# 5. Collectstatic
echo "5. Сборка статики..."
docker compose -f $COMPOSE_FILE exec -T web \
  python manage.py collectstatic --noinput

# 6. Health check
echo "6. Проверка здоровья..."
sleep 10
for i in $(seq 1 5); do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
    https://yourdomain.com/health/)
  if [ "$STATUS" = "200" ]; then
    echo "✅ Health check OK"
    break
  fi
  echo "⚠️ Попытка $i: статус $STATUS"
  sleep 5
done

if [ "$STATUS" != "200" ]; then
  echo "❌ Health check FAILED. Откат..."
  ./deploy/scripts/rollback.sh
  exit 1
fi

echo "═══ Деплой завершён успешно ═══"
```

### Скрипт отката

```
# deploy/scripts/rollback.sh
#!/bin/bash
set -e

APP_DIR="/opt/dod"
COMPOSE_FILE="docker-compose.prod.yml"

echo "═══ ОТКАТ DOD ═══"

cd $APP_DIR

# Откат к предыдущему коммиту
PREV_COMMIT=$(cat /tmp/dod_prev_commit 2>/dev/null)

if [ -z "$PREV_COMMIT" ]; then
  echo "❌ Файл предыдущего коммита не найден"
  echo "Откат к предыдущему коммиту Git:"
  git log --oneline -5
  echo "Используйте: git checkout <commit>"
  exit 1
fi

echo "Откат к коммиту: $PREV_COMMIT"
git checkout $PREV_COMMIT

# Пересобрать
docker compose -f $COMPOSE_FILE up -d --build

# Восстановить базу (если нужно)
LATEST_BACKUP=$(ls -t deploy/backups/pre-deploy-*.sql.gz | head -1)
if [ -n "$LATEST_BACKUP" ]; then
  echo "Доступен бэкап: $LATEST_BACKUP"
  echo "Для восстановления базы:"
  echo "  ./deploy/backups/restore.sh $LATEST_BACKUP"
fi

echo "═══ Откат завершён ═══"
```

### Инициализация сервера

```
# deploy/scripts/init-server.sh
#!/bin/bash
set -e

echo "═══ Инициализация сервера DOD ═══"

# 1. Обновление системы
apt-get update && apt-get upgrade -y

# 2. Установка Docker
curl -fsSL https://get.docker.com | sh
systemctl enable docker
systemctl start docker

# 3. Docker Compose
apt-get install -y docker-compose-plugin

# 4. Создание пользователя
useradd -m -s /bin/bash deploy
usermod -aG docker deploy

# 5. SSH ключи
mkdir -p /home/deploy/.ssh
# Добавить публичный ключ
chmod 700 /home/deploy/.ssh
chmod 600 /home/deploy/.ssh/authorized_keys
chown -R deploy:deploy /home/deploy/.ssh

# 6. Firewall
apt-get install -y ufw
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw enable

# 7. Fail2Ban
apt-get install -y fail2ban
systemctl enable fail2ban

# 8. Swap (если мало RAM)
if [ $(free -g | awk '/Mem:/{print $2}') -lt 4 ]; then
  fallocate -l 2G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

# 9. Директория проекта
mkdir -p /opt/dod
chown deploy:deploy /opt/dod

# 10. Timezone
timedatectl set-timezone UTC

echo "═══ Сервер готов ═══"
echo "Затем:"
echo "  1. git clone <repo> /opt/dod"
echo "  2. cp .env.production /opt/dod/"
echo "  3. cd /opt/dod && docker compose -f docker-compose.prod.yml up -d"
```

### Критерий готовности шага 12.2

```
□ GitHub Actions CI: lint (flake8, black, isort)
□ GitHub Actions CI: тесты (PostgreSQL + Redis services)
□ GitHub Actions CI: coverage ≥ 70%
□ GitHub Actions CI: security (safety, bandit)
□ GitHub Actions CI: build Docker image
□ GitHub Actions Deploy: автодеплой staging
□ GitHub Actions Deploy: автодеплой production (с protection)
□ deploy.sh: полный цикл деплоя
□ rollback.sh: откат к предыдущей версии
□ health-check.sh: проверка после деплоя
□ init-server.sh: инициализация нового сервера
□ Два окружения: staging + production
□ Бэкап перед каждым деплоем
□ Автооткат при неудачном health check
```

---

## ШАГ 12.3 — ТЕСТИРОВАНИЕ

### Задача

```
Покрой проект тестами: unit, integration,
e2e. Настрой test settings. Минимальный
coverage: 70%.
```

### Настройки для тестов

```
# config/settings/test.py

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
```

### Unit тесты (по приложениям)

```
Каждое приложение должно иметь тесты:

apps/accounts/tests/
  test_models.py:
    □ Создание User
    □ Генерация referral_code
    □ Флаги is_email_verified, is_phone_verified
    □ Метод check_password
    □ Уникальность username, email
    □ Метод update_last_login()
    □ 2FA поля (secret, backup_codes)

  test_auth.py:
    □ Регистрация (email + пароль)
    □ Регистрация (дубль email → ошибка)
    □ Логин (верный пароль)
    □ Логин (неверный пароль → ошибка)
    □ Логин (заблокированный → ошибка)
    □ 2FA верификация
    □ 2FA с неверным кодом → ошибка
    □ Сброс пароля (запрос + подтверждение)
    □ Email верификация
    □ OAuth (Google) — мок

  test_views.py:
    □ Страница логина (GET → 200)
    □ Страница регистрации (GET → 200)
    □ Профиль (авторизованный → 200)
    □ Профиль (не авторизованный → redirect)
    □ Редактирование профиля
    □ Настройки уведомлений


apps/wallet/tests/
  test_models.py:
    □ Создание Wallet при создании User
    □ Создание CurrencyBalance
    □ Deposit модель
    □ Withdrawal модель
    □ Transaction модель

  test_wallet_service.py:
    □ Пополнение баланса
    □ Списание баланса
    □ Недостаточно средств → ошибка
    □ Конвертация валют
    □ Заморозка средств (при ставке)
    □ Разморозка средств (отмена ставки)

  test_withdrawals.py:
    □ Создание вывода
    □ Вывод > баланс → ошибка
    □ Минимальная сумма вывода
    □ Автоодобрение (маленькая сумма)
    □ Флаги подозрительности
    □ Отмена вывода

  test_payments.py:
    □ NOWpayments callback (IPN)
    □ RUkassa callback
    □ Невалидная подпись → отказ
    □ Дубль callback → идемпотентность


apps/sports/tests/
  test_models.py:
    □ Sport, League, Event, Market, Outcome модели
    □ Bet модель
    □ BetSlip модель

  test_betting.py:
    □ Создание ставки (одиночная)
    □ Создание ставки (экспресс)
    □ Ставка без баланса → ошибка
    □ Ставка на закрытый рынок → ошибка
    □ Ставка на заблокированное событие → ошибка
    □ Расчёт выигрыша (одиночная)
    □ Расчёт выигрыша (экспресс)
    □ Live коэффициент изменился → предупреждение

  test_settlement.py:
    □ Расчёт ставок (победа)
    □ Расчёт ставок (проигрыш)
    □ Расчёт ставок (возврат)
    □ Начисление выигрыша на баланс
    □ Экспресс: один исход проиграл → весь проиграл


apps/casino/tests/
  test_crash.py:
    □ Генерация crash point (Provably Fair)
    □ Верификация crash point
    □ Ставка + cashout
    □ Ставка + crash (проигрыш)
    □ Cashout до crash → выигрыш

  test_mines.py:
    □ Генерация поля (seed)
    □ Открытие ячейки (безопасная)
    □ Открытие ячейки (мина)
    □ Cashout
    □ Расчёт множителя

  test_dice.py:
    □ Бросок кубика (Provably Fair)
    □ Верификация
    □ Выигрыш / проигрыш

  test_provably_fair.py:
    □ HMAC-SHA256 корректность
    □ Seed rotation
    □ Верификация клиентом


apps/predictions/tests/
  test_markets.py:
    □ Создание маркета
    □ Закрытие маркета по дате
    □ Резолюция маркета (YES/NO)
    □ AMM: расчёт цены
    □ AMM: покупка долей
    □ AMM: продажа долей
    □ Slippage protection
    □ Выплата при резолюции


apps/referral/tests/
  test_referral.py:
    □ Регистрация по реферальной ссылке
    □ Создание Referral записи
    □ Начисление комиссии (GGR)
    □ Negative carryover
    □ Уровни (tier upgrade)
    □ Антифрод: один IP → флаг
    □ Вывод партнёрских на баланс


apps/support/tests/
  test_tickets.py:
    □ Создание тикета
    □ Генерация ticket_number
    □ Отправка сообщения
    □ Назначение оператору
    □ Закрытие тикета
    □ SLA отслеживание

  test_faq.py:
    □ Создание категории и статьи
    □ Поиск по FAQ
    □ Рейтинг полезности


apps/dashboard/tests/
  test_access.py:
    □ Не-админ → 403
    □ Деактивированный → 403
    □ IP не в whitelist → 403
    □ Без 2FA → redirect
    □ С правами → 200

  test_permissions.py:
    □ require_permission декоратор
    □ require_role_level декоратор
    □ Superadmin = все права
    □ Кастомные права (переопределение роли)


apps/miniapp/tests/
  test_initdata.py:
    □ Валидация initData (валидный)
    □ Валидация initData (невалидный hash)
    □ Валидация initData (истёкший)
    □ Валидация initData (без user)

  test_auth.py:
    □ Автосоздание пользователя
    □ Привязка к существующему
    □ Middleware авторизация

  test_bot.py:
    □ Webhook принимает updates
    □ /start обработка
    □ /balance ответ
    □ Inline query
    □ Deeplink парсинг
```

### Integration тесты

```
tests/integration/

  test_user_journey.py:
    """
    Полный путь пользователя:
    1. Регистрация
    2. Верификация email
    3. Настройка 2FA
    4. Пополнение баланса (mock payment)
    5. Ставка на спорт
    6. Расчёт ставки
    7. Проверка баланса
    8. Вывод средств
    """

  test_casino_flow.py:
    """
    1. Логин
    2. Пополнение
    3. Игра в Crash (WebSocket)
    4. Cashout
    5. Проверка баланса
    """

  test_prediction_flow.py:
    """
    1. Логин
    2. Покупка долей маркета
    3. Продажа долей
    4. Резолюция маркета (админ)
    5. Выплата
    """

  test_referral_flow.py:
    """
    1. Партнёр регистрируется
    2. Реферал регистрируется по ссылке
    3. Реферал делает депозит
    4. Реферал делает ставки
    5. GGR рассчитывается
    6. Комиссия начисляется
    7. Партнёр выводит комиссию
    """

  test_telegram_flow.py:
    """
    1. /start с deeplink
    2. Открытие Mini App (mock initData)
    3. Авторизация через initData
    4. Просмотр баланса
    5. Размещение ставки
    """
```

### Fixtures для тестов

```
# conftest.py (pytest) или setUp (unittest)

Фикстуры:
  user_factory:
    Создаёт User с уникальными данными
    Опции: verified, with_2fa, with_wallet, with_balance

  event_factory:
    Создаёт Sport → League → Event → Market → Outcome
    Опции: live, finished, with_results

  market_factory:
    Создаёт PredictionMarket с AMM пулом
    Опции: with_positions, resolved

  admin_factory:
    Создаёт User + AdminProfile + AdminRole
    Опции: superadmin, moderator, support

  telegram_user_factory:
    Создаёт TelegramUser + mock initData
```

### Критерий готовности шага 12.3

```
□ config/settings/test.py настроен
□ Unit тесты: accounts (≥15 тестов)
□ Unit тесты: wallet (≥15 тестов)
□ Unit тесты: sports (≥15 тестов)
□ Unit тесты: casino (≥12 тестов)
□ Unit тесты: predictions (≥10 тестов)
□ Unit тесты: referral (≥8 тестов)
□ Unit тесты: support (≥8 тестов)
□ Unit тесты: dashboard (≥8 тестов)
□ Unit тесты: miniapp (≥10 тестов)
□ Integration тесты: user journey
□ Integration тесты: casino flow
□ Integration тесты: prediction flow
□ Integration тесты: referral flow
□ Integration тесты: telegram flow
□ Fixtures / Factories для тестов
□ Coverage ≥ 70%
□ Все тесты проходят в CI
□ python manage.py test --parallel работает
```

---

## ШАГ 12.4 — МОНИТОРИНГ + БЭКАПЫ

### Задача

```
Настрой мониторинг (Prometheus + Grafana),
алерты, бэкапы базы данных, план
восстановления (disaster recovery).
```

### Prometheus + Grafana (docker-compose)

```
# docker-compose.monitoring.yml (расширение prod)

services:
  # ── Prometheus ──────────────────
  prometheus:
    image: prom/prometheus:v2.50.0
    restart: always
    volumes:
      - ./deploy/monitoring/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    ports:
      - "127.0.0.1:9090:9090"
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.retention.time=30d'
      - '--storage.tsdb.retention.size=10GB'

  # ── Grafana ─────────────────────
  grafana:
    image: grafana/grafana:10.3.0
    restart: always
    volumes:
      - grafana_data:/var/lib/grafana
      - ./deploy/monitoring/grafana/provisioning:/etc/grafana/provisioning
    environment:
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_PASSWORD}
      GF_SERVER_ROOT_URL: https://yourdomain.com/grafana/
      GF_SERVER_SERVE_FROM_SUB_PATH: 'true'
    ports:
      - "127.0.0.1:3000:3000"

  # ── Node Exporter ───────────────
  node_exporter:
    image: prom/node-exporter:v1.7.0
    restart: always
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /:/rootfs:ro
    command:
      - '--path.procfs=/host/proc'
      - '--path.sysfs=/host/sys'
      - '--path.rootfs=/rootfs'

  # ── PostgreSQL Exporter ─────────
  postgres_exporter:
    image: prometheuscommunity/postgres-exporter:v0.15.0
    restart: always
    environment:
      DATA_SOURCE_NAME: "postgresql://${DB_USER}:${DB_PASSWORD}@db:5432/${DB_NAME}?sslmode=disable"

  # ── Redis Exporter ──────────────
  redis_exporter:
    image: oliver006/redis_exporter:v1.56.0
    restart: always
    environment:
      REDIS_ADDR: redis://redis:6379
      REDIS_PASSWORD: ${REDIS_PASSWORD}

volumes:
  prometheus_data:
  grafana_data:
```

### Prometheus конфиг

```
# deploy/monitoring/prometheus/prometheus.yml

global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - 'alerts.yml'

scrape_configs:
  - job_name: 'django'
    metrics_path: '/metrics'
    static_configs:
      - targets: ['web:8000']

  - job_name: 'node'
    static_configs:
      - targets: ['node_exporter:9100']

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres_exporter:9187']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis_exporter:9121']

  - job_name: 'celery'
    static_configs:
      - targets: ['celery_worker:9991']
```

### Django Prometheus метрики

```
# requirements.txt (добавить)
django-prometheus

# config/settings/base.py
INSTALLED_APPS += ['django_prometheus']

MIDDLEWARE = [
    'django_prometheus.middleware.PrometheusBeforeMiddleware',
    ...
    'django_prometheus.middleware.PrometheusAfterMiddleware',
]

# config/urls.py
urlpatterns += [
    path('', include('django_prometheus.urls')),
]

Кастомные метрики (apps/core/metrics.py):

  from prometheus_client import Counter, Histogram, Gauge

  # Бизнес-метрики
  bets_placed_total = Counter(
      'dod_bets_placed_total',
      'Всего ставок',
      ['type', 'sport']
  )

  bets_amount_total = Counter(
      'dod_bets_amount_total',
      'Сумма ставок (USD)',
      ['type']
  )

  deposits_total = Counter(
      'dod_deposits_total',
      'Всего депозитов',
      ['method', 'currency']
  )

  withdrawals_total = Counter(
      'dod_withdrawals_total',
      'Всего выводов',
      ['method', 'status']
  )

  active_users_gauge = Gauge(
      'dod_active_users',
      'Активные пользователи сейчас'
  )

  websocket_connections = Gauge(
      'dod_websocket_connections',
      'WebSocket соединения',
      ['type']  # chat, casino, notifications
  )

  casino_rounds_total = Counter(
      'dod_casino_rounds_total',
      'Всего раундов казино',
      ['game']
  )

  ggr_total = Counter(
      'dod_ggr_total',
      'Gross Gaming Revenue (USD)'
  )

  prediction_trades_total = Counter(
      'dod_prediction_trades_total',
      'Сделки в маркетах',
      ['action']  # buy, sell
  )
```

### Алерты

```
# deploy/monitoring/prometheus/alerts.yml

groups:
  - name: dod_critical
    rules:
      - alert: HighErrorRate
        expr: rate(django_http_responses_total_by_status_total{status=~"5.."}[5m]) > 0.1
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Высокий % ошибок 5xx"

      - alert: DatabaseDown
        expr: pg_up == 0
        for: 30s
        labels:
          severity: critical
        annotations:
          summary: "PostgreSQL недоступен"

      - alert: RedisDown
        expr: redis_up == 0
        for: 30s
        labels:
          severity: critical
        annotations:
          summary: "Redis недоступен"

      - alert: HighMemoryUsage
        expr: (node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes > 0.9
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Память > 90%"

      - alert: DiskSpaceLow
        expr: node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"} < 0.1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Диск заканчивается (< 10%)"

      - alert: HighResponseTime
        expr: histogram_quantile(0.95, rate(django_http_requests_latency_seconds_by_view_method_bucket[5m])) > 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "P95 время ответа > 2 секунд"

      - alert: CeleryQueueBacklog
        expr: celery_queue_length > 100
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Очередь Celery > 100 задач"

      - alert: WithdrawalsPending
        expr: dod_withdrawals_total{status="pending"} > 20
        for: 30m
        labels:
          severity: warning
        annotations:
          summary: "> 20 выводов в ожидании 30+ мин"
```

### Бэкапы

```
# deploy/backups/backup.sh
#!/bin/bash
set -e

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/opt/dod/deploy/backups/data"
DB_NAME=${DB_NAME:-dod_production}
RETENTION_DAYS=${BACKUP_RETENTION_DAYS:-30}
TAG=${1:-scheduled}

mkdir -p $BACKUP_DIR

echo "═══ Бэкап DOD ($TAG) ═══"
echo "Время: $TIMESTAMP"

# 1. Database dump
echo "1. Бэкап PostgreSQL..."
docker compose -f /opt/dod/docker-compose.prod.yml \
  exec -T db pg_dump -U $DB_USER $DB_NAME \
  --format=custom --compress=9 \
  > "$BACKUP_DIR/db_${TAG}_${TIMESTAMP}.dump"

DB_SIZE=$(du -sh "$BACKUP_DIR/db_${TAG}_${TIMESTAMP}.dump" | cut -f1)
echo "   Размер: $DB_SIZE"

# 2. Media files
echo "2. Бэкап медиа..."
tar czf "$BACKUP_DIR/media_${TAG}_${TIMESTAMP}.tar.gz" \
  -C /opt/dod media/ 2>/dev/null || true

# 3. Env files
echo "3. Бэкап конфигов..."
cp /opt/dod/.env.production \
  "$BACKUP_DIR/env_${TAG}_${TIMESTAMP}.env"

# 4. Upload to S3 (если настроен)
if [ -n "$BACKUP_S3_BUCKET" ]; then
  echo "4. Загрузка в S3..."
  aws s3 cp "$BACKUP_DIR/db_${TAG}_${TIMESTAMP}.dump" \
    "s3://$BACKUP_S3_BUCKET/db/" \
    --endpoint-url "$BACKUP_S3_ENDPOINT"
  aws s3 cp "$BACKUP_DIR/media_${TAG}_${TIMESTAMP}.tar.gz" \
    "s3://$BACKUP_S3_BUCKET/media/" \
    --endpoint-url "$BACKUP_S3_ENDPOINT"
fi

# 5. Cleanup старых бэкапов
echo "5. Удаление старых бэкапов (> ${RETENTION_DAYS} дней)..."
find $BACKUP_DIR -type f -mtime +$RETENTION_DAYS -delete

echo "═══ Бэкап завершён ═══"


# deploy/backups/restore.sh
#!/bin/bash
set -e

BACKUP_FILE=$1
if [ -z "$BACKUP_FILE" ]; then
  echo "Использование: ./restore.sh <backup_file.dump>"
  echo "Доступные бэкапы:"
  ls -la /opt/dod/deploy/backups/data/db_*.dump
  exit 1
fi

echo "═══ ВОССТАНОВЛЕНИЕ DOD ═══"
echo "Файл: $BACKUP_FILE"
echo "ВНИМАНИЕ: Текущие данные будут перезаписаны!"
read -p "Продолжить? (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
  exit 0
fi

# 1. Остановить приложение
echo "1. Остановка приложения..."
docker compose -f /opt/dod/docker-compose.prod.yml \
  stop web channels celery_worker celery_beat

# 2. Восстановить базу
echo "2. Восстановление базы..."
docker compose -f /opt/dod/docker-compose.prod.yml \
  exec -T db pg_restore -U $DB_USER \
  --clean --if-exists -d $DB_NAME < "$BACKUP_FILE"

# 3. Запустить приложение
echo "3. Запуск приложения..."
docker compose -f /opt/dod/docker-compose.prod.yml \
  up -d

echo "═══ Восстановление завершено ═══"


# Cron задача (каждые 6 часов)
# deploy/backups/cron/backup-cron
0 */6 * * * /opt/dod/deploy/backups/backup.sh scheduled >> /var/log/dod-backup.log 2>&1
```

### Disaster Recovery план

```
Уровни восстановления:

  RTO (Recovery Time Objective): 30 минут
  RPO (Recovery Point Objective): 6 часов

Процедура:

  1. ИНЦИДЕНТ ОБНАРУЖЕН (алерт / ручная проверка)

  2. ДИАГНОСТИКА (5 мин):
     - Проверить health check
     - Проверить логи (docker compose logs)
     - Определить масштаб проблемы

  3. ВОССТАНОВЛЕНИЕ по типу:

     a) Приложение упало:
        docker compose -f docker-compose.prod.yml restart web
        → Проверить health check

     b) База повреждена:
        ./deploy/backups/restore.sh <latest_backup>
        → Запустить миграции
        → Проверить данные

     c) Сервер умер:
        1. Поднять новый VPS
        2. ./deploy/scripts/init-server.sh
        3. Клонировать repo
        4. Восстановить .env
        5. Восстановить бэкап DB из S3
        6. docker compose up -d
        7. Обновить DNS
        8. Обновить SSL

     d) Redis потерян:
        docker compose restart redis
        → Кэш пересоздастся автоматически
        → Активные WebSocket сессии потеряются

  4. ПРОВЕРКА (5 мин):
     - Health check OK
     - Тестовая ставка
     - Тестовый логин
     - Проверить WebSocket (казино)

  5. POST-MORTEM:
     - Документировать инцидент
     - Определить причину
     - Внести изменения для предотвращения
```

### Критерий готовности шага 12.4

```
□ Prometheus: сбор метрик (Django, PG, Redis, Node)
□ Grafana: дашборды (Django, PostgreSQL, Redis, Celery)
□ Django Prometheus: middleware + кастомные метрики
□ Алерты: 5xx, DB down, Redis down, RAM, диск, latency
□ Алерты: Celery очередь, pending withdrawals
□ Бэкапы: pg_dump каждые 6 часов
□ Бэкапы: media files
□ Бэкапы: upload в S3
□ Бэкапы: retention 30 дней
□ restore.sh: восстановление из бэкапа
□ Disaster Recovery: план документирован
□ Cron задача бэкапов настроена
```

---

## ШАГ 12.5 — SECURITY AUDIT + НАГРУЗОЧНОЕ ТЕСТИРОВАНИЕ

### Задача

```
Проведи security audit всей платформы,
нагрузочное тестирование, оптимизацию
производительности.
```

### Security Checklist

```
АУТЕНТИФИКАЦИЯ И СЕССИИ:
  □ Пароли хешируются (bcrypt/argon2)
  □ 2FA обязательна для админов
  □ Сессии: httponly, secure, samesite
  □ CSRF protection на всех формах
  □ Rate limiting на логин (5 попыток → блок)
  □ Rate limiting на API (30 req/s)
  □ JWT/сессии: нет чувствительных данных
  □ Logout инвалидирует сессию

ДАННЫЕ:
  □ SQL injection: ORM everywhere (нет raw SQL)
  □ XSS: все шаблоны автоэкранируют
  □ Sensitive data не логируется (пароли, токены)
  □ .env НЕ в Git (.gitignore)
  □ Personaly Identifiable Information (PII) шифрование
  □ Бэкапы шифруются (gpg)
  □ Media uploads: валидация типа + размера
  □ Нет directory listing

СЕТЕВАЯ БЕЗОПАСНОСТЬ:
  □ HTTPS only (HSTS preload)
  □ TLS 1.2+ only
  □ Security headers (CSP, X-Frame, etc.)
  □ CORS ограничен (только нужные домены)
  □ Webhook: IP whitelist (Telegram, payments)
  □ Admin panel: IP whitelist (опционально)
  □ Firewall: только 22, 80, 443
  □ Fail2Ban: SSH brute force protection

БИЗНЕС-ЛОГИКА:
  □ Ставки: нельзя поставить > баланса
  □ Ставки: нельзя на закрытый рынок
  □ Вывод: нельзя > баланса
  □ Вывод: подозрительные → ручная проверка
  □ Casino: Provably Fair верифицируем
  □ Casino: RNG не манипулируем клиентом
  □ Payments: идемпотентность callbacks
  □ Payments: подпись IPN проверяется
  □ Referral: антифрод (один IP, мульти-аккаунты)
  □ initData: HMAC-SHA256 валидация
  □ initData: не старше 1 часа

ИНФРАСТРУКТУРА:
  □ Docker: non-root user
  □ Docker: minimal base images
  □ Docker: no secrets в образе
  □ PostgreSQL: сильный пароль
  □ Redis: requirepass
  □ SSH: key-only (пароль отключён)
  □ Порты DB/Redis: только localhost
  □ Мониторинг: не публичный
  □ Бэкапы: вне основного сервера (S3)

DEPENDENCIES:
  □ pip install safety → 0 vulnerabilities
  □ bandit → no high severity
  □ requirements.txt: версии закреплены (==)
  □ Нет deprecated пакетов
```

### Нагрузочное тестирование (Locust)

```
# requirements-dev.txt (добавить)
locust

# tests/load/locustfile.py

from locust import HttpUser, task, between

class DODUser(HttpUser):
    """
    Нагрузочное тестирование DOD.
    Имитация реальных пользователей.
    """
    wait_time = between(1, 5)

    def on_start(self):
        """Логин перед тестами."""
        self.client.post('/accounts/login/', {
            'email': f'loadtest_{self.id}@test.com',
            'password': 'TestPassword123!',
        })

    @task(10)
    def view_home(self):
        self.client.get('/')

    @task(8)
    def view_sports(self):
        self.client.get('/sports/')

    @task(5)
    def view_match(self):
        self.client.get('/sports/event/<test_event_id>/')

    @task(3)
    def place_bet(self):
        self.client.post('/sports/bet/', json={
            'outcome_id': '<test_outcome_id>',
            'amount': '10.00',
        })

    @task(7)
    def view_casino(self):
        self.client.get('/casino/')

    @task(5)
    def view_predictions(self):
        self.client.get('/predictions/')

    @task(4)
    def view_wallet(self):
        self.client.get('/wallet/')

    @task(2)
    def view_profile(self):
        self.client.get('/profile/')


Запуск:
  locust -f tests/load/locustfile.py \
    --host=https://staging.yourdomain.com \
    --users=100 --spawn-rate=10 --run-time=10m

Целевые показатели:
  □ 100 одновременных пользователей
  □ P95 < 500ms для страниц
  □ P95 < 200ms для API
  □ 0 ошибок при нормальной нагрузке
  □ Graceful degradation при 500+ пользователях
  □ WebSocket: 50 одновременных в Crash
```

### Оптимизация производительности

```
БАЗА ДАННЫХ:
  □ Индексы: все поля в WHERE / ORDER BY
  □ select_related / prefetch_related везде
  □ N+1 запросов нет (django-debug-toolbar)
  □ Пагинация: все списки
  □ CONN_MAX_AGE = 600 (connection pooling)

КЭШИРОВАНИЕ:
  □ Redis кэш для частых запросов
  □ Баланс: кэш 10 сек
  □ Коэффициенты: кэш 30 сек
  □ FAQ: кэш 5 мин
  □ Аналитика: кэш 1 час
  □ Template fragments: кэш

СТАТИКА:
  □ Gzip включён (Nginx)
  □ Cache-Control: 30 дней для static
  □ WhiteNoise для collectstatic (опц.)
  □ CDN для статики (опционально)

DJANGO:
  □ DEBUG = False
  □ Gunicorn: workers = CPU * 2 + 1
  □ Gunicorn: threads = 2
  □ CONN_HEALTH_CHECKS = True

CELERY:
  □ Raздленение очередей (payments, notifications)
  □ max-tasks-per-child = 1000 (memory leaks)
  □ Timeout на задачи
```

### Критерий готовности шага 12.5

```
□ Security checklist: всё отмечено
□ bandit: 0 high severity
□ safety: 0 known vulnerabilities
□ Нагрузочный тест: 100 пользователей, P95 < 500ms
□ WebSocket нагрузка: 50 соединений
□ N+1 запросов нет
□ Все списки с пагинацией
□ Redis кэш для частых запросов
□ Индексы оптимизированы
□ Gzip включён
□ Static: long cache headers
□ Gunicorn: оптимальное число workers
```

---

## ШАГ 12.6 — ДОКУМЕНТАЦИЯ + ЗАПУСК

### Задача

```
Напиши полную документацию проекта,
подготовь к запуску, создай runbook
для команды.
```

### README.md

```
# README.md

## DOD Platform

Платформа для ставок на спорт, казино
и рынков предсказаний.

### Стек
  - Django 5.1 + Django Channels
  - PostgreSQL 16
  - Redis 7
  - Celery
  - HTMX + TailwindCSS
  - Docker + Docker Compose
  - Nginx + Let's Encrypt
  - Telegram Mini App

### Быстрый старт (development)
  git clone <repo>
  cp .env.example .env
  docker compose up -d
  docker compose exec web python manage.py migrate
  docker compose exec web python manage.py loaddata initial_data
  docker compose exec web python manage.py createsuperuser
  Открыть: http://localhost:8000

### Production деплой
  Смотри: docs/deployment.md

### Структура проекта
  apps/
    accounts/    — Авторизация, профиль, KYC
    wallet/      — Кошелёк, платежи
    sports/      — Ставки на спорт
    casino/      — Казино (6 игр)
    predictions/ — Маркеты предсказаний
    referral/    — Партнёрская программа
    support/     — Чат поддержки
    dashboard/   — Админ-панель
    miniapp/     — Telegram Mini App
    core/        — Общие утилиты

### Документация
  docs/
    deployment.md     — Инструкция по деплою
    api.md            — API документация
    architecture.md   — Архитектура
    runbook.md        — Runbook для команды
    security.md       — Политика безопасности
    backup-restore.md — Бэкапы и восстановление
```

### Документация

```
docs/
├── deployment.md
│   Содержание:
│     1. Требования к серверу
│        - Ubuntu 22.04+
│        - 4 CPU, 8GB RAM (минимум)
│        - 100GB SSD
│        - Домен с DNS
│     2. Установка Docker
│     3. Клонирование и настройка .env
│     4. SSL сертификат (Certbot)
│     5. Запуск docker compose
│     6. Первоначальная настройка
│        - Создание суперадмина
│        - Загрузка fixtures
│        - Настройка Telegram бота
│     7. Обновление платформы
│     8. Откат

├── api.md
│   Содержание:
│     Все API endpoints:
│     - POST /accounts/login/
│     - POST /accounts/register/
│     - GET  /wallet/balance/
│     - POST /wallet/deposit/
│     - POST /sports/bet/
│     - GET  /predictions/markets/
│     - POST /predictions/trade/
│     - POST /tg/bot/webhook/
│     - GET  /health/
│     Формат: URL, метод, параметры, ответ, ошибки

├── architecture.md
│   Содержание:
│     1. Обзор архитектуры (модульный монолит)
│     2. Диаграмма компонентов
│     3. Поток данных (авторизация, ставки, платежи)
│     4. База данных (ER-диаграмма)
│     5. WebSocket архитектура
│     6. Celery задачи
│     7. Telegram интеграция
│     8. Масштабирование

├── runbook.md
│   Содержание:
│     ЕЖЕДНЕВНЫЕ ЗАДАЧИ:
│       - Проверить Grafana дашборд
│       - Проверить очередь выводов
│       - Проверить логи ошибок

│     ЕЖЕНЕДЕЛЬНЫЕ ЗАДАЧИ:
│       - Проверить размер БД
│       - Проверить размер логов
│       - Обновить зависимости (pip)
│       - Проверить бэкапы

│     ЕЖЕМЕСЯЧНЫЕ ЗАДАЧИ:
│       - Обновить SSL (автоматически)
│       - Обновить Docker images
│       - Ротация секретов
│       - Security scan

│     ЧАСТЫЕ ПРОБЛЕМЫ:
│       Проблема: 502 Bad Gateway
│       Решение: docker compose restart web

│       Проблема: Медленные запросы
│       Решение: EXPLAIN ANALYZE, добавить индекс

│       Проблема: Redis OOM
│       Решение: redis-cli FLUSHDB (cache only)

│       Проблема: Celery зависла
│       Решение: docker compose restart celery_worker

│       Проблема: Диск заполнился
│       Решение: docker system prune, старые логи

├── security.md
│   Содержание:
│     1. Политика паролей
│     2. 2FA (обязательная для админов)
│     3. IP whitelist
│     4. HTTPS / HSTS
│     5. Rate limiting
│     6. Обработка инцидентов
│     7. Ротация секретов
│     8. Аудит доступа

└── backup-restore.md
    Содержание:
      1. Расписание бэкапов (каждые 6 часов)
      2. Хранение (локально + S3)
      3. Retention (30 дней)
      4. Процедура восстановления
      5. Тестирование бэкапов
      6. Disaster Recovery план
```

### Чеклист запуска (Launch)

```
ПЕРЕД ЗАПУСКОМ:

  Инфраструктура:
    □ Сервер арендован и настроен
    □ Домен куплен и DNS настроен
    □ SSL сертификат получен
    □ Docker + Docker Compose установлены
    □ Firewall настроен (22, 80, 443)
    □ Fail2Ban активен
    □ SSH ключи (пароль отключён)

  Приложение:
    □ .env.production заполнен
    □ SECRET_KEY сгенерирован
    □ DEBUG = False
    □ ALLOWED_HOSTS настроен
    □ Все миграции применены
    □ Fixtures загружены
    □ collectstatic выполнен
    □ Суперадмин создан

  Интеграции:
    □ SMTP настроен (email работает)
    □ NOWpayments API ключи (production)
    □ RUkassa ключи (production)
    □ Google OAuth настроен
    □ Telegram бот: webhook установлен
    □ Telegram Mini App: URL настроен
    □ Sentry DSN настроен

  Мониторинг:
    □ Prometheus собирает метрики
    □ Grafana дашборды настроены
    □ Алерты настроены (Telegram / email)
    □ Health check работает

  Бэкапы:
    □ Cron задача настроена (каждые 6 часов)
    □ S3 хранилище настроено
    □ Тестовый restore прошёл

  Безопасность:
    □ Security audit пройден
    □ bandit: 0 high severity
    □ safety: 0 vulnerabilities
    □ SSL Labs: A+ рейтинг
    □ Security headers: все на месте

  Тестирование:
    □ Все юнит-тесты проходят
    □ Integration тесты проходят
    □ Нагрузочный тест: OK
    □ Тестовый депозит (staging)
    □ Тестовая ставка (staging)
    □ Тестовый вывод (staging)
    □ Telegram Mini App: тест (staging)

  Документация:
    □ README.md написан
    □ deployment.md написан
    □ runbook.md написан
    □ security.md написан
    □ api.md написан

ЗАПУСК:
  □ docker compose -f docker-compose.prod.yml up -d
  □ Health check: 200 OK
  □ Тестовый логин
  □ Тестовый депозит
  □ Мониторинг: метрики приходят
  □ Бот Telegram: /start работает
  □ Mini App: открывается из Telegram
```

### Критерий готовности шага 12.6

```
□ README.md написан
□ docs/deployment.md
□ docs/api.md
□ docs/architecture.md
□ docs/runbook.md
□ docs/security.md
□ docs/backup-restore.md
□ Чеклист запуска: все пункты выполнены
□ Staging: полный тест прошёл
□ Production: запуск выполнен
□ Health check: 200 OK
□ Мониторинг: метрики видны
□ Бэкапы: первый бэкап создан
□ Telegram: бот и Mini App работают
```

---

## 📊 ОБЩИЙ ЧЕКЛИСТ ЭТАПА 12

```
DOCKER:
  □ Dockerfile (multi-stage, non-root, healthcheck)
  □ docker-compose.prod.yml (все сервисы)
  □ PostgreSQL + Redis (volumes, healthcheck)
  □ Gunicorn + Daphne
  □ Celery Worker + Beat
  □ Nginx (HTTPS, WebSocket, rate limiting)
  □ Certbot (autorenewal)

CI/CD:
  □ GitHub Actions: lint + test + security + build
  □ Auto-deploy: staging (develop/staging) + production (main)
  □ Coverage ≥ 70%
  □ deploy.sh + rollback.sh
  □ Health check после деплоя
  □ Auto-rollback при ошибке

ТЕСТИРОВАНИЕ:
  □ Unit тесты: все приложения (≥100 тестов)
  □ Integration тесты: 5 сценариев
  □ Нагрузочный тест: 100 пользователей
  □ Security audit: пройден
  □ bandit + safety: 0 critical

МОНИТОРИНГ:
  □ Prometheus + Grafana
  □ Дашборды: Django, PostgreSQL, Redis, Celery
  □ Кастомные метрики (ставки, депозиты, GGR)
  □ Алерты: 5xx, DB down, RAM, диск, latency

БЭКАПЫ:
  □ PostgreSQL dump каждые 6 часов
  □ Media backup
  □ S3 upload
  □ Retention 30 дней
  □ restore.sh протестирован
  □ Disaster Recovery план

БЕЗОПАСНОСТЬ:
  □ HTTPS + HSTS + TLS 1.2+
  □ Security headers (CSP, X-Frame, etc.)
  □ Rate limiting
  □ Firewall + Fail2Ban
  □ Non-root Docker
  □ Secrets не в git

ОПТИМИЗАЦИЯ:
  □ N+1 запросов нет
  □ Redis кэш для частых данных
  □ Gzip + static caching
  □ Gunicorn: оптимальные workers
  □ DB: connection pooling

ДОКУМЕНТАЦИЯ:
  □ README.md
  □ deployment.md
  □ api.md
  □ architecture.md
  □ runbook.md
  □ security.md
  □ backup-restore.md

ЗАПУСК:
  □ Staging: полный тест
  □ Production: деплой
  □ Health check: OK
  □ Мониторинг: работает
  □ Бэкапы: работают
  □ Telegram: бот + Mini App
```

---

```
╔══════════════════════════════════════════════════════╗
║                                                      ║
║   🎉 ПРОЕКТ DOD — ВСЕ 12 ЭТАПОВ ЗАВЕРШЕНЫ         ║
║                                                      ║
║   Этап 1:  Фундамент + Авторизация                 ║
║   Этап 2:  Профиль + KYC                           ║
║   Этап 3:  Кошелёк                                  ║
║   Этап 4:  Платежи                                  ║
║   Этап 5:  Ставки на спорт                          ║
║   Этап 6:  Казино                                   ║
║   Этап 7:  Prediction Market                        ║
║   Этап 8:  Партнёрская программа                    ║
║   Этап 9:  Поддержка + Уведомления                  ║
║   Этап 10: Админ-панель                             ║
║   Этап 11: Telegram Mini App                        ║
║   Этап 12: Деплой + Тестирование + Запуск           ║
║                                                      ║
║   Платформа готова к production! 🚀                 ║
║                                                      ║
╚══════════════════════════════════════════════════════╝
```
