

# 📋 ТЗ ПРОЕКТА DOD — ЭТАП 3

# ПЛАТЁЖНАЯ СИСТЕМА (NOWpayments + RUkassa)

```
╔══════════════════════════════════════════════════════╗
║                                                      ║
║   ПРОЕКТ:    DOD                                    ║
║   ЭТАП:      3 из 12                                ║
║   НАЗВАНИЕ:  Платёжная система                      ║
║   ЗАВИСИТ:   Этап 1 (accounts) + Этап 2 (wallet)   ║
║                                                      ║
║   ЦЕЛЬ:      Реальные деньги: пополнение через      ║
║              банковские карты, крипто, электронные   ║
║              кошельки. Реальные выводы средств.      ║
║              Webhook обработка. Антифрод.            ║
║                                                      ║
╚══════════════════════════════════════════════════════╝
```

---

## 📌 КОНТЕКСТ ДЛЯ ИИ-АГЕНТА

```
Ты продолжаешь разработку проекта DOD.
Этап 1 (авторизация) и Этап 2 (кошелёк) готовы.

Сейчас ты подключаешь РЕАЛЬНЫЕ платёжные системы:

1. RUkassa (https://rukassa.is/)
   - Банковские карты (Visa, MasterCard, МИР)
   - СБП (Система Быстрых Платежей)
   - Электронные кошельки (QIWI, ЮMoney)
   - Мобильные платежи
   - Фиат: RUB, UAH, KZT, UZS, BYN
   - Приём и выплаты

2. NOWpayments (https://nowpayments.io/)
   - Криптовалюты: BTC, ETH, USDT, TON и 200+ других
   - Автоконвертация в стейблкоины
   - Приём и выплаты

На этом этапе заменяем "демо пополнение" из Этапа 2
на реальные платежи.

ВАЖНО:
- Webhook безопасность (проверка подписей)
- Идемпотентность (один платёж = одно зачисление)
- Логирование ВСЕХ платежей
- Обработка ошибок и retry
- Антифрод проверки
```

---

## ШАГ 3.1 — МОДЕЛИ ПЛАТЕЖЕЙ

### Задача

```
Создай приложение payments со всеми моделями
для работы с платёжными провайдерами.
```

### Структура приложения

```
apps/payments/
├── __init__.py
├── models.py
├── admin.py
├── views.py
├── urls.py
├── forms.py
├── signals.py
├── tasks.py
├── services/
│   ├── __init__.py
│   ├── payment_service.py        # Общая логика платежей
│   ├── rukassa_service.py        # Интеграция RUkassa
│   ├── nowpayments_service.py    # Интеграция NOWpayments
│   ├── payout_service.py         # Выплаты (выводы)
│   └── antifraud_service.py      # Антифрод проверки
├── webhooks/
│   ├── __init__.py
│   ├── rukassa_webhook.py        # Webhook от RUkassa
│   └── nowpayments_webhook.py    # Webhook от NOWpayments
├── providers/
│   ├── __init__.py
│   ├── base.py                   # Абстрактный провайдер
│   ├── rukassa.py                # SDK RUkassa
│   └── nowpayments.py            # SDK NOWpayments
├── tests/
│   ├── __init__.py
│   ├── test_rukassa.py
│   ├── test_nowpayments.py
│   ├── test_webhooks.py
│   └── test_antifraud.py
├── templates/
│   └── payments/
│       └── (шаблоны)
└── migrations/
    └── __init__.py
```

### Модель PaymentProvider (models.py)

```
class PaymentProvider(models.Model):

    Назначение:
      Справочник платёжных провайдеров.
      Настройки каждого провайдера.
      Управляется через админку.

    Поля:
    ─────
    code:
      тип: CharField, max 50, primary key
      Примеры: 'rukassa', 'nowpayments'

    name:
      тип: CharField, max 100
      Примеры: 'RUkassa', 'NOWpayments'

    type:
      тип: CharField
      choices:
        ('fiat', 'Фиатные платежи')
        ('crypto', 'Криптовалюта')
        ('mixed', 'Смешанный')

    description:
      тип: TextField
      Описание для пользователя

    icon:
      тип: CharField, max 50
      Иконка или emoji

    api_base_url:
      тип: URLField
      Базовый URL API провайдера
      RUkassa: 'https://lk.rukassa.is/api/v1'
      NOWpayments: 'https://api.nowpayments.io/v1'

    api_key:
      тип: CharField, max 500
      ШИФРУЕТСЯ в БД
      API ключ провайдера

    api_secret:
      тип: CharField, max 500, nullable
      ШИФРУЕТСЯ в БД
      Секретный ключ (для подписи webhook)

    merchant_id:
      тип: CharField, max 100, nullable
      ID магазина у провайдера
      RUkassa: shop_id
      NOWpayments: не используется

    webhook_secret:
      тип: CharField, max 500, nullable
      ШИФРУЕТСЯ в БД
      Ключ для проверки подписи webhook

    extra_settings:
      тип: JSONField, default=dict
      Дополнительные настройки
      Пример для RUkassa:
        {
          "success_url": "https://dod.com/payment/success/",
          "fail_url": "https://dod.com/payment/fail/",
          "webhook_url": "https://dod.com/webhooks/rukassa/"
        }
      Пример для NOWpayments:
        {
          "ipn_callback_url": "https://dod.com/webhooks/nowpayments/",
          "default_pay_currency": "btc"
        }

    supported_currencies:
      тип: ManyToManyField → Currency
      Какие валюты поддерживает провайдер

    is_active:
      тип: BooleanField, default=True
      Можно временно отключить

    is_deposit_enabled:
      тип: BooleanField, default=True

    is_withdrawal_enabled:
      тип: BooleanField, default=True

    min_deposit:
      тип: DecimalField
      Глобальный минимум депозита для провайдера (в USD)

    max_deposit:
      тип: DecimalField
      Глобальный максимум депозита (в USD)

    deposit_fee_percent:
      тип: DecimalField, default=0
      Комиссия провайдера за приём (%)

    deposit_fee_fixed:
      тип: DecimalField, default=0
      Фиксированная комиссия за приём

    processing_time:
      тип: CharField, max 100
      Время обработки для отображения
      "Мгновенно", "10-30 минут", "1-3 подтверждения"

    sort_order:
      тип: IntegerField, default=0

    created_at:
      тип: DateTimeField, auto_now_add

    updated_at:
      тип: DateTimeField, auto_now

    Meta:
      verbose_name = 'Платёжный провайдер'
      ordering = ['sort_order']
```

### Модель PaymentMethod (models.py)

```
class PaymentMethod(models.Model):

    Назначение:
      Конкретные способы оплаты внутри провайдера.
      Пример: RUkassa имеет "Карта", "СБП", "QIWI".

    Поля:
    ─────
    id:
      тип: UUID, primary key

    provider:
      тип: ForeignKey → PaymentProvider

    code:
      тип: CharField, max 50
      Код метода у провайдера
      RUkassa: 'card', 'sbp', 'qiwi', 'yoomoney', 'mobile'
      NOWpayments: 'btc', 'eth', 'usdttrc20', 'ton'

    name:
      тип: CharField, max 100
      Отображаемое имя
      "Банковская карта", "СБП", "QIWI", "Bitcoin"

    description:
      тип: CharField, max 200
      "Visa, MasterCard, МИР"
      "Через мобильный банк"

    icon:
      тип: CharField, max 50
      "💳", "📱", "🪙", "₿"

    currency:
      тип: ForeignKey → Currency
      В какой валюте принимает
      Карта → RUB
      BTC → BTC

    type:
      тип: CharField
      choices:
        ('deposit', 'Только пополнение')
        ('withdrawal', 'Только вывод')
        ('both', 'Пополнение и вывод')

    min_amount:
      тип: DecimalField
      Минимальная сумма

    max_amount:
      тип: DecimalField
      Максимальная сумма

    fee_percent:
      тип: DecimalField, default=0

    fee_fixed:
      тип: DecimalField, default=0

    processing_time:
      тип: CharField, max 100
      "Мгновенно", "10-30 мин", "1-24 часа"

    is_active:
      тип: BooleanField, default=True

    requires_kyc:
      тип: BooleanField, default=False
      Нужна ли KYC для этого метода

    sort_order:
      тип: IntegerField, default=0

    Meta:
      verbose_name = 'Способ оплаты'
      ordering = ['provider', 'sort_order']
      unique_together = ['provider', 'code']
```

### Модель DepositOrder (models.py)

```
class DepositOrder(models.Model):

    Назначение:
      Заявка на пополнение.
      Создаётся когда пользователь нажимает "Пополнить".
      Обновляется когда приходит webhook от провайдера.

    Поля:
    ─────
    id:
      тип: UUID, primary key

    order_id:
      тип: CharField, max 50, уникальный
      Наш внутренний ID
      Формат: DEP-{timestamp}-{random6}
      Пример: DEP-20250315143022-A7B3C2

    user:
      тип: ForeignKey → User

    wallet:
      тип: ForeignKey → Wallet

    provider:
      тип: ForeignKey → PaymentProvider

    payment_method:
      тип: ForeignKey → PaymentMethod

    currency:
      тип: ForeignKey → Currency
      Валюта в которой пополняет

    amount:
      тип: DecimalField
      Сумма пополнения (которую просил пользователь)

    amount_received:
      тип: DecimalField, nullable
      Фактически полученная сумма (может отличаться для крипты)

    amount_usd:
      тип: DecimalField
      Эквивалент в USD

    fee_amount:
      тип: DecimalField, default=0
      Комиссия

    status:
      тип: CharField
      choices:
        ('created', 'Создана')
        ('pending', 'Ожидает оплаты')
        ('processing', 'Обрабатывается')
        ('completed', 'Завершена')
        ('expired', 'Истекла')
        ('failed', 'Ошибка')
        ('cancelled', 'Отменена')
        ('refunded', 'Возвращена')
      default: 'created'

    provider_order_id:
      тип: CharField, max 200, nullable
      ID заказа в системе провайдера
      RUkassa: их ID платежа
      NOWpayments: их payment_id

    provider_payment_url:
      тип: URLField, nullable
      Ссылка на оплату у провайдера
      Куда редиректить пользователя

    provider_response:
      тип: JSONField, default=dict
      Полный ответ от провайдера при создании
      Для отладки

    provider_status:
      тип: CharField, max 50, nullable
      Статус в системе провайдера

    crypto_address:
      тип: CharField, max 200, nullable
      Адрес для оплаты (крипто)
      Только для NOWpayments

    crypto_network:
      тип: CharField, max 50, nullable
      Сеть (TRC20, ERC20, BEP20)

    crypto_tx_hash:
      тип: CharField, max 200, nullable
      Хеш транзакции в блокчейне

    success_url:
      тип: URLField
      Куда вернуть после успешной оплаты
      default: /wallet/?deposit=success

    fail_url:
      тип: URLField
      Куда вернуть при ошибке
      default: /wallet/?deposit=fail

    transaction:
      тип: OneToOneField → Transaction, nullable
      Связь с транзакцией зачисления
      Создаётся когда status='completed'

    ip_address:
      тип: GenericIPAddressField

    user_agent:
      тип: TextField, nullable

    expires_at:
      тип: DateTimeField
      Время жизни заказа
      Фиат: 30 минут
      Крипто: 60 минут

    completed_at:
      тип: DateTimeField, nullable

    created_at:
      тип: DateTimeField, auto_now_add

    updated_at:
      тип: DateTimeField, auto_now

    Методы:
    ───────
    is_expired():
      True если expires_at < now и status in ('created', 'pending')

    can_be_completed():
      True если status in ('created', 'pending', 'processing')

    Meta:
      verbose_name = 'Заявка на пополнение'
      ordering = ['-created_at']
      indexes:
        - order_id
        - user + created_at
        - provider_order_id
        - status
```

### Модель PayoutOrder (models.py)

```
class PayoutOrder(models.Model):

    Назначение:
      Заявка на выплату (вывод средств через провайдера).
      Связана с WithdrawalRequest из модуля wallet.

    Поля:
    ─────
    id:
      тип: UUID, primary key

    payout_id:
      тип: CharField, max 50, уникальный
      Формат: PAY-{timestamp}-{random6}

    withdrawal_request:
      тип: OneToOneField → WithdrawalRequest
      Связь с заявкой на вывод

    user:
      тип: ForeignKey → User

    provider:
      тип: ForeignKey → PaymentProvider

    payment_method:
      тип: ForeignKey → PaymentMethod

    currency:
      тип: ForeignKey → Currency

    amount:
      тип: DecimalField
      Сумма выплаты

    fee_amount:
      тип: DecimalField

    net_amount:
      тип: DecimalField
      Сумма к получению

    status:
      тип: CharField
      choices:
        ('created', 'Создана')
        ('processing', 'Обрабатывается')
        ('sent', 'Отправлена')
        ('completed', 'Завершена')
        ('failed', 'Ошибка')
        ('cancelled', 'Отменена')

    provider_payout_id:
      тип: CharField, max 200, nullable
      ID выплаты у провайдера

    provider_response:
      тип: JSONField, default=dict

    provider_status:
      тип: CharField, max 50, nullable

    payment_details:
      тип: JSONField
      Реквизиты получателя
      {"card_number": "4***1234", "holder": "IVAN IVANOV"}
      или
      {"crypto_address": "0x...", "network": "TRC20"}

    error_message:
      тип: TextField, nullable
      Текст ошибки если failed

    retry_count:
      тип: IntegerField, default=0
      Количество попыток отправки

    max_retries:
      тип: IntegerField, default=3

    completed_at:
      тип: DateTimeField, nullable

    created_at:
      тип: DateTimeField, auto_now_add

    updated_at:
      тип: DateTimeField, auto_now

    Meta:
      verbose_name = 'Выплата'
      ordering = ['-created_at']
```

### Модель WebhookLog (models.py)

```
class WebhookLog(models.Model):

    Назначение:
      Логирование ВСЕХ входящих webhook от провайдеров.
      Для отладки и аудита.
      НИКОГДА не удаляется.

    Поля:
    ─────
    id:
      тип: UUID, primary key

    provider:
      тип: CharField, max 50
      'rukassa' или 'nowpayments'

    event_type:
      тип: CharField, max 100
      Тип события
      'payment_completed', 'payment_failed',
      'payout_completed', и т.д.

    payload:
      тип: JSONField
      Полное тело запроса

    headers:
      тип: JSONField
      Заголовки запроса (для проверки подписи)

    ip_address:
      тип: GenericIPAddressField

    signature:
      тип: CharField, max 500, nullable
      Подпись из заголовка

    is_valid_signature:
      тип: BooleanField, default=False
      Прошла ли проверка подписи

    is_processed:
      тип: BooleanField, default=False
      Был ли обработан

    processing_result:
      тип: CharField, max 50, nullable
      'success', 'duplicate', 'error', 'invalid_signature'

    processing_error:
      тип: TextField, nullable
      Текст ошибки при обработке

    related_order_id:
      тип: CharField, max 100, nullable
      ID связанного заказа (DEP-... или PAY-...)

    response_code:
      тип: IntegerField, default=200
      Какой HTTP код мы вернули

    processing_time_ms:
      тип: IntegerField, nullable
      Время обработки в миллисекундах

    created_at:
      тип: DateTimeField, auto_now_add

    Meta:
      verbose_name = 'Лог webhook'
      ordering = ['-created_at']
      indexes:
        - provider + created_at
        - related_order_id
        - is_processed
```

### Модель SavedPaymentMethod (models.py)

```
class SavedPaymentMethod(models.Model):

    Назначение:
      Сохранённые реквизиты для быстрого вывода.
      Пользователь сохраняет карту или крипто адрес.

    Поля:
    ─────
    id:
      тип: UUID, primary key

    user:
      тип: ForeignKey → User
      related_name: 'saved_payment_methods'

    type:
      тип: CharField
      choices:
        ('card', 'Банковская карта')
        ('crypto', 'Криптокошелёк')
        ('ewallet', 'Электронный кошелёк')

    name:
      тип: CharField, max 100
      Название для отображения
      "Моя карта Сбербанк", "Основной BTC кошелёк"

    details:
      тип: JSONField
      ШИФРУЕТСЯ
      Для карты:
        {
          "card_number_masked": "4276 **** **** 1234",
          "card_number_hash": "sha256...",
          "holder": "IVAN IVANOV",
          "bank": "Сбербанк"
        }
      Для крипто:
        {
          "address": "0x1234...abcd",
          "network": "TRC20",
          "currency": "USDT"
        }
      Для кошелька:
        {
          "wallet_id": "+79001234567",
          "provider": "qiwi"
        }

    currency:
      тип: ForeignKey → Currency

    is_verified:
      тип: BooleanField, default=False
      Была ли успешная выплата на эти реквизиты

    is_default:
      тип: BooleanField, default=False

    last_used_at:
      тип: DateTimeField, nullable

    created_at:
      тип: DateTimeField, auto_now_add

    Meta:
      verbose_name = 'Сохранённый способ оплаты'
      ordering = ['-is_default', '-last_used_at']

    ВАЖНО:
      - Полный номер карты НИКОГДА не хранится
      - Хранится только маска и хеш для идентификации
      - Криптоадреса хранятся в зашифрованном виде
```

### Модель PaymentSettings (models.py)

```
class PaymentSettings(models.Model):

    Назначение:
      Глобальные настройки платёжной системы.
      Singleton.

    Поля:
    ─────
    deposit_enabled:
      тип: BooleanField, default=True
      Глобальное включение/выключение депозитов

    withdrawal_enabled:
      тип: BooleanField, default=True
      Глобальное включение/выключение выводов

    maintenance_message:
      тип: TextField, nullable
      Сообщение при отключении платежей
      "Платежи временно недоступны. Ожидайте."

    deposit_notification_threshold:
      тип: DecimalField
      Уведомлять админа о депозитах свыше (в USD)
      default=5000

    auto_payout_enabled:
      тип: BooleanField, default=True

    auto_payout_max_amount_usd:
      тип: DecimalField
      Максимум для автовыплаты (в USD)
      default=500

    daily_deposit_limit_per_user:
      тип: DecimalField
      Максимум депозитов в день для одного пользователя (USD)
      default=50000

    daily_payout_limit_total:
      тип: DecimalField
      Максимум выплат в день со всей платформы (USD)
      default=100000

    suspicious_deposit_patterns:
      тип: JSONField
      Паттерны подозрительных депозитов
      {
        "max_deposits_per_hour": 5,
        "max_deposits_per_day": 20,
        "round_amount_alert": true,
        "same_amount_count_alert": 3
      }

    Meta:
      verbose_name = 'Настройки платежей'
```

### Файл admin.py

```
PaymentProviderAdmin:
  list_display: code, name, type, is_active,
                is_deposit_enabled, is_withdrawal_enabled
  list_editable: is_active, is_deposit_enabled, is_withdrawal_enabled
  Скрыть: api_key, api_secret, webhook_secret (показывать маскированно)

PaymentMethodAdmin:
  list_display: name, provider, code, currency, type,
                min_amount, max_amount, fee_percent, is_active
  list_filter: provider, type, is_active, currency
  list_editable: is_active, fee_percent, min_amount, max_amount

DepositOrderAdmin:
  list_display: order_id, user, provider, currency,
                amount, status, created_at
  list_filter: status, provider, currency, created_at
  search_fields: order_id, user__email, provider_order_id
  readonly_fields: provider_response, transaction
  date_hierarchy: created_at

  Действия:
    - Ручное подтверждение (если webhook не пришёл)
    - Отменить
    - Вернуть средства

PayoutOrderAdmin:
  list_display: payout_id, user, provider, currency,
                amount, status, retry_count, created_at
  list_filter: status, provider, currency
  search_fields: payout_id, user__email
  readonly_fields: provider_response, payment_details

  Действия:
    - Повторить отправку
    - Отменить и вернуть средства

WebhookLogAdmin:
  list_display: provider, event_type, is_valid_signature,
                is_processed, processing_result,
                related_order_id, created_at
  list_filter: provider, is_valid_signature, is_processed,
               processing_result
  search_fields: related_order_id
  readonly_fields: ВСЕ (логи не редактируются)

SavedPaymentMethodAdmin:
  list_display: user, type, name, currency, is_verified, is_default
  list_filter: type, currency, is_verified
  search_fields: user__email, name
  Скрыть: details (конфиденциально)

PaymentSettingsAdmin:
  Singleton
  Все поля редактируемые
```

### Критерий готовности шага 3.1

```
□ Модель PaymentProvider создана
□ Модель PaymentMethod создана
□ Модель DepositOrder создана
□ Модель PayoutOrder создана
□ Модель WebhookLog создана
□ Модель SavedPaymentMethod создана
□ Модель PaymentSettings создана (singleton)
□ Все миграции применены
□ Admin настроен для всех моделей
□ Fixtures: начальные данные провайдеров и методов
□ API ключи в .env (не в коде!)
```

---

## ШАГ 3.2 — ПРОВАЙДЕРЫ (SDK)

### Задача

```
Создай абстракцию провайдера и конкретные реализации
для RUkassa и NOWpayments.
```

### Абстрактный провайдер (providers/base.py)

```
class BasePaymentProvider(ABC):

    Назначение:
      Абстрактный класс для всех платёжных провайдеров.
      Все провайдеры реализуют одинаковый интерфейс.
      Это позволяет легко добавлять новых провайдеров.

    Абстрактные методы:
    ────────────────────

    @abstractmethod
    def create_deposit(self, order_id, amount, currency,
                        description, success_url, fail_url,
                        customer_email) -> dict:
      Создать платёж (депозит).
      
      Возвращает:
        {
          "provider_order_id": "...",
          "payment_url": "https://...",
          "status": "pending",
          "raw_response": {...}
        }


    @abstractmethod
    def check_deposit_status(self, provider_order_id) -> dict:
      Проверить статус платежа.
      
      Возвращает:
        {
          "status": "completed" | "pending" | "failed",
          "amount_received": Decimal,
          "raw_response": {...}
        }


    @abstractmethod
    def create_payout(self, payout_id, amount, currency,
                       payment_details) -> dict:
      Создать выплату (вывод).
      
      Возвращает:
        {
          "provider_payout_id": "...",
          "status": "processing",
          "raw_response": {...}
        }


    @abstractmethod
    def check_payout_status(self, provider_payout_id) -> dict:
      Проверить статус выплаты.


    @abstractmethod
    def verify_webhook_signature(self, payload, headers) -> bool:
      Проверить подпись webhook.
      True если подпись валидна.


    @abstractmethod
    def parse_webhook(self, payload, headers) -> dict:
      Распарсить webhook в стандартный формат.
      
      Возвращает:
        {
          "event_type": "deposit_completed" | "payout_completed" | ...,
          "order_id": "наш order_id",
          "provider_order_id": "...",
          "status": "completed" | "failed" | ...,
          "amount": Decimal,
          "currency": "USD",
          "raw_data": {...}
        }


    Общие методы:
    ─────────────

    def _make_request(self, method, endpoint, data=None):
      HTTP запрос к API провайдера.
      С таймаутом 30 секунд.
      С retry 3 попытки.
      С логированием.
      Возвращает response.

    def _log_api_call(self, method, endpoint, request_data,
                       response_data, status_code, duration_ms):
      Логирование вызова API.
```

### RUkassa провайдер (providers/rukassa.py)

```
class RUkassaProvider(BasePaymentProvider):

    Назначение:
      Интеграция с RUkassa.
      Документация: https://lk.rukassa.is/api/v1

    Настройки (из .env):
      RUKASSA_SHOP_ID
      RUKASSA_TOKEN
      RUKASSA_WEBHOOK_SECRET

    Методы:
    ───────

    def create_deposit(self, order_id, amount, currency,
                        description, success_url, fail_url,
                        customer_email):
      
      API RUkassa: POST /api/v1/create
      
      Запрос:
        {
          "shop_id": RUKASSA_SHOP_ID,
          "token": RUKASSA_TOKEN,
          "order_id": order_id,
          "amount": float(amount),
          "method": "card" / "sbp" / "qiwi" / ...,
          "currency": currency,  # "RUB"
          "description": description,
          "success_url": success_url,
          "fail_url": fail_url,
          "email": customer_email,
          "webhook_url": "https://dod.com/webhooks/rukassa/"
        }

      Ответ RUkassa:
        {
          "id": 12345,
          "url": "https://pay.rukassa.is/xxx",
          "status": "WAIT"
        }

      Возвращаем:
        {
          "provider_order_id": "12345",
          "payment_url": "https://pay.rukassa.is/xxx",
          "status": "pending",
          "raw_response": {...}
        }


    def check_deposit_status(self, provider_order_id):
      
      API RUkassa: POST /api/v1/getInfo
      
      Запрос:
        {
          "shop_id": RUKASSA_SHOP_ID,
          "token": RUKASSA_TOKEN,
          "id": provider_order_id
        }

      Ответ:
        {
          "id": 12345,
          "status": "PAID" / "WAIT" / "CANCEL",
          "amount": 1000.00,
          "in_amount": 1000.00
        }

      Маппинг статусов RUkassa → наши:
        "WAIT"   → "pending"
        "PAID"   → "completed"
        "CANCEL" → "cancelled"
        "FAIL"   → "failed"


    def create_payout(self, payout_id, amount, currency,
                       payment_details):
      
      API RUkassa: POST /api/v1/createWithdraw
      
      Запрос:
        {
          "shop_id": RUKASSA_SHOP_ID,
          "token": RUKASSA_TOKEN,
          "order_id": payout_id,
          "amount": float(amount),
          "method": "card" / "qiwi" / ...,
          "wallet": payment_details["card_number"]
                    или payment_details["wallet_id"]
        }


    def verify_webhook_signature(self, payload, headers):
      
      RUkassa подписывает webhook.
      Формула:
        sign = md5(
          shop_id + amount + order_id + webhook_secret
        )
      Сравнить с payload["sign"]


    def parse_webhook(self, payload, headers):
      
      RUkassa отправляет POST на наш webhook_url.
      
      Тело:
        {
          "id": "12345",
          "order_id": "DEP-20250315-A7B3C2",
          "amount": "1000.00",
          "in_amount": "1000.00",
          "status": "PAID",
          "method": "card",
          "sign": "md5hash..."
        }

      Парсим:
        {
          "event_type": "deposit_completed",
          "order_id": "DEP-20250315-A7B3C2",
          "provider_order_id": "12345",
          "status": "completed",
          "amount": Decimal("1000.00"),
          "currency": "RUB",
          "raw_data": {...}
        }
```

### NOWpayments провайдер (providers/nowpayments.py)

```
class NOWpaymentsProvider(BasePaymentProvider):

    Назначение:
      Интеграция с NOWpayments.
      Документация: https://documenter.getpostman.com/view/7907941/

    Настройки (из .env):
      NOWPAYMENTS_API_KEY
      NOWPAYMENTS_IPN_SECRET

    Методы:
    ───────

    def create_deposit(self, order_id, amount, currency,
                        description, success_url, fail_url,
                        customer_email):
      
      API: POST /v1/invoice
      
      Заголовки:
        x-api-key: NOWPAYMENTS_API_KEY

      Запрос:
        {
          "price_amount": float(amount),
          "price_currency": currency.lower(),  # "usd", "btc"
          "pay_currency": currency.lower(),
          "order_id": order_id,
          "order_description": description,
          "ipn_callback_url": "https://dod.com/webhooks/nowpayments/",
          "success_url": success_url,
          "cancel_url": fail_url
        }

      Ответ NOWpayments:
        {
          "id": "5678901234",
          "invoice_url": "https://nowpayments.io/payment/?iid=...",
          "token_id": "...",
          "order_id": "DEP-20250315-A7B3C2"
        }

      Возвращаем:
        {
          "provider_order_id": "5678901234",
          "payment_url": "https://nowpayments.io/payment/?iid=...",
          "status": "pending",
          "raw_response": {...}
        }


    def check_deposit_status(self, provider_order_id):
      
      API: GET /v1/payment/{payment_id}
      
      Маппинг статусов:
        "waiting"    → "pending"
        "confirming" → "processing"
        "confirmed"  → "processing"
        "sending"    → "processing"
        "finished"   → "completed"
        "failed"     → "failed"
        "expired"    → "expired"
        "refunded"   → "refunded"


    def create_payout(self, payout_id, amount, currency,
                       payment_details):
      
      API: POST /v1/payout
      
      Запрос:
        {
          "address": payment_details["crypto_address"],
          "currency": currency.lower(),
          "amount": float(amount),
          "ipn_callback_url": "https://dod.com/webhooks/nowpayments/payout/"
        }


    def verify_webhook_signature(self, payload, headers):
      
      NOWpayments подписывает webhook через HMAC SHA-512.
      
      Формула:
        sorted_payload = sort payload by key alphabetically
        json_string = json.dumps(sorted_payload)
        hmac = HMAC-SHA512(IPN_SECRET, json_string)
      
      Заголовок: x-nowpayments-sig
      Сравнить hmac с заголовком.


    def parse_webhook(self, payload, headers):
      
      NOWpayments IPN callback.
      
      Тело:
        {
          "payment_id": 5678901234,
          "payment_status": "finished",
          "pay_address": "0x...",
          "price_amount": 100.0,
          "price_currency": "usd",
          "pay_amount": 0.0015,
          "pay_currency": "btc",
          "order_id": "DEP-20250315-A7B3C2",
          "order_description": "...",
          "actually_paid": 0.0015,
          "outcome_amount": 99.5,
          "outcome_currency": "usd"
        }

      Парсим:
        {
          "event_type": "deposit_completed",
          "order_id": "DEP-20250315-A7B3C2",
          "provider_order_id": "5678901234",
          "status": "completed",
          "amount": Decimal("100.00"),
          "amount_received": Decimal("0.0015"),
          "currency": "BTC",
          "raw_data": {...}
        }
```

### Критерий готовности шага 3.2

```
□ BasePaymentProvider абстрактный класс
□ RUkassaProvider: create_deposit, check_status,
  create_payout, verify_webhook, parse_webhook
□ NOWpaymentsProvider: create_deposit, check_status,
  create_payout, verify_webhook, parse_webhook
□ API ключи из .env (не захардкожены!)
□ Retry логика при ошибках API
□ Логирование всех API вызовов
□ Таймауты настроены
□ Маппинг статусов провайдеров → наши
```

---

## ШАГ 3.3 — СЕРВИСЫ ПЛАТЕЖЕЙ

### PaymentService (services/payment_service.py)

```
class PaymentService:

    Назначение:
      Основная логика создания платежей.
      Связывает провайдеров с моделями и кошельком.

    Методы:
    ───────

    @staticmethod
    def get_available_deposit_methods(user, currency_code=None):
      
      Получить доступные способы пополнения.
      
      Логика:
        1. Получить все активные PaymentMethod
           где type in ('deposit', 'both')
        2. Фильтровать по currency если указан
        3. Проверить лимиты
        4. Сгруппировать по провайдеру
        
      Возвращает:
        [
          {
            "provider": "rukassa",
            "provider_name": "RUkassa",
            "methods": [
              {
                "code": "card",
                "name": "Банковская карта",
                "icon": "💳",
                "currency": "RUB",
                "min": 100,
                "max": 500000,
                "fee": "0%",
                "processing_time": "Мгновенно"
              },
              {
                "code": "sbp",
                "name": "СБП",
                ...
              }
            ]
          },
          {
            "provider": "nowpayments",
            "provider_name": "NOWpayments",
            "methods": [
              {
                "code": "btc",
                "name": "Bitcoin",
                ...
              }
            ]
          }
        ]


    @staticmethod
    def create_deposit(user, currency_code, amount,
                        provider_code, method_code,
                        ip_address, user_agent):
      
      Создать депозит.
      
      Логика:
        1. ВАЛИДАЦИЯ:
           - PaymentSettings.deposit_enabled == True
           - Провайдер и метод активны
           - amount >= min и amount <= max
           - Дневной лимит не превышен
           - wallet.is_frozen == False
           - Антифрод проверка (AntiFraudService)

        2. Создать DepositOrder:
           - order_id = generate_order_id("DEP")
           - status = 'created'
           - expires_at = now + 30min (фиат) / 60min (крипто)

        3. Получить провайдер:
           provider = get_provider_instance(provider_code)

        4. Вызвать API провайдера:
           result = provider.create_deposit(
             order_id=deposit.order_id,
             amount=amount,
             currency=currency_code,
             description=f"DOD пополнение {deposit.order_id}",
             success_url=f"https://dod.com/payment/success/{deposit.order_id}/",
             fail_url=f"https://dod.com/payment/fail/{deposit.order_id}/",
             customer_email=user.email
           )

        5. Обновить DepositOrder:
           - provider_order_id = result["provider_order_id"]
           - provider_payment_url = result["payment_url"]
           - provider_response = result["raw_response"]
           - status = 'pending'

        6. Вернуть:
           {
             "deposit_id": deposit.order_id,
             "payment_url": result["payment_url"],
             "expires_at": deposit.expires_at
           }

      Ошибки:
        - PaymentDisabledError
        - ProviderUnavailableError
        - LimitExceededError
        - AntiFraudBlockError


    @staticmethod
    def complete_deposit(order_id, amount_received=None):
      
      Завершить депозит (вызывается из webhook).
      
      ВАЖНО: ИДЕМПОТЕНТНОСТЬ!
      Если уже completed → ничего не делать (duplicate).
      
      Логика (АТОМАРНО):
        1. Найти DepositOrder по order_id
           С блокировкой (select_for_update)

        2. Проверить can_be_completed()
           Если уже completed → return "duplicate"
           Если expired/cancelled → return "rejected"

        3. Определить фактическую сумму:
           actual_amount = amount_received or deposit.amount

        4. Зачислить на кошелёк:
           transaction = TransactionService.deposit(
             wallet=deposit.wallet,
             currency=deposit.currency.code,
             amount=actual_amount,
             description=f"Пополнение {deposit.payment_method.name}",
             metadata={
               "provider": deposit.provider.code,
               "method": deposit.payment_method.code,
               "deposit_order_id": deposit.order_id,
               "provider_order_id": deposit.provider_order_id
             },
             ip_address=deposit.ip_address
           )

        5. Обновить DepositOrder:
           - status = 'completed'
           - amount_received = actual_amount
           - transaction = transaction
           - completed_at = now

        6. Обновить trust_level (если первый депозит):
           если user.trust_level == 1:
             user.trust_level = 2

        7. Уведомить пользователя:
           - На сайте (колокольчик)
           - Email (если включено)
           - Telegram (если подключён)
           "Баланс пополнен на $100.00"

        8. Если amount_usd > threshold:
           Уведомить админов

        9. Вернуть "success"


    @staticmethod
    def fail_deposit(order_id, reason=""):
      
      Отметить депозит как неудачный.
      
      Логика:
        1. Найти DepositOrder
        2. Если уже completed → игнорировать
        3. status = 'failed'
        4. Уведомить пользователя


    @staticmethod
    def get_provider_instance(provider_code):
      
      Фабрика провайдеров.
      
      Логика:
        provider_map = {
          'rukassa': RUkassaProvider,
          'nowpayments': NOWpaymentsProvider
        }
        
        provider_model = PaymentProvider.objects.get(code=provider_code)
        provider_class = provider_map[provider_code]
        
        return provider_class(
          api_key=provider_model.api_key,
          api_secret=provider_model.api_secret,
          merchant_id=provider_model.merchant_id,
          webhook_secret=provider_model.webhook_secret,
          extra_settings=provider_model.extra_settings
        )
```

### PayoutService (services/payout_service.py)

```
class PayoutService:

    Назначение:
      Обработка выплат (выводов) через провайдеров.

    Методы:
    ───────

    @staticmethod
    def process_payout(withdrawal_request_id):
      
      Celery задача. Отправить деньги через провайдера.
      
      Логика:
        1. Найти WithdrawalRequest

        2. Определить провайдера:
           - Если payment_method == 'card' → RUkassa
           - Если payment_method == 'crypto' → NOWpayments
           - Если payment_method == 'ewallet' → RUkassa

        3. Определить PaymentMethod:
           Из payment_details → конкретный метод

        4. Создать PayoutOrder:
           - status = 'created'

        5. Вызвать API провайдера:
           provider = get_provider_instance(...)
           result = provider.create_payout(
             payout_id=payout.payout_id,
             amount=withdrawal.net_amount,
             currency=withdrawal.currency.code,
             payment_details=withdrawal.payment_details
           )

        6. Обновить PayoutOrder:
           - provider_payout_id = result["provider_payout_id"]
           - provider_response = result["raw_response"]
           - status = 'processing'

        7. Обновить WithdrawalRequest:
           - status = 'processing'

      Обработка ошибок:
        Если API вернул ошибку:
        - retry_count += 1
        - Если retry_count < max_retries:
          → Повторить через 5 минут (Celery retry)
        - Если retry_count >= max_retries:
          → status = 'failed'
          → Разморозить средства
          → Уведомить пользователя и админов


    @staticmethod
    def complete_payout(payout_id, provider_data=None):
      
      Выплата завершена (из webhook).
      ИДЕМПОТЕНТНО.
      
      Логика (АТОМАРНО):
        1. Найти PayoutOrder
        2. Если уже completed → duplicate
        3. status = 'completed'
        4. completed_at = now

        5. Списать из frozen:
           TransactionService.settle_frozen(
             wallet, currency, frozen_amount
           )
        6. Создать Transaction type='withdrawal'

        7. Обновить WithdrawalRequest:
           - status = 'completed'
           - completed_at = now

        8. Обновить wallet.total_withdrawn

        9. Сохранить реквизиты как SavedPaymentMethod
           (если первая успешная выплата на эти реквизиты)

        10. Уведомить пользователя:
            "Вывод $1,000 на карту *1234 выполнен"


    @staticmethod
    def fail_payout(payout_id, error_message=""):
      
      Выплата не удалась.
      
      Логика:
        1. PayoutOrder.status = 'failed'
        2. PayoutOrder.error_message = error_message
        3. РАЗМОРОЗИТЬ средства
        4. WithdrawalRequest.status = 'failed'
        5. Уведомить пользователя и админов
```

### AntiFraudService (services/antifraud_service.py)

```
class AntiFraudService:

    Назначение:
      Проверка транзакций на мошенничество.
      Вызывается при каждом депозите и выводе.

    Методы:
    ───────

    @staticmethod
    def check_deposit(user, amount, currency, ip_address,
                       payment_method):
      
      Проверить депозит на подозрительность.
      
      Возвращает:
        {
          "allowed": True / False,
          "risk_score": 0-100,
          "flags": ["flag1", "flag2"],
          "block_reason": "..." или None
        }

      Проверки:

        1. Частота депозитов:
           deposits_last_hour = count deposits last 1h
           if deposits_last_hour >= 5:
             flags.append("high_frequency")
             risk_score += 20

        2. Одинаковые суммы:
           same_amount_count = count same amount deposits last 24h
           if same_amount_count >= 3:
             flags.append("same_amount_pattern")
             risk_score += 15

        3. Круглые суммы:
           if amount % 1000 == 0 and amount >= 5000:
             flags.append("round_large_amount")
             risk_score += 10

        4. Новый аккаунт + большой депозит:
           account_age = now - user.created_at
           if account_age < 1 hour and amount_usd > 500:
             flags.append("new_account_large_deposit")
             risk_score += 25

        5. IP не совпадает с регистрацией:
           if ip_address != user.registration_ip:
             if not ip_in_same_country:
               flags.append("foreign_ip")
               risk_score += 15

        6. Нет активности кроме депозитов:
           bets = Transaction.filter(user=user, type='bet').count()
           deposits = Transaction.filter(user=user, type='deposit').count()
           if deposits > 3 and bets == 0:
             flags.append("deposit_only_no_activity")
             risk_score += 30

        7. Чёрный список IP:
           if ip_address in blacklisted_ips:
             allowed = False
             block_reason = "IP заблокирован"

        8. Дневной лимит:
           today_deposits_usd = sum deposits today in usd
           if today_deposits_usd + amount_usd > daily_limit:
             allowed = False
             block_reason = "Дневной лимит превышен"

      Решение:
        if risk_score >= 80:
          allowed = False
          block_reason = "Подозрительная активность"
          notify_admins()
        elif risk_score >= 50:
          allowed = True  # но помечаем
          notify_admins()


    @staticmethod
    def check_withdrawal(user, amount, currency, ip_address):
      
      Уже реализовано в WithdrawalService.calculate_risk_level
      Но дополнительно:

        1. Скорость вывода после депозита:
           last_deposit = last deposit transaction
           if last_deposit and (now - last_deposit.created_at) < 10 min:
             flags.append("immediate_withdrawal_after_deposit")
             risk_score += 40

        2. Вывод больше чем играл:
           total_bets = wallet.total_wagered
           if total_bets < amount_usd * 0.5:
             flags.append("low_wagering")
             risk_score += 20

        3. Мульти-аккаунт проверка:
           same_ip_users = User.filter(registration_ip=ip_address)
           if same_ip_users.count() > 1:
             flags.append("possible_multi_account")
             risk_score += 30
```

### Критерий готовности шага 3.3

```
□ PaymentService: get_methods, create_deposit, complete, fail
□ PayoutService: process, complete, fail
□ AntiFraudService: check_deposit, check_withdrawal
□ Идемпотентность: дублирующие webhook не дублируют зачисление
□ Атомарные операции
□ Retry логика для выплат
□ Уведомления пользователей и админов
□ Логирование всех операций
```

---

## ШАГ 3.4 — WEBHOOK ОБРАБОТЧИКИ

### Задача

```
Создай webhook endpoints для приёма уведомлений
от платёжных провайдеров.
БЕЗОПАСНОСТЬ — приоритет №1.
```

### RUkassa Webhook (webhooks/rukassa_webhook.py)

```
URL: /webhooks/rukassa/
Метод: POST
CSRF: ОТКЛЮЧЁН (exempt)
Аутентификация: подпись в теле запроса

Логика:

  def rukassa_webhook(request):
    
    start_time = time.time()

    # 1. ЛОГИРОВАНИЕ
    webhook_log = WebhookLog.objects.create(
      provider='rukassa',
      payload=json.loads(request.body),
      headers=dict(request.headers),
      ip_address=get_client_ip(request),
      event_type='incoming'
    )

    try:

      # 2. ПРОВЕРКА IP (белый список RUkassa)
      allowed_ips = [
        '185.71.65.0/24',
        '185.71.66.0/24',
        # ... актуальные IP RUkassa
      ]
      client_ip = get_client_ip(request)
      if not ip_in_whitelist(client_ip, allowed_ips):
        webhook_log.is_valid_signature = False
        webhook_log.processing_result = 'blocked_ip'
        webhook_log.response_code = 403
        webhook_log.save()
        return HttpResponse(status=403)

      # 3. ПАРСИНГ
      payload = json.loads(request.body)

      # 4. ПРОВЕРКА ПОДПИСИ
      provider = RUkassaProvider(...)
      if not provider.verify_webhook_signature(payload, request.headers):
        webhook_log.is_valid_signature = False
        webhook_log.processing_result = 'invalid_signature'
        webhook_log.response_code = 400
        webhook_log.save()
        return HttpResponse(status=400)

      webhook_log.is_valid_signature = True

      # 5. ПАРСИНГ В СТАНДАРТНЫЙ ФОРМАТ
      parsed = provider.parse_webhook(payload, request.headers)
      webhook_log.event_type = parsed['event_type']
      webhook_log.related_order_id = parsed.get('order_id')

      # 6. ОБРАБОТКА
      if parsed['event_type'] == 'deposit_completed':
        result = PaymentService.complete_deposit(
          order_id=parsed['order_id'],
          amount_received=parsed.get('amount')
        )
      elif parsed['event_type'] == 'deposit_failed':
        result = PaymentService.fail_deposit(
          order_id=parsed['order_id'],
          reason=parsed.get('reason', '')
        )
      elif parsed['event_type'] == 'payout_completed':
        result = PayoutService.complete_payout(
          payout_id=parsed['order_id'],
          provider_data=parsed
        )
      elif parsed['event_type'] == 'payout_failed':
        result = PayoutService.fail_payout(
          payout_id=parsed['order_id'],
          error_message=parsed.get('reason', '')
        )
      else:
        result = 'unknown_event'

      # 7. ОБНОВИТЬ ЛОГ
      webhook_log.is_processed = True
      webhook_log.processing_result = result
      webhook_log.processing_time_ms = int(
        (time.time() - start_time) * 1000
      )
      webhook_log.response_code = 200
      webhook_log.save()

      # 8. ОТВЕТ ПРОВАЙДЕРУ
      # RUkassa ожидает HTTP 200
      return HttpResponse("OK", status=200)

    except Exception as e:
      webhook_log.is_processed = False
      webhook_log.processing_result = 'error'
      webhook_log.processing_error = str(e)
      webhook_log.response_code = 500
      webhook_log.save()

      # Логировать ошибку
      logger.error(f"Webhook error: {e}", exc_info=True)

      # Всё равно вернуть 200 чтобы провайдер
      # не слал повторно (мы сами разберёмся)
      return HttpResponse("OK", status=200)
```

### NOWpayments Webhook (webhooks/nowpayments_webhook.py)

```
URL: /webhooks/nowpayments/
Метод: POST
CSRF: ОТКЛЮЧЁН

Логика:
  Аналогично RUkassa, но:
  
  - Проверка подписи: HMAC SHA-512 из заголовка x-nowpayments-sig
  - IP whitelist NOWpayments (из их документации)
  - Статусы: waiting, confirming, confirmed, sending, 
              partially_paid, finished, failed, refunded, expired
  
  Особенности крипто:
    - partially_paid: получено меньше чем нужно
      → Зачислить то что получено
      → Уведомить пользователя "Получено $95 из $100"
    
    - confirming: ждём подтверждения в блокчейне
      → Ничего не делаем, ждём finished
    
    - Курс крипто может измениться между созданием и оплатой
      → Зачислять то что фактически получено (actually_paid)
```

### URL конфигурация

```
apps/payments/urls.py:

urlpatterns = [
    # Webhook (без авторизации, без CSRF)
    path('webhooks/rukassa/', rukassa_webhook, name='rukassa-webhook'),
    path('webhooks/nowpayments/', nowpayments_webhook, name='nowpayments-webhook'),

    # Страницы для пользователя
    path('payment/success/<str:order_id>/', payment_success, name='payment-success'),
    path('payment/fail/<str:order_id>/', payment_fail, name='payment-fail'),
    path('payment/status/<str:order_id>/', payment_status, name='payment-status'),
]
```

### Критерий готовности шага 3.4

```
□ Webhook RUkassa: принимает, проверяет подпись, обрабатывает
□ Webhook NOWpayments: принимает, проверяет HMAC, обрабатывает
□ IP whitelist для обоих провайдеров
□ CSRF отключён для webhook URL
□ WebhookLog записывается для КАЖДОГО запроса
□ Идемпотентность: повторный webhook не дублирует операцию
□ Ошибки логируются но не ломают ответ провайдеру
□ Провайдер получает HTTP 200
□ Partially paid обрабатывается (крипто)
```

---

## ШАГ 3.5 — ОБНОВЛЕНИЕ СТРАНИЦ КОШЕЛЬКА

### Задача

```
Обнови страницы пополнения и вывода из Этапа 2.
Заменяй демо-пополнение на реальные провайдеры.
Добавь статусные страницы.
```

### Обновлённая страница пополнения

```
URL: /wallet/deposit/

Изменения по сравнению с Этапом 2:

  1. Вместо "Демо пополнение":
     Реальный выбор провайдера и метода

  2. При нажатии "Пополнить":
     → PaymentService.create_deposit()
     → Редирект на payment_url провайдера
     → Пользователь оплачивает на стороне провайдера
     → Провайдер редиректит обратно на success/fail URL
     → Webhook зачисляет деньги

  3. Для крипто:
     Показать адрес для оплаты + QR код
     Статус обновляется через HTMX polling
     hx-get="/payment/status/{order_id}/"
     hx-trigger="every 10s"
     Показывать:
       "Ожидание оплаты..."
       "1/3 подтверждения..."
       "Оплата получена! ✅"

  4. Сохранённые методы:
     Если пользователь уже пополнял →
     показать "Последний метод: 💳 Карта *1234 [Использовать]"
```

### Страница успешной оплаты

```
URL: /payment/success/{order_id}/

  ┌──────────────────────────────────────┐
  │                                      │
  │  ✅ Оплата получена!                │
  │                                      │
  │  Заказ: DEP-20250315-A7B3C2         │
  │  Сумма: $100.00                      │
  │  Метод: 💳 Банковская карта         │
  │  Статус: Зачислено                  │
  │                                      │
  │  Ваш баланс: $1,100.00             │
  │                                      │
  │  [Перейти в кошелёк]               │
  │  [Сделать ставку]                   │
  │                                      │
  └──────────────────────────────────────┘

  ВАЖНО:
    Если webhook ещё не пришёл →
    показать "Обрабатывается..." и polling
    hx-get="/payment/status/{order_id}/"
    hx-trigger="every 5s"
```

### Страница неудачной оплаты

```
URL: /payment/fail/{order_id}/

  ┌──────────────────────────────────────┐
  │                                      │
  │  ❌ Оплата не прошла                │
  │                                      │
  │  Заказ: DEP-20250315-A7B3C2         │
  │  Деньги не были списаны.            │
  │                                      │
  │  [Попробовать снова]                │
  │  [Выбрать другой способ]            │
  │  [Обратиться в поддержку]           │
  │                                      │
  └──────────────────────────────────────┘
```

### Страница статуса крипто-оплаты

```
URL: /payment/crypto/{order_id}/

  ┌──────────────────────────────────────────────┐
  │                                              │
  │  🪙 Оплата Bitcoin                          │
  │                                              │
  │  Отправьте 0.00150000 BTC на адрес:        │
  │                                              │
  │  ┌────────────────────────────────────────┐ │
  │  │ bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh │
  │  └────────────────────────────────────────┘ │
  │  [📋 Скопировать]                          │
  │                                              │
  │  ┌─────────┐                                │
  │  │ QR CODE │                                │
  │  │         │                                │
  │  └─────────┘                                │
  │                                              │
  │  Сеть: Bitcoin                              │
  │  Сумма: 0.00150000 BTC (≈ $100.00)        │
  │                                              │
  │  Статус: ⏳ Ожидание оплаты                │
  │  Осталось времени: 54:32                    │
  │                                              │
  │  ⚠️ Отправьте ТОЧНУЮ сумму                 │
  │  ⚠️ Только в сети Bitcoin                  │
  │  ⚠️ Минимум 1 подтверждение               │
  │                                              │
  └──────────────────────────────────────────────┘

  HTMX polling:
    Статус обновляется каждые 10 секунд:
    "⏳ Ожидание..." → "🔄 Обнаружена транзакция..."
    → "🔄 1/3 подтверждения..." → "✅ Оплата получена!"
```

### Обновлённая страница вывода

```
Изменения:

  1. Выбор метода вывода → привязан к реальным провайдерам:
     💳 На карту (RUkassa) → ввод номера карты
     🪙 Криптовалюта (NOWpayments) → ввод адреса
     📱 Электронный кошелёк (RUkassa) → ввод номера кошелька

  2. Сохранённые реквизиты:
     Если есть → показать: "💳 *1234 (Сбербанк) [Использовать]"
     
  3. При нажатии "Вывести":
     → 2FA подтверждение (обязательно)
     → WithdrawalService.create_withdrawal_request()
     → Если автовывод → PayoutService.process_payout()
     → Если ручной → уведомление админам

  4. Статусная страница вывода:
     /wallet/withdrawal/{request_id}/
     Показывает текущий статус:
     "⏳ На проверке" → "✅ Одобрено" → "🔄 Обрабатывается"
     → "✅ Выполнено" или "❌ Отклонено"
```

### Критерий готовности шага 3.5

```
□ Страница пополнения: реальные провайдеры вместо демо
□ Редирект на платёжную систему работает
□ Страница успешной оплаты
□ Страница неудачной оплаты
□ Страница крипто-оплаты с QR кодом и таймером
□ Polling статуса (HTMX)
□ Страница вывода: реальные методы
□ Сохранённые реквизиты
□ 2FA при выводе
□ Статусная страница вывода
□ Все страницы: тёмная тема, мобильная адаптация
```

---

## ШАГ 3.6 — CELERY ЗАДАЧИ + МОНИТОРИНГ

### Задача

```
Создай фоновые задачи и мониторинг платежей.
```

### Файл tasks.py

```
Периодические задачи:

check_pending_deposits():
    Каждые 5 минут.
    Найти все DepositOrder со status='pending'
    и created_at > 5 минут назад.
    Для каждого → проверить статус у провайдера:
      provider.check_deposit_status(provider_order_id)
    Если completed → complete_deposit()
    Если expired → expire_deposit()
    Зачем:
      Webhook может не прийти (сеть, ошибка).
      Это страховка.

check_pending_payouts():
    Каждые 5 минут.
    Аналогично: проверить статус выплат у провайдера.

expire_old_deposits():
    Каждые 10 минут.
    DepositOrder где expires_at < now и status='pending'
    → status = 'expired'

retry_failed_payouts():
    Каждые 15 минут.
    PayoutOrder где status='failed' и retry_count < max_retries
    → Повторить попытку.

daily_payment_report():
    Каждый день в 09:00.
    Отчёт для админов:
      - Всего депозитов за день: $X (N штук)
      - Всего выводов за день: $Y (N штук)
      - Ожидающих выводов: N
      - Подозрительных: N
      - Ошибок: N
    Отправить в Telegram админам.

check_provider_health():
    Каждые 30 минут.
    Ping API каждого провайдера.
    Если не отвечает:
      - Пометить provider.is_active = False (временно)
      - Уведомить админов
      - Показать пользователям "Способ временно недоступен"
    Если заработал:
      - provider.is_active = True
      - Уведомить админов

reconciliation_check():
    Каждый день в 03:00.
    Сверка:
      Сумма completed deposits - сумма completed payouts
      должна примерно = сумма всех балансов.
    Если расхождение > 1%:
      КРИТИЧЕСКОЕ уведомление.
```

### Мониторинг для админки

```
Дашборд платежей в админке:

  /admin/payments/dashboard/

  ┌──────────────────────────────────────────────────┐
  │  📊 Платежи — Дашборд                          │
  │                                                  │
  │  Сегодня:                                       │
  │  ┌──────────┬──────────┬──────────┬──────────┐ │
  │  │📥 $12,345│📤 $5,678 │⏳ 3      │⚠️ 1     │ │
  │  │Депозиты  │Выводы    │Ожидают   │Подозрит. │ │
  │  └──────────┴──────────┴──────────┴──────────┘ │
  │                                                  │
  │  Провайдеры:                                    │
  │  RUkassa:      🟢 Онлайн  | Депозитов: $8,000 │
  │  NOWpayments:  🟢 Онлайн  | Депозитов: $4,345 │
  │                                                  │
  │  Последние ошибки:                              │
  │  ❌ 14:30 — Payout PAY-xxx failed: timeout     │
  │  ❌ 12:15 — Webhook invalid signature          │
  │                                                  │
  └──────────────────────────────────────────────────┘
```

### Критерий готовности шага 3.6

```
□ Celery beat: все периодические задачи
□ check_pending_deposits работает (страховка от потери webhook)
□ check_pending_payouts работает
□ expire_old_deposits работает
□ retry_failed_payouts работает
□ daily_payment_report отправляется
□ check_provider_health работает
□ reconciliation_check работает
□ Дашборд платежей в админке
□ Уведомления при ошибках
```

---

## 📊 ОБЩИЙ ЧЕКЛИСТ ЭТАПА 3

```
МОДЕЛИ:
  □ PaymentProvider (RUkassa, NOWpayments)
  □ PaymentMethod (card, sbp, qiwi, btc, eth, usdt, ton)
  □ DepositOrder
  □ PayoutOrder
  □ WebhookLog
  □ SavedPaymentMethod
  □ PaymentSettings

ПРОВАЙДЕРЫ:
  □ BasePaymentProvider (абстракция)
  □ RUkassaProvider (все методы)
  □ NOWpaymentsProvider (все методы)
  □ API ключи в .env

СЕРВИСЫ:
  □ PaymentService (create_deposit, complete, fail)
  □ PayoutService (process, complete, fail)
  □ AntiFraudService (check_deposit, check_withdrawal)

WEBHOOK:
  □ RUkassa webhook (проверка подписи, IP whitelist)
  □ NOWpayments webhook (HMAC SHA-512)
  □ WebhookLog для каждого запроса
  □ Идемпотентность
  □ CSRF exempt

СТРАНИЦЫ:
  □ Пополнение (реальные провайдеры)
  □ Крипто-оплата (адрес, QR, таймер, polling)
  □ Успешная оплата
  □ Неудачная оплата
  □ Вывод (реальные методы)
  □ Статус вывода
  □ Сохранённые реквизиты

CELERY:
  □ Проверка pending депозитов
  □ Проверка pending выплат
  □ Expiration старых заказов
  □ Retry failed payouts
  □ Ежедневный отчёт
  □ Health check провайдеров
  □ Reconciliation

БЕЗОПАСНОСТЬ:
  □ Подписи webhook проверяются
  □ IP whitelist для webhook
  □ Антифрод при депозите
  □ Антифрод при выводе
  □ Шифрование реквизитов
  □ Маскирование номеров карт
  □ 2FA при выводе
  □ Rate limiting
  □ Логирование ВСЕХ операций

АДМИНКА:
  □ Управление провайдерами
  □ Управление методами
  □ Просмотр депозитов
  □ Просмотр выплат
  □ Просмотр webhook логов
  □ Дашборд платежей
  □ Ручное подтверждение/отмена
```

---

```
╔══════════════════════════════════════════════════════╗
║                                                      ║
║   ЭТАП 3 ЗАВЕРШЁН                                   ║
║                                                      ║
║   Следующий: ЭТАП 4                                 ║
║   Ставки на спорт                                   ║
║                                                      ║
║   Продолжить?                                       ║
║                                                      ║
╚══════════════════════════════════════════════════════╝
```