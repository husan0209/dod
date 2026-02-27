

# 📋 ТЗ ПРОЕКТА DOD — ЭТАП 11

# TELEGRAM MINI APP

```
╔══════════════════════════════════════════════════════╗
║                                                      ║
║   ПРОЕКТ:    DOD                                    ║
║   ЭТАП:      11 из 12                               ║
║   НАЗВАНИЕ:  Telegram Mini App                      ║
║   ЗАВИСИТ:   Этапы 1-10 (полностью завершены)       ║
║   ЦЕЛЬ:      Полноценное мобильное приложение       ║
║              внутри Telegram: авторизация через      ║
║              initData, адаптивный UI, кошелёк,      ║
║              ставки, казино, predictions, поддержка, ║
║              push-уведомления через Telegram бот,   ║
║              интеграция с TON Connect, PWA fallback ║
║                                                      ║
╚══════════════════════════════════════════════════════╝
```

---

## 📌 КОНТЕКСТ ДЛЯ ИИ-АГЕНТА

```
Этапы 1-10 выполнены. У тебя есть:
  - Полная авторизация + 2FA + KYC
  - Мультивалютный кошелёк + платежи (NOWpayments, RUkassa)
  - Ставки на спорт (полный функционал)
  - Казино (Crash, Mines, Dice, Plinko, Roulette, Slots)
  - Prediction Market (AMM, торги, резолюция)
  - Партнёрская программа (реферальная система)
  - Чат поддержки + тикеты + FAQ + Telegram бот уведомлений
  - Полная админ-панель
  - Django Channels (WebSocket) настроен
  - Telegram бот уведомлений (из этапа 9) работает

В этом этапе ты строишь:
  1. Telegram Mini App (Web App внутри Telegram)
  2. Бесшовную авторизацию через Telegram initData
  3. Мобильный UI, адаптированный под WebView Telegram
  4. Доступ ко ВСЕМ основным функциям платформы
  5. Интеграцию с Telegram Payments / TON Connect
  6. Deeplinks и inline-режим бота

Telegram Mini App — это веб-приложение, которое
открывается внутри Telegram через WebView.
Пользователь НЕ покидает Telegram.
Авторизация проходит АВТОМАТИЧЕСКИ через initData.

Стек Mini App:
  - Backend: Django (существующий) + новые endpoint'ы
  - Frontend: HTMX + TailwindCSS (мобильный layout)
  - SDK: Telegram WebApp JS SDK (@twa-dev/sdk)
  - Транспорт: HTTPS обязательно (Telegram требует)
  - Channel Layer: Redis (для WebSocket в казино)

Bot API версия: 9.1+ (поддержка DeviceStorage,
SecureStorage, hideKeyboard)

Этот этап включает 6 шагов.
Каждый шаг — отдельная задача.
Выполняй строго по порядку.
```

---

## ШАГ 11.1 — TELEGRAM БОТ + ПРИЛОЖЕНИЕ + АВТОРИЗАЦИЯ

### Задача

```
Настрой Telegram бота через BotFather,
создай Django-приложение для Mini App,
реализуй безопасную авторизацию через initData
с автоматическим созданием/привязкой аккаунтов.
```

### Настройка бота (BotFather)

```
1. Создать бота (если ещё нет):
   /newbot → @DODPlatformBot

2. Настроить Mini App:
   /newapp → DOD Platform
   URL: https://yourdomain.com/tg/

3. Настроить меню бота:
   /setmenubutton →
     text: "🎮 Открыть DOD"
     url: https://yourdomain.com/tg/

4. Настроить домен:
   /setdomain → yourdomain.com

5. Описание бота:
   /setdescription →
   "DOD — ставки на спорт, казино и prediction market.
    Открой приложение через кнопку меню 👇"

6. Команды бота:
   /setcommands →
     start - Запустить приложение
     help - Помощь
     balance - Мой баланс
     deposit - Пополнить
     support - Поддержка
     settings - Настройки
     referral - Партнёрская ссылка

7. Inline режим:
   /setinline → включить
   placeholder: "Поделиться ставкой или маркетом..."

Переменные окружения (.env):
  TELEGRAM_BOT_TOKEN=7000000000:AAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
  TELEGRAM_BOT_USERNAME=DODPlatformBot
  TELEGRAM_WEBAPP_URL=https://yourdomain.com/tg/
  TELEGRAM_MINI_APP_SHORT_NAME=dod
```

### Структура приложения

```
apps/miniapp/
├── __init__.py
├── models.py
├── admin.py
├── views/
│   ├── __init__.py
│   ├── app.py              # Главная точка входа Mini App
│   ├── auth.py             # Авторизация через initData
│   ├── wallet.py           # Кошелёк (мобильный)
│   ├── sports.py           # Ставки (мобильный)
│   ├── casino.py           # Казино (мобильный)
│   ├── predictions.py      # Predictions (мобильный)
│   ├── profile.py          # Профиль (мобильный)
│   ├── support.py          # Поддержка (мобильный)
│   └── api.py              # API для Mini App (JSON)
├── urls.py
├── forms.py
├── middleware.py            # initData валидация middleware
├── decorators.py            # @require_telegram_auth
├── services/
│   ├── __init__.py
│   ├── auth_service.py      # Валидация initData + авторизация
│   ├── bot_service.py       # Логика Telegram бота
│   ├── deeplink_service.py  # Deeplinks и inline
│   ├── payment_service.py   # Telegram Payments / TON
│   └── notification_service.py  # Push через бота
├── bot/
│   ├── __init__.py
│   ├── handlers.py          # Обработчики команд бота
│   ├── keyboards.py         # Inline-клавиатуры
│   ├── callbacks.py         # Callback-обработчики
│   └── webhook.py           # Webhook endpoint
├── templatetags/
│   ├── __init__.py
│   └── miniapp_tags.py
├── templates/
│   └── miniapp/
│       ├── base.html         # Базовый layout (мобильный)
│       ├── app.html          # Главная страница
│       ├── auth/
│       │   ├── linking.html  # Привязка аккаунта
│       │   └── welcome.html  # Первый вход
│       ├── wallet/
│       ├── sports/
│       ├── casino/
│       ├── predictions/
│       ├── profile/
│       ├── support/
│       └── components/       # Переиспользуемые компоненты
│           ├── bottom_nav.html
│           ├── header.html
│           ├── card.html
│           ├── modal.html
│           └── loading.html
├── static/
│   └── miniapp/
│       ├── css/
│       │   └── miniapp.css   # Мобильные стили
│       ├── js/
│       │   ├── telegram.js   # WebApp SDK обёртка
│       │   ├── app.js        # Основная логика
│       │   ├── haptic.js     # Тактильная обратная связь
│       │   └── theme.js      # Адаптация под тему Telegram
│       └── img/
│           └── placeholder.svg
├── tests/
│   ├── __init__.py
│   ├── test_auth.py
│   ├── test_initdata.py
│   ├── test_bot.py
│   └── test_views.py
└── migrations/
    └── __init__.py
```

### Модель TelegramUser (Связь Telegram ↔ User)

```
class TelegramUser(models.Model):

    Назначение:
      Связь аккаунта Telegram с пользователем DOD.
      Хранит данные из initData и настройки Mini App.
      Один Telegram аккаунт = один пользователь DOD.

    Поля:
    ─────
    id:
      тип: AutoField, primary key

    user:
      тип: OneToOneField → User
      on_delete: CASCADE
      related_name: 'telegram_profile'
      Связанный пользователь DOD
      nullable: True (при первом запуске до привязки)

    # Telegram данные
    telegram_id:
      тип: BigIntegerField, уникальный
      ID пользователя в Telegram
      Неизменяемый

    username:
      тип: CharField, max 100, blank=True
      Username в Telegram (@username)
      Может меняться

    first_name:
      тип: CharField, max 200
      Имя в Telegram

    last_name:
      тип: CharField, max 200, blank=True
      Фамилия в Telegram

    photo_url:
      тип: URLField, blank=True
      Ссылка на аватар в Telegram

    language_code:
      тип: CharField, max 10, blank=True
      Язык Telegram клиента
      Пример: "ru", "en", "uz"

    is_premium:
      тип: BooleanField, default=False
      Telegram Premium подписка

    # Авторизация
    auth_date:
      тип: DateTimeField
      Дата последней авторизации через initData

    auth_hash:
      тип: CharField, max 64
      Последний валидный hash initData

    # Настройки Mini App
    theme_params:
      тип: JSONField, default=dict
      Параметры темы Telegram клиента
      {
        "bg_color": "#1a1a2e",
        "text_color": "#ffffff",
        "hint_color": "#999999",
        "link_color": "#00e701",
        "button_color": "#00e701",
        "button_text_color": "#ffffff",
        "secondary_bg_color": "#16213e"
      }

    # Статистика
    app_opens_count:
      тип: IntegerField, default=0
      Сколько раз открывал Mini App

    last_app_open:
      тип: DateTimeField, nullable
      Последний раз открывал

    total_time_spent:
      тип: IntegerField, default=0
      Время в Mini App (секунды)

    # Привязка
    account_linked_at:
      тип: DateTimeField, nullable
      Когда привязан к аккаунту DOD

    link_method:
      тип: CharField, max 20, blank=True
      choices:
        ('auto', 'Автоматически')
        ('email', 'Через email')
        ('phone', 'Через телефон')
        ('existing', 'Через существующий аккаунт')
        ('new', 'Новый аккаунт')

    # Уведомления через бота
    bot_notifications_enabled:
      тип: BooleanField, default=True
      Разрешил уведомления от бота

    notification_preferences:
      тип: JSONField, default=dict
      {
        "bets_results": true,
        "deposits": true,
        "withdrawals": true,
        "promotions": false,
        "market_resolved": true,
        "referral_activity": true,
        "security_alerts": true
      }

    # Реферал (deeplink)
    referred_by_deeplink:
      тип: CharField, max 100, blank=True
      Deeplink параметр при первом /start
      Пример: "ref_DOD-X7K9M2"

    # Мета
    device_info:
      тип: JSONField, default=dict
      {
        "platform": "android",
        "version": "10.8.3",
        "is_mobile": true
      }

    created_at:
      тип: DateTimeField, auto_now_add=True

    updated_at:
      тип: DateTimeField, auto_now=True

    Meta:
      verbose_name = 'Telegram пользователь'
      verbose_name_plural = 'Telegram пользователи'
      indexes:
        - telegram_id (unique)
        - user
        - created_at

    Методы:
      __str__():
        return f"TG:{self.telegram_id} → {self.user}"

      get_display_name():
        """Имя для отображения."""
        if self.user:
          return self.user.username
        return self.first_name or f"TG-{self.telegram_id}"

      is_linked():
        """Привязан ли к аккаунту DOD."""
        return self.user is not None

      update_from_initdata(data):
        """Обновить данные из initData."""
        self.username = data.get('username', '')
        self.first_name = data.get('first_name', '')
        self.last_name = data.get('last_name', '')
        self.photo_url = data.get('photo_url', '')
        self.language_code = data.get('language_code', '')
        self.is_premium = data.get('is_premium', False)
        self.auth_date = datetime.fromtimestamp(data['auth_date'])
        self.save()
```

### Модель MiniAppSession (Сессии Mini App)

```
class MiniAppSession(models.Model):

    Назначение:
      Отслеживание сессий Mini App.
      Для аналитики и безопасности.

    Поля:
    ─────
    id:
      тип: UUID, primary key

    telegram_user:
      тип: ForeignKey → TelegramUser
      on_delete: CASCADE
      related_name: 'sessions'

    # Данные сессии
    session_key:
      тип: CharField, max 64, уникальный
      Генерируется при каждом открытии

    init_data_hash:
      тип: CharField, max 64
      Hash для валидации

    # Платформа
    platform:
      тип: CharField, max 20
      choices:
        ('android', 'Android')
        ('ios', 'iOS')
        ('tdesktop', 'Desktop')
        ('web', 'Web Telegram')
        ('macos', 'macOS')
      Определяется из initData

    telegram_version:
      тип: CharField, max 20
      Версия Telegram клиента

    # Активность
    started_at:
      тип: DateTimeField, auto_now_add=True

    last_activity_at:
      тип: DateTimeField, auto_now=True

    ended_at:
      тип: DateTimeField, nullable

    duration_seconds:
      тип: IntegerField, default=0

    # Навигация
    pages_visited:
      тип: JSONField, default=list
      ["home", "casino/crash", "wallet", "sports"]

    actions_count:
      тип: IntegerField, default=0

    # Состояние
    is_active:
      тип: BooleanField, default=True

    Meta:
      verbose_name = 'Сессия Mini App'
      ordering = ['-started_at']
      indexes:
        - telegram_user + is_active
        - started_at
```

### Валидация initData (Безопасность)

```
# apps/miniapp/services/auth_service.py

import hmac
import hashlib
import json
import time
from urllib.parse import unquote, parse_qs
from django.conf import settings


class TelegramAuthService:
    """
    Сервис авторизации через Telegram initData.

    initData — строка, которую Telegram передаёт
    в WebApp при открытии Mini App.
    Содержит данные пользователя, подписанные
    токеном бота. ОБЯЗАТЕЛЬНО валидировать на сервере.

    Формат initData:
      query_id=AAHdF6IQAAAAAAN0Xog...
      &user={"id":123456,"first_name":"John",...}
      &auth_date=1234567890
      &hash=abc123def456...

    Алгоритм валидации:
      1. Разобрать initData на пары ключ=значение
      2. Убрать hash из набора
      3. Отсортировать пары по ключу
      4. Собрать строку "key=value\n..."
      5. Создать HMAC-SHA256:
         secret = HMAC-SHA256("WebAppData", BOT_TOKEN)
         hash = HMAC-SHA256(secret, data_check_string)
      6. Сравнить с полученным hash
      7. Проверить auth_date (не старше 1 часа)
    """

    MAX_AUTH_AGE_SECONDS = 3600  # 1 час

    @staticmethod
    def validate_init_data(init_data_raw: str) -> dict:
        """
        Валидация initData от Telegram.

        Args:
            init_data_raw: Строка initData из WebApp

        Returns:
            dict с данными пользователя

        Raises:
            ValueError: Если данные невалидны
        """
        if not init_data_raw:
            raise ValueError('initData пуста')

        # 1. Парсинг
        parsed = dict(
            pair.split('=', 1)
            for pair in unquote(init_data_raw).split('&')
        )

        # 2. Извлечь hash
        received_hash = parsed.pop('hash', None)
        if not received_hash:
            raise ValueError('hash отсутствует в initData')

        # 3. Сортировать и собрать строку
        data_check_pairs = sorted(parsed.items())
        data_check_string = '\n'.join(
            f'{k}={v}' for k, v in data_check_pairs
        )

        # 4. Вычислить HMAC
        secret_key = hmac.new(
            b'WebAppData',
            settings.TELEGRAM_BOT_TOKEN.encode(),
            hashlib.sha256
        ).digest()

        computed_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()

        # 5. Сравнить
        if not hmac.compare_digest(computed_hash, received_hash):
            raise ValueError('Невалидная подпись initData')

        # 6. Проверить auth_date
        auth_date = int(parsed.get('auth_date', 0))
        current_time = int(time.time())
        if current_time - auth_date > TelegramAuthService.MAX_AUTH_AGE_SECONDS:
            raise ValueError(
                'initData истекла '
                f'(возраст: {current_time - auth_date}s)'
            )

        # 7. Извлечь user
        user_data = json.loads(parsed.get('user', '{}'))
        if not user_data.get('id'):
            raise ValueError('ID пользователя отсутствует')

        return {
            'user': user_data,
            'query_id': parsed.get('query_id'),
            'auth_date': auth_date,
            'hash': received_hash,
        }

    @staticmethod
    def get_or_create_user(validated_data: dict):
        """
        Получить или создать пользователя DOD
        по данным из Telegram.

        Логика:
          1. Ищем TelegramUser по telegram_id
          2. Если найден и привязан → возвращаем User
          3. Если найден но НЕ привязан → пробуем привязать
          4. Если НЕ найден → создаём TelegramUser
             + автосоздаём User

        Автосоздание User:
          username = tg_{telegram_id}
          (можно поменять позже)
          email = не задан (потребуется позже для KYC)
          is_email_verified = False
          источник_регистрации = 'telegram'
        """
        tg_data = validated_data['user']
        telegram_id = tg_data['id']

        tg_user, created = TelegramUser.objects.get_or_create(
            telegram_id=telegram_id,
            defaults={
                'first_name': tg_data.get('first_name', ''),
                'last_name': tg_data.get('last_name', ''),
                'username': tg_data.get('username', ''),
                'photo_url': tg_data.get('photo_url', ''),
                'language_code': tg_data.get('language_code', ''),
                'is_premium': tg_data.get('is_premium', False),
                'auth_date': datetime.fromtimestamp(
                    validated_data['auth_date']
                ),
                'auth_hash': validated_data['hash'],
            }
        )

        if not created:
            # Обновить данные
            tg_user.update_from_initdata(tg_data)

        if tg_user.is_linked():
            # Уже привязан → вернуть пользователя
            return tg_user.user, tg_user, False

        # Автосоздание нового User
        from apps.accounts.models import User
        user = User.objects.create(
            username=f'tg_{telegram_id}',
            first_name=tg_data.get('first_name', ''),
            last_name=tg_data.get('last_name', ''),
            registration_method='telegram',
            preferred_language=(
                'ru' if tg_data.get('language_code') == 'ru'
                else 'en'
            ),
        )

        # Привязать
        tg_user.user = user
        tg_user.account_linked_at = now()
        tg_user.link_method = 'new'
        tg_user.save()

        # Создать кошелёк, партнёрский профиль и т.д.
        # (сигналы post_save User уже сделают это)

        # Обработать deeplink (реферальный код)
        if tg_user.referred_by_deeplink:
            process_referral_deeplink(
                user, tg_user.referred_by_deeplink
            )

        return user, tg_user, True  # True = новый


    @staticmethod
    def link_existing_account(tg_user, email, password):
        """
        Привязать Telegram к существующему аккаунту.
        Пользователь вводит email + пароль своего аккаунта.
        """
        from apps.accounts.models import User
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise ValueError('Аккаунт не найден')

        if not user.check_password(password):
            raise ValueError('Неверный пароль')

        if hasattr(user, 'telegram_profile'):
            raise ValueError(
                'К этому аккаунту уже привязан Telegram'
            )

        tg_user.user = user
        tg_user.account_linked_at = now()
        tg_user.link_method = 'existing'
        tg_user.save()

        return user
```

### Middleware для Mini App

```
# apps/miniapp/middleware.py

class TelegramMiniAppMiddleware:
    """
    Middleware для всех запросов к /tg/.
    Проверяет и валидирует initData.
    Автоматически авторизует пользователя.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.path.startswith('/tg/'):
            return self.get_response(request)

        # Получить initData
        init_data = (
            request.headers.get('X-Telegram-Init-Data')
            or request.GET.get('initData')
            or request.POST.get('initData')
        )

        request.is_telegram_miniapp = bool(init_data)
        request.telegram_user = None

        if init_data:
            try:
                validated = TelegramAuthService.validate_init_data(
                    init_data
                )
                user, tg_user, is_new = (
                    TelegramAuthService.get_or_create_user(validated)
                )

                # Авторизовать в Django
                if user and user.is_active:
                    login(request, user)
                    request.telegram_user = tg_user

                    # Обновить статистику
                    tg_user.app_opens_count += 1
                    tg_user.last_app_open = now()
                    tg_user.save(update_fields=[
                        'app_opens_count', 'last_app_open'
                    ])

                    # Создать сессию Mini App
                    MiniAppSession.objects.create(
                        telegram_user=tg_user,
                        session_key=generate_session_key(),
                        init_data_hash=validated['hash'],
                        platform=extract_platform(request),
                    )

            except ValueError as e:
                # Невалидные данные — не авторизуем
                logger.warning(
                    f'Invalid initData: {e}'
                )

        return self.get_response(request)
```

### Декоратор

```
# apps/miniapp/decorators.py

def require_telegram_auth(view_func):
    """
    Декоратор: только авторизованные через Telegram.

    Использование:
    @require_telegram_auth
    def my_view(request):
        tg_user = request.telegram_user
        ...
    """
    @functools.wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.is_telegram_miniapp:
            return JsonResponse(
                {'error': 'Доступно только из Telegram'},
                status=403
            )
        if not request.telegram_user:
            return JsonResponse(
                {'error': 'Авторизация не пройдена'},
                status=401
            )
        if not request.telegram_user.is_linked():
            return redirect('miniapp:link-account')

        return view_func(request, *args, **kwargs)
    return wrapper


def require_linked_account(view_func):
    """
    Требует привязанный аккаунт DOD.
    Если не привязан → редирект на привязку.
    """
    @functools.wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not hasattr(request, 'telegram_user'):
            return redirect('miniapp:home')
        if not request.telegram_user.is_linked():
            return redirect('miniapp:link-account')
        return view_func(request, *args, **kwargs)
    return wrapper
```

### URL конфигурация

```
# apps/miniapp/urls.py

app_name = 'miniapp'

urlpatterns = [
    # Главная
    path('', views.home, name='home'),

    # Авторизация
    path('auth/link/', views.link_account, name='link-account'),
    path('auth/link/existing/', views.link_existing,
         name='link-existing'),
    path('auth/welcome/', views.welcome, name='welcome'),

    # Кошелёк
    path('wallet/', views.wallet_home, name='wallet'),
    path('wallet/deposit/', views.wallet_deposit,
         name='wallet-deposit'),
    path('wallet/withdraw/', views.wallet_withdraw,
         name='wallet-withdraw'),
    path('wallet/history/', views.wallet_history,
         name='wallet-history'),
    path('wallet/convert/', views.wallet_convert,
         name='wallet-convert'),

    # Спорт
    path('sports/', views.sports_home, name='sports'),
    path('sports/<slug:sport>/', views.sports_events,
         name='sports-events'),
    path('sports/event/<uuid:event_id>/', views.sports_event,
         name='sports-event'),
    path('sports/bet/', views.sports_place_bet,
         name='sports-bet'),
    path('sports/my-bets/', views.sports_my_bets,
         name='sports-my-bets'),

    # Казино
    path('casino/', views.casino_home, name='casino'),
    path('casino/<slug:game>/', views.casino_game,
         name='casino-game'),

    # Predictions
    path('predictions/', views.predictions_home,
         name='predictions'),
    path('predictions/<uuid:market_id>/',
         views.predictions_market, name='predictions-market'),
    path('predictions/trade/', views.predictions_trade,
         name='predictions-trade'),
    path('predictions/portfolio/', views.predictions_portfolio,
         name='predictions-portfolio'),

    # Профиль
    path('profile/', views.profile_home, name='profile'),
    path('profile/edit/', views.profile_edit,
         name='profile-edit'),
    path('profile/referral/', views.profile_referral,
         name='profile-referral'),
    path('profile/settings/', views.profile_settings,
         name='profile-settings'),

    # Поддержка
    path('support/', views.support_home, name='support'),
    path('support/new/', views.support_new_ticket,
         name='support-new'),
    path('support/faq/', views.support_faq,
         name='support-faq'),

    # API (JSON для HTMX и JS)
    path('api/balance/', views.api_balance,
         name='api-balance'),
    path('api/notifications/', views.api_notifications,
         name='api-notifications'),
    path('api/theme/', views.api_theme, name='api-theme'),

    # Webhook бота
    path('bot/webhook/', views.bot_webhook,
         name='bot-webhook'),
]

# config/urls.py — добавить:
path('tg/', include('apps.miniapp.urls')),
```

### Критерий готовности шага 11.1

```
□ Бот создан и настроен через BotFather
□ Mini App зарегистрирован (/newapp)
□ apps/miniapp создано с полной структурой
□ Модель TelegramUser: все поля
□ Модель MiniAppSession: все поля
□ TelegramAuthService: validate_init_data() работает
□ TelegramAuthService: get_or_create_user() работает
□ TelegramAuthService: link_existing_account() работает
□ Middleware: автоматическая авторизация при /tg/
□ Декоратор @require_telegram_auth работает
□ Декоратор @require_linked_account работает
□ URL namespace /tg/ настроен
□ Webhook endpoint для бота
□ Deeplink обработка (/start ref_XXXXXX)
□ initData не старше 1 часа (защита от replay)
□ HMAC-SHA256 валидация корректна
□ Автосоздание User при первом входе через Telegram
□ Привязка существующего аккаунта через email+пароль
□ Миграции созданы и применены
```

---

## ШАГ 11.2 — МОБИЛЬНЫЙ UI + БАЗОВЫЙ LAYOUT

### Задача

```
Создай базовый мобильный layout Mini App:
навигация, тема из Telegram, компоненты,
тактильная обратная связь (haptic feedback),
адаптация под все платформы Telegram.
```

### Базовый шаблон (base.html)

```
# templates/miniapp/base.html

Структура:

  ┌──────────────────────────────────┐
  │  HEADER (фикс. сверху)          │
  │  ← Назад │ DOD │ 💰 $1,234 │ 🔔│
  ├──────────────────────────────────┤
  │                                  │
  │                                  │
  │  CONTENT AREA                    │
  │  (скроллируемый)                 │
  │                                  │
  │  {% block content %}             │
  │  {% endblock %}                  │
  │                                  │
  │                                  │
  │                                  │
  ├──────────────────────────────────┤
  │  BOTTOM NAV (фикс. снизу)       │
  │  🏠  ⚽  🎰  📊  👤            │
  │  Главная Спорт Казино Маркет Я  │
  └──────────────────────────────────┘

Важные правила:
  1. НЕ показывать стандартный навбар Telegram
     (WebApp SDK: Telegram.WebApp.expand())
  2. Использовать 100vh корректно
     (var(--tg-viewport-stable-height))
  3. safe-area-inset для бровки iPhone
  4. Нет горизонтального скролла
  5. Все элементы — touch-friendly (мин. 44×44px)
  6. Bottom nav скрывается при прокрутке вниз
  7. Анимации — 60fps, без тяжёлых эффектов

<head>:
  <!-- Telegram WebApp SDK -->
  <script
    src="https://telegram.org/js/telegram-web-app.js">
  </script>

  <!-- TailwindCSS CDN (для мобильных стилей) -->
  <script src="https://cdn.tailwindcss.com"></script>

  <!-- HTMX -->
  <script src="https://unpkg.com/htmx.org@2.0.0"></script>

  <!-- Кастомные стили -->
  <link rel="stylesheet" href="{% static 'miniapp/css/miniapp.css' %}">

  <meta name="viewport"
    content="width=device-width, initial-scale=1.0,
    maximum-scale=1.0, user-scalable=no">
```

### Интеграция с Telegram SDK

```
# static/miniapp/js/telegram.js

const tg = window.Telegram.WebApp;

// Инициализация при загрузке
document.addEventListener('DOMContentLoaded', () => {

  // 1. Развернуть на весь экран
  tg.expand();
  tg.isClosingConfirmationEnabled = true;

  // 2. Применить тему Telegram
  applyTelegramTheme();

  // 3. Настроить кнопку "Назад"
  tg.BackButton.onClick(() => {
    if (window.history.length > 1) {
      window.history.back();
    } else {
      tg.close();
    }
  });

  // 4. Отправить initData на сервер
  // (через заголовок в каждом HTMX запросе)
  document.body.setAttribute(
    'hx-headers',
    JSON.stringify({
      'X-Telegram-Init-Data': tg.initData,
      'X-CSRFToken': getCsrfToken(),
    })
  );

  // 5. Показать кнопку "Назад" если не главная
  updateBackButton();

  // 6. Настроить viewport
  tg.onEvent('viewportChanged', (event) => {
    document.documentElement.style.setProperty(
      '--tg-viewport-height',
      `${event.viewportHeight}px`
    );
  });

  // 7. DeviceStorage (Bot API 9.0+)
  // Для сохранения настроек пользователя на устройстве
  tg.DeviceStorage.getItem('preferred_tab', (err, val) => {
    if (val) navigateToTab(val);
  });
});


function applyTelegramTheme() {
  /**
   * Адаптация цветов под тему Telegram клиента.
   * Telegram передаёт theme_params с цветами.
   * Мы применяем их к CSS переменным.
   */
  const tp = tg.themeParams;
  const root = document.documentElement;

  root.style.setProperty('--tg-bg', tp.bg_color || '#1a1a2e');
  root.style.setProperty('--tg-text', tp.text_color || '#fff');
  root.style.setProperty('--tg-hint', tp.hint_color || '#999');
  root.style.setProperty('--tg-link', tp.link_color || '#00e701');
  root.style.setProperty('--tg-btn', tp.button_color || '#00e701');
  root.style.setProperty('--tg-btn-text',
    tp.button_text_color || '#fff');
  root.style.setProperty('--tg-secondary',
    tp.secondary_bg_color || '#16213e');
  root.style.setProperty('--tg-header',
    tp.header_bg_color || '#0f3460');
  root.style.setProperty('--tg-section',
    tp.section_bg_color || '#16213e');

  // Установить цвет шапки
  tg.setHeaderColor(tp.header_bg_color || '#0f3460');
  tg.setBackgroundColor(tp.bg_color || '#1a1a2e');
}


// Тактильная обратная связь (Haptic Feedback)
const haptic = {
  light: () => tg.HapticFeedback.impactOccurred('light'),
  medium: () => tg.HapticFeedback.impactOccurred('medium'),
  heavy: () => tg.HapticFeedback.impactOccurred('heavy'),
  success: () => tg.HapticFeedback.notificationOccurred('success'),
  warning: () => tg.HapticFeedback.notificationOccurred('warning'),
  error: () => tg.HapticFeedback.notificationOccurred('error'),
  select: () => tg.HapticFeedback.selectionChanged(),
};

// Использование:
// <button onclick="haptic.light(); placebet()">
//   Поставить
// </button>
```

### Bottom Navigation

```
# templates/miniapp/components/bottom_nav.html

  ┌──────────────────────────────────┐
  │  🏠       ⚽      🎰      📊   👤 │
  │ Главная  Спорт  Казино  Маркет  Я │
  └──────────────────────────────────┘

  Каждый таб:
    - Иконка (emoji или SVG)
    - Подпись (маленький текст)
    - Активный = цвет акцента (--tg-link)
    - Неактивный = серый (--tg-hint)
    - Бейджи: 🔴 3 (непрочитанные)
    - При нажатии: haptic.select()
    - Переход через HTMX (hx-get, hx-push-url)
    - Сохранять выбранный таб в DeviceStorage

  Высота: 60px + safe-area-inset-bottom
  Фон: var(--tg-secondary)
  Граница сверху: 1px solid rgba(255,255,255,0.1)
  Позиция: fixed bottom
```

### Header компонент

```
# templates/miniapp/components/header.html

  ┌──────────────────────────────────┐
  │  ← │ Заголовок │ 💰 $1,234 │ 🔔 │
  └──────────────────────────────────┘

  ← Кнопка назад:
    Показывается если не главная страница.
    Telegram BackButton синхронизирован.

  Заголовок:
    Название текущего раздела.
    Шрифт: 16px, bold.

  💰 Баланс:
    Основная валюта пользователя.
    Нажатие → переход в кошелёк.
    HTMX: обновляется каждые 10 секунд.
    hx-get="/tg/api/balance/"
    hx-trigger="every 10s"
    hx-swap="innerHTML"

  🔔 Уведомления:
    Бейдж с количеством непрочитанных.
    Нажатие → модалка с уведомлениями.

  Высота: 48px + safe-area-inset-top
  Фон: var(--tg-header)
  Позиция: fixed top
```

### CSS стили (miniapp.css)

```
# static/miniapp/css/miniapp.css

:root {
  /* Telegram тема (перезаписывается JS) */
  --tg-bg: #1a1a2e;
  --tg-text: #ffffff;
  --tg-hint: #999999;
  --tg-link: #00e701;
  --tg-btn: #00e701;
  --tg-btn-text: #ffffff;
  --tg-secondary: #16213e;
  --tg-header: #0f3460;
  --tg-section: #16213e;

  /* Размеры */
  --header-height: 48px;
  --bottom-nav-height: 60px;
  --safe-top: env(safe-area-inset-top, 0px);
  --safe-bottom: env(safe-area-inset-bottom, 0px);
}

* {
  -webkit-tap-highlight-color: transparent;
  -webkit-touch-callout: none;
  user-select: none;
}

body {
  background: var(--tg-bg);
  color: var(--tg-text);
  font-family: -apple-system, BlinkMacSystemFont,
    'Segoe UI', Roboto, sans-serif;
  margin: 0;
  padding: 0;
  overflow-x: hidden;
  -webkit-overflow-scrolling: touch;
}

.content-area {
  padding-top: calc(var(--header-height) + var(--safe-top));
  padding-bottom: calc(var(--bottom-nav-height) + var(--safe-bottom));
  min-height: 100vh;
  min-height: var(--tg-viewport-stable-height, 100vh);
}

/* Карточки */
.tg-card {
  background: var(--tg-section);
  border-radius: 12px;
  padding: 16px;
  margin: 8px 16px;
}

/* Кнопки */
.tg-btn {
  background: var(--tg-btn);
  color: var(--tg-btn-text);
  border: none;
  border-radius: 12px;
  padding: 14px 24px;
  font-size: 16px;
  font-weight: 600;
  width: 100%;
  min-height: 48px;
  cursor: pointer;
  transition: opacity 0.2s;
  -webkit-appearance: none;
}

.tg-btn:active {
  opacity: 0.7;
  transform: scale(0.98);
}

/* Списки */
.tg-list-item {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid rgba(255,255,255,0.06);
  min-height: 56px;
}

/* Pull-to-refresh */
.pull-to-refresh {
  text-align: center;
  padding: 10px;
  color: var(--tg-hint);
  font-size: 14px;
}

/* Скелетон загрузки */
.skeleton {
  background: linear-gradient(
    90deg,
    var(--tg-section) 25%,
    rgba(255,255,255,0.05) 50%,
    var(--tg-section) 75%
  );
  background-size: 200% 100%;
  animation: skeleton-loading 1.5s infinite;
  border-radius: 8px;
}

@keyframes skeleton-loading {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* Свайп-жесты */
.swipeable {
  touch-action: pan-y;
  overflow-x: hidden;
}

/* Модальное окно (снизу) */
.tg-modal-backdrop {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.5);
  z-index: 100;
  animation: fadeIn 0.2s;
}

.tg-modal {
  position: fixed;
  bottom: 0; left: 0; right: 0;
  background: var(--tg-secondary);
  border-radius: 16px 16px 0 0;
  padding: 16px;
  padding-bottom: calc(16px + var(--safe-bottom));
  z-index: 101;
  animation: slideUp 0.3s ease-out;
  max-height: 85vh;
  overflow-y: auto;
}

@keyframes slideUp {
  from { transform: translateY(100%); }
  to { transform: translateY(0); }
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}
```

### Главная страница Mini App

```
URL: /tg/
Доступ: @require_telegram_auth

  ┌──────────────────────────────────┐
  │  DOD          💰 $1,234.56  🔔(2)│
  ├──────────────────────────────────┤
  │                                  │
  │  Привет, Иван! 👋               │
  │                                  │
  │  ┌──────────────────────────┐   │
  │  │ 💰 Баланс               │   │
  │  │ $1,234.56                │   │
  │  │ [Пополнить] [Вывести]   │   │
  │  └──────────────────────────┘   │
  │                                  │
  │  ── 🔥 Быстрые действия ──────  │
  │                                  │
  │  ┌────┐ ┌────┐ ┌────┐ ┌────┐   │
  │  │ 🎰 │ │ ⚽ │ │ 📊 │ │ 🎲 │   │
  │  │Crash│ │Live│ │Мар.│ │Dice│   │
  │  └────┘ └────┘ └────┘ └────┘   │
  │                                  │
  │  ── ⚽ Live сейчас ────────────  │
  │                                  │
  │  ┌──────────────────────────┐   │
  │  │ 🟢 Реал Мадрид — Барса  │   │
  │  │    2 : 1  │ 67'         │   │
  │  │ 1: 2.10 │ X: 3.40│ 2: 3.80│ │
  │  └──────────────────────────┘   │
  │                                  │
  │  ┌──────────────────────────┐   │
  │  │ 🟢 МанСити — Ливерпуль  │   │
  │  │    0 : 0  │ 23'         │   │
  │  │ 1: 1.90 │ X: 3.60│ 2: 4.20│ │
  │  └──────────────────────────┘   │
  │                                  │
  │  ── 📊 Тренд маркеты ─────────  │
  │                                  │
  │  ┌──────────────────────────┐   │
  │  │ BTC > $150k к 01.06?    │   │
  │  │ ██████░░░░ YES 62%       │   │
  │  │ Объём: $45,678           │   │
  │  └──────────────────────────┘   │
  │                                  │
  │  ── 🏆 Топ выигрышей ─────────  │
  │                                  │
  │  🥇 player123  +$5,400 (Crash) │
  │  🥈 winner_x   +$3,200 (Slots) │
  │  🥉 lucky7     +$2,100 (Спорт) │
  │                                  │
  │  ── 🎁 Промо ─────────────────  │
  │  ┌──────────────────────────┐   │
  │  │ 🎉 Приветственный бонус  │   │
  │  │ 100% на первый депозит   │   │
  │  │ [Получить]               │   │
  │  └──────────────────────────┘   │
  │                                  │
  ├──────────────────────────────────┤
  │  🏠       ⚽      🎰     📊   👤│
  │ Главная  Спорт  Казино Маркет  Я│
  └──────────────────────────────────┘

HTMX:
  Live матчи обновляются каждые 30 сек
  hx-get="/tg/api/live-matches/"
  hx-trigger="every 30s"

  Баланс обновляется каждые 10 сек
```

### Критерий готовности шага 11.2

```
□ base.html: header + content + bottom nav
□ Telegram SDK инициализирован (expand, theme, backbutton)
□ CSS переменные из themeParams
□ Haptic feedback подключён
□ Bottom nav: 5 табов + бейджи + haptic
□ Header: назад + заголовок + баланс + уведомления
□ miniapp.css: все базовые компоненты
□ Кнопки 48px+, touch-friendly
□ Safe-area для iPhone (бровка)
□ Скелетон загрузки
□ Модальное окно снизу (bottom sheet)
□ Главная страница: все секции
□ HTMX: live обновления (матчи, баланс)
□ DeviceStorage: сохранение настроек
□ BackButton синхронизирован с историей
□ Нет горизонтального скролла
□ Все анимации 60fps
```

---

## ШАГ 11.3 — КОШЕЛЁК + СПОРТ + КАЗИНО (МОБИЛЬНЫЙ)

### Задача

```
Адаптируй кошелёк, ставки на спорт и казино
для мобильного Mini App. Оптимизированный UI,
touch-жесты, быстрые действия.
```

### Кошелёк (мобильный)

```
URL: /tg/wallet/
Доступ: @require_telegram_auth

  ┌──────────────────────────────────┐
  │  ← Кошелёк          💰 $1,234   │
  ├──────────────────────────────────┤
  │                                  │
  │       💰 $1,234.56              │
  │       Основной баланс            │
  │                                  │
  │  ┌──────┐ ┌──────┐ ┌──────┐    │
  │  │  ➕  │ │  ➖  │ │  🔄  │    │
  │  │Попол.│ │Вывод │ │Конвер│    │
  │  └──────┘ └──────┘ └──────┘    │
  │                                  │
  │  ── Мои валюты ────────────────  │
  │                                  │
  │  ┌──────────────────────────┐   │
  │  │ 🇺🇸 USD     $1,234.56   │   │
  │  │ ₿  BTC     0.01234     │   │
  │  │ 💎 USDT    $500.00      │   │
  │  │ 💎 TON     123.45       │   │
  │  │ 🇷🇺 RUB     ₽15,000     │   │
  │  └──────────────────────────┘   │
  │                                  │
  │  ── Последние операции ────────  │
  │                                  │
  │  ↓ +$100.00  Депозит    10:30  │
  │  ↑ -$50.00   Ставка     09:45  │
  │  ↓ +$210.00  Выигрыш    09:40  │
  │  ↑ -$300.00  Вывод ⏳   вчера  │
  │                                  │
  │  [Показать все →]               │
  │                                  │
  ├──────────────────────────────────┤
  │  🏠       ⚽      🎰     📊   👤│
  └──────────────────────────────────┘

Пополнение (/tg/wallet/deposit/):
  Bottom sheet (модалка снизу):

  ┌──────────────────────────────────┐
  │  ─── (ручка для свайпа)         │
  │                                  │
  │  ➕ Пополнить                    │
  │                                  │
  │  Валюта: [USD ▼]                │
  │  Сумма:  [$________]            │
  │                                  │
  │  Быстрые суммы:                  │
  │  [$10] [$25] [$50] [$100] [$500]│
  │                                  │
  │  Способ оплаты:                  │
  │  ○ 💳 Банковская карта (RUkassa)│
  │  ○ ₿  Криптовалюта (NOWpayments)│
  │  ○ 💎 TON (Telegram Payments)   │
  │                                  │
  │  [💰 Пополнить $50]             │
  │                                  │
  └──────────────────────────────────┘

  При выборе TON:
    Telegram Payments API:
    tg.openInvoice(invoiceUrl, (status) => {
      if (status === 'paid') {
        // Обновить баланс
        htmx.trigger('#balance', 'refresh');
        haptic.success();
        tg.showAlert('Баланс пополнен!');
      }
    });

  При выборе крипто / карты:
    Открыть URL в Telegram WebView:
    tg.openLink(paymentUrl, {try_instant_view: false});
```

### Ставки на спорт (мобильный)

```
URL: /tg/sports/
Доступ: @require_telegram_auth

  ┌──────────────────────────────────┐
  │  ← Спорт              🔍        │
  ├──────────────────────────────────┤
  │                                  │
  │  [⚽][🏀][🎾][🏒][🥊][🎮] ←→   │
  │  Горизонтальный список спортов   │
  │  (свайп влево/вправо)            │
  │                                  │
  │  [🔴 Live (5)] [Сегодня] [Завтра]│
  │                                  │
  │  ── 🔴 Live ───────────────────  │
  │                                  │
  │  ┌──────────────────────────┐   │
  │  │ ⚽ Ла Лига              │   │
  │  │ Реал Мадрид — Барселона │   │
  │  │ 2 : 1  │ 67'            │   │
  │  │                          │   │
  │  │ [1]     [X]     [2]     │   │
  │  │ [2.10]  [3.40]  [3.80]  │   │
  │  │                          │   │
  │  │ +24 исхода →             │   │
  │  └──────────────────────────┘   │
  │                                  │
  │  ── Сегодня ───────────────────  │
  │                                  │
  │  ⚽ Премьер-Лига                 │
  │  ┌──────────────────────────┐   │
  │  │ Арсенал — Челси  19:00  │   │
  │  │ [1.85]  [3.50]  [4.40]  │   │
  │  └──────────────────────────┘   │
  │                                  │
  │  ┌──────────────────────────┐   │
  │  │ МанЮн — Тоттенхэм 21:30│   │
  │  │ [2.20]  [3.30]  [3.50]  │   │
  │  └──────────────────────────┘   │
  │                                  │
  ├──────────────────────────────────┤
  │  🏠       ⚽      🎰     📊   👤│
  └──────────────────────────────────┘

Нажатие на коэффициент:
  1. haptic.medium()
  2. Коэффициент подсвечивается (акцент)
  3. Внизу появляется купон (slide up):

  ┌──────────────────────────────────┐
  │  ── Купон (1 ставка) ──────  ✕  │
  │                                  │
  │  Реал Мадрид — Барса             │
  │  Победа 1 │ коэфф: 2.10         │
  │                                  │
  │  Сумма: [$_________]             │
  │  [$5] [$10] [$25] [$50] [ALL]   │
  │                                  │
  │  Возможный выигрыш: $105.00     │
  │                                  │
  │  [⚡ Поставить $50 →]            │
  │                                  │
  └──────────────────────────────────┘

  При нажатии «Поставить»:
    haptic.heavy()
    HTMX POST → /tg/sports/bet/
    Успех → haptic.success() + popup
    Ошибка → haptic.error() + tg.showAlert()
```

### Казино (мобильный)

```
URL: /tg/casino/
Доступ: @require_telegram_auth

  ┌──────────────────────────────────┐
  │  ← Казино              💰$1,234 │
  ├──────────────────────────────────┤
  │                                  │
  │  ── Наши игры ─────────────────  │
  │                                  │
  │  ┌────────┐ ┌────────┐         │
  │  │  🚀    │ │  💣    │         │
  │  │ CRASH  │ │ MINES  │         │
  │  │ x2.34  │ │        │         │
  │  └────────┘ └────────┘         │
  │                                  │
  │  ┌────────┐ ┌────────┐         │
  │  │  🎲    │ │  📍    │         │
  │  │ DICE   │ │ PLINKO │         │
  │  │        │ │        │         │
  │  └────────┘ └────────┘         │
  │                                  │
  │  ┌────────┐ ┌────────┐         │
  │  │  🎡    │ │  🎰    │         │
  │  │ROULET. │ │ SLOTS  │         │
  │  │        │ │        │         │
  │  └────────┘ └────────┘         │
  │                                  │
  │  ── 🏆 Последние выигрыши ────  │
  │                                  │
  │  🥇 player1  +$5,400  Crash    │
  │  🥈 winner   +$3,200  Slots    │
  │  🥉 lucky    +$2,100  Mines    │
  │                                  │
  │  [Показать все →]               │
  │                                  │
  ├──────────────────────────────────┤
  │  🏠       ⚽      🎰     📊   👤│
  └──────────────────────────────────┘

Открытие игры (/tg/casino/crash/):
  Полноэкранный режим.
  Скрыть header и bottom nav.
  Кнопка выхода [✕] в углу.

  Crash в Mini App:
    WebSocket через Django Channels.
    Адаптированный UI для мобильных.
    Кнопки ставки: минимум 56px высота.
    Анимация графика — canvas или SVG.
    Haptic при краше: haptic.heavy()
    Haptic при выигрыше: haptic.success()

  Mines в Mini App:
    Сетка 5×5 с увеличенными ячейками.
    Нажатие на ячейку: haptic.light()
    Мина: haptic.error() + вибрация
    Выигрыш: haptic.success()

  Общие правила для всех игр:
    - Полноэкранный режим
    - Ландшафтная ориентация НЕ поддерживается
    - Все кнопки touch-friendly
    - Минимум текста, максимум визуала
    - Быстрый выбор суммы ставки
    - Провабли Fair доступна из меню (⋮)
```

### Критерий готовности шага 11.3

```
□ Кошелёк: баланс, список валют, история
□ Кошелёк: пополнение (карта, крипто, TON)
□ Кошелёк: вывод (bottom sheet)
□ Кошелёк: конвертация валют
□ Telegram Payments: openInvoice для TON
□ Спорт: список спортов (горизонтальный свайп)
□ Спорт: live матчи с обновлением каждые 30s
□ Спорт: детали матча с исходами
□ Спорт: купон (slide-up, быстрые суммы)
□ Спорт: размещение ставки (HTMX POST)
□ Спорт: haptic feedback при ставке
□ Казино: сетка игр (2 колонки)
□ Казино: полноэкранный режим для игры
□ Казино: WebSocket для Crash
□ Казино: все игры адаптированы для мобильных
□ Казино: haptic при событиях (краш, выигрыш)
□ tg.showAlert для результатов
□ Все кнопки ≥ 48px
```

---

## ШАГ 11.4 — PREDICTIONS + ПРОФИЛЬ + ПОДДЕРЖКА

### Задача

```
Адаптируй маркеты предсказаний, профиль
пользователя и поддержку для Mini App.
Реферальный шеринг через Telegram.
```

### Predictions (мобильный)

```
URL: /tg/predictions/
Доступ: @require_telegram_auth

  ┌──────────────────────────────────┐
  │  ← Маркеты             💰$1,234 │
  ├──────────────────────────────────┤
  │                                  │
  │  [🔥Тренд] [🆕Новые] [⏰Скоро]  │
  │  [🏆Резолв] [📂Мои]             │
  │                                  │
  │  Категории:                      │
  │  [🌐Все][💹Крипто][🏛️Полит]    │
  │  [⚽Спорт][🎬Шоу][🔬Наука]     │
  │                                  │
  │  ── 🔥 Тренд маркеты ─────────  │
  │                                  │
  │  ┌──────────────────────────┐   │
  │  │ 📊 BTC > $150k к 01.06?  │   │
  │  │                          │   │
  │  │ YES ████████░░ 78%       │   │
  │  │ NO  ██░░░░░░░░ 22%       │   │
  │  │                          │   │
  │  │ 💰 Объём: $45,678        │   │
  │  │ ⏰ До закрытия: 12 дней  │   │
  │  │                          │   │
  │  │ [Купить YES $0.78]       │   │
  │  │ [Купить NO  $0.22]       │   │
  │  └──────────────────────────┘   │
  │                                  │
  │  ┌──────────────────────────┐   │
  │  │ 🏛️ Трамп выиграет 2028?  │   │
  │  │ YES ██████░░░░ 55%       │   │
  │  │ 💰 $23,456 │ ⏰ 2 мес    │   │
  │  └──────────────────────────┘   │
  │                                  │
  ├──────────────────────────────────┤
  │  🏠       ⚽      🎰     📊   👤│
  └──────────────────────────────────┘

Нажатие на маркет → детали:

  ┌──────────────────────────────────┐
  │  ← BTC > $150k к 01.06?         │
  ├──────────────────────────────────┤
  │                                  │
  │  📊 График цены YES/NO          │
  │  ╱──╲    ╱──                    │
  │ ╱    ╲──╱                       │
  │  [1Д] [1Н] [1М] [Всё]          │
  │                                  │
  │  ── Торговля ──────────────────  │
  │                                  │
  │  [YES $0.78] ← → [NO $0.22]    │
  │                                  │
  │  Сумма: [$_________]             │
  │  [$5] [$10] [$25] [$50]         │
  │                                  │
  │  Вы получите: ~12.8 долей       │
  │  Макс. выигрыш: $12.80          │
  │                                  │
  │  [⚡ Купить YES $10 →]           │
  │                                  │
  │  ── Моя позиция ───────────────  │
  │  YES: 25.4 долей (ср.цена $0.65)│
  │  Инвестировано: $16.51           │
  │  Текущая стоим.: $19.81          │
  │  P&L: +$3.30 (+20.0%)  🟢      │
  │  [Продать всё]                   │
  │                                  │
  │  ── 📋 Описание ───────────────  │
  │  Разрешится по цене BTC на       │
  │  бирже Binance...                │
  │                                  │
  │  ── 💬 Комментарии (23) ────── │
  │  [Загрузить комментарии →]       │
  │                                  │
  │  ── 📊 Статистика ─────────────  │
  │  Участников: 456                 │
  │  Сделок: 1,234                   │
  │  Объём: $45,678                  │
  │  Создан: 01.03.2025              │
  │  Закрытие: 01.06.2025            │
  │                                  │
  │  ── 🔗 Поделиться ─────────────  │
  │  [📤 Отправить другу]            │
  │                                  │
  └──────────────────────────────────┘

Кнопка «Отправить другу»:
  tg.switchInlineQuery(
    'market_UUID_SHORT',
    ['users', 'groups', 'channels']
  );
  → Отправляет inline-сообщение с карточкой маркета
```

### Профиль и реферальная программа

```
URL: /tg/profile/
Доступ: @require_telegram_auth

  ┌──────────────────────────────────┐
  │  ← Профиль                      │
  ├──────────────────────────────────┤
  │                                  │
  │       [АВАТАР]                   │
  │      Ivan Petrov                 │
  │      @username123                │
  │      🟢 TG Premium              │
  │                                  │
  │  ┌──────────────────────────┐   │
  │  │ 💰 Баланс    $1,234.56  │   │
  │  │ 📊 Ставки    342        │   │
  │  │ 🏆 Побед     168 (49%)  │   │
  │  │ 📈 Прибыль   +$456      │   │
  │  └──────────────────────────┘   │
  │                                  │
  │  ── Меню ──────────────────────  │
  │                                  │
  │  [💰 Кошелёк                 →] │
  │  [📜 История ставок          →] │
  │  [📊 Мои позиции (Маркеты)  →] │
  │  [🤝 Партнёрская программа  →] │
  │  [🎧 Поддержка              →] │
  │  [❓ FAQ                     →] │
  │  [⚙️ Настройки               →] │
  │  [🔗 Привязать аккаунт      →] │
  │                                  │
  ├──────────────────────────────────┤
  │  🏠       ⚽      🎰     📊   👤│
  └──────────────────────────────────┘

Партнёрская (/tg/profile/referral/):

  ┌──────────────────────────────────┐
  │  ← Партнёрская программа        │
  ├──────────────────────────────────┤
  │                                  │
  │  🥈 Продвинутый партнёр          │
  │  Комиссия: 40% от GGR           │
  │                                  │
  │  ┌──────────────────────────┐   │
  │  │ 💰 Баланс   $234.56     │   │
  │  │ 👥 Рефералы  23          │   │
  │  │ 📊 Доход     $890.12    │   │
  │  │ [Вывести на баланс →]    │   │
  │  └──────────────────────────┘   │
  │                                  │
  │  ── Твоя ссылка ───────────────  │
  │  ┌──────────────────────────┐   │
  │  │ t.me/DODPlatformBot?     │   │
  │  │ start=ref_DOD-X7K9M2     │   │
  │  │ [📋 Копировать]          │   │
  │  │ [📤 Поделиться]          │   │
  │  └──────────────────────────┘   │
  │                                  │
  │  «Поделиться» использует:        │
  │  tg.switchInlineQuery(           │
  │    'ref_DOD-X7K9M2',            │
  │    ['users', 'groups']           │
  │  );                              │
  │                                  │
  └──────────────────────────────────┘

Настройки (/tg/profile/settings/):
  - Язык (RU / EN)
  - Валюта отображения
  - Уведомления через бота (вкл/выкл каждый тип)
  - Привязка email / телефона
  - Привязка к существующему аккаунту
```

### Поддержка (мобильный)

```
URL: /tg/support/
Доступ: @require_telegram_auth

  ┌──────────────────────────────────┐
  │  ← Поддержка                    │
  ├──────────────────────────────────┤
  │                                  │
  │  ── Быстрые действия ─────────  │
  │                                  │
  │  ┌────────────┐ ┌────────────┐ │
  │  │ 💬 Новый   │ │ ❓ FAQ     │ │
  │  │   тикет    │ │            │ │
  │  └────────────┘ └────────────┘ │
  │                                  │
  │  ── Мои обращения ─────────────  │
  │                                  │
  │  ┌──────────────────────────┐   │
  │  │ 🟢 DOD-20250320-0042    │   │
  │  │ Задержка вывода USDT     │   │
  │  │ В работе │ 3 часа назад  │   │
  │  └──────────────────────────┘   │
  │                                  │
  │  ┌──────────────────────────┐   │
  │  │ ✅ DOD-20250319-0038    │   │
  │  │ Вопрос по KYC            │   │
  │  │ Решён │ вчера            │   │
  │  └──────────────────────────┘   │
  │                                  │
  ├──────────────────────────────────┤
  │  🏠       ⚽      🎰     📊   👤│
  └──────────────────────────────────┘

Новый тикет:
  Bottom sheet с формой:
  - Категория (выпадающий)
  - Тема (текст)
  - Описание (textarea)
  - Прикрепить фото (камера / галерея)
  - [Отправить]

  Фото через:
  tg.showScanQrPopup() — для QR
  <input type="file" accept="image/*" capture>
```

### Критерий готовности шага 11.4

```
□ Predictions: список маркетов с фильтрами
□ Predictions: детали маркета (график, торговля)
□ Predictions: покупка/продажа долей (HTMX)
□ Predictions: моя позиция + P&L
□ Predictions: поделиться (switchInlineQuery)
□ Профиль: аватар, статистика, меню
□ Профиль: редактирование
□ Партнёрка: статистика, ссылка, шеринг
□ Поддержка: список тикетов
□ Поддержка: создание тикета (bottom sheet)
□ Поддержка: прикрепление файлов
□ FAQ: поиск и отображение
□ Настройки: язык, валюта, уведомления
□ Привязка аккаунта (email/телефон)
```

---

## ШАГ 11.5 — TELEGRAM БОТ (КОМАНДЫ + INLINE + DEEPLINKS)

### Задача

```
Реализуй полноценного Telegram бота:
команды, inline-режим, deeplinks,
webhook, клавиатуры, callback-обработчики.
```

### Обработчики команд бота

```
# apps/miniapp/bot/handlers.py

/start:
  Параметр: /start ref_DOD-X7K9M2
  1. Сохранить deeplink для реферала
  2. Приветственное сообщение:

  ── Сообщение ──
  🎮 Добро пожаловать в DOD!

  Ставки на спорт ⚽ | Казино 🎰
  Маркеты предсказаний 📊

  👇 Нажми кнопку ниже чтобы начать!
  ── Клавиатура ──
  [🎮 Открыть DOD] (webapp_url)


/balance:
  ── Сообщение ──
  💰 Ваш баланс:

  🇺🇸 USD: $1,234.56
  ₿ BTC: 0.01234
  💎 USDT: $500.00

  [🎮 Открыть кошелёк] (webapp_url/wallet)
  [➕ Пополнить] (webapp_url/wallet/deposit)


/deposit:
  Inline-кнопка → открывает Mini App на /wallet/deposit


/referral:
  ── Сообщение ──
  🤝 Партнёрская программа

  Твоя ссылка:
  t.me/DODPlatformBot?start=ref_DOD-X7K9M2

  👥 Рефералов: 23
  💰 Заработано: $890.12

  [📋 Копировать ссылку] (callback)
  [📤 Поделиться] (switch_inline_query)
  [📊 Подробная статистика] (webapp_url/referral)


/support:
  ── Сообщение ──
  🎧 Поддержка DOD

  Выберите действие:

  [💬 Создать тикет] (webapp_url/support/new)
  [📋 Мои тикеты] (webapp_url/support)
  [❓ FAQ] (webapp_url/support/faq)


/settings:
  ── Сообщение ──
  ⚙️ Настройки уведомлений:

  ✅ Результаты ставок
  ✅ Депозиты
  ✅ Выводы
  ❌ Промо-акции
  ✅ Резолюция маркетов
  ✅ Реферальная активность
  ✅ Безопасность

  [Изменить настройки] (webapp_url/settings)


/help:
  Список команд и описание
```

### Inline-режим

```
Inline бот позволяет пользователям делиться
контентом из DOD прямо в чатах Telegram.

Активация: @DODPlatformBot <запрос>

Типы inline-результатов:

1. Реферальная ссылка:
   @DODPlatformBot ref
   →
   ┌──────────────────────────────┐
   │  🎮 DOD — Ставки и Казино   │
   │                              │
   │  Присоединяйся к DOD!       │
   │  Ставки на спорт ⚽          │
   │  Казино 🎰 | Predictions 📊 │
   │                              │
   │  [🎮 Открыть DOD]           │
   └──────────────────────────────┘

2. Маркет предсказаний:
   @DODPlatformBot market <search>
   →
   ┌──────────────────────────────┐
   │  📊 BTC > $150k к 01.06?    │
   │  YES: 78% │ NO: 22%         │
   │  Объём: $45,678              │
   │  [📊 Торговать]              │
   └──────────────────────────────┘

3. Матч:
   @DODPlatformBot match <search>
   →
   ┌──────────────────────────────┐
   │  ⚽ Реал Мадрид — Барселона  │
   │  Сегодня 21:00              │
   │  1: 2.10 │ X: 3.40│ 2: 3.80│
   │  [⚽ Сделать ставку]        │
   └──────────────────────────────┘
```

### Deeplinks

```
Формат deeplinks:

  t.me/DODPlatformBot?startapp=<payload>

Типы payload:

  ref_DOD-X7K9M2
    → Реферальная ссылка
    → Открыть Mini App + привязать реферала

  market_<uuid_short>
    → Открыть конкретный маркет

  match_<event_id>
    → Открыть конкретный матч

  game_crash
    → Открыть игру Crash

  deposit
    → Открыть пополнение

  wallet
    → Открыть кошелёк

Обработка deeplink в Mini App:
  1. tg.initDataUnsafe.start_param содержит payload
  2. Middleware парсит и редиректит на нужную страницу
  3. Если ref_ → сохраняет в TelegramUser.referred_by_deeplink
```

### Webhook

```
# apps/miniapp/bot/webhook.py

URL: /tg/bot/webhook/
Метод: POST
Проверка: X-Telegram-Bot-Api-Secret-Token

Настройка webhook:
  POST https://api.telegram.org/bot<TOKEN>/setWebhook
  {
    "url": "https://yourdomain.com/tg/bot/webhook/",
    "secret_token": "<RANDOM_SECRET>",
    "allowed_updates": [
      "message", "callback_query",
      "inline_query", "chosen_inline_result"
    ]
  }

Обработка:
  1. Проверить secret_token
  2. Определить тип update
  3. Вызвать соответствующий handler
  4. Вернуть 200 OK (всегда, даже при ошибке)
```

### Критерий готовности шага 11.5

```
□ Webhook настроен и принимает updates
□ /start: приветствие + deeplink обработка
□ /balance: показ баланса
□ /deposit: ссылка на пополнение
□ /referral: ссылка + статистика + шеринг
□ /support: ссылки на поддержку
□ /settings: настройки уведомлений
□ /help: список команд
□ Inline: реферальная ссылка
□ Inline: маркеты предсказаний
□ Inline: матчи
□ Deeplinks: ref, market, match, game, deposit
□ Callback-обработчики для inline-кнопок
□ Secret token проверяется
□ Ошибки не ломают webhook (всегда 200)
```

---

## ШАГ 11.6 — УВЕДОМЛЕНИЯ + АНАЛИТИКА + PWA

### Задача

```
Push-уведомления через бота, аналитика
Mini App в админке, PWA fallback для
пользователей без Telegram.
```

### Push-уведомления через бота

```
# apps/miniapp/services/notification_service.py

class TelegramNotificationService:
    """
    Отправка уведомлений пользователям через бота.
    Интегрируется с NotificationService из этапа 9.
    """

    Типы уведомлений:

    1. Результат ставки:
       ── Сообщение ──
       ⚽ Ставка завершена!

       Реал Мадрид — Барселона
       Ваша ставка: Победа 1 (коэфф. 2.10)
       Сумма: $50.00

       🏆 Результат: ВЫИГРЫШ!
       💰 Выигрыш: $105.00

       [📊 Детали] [🎮 Новая ставка]

    2. Маркет резолвлен:
       ── Сообщение ──
       📊 Маркет резолвлен!

       BTC > $150k к 01.06?
       Результат: ✅ YES

       Ваша позиция: 25.4 долей YES
       💰 Выигрыш: $25.40

       [📊 Детали]

    3. Депозит / Вывод:
       ── Сообщение ──
       ✅ Вывод одобрен!

       Сумма: $300.00 (USDT TRC20)
       Адрес: TXxx...xxx
       Статус: Обработан

    4. Безопасность:
       ── Сообщение ──
       ⚠️ Вход с нового устройства!

       Устройство: iPhone 15, Safari
       IP: 95.161.xx.xx (Москва)
       Время: 10:30 МСК

       Это вы? [✅ Да] [❌ Нет, заблокировать]

    5. Реферал:
       ── Сообщение ──
       🤝 Новый реферал!

       Пользователь зарегистрировался
       по вашей ссылке.
       Всего рефералов: 24

    Настройки:
      Каждый тип уведомления можно вкл/выкл.
      Хранится в TelegramUser.notification_preferences.

    Рассылка:
      НЕ спамить. Максимум 5 сообщений в час.
      Группировать: если 3 ставки выиграли →
      одно сообщение с итогом.
```

### Аналитика Mini App (в админке)

```
URL: /admin-panel/analytics/miniapp/
Доступ: @require_permission('analytics', 'view_dashboard')

Метрики:

  ┌──────────────────────────────────────────┐
  │ 📱 Аналитика Mini App                    │
  │                                          │
  │ ── Сегодня ──────────────────────────── │
  │ Открытий: 1,234                          │
  │ Уникальных: 567                          │
  │ Новых: 89                                │
  │ Ставок через Mini App: 234 ($12,345)     │
  │ Среднее время сессии: 4:32               │
  │                                          │
  │ ── Платформы ────────────────────────── │
  │ Android: 45% │ iOS: 40% │ Desktop: 15% │
  │                                          │
  │ ── Воронка ──────────────────────────── │
  │ Открыл Mini App: 567                     │
  │ → Авторизовался: 567 (100%)             │
  │ → Посетил кошелёк: 234 (41%)            │
  │ → Сделал депозит: 45 (8%)               │
  │ → Сделал ставку: 89 (16%)               │
  │                                          │
  │ ── Популярные разделы ─────────────── │
  │ 1. Казино (Crash): 340 заходов           │
  │ 2. Спорт: 280 заходов                    │
  │ 3. Predictions: 190 заходов              │
  │ 4. Кошелёк: 150 заходов                  │
  │                                          │
  │ ── Реферальный трафик ────────────── │
  │ Переходов по deeplink: 456               │
  │ Регистраций: 89                          │
  │ Конверсия: 19.5%                         │
  └──────────────────────────────────────────┘
```

### PWA Fallback

```
Для пользователей, которые хотят использовать
платформу без Telegram (или на десктопе),
предоставляем PWA (Progressive Web App).

# static/miniapp/manifest.json
{
  "name": "DOD Platform",
  "short_name": "DOD",
  "description": "Ставки, казино и маркеты предсказаний",
  "start_url": "/tg/",
  "display": "standalone",
  "background_color": "#1a1a2e",
  "theme_color": "#00e701",
  "orientation": "portrait",
  "icons": [
    {
      "src": "/static/miniapp/img/icon-192.png",
      "sizes": "192x192",
      "type": "image/png"
    },
    {
      "src": "/static/miniapp/img/icon-512.png",
      "sizes": "512x512",
      "type": "image/png"
    }
  ]
}

Service Worker:
  - Кэширование статики (CSS, JS, шрифты)
  - Offline страница (при отсутствии сети)
  - Фоновая синхронизация
  - НЕ кэшировать API ответы (баланс, ставки)

Если открыт НЕ из Telegram:
  - initData не будет
  - Middleware перенаправит на обычный логин
  - UI остаётся мобильным (тот же layout)
  - Haptic feedback деградирует gracefully
  - Вместо tg.showAlert → стандартный alert
```

### Celery задачи

```
# apps/miniapp/tasks.py

# Каждые 5 минут
update_miniapp_analytics():
  """Обновить метрики Mini App в Redis."""

# Каждый час
cleanup_expired_sessions():
  """Закрыть неактивные сессии Mini App (> 30 мин)."""

# Ежедневно
send_daily_digest():
  """
  Отправить дайджест активным пользователям:
  - Результаты ставок за день
  - Новые интересные маркеты
  - Топ выигрышей
  Только тем у кого включены уведомления.
  """

generate_miniapp_report():
  """Отчёт по Mini App для админов."""

sync_telegram_user_data():
  """
  Синхронизировать данные Telegram пользователей:
  - Обновить username (мог измениться)
  - Обновить premium статус
  - Пометить неактивных (> 30 дней)
  """
```

### Критерий готовности шага 11.6

```
□ Уведомления: результат ставки
□ Уведомления: маркет резолвлен
□ Уведомления: депозит/вывод
□ Уведомления: безопасность
□ Уведомления: реферал
□ Уведомления: настройки (вкл/выкл каждый тип)
□ Лимит: максимум 5 сообщений в час
□ Группировка уведомлений
□ Аналитика Mini App в админке
□ Воронка: открыл → авторизовался → ставка
□ PWA: manifest.json
□ PWA: Service Worker (кэш статики, offline)
□ PWA: fallback для не-Telegram
□ Celery: аналитика, cleanup, дайджест
□ Celery: синхронизация данных TG
```

---

## 📊 ОБЩИЙ ЧЕКЛИСТ ЭТАПА 11

```
БОТА И АВТОРИЗАЦИЯ:
  □ Бот создан и настроен (BotFather)
  □ Mini App зарегистрирован
  □ initData валидация (HMAC-SHA256)
  □ Автосоздание пользователя при первом входе
  □ Привязка к существующему аккаунту
  □ Модель TelegramUser (все поля)
  □ Модель MiniAppSession (сессии)
  □ Middleware автоматической авторизации
  □ Декораторы @require_telegram_auth
  □ Deeplink обработка (ref, market, game)

МОБИЛЬНЫЙ UI:
  □ base.html: header + content + bottom nav
  □ Telegram SDK: expand, theme, backbutton
  □ CSS переменные из themeParams
  □ Haptic feedback (на все действия)
  □ Bottom nav: 5 табов + бейджи
  □ Safe-area (iPhone бровка)
  □ Скелетон загрузки
  □ Bottom sheet модалки
  □ Touch-friendly (все кнопки ≥ 48px)
  □ 60fps анимации

ФУНКЦИОНАЛЬНОСТЬ:
  □ Главная: баланс, live, тренды, промо
  □ Кошелёк: баланс, валюты, пополнение, вывод
  □ Telegram Payments (TON)
  □ Спорт: список, live, ставки, купон
  □ Казино: все игры, полноэкранный режим
  □ Predictions: маркеты, торговля, портфель
  □ Профиль: статистика, настройки
  □ Партнёрка: ссылка, статистика, шеринг
  □ Поддержка: тикеты, FAQ

TELEGRAM БОТ:
  □ Webhook (POST + secret token)
  □ Команды: /start, /balance, /deposit, /referral,
    /support, /settings, /help
  □ Inline-режим (реф.ссылка, маркеты, матчи)
  □ Deeplinks (ref, market, match, game)
  □ Callback-обработчики

УВЕДОМЛЕНИЯ:
  □ Результат ставки
  □ Маркет резолвлен
  □ Депозит / вывод
  □ Безопасность (новый вход)
  □ Реферал
  □ Настройки уведомлений (вкл/выкл)
  □ Лимит 5 сообщений/час
  □ Группировка

АНАЛИТИКА:
  □ Mini App метрики в админке
  □ Воронка конверсий
  □ Популярные разделы
  □ Платформы (Android/iOS/Desktop)

PWA:
  □ manifest.json
  □ Service Worker
  □ Offline страница
  □ Fallback для не-Telegram

CELERY:
  □ Аналитика Mini App (5 мин)
  □ Cleanup сессий (1 час)
  □ Daily digest (ежедневно)
  □ Отчёт Mini App (ежедневно)
  □ Синхронизация TG данных (ежедневно)
```

---

```
╔══════════════════════════════════════════════════════╗
║                                                      ║
║   ЭТАП 11 ЗАВЕРШЁН                                  ║
║                                                      ║
║   Следующий: ЭТАП 12                                ║
║   Деплой + Тестирование + Запуск                    ║
║                                                      ║
║   Продолжить?                                       ║
║                                                      ║
╚══════════════════════════════════════════════════════╝
```
