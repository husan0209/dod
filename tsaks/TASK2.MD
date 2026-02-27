

# 📋 ТЗ ПРОЕКТА DOD — ЭТАП 2

# КОШЕЛЁК + МУЛЬТИВАЛЮТНОСТЬ + KYC

```
╔══════════════════════════════════════════════════════╗
║                                                      ║
║   ПРОЕКТ:    DOD                                    ║
║   ЭТАП:      2 из 12                                ║
║   НАЗВАНИЕ:  Кошелёк + Мультивалютность + KYC       ║
║   ЗАВИСИТ:   Этап 1 (accounts) полностью готов      ║
║                                                      ║
║   ЦЕЛЬ:      Пользователь может хранить деньги      ║
║              в разных валютах, конвертировать,       ║
║              видеть историю всех операций,           ║
║              пройти KYC для больших выводов          ║
║                                                      ║
╚══════════════════════════════════════════════════════╝
```

---

## 📌 КОНТЕКСТ ДЛЯ ИИ-АГЕНТА

```
Ты продолжаешь разработку проекта DOD.
Этап 1 (авторизация) полностью готов.

Сейчас ты создаёшь модуль кошелька.
Это КРИТИЧЕСКИЙ модуль — все деньги проходят через него.
Спорт, казино, predictions — все будут зависеть от wallet.

ГЛАВНОЕ ПРАВИЛО:
  Баланс пользователя НИКОГДА не меняется напрямую.
  Каждое изменение баланса = запись Transaction.
  Все операции с деньгами АТОМАРНЫЕ (database transaction).
  Баланс НИКОГДА не может быть отрицательным.

Стек: Django 5.1, PostgreSQL 16, Redis 7,
      TailwindCSS, HTMX, Celery.
Дизайн: тёмная тема DOD.
```

---

## ШАГ 2.1 — МОДЕЛИ КОШЕЛЬКА

### Задача

```
Создай приложение wallet со всеми моделями
для работы с деньгами, транзакциями,
валютами и конвертацией.
```

### Структура приложения

```
apps/wallet/
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
│   ├── wallet_service.py      # Основная логика кошелька
│   ├── transaction_service.py # Логика транзакций
│   ├── conversion_service.py  # Конвертация валют
│   ├── withdrawal_service.py  # Логика выводов
│   └── rate_service.py        # Получение курсов валют
├── templatetags/
│   ├── __init__.py
│   └── wallet_tags.py         # Форматирование валют
├── tests/
│   ├── __init__.py
│   ├── test_models.py
│   ├── test_services.py
│   └── test_views.py
├── templates/
│   └── wallet/
│       └── (шаблоны — следующие шаги)
└── migrations/
    └── __init__.py
```

### Модель Currency (models.py)

```
class Currency(models.Model):

    Назначение:
      Справочник всех поддерживаемых валют.
      Управляется через админку.
      Содержит курсы для конвертации.

    Поля:
    ─────
    code:
      тип: CharField, max 10, primary key
      Примеры: 'USD', 'EUR', 'RUB', 'BTC', 'USDT'
      Уникальный

    name:
      тип: CharField, max 100
      Примеры: 'Доллар США', 'Евро', 'Российский рубль'

    symbol:
      тип: CharField, max 10
      Примеры: '$', '€', '₽', '₸', '₿'

    type:
      тип: CharField
      choices: [('fiat', 'Фиатная'), ('crypto', 'Криптовалюта')]

    decimal_places:
      тип: IntegerField
      Фиат: 2 (100.00)
      Крипто: 8 (0.00000001 BTC)
      USDT: 2 (100.00)

    rate_to_usd:
      тип: DecimalField, max_digits=20, decimal_places=10
      Курс к USD (базовая валюта)
      USD = 1.0000000000
      EUR = 1.0800000000 (1 EUR = 1.08 USD)
      RUB = 0.0110000000 (1 RUB = 0.011 USD)
      BTC = 67000.0000000000 (1 BTC = 67000 USD)
      Обновляется автоматически (Celery задача)

    rate_updated_at:
      тип: DateTimeField
      Когда последний раз обновлялся курс

    min_deposit:
      тип: DecimalField
      Минимальное пополнение в этой валюте
      Примеры: USD=5, BTC=0.0001, RUB=500

    min_withdrawal:
      тип: DecimalField
      Минимальный вывод
      Примеры: USD=10, BTC=0.001, RUB=1000

    max_withdrawal_daily:
      тип: DecimalField
      Максимальный вывод в день
      Примеры: USD=10000, BTC=1, RUB=500000

    withdrawal_fee_percent:
      тип: DecimalField
      Комиссия за вывод в процентах
      Примеры: 0 (бесплатно), 1.5 (1.5%), 0.5

    withdrawal_fee_fixed:
      тип: DecimalField
      Фиксированная комиссия за вывод
      Примеры: USD=1.00, BTC=0.0001

    conversion_fee_percent:
      тип: DecimalField
      Комиссия за конвертацию
      По умолчанию: 1.0 (1%)

    is_active:
      тип: BooleanField
      default=True
      Можно временно отключить валюту

    is_deposit_enabled:
      тип: BooleanField
      default=True

    is_withdrawal_enabled:
      тип: BooleanField
      default=True

    icon:
      тип: CharField, max 50
      CSS класс или emoji для иконки
      Примеры: '🇺🇸', '🇪🇺', '🇷🇺', '₿'

    sort_order:
      тип: IntegerField
      Порядок отображения в списке
      default=0

    created_at:
      тип: DateTimeField, auto_now_add

    Методы:
    ───────
    __str__():
      возвращает "USD ($)" или "BTC (₿)"

    format_amount(amount):
      Форматирует сумму с символом и нужным количеством знаков
      USD: "$1,234.56"
      RUB: "₽123,456.78"
      BTC: "₿0.00234500"
      KZT: "₸500,000"

    convert_to_usd(amount):
      Конвертирует сумму в USD по текущему курсу

    convert_from_usd(usd_amount):
      Конвертирует из USD в эту валюту

    Meta:
      verbose_name = 'Валюта'
      verbose_name_plural = 'Валюты'
      ordering = ['sort_order', 'code']

    Начальные данные (fixtures/currencies.json):
      Код  | Символ | Тип    | Знаки | Курс к USD
      ─────┼────────┼────────┼───────┼───────────
      USD  | $      | fiat   | 2     | 1.0
      EUR  | €      | fiat   | 2     | 1.08
      RUB  | ₽      | fiat   | 2     | 0.011
      UAH  | ₴      | fiat   | 2     | 0.024
      KZT  | ₸      | fiat   | 0     | 0.0021
      UZS  | сўм    | fiat   | 0     | 0.000078
      BYN  | Br     | fiat   | 2     | 0.31
      BTC  | ₿      | crypto | 8     | 67000.0
      ETH  | Ξ      | crypto | 8     | 3500.0
      USDT | ₮      | crypto | 2     | 1.0
      TON  | ◎      | crypto | 4     | 7.5
```

### Модель Wallet (models.py)

```
class Wallet(models.Model):

    Назначение:
      Мультивалютный кошелёк пользователя.
      ОДИН пользователь = ОДИН кошелёк.
      Внутри кошелька — балансы по каждой валюте.
      Пользователь выбирает основную валюту отображения.

    Поля:
    ─────
    id:
      тип: UUID, primary key

    user:
      тип: OneToOneField → User
      on_delete: CASCADE
      related_name: 'wallet'

    primary_currency:
      тип: ForeignKey → Currency
      default='USD'
      Основная валюта отображения
      В navbar баланс показывается в этой валюте

    total_deposited:
      тип: DecimalField, max_digits=18, decimal_places=2
      Всего пополнено (в USD эквиваленте)
      Для статистики

    total_withdrawn:
      тип: DecimalField, max_digits=18, decimal_places=2
      Всего выведено (в USD эквиваленте)

    total_wagered:
      тип: DecimalField, max_digits=18, decimal_places=2
      Всего поставлено (для расчёта GGR)

    total_won:
      тип: DecimalField, max_digits=18, decimal_places=2
      Всего выиграно

    is_frozen:
      тип: BooleanField
      default=False
      True = кошелёк заморожен (подозрение в мошенничестве)
      Нельзя ни пополнять, ни выводить

    frozen_reason:
      тип: TextField, nullable
      Причина заморозки

    frozen_at:
      тип: DateTimeField, nullable

    frozen_by:
      тип: ForeignKey → User (админ), nullable

    created_at:
      тип: DateTimeField, auto_now_add

    updated_at:
      тип: DateTimeField, auto_now

    Методы:
    ───────
    get_balance(currency_code):
      Возвращает баланс в указанной валюте.
      Ищет WalletBalance по currency.
      Если нет записи → возвращает 0.

    get_total_balance_usd():
      Суммирует все балансы в USD эквиваленте.
      Для каждого WalletBalance:
        amount * currency.rate_to_usd
      Возвращает общую сумму.

    get_primary_balance():
      Возвращает баланс в primary_currency.

    get_primary_balance_display():
      Форматированный баланс: "$1,234.56"

    has_sufficient_balance(currency_code, amount):
      True если баланс >= amount в указанной валюте.

    Meta:
      verbose_name = 'Кошелёк'
      verbose_name_plural = 'Кошельки'
```

### Модель WalletBalance (models.py)

```
class WalletBalance(models.Model):

    Назначение:
      Баланс в конкретной валюте внутри кошелька.
      Один кошелёк может иметь балансы в нескольких валютах.
      Пример: $100 + €50 + 0.005 BTC

    Поля:
    ─────
    id:
      тип: UUID, primary key

    wallet:
      тип: ForeignKey → Wallet
      on_delete: CASCADE
      related_name: 'balances'

    currency:
      тип: ForeignKey → Currency
      on_delete: PROTECT (нельзя удалить валюту если есть балансы)

    available:
      тип: DecimalField, max_digits=18, decimal_places=8
      default=0
      Доступный баланс (можно использовать)
      НЕ МОЖЕТ быть отрицательным

    frozen:
      тип: DecimalField, max_digits=18, decimal_places=8
      default=0
      Замороженный баланс
      (активные ставки, ожидающие выводы)
      НЕ МОЖЕТ быть отрицательным

    total:
      Свойство (property), НЕ поле в БД
      return available + frozen

    updated_at:
      тип: DateTimeField, auto_now

    Методы:
    ───────
    credit(amount):
      НЕЛЬЗЯ вызывать напрямую!
      Только через TransactionService.
      available += amount

    debit(amount):
      НЕЛЬЗЯ вызывать напрямую!
      Только через TransactionService.
      Проверка: available >= amount
      available -= amount

    freeze(amount):
      Заморозить часть баланса (при ставке).
      Проверка: available >= amount
      available -= amount
      frozen += amount

    unfreeze(amount):
      Разморозить (отмена ставки).
      Проверка: frozen >= amount
      frozen -= amount
      available += amount

    settle_frozen(amount):
      Списать из замороженного (ставка проиграла).
      frozen -= amount

    Meta:
      unique_together = ['wallet', 'currency']
      verbose_name = 'Баланс валюты'

    Constraints:
      CheckConstraint: available >= 0
      CheckConstraint: frozen >= 0
```

### Модель Transaction (models.py)

```
class Transaction(models.Model):

    Назначение:
      КАЖДОЕ изменение баланса = одна Transaction.
      Это журнал ВСЕХ операций. Неизменяемый (append-only).
      Никогда не удаляется и не редактируется.

    Поля:
    ─────
    id:
      тип: UUID, primary key
      Генерируется автоматически

    transaction_id:
      тип: CharField, max 50, уникальный
      Человекочитаемый ID
      Формат: TXN-{timestamp}-{random}
      Пример: TXN-20250315-A7B3C2

    wallet:
      тип: ForeignKey → Wallet
      on_delete: PROTECT (нельзя удалить кошелёк с транзакциями)

    user:
      тип: ForeignKey → User
      on_delete: PROTECT
      Дублирование для удобства запросов

    type:
      тип: CharField
      choices:
        ('deposit', 'Пополнение')
        ('withdrawal', 'Вывод')
        ('bet', 'Ставка')
        ('win', 'Выигрыш')
        ('refund', 'Возврат')
        ('bonus', 'Бонус')
        ('referral', 'Реферальная комиссия')
        ('conversion_debit', 'Конвертация (списание)')
        ('conversion_credit', 'Конвертация (зачисление)')
        ('freeze', 'Заморозка')
        ('unfreeze', 'Разморозка')
        ('fee', 'Комиссия')
        ('adjustment', 'Корректировка (админ)')

    currency:
      тип: ForeignKey → Currency
      Валюта транзакции

    amount:
      тип: DecimalField, max_digits=18, decimal_places=8
      Сумма (всегда положительная)
      Направление определяется по type:
        deposit, win, refund, bonus, referral, unfreeze,
        conversion_credit → зачисление (+)
        withdrawal, bet, fee, freeze,
        conversion_debit → списание (-)

    amount_usd:
      тип: DecimalField, max_digits=18, decimal_places=2
      Эквивалент в USD на момент операции
      Для статистики и отчётов

    fee_amount:
      тип: DecimalField, max_digits=18, decimal_places=8
      default=0
      Комиссия (если есть)

    balance_before:
      тип: DecimalField, max_digits=18, decimal_places=8
      Баланс ДО операции (в этой валюте)

    balance_after:
      тип: DecimalField, max_digits=18, decimal_places=8
      Баланс ПОСЛЕ операции

    status:
      тип: CharField
      choices:
        ('pending', 'В обработке')
        ('completed', 'Завершена')
        ('failed', 'Ошибка')
        ('cancelled', 'Отменена')
        ('rejected', 'Отклонена')
      default: 'completed' (для мгновенных операций)

    reference_type:
      тип: CharField, max 50, nullable
      Тип связанного объекта
      Примеры: 'bet', 'casino_game', 'prediction_trade',
               'withdrawal_request', 'conversion'

    reference_id:
      тип: CharField, max 100, nullable
      ID связанного объекта
      Пример: 'bet_abc123', 'game_xyz789'

    description:
      тип: TextField, nullable
      Человекочитаемое описание
      Примеры:
        "Пополнение через RUkassa"
        "Ставка на Реал — Барселона"
        "Выигрыш в Crash x2.5"
        "Конвертация $100 → ₽9,000"

    metadata:
      тип: JSONField, default=dict
      Дополнительные данные
      Примеры:
        Для deposit: {"payment_method": "card", "provider": "rukassa"}
        Для bet: {"event": "Real vs Barca", "odd": 2.10}
        Для conversion: {"from": "USD", "to": "RUB", "rate": 90.5}

    ip_address:
      тип: GenericIPAddressField, nullable
      IP с которого была операция

    created_by:
      тип: ForeignKey → User, nullable
      Кто инициировал (для корректировок админа)

    created_at:
      тип: DateTimeField, auto_now_add
      ИНДЕКС для быстрых запросов

    updated_at:
      тип: DateTimeField, auto_now

    Методы:
    ───────
    __str__():
      "TXN-20250315-A7B3C2: deposit +$100.00"

    is_credit():
      True если зачисление (deposit, win, refund, bonus, referral,
                             conversion_credit, unfreeze)

    is_debit():
      True если списание (withdrawal, bet, fee, freeze,
                           conversion_debit)

    get_signed_amount():
      Возвращает +amount или -amount в зависимости от типа

    get_type_icon():
      deposit → 📥
      withdrawal → 📤
      bet → 🎯
      win → 🏆
      refund → ↩️
      bonus → 🎁
      referral → 🤝
      conversion → 🔄
      fee → 💸
      adjustment → ⚙️

    Meta:
      verbose_name = 'Транзакция'
      verbose_name_plural = 'Транзакции'
      ordering = ['-created_at']
      indexes:
        - wallet + created_at
        - user + created_at
        - type
        - status
        - reference_type + reference_id
        - transaction_id
```

### Модель WithdrawalRequest (models.py)

```
class WithdrawalRequest(models.Model):

    Назначение:
      Заявка на вывод средств.
      Маленькие суммы → автовывод.
      Большие суммы → ручное подтверждение админом.
      Подозрительные → флаг для проверки.

    Поля:
    ─────
    id:
      тип: UUID, primary key

    request_id:
      тип: CharField, max 50, уникальный
      Формат: WD-{timestamp}-{random}
      Пример: WD-20250315-X4Y5Z6

    wallet:
      тип: ForeignKey → Wallet

    user:
      тип: ForeignKey → User

    currency:
      тип: ForeignKey → Currency

    amount:
      тип: DecimalField
      Сумма вывода

    fee_amount:
      тип: DecimalField
      Комиссия за вывод
      Рассчитывается автоматически из Currency настроек

    net_amount:
      тип: DecimalField
      Сумма к получению (amount - fee_amount)

    payment_method:
      тип: CharField
      choices:
        ('card', 'Банковская карта')
        ('crypto', 'Криптовалюта')
        ('ewallet', 'Электронный кошелёк')

    payment_details:
      тип: JSONField
      Реквизиты для выплаты
      Для карты: {"card_number": "4***1234", "holder": "IVAN IVANOV"}
      Для крипто: {"address": "0x...", "network": "TRC20"}
      Для кошелька: {"wallet_id": "...", "provider": "qiwi"}
      ВАЖНО: номер карты маскируется при сохранении!

    status:
      тип: CharField
      choices:
        ('pending', 'Ожидает обработки')
        ('auto_approved', 'Автоматически одобрена')
        ('manual_review', 'На ручной проверке')
        ('approved', 'Одобрена')
        ('processing', 'Обрабатывается')
        ('completed', 'Выполнена')
        ('rejected', 'Отклонена')
        ('cancelled', 'Отменена пользователем')
      default: 'pending'

    risk_level:
      тип: CharField
      choices:
        ('low', '🟢 Низкий')
        ('medium', '🟡 Средний')
        ('high', '🔴 Высокий')
        ('critical', '⛔ Критический')
      Рассчитывается автоматически

    risk_factors:
      тип: JSONField, default=list
      Список причин повышения риска
      Примеры:
        ["new_account", "Аккаунт моложе 24 часов"]
        ["large_amount", "Сумма превышает $5,000"]
        ["no_bets", "Нет ставок между депозитом и выводом"]
        ["ip_changed", "IP изменился"]
        ["multiple_withdrawals", "3+ выводов за час"]
        ["kyc_not_passed", "KYC не пройдена"]
        ["suspicious_pattern", "Подозрительный паттерн"]

    auto_withdrawal_limit:
      тип: DecimalField, nullable
      Лимит автовывода для этого пользователя
      Берётся из настроек + trust_level

    reviewed_by:
      тип: ForeignKey → User (админ), nullable

    reviewed_at:
      тип: DateTimeField, nullable

    review_comment:
      тип: TextField, nullable
      Комментарий админа при одобрении/отклонении

    rejection_reason:
      тип: CharField, nullable
      Причина отклонения (показывается пользователю)

    transaction:
      тип: OneToOneField → Transaction, nullable
      Связь с транзакцией списания

    external_id:
      тип: CharField, nullable
      ID транзакции в платёжной системе

    completed_at:
      тип: DateTimeField, nullable

    expires_at:
      тип: DateTimeField
      Заявка истекает через 72 часа если не обработана
      default: now + 72h

    ip_address:
      тип: GenericIPAddressField

    user_agent:
      тип: TextField, nullable

    created_at:
      тип: DateTimeField, auto_now_add

    updated_at:
      тип: DateTimeField, auto_now

    Методы:
    ───────
    calculate_risk_level():
      Автоматический расчёт риска.

      Факторы повышающие риск:
        +1 уровень: аккаунт < 24 часов
        +1 уровень: сумма > дневного лимита * 0.5
        +1 уровень: нет ставок (депозит → сразу вывод)
        +1 уровень: IP отличается от registration_ip
        +1 уровень: KYC не пройдена при сумме > порога
        +1 уровень: 3+ выводов за последний час
        +1 уровень: устройство новое
        +1 уровень: страна отличается от обычной

      Уровни:
        0 факторов → low
        1-2 фактора → medium
        3-4 фактора → high
        5+ факторов → critical

    can_auto_approve():
      True если:
        - risk_level == 'low'
        - amount <= auto_withdrawal_limit
        - user.trust_level >= 2
        - user.kyc_status == 'approved' (если сумма > порога)
        - Нет заморозки кошелька

    Meta:
      verbose_name = 'Заявка на вывод'
      ordering = ['-created_at']
      indexes:
        - status
        - risk_level
        - user + created_at
```

### Модель ConversionOrder (models.py)

```
class ConversionOrder(models.Model):

    Назначение:
      Запись конвертации валют внутри кошелька.
      Пример: $100 → ₽9,000

    Поля:
    ─────
    id:
      тип: UUID, primary key

    wallet:
      тип: ForeignKey → Wallet

    user:
      тип: ForeignKey → User

    from_currency:
      тип: ForeignKey → Currency, related_name='conversions_from'

    to_currency:
      тип: ForeignKey → Currency, related_name='conversions_to'

    from_amount:
      тип: DecimalField
      Сумма списания (исходная валюта)

    to_amount:
      тип: DecimalField
      Сумма зачисления (целевая валюта)

    exchange_rate:
      тип: DecimalField, max_digits=20, decimal_places=10
      Курс конвертации на момент операции

    fee_percent:
      тип: DecimalField
      Процент комиссии

    fee_amount:
      тип: DecimalField
      Сумма комиссии (в исходной валюте)

    status:
      тип: CharField
      choices: completed / failed

    debit_transaction:
      тип: ForeignKey → Transaction (списание)

    credit_transaction:
      тип: ForeignKey → Transaction (зачисление)

    created_at:
      тип: DateTimeField, auto_now_add

    Meta:
      verbose_name = 'Конвертация'
      ordering = ['-created_at']
```

### Модель KYCVerification (models.py)

```
class KYCVerification(models.Model):

    Назначение:
      Заявка на верификацию личности.
      Обязательна при выводе больших сумм.

    Поля:
    ─────
    id:
      тип: UUID, primary key

    user:
      тип: OneToOneField → User
      related_name: 'kyc'

    status:
      тип: CharField
      choices:
        ('not_submitted', 'Не подана')
        ('pending', 'На проверке')
        ('approved', 'Одобрена')
        ('rejected', 'Отклонена')
      default: 'not_submitted'

    document_type:
      тип: CharField, nullable
      choices:
        ('passport', 'Паспорт')
        ('national_id', 'ID карта')
        ('drivers_license', 'Водительское удостоверение')

    document_front:
      тип: ImageField
      Фото лицевой стороны документа
      Путь: kyc/{user_id}/front_{timestamp}.jpg
      Максимум 10 MB

    document_back:
      тип: ImageField, nullable
      Фото обратной стороны (если нужно)

    selfie_with_document:
      тип: ImageField
      Селфи с документом в руке
      Максимум 10 MB

    full_name:
      тип: CharField, max 200
      Полное имя как в документе

    document_number:
      тип: CharField, max 50
      Номер документа
      ШИФРУЕТСЯ в БД (encryption)

    date_of_birth:
      тип: DateField

    country_of_issue:
      тип: CountryField

    expiry_date:
      тип: DateField, nullable
      Срок действия документа

    address:
      тип: TextField, nullable
      Адрес проживания

    submitted_at:
      тип: DateTimeField, nullable
      Когда подана заявка

    reviewed_by:
      тип: ForeignKey → User (админ), nullable

    reviewed_at:
      тип: DateTimeField, nullable

    review_comment:
      тип: TextField, nullable
      Комментарий от проверяющего

    rejection_reason:
      тип: CharField, nullable
      choices:
        ('blurry', 'Нечёткое фото')
        ('expired', 'Документ просрочен')
        ('mismatch', 'Данные не совпадают')
        ('fake', 'Подозрение на подделку')
        ('other', 'Другое')

    attempts:
      тип: IntegerField
      default=0
      Количество попыток подачи
      Максимум 3, потом → обращение в поддержку

    ip_address:
      тип: GenericIPAddressField, nullable
      IP при подаче

    created_at:
      тип: DateTimeField, auto_now_add

    updated_at:
      тип: DateTimeField, auto_now

    Методы:
    ───────
    is_expired():
      True если документ просрочен

    can_resubmit():
      True если attempts < 3 и status == 'rejected'

    Meta:
      verbose_name = 'KYC Верификация'

    ВАЖНО ПО БЕЗОПАСНОСТИ:
      - Фото документов хранятся в ЗАЩИЩЁННОЙ папке
      - Доступ только авторизованным админам
      - Номер документа ШИФРУЕТСЯ
      - Логирование всех просмотров KYC данных
```

### Модель WalletSettings (models.py)

```
class WalletSettings(models.Model):

    Назначение:
      Глобальные настройки кошелька.
      Управляются через админку.
      Singleton (одна запись).

    Поля:
    ─────
    auto_withdrawal_limit_default:
      тип: DecimalField
      Лимит автовывода для новых пользователей (в USD)
      default=100

    auto_withdrawal_limit_verified:
      тип: DecimalField
      Лимит для пользователей с KYC (в USD)
      default=5000

    auto_withdrawal_limit_trusted:
      тип: DecimalField
      Лимит для trust_level >= 4 (в USD)
      default=10000

    kyc_required_amount:
      тип: DecimalField
      Сумма вывода при которой KYC обязательна (в USD)
      default=1000

    max_daily_withdrawal_usd:
      тип: DecimalField
      Максимум вывода в день для одного пользователя (в USD)
      default=50000

    new_account_withdrawal_delay_hours:
      тип: IntegerField
      Через сколько часов новый аккаунт может делать вывод
      default=24

    min_bets_before_withdrawal:
      тип: IntegerField
      Минимум ставок перед выводом (анти-отмывание)
      default=0 (выключено)

    conversion_enabled:
      тип: BooleanField
      default=True

    registration_bonus_amount:
      тип: DecimalField
      Бонус при регистрации (в USD)
      default=0

    registration_bonus_currency:
      тип: CharField
      default='USD'

    Meta:
      verbose_name = 'Настройки кошелька'

    Метод:
      @classmethod
      get_settings():
        Возвращает единственный экземпляр.
        Если нет → создаёт с дефолтными значениями.
        Кэшируется в Redis на 5 минут.
```

### Файл admin.py

```
CurrencyAdmin:
  list_display: code, name, symbol, type, rate_to_usd,
                is_active, is_deposit_enabled, is_withdrawal_enabled
  list_filter: type, is_active
  list_editable: rate_to_usd, is_active, is_deposit_enabled,
                 is_withdrawal_enabled, min_deposit, min_withdrawal
  search_fields: code, name

WalletAdmin:
  list_display: user, primary_currency, total_deposited,
                total_withdrawn, is_frozen, created_at
  list_filter: is_frozen, primary_currency
  search_fields: user__email, user__username
  readonly_fields: total_deposited, total_withdrawn,
                   total_wagered, total_won
  inlines: [WalletBalanceInline]

WalletBalanceInline:
  model: WalletBalance
  extra: 0
  readonly_fields: available, frozen

TransactionAdmin:
  list_display: transaction_id, user, type, currency,
                amount, status, created_at
  list_filter: type, status, currency, created_at
  search_fields: transaction_id, user__email, description
  readonly_fields: ВСЕ ПОЛЯ (транзакции нельзя редактировать!)
  date_hierarchy: created_at

  actions:
    - Экспорт в CSV
    - Экспорт в Excel

WithdrawalRequestAdmin:
  list_display: request_id, user, currency, amount,
                status, risk_level, created_at
  list_filter: status, risk_level, currency, created_at
  search_fields: request_id, user__email
  readonly_fields: risk_factors, ip_address, user_agent

  actions:
    - Одобрить выбранные (с проверкой)
    - Отклонить выбранные (с вводом причины)

  Кастомная страница для ревью:
    Показывает:
    - Все данные заявки
    - Профиль пользователя
    - Историю транзакций за последние 7 дней
    - Предыдущие выводы
    - Факторы риска (подробно)
    - KYC статус
    - Кнопки: Одобрить / Отклонить (с комментарием)

KYCVerificationAdmin:
  list_display: user, status, document_type,
                submitted_at, reviewed_by
  list_filter: status, document_type, country_of_issue
  search_fields: user__email, full_name
  readonly_fields: document_front, document_back,
                   selfie_with_document (превью)
  
  actions:
    - Одобрить
    - Отклонить (с причиной)

WalletSettingsAdmin:
  Singleton — одна запись.
  Все поля редактируемые.
```

### Критерий готовности шага 2.1

```
□ Модель Currency создана с начальными данными (11 валют)
□ Модель Wallet создана
□ Модель WalletBalance создана с constraints
□ Модель Transaction создана с ВСЕМИ типами
□ Модель WithdrawalRequest создана с системой рисков
□ Модель ConversionOrder создана
□ Модель KYCVerification создана
□ Модель WalletSettings создана (singleton)
□ Все миграции применены
□ Admin настроен для всех моделей
□ Fixtures с валютами загружены
□ Транзакции в админке READONLY
```

---

## ШАГ 2.2 — СЕРВИСЫ КОШЕЛЬКА (БИЗНЕС-ЛОГИКА)

### Задача

```
Создай сервисы для работы с кошельком.
ВСЯ логика с деньгами — ТОЛЬКО через сервисы.
Views НИКОГДА не работают с балансом напрямую.
```

### WalletService (services/wallet_service.py)

```
class WalletService:

    Назначение:
      Создание кошелька.
      Получение балансов.
      Базовые операции.

    Методы:
    ───────

    @staticmethod
    create_wallet(user):
      Создаёт кошелёк для пользователя.
      Вызывается при регистрации (signal).
      
      Логика:
        1. Создать Wallet с primary_currency='USD'
        2. Создать WalletBalance для USD (available=0)
        3. Если есть registration_bonus → начислить
        4. Вернуть wallet

    @staticmethod
    get_or_create_balance(wallet, currency_code):
      Получает WalletBalance для валюты.
      Если нет → создаёт с нулевым балансом.
      Возвращает WalletBalance.

    @staticmethod
    get_all_balances(wallet):
      Возвращает список всех балансов с суммами > 0.
      Формат:
        [
          {"currency": "USD", "symbol": "$",
           "available": 100.00, "frozen": 10.00,
           "total": 110.00, "usd_equivalent": 110.00},
          {"currency": "BTC", "symbol": "₿",
           "available": 0.005, "frozen": 0,
           "total": 0.005, "usd_equivalent": 335.00},
        ]

    @staticmethod
    get_total_balance_usd(wallet):
      Суммирует все балансы в USD.
      Возвращает Decimal.

    @staticmethod
    change_primary_currency(wallet, currency_code):
      Меняет основную валюту отображения.
      Обновляет wallet.primary_currency.
```

### TransactionService (services/transaction_service.py)

```
class TransactionService:

    Назначение:
      ВСЕ операции с деньгами проходят через этот сервис.
      Каждая операция АТОМАРНАЯ (select_for_update + transaction.atomic).
      Каждая операция создаёт запись Transaction.

    ВАЖНЕЙШИЕ ПРАВИЛА:
      1. ВСЕГДА использовать select_for_update() при чтении баланса
      2. ВСЕГДА внутри transaction.atomic()
      3. ВСЕГДА проверять достаточность средств ПЕРЕД операцией
      4. ВСЕГДА записывать balance_before и balance_after
      5. НИКОГДА не ловить и не глотать исключения тихо

    Методы:
    ───────

    @staticmethod
    def deposit(wallet, currency_code, amount,
                description="", metadata=None, ip_address=None):
      
      Пополнение баланса.
      
      Логика (АТОМАРНО):
        1. Получить WalletBalance с блокировкой (select_for_update)
        2. balance_before = balance.available
        3. balance.available += amount
        4. balance_after = balance.available
        5. Сохранить balance
        6. Рассчитать amount_usd = amount * currency.rate_to_usd
        7. Создать Transaction:
           type='deposit'
           status='completed'
           balance_before, balance_after
           amount_usd
        8. Обновить wallet.total_deposited += amount_usd
        9. Вернуть Transaction

      Валидация:
        - amount > 0
        - amount >= currency.min_deposit
        - wallet.is_frozen == False
        - currency.is_deposit_enabled == True

      Ошибки:
        - InsufficientFundsError (не для депозита)
        - WalletFrozenError
        - CurrencyDisabledError
        - InvalidAmountError


    @staticmethod
    def withdraw(wallet, currency_code, amount,
                 description="", metadata=None, ip_address=None):
      
      Списание (для ставок, комиссий и т.д.)
      НЕ для вывода денег! Для вывода → WithdrawalService.
      
      Логика (АТОМАРНО):
        1. Получить WalletBalance с блокировкой
        2. Проверить: balance.available >= amount
        3. Если нет → raise InsufficientFundsError
        4. balance_before = balance.available
        5. balance.available -= amount
        6. balance_after = balance.available
        7. Сохранить
        8. Создать Transaction (type зависит от вызывающего)
        9. Вернуть Transaction

      Валидация:
        - amount > 0
        - Достаточно средств
        - wallet.is_frozen == False


    @staticmethod
    def freeze_funds(wallet, currency_code, amount,
                     reference_type, reference_id):
      
      Заморозить средства (при размещении ставки).
      Деньги списываются из available → в frozen.
      
      Логика (АТОМАРНО):
        1. Получить WalletBalance с блокировкой
        2. Проверить: balance.available >= amount
        3. balance.available -= amount
        4. balance.frozen += amount
        5. Сохранить
        6. Создать Transaction type='freeze'
        7. Вернуть Transaction


    @staticmethod
    def unfreeze_funds(wallet, currency_code, amount,
                       reference_type, reference_id):
      
      Разморозить средства (отмена ставки).
      Деньги возвращаются из frozen → в available.
      
      Логика (АТОМАРНО):
        1. Получить WalletBalance с блокировкой
        2. Проверить: balance.frozen >= amount
        3. balance.frozen -= amount
        4. balance.available += amount
        5. Сохранить
        6. Создать Transaction type='unfreeze'
        7. Вернуть Transaction


    @staticmethod
    def settle_bet(wallet, currency_code, frozen_amount,
                   win_amount, reference_type, reference_id):
      
      Расчёт ставки.
      Если выиграл: frozen → убрать, зачислить win_amount.
      Если проиграл: frozen → убрать (деньги уходят).
      
      Логика (АТОМАРНО):
        1. Получить WalletBalance с блокировкой
        2. balance.frozen -= frozen_amount

        Если win_amount > 0 (выигрыш):
          3. balance.available += win_amount
          4. Создать Transaction type='win'
          5. wallet.total_won += win_amount_usd

        Если win_amount == 0 (проигрыш):
          3. Создать Transaction type='bet' (списание)
          4. wallet.total_wagered += frozen_amount_usd


    @staticmethod
    def credit_bonus(wallet, currency_code, amount, description):
      
      Начисление бонуса.
      
      Логика:
        deposit() с type='bonus'


    @staticmethod
    def credit_referral(wallet, currency_code, amount,
                        referral_user_id):
      
      Начисление реферальной комиссии.
      
      Логика:
        deposit() с type='referral'
        metadata = {"from_user": referral_user_id}


    @staticmethod
    def admin_adjustment(wallet, currency_code, amount,
                         is_credit, admin_user, reason):
      
      Ручная корректировка баланса админом.
      
      Логика:
        Если is_credit: deposit()
        Если не is_credit: withdraw()
        type='adjustment'
        created_by=admin_user
        description=reason
        ОБЯЗАТЕЛЬНО логирование в audit log
```

### ConversionService (services/conversion_service.py)

```
class ConversionService:

    Назначение:
      Конвертация валют внутри кошелька.
      Пример: $100 → ₽9,000

    Методы:
    ───────

    @staticmethod
    def get_conversion_rate(from_currency, to_currency):
      
      Получить курс конвертации.
      
      Логика:
        1. from_rate = from_currency.rate_to_usd
        2. to_rate = to_currency.rate_to_usd
        3. rate = from_rate / to_rate
        4. Вернуть rate

      Пример:
        USD → RUB: 1.0 / 0.011 = 90.909 (1 USD = 90.9 RUB)
        EUR → USD: 1.08 / 1.0 = 1.08 (1 EUR = 1.08 USD)
        BTC → USDT: 67000 / 1.0 = 67000 (1 BTC = 67000 USDT)


    @staticmethod
    def preview_conversion(wallet, from_code, to_code, amount):
      
      Предпросмотр конвертации (БЕЗ выполнения).
      Показывается пользователю перед подтверждением.
      
      Возвращает:
        {
          "from_currency": "USD",
          "to_currency": "RUB",
          "from_amount": 100.00,
          "exchange_rate": 90.909,
          "fee_percent": 1.0,
          "fee_amount": 1.00,
          "net_from_amount": 99.00,
          "to_amount": 8999.99,
          "rate_expires_in": 30  # секунд
        }


    @staticmethod
    def execute_conversion(wallet, from_code, to_code, amount):
      
      Выполнить конвертацию.
      
      Логика (АТОМАРНО):
        1. Получить курс
        2. Рассчитать комиссию
        3. Рассчитать to_amount
        4. Проверить баланс from_currency >= amount
        5. Списать from_currency (TransactionService.withdraw)
           type='conversion_debit'
        6. Зачислить to_currency (TransactionService.deposit)
           type='conversion_credit'
        7. Создать ConversionOrder
        8. Вернуть ConversionOrder

      Валидация:
        - amount > 0
        - from_code != to_code
        - Достаточно средств
        - Конвертация включена (WalletSettings)
        - Обе валюты активны
```

### WithdrawalService (services/withdrawal_service.py)

```
class WithdrawalService:

    Назначение:
      Обработка заявок на вывод средств.
      Расчёт рисков.
      Автовывод / ручная проверка.

    Методы:
    ───────

    @staticmethod
    def create_withdrawal_request(wallet, currency_code, amount,
                                   payment_method, payment_details,
                                   ip_address, user_agent):
      
      Создать заявку на вывод.
      
      Логика:
        1. ВАЛИДАЦИЯ:
           - amount > 0
           - amount >= currency.min_withdrawal
           - wallet.is_frozen == False
           - currency.is_withdrawal_enabled == True
           - Проверить дневной лимит
           - Проверить: нет ли уже pending заявки
           - Если KYC нужна (amount_usd > kyc_required_amount):
             → user.kyc_status == 'approved'
             → Иначе ошибка "Пройдите KYC"
           - Если аккаунт новый (< withdrawal_delay_hours):
             → Ошибка "Вывод доступен через X часов"

        2. Рассчитать комиссию:
           fee = amount * currency.withdrawal_fee_percent / 100
           fee += currency.withdrawal_fee_fixed
           net_amount = amount - fee

        3. ЗАМОРОЗИТЬ средства:
           TransactionService.freeze_funds(
             wallet, currency, amount,
             'withdrawal_request', request_id
           )

        4. Рассчитать риск:
           risk_level = calculate_risk_level()
           risk_factors = get_risk_factors()

        5. Создать WithdrawalRequest

        6. Определить обработку:
           Если can_auto_approve():
             → status = 'auto_approved'
             → Запустить Celery задачу process_withdrawal
           Иначе:
             → status = 'manual_review'
             → Уведомить админов

        7. Уведомить пользователя (email/telegram)
        8. Вернуть WithdrawalRequest


    @staticmethod
    def calculate_risk_level(user, wallet, amount, currency,
                              ip_address, user_agent):
      
      Рассчитать уровень риска.
      
      Факторы:

        account_age_hours = (now - user.created_at).total_hours
        if account_age_hours < 24:
          risk_factors.append("new_account")

        amount_usd = amount * currency.rate_to_usd
        daily_limit = WalletSettings.max_daily_withdrawal_usd
        if amount_usd > daily_limit * 0.5:
          risk_factors.append("large_amount")

        recent_bets = Transaction.filter(
          user=user, type='bet',
          created_at__gte=last_deposit_time
        ).count()
        if recent_bets == 0:
          risk_factors.append("no_bets_after_deposit")

        if ip_address != user.registration_ip:
          risk_factors.append("ip_mismatch")

        if user.kyc_status != 'approved' and amount_usd > 500:
          risk_factors.append("kyc_not_passed")

        recent_withdrawals = WithdrawalRequest.filter(
          user=user,
          created_at__gte=now - 1hour,
          status__in=['pending', 'auto_approved', 'completed']
        ).count()
        if recent_withdrawals >= 3:
          risk_factors.append("multiple_withdrawals")

        known_devices = ActiveSession.filter(user=user).values('device_name')
        current_device = parse_user_agent(user_agent)
        if current_device not in known_devices:
          risk_factors.append("unknown_device")

        usual_country = most_common_country(user)
        current_country = geoip_country(ip_address)
        if current_country != usual_country:
          risk_factors.append("unusual_country")

        total_deposited = wallet.total_deposited
        total_withdrawn = wallet.total_withdrawn
        if total_withdrawn > total_deposited * 0.9:
          risk_factors.append("withdrawal_exceeds_deposits")

      Уровень:
        len(risk_factors) == 0 → 'low'
        len(risk_factors) <= 2 → 'medium'
        len(risk_factors) <= 4 → 'high'
        len(risk_factors) >= 5 → 'critical'


    @staticmethod
    def approve_withdrawal(request_id, admin_user, comment=""):
      
      Одобрить заявку (ручное).
      
      Логика:
        1. Найти WithdrawalRequest
        2. Проверить status == 'manual_review'
        3. status = 'approved'
        4. reviewed_by = admin_user
        5. reviewed_at = now
        6. review_comment = comment
        7. Запустить Celery задачу process_withdrawal
        8. Уведомить пользователя


    @staticmethod
    def reject_withdrawal(request_id, admin_user, reason, comment=""):
      
      Отклонить заявку.
      
      Логика:
        1. Найти WithdrawalRequest
        2. status = 'rejected'
        3. rejection_reason = reason
        4. РАЗМОРОЗИТЬ средства:
           TransactionService.unfreeze_funds()
        5. Уведомить пользователя


    @staticmethod
    def cancel_withdrawal(request_id, user):
      
      Отмена пользователем (пока pending или manual_review).
      
      Логика:
        1. Проверить что заявка принадлежит user
        2. Проверить status in ('pending', 'manual_review')
        3. status = 'cancelled'
        4. РАЗМОРОЗИТЬ средства
        5. Уведомить пользователя


    @staticmethod
    def process_withdrawal(request_id):
      
      Celery задача. Отправка денег.
      
      Логика:
        1. Найти WithdrawalRequest
        2. status = 'processing'
        3. Вызвать платёжную систему (Этап 4)
           Пока → имитация (status = 'completed')
        4. Если успешно:
           - Списать из frozen
             TransactionService.settle_frozen()
           - status = 'completed'
           - completed_at = now
           - Создать Transaction type='withdrawal'
           - wallet.total_withdrawn += amount_usd
        5. Если ошибка:
           - status = 'failed'
           - РАЗМОРОЗИТЬ средства
           - Уведомить пользователя + админов
```

### RateService (services/rate_service.py)

```
class RateService:

    Назначение:
      Получение и обновление курсов валют.

    Методы:
    ───────

    @staticmethod
    def update_all_rates():
      
      Celery periodic task (каждые 15 минут).
      
      Логика:
        1. Получить курсы фиат из бесплатного API:
           exchangerate-api.com (бесплатный тариф)
           или open.er-api.com

        2. Получить курсы крипто:
           CoinGecko API (бесплатный)
           или CoinMarketCap API

        3. Обновить Currency.rate_to_usd для каждой валюты
        4. Обновить Currency.rate_updated_at
        5. Кэшировать в Redis на 15 минут
        6. Логировать изменения

      Обработка ошибок:
        - Если API недоступен → использовать последний известный курс
        - Если курс изменился больше чем на 10% → пометить для проверки
        - Уведомить админа если API не отвечает > 1 часа


    @staticmethod
    def get_rate(from_code, to_code):
      
      Получить текущий курс.
      
      Логика:
        1. Проверить Redis кэш
        2. Если есть → вернуть
        3. Если нет → взять из БД
        4. Рассчитать cross-rate
        5. Кэшировать
        6. Вернуть
```

### Файл tasks.py (Celery)

```
Фоновые задачи:

process_withdrawal_task(request_id):
    Обработка вывода (вызов платёжной системы).
    Retry: 3 попытки с интервалом 5 мин.

update_exchange_rates():
    Обновление курсов валют.
    Периодическая: каждые 15 минут.

check_expired_withdrawals():
    Отменить заявки старше 72 часов.
    Разморозить средства.
    Периодическая: каждый час.

notify_admins_pending_withdrawals():
    Уведомить админов о заявках на ручной проверке.
    Если заявка висит > 2 часов → напомнить.
    Периодическая: каждые 30 минут.

daily_wallet_reconciliation():
    Ежедневная сверка:
    Сумма всех транзакций == текущий баланс.
    Если расхождение → КРИТИЧЕСКОЕ уведомление.
    Периодическая: каждый день в 03:00 UTC.
```

### Файл signals.py

```
post_save(User):
    При создании пользователя:
    → WalletService.create_wallet(user)

    При этом:
    - Создаётся Wallet
    - Создаётся WalletBalance для USD (0)
    - Если есть registration_bonus → начисляется
```

### Критерий готовности шага 2.2

```
□ WalletService: create_wallet, get_balances, get_total
□ TransactionService: deposit, withdraw, freeze, unfreeze, settle
□ ConversionService: get_rate, preview, execute
□ WithdrawalService: create, calculate_risk, approve, reject, cancel
□ RateService: update_rates, get_rate
□ ВСЕ операции атомарные (select_for_update + atomic)
□ ВСЕ операции создают Transaction
□ balance_before и balance_after записываются
□ Баланс НИКОГДА не отрицательный
□ Celery задачи настроены
□ Signal создаёт кошелёк при регистрации
□ Сверка балансов (reconciliation)
```

---

## ШАГ 2.3 — СТРАНИЦЫ КОШЕЛЬКА

### Задача

```
Создай все страницы кошелька:
главная, пополнение, вывод, конвертация,
история транзакций, KYC верификация.
```

### Структура шаблонов

```
templates/wallet/
├── overview.html           # Главная страница кошелька
├── deposit.html            # Пополнение
├── withdraw.html           # Вывод
├── withdraw_confirm.html   # Подтверждение вывода (2FA)
├── conversion.html         # Конвертация валют
├── transactions.html       # История транзакций
├── transaction_detail.html # Детали транзакции
├── withdrawal_status.html  # Статус заявки на вывод
├── kyc/
│   ├── kyc_start.html      # Начало KYC
│   ├── kyc_form.html       # Форма KYC
│   ├── kyc_status.html     # Статус KYC
│   └── kyc_required.html   # "Нужна KYC для вывода"
└── components/
    ├── balance_card.html   # Карточка баланса (переиспользуемая)
    ├── currency_selector.html  # Выбор валюты
    └── transaction_row.html    # Строка транзакции
```

### Главная страница кошелька

```
URL: /wallet/
Доступ: @login_required

  ┌──────────────────────────────────────────────────────┐
  │  💰 Мой кошелёк                                     │
  │                                                      │
  │  ┌───────────────────────────────────────────────┐  │
  │  │  Общий баланс (в USD)                         │  │
  │  │                                               │  │
  │  │  $12,345.67                                   │  │
  │  │                                               │  │
  │  │  [Пополнить]  [Вывести]  [Конвертировать]    │  │
  │  └───────────────────────────────────────────────┘  │
  │                                                      │
  │  ── Мои балансы ──────────────────────────────────  │
  │                                                      │
  │  ┌──────────────────────────────────────────────┐   │
  │  │ 🇺🇸 USD    $10,000.00          ★ основная   │   │
  │  │            Заморожено: $500.00               │   │
  │  │            [Пополнить] [Вывести]             │   │
  │  ├──────────────────────────────────────────────┤   │
  │  │ ₿ BTC     0.00500000  ≈ $335.00             │   │
  │  │            Заморожено: 0                     │   │
  │  │            [Пополнить] [Вывести]             │   │
  │  ├──────────────────────────────────────────────┤   │
  │  │ ₽ RUB     ₽185,000.00  ≈ $2,010.67         │   │
  │  │            Заморожено: ₽5,000               │   │
  │  │            [Пополнить] [Вывести]             │   │
  │  └──────────────────────────────────────────────┘   │
  │                                                      │
  │  Основная валюта: [USD ▼] ← dropdown, меняет        │
  │  отображение баланса в navbar                        │
  │                                                      │
  │  ── Последние операции ────────────────────────────  │
  │                                                      │
  │  📥 +$500.00     Пополнение (карта)      Сегодня   │
  │  🎯 -$50.00     Ставка: Реал — Барса    Сегодня   │
  │  🏆 +$105.00    Выигрыш: Crash x2.1     Вчера     │
  │  🔄 -$100 → +₽9,090  Конвертация        Вчера     │
  │  📤 -₽50,000    Вывод (карта)            2 дня     │
  │                                                      │
  │  [Показать все транзакции →]                        │
  │                                                      │
  │  ── Ожидающие выводы ──────────────────────────────  │
  │  (показывается если есть pending/manual_review)     │
  │                                                      │
  │  🕐 WD-20250315-X4Y5Z6  $1,000  На проверке       │
  │     [Отменить]                                      │
  │                                                      │
  └──────────────────────────────────────────────────────┘

HTMX:
  - Баланс обновляется каждые 30 сек
    hx-get="/wallet/api/balances/" hx-trigger="every 30s"
  - Смена основной валюты без перезагрузки
    hx-post="/wallet/api/primary-currency/"
```

### Страница пополнения

```
URL: /wallet/deposit/
URL с валютой: /wallet/deposit/?currency=BTC

  ┌──────────────────────────────────────────────────────┐
  │  📥 Пополнение                                      │
  │                                                      │
  │  Выберите валюту:                                   │
  │  ┌──────────────────────────────────────────────┐   │
  │  │ [🇺🇸 USD] [€ EUR] [₽ RUB] [₴ UAH]          │   │
  │  │ [₸ KZT] [Br BYN]                            │   │
  │  │ [₿ BTC] [Ξ ETH] [₮ USDT] [◎ TON]           │   │
  │  └──────────────────────────────────────────────┘   │
  │                                                      │
  │  Выбрано: 🇺🇸 USD                                  │
  │                                                      │
  │  Сумма:                                             │
  │  ┌────────────────────────────────┐                 │
  │  │ $                         0.00 │                 │
  │  └────────────────────────────────┘                 │
  │  Минимум: $5.00                                     │
  │                                                      │
  │  Быстрый выбор:                                     │
  │  [$10] [$25] [$50] [$100] [$500] [$1000]           │
  │                                                      │
  │  Способ оплаты:                                     │
  │  ┌────────────────────────────────────────────┐    │
  │  │ 💳 Банковская карта (RUkassa)              │    │
  │  │    Visa, MasterCard, МИР                    │    │
  │  │    Комиссия: 0%  •  Мгновенно              │    │
  │  ├────────────────────────────────────────────┤    │
  │  │ 🪙 Криптовалюта (NOWpayments)              │    │
  │  │    BTC, ETH, USDT, TON и другие            │    │
  │  │    Комиссия: 0%  •  10-30 мин              │    │
  │  ├────────────────────────────────────────────┤    │
  │  │ 📱 Электронный кошелёк (RUkassa)           │    │
  │  │    QIWI, ЮMoney, WebMoney                  │    │
  │  │    Комиссия: 0%  •  Мгновенно              │    │
  │  └────────────────────────────────────────────┘    │
  │                                                      │
  │  [Пополнить $100.00]                                │
  │                                                      │
  │  ⓘ После нажатия вы будете перенаправлены          │
  │    на страницу платёжной системы                     │
  │                                                      │
  └──────────────────────────────────────────────────────┘

  Логика:
    1. Пользователь выбирает валюту и сумму
    2. Выбирает способ оплаты
    3. Нажимает "Пополнить"
    4. Создаётся DepositRequest (pending)
    5. Редирект на платёжную систему
       (RUkassa или NOWpayments)
    6. После оплаты → webhook от провайдера
    7. TransactionService.deposit() → баланс обновляется
    8. Редирект обратно на /wallet/ с сообщением "Пополнено!"

    НА ЭТАПЕ 2:
    Платёжные системы ещё не подключены.
    Делаем ДЕМО пополнение:
    Кнопка "Демо пополнение" → мгновенно начисляет
    без реальной оплаты.
    Реальное подключение → Этап 4.
```

### Страница вывода

```
URL: /wallet/withdraw/

  ┌──────────────────────────────────────────────────────┐
  │  📤 Вывод средств                                   │
  │                                                      │
  │  Выберите валюту:                                   │
  │  (показываются только валюты с балансом > 0)        │
  │  [🇺🇸 USD $10,000] [₿ BTC 0.005] [₽ RUB ₽185,000]│
  │                                                      │
  │  Выбрано: 🇺🇸 USD                                  │
  │  Доступно: $9,500.00 (заморожено: $500.00)         │
  │                                                      │
  │  Сумма вывода:                                      │
  │  ┌────────────────────────────────┐                 │
  │  │ $                      1000.00 │                 │
  │  └────────────────────────────────┘                 │
  │  Мин: $10.00 | Макс: $10,000/день                  │
  │  [25%] [50%] [75%] [Всё]                           │
  │                                                      │
  │  Комиссия: $1.00 (0.1%)                            │
  │  Вы получите: $999.00                               │
  │                                                      │
  │  Способ вывода:                                     │
  │  ┌────────────────────────────────────────────┐    │
  │  │ 💳 На карту                                │    │
  │  │    Номер карты: 4***1234                   │    │
  │  │    (сохранённая) [Другая карта]            │    │
  │  ├────────────────────────────────────────────┤    │
  │  │ 🪙 Криптовалюта                            │    │
  │  │    Адрес: ┌────────────────────┐           │    │
  │  │           │ 0x...              │           │    │
  │  │           └────────────────────┘           │    │
  │  │    Сеть: [TRC20 ▼]                        │    │
  │  └────────────────────────────────────────────┘    │
  │                                                      │
  │  [Вывести $1,000.00 →]                             │
  │                                                      │
  │  ⚠️ Заявки на сумму более $1,000 требуют           │
  │     проверки и обрабатываются в течение 24 часов    │
  │                                                      │
  └──────────────────────────────────────────────────────┘

  При нажатии "Вывести":
    → Если 2FA включена → показать форму 2FA
    → Если KYC нужна (большая сумма) → показать kyc_required.html
    → Если всё ок → создать WithdrawalRequest
    → Показать withdrawal_status.html

  Сохранённые реквизиты:
    Пользователь может сохранить карту/адрес
    для быстрого вывода в следующий раз.
    Номер карты маскируется: 4276 **** **** 1234
```

### Страница конвертации

```
URL: /wallet/convert/

  ┌──────────────────────────────────────────────────────┐
  │  🔄 Конвертация валют                               │
  │                                                      │
  │  Из:                                                │
  │  ┌─────────────────────────────────┐                │
  │  │ [🇺🇸 USD ▼]         100.00    │                │
  │  └─────────────────────────────────┘                │
  │  Доступно: $10,000.00                               │
  │                                                      │
  │                   🔄 (кнопка переключения)          │
  │                                                      │
  │  В:                                                  │
  │  ┌─────────────────────────────────┐                │
  │  │ [₽ RUB ▼]         9,045.00    │                │
  │  └─────────────────────────────────┘                │
  │                                                      │
  │  Курс: 1 USD = 90.45 RUB                           │
  │  Комиссия: 1.0% ($1.00)                            │
  │  Вы отдаёте: $100.00                                │
  │  Вы получите: ₽9,045.00                             │
  │                                                      │
  │  ⓘ Курс обновляется каждые 15 минут               │
  │  ⓘ Курс зафиксируется на 30 секунд при нажатии    │
  │                                                      │
  │  [Конвертировать]                                   │
  │                                                      │
  └──────────────────────────────────────────────────────┘

HTMX:
  При изменении суммы или валюты:
    hx-get="/wallet/api/conversion-preview/"
    → обновляет блок с расчётами
    → без перезагрузки страницы
```

### Страница истории транзакций

```
URL: /wallet/transactions/

  ┌──────────────────────────────────────────────────────┐
  │  📋 История транзакций                              │
  │                                                      │
  │  Фильтры:                                          │
  │  Тип: [Все ▼] Валюта: [Все ▼] Период: [7 дней ▼] │
  │  Поиск: [TXN-... или описание        ] [🔍]       │
  │                                                      │
  │  ┌──────────────────────────────────────────────┐   │
  │  │ Дата        Тип      Сумма      Баланс     │   │
  │  ├──────────────────────────────────────────────┤   │
  │  │ 15.03 14:30 📥 Dep.  +$500.00   $10,500    │   │
  │  │ 15.03 15:00 🎯 Bet   -$50.00    $10,450    │   │
  │  │ 15.03 15:45 🏆 Win   +$105.00   $10,555    │   │
  │  │ 14.03 20:00 🔄 Conv  -$100      $10,455    │   │
  │  │ 14.03 20:00 🔄 Conv  +₽9,090    ₽194,090   │   │
  │  │ 14.03 12:00 📤 Withd -₽50,000   ₽144,090   │   │
  │  │ 13.03 09:00 🎁 Bonus +$100      $10,555    │   │
  │  │ 13.03 08:00 🤝 Ref   +$5.50     $10,455    │   │
  │  └──────────────────────────────────────────────┘   │
  │                                                      │
  │  При клике на строку → детали транзакции            │
  │                                                      │
  │  Показано 1-20 из 156   [← 1 2 3 4 5 →]           │
  │                                                      │
  │  [📥 Экспорт CSV]  [📊 Экспорт Excel]              │
  │                                                      │
  └──────────────────────────────────────────────────────┘

HTMX:
  Фильтрация без перезагрузки:
    hx-get="/wallet/transactions/?type=deposit&currency=USD"
    hx-trigger="change"
    hx-target="#transactions-table"

  Пагинация:
    hx-get="/wallet/transactions/?page=2"
    hx-target="#transactions-table"
    hx-swap="innerHTML"
```

### Страница KYC

```
URL: /wallet/kyc/

Если статус 'not_submitted':
  ┌──────────────────────────────────────────────────────┐
  │  🪪 Верификация личности (KYC)                     │
  │                                                      │
  │  Для вывода сумм более $1,000 необходимо            │
  │  подтвердить вашу личность.                         │
  │                                                      │
  │  Что потребуется:                                   │
  │  ✅ Фото документа (паспорт или ID карта)          │
  │  ✅ Селфи с документом в руке                      │
  │  ✅ 5 минут вашего времени                         │
  │                                                      │
  │  [Начать верификацию →]                             │
  │                                                      │
  └──────────────────────────────────────────────────────┘

URL: /wallet/kyc/form/

Форма KYC:
  ┌──────────────────────────────────────────────────────┐
  │  🪪 Шаг 1 из 3: Личные данные                     │
  │  ━━━━━━━━●━━━━━━━━○━━━━━━━━○                       │
  │                                                      │
  │  Тип документа:                                     │
  │  ○ Паспорт  ○ ID карта  ○ Водительское удост.      │
  │                                                      │
  │  Полное имя (как в документе):                      │
  │  ┌────────────────────────────────────┐             │
  │  │ Иван Иванович Иванов              │             │
  │  └────────────────────────────────────┘             │
  │                                                      │
  │  Номер документа:                                   │
  │  ┌────────────────────────────────────┐             │
  │  │ 45 06 123456                       │             │
  │  └────────────────────────────────────┘             │
  │                                                      │
  │  Дата рождения:                                     │
  │  ┌────────────────────────────────────┐             │
  │  │ 15.03.1990                         │             │
  │  └────────────────────────────────────┘             │
  │                                                      │
  │  Страна выдачи:                                     │
  │  ┌────────────────────────────────────┐             │
  │  │ Россия                        ▼   │             │
  │  └────────────────────────────────────┘             │
  │                                                      │
  │  [Далее →]                                          │
  │                                                      │
  ├──────────────────────────────────────────────────────┤
  │  🪪 Шаг 2 из 3: Фото документа                    │
  │  ━━━━━━━━━━━━━━━━●━━━━━━━━○                        │
  │                                                      │
  │  Лицевая сторона:                                   │
  │  ┌─────────────────────────┐                        │
  │  │                         │                        │
  │  │    📷 Загрузить фото    │                        │
  │  │    или перетащите сюда  │                        │
  │  │                         │                        │
  │  └─────────────────────────┘                        │
  │  JPG, PNG • Макс. 10 MB • Чёткое фото              │
  │                                                      │
  │  Обратная сторона (если есть):                      │
  │  ┌─────────────────────────┐                        │
  │  │    📷 Загрузить фото    │                        │
  │  └─────────────────────────┘                        │
  │                                                      │
  │  [← Назад]  [Далее →]                              │
  │                                                      │
  ├──────────────────────────────────────────────────────┤
  │  🪪 Шаг 3 из 3: Селфи                             │
  │  ━━━━━━━━━━━━━━━━━━━━━━━━●                         │
  │                                                      │
  │  Сделайте селфи с документом в руке:               │
  │                                                      │
  │  Требования:                                        │
  │  • Держите документ рядом с лицом                   │
  │  • Лицо и документ должны быть чёткими             │
  │  • Все данные документа должны читаться             │
  │                                                      │
  │  ┌─────────────────────────┐                        │
  │  │    📷 Загрузить селфи   │                        │
  │  └─────────────────────────┘                        │
  │                                                      │
  │  [← Назад]  [Отправить на проверку]                │
  │                                                      │
  └──────────────────────────────────────────────────────┘

Если статус 'pending':
  ┌──────────────────────────────────────┐
  │  🕐 Заявка на проверке              │
  │                                      │
  │  Ваши документы проверяются.        │
  │  Обычно это занимает до 24 часов.   │
  │                                      │
  │  Статус: 🔄 На проверке             │
  │  Подана: 15 марта 2025, 14:30       │
  │                                      │
  └──────────────────────────────────────┘

Если статус 'approved':
  ┌──────────────────────────────────────┐
  │  ✅ Верификация пройдена            │
  │                                      │
  │  Ваша личность подтверждена.        │
  │  Дата: 16 марта 2025               │
  │                                      │
  └──────────────────────────────────────┘

Если статус 'rejected':
  ┌──────────────────────────────────────┐
  │  ❌ Верификация отклонена           │
  │                                      │
  │  Причина: Нечёткое фото документа  │
  │                                      │
  │  Попыток осталось: 2 из 3          │
  │  [Подать повторно]                  │
  │                                      │
  └──────────────────────────────────────┘
```

### Критерий готовности шага 2.3

```
□ Главная страница кошелька: все балансы, операции
□ Страница пополнения: выбор валюты, суммы, метода
□ Демо пополнение работает (без реальных платежей)
□ Страница вывода: выбор, сумма, реквизиты
□ Вывод создаёт WithdrawalRequest с расчётом риска
□ Автовывод для маленьких сумм
□ Ручная проверка для больших сумм
□ Отмена вывода пользователем
□ Страница конвертации: предпросмотр + выполнение
□ HTMX обновление расчётов без перезагрузки
□ История транзакций с фильтрами и пагинацией
□ Экспорт CSV/Excel
□ KYC: форма из 3 шагов
□ KYC: загрузка документов
□ KYC: статусы отображаются
□ 2FA при выводе средств
□ Смена основной валюты
□ Баланс в navbar обновляется
□ Все страницы: тёмная тема, мобильная адаптация
□ HTMX: интерактивность без перезагрузки
```

---

## ШАГ 2.4 — NAVBAR БАЛАНС + TEMPLATE TAGS + API

### Задача

```
Баланс в navbar должен работать корректно.
Создай template tags для форматирования валют.
Создай API endpoints для HTMX.
```

### Template tags (templatetags/wallet_tags.py)

```
Назначение:
  Удобные теги для использования в шаблонах.

Теги:

  {% load wallet_tags %}

  {% user_balance request.user %}
    → Возвращает форматированный баланс в основной валюте
    → "$1,234.56" или "₽100,000" или "₿0.00500000"

  {% user_balance_raw request.user %}
    → Возвращает число (для JS)
    → 1234.56

  {% format_currency amount currency_code %}
    → Форматирует число в валюту
    → {% format_currency 1234.56 "USD" %} → "$1,234.56"
    → {% format_currency 0.005 "BTC" %} → "₿0.00500000"
    → {% format_currency 100000 "KZT" %} → "₸100,000"

  {% format_transaction_amount transaction %}
    → "+$105.00" (зелёный) или "-$50.00" (красный)
    → С иконкой типа

  {% currency_icon currency_code %}
    → Возвращает символ/иконку валюты
    → "USD" → "$", "BTC" → "₿"

  {% conversion_rate from_code to_code %}
    → "1 USD = 90.45 RUB"
```

### API endpoints для HTMX

```
/wallet/api/balances/
  GET: Возвращает HTML фрагмент со всеми балансами.
  Используется: HTMX в navbar и на странице кошелька.
  Обновляется каждые 30 секунд.

/wallet/api/navbar-balance/
  GET: Возвращает HTML фрагмент баланса для navbar.
  Только основная валюта: "$1,234.56"
  HTMX: hx-get hx-trigger="every 30s"

/wallet/api/primary-currency/
  POST: Сменить основную валюту.
  Параметр: currency_code
  Возвращает: обновлённый фрагмент баланса.
  HTMX: hx-post hx-swap

/wallet/api/conversion-preview/
  GET: Предпросмотр конвертации.
  Параметры: from, to, amount
  Возвращает: HTML фрагмент с расчётами.
  HTMX: hx-get hx-trigger="keyup changed delay:500ms"

/wallet/api/withdrawal-fee/
  GET: Расчёт комиссии за вывод.
  Параметры: currency, amount
  Возвращает: HTML фрагмент с комиссией и суммой к получению.
```

### Обновление navbar

```
В components/navbar.html:

Блок баланса:
  <div id="navbar-balance"
       hx-get="/wallet/api/navbar-balance/"
       hx-trigger="every 30s"
       hx-swap="innerHTML">
    {% user_balance request.user %}
  </div>

При изменении баланса (ставка, выигрыш):
  Сервер отправляет HX-Trigger header → обновляет баланс.
  Или: WebSocket пуш (в будущем, Этап 10).
```

### Критерий готовности шага 2.4

```
□ Template tags: user_balance, format_currency, и другие
□ API /wallet/api/navbar-balance/ работает
□ API /wallet/api/balances/ работает
□ API /wallet/api/conversion-preview/ работает
□ API /wallet/api/withdrawal-fee/ работает
□ API /wallet/api/primary-currency/ работает
□ Navbar баланс обновляется каждые 30 секунд
□ Суммы форматируются правильно для каждой валюты
□ Отрицательные суммы красные, положительные зелёные
```

---

## 📊 ОБЩИЙ ЧЕКЛИСТ ЭТАПА 2

```
МОДЕЛИ:
  □ Currency (11 валют с настройками)
  □ Wallet (мультивалютный кошелёк)
  □ WalletBalance (баланс по валютам)
  □ Transaction (журнал операций, append-only)
  □ WithdrawalRequest (заявки на вывод с рисками)
  □ ConversionOrder (история конвертаций)
  □ KYCVerification (верификация личности)
  □ WalletSettings (глобальные настройки, singleton)

СЕРВИСЫ:
  □ WalletService (создание, балансы)
  □ TransactionService (deposit, withdraw, freeze, settle)
  □ ConversionService (preview, execute)
  □ WithdrawalService (create, risk, approve, reject)
  □ RateService (обновление курсов)

СТРАНИЦЫ:
  □ /wallet/ — обзор кошелька
  □ /wallet/deposit/ — пополнение (демо)
  □ /wallet/withdraw/ — вывод
  □ /wallet/convert/ — конвертация
  □ /wallet/transactions/ — история
  □ /wallet/kyc/ — верификация

БЕЗОПАСНОСТЬ:
  □ Атомарные операции (select_for_update + atomic)
  □ Баланс никогда не отрицательный
  □ Система рисков для выводов
  □ 2FA при выводе
  □ KYC при больших суммах
  □ Маскирование номеров карт
  □ Шифрование номера документа

CELERY ЗАДАЧИ:
  □ Обновление курсов (каждые 15 мин)
  □ Обработка выводов
  □ Проверка expired заявок
  □ Уведомления админам
  □ Ежедневная сверка балансов

HTMX / ИНТЕРАКТИВНОСТЬ:
  □ Баланс в navbar обновляется
  □ Конвертация пересчитывается
  □ Фильтры транзакций
  □ Пагинация транзакций

АДМИНКА:
  □ Управление валютами
  □ Просмотр кошельков
  □ Просмотр транзакций (readonly)
  □ Обработка заявок на вывод
  □ Обработка KYC
  □ Настройки кошелька (лимиты)
```

---

```
╔══════════════════════════════════════════════════════╗
║                                                      ║
║   ЭТАП 2 ЗАВЕРШЁН                                   ║
║                                                      ║
║   Следующий: ЭТАП 3                                 ║
║   Платёжная система (NOWpayments + RUkassa)         ║
║                                                      ║
║   Продолжить?                                       ║
║                                                      ║
╚══════════════════════════════════════════════════════╝
```