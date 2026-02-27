# 📋 ТЗ ПРОЕКТА DOD — ЭТАП 8

# ПАРТНЁРСКАЯ ПРОГРАММА (РЕФЕРАЛЬНАЯ СИСТЕМА)

```
╔══════════════════════════════════════════════════════╗
║                                                      ║
║   ПРОЕКТ:    DOD                                    ║
║   ЭТАП:      8 из 12                                ║
║   НАЗВАНИЕ:  Партнёрская программа                  ║
║   ЗАВИСИТ:   Этапы 1-7 (полностью завершены)        ║
║   ЦЕЛЬ:      Пользователь может приглашать других,  ║
║              получать комиссию от GGR рефералов,    ║
║              видеть детальную статистику,            ║
║              выводить партнёрский доход,             ║
║              админ управляет программой полностью   ║
║                                                      ║
╚══════════════════════════════════════════════════════╝
```

---

## 📌 КОНТЕКСТ ДЛЯ ИИ-АГЕНТА

```
Этапы 1-7 выполнены. У тебя есть:
  - Полная авторизация + 2FA + KYC
  - Мультивалютный кошелёк + платежи
  - Ставки на спорт (полный функционал)
  - Казино (Crash, Mines, Dice, Plinko, Roulette, Slots)
  - Prediction Market (AMM, торги, резолюция)
  - Уведомления (сайт, email, Telegram)
  - Модель User уже имеет поля:
    referral_code (DOD-XXXXXX)
    referred_by (FK → User)

Партнёрская программа — ключевой инструмент роста.
Партнёры приводят новых пользователей и получают
процент от GGR (Gross Gaming Revenue) рефералов.

GGR = сумма ставок — сумма выигрышей
(то что платформа заработала на игроке)

Партнёрская программа должна быть:
  - Прозрачной (партнёр видит всю статистику)
  - Гибкой (разные % для разных уровней)
  - Защищённой от фрода (мульти-аккаунты, фейки)
  - Многоуровневой (опционально: 2 уровня)

Этот этап включает 6 шагов.
Каждый шаг — отдельная задача.
Выполняй строго по порядку.
```

---

## ШАГ 8.1 — ПРИЛОЖЕНИЕ И МОДЕЛИ

### Задача

```
Создай приложение referral с полной структурой моделей:
партнёрские уровни, комиссии, выплаты, статистика,
промо-материалы, антифрод.
```

### Структура приложения

```
apps/referral/
├── __init__.py
├── models.py
├── managers.py
├── admin.py
├── views.py
├── urls.py
├── forms.py
├── signals.py
├── tasks.py                  # Celery задачи
├── validators.py
├── services/
│   ├── __init__.py
│   ├── referral_service.py   # Логика реферальной системы
│   ├── commission_service.py # Расчёт и начисление комиссий
│   ├── payout_service.py     # Вывод партнёрских средств
│   ├── analytics_service.py  # Статистика и отчёты
│   └── antifraud_service.py  # Защита от фрода
├── templatetags/
│   ├── __init__.py
│   └── referral_tags.py
├── tests/
│   ├── __init__.py
│   ├── test_models.py
│   ├── test_commission.py
│   ├── test_antifraud.py
│   └── test_views.py
├── templates/
│   └── referral/
│       └── (шаблоны — шаг 8.5)
└── migrations/
    └── __init__.py
```

### Модель PartnerTier (Уровни партнёров)

```
class PartnerTier(models.Model):

    Назначение:
      Уровни партнёрской программы.
      Каждый уровень имеет свои проценты и условия.
      Настраивается из админки.

    Поля:
    ─────
    id:
      тип: AutoField, primary key

    name:
      тип: CharField, max 50
      Название уровня
      Пример: "Стартовый", "Продвинутый", "VIP"

    name_en:
      тип: CharField, max 50, blank=True

    slug:
      тип: SlugField, уникальный
      Пример: "starter", "advanced", "vip"

    icon:
      тип: CharField, max 10
      Пример: "🥉", "🥈", "🥇", "💎"

    color:
      тип: CharField, max 7
      HEX цвет
      Пример: "#94a3b8", "#f59e0b", "#8b5cf6", "#ec4899"

    # Условия получения уровня
    min_referrals:
      тип: IntegerField, default=0
      Минимум активных рефералов для получения уровня
      Стартовый: 0 (по умолчанию)
      Продвинутый: 10
      Профи: 50
      VIP: 200

    min_monthly_ggr:
      тип: DecimalField(18, 2), default=0
      Минимальный месячный GGR рефералов (USD)
      Стартовый: 0
      Продвинутый: $500
      Профи: $2,000
      VIP: $10,000

    # Комиссионные ставки (% от GGR)
    commission_rate_month_1:
      тип: DecimalField(5, 2)
      Процент комиссии в первый месяц жизни реферала
      Стартовый: 30%
      Продвинутый: 40%
      Профи: 45%
      VIP: 50%

    commission_rate_month_2_3:
      тип: DecimalField(5, 2)
      Процент комиссии во 2-3 месяц
      Стартовый: 20%
      Продвинутый: 30%
      Профи: 35%
      VIP: 40%

    commission_rate_month_4_plus:
      тип: DecimalField(5, 2)
      Процент комиссии с 4-го месяца и далее
      Стартовый: 10%
      Продвинутый: 20%
      Профи: 25%
      VIP: 30%

    # Комиссия 2-го уровня (от рефералов рефералов)
    level2_commission_rate:
      тип: DecimalField(5, 2), default=0
      Процент от GGR рефералов 2-го уровня
      Стартовый: 0% (нет 2-го уровня)
      Продвинутый: 3%
      Профи: 5%
      VIP: 7%

    # Минимальный вывод
    min_payout_amount:
      тип: DecimalField(18, 2), default=50
      Минимальная сумма для вывода партнёрских
      Стартовый: $50
      Продвинутый: $30
      Профи: $20
      VIP: $10

    # Бонусы
    signup_bonus:
      тип: DecimalField(18, 2), default=0
      Бонус за каждую регистрацию (фиксированный)
      Стартовый: $0
      Продвинутый: $0
      Профи: $1
      VIP: $2

    first_deposit_bonus_rate:
      тип: DecimalField(5, 2), default=0
      Процент от первого депозита реферала
      Стартовый: 0%
      Продвинутый: 5%
      Профи: 10%
      VIP: 15%

    # Привилегии
    has_custom_links:
      тип: BooleanField, default=False
      Может создавать кастомные промо-ссылки
      Стартовый: нет
      Продвинутый: да

    has_promo_materials:
      тип: BooleanField, default=True

    has_api_access:
      тип: BooleanField, default=False
      Доступ к партнёрскому API
      VIP: да

    has_dedicated_manager:
      тип: BooleanField, default=False
      Персональный менеджер
      VIP: да

    # Порядок
    sort_order:
      тип: IntegerField, default=0
      Чем больше → выше уровень

    is_active:
      тип: BooleanField, default=True

    created_at:
      тип: DateTimeField, auto_now_add=True

    Meta:
      verbose_name = 'Уровень партнёра'
      verbose_name_plural = 'Уровни партнёров'
      ordering = ['sort_order']

    Предзаполнение (fixtures):
      🥉 Стартовый    (starter)    — sort_order=1
      🥈 Продвинутый  (advanced)   — sort_order=2
      🥇 Профи        (pro)        — sort_order=3
      💎 VIP          (vip)        — sort_order=4
```

### Модель PartnerProfile (Профиль партнёра)

```
class PartnerProfile(models.Model):

    Назначение:
      Расширение User для партнёрской программы.
      Создаётся автоматически для каждого пользователя.
      Содержит партнёрский баланс и статистику.

    Поля:
    ─────
    id:
      тип: UUID, primary key

    user:
      тип: OneToOneField → User
      on_delete: CASCADE
      related_name: 'partner_profile'

    tier:
      тип: ForeignKey → PartnerTier
      on_delete: PROTECT
      default: стартовый уровень

    # Партнёрский баланс (отдельно от игрового)
    balance:
      тип: DecimalField(18, 2), default=0
      Доступные для вывода средства (USD)

    total_earned:
      тип: DecimalField(18, 2), default=0
      Всего заработано за всё время

    total_withdrawn:
      тип: DecimalField(18, 2), default=0
      Всего выведено

    # Статистика (кэшированная, обновляется Celery)
    total_referrals:
      тип: IntegerField, default=0
      Всего привёл рефералов (зарегистрированных)

    active_referrals:
      тип: IntegerField, default=0
      Активные рефералы (были активны за 30 дней)

    referrals_with_deposit:
      тип: IntegerField, default=0
      Рефералы которые сделали хотя бы 1 депозит

    total_referral_deposits:
      тип: DecimalField(18, 2), default=0
      Сумма всех депозитов рефералов

    total_referral_ggr:
      тип: DecimalField(18, 2), default=0
      Суммарный GGR всех рефералов

    # 2-й уровень
    total_level2_referrals:
      тип: IntegerField, default=0
    total_level2_earned:
      тип: DecimalField(18, 2), default=0

    # Текущий месяц
    monthly_ggr:
      тип: DecimalField(18, 2), default=0
      GGR рефералов за текущий месяц
      (для определения уровня)

    monthly_earned:
      тип: DecimalField(18, 2), default=0

    monthly_referrals:
      тип: IntegerField, default=0
      Новых рефералов за текущий месяц

    # Лучшие показатели
    best_month_earnings:
      тип: DecimalField(18, 2), default=0
      Лучший месяц по заработку

    best_month_date:
      тип: DateField, nullable

    # Статус
    is_partner_active:
      тип: BooleanField, default=True
      Может быть деактивирован за фрод

    is_suspended:
      тип: BooleanField, default=False
      Приостановлен (на проверке)

    suspension_reason:
      тип: TextField, blank=True

    # Пользовательские ссылки
    custom_slug:
      тип: SlugField, nullable, unique
      Кастомная ссылка: dod.com/r/my-channel
      Доступно с уровня Продвинутый

    # Промо
    bio:
      тип: TextField, max 500, blank=True
      О себе (для страницы партнёра)

    website_url:
      тип: URLField, nullable
      Сайт партнёра

    telegram_channel:
      тип: CharField, max 100, blank=True
      Telegram канал

    # Даты
    partner_since:
      тип: DateTimeField, auto_now_add=True

    tier_changed_at:
      тип: DateTimeField, nullable
      Когда последний раз менялся уровень

    last_payout_at:
      тип: DateTimeField, nullable

    created_at:
      тип: DateTimeField, auto_now_add=True

    updated_at:
      тип: DateTimeField, auto_now=True

    Meta:
      verbose_name = 'Профиль партнёра'
      verbose_name_plural = 'Профили партнёров'

    Методы:
      get_commission_rate(referral_age_months):
        """Получить текущий % комиссии по возрасту реферала."""
        if referral_age_months <= 1:
          return self.tier.commission_rate_month_1
        elif referral_age_months <= 3:
          return self.tier.commission_rate_month_2_3
        else:
          return self.tier.commission_rate_month_4_plus

      get_referral_link():
        """Полная реферальная ссылка."""
        code = self.custom_slug or self.user.referral_code
        return f'{settings.SITE_URL}/r/{code}'

      available_for_payout():
        """Доступно для вывода."""
        return self.balance >= self.tier.min_payout_amount

    Создание:
      При создании User (сигнал post_save) →
      автоматически создавать PartnerProfile
      с tier = стартовый.
```

### Модель Referral (Связь реферер ↔ реферал)

```
class Referral(models.Model):

    Назначение:
      Связь между партнёром и привлечённым пользователем.
      Одна запись = один привлечённый пользователь.
      Хранит детальную статистику по каждому рефералу.

    Поля:
    ─────
    id:
      тип: UUID, primary key

    partner:
      тип: ForeignKey → User
      on_delete: CASCADE
      related_name: 'referred_users'
      Партнёр который привёл

    referral:
      тип: OneToOneField → User
      on_delete: CASCADE
      related_name: 'referral_record'
      Привлечённый пользователь

    # Как пришёл
    referral_code_used:
      тип: CharField, max 20
      Какой код/ссылка использована

    source:
      тип: CharField, max 50, blank=True
      UTM-метка или субаккаунт
      Пример: "youtube", "telegram_post_123"

    promo_link:
      тип: ForeignKey → PromoLink, nullable
      Через какую промо-ссылку пришёл

    # Регистрация
    registration_ip:
      тип: GenericIPAddressField, nullable

    registration_country:
      тип: CharField, max 100, blank=True

    registration_device:
      тип: CharField, max 50, blank=True
      desktop / mobile / tablet

    registered_at:
      тип: DateTimeField, auto_now_add=True

    # Статус реферала
    status:
      тип: CharField
      choices:
        ('registered', 'Зарегистрирован')
        ('deposited', 'Сделал депозит')
        ('active', 'Активный')
        ('churned', 'Ушёл')
        ('blocked', 'Заблокирован')
        ('fraud', 'Фрод')
      default: 'registered'

    # Финансы реферала
    total_deposits:
      тип: DecimalField(18, 2), default=0
      Всего депозитов реферала

    first_deposit_amount:
      тип: DecimalField(18, 2), default=0
      Сумма первого депозита

    first_deposit_at:
      тип: DateTimeField, nullable

    total_bets:
      тип: DecimalField(18, 2), default=0
      Суммарный оборот ставок

    total_ggr:
      тип: DecimalField(18, 2), default=0
      GGR (gross gaming revenue) этого реферала
      = total_bets - total_winnings

    total_winnings:
      тип: DecimalField(18, 2), default=0

    # Комиссия с этого реферала
    total_commission_earned:
      тип: DecimalField(18, 2), default=0
      Сколько партнёр заработал с этого реферала

    # Активность
    last_active_at:
      тип: DateTimeField, nullable

    is_active:
      тип: BooleanField, default=True
      Был активен за последние 30 дней

    # Уровень (для многоуровневой)
    level:
      тип: IntegerField, default=1
      1 = прямой реферал
      2 = реферал реферала

    # Антифрод
    is_suspicious:
      тип: BooleanField, default=False
      Помечен системой антифрода

    fraud_flags:
      тип: JSONField, default=list
      Список флагов:
      ["same_ip", "same_device", "no_deposit", "instant_withdraw"]

    is_qualified:
      тип: BooleanField, default=False
      Квалифицированный реферал (прошёл минимальные условия)
      Условия: сделал депозит >= $10 И сделал >= 3 ставки

    qualified_at:
      тип: DateTimeField, nullable

    created_at:
      тип: DateTimeField, auto_now_add=True

    updated_at:
      тип: DateTimeField, auto_now=True

    Meta:
      verbose_name = 'Реферал'
      verbose_name_plural = 'Рефералы'
      ordering = ['-created_at']
      indexes:
        - partner + status
        - partner + created_at
        - partner + is_qualified
        - referral (unique, уже OneToOne)
        - status + created_at
        - level
```

### Модель Commission (Начисление комиссии)

```
class Commission(models.Model):

    Назначение:
      Каждое начисление комиссии партнёру.
      Детальная запись: от какого реферала,
      за какой период, какой процент, сумма.

    Поля:
    ─────
    id:
      тип: UUID, primary key

    partner:
      тип: ForeignKey → User
      on_delete: CASCADE
      related_name: 'commissions'

    referral:
      тип: ForeignKey → Referral
      on_delete: CASCADE
      related_name: 'commissions'

    # Тип комиссии
    commission_type:
      тип: CharField
      choices:
        ('ggr', 'Комиссия от GGR')
        ('signup_bonus', 'Бонус за регистрацию')
        ('first_deposit', 'Бонус за первый депозит')
        ('level2_ggr', 'Комиссия 2-го уровня')
        ('manual', 'Ручное начисление (админ)')
        ('bonus', 'Бонус от платформы')

    # Период
    period_start:
      тип: DateField
      Начало периода за который начислена

    period_end:
      тип: DateField
      Конец периода

    # Расчёт
    referral_ggr:
      тип: DecimalField(18, 2), default=0
      GGR реферала за этот период

    commission_rate:
      тип: DecimalField(5, 2)
      Процент комиссии который применялся

    # Суммы
    gross_amount:
      тип: DecimalField(18, 2)
      Начисленная сумма (до корректировок)

    adjustments:
      тип: DecimalField(18, 2), default=0
      Корректировки (отрицательный GGR — carryover)

    net_amount:
      тип: DecimalField(18, 2)
      Итоговая сумма = gross_amount + adjustments
      Может быть 0 если GGR отрицательный

    # Статус
    status:
      тип: CharField
      choices:
        ('pending', 'Ожидает')
        ('approved', 'Одобрена')
        ('paid', 'Выплачена')
        ('cancelled', 'Отменена')
        ('held', 'Задержана (проверка)')
      default: 'pending'

    # Выплата
    payout:
      тип: ForeignKey → PartnerPayout, nullable
      В какую выплату включена

    # Мета
    notes:
      тип: TextField, blank=True
      Заметки (для ручных начислений)

    created_by:
      тип: ForeignKey → User, nullable
      Кто создал (для ручных)

    created_at:
      тип: DateTimeField, auto_now_add=True

    Meta:
      verbose_name = 'Комиссия'
      verbose_name_plural = 'Комиссии'
      ordering = ['-created_at']
      indexes:
        - partner + created_at
        - partner + status
        - referral + period_start
        - commission_type
        - status + created_at

    Важно: Отрицательный GGR (Negative Carryover)
      Если реферал ВЫИГРАЛ больше чем проиграл,
      GGR отрицательный. Комиссия = 0 (не отрицательная).
      НО: отрицательный GGR переносится на следующий период.
      Пока накопленный GGR не станет положительным,
      комиссия не начисляется.

    Пример:
      Январь: GGR = -$200 → комиссия = $0, carryover = -$200
      Февраль: GGR = +$500 → эффективный GGR = $500 - $200 = $300
      Комиссия = $300 * 30% = $90
```

### Модель PartnerPayout (Выплата партнёру)

```
class PartnerPayout(models.Model):

    Назначение:
      Запрос на вывод партнёрских средств.
      Отдельно от обычных выводов из кошелька.

    Поля:
    ─────
    id:
      тип: UUID, primary key

    partner:
      тип: ForeignKey → User
      on_delete: CASCADE
      related_name: 'partner_payouts'

    # Суммы
    amount:
      тип: DecimalField(18, 2)
      Сумма вывода (USD)

    fee:
      тип: DecimalField(18, 2), default=0
      Комиссия за вывод (если есть)

    net_amount:
      тип: DecimalField(18, 2)
      К выплате = amount - fee

    # Куда выводить
    payout_method:
      тип: CharField
      choices:
        ('game_balance', 'На игровой баланс')
        ('wallet', 'На кошелёк (далее вывод)')
        ('usdt', 'USDT напрямую')
        ('bank_card', 'На банковскую карту')
      default: 'game_balance'

    payout_details:
      тип: JSONField, nullable
      Реквизиты для вывода
      Для USDT: {"address": "...", "network": "TRC20"}
      Для карты: {"card_number": "****1234"}

    # Статус
    status:
      тип: CharField
      choices:
        ('pending', 'Ожидает')
        ('processing', 'Обрабатывается')
        ('completed', 'Выполнена')
        ('rejected', 'Отклонена')
        ('cancelled', 'Отменена')
      default: 'pending'

    rejection_reason:
      тип: TextField, blank=True

    # Обработка
    processed_by:
      тип: ForeignKey → User, nullable
      Админ который обработал

    processed_at:
      тип: DateTimeField, nullable

    # Связанные комиссии
    # (ManyToMany через Commission.payout FK)

    # Мета
    ip_address:
      тип: GenericIPAddressField, nullable

    created_at:
      тип: DateTimeField, auto_now_add=True

    Meta:
      verbose_name = 'Выплата партнёру'
      verbose_name_plural = 'Выплаты партнёрам'
      ordering = ['-created_at']
      indexes:
        - partner + status
        - status + created_at
```

### Модель PromoLink (Промо-ссылки)

```
class PromoLink(models.Model):

    Назначение:
      Кастомные промо-ссылки для отслеживания
      разных источников трафика.
      Партнёр может создать ссылку для YouTube,
      другую для Telegram, третью для блога.

    Поля:
    ─────
    id:
      тип: UUID, primary key

    partner:
      тип: ForeignKey → User
      on_delete: CASCADE
      related_name: 'promo_links'

    name:
      тип: CharField, max 100
      Название ссылки (для себя)
      Пример: "YouTube канал", "Telegram пост #123"

    slug:
      тип: SlugField, max 50, уникальный
      URL часть: dod.com/r/{slug}
      Генерируется автоматически или задаётся вручную

    # Статистика
    clicks:
      тип: IntegerField, default=0
      Количество кликов

    registrations:
      тип: IntegerField, default=0
      Количество регистраций через эту ссылку

    deposits:
      тип: IntegerField, default=0
      Количество рефералов сделавших депозит

    total_deposit_amount:
      тип: DecimalField(18, 2), default=0
      Сумма депозитов через эту ссылку

    total_ggr:
      тип: DecimalField(18, 2), default=0
      GGR рефералов пришедших по этой ссылке

    total_earned:
      тип: DecimalField(18, 2), default=0
      Заработано комиссий через эту ссылку

    # Конверсия
    conversion_rate:
      тип: DecimalField(5, 2), default=0
      Клик → Регистрация (%)

    deposit_rate:
      тип: DecimalField(5, 2), default=0
      Регистрация → Депозит (%)

    # Настройки
    is_active:
      тип: BooleanField, default=True

    # UTM
    utm_source:
      тип: CharField, max 100, blank=True
    utm_medium:
      тип: CharField, max 100, blank=True
    utm_campaign:
      тип: CharField, max 100, blank=True

    created_at:
      тип: DateTimeField, auto_now_add=True

    updated_at:
      тип: DateTimeField, auto_now=True

    Meta:
      verbose_name = 'Промо-ссылка'
      ordering = ['-created_at']
      indexes:
        - partner + is_active
        - slug (unique)

    Методы:
      get_full_url():
        return f'{settings.SITE_URL}/r/{self.slug}'

      get_qr_code():
        Генерирует QR-код для ссылки.
        Кешируется.

    Ограничения:
      Стартовый партнёр: 1 ссылка (стандартная)
      Продвинутый: до 10 ссылок
      Профи: до 50 ссылок
      VIP: без ограничений
```

### Модель PromoLinkClick (Клики)

```
class PromoLinkClick(models.Model):

    Назначение:
      Запись каждого клика по промо-ссылке.
      Для аналитики и антифрода.

    Поля:
    ─────
    id:
      тип: BigAutoField (не UUID, для скорости)

    promo_link:
      тип: ForeignKey → PromoLink
      on_delete: CASCADE

    ip_address:
      тип: GenericIPAddressField

    country:
      тип: CharField, max 100, blank=True

    user_agent:
      тип: TextField, blank=True

    device_type:
      тип: CharField, max 20
      desktop / mobile / tablet

    referer:
      тип: URLField, blank=True
      Откуда пришёл (HTTP Referer)

    is_unique:
      тип: BooleanField, default=True
      False если этот IP уже кликал

    resulted_in_registration:
      тип: BooleanField, default=False
      Привёл ли клик к регистрации

    user_registered:
      тип: ForeignKey → User, nullable
      Зарегистрированный пользователь (если был)

    created_at:
      тип: DateTimeField, auto_now_add=True

    Meta:
      ordering = ['-created_at']
      indexes:
        - promo_link + created_at
        - ip_address
```

### Модель NegativeCarryover (Перенос отрицательного GGR)

```
class NegativeCarryover(models.Model):

    Назначение:
      Хранит накопленный отрицательный GGR
      для каждой пары партнёр-реферал.
      Когда GGR становится положительным,
      сначала покрывается carryover.

    Поля:
    ─────
    partner:
      тип: ForeignKey → User
      on_delete: CASCADE

    referral:
      тип: ForeignKey → Referral
      on_delete: CASCADE

    amount:
      тип: DecimalField(18, 2), default=0
      Текущий накопленный отрицательный GGR
      Всегда <= 0

    Meta:
      unique_together = ['partner', 'referral']
```

### Модель ReferralSettings (Глобальные настройки)

```
class ReferralSettings(models.Model):

    Назначение:
      Глобальные настройки реферальной программы.
      Синглтон. Редактируется из админки.

    Поля:
    ─────
    # Квалификация реферала
    min_deposit_to_qualify:
      тип: DecimalField(18, 2), default=10
      Минимальный депозит для квалификации ($10)

    min_bets_to_qualify:
      тип: IntegerField, default=3
      Минимум ставок для квалификации

    min_wagered_to_qualify:
      тип: DecimalField(18, 2), default=20
      Минимальный оборот для квалификации ($20)

    # Периоды расчёта
    commission_period:
      тип: CharField
      choices: [('daily', 'Ежедневно'),
                ('weekly', 'Еженедельно'),
                ('monthly', 'Ежемесячно')]
      default: 'daily'

    # Ограничения
    max_referrals_per_ip:
      тип: IntegerField, default=3
      Максимум рефералов с одного IP

    max_referrals_per_day:
      тип: IntegerField, default=50
      Максимум регистраций по одной ссылке в день

    # Антифрод
    min_time_between_registrations:
      тип: IntegerField, default=60
      Секунд между регистрациями с одного IP

    suspicious_patterns_enabled:
      тип: BooleanField, default=True

    auto_block_on_fraud:
      тип: BooleanField, default=True

    # 2-й уровень
    level2_enabled:
      тип: BooleanField, default=True
      Включен ли 2-й уровень

    # Метод вывода
    payout_to_game_balance:
      тип: BooleanField, default=True
    payout_to_wallet:
      тип: BooleanField, default=True
    payout_direct_crypto:
      тип: BooleanField, default=False

    Meta:
      verbose_name = 'Настройки реферальной программы'

    Реализация синглтона:
      как KYCSettings из этапа 2.
```

### Критерий готовности шага 8.1

```
□ Приложение referral создано
□ Модель PartnerTier: создана + fixtures (4 уровня)
□ Модель PartnerProfile: все поля
□ Модель Referral: все поля + статусы
□ Модель Commission: все поля + типы
□ Модель PartnerPayout: все поля
□ Модель PromoLink: все поля
□ Модель PromoLinkClick
□ Модель NegativeCarryover
□ Модель ReferralSettings (синглтон)
□ Все миграции применены
□ Django Admin: все модели зарегистрированы
□ PartnerProfile создаётся автоматически (сигнал)
□ Fixtures с уровнями загружены
□ Индексы для быстрых запросов
```

---

## ШАГ 8.2 — РЕФЕРАЛЬНАЯ МЕХАНИКА

### Задача

```
Реализуй логику регистрации по реферальной ссылке.
Отслеживание кликов. Привязка реферала к партнёру.
Квалификация рефералов. Антифрод при регистрации.
```

### ReferralService

```
ReferralService:

  process_referral_click(request, code_or_slug):
    """
    Обработка клика по реферальной ссылке.
    URL: /r/{code_or_slug}/
    
    1. Определить партнёра
    2. Записать клик
    3. Сохранить в сессии/cookie
    4. Редирект на регистрацию
    """

    # Найти партнёра
    partner = None
    promo_link = None

    # Сначала ищем по PromoLink slug
    try:
      promo_link = PromoLink.objects.get(
        slug=code_or_slug, is_active=True
      )
      partner = promo_link.partner
    except PromoLink.DoesNotExist:
      # Потом по referral_code пользователя
      try:
        partner = User.objects.get(
          referral_code=code_or_slug, is_active=True
        )
      except User.DoesNotExist:
        # Невалидная ссылка → просто редирект на регистрацию
        return redirect('accounts:register')

    # Проверка: партнёр не заблокирован
    partner_profile = partner.partner_profile
    if not partner_profile.is_partner_active or partner_profile.is_suspended:
      return redirect('accounts:register')

    # Записать клик
    ip = get_client_ip(request)
    ua = request.META.get('HTTP_USER_AGENT', '')
    referer = request.META.get('HTTP_REFERER', '')

    # Проверить уникальность клика (по IP за 24ч)
    is_unique = not PromoLinkClick.objects.filter(
      promo_link=promo_link,
      ip_address=ip,
      created_at__gte=now() - timedelta(hours=24),
    ).exists() if promo_link else True

    if promo_link:
      PromoLinkClick.objects.create(
        promo_link=promo_link,
        ip_address=ip,
        country=get_country_from_ip(ip),
        user_agent=ua,
        device_type=get_device_type(ua),
        referer=referer,
        is_unique=is_unique,
      )

      # Обновить счётчик кликов
      if is_unique:
        PromoLink.objects.filter(id=promo_link.id).update(
          clicks=F('clicks') + 1
        )

    # Сохранить в сессии и cookie
    request.session['referral_code'] = partner.referral_code
    request.session['promo_link_id'] = str(promo_link.id) if promo_link else None

    # Cookie на 30 дней (если сессия истечёт)
    response = redirect('accounts:register')
    response.set_cookie(
      'ref',
      partner.referral_code,
      max_age=30 * 24 * 60 * 60,  # 30 дней
      httponly=True,
      samesite='Lax',
    )

    return response


  process_referral_registration(new_user, request):
    """
    Вызывается ПОСЛЕ успешной регистрации нового пользователя.
    Привязывает реферала к партнёру.
    """

    # Получить реферальный код
    referral_code = (
      request.session.get('referral_code')
      or request.COOKIES.get('ref')
      or request.POST.get('referral_code')
    )

    if not referral_code:
      return None  # Пришёл не по реферальной ссылке

    # Найти партнёра
    try:
      partner = User.objects.get(referral_code=referral_code)
    except User.DoesNotExist:
      return None

    # АНТИФРОД ПРОВЕРКИ
    fraud_flags = AntiFraudService.check_registration(
      partner, new_user, request
    )

    if 'blocked' in fraud_flags:
      # Критический фрод → не засчитывать
      return None

    # Определить уровень
    level = 1  # Прямой реферал

    # Проверить: партнёр сам является рефералом?
    # Если да → создать запись 2-го уровня
    level2_partner = None
    if partner.referred_by:
      settings = ReferralSettings.get_settings()
      if settings.level2_enabled:
        level2_partner = partner.referred_by

    # Получить промо-ссылку
    promo_link_id = request.session.get('promo_link_id')
    promo_link = None
    if promo_link_id:
      try:
        promo_link = PromoLink.objects.get(id=promo_link_id)
      except PromoLink.DoesNotExist:
        pass

    ip = get_client_ip(request)

    # Создать запись реферала (1-й уровень)
    referral = Referral.objects.create(
      partner=partner,
      referral=new_user,
      referral_code_used=referral_code,
      source=request.GET.get('utm_source', ''),
      promo_link=promo_link,
      registration_ip=ip,
      registration_country=get_country_from_ip(ip),
      registration_device=get_device_type(
        request.META.get('HTTP_USER_AGENT', '')
      ),
      level=1,
      is_suspicious=bool(fraud_flags),
      fraud_flags=fraud_flags,
    )

    # Обновить User.referred_by
    new_user.referred_by = partner
    new_user.save(update_fields=['referred_by'])

    # Обновить статистику партнёра
    partner_profile = partner.partner_profile
    partner_profile.total_referrals = F('total_referrals') + 1
    partner_profile.monthly_referrals = F('monthly_referrals') + 1
    partner_profile.save(update_fields=[
      'total_referrals', 'monthly_referrals'
    ])

    # Обновить PromoLink статистику
    if promo_link:
      PromoLink.objects.filter(id=promo_link.id).update(
        registrations=F('registrations') + 1,
      )
      # Обновить конверсию
      promo_link.refresh_from_db()
      if promo_link.clicks > 0:
        promo_link.conversion_rate = (
          promo_link.registrations / promo_link.clicks * 100
        )
        promo_link.save(update_fields=['conversion_rate'])

    # Бонус за регистрацию (если есть)
    tier = partner_profile.tier
    if tier.signup_bonus > 0 and not referral.is_suspicious:
      CommissionService.create_commission(
        partner=partner,
        referral=referral,
        commission_type='signup_bonus',
        amount=tier.signup_bonus,
        description=f'Бонус за регистрацию {new_user.username}',
      )

    # Создать реферала 2-го уровня
    if level2_partner:
      Referral.objects.create(
        partner=level2_partner,
        referral=new_user,
        referral_code_used=referral_code,
        level=2,
        registration_ip=ip,
        is_suspicious=bool(fraud_flags),
        fraud_flags=fraud_flags,
      )

      level2_profile = level2_partner.partner_profile
      level2_profile.total_level2_referrals = (
        F('total_level2_referrals') + 1
      )
      level2_profile.save(update_fields=['total_level2_referrals'])

    # Уведомление партнёру
    NotificationService.create_notification(
      user=partner,
      notification_type='new_referral',
      title='🤝 Новый реферал!',
      message=f'Пользователь {new_user.username} '
              f'зарегистрировался по вашей ссылке.',
      icon='🤝',
      link='/partners/',
    )

    # Очистить сессию
    if 'referral_code' in request.session:
      del request.session['referral_code']
    if 'promo_link_id' in request.session:
      del request.session['promo_link_id']

    return referral


  qualify_referral(referral):
    """
    Квалифицировать реферала.
    Вызывается когда реферал выполняет условия:
      - Депозит >= min_deposit_to_qualify
      - Ставок >= min_bets_to_qualify
      - Оборот >= min_wagered_to_qualify
    """
    if referral.is_qualified:
      return  # Уже квалифицирован

    settings = ReferralSettings.get_settings()
    user = referral.referral

    # Проверить условия
    if referral.total_deposits < settings.min_deposit_to_qualify:
      return
    if referral.total_bets < settings.min_wagered_to_qualify:
      return
    # Количество ставок — считать из моделей ставок
    bets_count = ... # подсчёт из Bet + CasinoGame + Trade
    if bets_count < settings.min_bets_to_qualify:
      return

    referral.is_qualified = True
    referral.qualified_at = now()
    referral.status = 'active'
    referral.save(update_fields=['is_qualified', 'qualified_at', 'status'])

    # Обновить партнёрскую статистику
    partner_profile = referral.partner.partner_profile
    partner_profile.referrals_with_deposit = Referral.objects.filter(
      partner=referral.partner,
      is_qualified=True,
      level=1,
    ).count()
    partner_profile.save(update_fields=['referrals_with_deposit'])

    # Уведомление
    NotificationService.create_notification(
      user=referral.partner,
      notification_type='referral_qualified',
      title='✅ Реферал квалифицирован!',
      message=f'{user.username} выполнил условия. '
              f'Теперь вы получаете комиссию от его активности.',
      icon='✅',
      link='/partners/referrals/',
    )
```

### Обновление регистрации (интеграция)

```
В views регистрации (из Этапа 1) добавить:

  После успешного создания User:
    ReferralService.process_referral_registration(user, request)

Во всех способах регистрации:
  - Email: из формы (поле referral_code) + session/cookie
  - Google OAuth: из session/cookie
  - Telegram: из session/cookie
  - Телефон: из формы + session/cookie
```

### URL для реферальных ссылок

```
# config/urls.py

urlpatterns = [
    ...
    path('r/<str:code>/', referral_redirect_view, name='referral-redirect'),
    ...
]

def referral_redirect_view(request, code):
    return ReferralService.process_referral_click(request, code)
```

### Критерий готовности шага 8.2

```
□ Клик по реферальной ссылке: запись + cookie + редирект
□ Регистрация по ссылке: Referral создаётся
□ User.referred_by устанавливается
□ PromoLink статистика обновляется
□ Бонус за регистрацию начисляется
□ 2-й уровень создаётся (если включён)
□ Уведомление партнёру о новом реферале
□ Квалификация реферала при выполнении условий
□ Cookie хранится 30 дней
□ Интеграция со всеми способами регистрации
□ Антифрод проверки при регистрации (шаг 8.4)
□ Конверсия промо-ссылок рассчитывается
```

---

## ШАГ 8.3 — РАСЧЁТ И НАЧИСЛЕНИЕ КОМИССИЙ

### Задача

```
Реализуй расчёт GGR рефералов.
Начисление комиссий по расписанию.
Negative carryover. Бонусы за первый депозит.
Автоматическое повышение уровня партнёра.
```

### CommissionService

```
CommissionService:

  calculate_daily_commissions():
    """
    Celery задача. Запускается ежедневно в 02:00 UTC.
    Рассчитывает GGR каждого реферала за прошедший день.
    Начисляет комиссию партнёру.
    """

    yesterday = date.today() - timedelta(days=1)

    # Получить всех квалифицированных рефералов
    referrals = Referral.objects.filter(
      is_qualified=True,
      status__in=['deposited', 'active'],
      is_suspicious=False,
    ).select_related('partner', 'partner__partner_profile')

    for referral in referrals:
      calculate_referral_ggr(referral, yesterday)


  calculate_referral_ggr(referral, date):
    """
    Рассчитать GGR одного реферала за один день.
    
    GGR = сумма_ставок — сумма_выигрышей
    
    Включает:
      - Ставки на спорт: bet_amount — winnings
      - Казино: wagered — payouts
      - Predictions: total_invested — settlements
    """

    user = referral.referral

    # Спорт GGR за день
    sport_ggr = calculate_sport_ggr(user, date)

    # Казино GGR за день
    casino_ggr = calculate_casino_ggr(user, date)

    # Predictions GGR за день
    prediction_ggr = calculate_prediction_ggr(user, date)

    daily_ggr = sport_ggr + casino_ggr + prediction_ggr

    if daily_ggr == 0:
      return  # Нет активности

    # Обновить GGR реферала
    referral.total_ggr += daily_ggr
    referral.save(update_fields=['total_ggr'])

    # Проверить negative carryover
    carryover, _ = NegativeCarryover.objects.get_or_create(
      partner=referral.partner,
      referral=referral,
    )

    effective_ggr = daily_ggr + carryover.amount

    if effective_ggr <= 0:
      # GGR всё ещё отрицательный
      carryover.amount = effective_ggr
      carryover.save()
      
      # Записать комиссию с нулевой суммой (для отчётности)
      Commission.objects.create(
        partner=referral.partner,
        referral=referral,
        commission_type='ggr',
        period_start=date,
        period_end=date,
        referral_ggr=daily_ggr,
        commission_rate=Decimal('0'),
        gross_amount=Decimal('0'),
        adjustments=carryover.amount,
        net_amount=Decimal('0'),
        status='approved',
      )
      return

    # GGR положительный → рассчитать комиссию
    # Сбросить carryover
    carryover.amount = Decimal('0')
    carryover.save()

    # Определить процент комиссии
    partner_profile = referral.partner.partner_profile
    referral_age_months = (
      (date - referral.registered_at.date()).days // 30
    ) + 1

    commission_rate = partner_profile.get_commission_rate(
      referral_age_months
    )

    # Рассчитать комиссию
    commission_amount = effective_ggr * (commission_rate / 100)

    if commission_amount <= 0:
      return

    # Создать запись комиссии
    commission = Commission.objects.create(
      partner=referral.partner,
      referral=referral,
      commission_type='ggr',
      period_start=date,
      period_end=date,
      referral_ggr=daily_ggr,
      commission_rate=commission_rate,
      gross_amount=commission_amount,
      adjustments=Decimal('0'),
      net_amount=commission_amount,
      status='approved',
    )

    # Зачислить на партнёрский баланс
    partner_profile.balance += commission_amount
    partner_profile.total_earned += commission_amount
    partner_profile.monthly_earned += commission_amount
    partner_profile.save(update_fields=[
      'balance', 'total_earned', 'monthly_earned'
    ])

    # Обновить статистику партнёра
    partner_profile.total_referral_ggr += daily_ggr
    partner_profile.monthly_ggr += daily_ggr
    partner_profile.save(update_fields=[
      'total_referral_ggr', 'monthly_ggr'
    ])

    # 2-й уровень
    if referral.level == 1:
      calculate_level2_commission(referral, daily_ggr, date)

    # Уведомление (раз в день — суммарное)
    # Отправляется отдельной задачей после обработки всех рефералов


  calculate_level2_commission(referral, ggr, date):
    """Комиссия 2-го уровня."""
    settings = ReferralSettings.get_settings()
    if not settings.level2_enabled:
      return

    # Партнёр 2-го уровня = тот кто привёл партнёра 1-го уровня
    level1_partner = referral.partner
    if not level1_partner.referred_by:
      return

    level2_partner = level1_partner.referred_by
    level2_profile = level2_partner.partner_profile

    rate = level2_profile.tier.level2_commission_rate
    if rate <= 0:
      return

    commission_amount = ggr * (rate / 100)
    if commission_amount <= 0:
      return

    # Найти или создать реферал 2-го уровня
    level2_referral, _ = Referral.objects.get_or_create(
      partner=level2_partner,
      referral=referral.referral,
      level=2,
      defaults={
        'referral_code_used': level1_partner.referral_code,
        'registration_ip': referral.registration_ip,
        'status': referral.status,
      }
    )

    Commission.objects.create(
      partner=level2_partner,
      referral=level2_referral,
      commission_type='level2_ggr',
      period_start=date,
      period_end=date,
      referral_ggr=ggr,
      commission_rate=rate,
      gross_amount=commission_amount,
      net_amount=commission_amount,
      status='approved',
    )

    level2_profile.balance += commission_amount
    level2_profile.total_earned += commission_amount
    level2_profile.total_level2_earned += commission_amount
    level2_profile.save(update_fields=[
      'balance', 'total_earned', 'total_level2_earned'
    ])


  calculate_sport_ggr(user, date):
    """GGR от ставок на спорт за день."""
    from apps.sports.models import Bet
    
    bets = Bet.objects.filter(
      user=user,
      settled_at__date=date,
      status__in=['won', 'lost'],
    )
    
    total_staked = bets.aggregate(s=Sum('amount'))['s'] or 0
    total_won = bets.filter(status='won').aggregate(
      s=Sum('payout')
    )['s'] or 0
    
    return total_staked - total_won


  calculate_casino_ggr(user, date):
    """GGR от казино за день."""
    from apps.casino.models import CasinoRound
    
    rounds = CasinoRound.objects.filter(
      user=user,
      played_at__date=date,
    )
    
    total_wagered = rounds.aggregate(s=Sum('bet_amount'))['s'] or 0
    total_won = rounds.aggregate(s=Sum('payout'))['s'] or 0
    
    return total_wagered - total_won


  calculate_prediction_ggr(user, date):
    """GGR от predictions за день."""
    from apps.predictions.models import Trade
    
    # Покупки = ставки
    buys = Trade.objects.filter(
      user=user,
      trade_type='buy',
      created_at__date=date,
    ).aggregate(s=Sum('total_amount'))['s'] or 0
    
    # Продажи и выплаты = выигрыши
    sells = Trade.objects.filter(
      user=user,
      trade_type='sell',
      created_at__date=date,
    ).aggregate(s=Sum('total_amount'))['s'] or 0
    
    # Settlements за этот день
    from apps.predictions.models import UserPosition
    settlements = UserPosition.objects.filter(
      user=user,
      is_settled=True,
      # settled_at__date=date,  # нужно добавить поле
    ).aggregate(s=Sum('settlement_amount'))['s'] or 0
    
    return buys - sells - settlements


  process_first_deposit(user, deposit_amount):
    """
    Вызывается при первом депозите реферала.
    Начисляет бонус за первый депозит партнёру.
    """
    try:
      referral = Referral.objects.get(
        referral=user, level=1
      )
    except Referral.DoesNotExist:
      return  # Не реферал

    if referral.first_deposit_at is not None:
      return  # Уже был первый депозит

    # Обновить реферала
    referral.first_deposit_amount = deposit_amount
    referral.first_deposit_at = now()
    referral.total_deposits += deposit_amount
    referral.status = 'deposited'
    referral.save()

    # Бонус за первый депозит
    partner_profile = referral.partner.partner_profile
    rate = partner_profile.tier.first_deposit_bonus_rate

    if rate > 0:
      bonus = deposit_amount * (rate / 100)
      
      Commission.objects.create(
        partner=referral.partner,
        referral=referral,
        commission_type='first_deposit',
        period_start=date.today(),
        period_end=date.today(),
        commission_rate=rate,
        gross_amount=bonus,
        net_amount=bonus,
        status='approved',
      )
      
      partner_profile.balance += bonus
      partner_profile.total_earned += bonus
      partner_profile.save(update_fields=['balance', 'total_earned'])

      NotificationService.create_notification(
        user=referral.partner,
        notification_type='referral_commission',
        title='💰 Бонус за первый депозит реферала!',
        message=f'{user.username} сделал первый депозит '
                f'${deposit_amount:.2f}. '
                f'Ваш бонус: ${bonus:.2f}',
        icon='💰',
        link='/partners/',
      )

    # Обновить PromoLink
    if referral.promo_link:
      PromoLink.objects.filter(id=referral.promo_link.id).update(
        deposits=F('deposits') + 1,
        total_deposit_amount=F('total_deposit_amount') + deposit_amount,
      )

    # Попробовать квалифицировать
    ReferralService.qualify_referral(referral)


  create_commission(partner, referral, commission_type,
                    amount, description=''):
    """Создать ручную или бонусную комиссию."""
    commission = Commission.objects.create(
      partner=partner,
      referral=referral,
      commission_type=commission_type,
      period_start=date.today(),
      period_end=date.today(),
      commission_rate=Decimal('0'),
      gross_amount=amount,
      net_amount=amount,
      status='approved',
      notes=description,
    )

    partner_profile = partner.partner_profile
    partner_profile.balance += amount
    partner_profile.total_earned += amount
    partner_profile.save(update_fields=['balance', 'total_earned'])

    return commission
```

### Автоматическое повышение уровня партнёра

```
PartnerTierService:

  check_and_upgrade(partner):
    """
    Проверить и повысить уровень партнёра.
    Вызывается:
      - После каждой квалификации реферала
      - Ежедневно (Celery)
      - При начислении комиссии
    """

    profile = partner.partner_profile
    current_tier = profile.tier
    
    # Получить все уровни выше текущего
    higher_tiers = PartnerTier.objects.filter(
      sort_order__gt=current_tier.sort_order,
      is_active=True,
    ).order_by('sort_order')

    for tier in higher_tiers:
      if can_upgrade_to(profile, tier):
        old_tier = profile.tier
        profile.tier = tier
        profile.tier_changed_at = now()
        profile.save(update_fields=['tier', 'tier_changed_at'])

        NotificationService.create_notification(
          user=partner,
          notification_type='partner_tier_up',
          title=f'🎉 Вы достигли уровня {tier.name}!',
          message=f'Поздравляем! Ваш партнёрский уровень '
                  f'повышен с {old_tier.name} до {tier.name}. '
                  f'Новые комиссионные ставки уже активны.',
          icon=tier.icon,
          link='/partners/',
        )

        AdminActionLog.objects.create(
          admin_user=None,
          action_type='partner_tier_changed',
          target_user=partner,
          description=f'Auto: {old_tier.name} → {tier.name}',
          details={
            'old_tier': old_tier.slug,
            'new_tier': tier.slug,
          },
        )
      else:
        break  # Если не можем на этот уровень, выше тоже нет


  can_upgrade_to(profile, tier):
    """Проверить соответствие условиям уровня."""

    # Активные рефералы (квалифицированные)
    active_refs = Referral.objects.filter(
      partner=profile.user,
      is_qualified=True,
      level=1,
      status__in=['active', 'deposited'],
    ).count()

    if active_refs < tier.min_referrals:
      return False

    # Месячный GGR
    if profile.monthly_ggr < tier.min_monthly_ggr:
      return False

    return True


  check_downgrade():
    """
    Celery задача (ежемесячно, 1-го числа).
    Проверить нужно ли понизить уровень партнёров.
    
    Если партнёр 2 месяца подряд не выполняет условия
    текущего уровня → понизить на 1 уровень.
    """

    profiles = PartnerProfile.objects.filter(
      is_partner_active=True,
      tier__sort_order__gt=1,  # Не стартовый
    ).select_related('tier', 'user')

    for profile in profiles:
      if not can_upgrade_to(profile, profile.tier):
        # Проверить: второй месяц подряд?
        # (нужно хранить историю — упрощённо: просто проверяем)
        lower_tier = PartnerTier.objects.filter(
          sort_order__lt=profile.tier.sort_order,
          is_active=True,
        ).order_by('-sort_order').first()

        if lower_tier:
          old_tier = profile.tier
          profile.tier = lower_tier
          profile.tier_changed_at = now()
          profile.save(update_fields=['tier', 'tier_changed_at'])

          NotificationService.create_notification(
            user=profile.user,
            notification_type='partner_tier_down',
            title=f'Уровень партнёра изменён',
            message=f'Ваш партнёрский уровень изменён '
                    f'с {old_tier.name} на {lower_tier.name}. '
                    f'Привлекайте больше рефералов для повышения.',
            icon='📉',
            link='/partners/',
          )


  reset_monthly_stats():
    """
    Celery задача (ежемесячно, 1-го числа 00:01 UTC).
    Сбросить месячные счётчики.
    """

    # Сохранить лучший месяц перед сбросом
    profiles = PartnerProfile.objects.filter(
      monthly_earned__gt=0
    )
    for profile in profiles:
      if profile.monthly_earned > profile.best_month_earnings:
        profile.best_month_earnings = profile.monthly_earned
        profile.best_month_date = date.today() - timedelta(days=1)
        profile.save(update_fields=[
          'best_month_earnings', 'best_month_date'
        ])

    # Сбросить
    PartnerProfile.objects.all().update(
      monthly_ggr=0,
      monthly_earned=0,
      monthly_referrals=0,
    )
```

### Интеграция с депозитами и ставками

```
Добавить вызовы в существующий код:

1. При депозите пользователя (apps/wallet/):
   После успешного депозита:
     CommissionService.process_first_deposit(user, amount)
   
   При каждом депозите:
     # Обновить total_deposits реферала
     try:
       referral = Referral.objects.get(referral=user, level=1)
       referral.total_deposits += amount
       referral.save(update_fields=['total_deposits'])
     except Referral.DoesNotExist:
       pass

2. При каждой ставке (спорт/казино/predictions):
   После ставки:
     # Обновить total_bets реферала
     try:
       referral = Referral.objects.get(referral=user, level=1)
       referral.total_bets += amount
       referral.save(update_fields=['total_bets'])
       ReferralService.qualify_referral(referral)
     except Referral.DoesNotExist:
       pass
```

### Критерий готовности шага 8.3

```
□ calculate_daily_commissions: расчёт GGR за день
□ GGR считается корректно: спорт + казино + predictions
□ Negative carryover работает
□ Комиссия зависит от возраста реферала (1м/2-3м/4+м)
□ Комиссия зависит от уровня партнёра
□ 2-й уровень комиссий работает
□ Бонус за первый депозит начисляется
□ Бонус за регистрацию начисляется
□ Баланс партнёра обновляется
□ Автоматическое повышение уровня
□ Проверка понижения уровня (ежемесячно)
□ Сброс месячных счётчиков (ежемесячно)
□ Интеграция с депозитами
□ Интеграция со ставками
□ Квалификация рефералов
□ Уведомления о комиссиях
□ Commission записи создаются
□ Celery: ежедневный расчёт в 02:00 UTC
```

---

## ШАГ 8.4 — АНТИФРОД СИСТЕМА

### Задача

```
Реализуй защиту от фрода в реферальной программе.
Мульти-аккаунты, фейковые рефералы, self-referral.
Автоматические и ручные проверки.
```

### AntiFraudService

```
AntiFraudService:

  check_registration(partner, new_user, request):
    """
    Проверка при регистрации реферала.
    Возвращает список флагов.
    Пустой список = чисто.
    """

    flags = []
    ip = get_client_ip(request)
    settings = ReferralSettings.get_settings()

    # 1. Self-referral (свой же код)
    if partner.email == new_user.email:
      flags.append('self_referral')
      return ['blocked']  # Критический

    # 2. Тот же IP что у партнёра
    if ip == partner.last_login_ip or ip == partner.registration_ip:
      flags.append('same_ip_as_partner')

    # 3. Слишком много рефералов с этого IP
    same_ip_count = Referral.objects.filter(
      partner=partner,
      registration_ip=ip,
    ).count()
    if same_ip_count >= settings.max_referrals_per_ip:
      flags.append('too_many_from_ip')
      if same_ip_count >= settings.max_referrals_per_ip * 2:
        return ['blocked']

    # 4. Слишком быстрые регистрации
    recent_registrations = Referral.objects.filter(
      partner=partner,
      registered_at__gte=now() - timedelta(
        seconds=settings.min_time_between_registrations
      ),
    ).count()
    if recent_registrations > 0:
      flags.append('rapid_registration')

    # 5. Слишком много за день
    today_count = Referral.objects.filter(
      partner=partner,
      registered_at__date=date.today(),
    ).count()
    if today_count >= settings.max_referrals_per_day:
      flags.append('daily_limit_exceeded')

    # 6. Одинаковый user_agent (fingerprint)
    ua = request.META.get('HTTP_USER_AGENT', '')
    same_ua_count = Referral.objects.filter(
      partner=partner,
      registration_ip=ip,
    ).count()
    # Проверяем через LoginHistory
    if same_ua_count > 5:
      flags.append('same_device_fingerprint')

    # 7. Подозрительный email домен
    email_domain = new_user.email.split('@')[1].lower()
    disposable_domains = [
      'tempmail.com', 'guerrillamail.com', 'throwaway.email',
      'mailinator.com', 'yopmail.com', 'trashmail.com',
      '10minutemail.com', 'temp-mail.org',
      # ... расширяемый список
    ]
    if email_domain in disposable_domains:
      flags.append('disposable_email')

    # 8. Страна не совпадает (подозрительно, не блокируем)
    user_country = get_country_from_ip(ip)
    partner_country = partner.country
    if partner_country and user_country and partner_country != user_country:
      # Не флаг сам по себе, но в комбинации с другими
      pass

    # Решение
    if len(flags) >= 3:
      flags.append('high_risk')
      if settings.auto_block_on_fraud:
        flags.append('blocked')

    return flags


  daily_fraud_check():
    """
    Celery задача. Ежедневная проверка на фрод.
    Анализирует паттерны за последние 24 часа.
    """

    yesterday = date.today() - timedelta(days=1)

    # 1. Партнёры с аномально высоким количеством регистраций
    suspicious_partners = (
      Referral.objects
      .filter(registered_at__date=yesterday)
      .values('partner')
      .annotate(count=Count('id'))
      .filter(count__gt=20)  # > 20 за день
    )

    for sp in suspicious_partners:
      partner = User.objects.get(id=sp['partner'])
      flag_partner(partner, 'high_registration_volume',
                   f'{sp["count"]} регистраций за день')

    # 2. Рефералы без активности
    # Рефералы зарегистрированные > 7 дней назад,
    # ни одного депозита, ни одной ставки
    inactive_referrals = Referral.objects.filter(
      registered_at__lt=now() - timedelta(days=7),
      total_deposits=0,
      status='registered',
    )

    # Партнёры с > 80% неактивных рефералов
    partner_stats = (
      Referral.objects
      .filter(level=1)
      .values('partner')
      .annotate(
        total=Count('id'),
        inactive=Count('id', filter=Q(
          total_deposits=0,
          registered_at__lt=now() - timedelta(days=7),
        )),
      )
    )

    for ps in partner_stats:
      if ps['total'] >= 10:
        inactive_rate = ps['inactive'] / ps['total']
        if inactive_rate > 0.8:
          partner = User.objects.get(id=ps['partner'])
          flag_partner(partner, 'high_inactive_rate',
                       f'{inactive_rate*100:.0f}% неактивных')

    # 3. Рефералы которые сразу выводят
    # Депозит → без ставок → вывод (отмывание)
    quick_withdrawers = Referral.objects.filter(
      first_deposit_at__gte=now() - timedelta(days=1),
      total_bets=0,
    )
    # Проверить есть ли у них запросы на вывод
    for ref in quick_withdrawers:
      # from apps.wallet... check withdrawals
      pass

    # 4. Одинаковые паттерны ставок
    # (все рефералы одного партнёра делают одинаковые ставки
    #  = ботоферма)
    # Сложная проверка, базовая версия:
    # Проверить совпадения по времени + сумме + матчу
    pass


  flag_partner(partner, flag_type, details):
    """Пометить партнёра для ручной проверки."""
    profile = partner.partner_profile
    profile.is_suspended = True
    profile.suspension_reason = f'{flag_type}: {details}'
    profile.save(update_fields=['is_suspended', 'suspension_reason'])

    # Уведомление админам
    NotificationService.create_notification(
      user=None,  # Системное, для всех админов
      notification_type='system',
      title=f'⚠️ Подозрительный партнёр: {partner.username}',
      message=f'Флаг: {flag_type}. {details}',
      icon='⚠️',
      link=f'/admin/referral/partner/{partner.id}/',
    )

    AdminActionLog.objects.create(
      admin_user=None,
      action_type='partner_flagged',
      target_user=partner,
      description=f'Auto fraud detection: {flag_type}',
      details={'flag_type': flag_type, 'details': details},
    )


  manual_review(partner, admin, action, reason=''):
    """
    Ручное решение админа после проверки.
    action: 'approve' | 'block' | 'suspend'
    """

    profile = partner.partner_profile

    if action == 'approve':
      profile.is_suspended = False
      profile.suspension_reason = ''
      profile.save()

    elif action == 'block':
      profile.is_partner_active = False
      profile.is_suspended = False
      profile.suspension_reason = reason
      profile.save()

      # Аннулировать незаработанные комиссии
      Commission.objects.filter(
        partner=partner,
        status='pending',
      ).update(status='cancelled')

      NotificationService.create_notification(
        user=partner,
        notification_type='system',
        title='Партнёрская программа приостановлена',
        message=f'Ваше участие в партнёрской программе '
                f'приостановлено. Причина: {reason}. '
                f'Обратитесь в поддержку.',
        icon='🚫',
      )

    elif action == 'suspend':
      profile.is_suspended = True
      profile.suspension_reason = reason
      profile.save()

    AdminActionLog.objects.create(
      admin_user=admin,
      action_type=f'partner_{action}',
      target_user=partner,
      description=f'Manual: {action}. {reason}',
    )
```

### Критерий готовности шага 8.4

```
□ Self-referral блокируется
□ Проверка совпадения IP партнёра и реферала
□ Лимит рефералов с одного IP
□ Лимит скорости регистраций
□ Лимит регистраций за день
□ Проверка disposable email
□ Комбинированный risk score
□ Ежедневная Celery проверка паттернов
□ Обнаружение высокого % неактивных рефералов
□ Автоматическая приостановка подозрительных
□ Ручная проверка админом (approve/block/suspend)
□ Аннулирование комиссий при блокировке
□ Уведомления админам о подозрительных
□ AdminActionLog для всех действий
```

---

## ШАГ 8.5 — ПАРТНЁРСКАЯ ПАНЕЛЬ (ФРОНТЕНД)

### Задача

```
Создай полную партнёрскую панель:
дашборд, список рефералов, статистика,
промо-материалы, выплаты, настройки.
```

### Структура URL

```
/partners/                     # Дашборд
/partners/referrals/           # Список рефералов
/partners/commissions/         # Комиссии
/partners/payouts/             # Выплаты
/partners/payouts/request/     # Запрос выплаты
/partners/promo/               # Промо-материалы
/partners/promo/create/        # Создать промо-ссылку
/partners/stats/               # Детальная статистика
/partners/settings/            # Настройки партнёра

# API (HTMX)
/api/partners/stats/           # Данные дашборда
/api/partners/chart/           # Данные графика
/api/partners/referrals/       # Список рефералов (пагинация)
```

### Дашборд партнёра

```
URL: /partners/
Доступ: @login_required

  ┌──────────────────────────────────────────────────────────────┐
  │  🤝 Партнёрская панель                                      │
  │                                                              │
  │  ── Ваш уровень ──────────────────────────────────────────  │
  │  🥈 Продвинутый                                             │
  │  [██████████████░░░░░░] 70% до Профи                        │
  │  Нужно: 50 рефералов (у вас: 35) + $2,000 GGR/мес ($1,400) │
  │                                                              │
  │  ── Ваша ссылка ───────────────────────────────────────────  │
  │  🔗 https://dod.com/r/DOD-X7K9M2                            │
  │  [📋 Копировать]  [📱 QR]  [📤 Поделиться]                  │
  │                                                              │
  │  ── Сводка ────────────────────────────────────────────────  │
  │                                                              │
  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
  │  │ 💰       │ │ 👥       │ │ 📊       │ │ 💵       │       │
  │  │ $234.50  │ │ 35       │ │ $1,400   │ │ $187.50  │       │
  │  │ Баланс   │ │ Рефералы │ │ GGR/мес  │ │ За месяц │       │
  │  │          │ │ (актив.) │ │          │ │          │       │
  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
  │                                                              │
  │  ── Доход за период ───────────────────────────────────────  │
  │  [Неделя|Месяц|3 месяца|Год|Всё]                            │
  │                                                              │
  │  $250 ┤                    ╱──                               │
  │       │              ╱──╱                                    │
  │  $200 ┤         ╱──╱                                        │
  │       │    ╱──╱                                              │
  │  $150 ┤ ╱╱                                                   │
  │       │╱                                                     │
  │  $100 ┤                                                      │
  │       └─────────────────────────────                         │
  │       1мар  5мар  10мар  15мар  20мар                        │
  │                                                              │
  │  ── Комиссионные ставки ───────────────────────────────────  │
  │                                                              │
  │  ┌─────────────────────────────────────────────────────────┐ │
  │  │ Возраст реферала │ Ваш %  │ Следующий уровень (Профи) │ │
  │  ├──────────────────┼────────┼───────────────────────────┤ │
  │  │ 1-й месяц        │ 40%    │ 45%                       │ │
  │  │ 2-3 месяц        │ 30%    │ 35%                       │ │
  │  │ 4+ месяц         │ 20%    │ 25%                       │ │
  │  │ 2-й уровень      │ 3%     │ 5%                        │ │
  │  └─────────────────────────────────────────────────────────┘ │
  │                                                              │
  │  ── Последние рефералы ────────────────────────────────────  │
  │                                                              │
  │  🟢 user456 • зарег. вчера • депозит: $50 • GGR: $12.30   │
  │  🟡 player789 • зарег. 3 дня • депозит: $0 • ожидание      │
  │  🟢 trader123 • зарег. 1 нед • депозит: $200 • GGR: $45.60│
  │                                                              │
  │  [Все рефералы →]                                            │
  │                                                              │
  │  ── Последние комиссии ────────────────────────────────────  │
  │                                                              │
  │  💰 $12.30 от user456 (GGR: $41.00 × 30%)  • сегодня      │
  │  💰 $9.12 от trader123 (GGR: $45.60 × 20%) • вчера        │
  │  🎁 $5.00 бонус за первый депозит user456  • вчера        │
  │                                                              │
  │  [Все комиссии →]                                            │
  │                                                              │
  │  ── Быстрые действия ─────────────────────────────────────  │
  │  [💵 Вывести средства]  [📋 Промо-материалы]               │
  │  [📊 Детальная статистика]                                   │
  │                                                              │
  └──────────────────────────────────────────────────────────────┘
```

### Список рефералов

```
URL: /partners/referrals/

  ┌──────────────────────────────────────────────────────────────┐
  │  👥 Мои рефералы                                            │
  │                                                              │
  │  Фильтры:                                                   │
  │  [Все|Активные|С депозитом|Без депозита|Заблокированные]    │
  │  Уровень: [1-й|2-й|Все]                                     │
  │  Поиск: [________________________] 🔍                       │
  │  Период: [За неделю|Месяц|3 мес|Всё]                       │
  │                                                              │
  │  Сортировка: [Дата↓|GGR↓|Депозиты↓|Комиссии↓]             │
  │                                                              │
  │  ── Всего: 35 рефералов | С депозитом: 22 | Активных: 18 ── │
  │                                                              │
  │  ┌──────────────────────────────────────────────────────┐   │
  │  │ 🟢 user456                            Уровень: 1    │   │
  │  │    Зарегистрирован: 15.03.2025 (5 дней назад)       │   │
  │  │    Через: Промо "YouTube канал"                     │   │
  │  │    Страна: 🇷🇺 Россия │ Устройство: mobile          │   │
  │  │    ─────────────────────────────────────────────── │   │
  │  │    Депозиты: $250  │ GGR: $78.40  │ Ставок: 45    │   │
  │  │    Ваша комиссия: $23.52 (30%)                     │   │
  │  │    Статус: ✅ Активный, квалифицирован              │   │
  │  │    Последняя активность: 2 часа назад               │   │
  │  └──────────────────────────────────────────────────────┘   │
  │                                                              │
  │  ┌──────────────────────────────────────────────────────┐   │
  │  │ 🟡 player789                          Уровень: 1    │   │
  │  │    Зарегистрирован: 18.03.2025 (2 дня назад)        │   │
  │  │    Через: Реферальный код                           │   │
  │  │    Страна: 🇺🇦 Украина │ Устройство: desktop        │   │
  │  │    ─────────────────────────────────────────────── │   │
  │  │    Депозиты: $0  │ GGR: $0  │ Ставок: 0           │   │
  │  │    Ваша комиссия: $0                               │   │
  │  │    Статус: ⏳ Зарегистрирован, ожидание депозита    │   │
  │  └──────────────────────────────────────────────────────┘   │
  │                                                              │
  │  (2-й уровень показывается отдельно или в том же списке)   │
  │  ┌──────────────────────────────────────────────────────┐   │
  │  │ 🔵 gamer999                           Уровень: 2    │   │
  │  │    Реферал вашего реферала trader123                 │   │
  │  │    GGR: $34.20  │ Ваша комиссия: $1.03 (3%)        │   │
  │  └──────────────────────────────────────────────────────┘   │
  │                                                              │
  │  [Загрузить ещё] (HTMX)                                    │
  │                                                              │
  │  ── Экспорт ──────────────────────────────────────────────  │
  │  [📥 CSV] [📥 Excel]                                        │
  │                                                              │
  └──────────────────────────────────────────────────────────────┘

Приватность:
  Партнёр видит:
    - Username реферала
    - Дату регистрации
    - Общие суммы (депозит, GGR)
    - Статус
  
  Партнёр НЕ видит:
    - Email реферала
    - Телефон
    - Точные ставки и их детали
    - Баланс реферала
    - Персональные данные
```

### Промо-материалы

```
URL: /partners/promo/

  ┌──────────────────────────────────────────────────────────────┐
  │  📋 Промо-материалы                                         │
  │                                                              │
  │  ── Ваши промо-ссылки ────────────────────────────────────  │
  │  [➕ Создать новую ссылку]                                   │
  │                                                              │
  │  ┌──────────────────────────────────────────────────────┐   │
  │  │ 🔗 YouTube канал                                    │   │
  │  │    https://dod.com/r/my-youtube                      │   │
  │  │    [📋 Копировать]  [📱 QR]                          │   │
  │  │    ─────────────────────────────────────────────── │   │
  │  │    Клики: 1,234  │ Регистрации: 89  │ Conv: 7.2%  │   │
  │  │    Депозиты: 45  │ GGR: $3,456  │ Заработано: $890│   │
  │  │    [✏️ Редакт.] [📊 Статистика] [🗑️ Удалить]       │   │
  │  └──────────────────────────────────────────────────────┘   │
  │                                                              │
  │  ┌──────────────────────────────────────────────────────┐   │
  │  │ 🔗 Telegram пост                                    │   │
  │  │    https://dod.com/r/tg-march-2025                   │   │
  │  │    Клики: 567  │ Регистрации: 34  │ Conv: 6.0%     │   │
  │  │    Депозиты: 18  │ GGR: $1,234  │ Заработано: $345 │   │
  │  └──────────────────────────────────────────────────────┘   │
  │                                                              │
  │  ── QR-код ────────────────────────────────────────────────  │
  │                                                              │
  │  ┌──────────────┐                                           │
  │  │  [QR CODE]   │  Ваша основная ссылка                    │
  │  │              │  https://dod.com/r/DOD-X7K9M2            │
  │  │              │  [📥 Скачать PNG]                         │
  │  └──────────────┘                                           │
  │                                                              │
  │  ── Баннеры ───────────────────────────────────────────────  │
  │                                                              │
  │  ┌─────────────────┐  ┌─────────────────┐                  │
  │  │   [BANNER 1]    │  │   [BANNER 2]    │                  │
  │  │   728×90         │  │   300×250        │                  │
  │  │   [📥 Скачать]   │  │   [📥 Скачать]   │                  │
  │  │   [📋 HTML код]  │  │   [📋 HTML код]  │                  │
  │  └─────────────────┘  └─────────────────┘                  │
  │                                                              │
  │  ┌─────────────────┐  ┌─────────────────┐                  │
  │  │   [BANNER 3]    │  │   [BANNER 4]    │                  │
  │  │   160×600        │  │   320×50         │                  │
  │  │   [📥 Скачать]   │  │   [📥 Скачать]   │                  │
  │  │   [📋 HTML код]  │  │   [📋 HTML код]  │                  │
  │  └─────────────────┘  └─────────────────┘                  │
  │                                                              │
  │  HTML код баннера (с вашей ссылкой):                        │
  │  ┌────────────────────────────────────────────────────────┐│
  │  │ <a href="https://dod.com/r/DOD-X7K9M2">              ││
  │  │   <img src="https://dod.com/static/banners/728.png"/> ││
  │  │ </a>                                                   ││
  │  └────────────────────────────────────────────────────────┘│
  │  [📋 Копировать]                                            │
  │                                                              │
  └──────────────────────────────────────────────────────────────┘

Создание промо-ссылки:
  ┌──────────────────────────────────────────────┐
  │  ➕ Новая промо-ссылка                      │
  │                                              │
  │  Название (для себя) *                      │
  │  ┌──────────────────────────────────┐       │
  │  │ YouTube видео март              │       │
  │  └──────────────────────────────────┘       │
  │                                              │
  │  Кастомный URL (необязательно)              │
  │  dod.com/r/                                  │
  │  ┌──────────────────────────────────┐       │
  │  │ youtube-march-2025              │       │
  │  └──────────────────────────────────┘       │
  │  Только a-z, 0-9, дефис. 3-50 символов.    │
  │                                              │
  │  UTM метки (необязательно)                  │
  │  Source: [youtube     ]                     │
  │  Medium: [video       ]                     │
  │  Campaign: [march_2025 ]                    │
  │                                              │
  │  [Создать]                                  │
  │                                              │
  └──────────────────────────────────────────────┘
```

### Запрос выплаты

```
URL: /partners/payouts/request/

  ┌──────────────────────────────────────────────────┐
  │  💵 Вывод партнёрских средств                   │
  │                                                  │
  │  Доступный баланс: $234.50                      │
  │  Минимальная сумма вывода: $30.00                │
  │                                                  │
  │  Сумма вывода                                   │
  │  ┌──────────────────────────────────────┐       │
  │  │ 234.50                               │       │
  │  └──────────────────────────────────────┘       │
  │  [Вывести всё]                                  │
  │                                                  │
  │  Куда вывести                                   │
  │                                                  │
  │  ○ 🎮 На игровой баланс (мгновенно)            │
  │  ○ 💰 На кошелёк DOD (далее можно вывести)      │
  │  ○ 💎 USDT (TRC20) — прямой вывод              │
  │    Адрес: [____________________________]        │
  │  ○ 💳 Банковская карта                          │
  │    Номер: [____________________________]        │
  │                                                  │
  │  [Запросить вывод]                              │
  │                                                  │
  │  ── История выплат ─────────────────────────── │
  │                                                  │
  │  ✅ $150.00 → Игровой баланс • 10.03.2025      │
  │  ✅ $87.50 → USDT TRC20 • 01.03.2025           │
  │  ⏳ $45.00 → Банковская карта • Ожидает        │
  │                                                  │
  └──────────────────────────────────────────────────┘

Логика:
  1. Проверить минимальную сумму (по уровню)
  2. Проверить что партнёр не приостановлен
  3. Если на игровой баланс → мгновенно:
     - Списать с partner_profile.balance
     - Зачислить на wallet
     - Статус: completed
  4. Если на кошелёк DOD → мгновенно:
     - Списать с partner_profile.balance
     - Зачислить на wallet
     - Статус: completed
  5. Если USDT или карта → запрос на проверку:
     - Создать PartnerPayout(status='pending')
     - Админ одобряет/отклоняет
     - Уведомление партнёру
  6. Запросить 2FA если включена
```

### Детальная статистика

```
URL: /partners/stats/

  ┌──────────────────────────────────────────────────────────────┐
  │  📊 Детальная статистика                                    │
  │                                                              │
  │  Период: [Неделя|Месяц|3 мес|6 мес|Год|Всё|Кастом]         │
  │                                                              │
  │  ── Общие показатели ──────────────────────────────────────  │
  │                                                              │
  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
  │  │ $1,234   │ │ $890     │ │ $344     │ │ 35       │       │
  │  │ Всего    │ │ Выведено │ │ Баланс   │ │ Всего    │       │
  │  │ заработ. │ │          │ │          │ │ рефералов│       │
  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
  │                                                              │
  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
  │  │ 22       │ │ 62.8%    │ │ $4,567   │ │ $78.40   │       │
  │  │ С депоз. │ │ Конверс. │ │ GGR      │ │ GGR/реф  │       │
  │  │ рефер.   │ │ рег→деп  │ │ рефералов│ │ средний  │       │
  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
  │                                                              │
  │  ── График дохода ─────────────────────────────────────────  │
  │  (линейный график, по дням/неделям/месяцам)                 │
  │                                                              │
  │  ── По источникам ─────────────────────────────────────────  │
  │                                                              │
  │  ┌────────────────────┬───────┬──────┬──────┬─────────┐    │
  │  │ Источник           │ Клики │ Рег. │ Деп. │ Доход   │    │
  │  ├────────────────────┼───────┼──────┼──────┼─────────┤    │
  │  │ YouTube канал      │ 1,234 │  89  │  45  │ $890.00 │    │
  │  │ Telegram пост      │   567 │  34  │  18  │ $345.00 │    │
  │  │ Прямая ссылка      │   234 │  12  │   5  │  $99.00 │    │
  │  └────────────────────┴───────┴──────┴──────┴─────────┘    │
  │                                                              │
  │  ── По продуктам ──────────────────────────────────────────  │
  │                                                              │
  │  ⚽ Спорт:        GGR $2,345 │ Комиссия $585             │
  │  🎰 Казино:       GGR $1,890 │ Комиссия $472             │
  │  📊 Predictions:  GGR $332   │ Комиссия $77              │
  │                                                              │
  │  ── Топ рефералы ──────────────────────────────────────────  │
  │                                                              │
  │  1. trader123    │ GGR: $890  │ Комиссия: $267           │
  │  2. user456      │ GGR: $567  │ Комиссия: $170           │
  │  3. player789    │ GGR: $345  │ Комиссия: $103           │
  │                                                              │
  │  ── Экспорт ───────────────────────────────────────────────  │
  │  [📥 CSV] [📥 Excel] [📥 PDF отчёт]                         │
  │                                                              │
  └──────────────────────────────────────────────────────────────┘
```

### Критерий готовности шага 8.5

```
□ Дашборд: баланс, рефералы, GGR, комиссии
□ График дохода за период
□ Комиссионные ставки текущего уровня
□ Прогресс к следующему уровню
□ Список рефералов с фильтрами и поиском
□ Детальная карточка каждого реферала
□ 2-й уровень рефералов отображается
□ Промо-ссылки: создание, статистика, QR
□ Баннеры: скачивание, HTML код
□ Запрос выплаты: все методы
□ На игровой баланс → мгновенно
□ USDT/карта → через модерацию
□ История выплат
□ Детальная статистика: источники, продукты, топ
□ Экспорт CSV/Excel
□ HTMX: обновление без перезагрузки
□ Мобильная адаптация
□ Приватность: не показывать личные данные рефералов
```

---

## ШАГ 8.6 — АДМИН УПРАВЛЕНИЕ + CELERY ЗАДАЧИ

### Задача

```
Админ-интерфейс для управления партнёрской программой.
Все Celery задачи. Настройка программы.
```

### Админ-панель партнёрской программы

```
URL: /admin/referral/
Доступ: @staff_required + permission 'manage_referral_program'

Разделы:

1. Обзор:
   - Общая статистика программы
   - Активных партнёров: N
   - Рефералов за сегодня/неделю/месяц
   - Комиссий начислено за период
   - Выплат ожидают обработки: N
   - Подозрительных партнёров: N

2. Партнёры:
   - Список всех партнёров
   - Фильтры: уровень, статус, активность
   - Детальная карточка партнёра
   - Ручное изменение уровня
   - Блокировка/разблокировка
   - История действий

3. Выплаты:
   - Очередь выплат (pending)
   - Одобрить / Отклонить
   - История выплат

4. Антифрод:
   - Приостановленные партнёры
   - Подозрительные рефералы
   - Отчёт по фроду

5. Настройки:
   - ReferralSettings (синглтон)
   - PartnerTier (уровни и проценты)
   - Баннеры (загрузка)
```

### Обработка выплат (админ)

```
URL: /admin/referral/payouts/
Доступ: @staff_required + permission 'process_partner_payouts'

  ┌──────────────────────────────────────────────────────────────┐
  │  💵 Выплаты партнёрам                                       │
  │                                                              │
  │  [Ожидают: 5] [Обработанные] [Отклонённые]                  │
  │                                                              │
  │  ┌──────────────────────────────────────────────────────┐   │
  │  │ ⏳ #1234 • partner_pro                               │   │
  │  │    Сумма: $150.00 → USDT TRC20                      │   │
  │  │    Адрес: TJxk3...7dF2                              │   │
  │  │    ─────────────────────────────────────────────── │   │
  │  │    Уровень: 🥈 Продвинутый                         │   │
  │  │    Рефералов: 35 │ Баланс до: $234.50              │   │
  │  │    Заработано всего: $1,234 │ Выведено: $890       │   │
  │  │    Подозрительность: Нет ✅                         │   │
  │  │    Запрошено: 2 часа назад                          │   │
  │  │                                                      │   │
  │  │    [✅ Одобрить]  [❌ Отклонить]                     │   │
  │  └──────────────────────────────────────────────────────┘   │
  │                                                              │
  └──────────────────────────────────────────────────────────────┘

При одобрении:
  1. Проверить баланс партнёра (ещё раз)
  2. Списать с partner_profile.balance
  3. Для USDT: создать транзакцию вывода (через wallet)
  4. Для карты: создать транзакцию через платёжную систему
  5. Обновить PartnerPayout.status = 'completed'
  6. Уведомление партнёру
  7. AdminActionLog

При отклонении:
  1. Вернуть средства на partner_profile.balance
  2. Причина обязательна
  3. Уведомление партнёру
  4. AdminActionLog
```

### Celery задачи (полный список)

```
# apps/referral/tasks.py

# ── ЕЖЕДНЕВНЫЕ ──────────────────────────────────

calculate_daily_commissions():
  """02:00 UTC. Расчёт комиссий за вчера."""
  CommissionService.calculate_daily_commissions()

daily_fraud_check():
  """03:00 UTC. Проверка на фрод."""
  AntiFraudService.daily_fraud_check()

update_referral_activity():
  """04:00 UTC. Обновить статусы активности рефералов."""
  # Кто был активен за 30 дней → is_active = True
  # Кто не был → is_active = False, status = 'churned'
  Referral.objects.filter(
    last_active_at__lt=now() - timedelta(days=30),
    is_active=True,
  ).update(is_active=False, status='churned')

  Referral.objects.filter(
    last_active_at__gte=now() - timedelta(days=30),
    is_active=False,
    status='churned',
  ).update(is_active=True, status='active')

  # Обновить active_referrals для каждого партнёра
  partners = PartnerProfile.objects.all()
  for profile in partners:
    profile.active_referrals = Referral.objects.filter(
      partner=profile.user,
      is_active=True,
      is_qualified=True,
      level=1,
    ).count()
    profile.save(update_fields=['active_referrals'])

send_daily_commission_summary():
  """06:00 UTC. Суммарное уведомление о комиссиях за день."""
  yesterday = date.today() - timedelta(days=1)
  
  partners_with_commissions = Commission.objects.filter(
    period_start=yesterday,
    net_amount__gt=0,
    status='approved',
  ).values('partner').annotate(
    total=Sum('net_amount'),
    count=Count('id'),
  )

  for pc in partners_with_commissions:
    partner = User.objects.get(id=pc['partner'])
    NotificationService.create_notification(
      user=partner,
      notification_type='referral_commission',
      title=f'💰 Комиссия за {yesterday.strftime("%d.%m")}',
      message=f'Начислено: ${pc["total"]:.2f} '
              f'от {pc["count"]} рефералов.',
      icon='💰',
      link='/partners/',
    )


# ── ЕЖЕМЕСЯЧНЫЕ ─────────────────────────────────

reset_monthly_stats():
  """1-е число, 00:01 UTC. Сброс месячных счётчиков."""
  PartnerTierService.reset_monthly_stats()

check_tier_downgrades():
  """1-е число, 00:30 UTC. Проверка понижения уровней."""
  PartnerTierService.check_downgrade()

generate_monthly_report():
  """1-е число, 01:00 UTC. Генерация месячного отчёта."""
  # Создать PDF/CSV отчёт за прошлый месяц
  # Для каждого партнёра:
  #   - Рефералов за месяц
  #   - GGR за месяц
  #   - Комиссии за месяц
  #   - Выплаты за месяц
  # Отправить на email
  pass


# ── КАЖДЫЙ ЧАС ──────────────────────────────────

check_tier_upgrades():
  """Каждый час. Проверка повышения уровней."""
  profiles = PartnerProfile.objects.filter(
    is_partner_active=True,
  ).select_related('tier', 'user')

  for profile in profiles:
    PartnerTierService.check_and_upgrade(profile.user)

update_promo_link_stats():
  """Каждый час. Обновить статистику промо-ссылок."""
  links = PromoLink.objects.filter(is_active=True)
  for link in links:
    # Пересчитать из Referral
    stats = Referral.objects.filter(
      promo_link=link,
    ).aggregate(
      regs=Count('id'),
      deps=Count('id', filter=Q(total_deposits__gt=0)),
      total_dep=Sum('total_deposits'),
      total_ggr=Sum('total_ggr'),
      total_earned=Sum('total_commission_earned'),
    )
    link.registrations = stats['regs'] or 0
    link.deposits = stats['deps'] or 0
    link.total_deposit_amount = stats['total_dep'] or 0
    link.total_ggr = stats['total_ggr'] or 0
    link.total_earned = stats['total_earned'] or 0
    if link.clicks > 0:
      link.conversion_rate = link.registrations / link.clicks * 100
    if link.registrations > 0:
      link.deposit_rate = link.deposits / link.registrations * 100
    link.save()


# ── ПРИ СОБЫТИЯХ ────────────────────────────────

update_referral_on_deposit(user_id, amount):
  """При каждом депозите реферала."""
  # Обновить Referral.total_deposits
  # Проверить first_deposit
  # Квалифицировать если нужно

update_referral_on_bet(user_id, bet_amount):
  """При каждой ставке реферала."""
  # Обновить Referral.total_bets
  # Квалифицировать если нужно

update_referral_last_activity(user_id):
  """При любой активности реферала."""
  # Обновить Referral.last_active_at
  # Обновить is_active


# ── CELERY BEAT CONFIG ───────────────────────────

CELERY_BEAT_SCHEDULE = {
  'calculate-daily-commissions': {
    'task': 'apps.referral.tasks.calculate_daily_commissions',
    'schedule': crontab(hour=2, minute=0),
  },
  'daily-fraud-check': {
    'task': 'apps.referral.tasks.daily_fraud_check',
    'schedule': crontab(hour=3, minute=0),
  },
  'update-referral-activity': {
    'task': 'apps.referral.tasks.update_referral_activity',
    'schedule': crontab(hour=4, minute=0),
  },
  'send-daily-commission-summary': {
    'task': 'apps.referral.tasks.send_daily_commission_summary',
    'schedule': crontab(hour=6, minute=0),
  },
  'reset-monthly-stats': {
    'task': 'apps.referral.tasks.reset_monthly_stats',
    'schedule': crontab(day_of_month=1, hour=0, minute=1),
  },
  'check-tier-downgrades': {
    'task': 'apps.referral.tasks.check_tier_downgrades',
    'schedule': crontab(day_of_month=1, hour=0, minute=30),
  },
  'check-tier-upgrades': {
    'task': 'apps.referral.tasks.check_tier_upgrades',
    'schedule': crontab(minute=0),  # каждый час
  },
  'update-promo-link-stats': {
    'task': 'apps.referral.tasks.update_promo_link_stats',
    'schedule': crontab(minute=15),  # каждый час в :15
  },
}
```

### Критерий готовности шага 8.6

```
□ Админ обзор: статистика программы
□ Админ: список партнёров с фильтрами
□ Админ: детальная карточка партнёра
□ Админ: ручное изменение уровня
□ Админ: блокировка/разблокировка
□ Админ: очередь выплат
□ Админ: одобрение/отклонение выплат
□ Админ: антифрод отчёт
□ Админ: настройки программы (ReferralSettings)
□ Админ: управление уровнями (PartnerTier)
□ Админ: загрузка баннеров
□ Celery: ежедневный расчёт комиссий (02:00)
□ Celery: ежедневная проверка фрода (03:00)
□ Celery: обновление активности (04:00)
□ Celery: суммарное уведомление (06:00)
□ Celery: ежемесячный сброс (1-е число)
□ Celery: проверка понижения уровней (1-е число)
□ Celery: проверка повышения (каждый час)
□ Celery: обновление статистики ссылок (каждый час)
□ Все задачи в Celery Beat
□ AdminActionLog для всех действий
```

---

## 📊 ОБЩИЙ ЧЕКЛИСТ ЭТАПА 8

```
МОДЕЛИ:
  □ PartnerTier (4 уровня + fixtures)
  □ PartnerProfile (автосоздание)
  □ Referral (1-й и 2-й уровень)
  □ Commission (все типы)
  □ PartnerPayout
  □ PromoLink + PromoLinkClick
  □ NegativeCarryover
  □ ReferralSettings (синглтон)

РЕФЕРАЛЬНАЯ МЕХАНИКА:
  □ Клик по ссылке: запись + cookie
  □ Регистрация: привязка реферала
  □ Интеграция со всеми способами регистрации
  □ 2-й уровень рефералов
  □ Квалификация рефералов
  □ Бонус за регистрацию
  □ Бонус за первый депозит

КОМИССИИ:
  □ Ежедневный расчёт GGR
  □ GGR: спорт + казино + predictions
  □ Комиссия зависит от возраста реферала
  □ Комиссия зависит от уровня партнёра
  □ Negative carryover
  □ 2-й уровень комиссий
  □ Начисление на партнёрский баланс

УРОВНИ ПАРТНЁРОВ:
  □ 4 уровня с разными условиями и %
  □ Автоматическое повышение
  □ Проверка понижения (ежемесячно)
  □ Ручное управление админом

АНТИФРОД:
  □ Self-referral блокируется
  □ Лимит рефералов с одного IP
  □ Лимит скорости регистраций
  □ Disposable email проверка
  □ Ежедневная проверка паттернов
  □ Автоматическая приостановка
  □ Ручная проверка админом

ПАРТНЁРСКАЯ ПАНЕЛЬ:
  □ Дашборд: баланс, рефералы, GGR
  □ График дохода
  □ Прогресс к следующему уровню
  □ Список рефералов (фильтры, поиск, экспорт)
  □ Промо-ссылки (создание, QR, статистика)
  □ Баннеры (скачивание, HTML код)
  □ Запрос выплаты (все методы)
  □ Детальная статистика (источники, продукты)

ВЫПЛАТЫ:
  □ На игровой баланс (мгновенно)
  □ На кошелёк DOD (мгновенно)
  □ USDT / карта (через модерацию)
  □ Админ: одобрение/отклонение

АДМИН:
  □ Обзор программы
  □ Управление партнёрами
  □ Очередь выплат
  □ Антифрод отчёт
  □ Настройки программы
  □ AdminActionLog

CELERY:
  □ Ежедневный расчёт комиссий
  □ Ежедневная проверка фрода
  □ Обновление активности рефералов
  □ Суммарные уведомления
  □ Ежемесячный сброс + проверка уровней
  □ Проверка повышения (каждый час)
  □ Обновление статистики ссылок

ИНТЕРФЕЙС:
  □ Тёмная тема DOD
  □ HTMX интерактивность
  □ Мобильная адаптация
  □ Графики (Chart.js или Lightweight Charts)
```

---

```
╔══════════════════════════════════════════════════════╗
║                                                      ║
║   ЭТАП 8 ЗАВЕРШЁН                                   ║
║                                                      ║
║   Следующий: ЭТАП 9                                 ║
║   Чат поддержки + Уведомления (расширение)          ║
║                                                      ║
║   Продолжить?                                       ║
║                                                      ║
╚══════════════════════════════════════════════════════╝
```