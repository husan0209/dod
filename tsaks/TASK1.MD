

# 📋 ТЗ ПРОЕКТА DOD — ЭТАП 1

# ФУНДАМЕНТ + ПОЛНАЯ СИСТЕМА АВТОРИЗАЦИИ

```
╔══════════════════════════════════════════════════════╗
║                                                      ║
║   ПРОЕКТ:    DOD                                    ║
║   ЭТАП:      1 из 12                                ║
║   НАЗВАНИЕ:  Фундамент + Авторизация               ║
║   ЦЕЛЬ:      Пользователь может зарегистрироваться  ║
║              любым способом, войти, настроить 2FA,  ║
║              восстановить аккаунт, видеть историю   ║
║              входов и управлять сессиями            ║
║                                                      ║
╚══════════════════════════════════════════════════════╝
```

---

## 📌 КОНТЕКСТ ДЛЯ ИИ-АГЕНТА

```
Ты начинаешь разработку проекта DOD с нуля.
DOD — это гемблинг-платформа (букмекер + казино + prediction market).

Технический стек (МЕНЯТЬ НЕЛЬЗЯ):
- Python 3.12 + Django 5.1
- PostgreSQL 16
- Redis 7
- TailwindCSS (CDN на старте)
- HTMX (CDN на старте)
- Docker Compose
- Django Channels (для WebSocket — позже)

Архитектура: модульный монолит.
Все модули — это Django apps внутри папки apps/.
Языки интерфейса: русский (основной) + английский.
Дизайн: тёмная тема (как Stake.com, 1xBet).

Этот этап включает 6 шагов.
Каждый шаг — это отдельная задача.
Выполняй строго по порядку.
Не пропускай ни одного пункта.
```

---

## ШАГ 1.1 — ИНИЦИАЛИЗАЦИЯ ПРОЕКТА

### Задача

```
Создай Django проект DOD с нуля.
Настрой Docker Compose.
Настрой подключение к PostgreSQL и Redis.
Подготовь структуру папок.
```

### Структура проекта

```
dod/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env
├── .env.example
├── .gitignore
├── manage.py
│
├── config/
│   ├── __init__.py
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py          # Общие настройки
│   │   ├── development.py   # Для разработки
│   │   └── production.py    # Для продакшена
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
│
├── apps/
│   └── __init__.py
│
├── templates/
│   └── (пока пусто)
│
├── static/
│   ├── css/
│   ├── js/
│   └── images/
│
├── media/                    # Загрузки пользователей
│   └── avatars/
│
├── locale/                   # Переводы
│   ├── ru/
│   └── en/
│
└── utils/                    # Общие утилиты
    ├── __init__.py
    └── helpers.py
```

### Файл requirements.txt

```
Обязательные пакеты:

Django==5.1
psycopg2-binary==2.9.9       # PostgreSQL
django-redis==5.4.0           # Redis кэш
channels==4.1.0               # WebSocket (подготовка)
channels-redis==4.2.0         # Redis для channels
python-dotenv==1.0.1          # Переменные окружения
Pillow==10.4.0                # Работа с изображениями
django-allauth==65.0.0        # OAuth (Google, Telegram)
django-otp==1.5.0             # 2FA TOTP
qrcode==7.4.2                 # QR коды для 2FA
phonenumbers==8.13.0          # Валидация телефонов
django-phonenumber-field==8.0.0  # Поле телефона
django-countries==7.6.1       # Список стран
django-timezone-field==7.0    # Часовые пояса
celery==5.4.0                 # Фоновые задачи
redis==5.0.0                  # Redis клиент
requests==2.32.0              # HTTP запросы
django-cors-headers==4.4.0    # CORS
django-ratelimit==4.1.0       # Rate limiting
user-agents==2.2.0            # Определение устройства
geoip2==4.8.0                 # Определение страны по IP
cryptography==43.0.0          # Шифрование
django-import-export==4.1.0   # Экспорт CSV/Excel в админке
```

### Файл docker-compose.yml

```
Четыре сервиса:

1. app (Django):
   - Собирается из Dockerfile
   - Порт 8000
   - Зависит от db, redis, celery
   - Монтирует текущую папку для hot reload
   - Переменные из .env
   - Команда: python manage.py runserver 0.0.0.0:8000

2. db (PostgreSQL 16 Alpine):
   - Порт 5432
   - Volume pgdata для персистентности
   - Переменные: POSTGRES_DB=dod, POSTGRES_USER, POSTGRES_PASSWORD

3. redis (Redis 7 Alpine):
   - Порт 6379
   - Конфиг: maxmemory 256mb, maxmemory-policy allkeys-lru

4. celery (worker для фоновых задач):
   - Тот же образ что app
   - Команда: celery -A config worker -l info
   - Зависит от redis
   - Используется для:
     отправки email
     отправки SMS
     проверки подозрительных действий
```

### Файл .env.example

```
# Django
SECRET_KEY=your-secret-key-here-change-in-production
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DJANGO_SETTINGS_MODULE=config.settings.development

# Database
DB_NAME=dod
DB_USER=dod_user
DB_PASSWORD=dod_password
DB_HOST=db
DB_PORT=5432

# Redis
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1

# Email (для подтверждения и 2FA)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=DOD <noreply@dod.com>

# SMS провайдер
SMS_API_KEY=your-sms-api-key
SMS_SENDER=DOD

# Google OAuth
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# Telegram Bot
TELEGRAM_BOT_TOKEN=your-telegram-bot-token

# GeoIP
GEOIP_PATH=/app/geoip/

# Безопасность
SESSION_COOKIE_AGE=1800          # 30 минут
RATE_LIMIT_LOGIN=5/15m           # 5 попыток за 15 минут
RATE_LIMIT_REGISTER=3/1h         # 3 регистрации за час
RATE_LIMIT_SMS=3/10m             # 3 SMS за 10 минут
```

### Настройки config/settings/base.py

```
Обязательные настройки:

SECRET_KEY:          из .env
DEBUG:               из .env
ALLOWED_HOSTS:       из .env (список)

INSTALLED_APPS:
  # Django стандартные
  django.contrib.admin
  django.contrib.auth
  django.contrib.contenttypes
  django.contrib.sessions
  django.contrib.messages
  django.contrib.staticfiles
  django.contrib.sites         # Для allauth

  # Сторонние
  allauth
  allauth.account
  allauth.socialaccount
  allauth.socialaccount.providers.google
  django_otp
  django_otp.plugins.otp_totp
  corsheaders
  django_celery_results
  import_export
  phonenumber_field

  # Наши приложения
  apps.accounts

MIDDLEWARE:
  SecurityMiddleware
  SessionMiddleware
  CorsMiddleware
  CommonMiddleware
  CsrfViewMiddleware
  AuthenticationMiddleware
  OTPMiddleware              # 2FA
  MessageMiddleware
  XFrameOptionsMiddleware
  # Кастомные:
  apps.accounts.middleware.LastActivityMiddleware
  apps.accounts.middleware.DeviceTrackingMiddleware

DATABASES:
  PostgreSQL из .env

CACHES:
  Redis из .env

AUTH_USER_MODEL = 'accounts.User'

AUTHENTICATION_BACKENDS:
  django.contrib.auth.backends.ModelBackend
  allauth.account.auth_backends.AuthenticationBackend

# Allauth настройки
ACCOUNT_AUTHENTICATION_METHOD = 'email'
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = 'mandatory'
ACCOUNT_LOGIN_ATTEMPTS_LIMIT = 5
ACCOUNT_LOGIN_ATTEMPTS_TIMEOUT = 900  # 15 мин
SOCIALACCOUNT_AUTO_SIGNUP = True

# Сессии
SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'
SESSION_CACHE_ALIAS = 'default'
SESSION_COOKIE_AGE = 1800  # 30 минут
SESSION_SAVE_EVERY_REQUEST = True  # Обновлять при активности

# Языки
LANGUAGE_CODE = 'ru'
LANGUAGES = [('ru', 'Русский'), ('en', 'English')]
USE_I18N = True
USE_L10N = True
LOCALE_PATHS = [BASE_DIR / 'locale']

TIME_ZONE = 'UTC'
USE_TZ = True

# Файлы
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Celery
CELERY_BROKER_URL = из .env
CELERY_RESULT_BACKEND = 'django-db'
```

### Критерий готовности шага 1.1

```
□ docker compose up запускает все 4 сервиса
□ localhost:8000 открывается без ошибок
□ PostgreSQL подключена (нет ошибок в логах)
□ Redis подключён (нет ошибок в логах)
□ Celery worker запускается
□ Структура папок создана
□ .env файл заполнен
□ settings разделены на base/development/production
□ Все пакеты из requirements установлены
```

---

## ШАГ 1.2 — МОДЕЛЬ ПОЛЬЗОВАТЕЛЯ + СВЯЗАННЫЕ МОДЕЛИ

### Задача

```
Создай приложение accounts с полной моделью User
и всеми связанными моделями для безопасности.
```

### Файлы приложения

```
apps/accounts/
├── __init__.py
├── models.py
├── managers.py
├── admin.py
├── views.py
├── urls.py
├── forms.py
├── signals.py
├── tasks.py              # Celery задачи
├── middleware.py
├── validators.py
├── decorators.py
├── services/
│   ├── __init__.py
│   ├── auth_service.py   # Логика авторизации
│   ├── otp_service.py    # Логика 2FA
│   └── sms_service.py    # Отправка SMS
├── templatetags/
│   ├── __init__.py
│   └── account_tags.py
├── tests/
│   ├── __init__.py
│   ├── test_models.py
│   ├── test_views.py
│   └── test_services.py
├── templates/
│   └── accounts/
│       └── (шаблоны — следующие шаги)
└── migrations/
    └── __init__.py
```

### Модель User (models.py)

```
class User(AbstractUser):

    Поля:
    ─────
    id:
      тип: UUID
      primary key
      генерируется автоматически (uuid4)
      НЕ автоинкремент (безопаснее)

    email:
      тип: EmailField
      уникальный
      обязательный
      индекс для быстрого поиска
      максимум 255 символов

    username:
      тип: CharField
      уникальный
      обязательный
      минимум 3 символа
      максимум 30 символов
      только: буквы (рус/англ), цифры, подчёркивание, точка
      регистронезависимый (User и user — одно и то же)

    phone:
      тип: PhoneNumberField (из django-phonenumber-field)
      уникальный
      необязательный (nullable)
      формат: международный (+7XXXXXXXXXX)
      индекс для быстрого поиска

    password:
      тип: CharField
      хешируется Django (argon2 или bcrypt)
      может быть NULL если зарегался через OAuth
      минимум 8 символов при установке

    first_name:
      тип: CharField
      необязательный
      максимум 50 символов

    last_name:
      тип: CharField
      необязательный
      максимум 50 символов

    avatar:
      тип: ImageField
      путь: avatars/{user_id}/{filename}
      необязательный
      максимум 5 MB
      форматы: jpg, png, webp
      при загрузке → ресайз до 256x256

    date_of_birth:
      тип: DateField
      необязательный (nullable)

    country:
      тип: CountryField (из django-countries)
      необязательный
      по умолчанию определяется из IP при регистрации

    language:
      тип: CharField
      choices: [('ru', 'Русский'), ('en', 'English')]
      по умолчанию: 'ru'

    timezone:
      тип: TimeZoneField
      по умолчанию: 'Europe/Moscow'

    preferred_currency:
      тип: CharField
      максимум 5
      choices: USD, EUR, RUB, UAH, KZT, UZS, BYN,
               BTC, ETH, USDT, TON
      по умолчанию: 'USD'

    balance:
      тип: DecimalField
      max_digits=18
      decimal_places=8 (для крипты нужно 8 знаков)
      default=0
      НЕ может быть отрицательным (валидация)

    is_email_verified:
      тип: BooleanField
      default=False

    is_phone_verified:
      тип: BooleanField
      default=False

    is_2fa_enabled:
      тип: BooleanField
      default=False

    two_fa_method:
      тип: CharField
      choices: [('totp', 'Google Authenticator'),
                ('email', 'Email код')]
      nullable (если 2FA выключена)

    kyc_status:
      тип: CharField
      choices: [('none', 'Не подана'),
                ('pending', 'На проверке'),
                ('approved', 'Одобрена'),
                ('rejected', 'Отклонена')]
      default: 'none'

    trust_level:
      тип: IntegerField
      choices: [(1, 'Новый'), (2, 'Базовый'),
                (3, 'Проверенный'), (4, 'Доверенный'),
                (5, 'VIP')]
      default: 1
      Влияет на лимиты автовывода:
        1 → мин. лимит
        5 → макс. лимит

    is_active:
      тип: BooleanField
      default=True
      False = аккаунт заблокирован

    is_staff:
      тип: BooleanField
      default=False
      True = доступ к админке

    is_online:
      тип: BooleanField
      default=False
      Обновляется middleware

    last_activity:
      тип: DateTimeField
      nullable
      Обновляется middleware при каждом запросе

    last_login_ip:
      тип: GenericIPAddressField
      nullable

    registration_ip:
      тип: GenericIPAddressField
      nullable
      Записывается один раз при регистрации

    registration_method:
      тип: CharField
      choices: [('email', 'Email'),
                ('google', 'Google'),
                ('telegram', 'Telegram'),
                ('phone', 'Телефон')]

    referred_by:
      тип: ForeignKey к самому себе (User)
      nullable
      on_delete: SET_NULL
      Кто пригласил этого пользователя

    referral_code:
      тип: CharField
      уникальный
      максимум 20
      генерируется автоматически при создании
      формат: DOD-XXXXXX (6 случайных символов)

    notification_settings:
      тип: JSONField
      default:
        {
          "site_notifications": true,
          "email_notifications": true,
          "telegram_notifications": false,
          "bet_results": true,
          "promotions": true,
          "security_alerts": true,
          "referral_activity": true
        }

    created_at:
      тип: DateTimeField
      auto_now_add=True

    updated_at:
      тип: DateTimeField
      auto_now=True

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    Методы:
    ───────
    __str__():
      возвращает email

    get_balance_display():
      возвращает форматированный баланс в выбранной валюте
      "$100.00" или "₽7,500.00" или "0.00234 BTC"

    get_avatar_url():
      если есть аватар → URL аватара
      если нет → URL заглушки с инициалами
      (через UI Avatars API или генерация SVG)

    generate_referral_code():
      генерирует DOD-XXXXXX
      проверяет уникальность
      вызывается при создании пользователя

    get_trust_level_display_extended():
      возвращает иконку + название уровня
      1 → "🔵 Новый"
      2 → "🟢 Базовый"
      3 → "🟡 Проверенный"
      4 → "🟠 Доверенный"
      5 → "💎 VIP"

    has_password():
      True если пароль установлен
      False если зарегался через OAuth без пароля

    is_fully_verified():
      True если email ИЛИ телефон подтверждён

    Meta:
      verbose_name = 'Пользователь'
      verbose_name_plural = 'Пользователи'
      ordering = ['-created_at']
      indexes:
        - email (для быстрого поиска)
        - username
        - phone
        - referral_code
        - created_at
```

### Модель LoginHistory (models.py)

```
class LoginHistory(models.Model):

    Назначение:
      Записывает каждый вход пользователя.
      Используется для безопасности и аналитики.

    Поля:
    ─────
    id:
      тип: UUID, primary key

    user:
      тип: ForeignKey → User
      on_delete: CASCADE
      related_name: 'login_history'

    ip_address:
      тип: GenericIPAddressField

    country:
      тип: CharField, max 100
      определяется из IP через GeoIP2
      nullable (если не удалось определить)

    city:
      тип: CharField, max 100
      nullable

    device_type:
      тип: CharField
      choices: [('desktop', 'Компьютер'),
                ('mobile', 'Мобильный'),
                ('tablet', 'Планшет'),
                ('unknown', 'Неизвестно')]

    browser:
      тип: CharField, max 100
      Пример: "Chrome 120", "Safari 17"

    os:
      тип: CharField, max 100
      Пример: "Windows 11", "iOS 17", "Android 14"

    device_name:
      тип: CharField, max 200
      Пример: "iPhone 15 Pro", "Samsung Galaxy S24"

    user_agent:
      тип: TextField
      полная строка user agent

    login_method:
      тип: CharField
      choices: [('email', 'Email + пароль'),
                ('google', 'Google'),
                ('telegram', 'Telegram'),
                ('phone', 'Телефон + SMS')]

    is_successful:
      тип: BooleanField
      default=True
      False = неудачная попытка входа

    failure_reason:
      тип: CharField, nullable
      Пример: "wrong_password", "account_blocked",
              "2fa_failed", "rate_limited"

    is_suspicious:
      тип: BooleanField
      default=False
      True если:
        - Новое устройство
        - Новая страна
        - Ночное время (для пользователя)
        - Множество неудачных попыток перед успешным входом

    session_key:
      тип: CharField, max 40
      nullable
      Для возможности завершить конкретную сессию

    created_at:
      тип: DateTimeField
      auto_now_add=True

    Meta:
      verbose_name = 'История входов'
      ordering = ['-created_at']
      indexes:
        - user + created_at
        - ip_address
```

### Модель ActiveSession (models.py)

```
class ActiveSession(models.Model):

    Назначение:
      Отслеживает активные сессии пользователя.
      Позволяет завершить конкретную сессию
      или все сессии кроме текущей.

    Поля:
    ─────
    id:
      тип: UUID, primary key

    user:
      тип: ForeignKey → User
      on_delete: CASCADE
      related_name: 'active_sessions'

    session_key:
      тип: CharField, max 40
      уникальный
      связь с Django Session

    ip_address:
      тип: GenericIPAddressField

    device_type:
      тип: CharField (desktop/mobile/tablet)

    browser:
      тип: CharField, max 100

    os:
      тип: CharField, max 100

    device_name:
      тип: CharField, max 200

    country:
      тип: CharField, max 100, nullable

    is_current:
      тип: BooleanField
      default=False
      True = это текущая сессия пользователя
      Помечается при просмотре списка сессий

    last_activity:
      тип: DateTimeField
      auto_now=True

    created_at:
      тип: DateTimeField
      auto_now_add=True

    Meta:
      verbose_name = 'Активная сессия'
      ordering = ['-last_activity']
```

### Модель EmailVerification (models.py)

```
class EmailVerification(models.Model):

    Назначение:
      Хранит токены подтверждения email.

    Поля:
    ─────
    id:
      тип: UUID, primary key

    user:
      тип: ForeignKey → User
      on_delete: CASCADE

    email:
      тип: EmailField
      Email который подтверждаем
      (может отличаться от текущего — при смене email)

    token:
      тип: CharField, max 64
      уникальный
      генерируется: secrets.token_urlsafe(32)

    is_used:
      тип: BooleanField
      default=False

    expires_at:
      тип: DateTimeField
      по умолчанию: now + 24 часа

    created_at:
      тип: DateTimeField
      auto_now_add=True

    Методы:
      is_expired(): True если expires_at < now
      is_valid(): True если не is_used и не is_expired

    Meta:
      ordering = ['-created_at']
```

### Модель PhoneVerification (models.py)

```
class PhoneVerification(models.Model):

    Назначение:
      Хранит SMS коды для подтверждения телефона.

    Поля:
    ─────
    id:
      тип: UUID, primary key

    user:
      тип: ForeignKey → User, nullable
      (nullable потому что при регистрации user ещё не создан)

    phone:
      тип: PhoneNumberField

    code:
      тип: CharField, max 6
      генерируется: 6 случайных цифр (secrets.randbelow)

    is_used:
      тип: BooleanField
      default=False

    attempts:
      тип: IntegerField
      default=0
      максимум 3 попытки ввода кода
      после 3 → код аннулируется

    expires_at:
      тип: DateTimeField
      по умолчанию: now + 10 минут

    created_at:
      тип: DateTimeField

    Meta:
      ordering = ['-created_at']

    Ограничения:
      Не более 3 SMS на один номер за 10 минут
      Не более 10 SMS на один номер за 1 час
      Не более 20 SMS на один номер за сутки
```

### Модель BackupCode (models.py)

```
class BackupCode(models.Model):

    Назначение:
      Резервные коды для восстановления доступа
      если пользователь потерял 2FA устройство.
      Генерируется 10 кодов при активации 2FA.

    Поля:
    ─────
    id:
      тип: UUID, primary key

    user:
      тип: ForeignKey → User
      on_delete: CASCADE
      related_name: 'backup_codes'

    code:
      тип: CharField, max 20
      формат: XXXX-XXXX (8 символов + дефис)
      ХРАНИТЬ В ХЕШИРОВАННОМ ВИДЕ (как пароль)

    is_used:
      тип: BooleanField
      default=False

    used_at:
      тип: DateTimeField
      nullable

    created_at:
      тип: DateTimeField
      auto_now_add=True

    Важно:
      Коды показываются пользователю ОДИН РАЗ
      при генерации. После этого мы храним только хеши.
      Пользователь должен сохранить коды.
```

### Модель LinkedAccount (models.py)

```
class LinkedAccount(models.Model):

    Назначение:
      Хранит привязанные аккаунты
      (Google, Telegram, телефон).
      Пользователь может привязать несколько.

    Поля:
    ─────
    id:
      тип: UUID, primary key

    user:
      тип: ForeignKey → User
      on_delete: CASCADE
      related_name: 'linked_accounts'

    provider:
      тип: CharField
      choices: [('google', 'Google'),
                ('telegram', 'Telegram'),
                ('phone', 'Телефон')]

    provider_id:
      тип: CharField, max 255
      ID пользователя у провайдера
      Для Google: google user id
      Для Telegram: telegram user id
      Для телефона: номер телефона

    provider_email:
      тип: EmailField, nullable
      Email от провайдера (Google)

    provider_username:
      тип: CharField, nullable
      Username от провайдера (Telegram)

    provider_avatar:
      тип: URLField, nullable
      Аватар от провайдера

    is_primary:
      тип: BooleanField
      default=False
      True = основной способ входа

    linked_at:
      тип: DateTimeField
      auto_now_add=True

    Meta:
      unique_together = ['provider', 'provider_id']
      verbose_name = 'Привязанный аккаунт'
```

### Файл managers.py

```
class UserManager(BaseUserManager):

    create_user(email, username, password=None, **extra):
      Валидация:
        - email обязателен и не пустой
        - email нормализуется (нижний регистр домена)
        - username обязателен
        - username приводится к нижнему регистру для проверки уникальности
      Создание:
        - Создать пользователя
        - Если password не None → set_password
        - Если password None → set_unusable_password (OAuth)
        - Сгенерировать referral_code
        - Сохранить
      Вернуть пользователя

    create_superuser(email, username, password, **extra):
      Обязательно:
        - is_staff = True
        - is_superuser = True
        - is_email_verified = True
        - trust_level = 5
        - password обязателен (не None)
      Вызвать create_user
```

### Файл admin.py

```
Регистрация User в админке:

UserAdmin:

  list_display:
    - email
    - username
    - balance
    - preferred_currency
    - trust_level
    - kyc_status
    - is_email_verified
    - is_2fa_enabled
    - is_online
    - registration_method
    - created_at

  list_filter:
    - is_active
    - is_email_verified
    - is_phone_verified
    - is_2fa_enabled
    - kyc_status
    - trust_level
    - registration_method
    - country
    - language
    - created_at

  search_fields:
    - email
    - username
    - phone
    - first_name
    - last_name
    - referral_code

  readonly_fields:
    - id
    - created_at
    - updated_at
    - registration_ip
    - last_login_ip
    - registration_method
    - referral_code

  fieldsets:
    Основная информация:
      email, username, password
    Личные данные:
      first_name, last_name, date_of_birth, avatar, country
    Финансы:
      balance, preferred_currency
    Безопасность:
      is_2fa_enabled, two_fa_method, trust_level, kyc_status
    Верификация:
      is_email_verified, is_phone_verified
    Настройки:
      language, timezone, notification_settings
    Реферальная система:
      referral_code, referred_by
    Служебные:
      is_active, is_staff, is_superuser
      registration_method, registration_ip, last_login_ip
      created_at, updated_at

  actions:
    - Заблокировать выбранных пользователей
    - Разблокировать выбранных пользователей
    - Сбросить 2FA
    - Установить trust_level

Также зарегистрировать:
  - LoginHistory (только чтение)
  - ActiveSession
  - EmailVerification
  - PhoneVerification
  - LinkedAccount
  - BackupCode (коды НЕ показывать в открытом виде)
```

### Файл middleware.py

```
class LastActivityMiddleware:

    Назначение:
      Обновляет last_activity и is_online при каждом запросе.
      Если пользователь не делал запросов 5 минут → is_online=False.

    Логика:
      При каждом запросе авторизованного пользователя:
        1. Обновить last_activity = now
        2. Установить is_online = True
        3. Сохранить в кэш Redis (НЕ в БД каждый запрос)
        4. Периодически (раз в 5 мин) синхронизировать с БД
      При бездействии:
        Celery задача каждые 5 минут:
          Найти пользователей где last_activity < now - 5 минут
          Установить is_online = False


class DeviceTrackingMiddleware:

    Назначение:
      При каждом запросе определяет устройство.
      Обновляет ActiveSession.
      Проверяет подозрительность.

    Логика:
      При каждом запросе:
        1. Получить user_agent → определить устройство
        2. Получить IP → определить страну (GeoIP2)
        3. Обновить ActiveSession.last_activity
        4. Если IP изменился в рамках сессии → пометить
```

### Файл signals.py

```
Сигналы:

post_save(User):
    При создании нового пользователя:
    1. Сгенерировать referral_code если пустой
    2. Определить country из registration_ip
    3. Создать дефолтные notification_settings

post_login (django.contrib.auth.signals.user_logged_in):
    При каждом входе:
    1. Записать LoginHistory
    2. Создать/обновить ActiveSession
    3. Обновить last_login_ip
    4. Проверить: новое устройство? новая страна?
    5. Если да → уведомление на email
    6. Если подозрительно → пометить is_suspicious

post_logout (user_logged_out):
    При выходе:
    1. Удалить ActiveSession
    2. Обновить is_online = False

login_failed (user_login_failed):
    При неудачном входе:
    1. Записать LoginHistory с is_successful=False
    2. Проверить количество неудачных попыток
    3. Если >= 5 → заблокировать на 15 минут
    4. Если >= 10 → уведомление на email + в админку
```

### Файл validators.py

```
validate_username(value):
    - Минимум 3 символа
    - Максимум 30 символов
    - Только: a-z, A-Z, а-я, А-Я, 0-9, _, .
    - Не начинается с цифры или точки
    - Не содержит двух точек подряд
    - Не содержит запрещённых слов: admin, moderator, support, dod, system
    - Регистронезависимая проверка уникальности

validate_password_strength(value):
    - Минимум 8 символов
    - Хотя бы одна заглавная буква
    - Хотя бы одна строчная буква
    - Хотя бы одна цифра
    - Не совпадает с email или username

validate_avatar(file):
    - Максимум 5 MB
    - Только jpg, png, webp
    - Минимум 100x100 пикселей
    - Максимум 2000x2000 пикселей

validate_phone(value):
    - Валидный международный формат
    - Поддерживаемые страны: RU, UA, KZ, UZ, BY и другие
```

### Файл tasks.py (Celery)

```
Фоновые задачи:

send_verification_email(user_id, token):
    Отправить email с ссылкой подтверждения.
    Шаблон: красивое HTML письмо с кнопкой.
    Ссылка: https://dod.com/verify-email/{token}
    Срок действия: 24 часа.

send_sms_code(phone, code):
    Отправить SMS через провайдера.
    Текст: "DOD: Ваш код подтверждения: {code}"
    Rate limit: 3 за 10 мин, 10 за час.

send_login_alert(user_id, login_history_id):
    Отправить уведомление о входе с нового устройства.
    На email и/или Telegram (по настройкам пользователя).
    Содержит: устройство, IP, страна, время.
    Кнопка: "Это не я" → заблокировать все сессии.

send_2fa_email_code(user_id, code):
    Отправить 2FA код на email.
    Код: 6 цифр.
    Срок действия: 5 минут.

cleanup_expired_verifications():
    Периодическая задача (каждый час).
    Удалить все expired EmailVerification и PhoneVerification.

update_online_status():
    Периодическая задача (каждые 5 минут).
    Пользователи без активности > 5 мин → is_online=False.
```

### Критерий готовности шага 1.2

```
□ Модель User создана со ВСЕМИ полями
□ Миграции применены без ошибок
□ Суперадмин создан (createsuperuser)
□ Django Admin показывает все модели
□ Все модели: LoginHistory, ActiveSession,
  EmailVerification, PhoneVerification,
  BackupCode, LinkedAccount
□ managers.py: UserManager работает
□ validators.py: все валидаторы
□ middleware.py: LastActivity, DeviceTracking
□ signals.py: все сигналы
□ tasks.py: все Celery задачи
□ Admin настроен с фильтрами и поиском
```

---

## ШАГ 1.3 — БАЗОВЫЙ ШАБЛОН И ДИЗАЙН

### Задача

```
Создай базовый HTML шаблон проекта DOD.
Тёмная тема. Навигация. Sidebar.
Адаптивность. Подключение TailwindCSS и HTMX.
```

### Структура шаблонов

```
templates/
├── base.html                  # Главный шаблон
├── base_auth.html             # Шаблон для auth страниц (без sidebar)
├── components/
│   ├── navbar.html            # Верхняя навигация
│   ├── sidebar.html           # Боковое меню
│   ├── footer.html            # Подвал
│   ├── messages.html          # Django сообщения (alerts)
│   ├── notification_bell.html # Колокольчик уведомлений
│   ├── balance_display.html   # Отображение баланса
│   └── mobile_menu.html       # Мобильное меню
├── home.html                  # Главная страница
└── errors/
    ├── 404.html
    ├── 500.html
    └── 403.html
```

### base.html — Главный шаблон

```
Структура:

<!DOCTYPE html>
<html lang="{{ LANGUAGE_CODE }}" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="DOD — ставки на спорт, казино, маркеты предсказаний">

    <title>{% block title %}DOD{% endblock %} | DOD</title>

    <!-- TailwindCSS через CDN -->
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {
            darkMode: 'class',
            theme: {
                extend: {
                    colors: {
                        'dod-bg': '#0f1923',         // Основной фон
                        'dod-card': '#1a2c38',       // Карточки
                        'dod-sidebar': '#0f1923',    // Sidebar
                        'dod-navbar': '#1a2c38',     // Navbar
                        'dod-border': '#2a3a48',     // Границы
                        'dod-accent': '#00e701',     // Акцент (зелёный)
                        'dod-accent-hover': '#00c801',
                        'dod-text': '#ffffff',       // Основной текст
                        'dod-text-secondary': '#8b9caa', // Вторичный
                        'dod-danger': '#ff4444',     // Ошибки
                        'dod-warning': '#ffaa00',    // Предупреждения
                        'dod-success': '#00e701',    // Успех
                        'dod-info': '#3b82f6',       // Информация
                    }
                }
            }
        }
    </script>

    <!-- HTMX -->
    <script src="https://unpkg.com/htmx.org@1.9.12"></script>

    <!-- Alpine.js (для интерактивности меню) -->
    <script defer src="https://unpkg.com/alpinejs@3.x.x/dist/cdn.min.js"></script>

    <!-- Свои стили -->
    {% block extra_css %}{% endblock %}
</head>

<body class="bg-dod-bg text-dod-text min-h-screen flex flex-col">

    <!-- Navbar -->
    {% include 'components/navbar.html' %}

    <!-- Основная часть -->
    <div class="flex flex-1">

        <!-- Sidebar (скрывается на мобильных) -->
        {% include 'components/sidebar.html' %}

        <!-- Контент -->
        <main class="flex-1 p-4 md:p-6 overflow-auto">

            <!-- Django сообщения -->
            {% include 'components/messages.html' %}

            <!-- Контент страницы -->
            {% block content %}{% endblock %}

        </main>
    </div>

    <!-- Footer -->
    {% include 'components/footer.html' %}

    <!-- Свои скрипты -->
    {% block extra_js %}{% endblock %}

</body>
</html>
```

### base_auth.html — Шаблон для страниц авторизации

```
Такой же как base.html, но:
  - БЕЗ sidebar
  - БЕЗ navbar (или минимальный navbar только с логотипом)
  - Контент центрирован по середине экрана
  - Фон: может быть с паттерном или градиентом
  - Используется для: login, register, forgot-password, verify
```

### components/navbar.html

```
Высота: 64px
Фон: bg-dod-navbar
Тень: shadow-lg
Липкая: sticky top-0 z-50

Содержимое:

ЛЕВАЯ ЧАСТЬ:
  - Бургер-кнопка (мобильные, открывает sidebar)
  - Логотип: "🎲 DOD" (крупный, жирный)
  - При клике → главная /

ЦЕНТРАЛЬНАЯ ЧАСТЬ (только десктоп):
  - Быстрые ссылки: Спорт | Казино | Прогнозы

ПРАВАЯ ЧАСТЬ:

  Если авторизован:
    ┌──────────────────────────────────────────────────┐
    │ 💰 $100.00 [Пополнить] 🔔(3) 👤 username ▼    │
    └──────────────────────────────────────────────────┘

    - Баланс: зелёным цветом, кликабельный → /wallet/
      HTMX: обновляется каждые 30 сек без перезагрузки
      hx-get="/api/balance/" hx-trigger="every 30s"

    - Кнопка "Пополнить": зелёная, → /wallet/deposit/

    - Колокольчик: с бейджем количества непрочитанных
      При клике → выпадающий список уведомлений

    - Аватар + username: при клике → выпадающее меню:
      ├── 👤 Профиль
      ├── 💰 Кошелёк
      ├── 📋 Мои ставки
      ├── 🤝 Партнёрская программа
      ├── ⚙️ Настройки
      ├── 🔐 Безопасность
      ├── ─────────────
      └── 🚪 Выйти

  Если НЕ авторизован:
    ┌──────────────────────────────────┐
    │ [Войти]  [Регистрация]          │
    └──────────────────────────────────┘

    - "Войти": прозрачная кнопка с рамкой
    - "Регистрация": зелёная кнопка (акцент)
```

### components/sidebar.html

```
Ширина: 240px (десктоп), скрыт (мобильные)
Фон: bg-dod-sidebar
Позиция: фиксированная слева
Высота: 100vh минус navbar

Пункты меню:

  ОСНОВНОЕ:
  ├── 🏠 Главная           → /
  ├── ⚽ Спорт             → /sports/
  ├── 🎰 Казино            → /casino/
  ├── 📊 Прогнозы          → /predictions/
  │
  ЛИЧНОЕ:
  ├── 💰 Кошелёк           → /wallet/
  ├── 📋 Мои ставки        → /my-bets/
  ├── 🤝 Партнёрка         → /partners/
  │
  ДРУГОЕ:
  ├── 💬 Поддержка         → /support/
  ├── 📖 FAQ               → /faq/
  └── ⚙️ Настройки         → /settings/

Поведение:
  - Активный пункт: bg-dod-accent с прозрачностью,
    зелёная левая полоска
  - Hover: bg-white/5
  - Каждый пункт: иконка + текст
  - Мобильные: выезжает слева при клике на бургер
    затемнение фона при открытом меню
    Alpine.js для анимации
  - Внизу sidebar: переключатель языка (RU / EN)
```

### components/messages.html

```
Django messages framework.
Показывает уведомления после действий.

Типы:
  success → зелёный блок с иконкой ✅
  error   → красный блок с иконкой ❌
  warning → жёлтый блок с иконкой ⚠️
  info    → синий блок с иконкой ℹ️

Поведение:
  - Появляется вверху контента
  - Кнопка X для закрытия
  - Автоскрытие через 5 секунд
  - Анимация появления/исчезновения
```

### home.html

```
{% extends 'base.html' %}
{% block title %}Главная{% endblock %}

Содержимое:

1. БАННЕР (hero секция):
   ┌──────────────────────────────────────────────┐
   │                                              │
   │   🎲 Добро пожаловать в DOD                 │
   │                                              │
   │   Ставки на спорт • Казино • Прогнозы       │
   │                                              │
   │   [Начать играть]  [Регистрация]             │
   │                                              │
   └──────────────────────────────────────────────┘
   Градиентный фон. Кнопки зелёные.
   Если авторизован → только "Начать играть"
   Если нет → обе кнопки

2. ТРИ КАРТОЧКИ РАЗДЕЛОВ:
   ┌──────────┐ ┌──────────┐ ┌──────────┐
   │ ⚽ Спорт │ │ 🎰Казино │ │ 📊Прогноз│
   │          │ │          │ │          │
   │ Делай    │ │ Crash    │ │ Предска- │
   │ ставки   │ │ Slots    │ │ зывай    │
   │ на матчи │ │ Roulette │ │ события  │
   │          │ │          │ │          │
   │ [Играть] │ │ [Играть] │ │ [Играть] │
   └──────────┘ └──────────┘ └──────────┘

3. ПОСЛЕДНИЕ ВЫИГРЫШИ (будущее, пока заглушка):
   Бегущая строка или таблица:
   "🎉 User*** выиграл $1,234 в Crash"
   "🎉 User*** выиграл $567 на ставке Реал — Барса"

4. СТАТИСТИКА ПЛАТФОРМЫ (заглушка):
   ┌────────────┬──────────────┬────────────┐
   │ 🎮 1,234   │ 💰 $123,456 │ 👥 5,678  │
   │ Игр сегодня│ Выплачено    │ Онлайн    │
   └────────────┴──────────────┴────────────┘
```

### Страницы ошибок

```
errors/404.html:
  "Страница не найдена"
  Тёмная тема
  Кнопка "На главную"

errors/500.html:
  "Ошибка сервера"
  "Мы уже работаем над решением"
  Кнопка "На главную"

errors/403.html:
  "Доступ запрещён"
  Кнопка "На главную"
```

### Критерий готовности шага 1.3

```
□ base.html создан с TailwindCSS + HTMX + Alpine.js
□ base_auth.html создан (для страниц авторизации)
□ Navbar: логотип, ссылки, баланс, аватар, выпадающее меню
□ Sidebar: все пункты, активный подсвечивается
□ Мобильная версия: бургер-меню, sidebar выезжает
□ Главная страница: баннер, 3 карточки, заглушки
□ Сообщения Django: стилизованы
□ Страницы ошибок: 404, 500, 403
□ Цветовая схема DOD применена
□ Переключатель языка RU/EN в sidebar
□ localhost:8000 показывает красивую главную
```

---

## ШАГ 1.4 — РЕГИСТРАЦИЯ (ВСЕ СПОСОБЫ)

### Задача

```
Создай полную систему регистрации:
- Email + пароль
- Google (OAuth в один клик)
- Telegram
- Номер телефона (SMS код)

С подтверждением email/телефона.
С реферальным кодом при регистрации.
С определением страны и устройства.
```

### Страница регистрации

```
URL: /register/

Шаблон: templates/accounts/register.html
Наследует: base_auth.html (без sidebar)

Дизайн:
  По центру экрана карточка (bg-dod-card, rounded-2xl)
  Максимальная ширина: 480px
  Внутренний отступ: 32px

Содержимое карточки:

  ┌───────────────────────────────────────┐
  │          🎲 Создать аккаунт DOD      │
  │                                       │
  │   [🔵 Войти через Google        ]    │
  │   [📱 Войти через Telegram      ]    │
  │                                       │
  │   ──────── или ────────              │
  │                                       │
  │   📧 Email                            │
  │   ┌─────────────────────────────┐    │
  │   │ your@email.com              │    │
  │   └─────────────────────────────┘    │
  │                                       │
  │   👤 Username                         │
  │   ┌─────────────────────────────┐    │
  │   │ username                    │    │
  │   └─────────────────────────────┘    │
  │                                       │
  │   📱 Телефон (необязательно)         │
  │   ┌─────────────────────────────┐    │
  │   │ +7 (___) ___-__-__         │    │
  │   └─────────────────────────────┘    │
  │                                       │
  │   🔒 Пароль                          │
  │   ┌─────────────────────────────┐    │
  │   │ ••••••••            👁️     │    │
  │   └─────────────────────────────┘    │
  │   Сила пароля: [████████░░] Хороший │
  │                                       │
  │   🔒 Подтвердите пароль              │
  │   ┌─────────────────────────────┐    │
  │   │ ••••••••            👁️     │    │
  │   └─────────────────────────────┘    │
  │                                       │
  │   🎁 Реферальный код (необязательно) │
  │   ┌─────────────────────────────┐    │
  │   │ DOD-XXXXXX                  │    │
  │   └─────────────────────────────┘    │
  │                                       │
  │   ☑ Я согласен с правилами сервиса  │
  │                                       │
  │   [    Зарегистрироваться     ]      │
  │                                       │
  │   Уже есть аккаунт? Войти           │
  │                                       │
  └───────────────────────────────────────┘
```

### Логика регистрации через Email

```
RegisterEmailView:

  GET:
    Показать форму регистрации.
    Если в URL есть ?ref=DOD-XXXXXX → подставить в поле.

  POST:
    Получить данные: email, username, phone (опц),
                     password1, password2, referral_code (опц)

    Валидация:
      1. email:
         - Формат валидный
         - НЕ занят другим пользователем
         - НЕ в чёрном списке доменов (tempmail, guerrillamail...)
         - Привести к нижнему регистру

      2. username:
         - 3-30 символов
         - Допустимые символы (валидатор)
         - НЕ занят (регистронезависимо)
         - НЕ запрещённое слово

      3. phone (если указан):
         - Валидный международный формат
         - НЕ занят
         - Поддерживаемая страна

      4. password:
         - Минимум 8 символов
         - Сложность (валидатор)
         - password1 == password2

      5. referral_code (если указан):
         - Существует в БД
         - Принадлежит активному пользователю
         - Не свой собственный (невозможно на регистрации, но проверка)

      6. Согласие с правилами:
         - Чекбокс отмечен

    При ошибках:
      Вернуть форму с ошибками.
      Ошибки показываются под каждым полем красным.
      Заполненные поля сохраняются (кроме пароля).

    При успехе:
      1. Создать User:
         - registration_method = 'email'
         - registration_ip = request IP
         - is_email_verified = False
         - trust_level = 1
         - country = определить из IP
         - language = определить из браузера или 'ru'
         - Сгенерировать referral_code

      2. Если referral_code указан:
         - referred_by = User с этим кодом

      3. Если phone указан:
         - Сохранить phone
         - is_phone_verified = False

      4. Создать EmailVerification:
         - Сгенерировать token
         - Отправить email (Celery задача)

      5. Автоматически залогинить (login)

      6. Создать LoginHistory

      7. Создать ActiveSession

      8. Редирект на /verify-email/
         (страница "Проверьте почту")

    Защита:
      - Rate limit: 3 регистрации с одного IP за час
      - CSRF token
      - Honeypot поле (скрытое поле для ботов)
```

### Логика регистрации через Google

```
URL: /auth/google/login/

Использует django-allauth.

Поток:
  1. Пользователь нажимает "Войти через Google"
  2. Редирект на Google OAuth
  3. Google возвращает данные:
     - google_id
     - email
     - first_name, last_name
     - avatar URL

  4. Если email уже есть в БД:
     → Это вход, не регистрация
     → Залогинить
     → Если Google не привязан → привязать LinkedAccount

  5. Если email НЕТ в БД:
     → Создать нового пользователя:
       - email = от Google
       - username = сгенерировать из email (до @)
         если занят → добавить случайные цифры
       - password = unusable (не задан)
       - is_email_verified = True (Google уже проверил)
       - registration_method = 'google'
       - first_name, last_name от Google
       - avatar = скачать от Google
       - trust_level = 2 (Google верифицировал email)

     → Создать LinkedAccount:
       - provider = 'google'
       - provider_id = google_id
       - provider_email = email
       - is_primary = True

     → Если в URL был ?ref=DOD-XXXXXX:
       - referred_by = User с этим кодом

     → Залогинить
     → Редирект на / (главная)

  Важно:
    При Google входе НЕ требовать 2FA на первый раз.
    Предложить настроить 2FA позже.
```

### Логика регистрации через Telegram

```
URL: /auth/telegram/callback/

Поток:
  1. На странице регистрации — Telegram Login Widget
     (официальный виджет от Telegram)

  2. Пользователь нажимает → авторизуется через Telegram

  3. Telegram возвращает:
     - telegram_id
     - first_name
     - last_name (опционально)
     - username (опционально)
     - photo_url (опционально)

  4. Проверить подпись данных (hash от Telegram Bot Token)
     Если подпись невалидна → ошибка "Недействительные данные"

  5. Если telegram_id уже есть в LinkedAccount:
     → Это вход, залогинить

  6. Если telegram_id НЕТ:
     → Показать дополнительную форму:
       ┌──────────────────────────────────┐
       │  Почти готово!                   │
       │                                  │
       │  📧 Email (обязательно)          │
       │  ┌──────────────────────────┐   │
       │  │ your@email.com           │   │
       │  └──────────────────────────┘   │
       │                                  │
       │  👤 Username                     │
       │  ┌──────────────────────────┐   │
       │  │ (подставлен из Telegram) │   │
       │  └──────────────────────────┘   │
       │                                  │
       │  🎁 Реферальный код (опц.)      │
       │  ┌──────────────────────────┐   │
       │  │ DOD-XXXXXX               │   │
       │  └──────────────────────────┘   │
       │                                  │
       │  [Завершить регистрацию]         │
       │                                  │
       └──────────────────────────────────┘

     → Создать User:
       - email = введённый
       - username = введённый
       - password = unusable
       - registration_method = 'telegram'
       - is_email_verified = False
       - Отправить email подтверждение

     → Создать LinkedAccount:
       - provider = 'telegram'
       - provider_id = telegram_id
       - provider_username = Telegram username
       - is_primary = True

     → Залогинить
     → Редирект на /verify-email/
```

### Логика регистрации через телефон

```
URL: /register/phone/

Поток (два шага):

  ШАГ 1 — Ввод номера:
    ┌──────────────────────────────────┐
    │  📱 Регистрация по телефону     │
    │                                  │
    │  Номер телефона                  │
    │  ┌──────────────────────────┐   │
    │  │ 🇷🇺 +7 (___) ___-__-__  │   │
    │  └──────────────────────────┘   │
    │                                  │
    │  [Получить SMS код]             │
    │                                  │
    └──────────────────────────────────┘

    При отправке:
      - Валидация номера
      - Проверка что номер не зарегистрирован
      - Rate limit: 3 SMS за 10 минут
      - Создать PhoneVerification (код 6 цифр)
      - Отправить SMS (Celery)
      - Показать шаг 2

  ШАГ 2 — Ввод кода + данные:
    ┌──────────────────────────────────┐
    │  Код отправлен на +7 (XXX)      │
    │                                  │
    │  Код из SMS                      │
    │  ┌──┐ ┌──┐ ┌──┐ ┌──┐ ┌──┐ ┌──┐│
    │  │  │ │  │ │  │ │  │ │  │ │  ││
    │  └──┘ └──┘ └──┘ └──┘ └──┘ └──┘│
    │  Отправить повторно через 60 сек│
    │                                  │
    │  📧 Email                        │
    │  ┌──────────────────────────┐   │
    │  │ your@email.com           │   │
    │  └──────────────────────────┘   │
    │                                  │
    │  👤 Username                     │
    │  ┌──────────────────────────┐   │
    │  │ username                 │   │
    │  └──────────────────────────┘   │
    │                                  │
    │  🔒 Пароль                      │
    │  ┌──────────────────────────┐   │
    │  │ ••••••••                 │   │
    │  └──────────────────────────┘   │
    │                                  │
    │  🎁 Реферальный код (опц.)      │
    │  ┌──────────────────────────┐   │
    │  │ DOD-XXXXXX               │   │
    │  └──────────────────────────┘   │
    │                                  │
    │  [Зарегистрироваться]           │
    │                                  │
    └──────────────────────────────────┘

    При отправке:
      - Проверить SMS код:
        - Не expired (10 мин)
        - Не использован
        - Не превышено количество попыток (3)
        - Код совпадает

      - Если код неверный:
        - attempts += 1
        - Если attempts >= 3 → код аннулирован, новый SMS
        - Показать ошибку

      - Если код верный:
        - Создать User
        - is_phone_verified = True
        - registration_method = 'phone'
        - Отправить email подтверждение
        - Залогинить
        - Редирект на /verify-email/
```

### Страница подтверждения email

```
URL: /verify-email/

Показывается после регистрации если email не подтверждён.

  ┌──────────────────────────────────────┐
  │  📧 Подтвердите ваш email           │
  │                                      │
  │  Мы отправили письмо на:            │
  │  user@example.com                    │
  │                                      │
  │  Перейдите по ссылке в письме       │
  │  для подтверждения аккаунта.        │
  │                                      │
  │  Не получили письмо?                │
  │  [Отправить повторно]               │
  │                                      │
  │  Отправить повторно через: 60 сек   │
  │                                      │
  └──────────────────────────────────────┘

URL подтверждения: /verify-email/{token}/

При переходе по ссылке:
  1. Найти EmailVerification по token
  2. Проверить: не expired, не used
  3. Если валидный:
     - User.is_email_verified = True
     - EmailVerification.is_used = True
     - trust_level = max(trust_level, 2)
     - Сообщение "Email подтверждён!"
     - Редирект на /
  4. Если невалидный:
     - Сообщение "Ссылка недействительна или истекла"
     - Кнопка "Отправить новую ссылку"
```

### Критерий готовности шага 1.4

```
□ Регистрация через Email работает
□ Регистрация через Google OAuth работает
□ Регистрация через Telegram работает
□ Регистрация через телефон (SMS) работает
□ Email подтверждение отправляется
□ SMS код отправляется
□ Реферальный код сохраняется
□ При регистрации определяется страна из IP
□ LoginHistory записывается
□ ActiveSession создаётся
□ Валидация всех полей работает
□ Ошибки показываются красным под полями
□ Rate limiting работает
□ CSRF защита работает
□ Форма красивая, тёмная тема
□ Мобильная адаптация
□ Honeypot для ботов
```

---

## ШАГ 1.5 — ВХОД + 2FA + ВОССТАНОВЛЕНИЕ

### Задача

```
Создай полную систему входа:
- Email + пароль + 2FA
- Google (один клик)
- Telegram
- Телефон + SMS
С восстановлением пароля и 2FA.
```

### Страница входа

```
URL: /login/

Шаблон: templates/accounts/login.html
Наследует: base_auth.html

  ┌───────────────────────────────────────┐
  │          🎲 Войти в DOD              │
  │                                       │
  │   [🔵 Войти через Google        ]    │
  │   [📱 Войти через Telegram      ]    │
  │                                       │
  │   ──────── или ────────              │
  │                                       │
  │   📧 Email или телефон               │
  │   ┌─────────────────────────────┐    │
  │   │ email@example.com           │    │
  │   └─────────────────────────────┘    │
  │                                       │
  │   🔒 Пароль                          │
  │   ┌─────────────────────────────┐    │
  │   │ ••••••••            👁️     │    │
  │   └─────────────────────────────┘    │
  │                                       │
  │   ☐ Запомнить меня                   │
  │                                       │
  │   [         Войти              ]      │
  │                                       │
  │   Забыли пароль?                     │
  │   Войти по SMS коду                  │
  │                                       │
  │   Нет аккаунта? Зарегистрироваться   │
  │                                       │
  └───────────────────────────────────────┘

Поле "Email или телефон":
  Принимает оба формата.
  Если введён телефон → ищет по phone.
  Если введён email → ищет по email.
```

### Логика входа через Email/Телефон

```
LoginView:

  POST:
    1. Получить: login_field, password

    2. Определить тип (email или телефон):
       - Содержит @ → email
       - Начинается с + или цифры → телефон

    3. Найти пользователя:
       - По email или phone

    4. Если не найден:
       - НЕ говорить "пользователь не найден"
         (безопасность: не раскрывать существование аккаунтов)
       - Сообщение: "Неверный email/телефон или пароль"

    5. Если найден:
       - Проверить is_active
         Если False → "Аккаунт заблокирован.
         Обратитесь в поддержку."

       - Проверить пароль (check_password)
         Если неверный:
           - Записать LoginHistory (is_successful=False)
           - Проверить количество неудачных попыток за 15 мин
           - Если >= 5 → "Слишком много попыток.
             Попробуйте через 15 минут."
           - Иначе → "Неверный email/телефон или пароль"

       - Если пароль верный:
         Проверить is_2fa_enabled

         Если 2FA ВЫКЛЮЧЕНА:
           → Залогинить
           → Записать LoginHistory
           → Создать ActiveSession
           → Проверить новое устройство → уведомление
           → Если "запомнить меня" → сессия 30 дней
             Иначе → сессия 30 минут
           → Редирект на / (или на ?next= если было)

         Если 2FA ВКЛЮЧЕНА:
           → НЕ логинить ещё
           → Сохранить user_id в сессии временно
           → Редирект на /login/2fa/

    Rate Limit:
      5 попыток за 15 минут с одного IP
      10 попыток за 15 минут на один аккаунт
```

### Страница 2FA подтверждения

```
URL: /login/2fa/

Доступна только после успешного ввода пароля.
Если зашёл напрямую → редирект на /login/

Отображение зависит от two_fa_method:

  Если TOTP (Google Authenticator):
    ┌──────────────────────────────────────┐
    │  🔐 Двухфакторная аутентификация    │
    │                                      │
    │  Введите код из Google Authenticator │
    │                                      │
    │  ┌──┐ ┌──┐ ┌──┐ ┌──┐ ┌──┐ ┌──┐    │
    │  │  │ │  │ │  │ │  │ │  │ │  │    │
    │  └──┘ └──┘ └──┘ └──┘ └──┘ └──┘    │
    │                                      │
    │  [Подтвердить]                      │
    │                                      │
    │  Нет доступа к приложению?          │
    │  Использовать резервный код         │
    │  Отправить код на email             │
    │                                      │
    └──────────────────────────────────────┘

  Если Email:
    ┌──────────────────────────────────────┐
    │  🔐 Двухфакторная аутентификация    │
    │                                      │
    │  Код отправлен на u***@example.com  │
    │                                      │
    │  ┌──┐ ┌──┐ ┌──┐ ┌──┐ ┌──┐ ┌──┐    │
    │  │  │ │  │ │  │ │  │ │  │ │  │    │
    │  └──┘ └──┘ └──┘ └──┘ └──┘ └──┘    │
    │                                      │
    │  [Подтвердить]                      │
    │                                      │
    │  Не получили код?                   │
    │  [Отправить повторно] через 60 сек  │
    │  Использовать резервный код         │
    │                                      │
    └──────────────────────────────────────┘

Логика:
  1. Проверить код (TOTP или Email)
  2. Если верный → залогинить полностью
  3. Если неверный → ошибка, попыток осталось: N
  4. После 3 неудачных → заблокировать на 15 мин
```

### Страница ввода резервного кода

```
URL: /login/backup-code/

  ┌──────────────────────────────────────┐
  │  🔑 Резервный код                   │
  │                                      │
  │  Введите один из ваших              │
  │  резервных кодов:                   │
  │                                      │
  │  ┌────────────────────────────┐     │
  │  │ XXXX-XXXX                  │     │
  │  └────────────────────────────┘     │
  │                                      │
  │  [Подтвердить]                      │
  │                                      │
  │  ⚠️ Каждый код можно                │
  │  использовать только один раз       │
  │                                      │
  └──────────────────────────────────────┘

Логика:
  1. Перебрать все BackupCode пользователя
  2. Сравнить хеш введённого с хранимыми
  3. Если совпал и не is_used:
     - Пометить is_used=True, used_at=now
     - Залогинить
     - Предупреждение: "Использован резервный код.
       Осталось: N. Рекомендуем перегенерировать."
  4. Если не совпал → ошибка
```

### Восстановление пароля

```
URL: /forgot-password/

ШАГ 1 — Ввод email:
  ┌──────────────────────────────────────┐
  │  🔑 Восстановление пароля           │
  │                                      │
  │  📧 Email                            │
  │  ┌────────────────────────────┐     │
  │  │ your@email.com             │     │
  │  └────────────────────────────┘     │
  │                                      │
  │  [Отправить ссылку]                 │
  │                                      │
  │  Вспомнили пароль? Войти            │
  │                                      │
  └──────────────────────────────────────┘

  Логика:
    - ВСЕГДА показывать "Если аккаунт существует,
      мы отправили ссылку" (безопасность)
    - Если email существует → отправить ссылку (Celery)
    - Если не существует → ничего не делать
    - Rate limit: 3 запроса за 15 минут
    - Ссылка действует 1 час

URL: /reset-password/{token}/

ШАГ 2 — Новый пароль:
  ┌──────────────────────────────────────┐
  │  🔑 Новый пароль                    │
  │                                      │
  │  🔒 Новый пароль                    │
  │  ┌────────────────────────────┐     │
  │  │ ••••••••                   │     │
  │  └────────────────────────────┘     │
  │  Сила: [████████░░] Хороший        │
  │                                      │
  │  🔒 Подтвердите пароль              │
  │  ┌────────────────────────────┐     │
  │  │ ••••••••                   │     │
  │  └────────────────────────────┘     │
  │                                      │
  │  [Сменить пароль]                   │
  │                                      │
  └──────────────────────────────────────┘

  Логика:
    1. Проверить token (валидный, не expired, не used)
    2. Валидация нового пароля
    3. Сменить пароль
    4. Завершить ВСЕ активные сессии (безопасность)
    5. Уведомление на email: "Ваш пароль изменён"
    6. Редирект на /login/ с сообщением "Пароль изменён"
```

### Вход по SMS (без пароля)

```
URL: /login/sms/

ШАГ 1 — Ввод номера:
  ┌──────────────────────────────────────┐
  │  📱 Вход по SMS                     │
  │                                      │
  │  Номер телефона                      │
  │  ┌────────────────────────────┐     │
  │  │ +7 (___) ___-__-__        │     │
  │  └────────────────────────────┘     │
  │                                      │
  │  [Получить код]                     │
  │                                      │
  └──────────────────────────────────────┘

  - Проверить что номер зарегистрирован
  - Отправить SMS код
  - Rate limit

ШАГ 2 — Ввод кода:
  - 6 цифр
  - 3 попытки
  - 10 минут на ввод
  - При успехе → проверить 2FA
    (если включена → перейти на /login/2fa/)
  - Если 2FA выключена → залогинить
```

### Логаут

```
URL: /logout/

Метод: POST (не GET! для безопасности)

Логика:
  1. Удалить ActiveSession
  2. Обновить is_online = False
  3. Вызвать logout(request)
  4. Редирект на / (главная)
```

### Критерий готовности шага 1.5

```
□ Вход через email + пароль работает
□ Вход через Google работает
□ Вход через Telegram работает
□ Вход через SMS работает
□ 2FA через Google Authenticator работает
□ 2FA через email код работает
□ Резервные коды работают
□ Восстановление пароля через email работает
□ Уведомление о входе с нового устройства
□ LoginHistory записывается
□ ActiveSession управляется
□ Rate limiting работает
□ Блокировка после 5 неудачных попыток
□ "Запомнить меня" меняет срок сессии
□ Логаут работает (POST)
□ Все формы красивые, тёмная тема
□ Мобильная адаптация
```

---

## ШАГ 1.6 — ПРОФИЛЬ + НАСТРОЙКИ БЕЗОПАСНОСТИ

### Задача

```
Создай страницы профиля, настроек,
управления безопасностью и сессиями.
```

### Страница профиля

```
URL: /profile/
Доступ: только авторизованные (@login_required)

  ┌──────────────────────────────────────────────┐
  │  👤 Мой профиль                              │
  │                                              │
  │  ┌────┐  username                            │
  │  │ AV │  user@email.com ✅ (подтверждён)     │
  │  │ AT │  +7 (XXX) XXX-XX-XX ✅              │
  │  │ AR │  Участник с: 15 марта 2025           │
  │  └────┘  Уровень доверия: 🟢 Базовый        │
  │                                              │
  │  ┌─────────────────────────────────────────┐ │
  │  │  💰 Баланс                              │ │
  │  │  $1,234.56                    [Пополнить]│ │
  │  └─────────────────────────────────────────┘ │
  │                                              │
  │  ┌──────────┬──────────┬──────────┐         │
  │  │ 📊 47    │ 🏆 23    │ 📈 48.9%│         │
  │  │ Ставок   │ Выиграно │ Винрейт │         │
  │  └──────────┴──────────┴──────────┘         │
  │                                              │
  │  [Редактировать] [Настройки] [Безопасность] │
  │                                              │
  └──────────────────────────────────────────────┘
```

### Страница редактирования профиля

```
URL: /profile/edit/

Форма:
  - Аватар (загрузка, кнопка "Удалить")
  - Username
  - Имя
  - Фамилия
  - Дата рождения
  - Страна (выпадающий список)
  - Язык (RU / EN)
  - Часовой пояс
  - Предпочитаемая валюта

Валидация:
  - Username: валидатор (уникальный, допустимые символы)
  - Аватар: валидатор (размер, формат)
  - При сохранении: сообщение "Профиль обновлён"

HTMX:
  Сохранение без перезагрузки страницы.
  hx-post, hx-swap
```

### Страница безопасности

```
URL: /security/

  ┌──────────────────────────────────────────────┐
  │  🔐 Безопасность                            │
  │                                              │
  │  ── Пароль ──────────────────────────────── │
  │  Последнее изменение: 15 марта 2025         │
  │  [Сменить пароль]                           │
  │  (Если зарегался через OAuth и пароля нет:  │
  │   [Установить пароль])                       │
  │                                              │
  │  ── Двухфакторная аутентификация ────────── │
  │  Статус: ✅ Включена (Google Authenticator) │
  │  [Отключить 2FA]  [Сменить метод]          │
  │  [Перегенерировать резервные коды]          │
  │  Резервных кодов осталось: 8 из 10          │
  │  (Если выключена:                           │
  │   ⚠️ Рекомендуем включить 2FA              │
  │   [Включить 2FA])                           │
  │                                              │
  │  ── Привязанные аккаунты ───────────────── │
  │  🔵 Google: user@gmail.com  [Отвязать]     │
  │  📱 Telegram: @username     [Отвязать]     │
  │  📞 Телефон: +7 (XXX)...   [Отвязать]     │
  │  [Привязать Google]                         │
  │  [Привязать Telegram]                       │
  │  [Привязать телефон]                        │
  │                                              │
  │  ── Активные сессии ─────────────────────── │
  │  🖥️ Chrome, Windows 11                     │
  │     Москва, Россия • Сейчас                │
  │     (текущая сессия)                        │
  │                                              │
  │  📱 Safari, iOS 17                          │
  │     Москва, Россия • 2 часа назад          │
  │     [Завершить]                             │
  │                                              │
  │  📱 Chrome, Android 14                      │
  │     Алматы, Казахстан • 1 день назад       │
  │     [Завершить]                             │
  │                                              │
  │  [Завершить все кроме текущей]              │
  │                                              │
  │  ── История входов ──────────────────────── │
  │                                              │
  │  ✅ Сегодня 14:30 • Chrome, Windows        │
  │     Москва, RU • Email + пароль             │
  │                                              │
  │  ✅ Вчера 09:15 • Safari, iOS              │
  │     Москва, RU • Google                      │
  │                                              │
  │  ❌ Вчера 03:22 • Firefox, Linux           │
  │     Минск, BY • Неверный пароль ⚠️          │
  │                                              │
  │  [Показать всю историю]                    │
  │                                              │
  │  ── KYC Верификация ─────────────────────── │
  │  Статус: ⏳ Не подана                       │
  │  [Пройти верификацию]                       │
  │  (или: ✅ Одобрена / 🔄 На проверке /      │
  │        ❌ Отклонена — подать повторно)      │
  │                                              │
  └──────────────────────────────────────────────┘
```

### Настройка 2FA

```
URL: /security/2fa/setup/

ШАГ 1 — Выбор метода:
  ┌──────────────────────────────────────┐
  │  🔐 Настройка 2FA                   │
  │                                      │
  │  Выберите метод:                     │
  │                                      │
  │  ┌────────────────────────────────┐ │
  │  │ 📱 Google Authenticator        │ │
  │  │ Рекомендуется. Самый надёжный. │ │
  │  │ [Выбрать]                      │ │
  │  └────────────────────────────────┘ │
  │                                      │
  │  ┌────────────────────────────────┐ │
  │  │ 📧 Email код                   │ │
  │  │ Код отправляется на email.     │ │
  │  │ [Выбрать]                      │ │
  │  └────────────────────────────────┘ │
  │                                      │
  └──────────────────────────────────────┘

ШАГ 2 — Если Google Authenticator:
  ┌──────────────────────────────────────┐
  │  📱 Отсканируйте QR-код            │
  │                                      │
  │        ┌──────────────┐             │
  │        │   QR CODE    │             │
  │        │              │             │
  │        └──────────────┘             │
  │                                      │
  │  Или введите ключ вручную:          │
  │  JBSWY3DPEHPK3PXP                  │
  │                                      │
  │  Введите код из приложения:         │
  │  ┌──┐ ┌──┐ ┌──┐ ┌──┐ ┌──┐ ┌──┐   │
  │  │  │ │  │ │  │ │  │ │  │ │  │   │
  │  └──┘ └──┘ └──┘ └──┘ └──┘ └──┘   │
  │                                      │
  │  [Подтвердить и включить]           │
  │                                      │
  └──────────────────────────────────────┘

  Логика:
    1. Сгенерировать TOTP секрет
    2. Показать QR код
    3. Пользователь сканирует и вводит код
    4. Проверить код
    5. Если верный:
       - Сохранить TOTP устройство
       - is_2fa_enabled = True
       - two_fa_method = 'totp'
       - Сгенерировать 10 резервных кодов
       - Показать резервные коды (ОДИН РАЗ)

ШАГ 3 — Резервные коды:
  ┌──────────────────────────────────────┐
  │  🔑 Сохраните резервные коды!       │
  │                                      │
  │  ⚠️ Эти коды будут показаны         │
  │  ТОЛЬКО ОДИН РАЗ.                   │
  │  Сохраните их в надёжном месте.     │
  │                                      │
  │  ┌────────────────────────────────┐ │
  │  │  1. ABCD-EFGH                  │ │
  │  │  2. IJKL-MNOP                  │ │
  │  │  3. QRST-UVWX                  │ │
  │  │  4. YZAB-CDEF                  │ │
  │  │  5. GHIJ-KLMN                  │ │
  │  │  6. OPQR-STUV                  │ │
  │  │  7. WXYZ-ABCD                  │ │
  │  │  8. EFGH-IJKL                  │ │
  │  │  9. MNOP-QRST                  │ │
  │  │ 10. UVWX-YZAB                  │ │
  │  └────────────────────────────────┘ │
  │                                      │
  │  [📋 Скопировать]  [📥 Скачать .txt]│
  │                                      │
  │  ☑ Я сохранил коды                  │
  │  [Готово]                            │
  │                                      │
  └──────────────────────────────────────┘
```

### Управление сессиями

```
URL: /security/sessions/

Завершить конкретную сессию:
  POST /security/sessions/{session_id}/terminate/
  
  Логика:
    1. Найти ActiveSession
    2. Удалить Django Session по session_key
    3. Удалить ActiveSession
    4. Сообщение "Сессия завершена"

Завершить все кроме текущей:
  POST /security/sessions/terminate-all/
  
  Логика:
    1. Получить текущий session_key из request
    2. Удалить все ActiveSession кроме текущей
    3. Удалить все Django Sessions кроме текущей
    4. Сообщение "Все сессии завершены"
```

### Смена пароля

```
URL: /security/change-password/

Если пароль ЕСТЬ:
  - Ввести текущий пароль
  - Ввести новый пароль
  - Подтвердить новый пароль
  - Валидация
  - При успехе: завершить все сессии кроме текущей
  - Уведомление на email

Если пароля НЕТ (OAuth пользователь):
  - Только новый пароль + подтверждение
  - При успехе: has_password() = True
```

### Привязка/отвязка аккаунтов

```
Привязать Google:
  POST /security/link/google/
  → OAuth поток → привязать LinkedAccount

Привязать Telegram:
  POST /security/link/telegram/
  → Telegram Widget → привязать LinkedAccount

Привязать телефон:
  POST /security/link/phone/
  → Ввод номера → SMS → подтверждение → привязать

Отвязать:
  POST /security/unlink/{provider}/
  Проверки:
    - Нельзя отвязать если это единственный способ входа
    - Нельзя отвязать если нет пароля и нет других способов
    - Запрос 2FA подтверждения перед отвязкой
```

### Настройки уведомлений

```
URL: /settings/notifications/

  ┌──────────────────────────────────────────────┐
  │  🔔 Настройки уведомлений                   │
  │                                              │
  │  На сайте (колокольчик):                    │
  │    ☑ Результаты ставок                      │
  │    ☑ Предупреждения безопасности            │
  │    ☑ Реферальная активность                 │
  │    ☑ Промо-акции                            │
  │                                              │
  │  Email:                                      │
  │    ☑ Результаты ставок                      │
  │    ☑ Предупреждения безопасности            │
  │    ☐ Реферальная активность                 │
  │    ☐ Промо-акции                            │
  │                                              │
  │  Telegram:                                   │
  │    Не подключён [Подключить]                │
  │    (или если подключён — те же чекбоксы)    │
  │                                              │
  │  [Сохранить]                                │
  │                                              │
  └──────────────────────────────────────────────┘

Сохраняется в User.notification_settings (JSONField).
HTMX: сохранение без перезагрузки.
```

### Критерий готовности шага 1.6

```
□ Страница профиля показывает все данные
□ Редактирование профиля работает
□ Загрузка аватара работает (ресайз до 256x256)
□ Страница безопасности работает
□ Смена пароля работает
□ Установка пароля (OAuth пользователи) работает
□ Настройка 2FA (TOTP) работает
□ Настройка 2FA (Email) работает
□ Генерация резервных кодов работает
□ Скачивание резервных кодов работает
□ Отключение 2FA работает (с подтверждением)
□ Привязка Google работает
□ Привязка Telegram работает
□ Привязка телефона работает
□ Отвязка с проверками работает
□ Просмотр активных сессий работает
□ Завершение конкретной сессии работает
□ Завершение всех сессий работает
□ История входов отображается
□ Настройки уведомлений работают
□ KYC страница (заглушка — подача документа)
□ Все страницы тёмная тема
□ HTMX для действий без перезагрузки
□ Мобильная адаптация
```

---

## 📊 ОБЩИЙ ЧЕКЛИСТ ЭТАПА 1

```
ФУНДАМЕНТ:
  □ Django проект создан и настроен
  □ Docker Compose: app, db, redis, celery
  □ PostgreSQL подключена
  □ Redis подключён
  □ Celery работает
  □ Настройки разделены (base/dev/prod)
  □ .env конфигурация

МОДЕЛИ:
  □ User (все 30+ полей)
  □ LoginHistory
  □ ActiveSession
  □ EmailVerification
  □ PhoneVerification
  □ BackupCode
  □ LinkedAccount

РЕГИСТРАЦИЯ:
  □ Через Email + пароль
  □ Через Google OAuth
  □ Через Telegram
  □ Через телефон (SMS)
  □ Подтверждение email
  □ Подтверждение телефона
  □ Реферальный код при регистрации
  □ Определение страны из IP

ВХОД:
  □ Email/телефон + пароль
  □ Google (один клик)
  □ Telegram
  □ SMS код (без пароля)
  □ 2FA: Google Authenticator
  □ 2FA: Email код
  □ Резервные коды
  □ Восстановление пароля
  □ "Запомнить меня"

БЕЗОПАСНОСТЬ:
  □ Rate limiting (логин, регистрация, SMS)
  □ Блокировка после 5 неудачных попыток
  □ Уведомление о новом устройстве
  □ История входов
  □ Управление сессиями
  □ CSRF защита
  □ Honeypot от ботов

ПРОФИЛЬ:
  □ Просмотр профиля
  □ Редактирование
  □ Загрузка аватара
  □ Смена пароля
  □ Настройка 2FA
  □ Привязка/отвязка аккаунтов
  □ Настройки уведомлений
  □ KYC заглушка

ИНТЕРФЕЙС:
  □ Тёмная тема DOD
  □ Navbar с балансом и меню
  □ Sidebar с навигацией
  □ Мобильная адаптация
  □ HTMX интерактивность
  □ Django messages стилизованы
  □ Страницы ошибок (404, 500, 403)

АДМИНКА:
  □ Все модели зарегистрированы
  □ Фильтры и поиск настроены
  □ Действия (блокировка, сброс 2FA)
```

---

```
╔══════════════════════════════════════════════════════╗
║                                                      ║
║   ЭТАП 1 ЗАВЕРШЁН                                   ║
║                                                      ║
║   Следующий: ЭТАП 2                                 ║
║   Профиль + KYC + Расширенная безопасность          ║
║                                                      ║
║   Продолжить?                                       ║
║                                                      ║
╚══════════════════════════════════════════════════════╝
```