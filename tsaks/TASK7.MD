# 📋 ТЗ ПРОЕКТА DOD — ЭТАП 7

# PREDICTION MARKET (МАРКЕТЫ ПРЕДСКАЗАНИЙ)

```
╔══════════════════════════════════════════════════════╗
║                                                      ║
║   ПРОЕКТ:    DOD                                    ║
║   ЭТАП:      7 из 12                                ║
║   НАЗВАНИЕ:  Prediction Market                      ║
║   ЗАВИСИТ:   Этапы 1-6 (полностью завершены)        ║
║   ЦЕЛЬ:      Пользователь может покупать и          ║
║              продавать доли исходов событий,         ║
║              модератор создаёт и резолвит маркеты,  ║
║              работает AMM ценообразование,           ║
║              графики, комментарии, лидерборд        ║
║                                                      ║
╚══════════════════════════════════════════════════════╝
```

---

## 📌 КОНТЕКСТ ДЛЯ ИИ-АГЕНТА

```
Этапы 1-6 выполнены. У тебя есть:
  - Полная авторизация (email, Google, Telegram, SMS, 2FA)
  - Профиль + KYC + система уровней доверия
  - Мультивалютный кошелёк (фиат + крипто)
  - Платёжная система (NOWpayments, RUkassa)
  - Ставки на спорт (полный функционал)
  - Казино (Crash, Mines, Dice, Plinko, Roulette, Slots)
  - Уведомления, чат поддержки (будет в этапе 9)
  - Админ-панель (базовая, расширение в этапе 10)

Prediction Market — это рынок предсказаний,
где пользователи покупают/продают доли исходов
реальных событий. Аналоги: Polymarket, Kalshi,
Manifold Markets.

Принцип работы:
  - Модератор создаёт маркет: "Трамп победит в 2028?"
  - У маркета есть исходы: YES / NO (или несколько)
  - Каждый исход имеет цену от $0.01 до $0.99
  - Цена отражает вероятность: $0.65 = 65% вероятность
  - Пользователи покупают доли (shares)
  - Когда событие случается → модератор резолвит
  - Выигрышные доли платят $1.00 за штуку
  - Проигрышные доли платят $0.00

Ценообразование: AMM (Automated Market Maker)
  На старте — CPMM (Constant Product Market Maker)
  Платформа выступает маркет-мейкером
  Формула: x * y = k (как Uniswap)

Этот этап включает 6 шагов.
Каждый шаг — отдельная задача.
Выполняй строго по порядку.
```

---

## ШАГ 7.1 — ПРИЛОЖЕНИЕ И МОДЕЛИ

### Задача

```
Создай приложение predictions с полной структурой
моделей: маркеты, исходы, доли, сделки, комментарии,
категории. Подготовь AMM логику.
```

### Структура приложения

```
apps/predictions/
├── __init__.py
├── models.py
├── managers.py
├── admin.py
├── views.py
├── urls.py
├── forms.py
├── signals.py
├── tasks.py                # Celery задачи
├── middleware.py
├── validators.py
├── services/
│   ├── __init__.py
│   ├── market_service.py   # Создание, управление маркетами
│   ├── trading_service.py  # Покупка/продажа долей (AMM)
│   ├── resolution_service.py  # Резолвинг маркетов
│   └── analytics_service.py   # Статистика, лидерборд
├── templatetags/
│   ├── __init__.py
│   └── prediction_tags.py
├── tests/
│   ├── __init__.py
│   ├── test_models.py
│   ├── test_trading.py
│   ├── test_resolution.py
│   └── test_views.py
├── templates/
│   └── predictions/
│       └── (шаблоны — шаг 7.5)
└── migrations/
    └── __init__.py
```

### Модель Category

```
class Category(models.Model):

    Назначение:
      Категории маркетов для группировки и фильтрации.
      Примеры: Политика, Спорт, Крипто, Технологии, 
      Развлечения, Наука, Экономика.

    Поля:
    ─────
    id:
      тип: UUID, primary key

    name:
      тип: CharField, max 100
      Название на основном языке (ru)
      Пример: "Политика"

    name_en:
      тип: CharField, max 100, blank=True
      Название на английском
      Пример: "Politics"

    slug:
      тип: SlugField, уникальный
      URL-friendly имя
      Пример: "politics"

    icon:
      тип: CharField, max 10
      Эмодзи иконка
      Пример: "🏛️"

    description:
      тип: TextField, blank=True
      Описание категории

    color:
      тип: CharField, max 7
      HEX цвет для UI
      Пример: "#3b82f6"

    sort_order:
      тип: IntegerField, default=0
      Порядок отображения (меньше → выше)

    is_active:
      тип: BooleanField, default=True

    # Статистика (кэшированная)
    markets_count:
      тип: IntegerField, default=0
      Количество активных маркетов

    total_volume:
      тип: DecimalField(18, 2), default=0
      Общий объём торгов в категории (USD)

    created_at:
      тип: DateTimeField, auto_now_add=True

    Meta:
      verbose_name = 'Категория предсказаний'
      verbose_name_plural = 'Категории предсказаний'
      ordering = ['sort_order', 'name']

    Предзаполнение (fixtures):
      🏛️ Политика (politics)
      ⚽ Спорт (sports)
      💰 Крипто и финансы (crypto-finance)
      💻 Технологии (technology)
      🎬 Развлечения (entertainment)
      🔬 Наука (science)
      📈 Экономика (economy)
      🌍 Мир (world-events)
      🎮 Игры и киберспорт (gaming)
      ⚖️ Другое (other)
```

### Модель Market

```
class Market(models.Model):

    Назначение:
      Основная модель маркета предсказаний.
      Представляет вопрос/событие для предсказаний.
      Пример: "Кто станет президентом США в 2028?"

    Поля:
    ─────
    id:
      тип: UUID, primary key

    # Основная информация
    title:
      тип: CharField, max 300
      Заголовок маркета
      Пример: "Трамп победит на выборах 2028?"

    title_en:
      тип: CharField, max 300, blank=True
      Заголовок на английском

    slug:
      тип: SlugField, max 350, уникальный
      Генерируется из title

    description:
      тип: TextField
      Подробное описание: что именно спрашивается,
      какие условия, как определяется результат.
      Поддержка Markdown.

    description_en:
      тип: TextField, blank=True
      Описание на английском

    category:
      тип: ForeignKey → Category
      on_delete: PROTECT
      related_name: 'markets'

    tags:
      тип: JSONField, default=list
      Теги для поиска
      Пример: ["трамп", "выборы", "сша", "2028"]

    # Изображение
    image:
      тип: ImageField, nullable
      upload_to: 'predictions/markets/'
      Обложка маркета (16:9)
      Ресайз при загрузке: 800×450

    image_thumbnail:
      тип: ImageField, nullable
      upload_to: 'predictions/markets/thumbnails/'
      400×225 для карточек

    # Тип маркета
    market_type:
      тип: CharField
      choices:
        ('binary', 'Бинарный (YES/NO)')
        ('multiple', 'Множественный выбор')
      default: 'binary'

    # Временные рамки
    created_at:
      тип: DateTimeField, auto_now_add=True

    updated_at:
      тип: DateTimeField, auto_now=True

    opens_at:
      тип: DateTimeField
      Когда маркет открывается для торгов
      По умолчанию: сразу при создании

    closes_at:
      тип: DateTimeField
      Дедлайн: после этого нельзя торговать
      Пример: дата выборов

    resolved_at:
      тип: DateTimeField, nullable
      Когда маркет был резолвлен

    # Статус
    status:
      тип: CharField
      choices:
        ('draft', 'Черновик')
        ('pending', 'На модерации')
        ('active', 'Активный')
        ('closed', 'Торги закрыты')
        ('resolved', 'Разрешён')
        ('cancelled', 'Отменён')
        ('disputed', 'Оспаривается')
      default: 'draft'

    # Результат
    resolution_source:
      тип: TextField, blank=True
      Источник определения результата
      Пример: "Официальные результаты выборов,
      объявленные ЦИК до 15 ноября 2028"

    resolution_details:
      тип: TextField, blank=True
      Подробности резолюции (заполняет модератор)

    # Финансы
    initial_liquidity:
      тип: DecimalField(18, 2), default=1000
      Начальная ликвидность (в USD)
      Определяет глубину рынка и волатильность
      Чем больше → цена меньше двигается от покупок

    total_volume:
      тип: DecimalField(18, 2), default=0
      Общий объём торгов (USD)

    total_traders:
      тип: IntegerField, default=0
      Количество уникальных трейдеров

    total_shares:
      тип: IntegerField, default=0
      Общее количество проданных долей

    # Комиссия
    fee_percent:
      тип: DecimalField(5, 2), default=2.00
      Комиссия платформы при покупке (%)
      По умолчанию: 2%

    # Создатель и модерация
    created_by:
      тип: ForeignKey → User
      on_delete: SET_NULL, nullable
      Модератор который создал

    resolved_by:
      тип: ForeignKey → User
      on_delete: SET_NULL, nullable
      Модератор который резолвил

    # Видимость
    is_featured:
      тип: BooleanField, default=False
      Показывать в "Рекомендуемых" на главной

    is_hot:
      тип: BooleanField, default=False
      Горячий маркет (большой объём или тренд)
      Обновляется автоматически через Celery

    views_count:
      тип: IntegerField, default=0
      Количество просмотров

    # Комментарии
    comments_enabled:
      тип: BooleanField, default=True
      Разрешить комментарии

    comments_count:
      тип: IntegerField, default=0
      Количество комментариев (кэш)

    Meta:
      verbose_name = 'Маркет предсказаний'
      verbose_name_plural = 'Маркеты предсказаний'
      ordering = ['-created_at']
      indexes:
        - status + created_at
        - status + closes_at
        - category + status
        - is_featured + status
        - is_hot + status
        - total_volume (для сортировки по популярности)
        - slug

    Методы:
    ───────
    __str__():
      return self.title

    is_open():
      return (
        self.status == 'active'
        and self.opens_at <= now()
        and self.closes_at > now()
      )

    is_trading_allowed():
      return self.is_open()

    time_until_close():
      если closes_at > now(): return closes_at - now()
      иначе: return None

    get_outcomes_with_prices():
      Вернуть все исходы с текущими ценами.
      Кешировать в Redis на 5 секунд.

    get_price_history(outcome_id, period='24h'):
      Вернуть историю цен исхода за период.
```

### Модель Outcome

```
class Outcome(models.Model):

    Назначение:
      Исход маркета. Для бинарного — два исхода
      (YES, NO). Для множественного — несколько.

    Поля:
    ─────
    id:
      тип: UUID, primary key

    market:
      тип: ForeignKey → Market
      on_delete: CASCADE
      related_name: 'outcomes'

    title:
      тип: CharField, max 200
      Название исхода
      Пример: "Да" / "Нет" или "Трамп" / "Байден" / "Другой"

    title_en:
      тип: CharField, max 200, blank=True

    slug:
      тип: SlugField

    # Порядок отображения
    sort_order:
      тип: IntegerField, default=0
      Для бинарных: YES=0, NO=1

    # AMM Pool
    pool_shares:
      тип: DecimalField(18, 8), default=0
      Количество долей в пуле AMM
      Начальное значение = initial_liquidity / initial_price

    # Текущая цена
    current_price:
      тип: DecimalField(10, 4), default=0.5000
      Текущая цена одной доли ($0.01 — $0.99)
      Для бинарного: YES + NO = ~$1.00

    # Результат
    is_winner:
      тип: BooleanField, nullable
      null = ещё не резолвлен
      True = этот исход выиграл
      False = этот исход проиграл

    # Статистика
    total_shares_sold:
      тип: DecimalField(18, 8), default=0
      Всего продано долей

    total_volume:
      тип: DecimalField(18, 2), default=0
      Объём торгов по этому исходу (USD)

    holders_count:
      тип: IntegerField, default=0
      Количество держателей долей

    created_at:
      тип: DateTimeField, auto_now_add=True

    Meta:
      verbose_name = 'Исход'
      verbose_name_plural = 'Исходы'
      ordering = ['sort_order']
      unique_together = ['market', 'slug']

    Методы:
      implied_probability():
        """Подразумеваемая вероятность в %."""
        return round(self.current_price * 100, 1)

      payout_per_share():
        """Выплата за долю при выигрыше."""
        return Decimal('1.00')  # Всегда $1.00

      potential_profit(buy_price):
        """Потенциальная прибыль."""
        return self.payout_per_share() - buy_price
```

### Модель AMM Pool (Automated Market Maker)

```
class AMMPool(models.Model):

    Назначение:
      Пул ликвидности для AMM.
      Один пул на один маркет.
      Использует формулу CPMM: ∏(q_i) = k
      Где q_i — количество долей исхода i в пуле,
      k — константа.

    Поля:
    ─────
    id:
      тип: UUID, primary key

    market:
      тип: OneToOneField → Market
      on_delete: CASCADE
      related_name: 'amm_pool'

    # Состояние пула
    liquidity:
      тип: DecimalField(18, 8)
      Текущая ликвидность пула (в USD)

    constant_product:
      тип: DecimalField(30, 8)
      Константа k в формуле AMM
      Устанавливается при инициализации:
      k = q_yes * q_no (для бинарного)

    # Для бинарного маркета
    # (для множественного — pool_shares в каждом Outcome)
    pool_yes:
      тип: DecimalField(18, 8), default=0
      Количество YES долей в пуле

    pool_no:
      тип: DecimalField(18, 8), default=0
      Количество NO долей в пуле

    # Общие
    total_fees_collected:
      тип: DecimalField(18, 2), default=0
      Всего комиссий собрано (USD)

    last_trade_at:
      тип: DateTimeField, nullable

    created_at:
      тип: DateTimeField, auto_now_add=True

    updated_at:
      тип: DateTimeField, auto_now=True

    Meta:
      verbose_name = 'AMM Пул'

    Методы:

      get_price_yes():
        """Текущая цена YES доли."""
        total = self.pool_yes + self.pool_no
        if total == 0:
          return Decimal('0.5')
        return self.pool_no / total

      get_price_no():
        """Текущая цена NO доли."""
        return 1 - self.get_price_yes()

      calculate_buy_cost(outcome, shares_amount):
        """
        Рассчитать стоимость покупки N долей.
        CPMM формула:
          cost = pool_opposite - (k / (pool_target + shares_amount))
        """
        ...описано в TradingService

      calculate_sell_return(outcome, shares_amount):
        """
        Рассчитать возврат при продаже N долей.
        Обратная формула.
        """
        ...описано в TradingService

    Инициализация пула:
      При создании маркета:
        liquidity = market.initial_liquidity
        Для бинарного (50/50):
          pool_yes = liquidity
          pool_no = liquidity
          constant_product = pool_yes * pool_no
        Для множественного (равные вероятности):
          Каждый outcome.pool_shares = liquidity
          constant_product = ∏(pool_shares)
```

### Модель UserPosition (Позиция пользователя)

```
class UserPosition(models.Model):

    Назначение:
      Текущая позиция пользователя в маркете.
      Сколько долей каждого исхода держит.

    Поля:
    ─────
    id:
      тип: UUID, primary key

    user:
      тип: ForeignKey → User
      on_delete: CASCADE
      related_name: 'prediction_positions'

    market:
      тип: ForeignKey → Market
      on_delete: CASCADE

    outcome:
      тип: ForeignKey → Outcome
      on_delete: CASCADE

    # Количество долей
    shares:
      тип: DecimalField(18, 8), default=0
      Текущее количество долей
      Может быть дробным (0.5 доли)

    # Средняя цена покупки
    avg_buy_price:
      тип: DecimalField(10, 4), default=0
      Средняя цена по которой покупал
      Для расчёта P&L

    # Инвестировано
    total_invested:
      тип: DecimalField(18, 2), default=0
      Всего потрачено (USD) включая комиссии

    total_fees_paid:
      тип: DecimalField(18, 2), default=0
      Всего комиссий уплачено

    # P&L
    realized_pnl:
      тип: DecimalField(18, 2), default=0
      Реализованная прибыль/убыток (от продаж)

    # Статусы
    is_settled:
      тип: BooleanField, default=False
      True когда маркет резолвлен и
      выплата произведена

    settlement_amount:
      тип: DecimalField(18, 2), default=0
      Сумма выплаты при резолюции

    created_at:
      тип: DateTimeField, auto_now_add=True

    updated_at:
      тип: DateTimeField, auto_now=True

    Meta:
      verbose_name = 'Позиция пользователя'
      unique_together = ['user', 'outcome']
      indexes:
        - user + market
        - user + is_settled
        - market + outcome

    Методы:
      current_value():
        """Текущая стоимость позиции."""
        return self.shares * self.outcome.current_price

      unrealized_pnl():
        """Нереализованная прибыль/убыток."""
        return self.current_value() - self.total_invested

      unrealized_pnl_percent():
        """Нереализованная P&L в %."""
        if self.total_invested == 0:
          return 0
        return (self.unrealized_pnl() / self.total_invested) * 100

      potential_payout():
        """Потенциальная выплата если исход выиграет."""
        return self.shares * Decimal('1.00')  # $1 за долю
```

### Модель Trade (Сделка)

```
class Trade(models.Model):

    Назначение:
      Запись каждой сделки (покупка/продажа долей).
      Для истории, аналитики и графиков.

    Поля:
    ─────
    id:
      тип: UUID, primary key

    user:
      тип: ForeignKey → User
      on_delete: CASCADE
      related_name: 'prediction_trades'

    market:
      тип: ForeignKey → Market
      on_delete: CASCADE

    outcome:
      тип: ForeignKey → Outcome
      on_delete: CASCADE

    # Тип сделки
    trade_type:
      тип: CharField
      choices:
        ('buy', 'Покупка')
        ('sell', 'Продажа')

    # Количество
    shares:
      тип: DecimalField(18, 8)
      Количество купленных/проданных долей

    # Цены
    price_per_share:
      тип: DecimalField(10, 4)
      Средняя цена за долю в этой сделке
      (AMM цена двигается по мере покупки)

    total_cost:
      тип: DecimalField(18, 2)
      Общая стоимость сделки (без комиссии)
      = shares * price_per_share (примерно, AMM точнее)

    fee_amount:
      тип: DecimalField(18, 2)
      Комиссия платформы

    total_amount:
      тип: DecimalField(18, 2)
      Итого списано/зачислено
      Покупка: total_cost + fee_amount
      Продажа: total_cost - fee_amount

    # Состояние пула после сделки
    price_before:
      тип: DecimalField(10, 4)
      Цена исхода ДО сделки

    price_after:
      тип: DecimalField(10, 4)
      Цена исхода ПОСЛЕ сделки

    # Мета
    ip_address:
      тип: GenericIPAddressField, nullable

    created_at:
      тип: DateTimeField, auto_now_add=True

    Meta:
      verbose_name = 'Сделка'
      verbose_name_plural = 'Сделки'
      ordering = ['-created_at']
      indexes:
        - user + created_at
        - market + created_at
        - outcome + created_at
        - market + outcome + created_at (для графика цен)
```

### Модель PriceHistory (для графиков)

```
class PriceHistory(models.Model):

    Назначение:
      Снимки цен с интервалом для построения графиков.
      Не каждая сделка, а периодические снимки.

    Поля:
    ─────
    id:
      тип: BigAutoField (не UUID, для скорости)

    outcome:
      тип: ForeignKey → Outcome
      on_delete: CASCADE
      related_name: 'price_history'

    price:
      тип: DecimalField(10, 4)

    volume:
      тип: DecimalField(18, 2), default=0
      Объём торгов за период

    trades_count:
      тип: IntegerField, default=0
      Количество сделок за период

    timestamp:
      тип: DateTimeField

    # Период снимка
    interval:
      тип: CharField
      choices:
        ('1m', '1 минута')
        ('5m', '5 минут')
        ('1h', '1 час')
        ('1d', '1 день')

    Meta:
      verbose_name = 'История цены'
      ordering = ['-timestamp']
      indexes:
        - outcome + interval + timestamp
      unique_together = ['outcome', 'interval', 'timestamp']

Заполнение:
  Celery задача каждую минуту:
    Для каждого активного маркета:
      Для каждого исхода:
        Создать PriceHistory(interval='1m')

  Celery задача каждые 5 минут:
    Агрегировать 1m → 5m

  Celery задача каждый час:
    Агрегировать 5m → 1h

  Celery задача ежедневно:
    Агрегировать 1h → 1d

  Хранение:
    1m — 7 дней
    5m — 30 дней
    1h — 1 год
    1d — навсегда
```

### Модель Comment

```
class Comment(models.Model):

    Назначение:
      Комментарии под маркетами.
      Дискуссия о вероятности исхода.

    Поля:
    ─────
    id:
      тип: UUID, primary key

    market:
      тип: ForeignKey → Market
      on_delete: CASCADE
      related_name: 'comments'

    user:
      тип: ForeignKey → User
      on_delete: CASCADE

    parent:
      тип: ForeignKey → self (Comment)
      on_delete: CASCADE
      nullable
      related_name: 'replies'
      Для вложенных ответов (1 уровень)

    text:
      тип: TextField, max 2000
      Текст комментария
      Markdown НЕ поддерживается (безопасность)
      HTML экранируется

    # Позиция автора на момент комментария
    user_position:
      тип: CharField, max 50, blank=True
      Пример: "YES: 150 долей" или "Нет позиции"
      Показывает что автор "шкурно" заинтересован

    # Модерация
    is_hidden:
      тип: BooleanField, default=False
      Скрыт модератором

    hidden_reason:
      тип: CharField, max 200, blank=True

    hidden_by:
      тип: ForeignKey → User, nullable

    # Лайки
    likes_count:
      тип: IntegerField, default=0

    # Флаги
    is_pinned:
      тип: BooleanField, default=False
      Закреплён модератором

    is_edited:
      тип: BooleanField, default=False

    edited_at:
      тип: DateTimeField, nullable

    created_at:
      тип: DateTimeField, auto_now_add=True

    Meta:
      verbose_name = 'Комментарий'
      ordering = ['-is_pinned', '-created_at']
      indexes:
        - market + created_at
        - user + created_at


class CommentLike(models.Model):

    Назначение:
      Лайки комментариев (уникальные).

    Поля:
      user: ForeignKey → User
      comment: ForeignKey → Comment

    Meta:
      unique_together = ['user', 'comment']
```

### Модель MarketActivity (Лента активности)

```
class MarketActivity(models.Model):

    Назначение:
      Лента событий маркета для отображения
      в боковой панели: кто что купил/продал.

    Поля:
    ─────
    id:
      тип: UUID, primary key

    market:
      тип: ForeignKey → Market
      on_delete: CASCADE
      related_name: 'activities'

    user:
      тип: ForeignKey → User
      on_delete: CASCADE

    activity_type:
      тип: CharField
      choices:
        ('buy', 'Купил')
        ('sell', 'Продал')
        ('comment', 'Комментарий')

    description:
      тип: CharField, max 200
      Пример: "купил 50 YES долей за $32.50"

    # Ссылка на объект
    trade:
      тип: ForeignKey → Trade, nullable
    comment:
      тип: ForeignKey → Comment, nullable

    created_at:
      тип: DateTimeField, auto_now_add=True

    Meta:
      ordering = ['-created_at']
      indexes:
        - market + created_at
```

### Критерий готовности шага 7.1

```
□ Приложение predictions создано
□ Модель Category: создана + fixtures (10 категорий)
□ Модель Market: все поля
□ Модель Outcome: все поля
□ Модель AMMPool: все поля + методы расчёта цены
□ Модель UserPosition: все поля
□ Модель Trade: все поля
□ Модель PriceHistory: все поля
□ Модель Comment + CommentLike
□ Модель MarketActivity
□ Все миграции применены
□ Django Admin: все модели зарегистрированы
□ Индексы для быстрых запросов
□ Fixtures с категориями загружены
```

---

## ШАГ 7.2 — СОЗДАНИЕ И УПРАВЛЕНИЕ МАРКЕТАМИ (МОДЕРАТОР)

### Задача

```
Создай интерфейс создания маркетов для модераторов.
Черновики, публикация, редактирование.
Настройка ликвидности и комиссий.
```

### Кто может создавать маркеты

```
На старте:
  - Суперадмин (любые)
  - Модератор с permission 'can_create_market'
  - Обычные пользователи НЕ могут (будет позже)

В будущем (не в этом этапе):
  - Пользователи смогут предлагать маркеты
  - Модератор одобряет или отклоняет
```

### Страница создания маркета

```
URL: /admin/predictions/create/
Доступ: @staff_required + permission 'can_create_market'

Форма:

  ┌──────────────────────────────────────────────────────┐
  │  ➕ Создать маркет предсказаний                     │
  │                                                      │
  │  ── Основное ────────────────────────────────────── │
  │                                                      │
  │  Заголовок (RU) *                                   │
  │  ┌────────────────────────────────────────────────┐ │
  │  │ Трамп победит на выборах 2028?                 │ │
  │  └────────────────────────────────────────────────┘ │
  │  ℹ️ Формулируйте как вопрос. Чётко и однозначно.  │
  │                                                      │
  │  Заголовок (EN)                                     │
  │  ┌────────────────────────────────────────────────┐ │
  │  │ Will Trump win 2028 election?                  │ │
  │  └────────────────────────────────────────────────┘ │
  │                                                      │
  │  Описание (RU) *                                    │
  │  ┌────────────────────────────────────────────────┐ │
  │  │ Этот маркет разрешится как YES если           │ │
  │  │ Дональд Трамп официально будет объявлен       │ │
  │  │ победителем президентских выборов США 2028    │ │
  │  │ года. Источник: Associated Press.             │ │
  │  └────────────────────────────────────────────────┘ │
  │  Поддержка Markdown. Укажите точные критерии       │
  │  разрешения маркета.                                │
  │                                                      │
  │  Описание (EN)                                      │
  │  ┌────────────────────────────────────────────────┐ │
  │  │ ...                                            │ │
  │  └────────────────────────────────────────────────┘ │
  │                                                      │
  │  Категория *                                        │
  │  ┌────────────────────────────────────────────────┐ │
  │  │ 🏛️ Политика                                 ▼ │ │
  │  └────────────────────────────────────────────────┘ │
  │                                                      │
  │  Теги                                               │
  │  ┌────────────────────────────────────────────────┐ │
  │  │ [трамп ×] [выборы ×] [сша ×] [добавить +]    │ │
  │  └────────────────────────────────────────────────┘ │
  │                                                      │
  │  Обложка                                            │
  │  ┌────────────────────────────────────────────────┐ │
  │  │        📤 Загрузить изображение                │ │
  │  │        800×450, до 5 МБ                        │ │
  │  └────────────────────────────────────────────────┘ │
  │                                                      │
  │  ── Тип маркета ─────────────────────────────────── │
  │                                                      │
  │  ○ Бинарный (YES / NO) — рекомендуется              │
  │  ○ Множественный выбор                              │
  │                                                      │
  │  (Если множественный):                              │
  │  Исходы:                                            │
  │  ┌────────────────────────────────────────────────┐ │
  │  │ 1. [Трамп                         ] [🗑️]     │ │
  │  │ 2. [Десантис                      ] [🗑️]     │ │
  │  │ 3. [Байден                        ] [🗑️]     │ │
  │  │ 4. [Другой кандидат               ] [🗑️]     │ │
  │  │ [+ Добавить исход]                            │ │
  │  └────────────────────────────────────────────────┘ │
  │  Минимум: 2 исхода. Максимум: 20.                  │
  │  ⚠️ Один из исходов ДОЛЖЕН быть "Другое"          │
  │  для покрытия всех вариантов.                       │
  │                                                      │
  │  ── Временные рамки ─────────────────────────────── │
  │                                                      │
  │  Открытие торгов *                                  │
  │  ┌────────────────────────────────────────────────┐ │
  │  │ 📅 Сейчас  /  Выбрать дату: ___________      │ │
  │  └────────────────────────────────────────────────┘ │
  │                                                      │
  │  Дедлайн (закрытие торгов) *                        │
  │  ┌────────────────────────────────────────────────┐ │
  │  │ 📅 05.11.2028  ⏰ 00:00 UTC                   │ │
  │  └────────────────────────────────────────────────┘ │
  │  ℹ️ После дедлайна покупка/продажа невозможна.     │
  │  Маркет ожидает резолюции.                          │
  │                                                      │
  │  Источник резолюции *                               │
  │  ┌────────────────────────────────────────────────┐ │
  │  │ Официальные результаты, объявленные            │ │
  │  │ Associated Press или Reuters.                  │ │
  │  └────────────────────────────────────────────────┘ │
  │                                                      │
  │  ── Финансовые настройки ────────────────────────── │
  │                                                      │
  │  Начальная ликвидность (USD) *                      │
  │  ┌────────────────────────────────────────────────┐ │
  │  │ 1000                                           │ │
  │  └────────────────────────────────────────────────┘ │
  │  ℹ️ Определяет глубину рынка. Больше ликвидность   │
  │  → меньше проскальзывание (slippage).              │
  │  Рекомендуется: $500-$5000.                         │
  │  ⚠️ Эти средства замораживаются как маркет-        │
  │  мейкерская ликвидность.                            │
  │                                                      │
  │  Начальные вероятности                              │
  │  (для бинарного):                                   │
  │  YES: [━━━━━━━●━━━] 50%                            │
  │  NO:  [━━━━━━━●━━━] 50%                            │
  │  Сумма всегда = 100%                                │
  │                                                      │
  │  (для множественного):                              │
  │  Трамп:    [━━━━●━━━━━] 40%                        │
  │  Десантис: [━━●━━━━━━━] 25%                        │
  │  Байден:   [━━●━━━━━━━] 20%                        │
  │  Другой:   [━●━━━━━━━━] 15%                        │
  │  Сумма: 100% ✅                                     │
  │                                                      │
  │  Комиссия платформы (%)                             │
  │  ┌────────────────────────────────────────────────┐ │
  │  │ 2.00                                           │ │
  │  └────────────────────────────────────────────────┘ │
  │  По умолчанию: 2%. Диапазон: 0%-10%.               │
  │                                                      │
  │  ── Настройки ───────────────────────────────────── │
  │                                                      │
  │  ☑ Разрешить комментарии                            │
  │  ☐ Рекомендуемый маркет (показать на главной)       │
  │                                                      │
  │  ── Действия ────────────────────────────────────── │
  │                                                      │
  │  [💾 Сохранить черновик]                            │
  │  [👁️ Предпросмотр]                                 │
  │  [🚀 Опубликовать]                                  │
  │                                                      │
  └──────────────────────────────────────────────────────┘

Валидация:
  - Заголовок: 10-300 символов
  - Описание: 50-10000 символов
  - Категория: обязательна
  - Дедлайн: в будущем (минимум через 1 час)
  - Ликвидность: $100 — $100,000
  - Комиссия: 0% — 10%
  - Для множественного: сумма вероятностей = 100%
  - Минимум 2 исхода, максимум 20
  - Источник резолюции: обязателен, минимум 20 символов
```

### Логика создания маркета (MarketService)

```
MarketService:

  create_market(data, creator):
    """Создание нового маркета."""

    1. Валидация данных (описано выше)

    2. Создать Market:
       - status = 'draft' если "Сохранить черновик"
       - status = 'active' если "Опубликовать"
       - created_by = creator
       - Сгенерировать slug из title

    3. Создать Outcomes:
       Для бинарного:
         - Outcome(title="Да", slug="yes", sort_order=0)
         - Outcome(title="Нет", slug="no", sort_order=1)
       Для множественного:
         - По одному Outcome для каждого введённого варианта

    4. Инициализировать AMM Pool:
       init_amm_pool(market, initial_liquidity, initial_probabilities)

    5. Установить начальные цены исходов:
       Для бинарного 50/50:
         outcome_yes.current_price = 0.50
         outcome_no.current_price = 0.50

    6. Записать первую точку PriceHistory

    7. Если опубликован:
       - Обновить Category.markets_count
       - Создать уведомление для подписчиков (будущее)

    8. Записать AdminActionLog

    return market


  init_amm_pool(market, liquidity, probabilities):
    """
    Инициализация AMM пула.

    Для бинарного маркета (50/50):
      pool_yes = liquidity  (= 1000)
      pool_no = liquidity   (= 1000)
      k = pool_yes * pool_no = 1,000,000

      Цена YES = pool_no / (pool_yes + pool_no) = 0.50
      Цена NO  = pool_yes / (pool_yes + pool_no) = 0.50

    Для бинарного маркета (70/30):
      Нужно подобрать pool_yes и pool_no так что:
        pool_no / (pool_yes + pool_no) = 0.70  (цена YES)
        pool_yes * pool_no = k
      
      pool_yes = liquidity * (1 - p_yes) / p_yes * adjustment
      pool_no = liquidity * p_yes / (1 - p_yes) * adjustment
      
      Проще: задать через соотношение.
      Если p_yes = 0.70:
        pool_yes = liquidity * 0.30 / 0.70 ≈ 428.57
        pool_no = liquidity * 0.70 / 0.30 ≈ 2333.33
        Нормализовать чтобы геометрическое среднее = liquidity:
        pool_yes = liquidity / p_yes^0.5 * (1-p_yes)^0.5
        Или проще:
        pool_yes = liquidity * sqrt((1-p) / p)
        pool_no = liquidity * sqrt(p / (1-p))
    """

    if market.market_type == 'binary':
      outcomes = market.outcomes.order_by('sort_order')
      p_yes = probabilities[0]  # 0.50 по умолчанию
      p_no = 1 - p_yes

      # Формула LMSR-подобная для начальной установки
      import math
      pool_yes = liquidity * math.sqrt(p_no / p_yes)
      pool_no = liquidity * math.sqrt(p_yes / p_no)

      pool = AMMPool.objects.create(
        market=market,
        liquidity=liquidity,
        pool_yes=Decimal(str(pool_yes)),
        pool_no=Decimal(str(pool_no)),
        constant_product=Decimal(str(pool_yes * pool_no)),
      )

      outcomes[0].current_price = Decimal(str(p_yes))
      outcomes[0].pool_shares = Decimal(str(pool_yes))
      outcomes[0].save()

      outcomes[1].current_price = Decimal(str(p_no))
      outcomes[1].pool_shares = Decimal(str(pool_no))
      outcomes[1].save()

    else:  # multiple
      # Для множественного: каждый исход имеет свой pool
      # Используем CPMM с несколькими токенами
      for i, outcome in enumerate(market.outcomes.order_by('sort_order')):
        p = probabilities[i]
        outcome.current_price = Decimal(str(p))
        outcome.pool_shares = liquidity / Decimal(str(p))
        outcome.save()

      pool = AMMPool.objects.create(
        market=market,
        liquidity=liquidity,
        constant_product=... (произведение всех pool_shares),
      )

    return pool
```

### Управление маркетами (список)

```
URL: /admin/predictions/
Доступ: @staff_required

  ┌──────────────────────────────────────────────────┐
  │  📊 Управление маркетами                        │
  │                                                  │
  │  [➕ Создать маркет]                             │
  │                                                  │
  │  Фильтры:                                       │
  │  [Все|Черновики|Активные|Закрытые|Резолвленные|Отм.]│
  │  Категория: [Все ▼]                              │
  │  Поиск: [________________________] 🔍            │
  │                                                  │
  │  ── Статистика ─────────────────────────────── │
  │  📊 Активных: 45  │ ⏳ Ожидают резолюции: 8    │
  │  💰 Общий объём: $123,456  │ 👥 Трейдеров: 2.3k│
  │                                                  │
  │  ── Маркеты ─────────────────────────────────── │
  │                                                  │
  │  ┌──────────────────────────────────────────┐   │
  │  │ 🟢 Трамп победит на выборах 2028?       │   │
  │  │    🏛️ Политика │ Объём: $12,345         │   │
  │  │    YES: 65¢ │ NO: 35¢                   │   │
  │  │    Дедлайн: 05.11.2028 │ 👥 234 трейдера│   │
  │  │    [Редактировать] [Закрыть] [Резолвить] │   │
  │  └──────────────────────────────────────────┘   │
  │                                                  │
  │  ┌──────────────────────────────────────────┐   │
  │  │ ⏳ BTC выше $100k до конца 2025?        │   │
  │  │    💰 Крипто │ Объём: $45,678            │   │
  │  │    YES: 72¢ │ NO: 28¢                   │   │
  │  │    Дедлайн: 31.12.2025 │ ТОРГИ ЗАКРЫТЫ  │   │
  │  │    [Резолвить →]                         │   │
  │  └──────────────────────────────────────────┘   │
  │                                                  │
  └──────────────────────────────────────────────────┘

Действия модератора:
  - Редактировать: описание, теги, обложку, дедлайн
    (Нельзя: тип маркета, исходы если есть сделки)
  - Закрыть торги досрочно (с причиной)
  - Отменить маркет (с причиной, возврат средств)
  - Резолвить (следующий шаг)
  - Пометить как Featured / Hot
```

### Критерий готовности шага 7.2

```
□ Форма создания маркета: все поля
□ Бинарный маркет (YES/NO) создаётся
□ Множественный маркет создаётся
□ Начальные вероятности настраиваются
□ AMM пул инициализируется правильно
□ Начальные цены соответствуют заданным вероятностям
□ Черновик/публикация работает
□ Предпросмотр маркета
□ Список маркетов с фильтрами и поиском
□ Редактирование (с ограничениями)
□ Досрочное закрытие торгов
□ Отмена маркета с возвратом средств
□ Изображение: загрузка + ресайз + thumbnail
□ AdminActionLog записывается
□ Валидация всех полей
□ Мобильная адаптация
```

---

## ШАГ 7.3 — ТОРГОВАЯ СИСТЕМА (AMM)

### Задача

```
Реализуй покупку и продажу долей через AMM.
CPMM ценообразование. Расчёт slippage.
Обновление цен. Списание/зачисление средств.
```

### TradingService

```
TradingService:

  buy_shares(user, outcome, amount_usd):
    """
    Покупка долей исхода за USD.
    
    Параметры:
      user — покупатель
      outcome — какой исход покупаем
      amount_usd — сколько USD готов потратить
    
    Возвращает:
      (trade, error) — сделка или ошибка
    """

    market = outcome.market
    pool = market.amm_pool

    # 1. ПРОВЕРКИ
    if not market.is_trading_allowed():
      return None, 'Маркет закрыт для торгов'

    if amount_usd < Decimal('0.10'):
      return None, 'Минимальная сумма: $0.10'

    if amount_usd > Decimal('10000'):
      return None, 'Максимальная сумма: $10,000'

    # Проверить баланс пользователя
    # (используем wallet из этапа 3)
    wallet = user.wallet
    if wallet.get_balance_usd() < amount_usd:
      return None, 'Недостаточно средств'

    # Проверить лимит ставки (trust level)
    limits = TrustLevelService.get_limits(user)
    if amount_usd > limits['max_bet_amount']:
      return None, f'Лимит ставки: ${limits["max_bet_amount"]}'

    # 2. РАСЧЁТ AMM
    fee = amount_usd * (market.fee_percent / 100)
    amount_after_fee = amount_usd - fee

    # Рассчитать сколько долей получит пользователь
    shares_received = calculate_shares_for_amount(
      pool, outcome, amount_after_fee
    )

    if shares_received <= 0:
      return None, 'Слишком маленькая сумма'

    # Цена до сделки
    price_before = outcome.current_price

    # Рассчитать среднюю цену за долю
    avg_price = amount_after_fee / shares_received

    # Рассчитать slippage (проскальзывание)
    slippage = ((avg_price - price_before) / price_before) * 100
    if slippage > Decimal('20'):
      return None, f'Слишком большое проскальзывание: {slippage:.1f}%'

    # 3. АТОМАРНАЯ ТРАНЗАКЦИЯ
    with transaction.atomic():
      # Списать средства
      wallet.debit(
        amount=amount_usd,
        currency='USD',
        description=f'Покупка {shares_received:.2f} долей '
                    f'"{outcome.title}" в маркете '
                    f'"{market.title}"',
        transaction_type='prediction_buy',
        reference_id=str(outcome.id),
      )

      # Обновить AMM пул
      update_pool_after_buy(pool, outcome, shares_received)

      # Обновить цены всех исходов
      new_prices = recalculate_prices(pool, market)
      for out_id, new_price in new_prices.items():
        Outcome.objects.filter(id=out_id).update(
          current_price=new_price
        )

      # Обновить/создать позицию пользователя
      position, created = UserPosition.objects.get_or_create(
        user=user,
        outcome=outcome,
        defaults={
          'market': market,
          'shares': Decimal('0'),
          'avg_buy_price': Decimal('0'),
          'total_invested': Decimal('0'),
        }
      )

      # Пересчитать среднюю цену
      old_total = position.shares * position.avg_buy_price
      new_total = old_total + amount_after_fee
      position.shares += shares_received
      position.avg_buy_price = new_total / position.shares
      position.total_invested += amount_usd
      position.total_fees_paid += fee
      position.save()

      # Записать сделку
      trade = Trade.objects.create(
        user=user,
        market=market,
        outcome=outcome,
        trade_type='buy',
        shares=shares_received,
        price_per_share=avg_price,
        total_cost=amount_after_fee,
        fee_amount=fee,
        total_amount=amount_usd,
        price_before=price_before,
        price_after=new_prices[outcome.id],
        ip_address=...,
      )

      # Обновить статистику маркета
      market.total_volume += amount_usd
      market.total_shares += int(shares_received)
      if created:
        market.total_traders += 1
      market.save(update_fields=[
        'total_volume', 'total_shares', 'total_traders'
      ])

      # Обновить статистику исхода
      outcome.total_volume += amount_usd
      outcome.total_shares_sold += shares_received
      if created:
        outcome.holders_count += 1
      outcome.current_price = new_prices[outcome.id]
      outcome.save()

      # Записать активность
      MarketActivity.objects.create(
        market=market,
        user=user,
        activity_type='buy',
        trade=trade,
        description=(
          f'купил {shares_received:.0f} '
          f'{outcome.title} по {avg_price:.2f}¢'
        ),
      )

      # Обновить статистику пользователя
      if hasattr(user, 'stats'):
        user.stats.total_predictions += 1
        user.stats.save(update_fields=['total_predictions'])

    # 4. ПОСЛЕ ТРАНЗАКЦИИ
    # Обновить PriceHistory (async)
    update_price_snapshot.delay(market.id)

    # Инвалидировать кэш
    cache.delete(f'market_prices:{market.id}')

    return trade, None


  sell_shares(user, outcome, shares_amount):
    """
    Продажа долей обратно в пул.
    
    Параметры:
      user — продавец
      outcome — какой исход продаём
      shares_amount — сколько долей продать
    """

    market = outcome.market
    pool = market.amm_pool

    # 1. ПРОВЕРКИ
    if not market.is_trading_allowed():
      return None, 'Маркет закрыт для торгов'

    # Проверить что у пользователя есть доли
    try:
      position = UserPosition.objects.get(
        user=user, outcome=outcome
      )
    except UserPosition.DoesNotExist:
      return None, 'У вас нет долей этого исхода'

    if position.shares < shares_amount:
      return None, f'У вас только {position.shares:.2f} долей'

    if shares_amount <= 0:
      return None, 'Количество должно быть больше 0'

    # 2. РАСЧЁТ AMM
    # Сколько USD получит пользователь за продажу
    usd_return = calculate_amount_for_shares(
      pool, outcome, shares_amount
    )

    fee = usd_return * (market.fee_percent / 100)
    usd_after_fee = usd_return - fee

    price_before = outcome.current_price
    avg_sell_price = usd_return / shares_amount

    # 3. АТОМАРНАЯ ТРАНЗАКЦИЯ
    with transaction.atomic():
      # Зачислить средства
      wallet = user.wallet
      wallet.credit(
        amount=usd_after_fee,
        currency='USD',
        description=f'Продажа {shares_amount:.2f} долей '
                    f'"{outcome.title}"',
        transaction_type='prediction_sell',
        reference_id=str(outcome.id),
      )

      # Обновить AMM пул
      update_pool_after_sell(pool, outcome, shares_amount)

      # Обновить цены
      new_prices = recalculate_prices(pool, market)
      for out_id, new_price in new_prices.items():
        Outcome.objects.filter(id=out_id).update(
          current_price=new_price
        )

      # Обновить позицию
      position.shares -= shares_amount
      # Рассчитать P&L от продажи
      cost_basis = shares_amount * position.avg_buy_price
      profit = usd_after_fee - cost_basis
      position.realized_pnl += profit

      if position.shares == 0:
        # Позиция полностью закрыта
        outcome.holders_count = max(0, outcome.holders_count - 1)
      position.save()

      # Записать сделку
      trade = Trade.objects.create(
        user=user,
        market=market,
        outcome=outcome,
        trade_type='sell',
        shares=shares_amount,
        price_per_share=avg_sell_price,
        total_cost=usd_return,
        fee_amount=fee,
        total_amount=usd_after_fee,
        price_before=price_before,
        price_after=new_prices[outcome.id],
      )

      # Обновить статистику
      market.total_volume += usd_return
      market.save(update_fields=['total_volume'])

      outcome.total_volume += usd_return
      outcome.current_price = new_prices[outcome.id]
      outcome.save()

      # Активность
      MarketActivity.objects.create(
        market=market,
        user=user,
        activity_type='sell',
        trade=trade,
        description=(
          f'продал {shares_amount:.0f} '
          f'{outcome.title} по {avg_sell_price:.2f}¢'
        ),
      )

    update_price_snapshot.delay(market.id)
    cache.delete(f'market_prices:{market.id}')

    return trade, None
```

### AMM формулы (CPMM)

```
Математика AMM:

  Для БИНАРНОГО маркета (YES/NO):

    Пул содержит:
      q_yes — количество YES долей
      q_no  — количество NO долей
      k = q_yes * q_no — константа (invariant)

    Цена YES = q_no / (q_yes + q_no)
    Цена NO  = q_yes / (q_yes + q_no)
    Цена YES + Цена NO ≈ 1.00 (всегда)

    ПОКУПКА YES за $X:
      1. Пользователь вкладывает $X
      2. Добавляет $X в оба пула (минтит полный сет):
         q_yes += X
         q_no += X
      3. Продаёт NO доли обратно в пул:
         Сколько NO долей можно продать чтобы k сохранилось?
         новый q_no = k / новый q_yes
         shares_received = X + (q_no - k / (q_yes + X))
         
      Упрощённо:
        shares_received = q_no - k / (q_yes + amount)
        ← НЕТ, правильная формула для CPMM:

      Правильная формула (CPMM swap):
        Пользователь покупает YES доли, отдавая USD.
        USD = "виртуальный NO" в пуле.
        
        amount_in = X (USD после комиссии)
        
        Новый q_no = q_no + amount_in
        Новый q_yes = k / Новый q_no
        shares_out = q_yes - Новый q_yes
        
        То есть:
        shares_out = q_yes - (k / (q_no + amount_in))

    ПРОДАЖА YES за USD:
      shares_in = количество YES долей
      
      Новый q_yes = q_yes + shares_in
      Новый q_no = k / Новый q_yes
      usd_out = q_no - Новый q_no
      
      То есть:
      usd_out = q_no - (k / (q_yes + shares_in))

    ОБНОВЛЕНИЕ ЦЕН после сделки:
      price_yes = new_q_no / (new_q_yes + new_q_no)
      price_no = new_q_yes / (new_q_yes + new_q_no)


  Для МНОЖЕСТВЕННОГО маркета (N исходов):

    Пул: q_1, q_2, ..., q_n
    k = ∏(q_i) — произведение всех

    Цена i-го исхода:
      price_i = (∏(q_j, j≠i)) / (Σ(∏(q_j, j≠i) для всех i))
      
    Упрощённо для 3 исходов (A, B, C):
      price_A = (q_B * q_C) / (q_B*q_C + q_A*q_C + q_A*q_B)

    Покупка исхода i:
      shares_out = q_i - (k / ∏(q_j + amount, j≠i))
      
      Но для множественных проще использовать:
      Покупка: добавить amount ко всем пулам кроме i,
      взять доли из i.
      
      Для каждого j ≠ i: new_q_j = q_j + delta
      new_q_i = k / ∏(new_q_j, j≠i)
      shares_out = q_i - new_q_i


Реализация в коде:

  calculate_shares_for_amount(pool, outcome, amount):
    """Сколько долей получит пользователь за amount USD."""
    
    market = outcome.market
    
    if market.market_type == 'binary':
      outcomes = list(market.outcomes.order_by('sort_order'))
      yes_outcome = outcomes[0]
      no_outcome = outcomes[1]
      
      q_yes = pool.pool_yes
      q_no = pool.pool_no
      k = pool.constant_product
      
      if outcome == yes_outcome:
        # Покупка YES: USD идёт в NO пул
        new_q_no = q_no + amount
        new_q_yes = k / new_q_no
        shares = q_yes - new_q_yes
      else:
        # Покупка NO: USD идёт в YES пул
        new_q_yes = q_yes + amount
        new_q_no = k / new_q_yes
        shares = q_no - new_q_no
      
      return shares

    else:  # multiple
      # Множественный маркет
      outcomes = list(market.outcomes.order_by('sort_order'))
      
      # Добавить amount ко всем пулам КРОМЕ выбранного
      product_others = Decimal('1')
      for o in outcomes:
        if o.id != outcome.id:
          product_others *= (o.pool_shares + amount)
      
      k = pool.constant_product
      new_pool_target = k / product_others
      shares = outcome.pool_shares - new_pool_target
      
      return shares


  calculate_amount_for_shares(pool, outcome, shares):
    """Сколько USD получит пользователь за shares долей."""
    
    market = outcome.market
    
    if market.market_type == 'binary':
      outcomes = list(market.outcomes.order_by('sort_order'))
      q_yes = pool.pool_yes
      q_no = pool.pool_no
      k = pool.constant_product
      
      if outcome == outcomes[0]:  # YES
        new_q_yes = q_yes + shares
        new_q_no = k / new_q_yes
        usd = q_no - new_q_no
      else:  # NO
        new_q_no = q_no + shares
        new_q_yes = k / new_q_no
        usd = q_yes - new_q_yes
      
      return max(usd, Decimal('0'))


  update_pool_after_buy(pool, outcome, shares):
    """Обновить пул после покупки."""
    market = outcome.market
    
    if market.market_type == 'binary':
      outcomes = list(market.outcomes.order_by('sort_order'))
      
      if outcome == outcomes[0]:  # Купили YES
        pool.pool_yes -= shares
        # pool_no увеличился на amount (уже учтено в расчёте)
        pool.pool_no = pool.constant_product / pool.pool_yes
      else:
        pool.pool_no -= shares
        pool.pool_yes = pool.constant_product / pool.pool_no
      
      pool.last_trade_at = now()
      pool.save()

    else:
      outcome.pool_shares -= shares
      outcome.save()
      # Пересчитать pool_shares для остальных
      ...


  recalculate_prices(pool, market):
    """Пересчитать цены всех исходов."""
    prices = {}
    
    if market.market_type == 'binary':
      total = pool.pool_yes + pool.pool_no
      outcomes = list(market.outcomes.order_by('sort_order'))
      prices[outcomes[0].id] = pool.pool_no / total     # YES
      prices[outcomes[1].id] = pool.pool_yes / total     # NO
    
    else:
      outcomes = list(market.outcomes.order_by('sort_order'))
      # Для множественного
      inverse_pools = []
      for o in outcomes:
        product = Decimal('1')
        for other in outcomes:
          if other.id != o.id:
            product *= other.pool_shares
        inverse_pools.append((o.id, product))
      
      total = sum(ip[1] for ip in inverse_pools)
      for o_id, inv in inverse_pools:
        prices[o_id] = inv / total
    
    return prices


  get_buy_preview(outcome, amount_usd):
    """
    Превью покупки (для отображения пользователю
    ПЕРЕД подтверждением сделки).
    """
    market = outcome.market
    pool = market.amm_pool
    
    fee = amount_usd * (market.fee_percent / 100)
    amount_after_fee = amount_usd - fee
    
    shares = calculate_shares_for_amount(
      pool, outcome, amount_after_fee
    )
    
    avg_price = amount_after_fee / shares if shares > 0 else 0
    
    # Рассчитать новую цену после покупки
    # (без реального обновления пула)
    ...
    
    slippage = ((avg_price - outcome.current_price) 
                / outcome.current_price) * 100
    
    potential_payout = shares * Decimal('1.00')
    potential_profit = potential_payout - amount_usd
    potential_roi = (potential_profit / amount_usd) * 100
    
    return {
      'shares': shares,
      'avg_price': avg_price,
      'fee': fee,
      'total_cost': amount_usd,
      'slippage': slippage,
      'potential_payout': potential_payout,
      'potential_profit': potential_profit,
      'potential_roi': potential_roi,
      'new_price': ...,
    }
```

### Пользовательский интерфейс покупки

```
Блок покупки на странице маркета (боковая панель):

  ┌──────────────────────────────────┐
  │  📊 Торговля                    │
  │                                  │
  │  [YES 65¢]  [NO 35¢]           │
  │  (выбранный таб подсвечен)      │
  │                                  │
  │  Сумма ($)                      │
  │  ┌──────────────────────────┐   │
  │  │ 50.00                    │   │
  │  └──────────────────────────┘   │
  │  [10] [25] [50] [100] [Все]     │
  │                                  │
  │  ── Превью ──────────────────  │
  │  Вы получите: 72.3 доли YES    │
  │  Средняя цена: 65.8¢           │
  │  Проскальзывание: 1.2%         │
  │  Комиссия: $1.00 (2%)          │
  │  ─────────────────────────────  │
  │  Потенциальная выплата: $72.30  │
  │  Потенциальная прибыль: +$21.30│
  │  ROI: +42.6% 📈                │
  │                                  │
  │  [Купить YES за $50.00]         │
  │  (зелёная кнопка)              │
  │                                  │
  │  ── Ваша позиция ────────────  │
  │  YES: 150 долей (avg 58¢)      │
  │  Стоимость: $97.50              │
  │  P&L: +$9.50 (+10.8%)          │
  │                                  │
  │  [Продать YES]                  │
  │                                  │
  └──────────────────────────────────┘

HTMX:
  При вводе суммы:
    hx-get="/api/predictions/{market_id}/preview/"
    hx-trigger="keyup changed delay:300ms"
    hx-target="#trade-preview"
    hx-include="[name='amount'],[name='outcome']"

  При покупке:
    hx-post="/api/predictions/{market_id}/buy/"
    hx-target="#trade-result"
    hx-confirm="Купить 72.3 YES долей за $50.00?"

  При продаже:
    Модальное окно с выбором количества долей
    Слайдер или ввод числа
    Превью возврата
    [Продать] → hx-post
```

### Модальное окно продажи

```
  ┌──────────────────────────────────────┐
  │  📤 Продать YES доли                │
  │                                      │
  │  У вас: 150 долей                   │
  │                                      │
  │  Количество для продажи:            │
  │  [━━━━━━━━━━━━●━━━] 100             │
  │  ┌────────────────────────────┐     │
  │  │ 100                        │     │
  │  └────────────────────────────┘     │
  │  [25%] [50%] [75%] [100%]           │
  │                                      │
  │  ── Превью ──────────────────────  │
  │  Вы получите: $61.20                │
  │  Средняя цена продажи: 61.2¢       │
  │  Комиссия: $1.25 (2%)              │
  │  Прибыль/убыток: +$3.20 (+5.5%)   │
  │                                      │
  │  [Продать 100 долей]                │
  │  [Отмена]                           │
  │                                      │
  └──────────────────────────────────────┘
```

### Критерий готовности шага 7.3

```
□ TradingService.buy_shares работает
□ TradingService.sell_shares работает
□ AMM формулы (CPMM) рассчитывают правильно
□ Цены YES + NO ≈ $1.00 (всегда)
□ Slippage рассчитывается
□ Ограничение по slippage (> 20% — отказ)
□ Комиссия списывается
□ Средства списываются/зачисляются через wallet
□ UserPosition создаётся/обновляется
□ Средняя цена покупки рассчитывается
□ P&L рассчитывается (realized + unrealized)
□ Trade записывается
□ MarketActivity записывается
□ Статистика маркета обновляется
□ Цены исходов обновляются после каждой сделки
□ PriceHistory записывается
□ Превью покупки/продажи (HTMX)
□ Атомарные транзакции (целостность данных)
□ Кэш инвалидируется
□ Проверка баланса перед покупкой
□ Проверка trust level лимитов
□ Множественные маркеты: торги работают
□ Минимальная сумма: $0.10
□ Нельзя торговать в закрытом маркете
```

---

## ШАГ 7.4 — РЕЗОЛЮЦИЯ МАРКЕТОВ

### Задача

```
Реализуй систему резолюции маркетов модератором.
Определение выигрышного исхода.
Выплата выигрышей. Оспаривание.
Автоматическое закрытие по дедлайну.
```

### ResolutionService

```
ResolutionService:

  close_market(market):
    """
    Закрыть торги (по дедлайну или вручную).
    Вызывается:
      - Celery задачей при достижении closes_at
      - Модератором вручную
    """
    if market.status != 'active':
      return False, 'Маркет не активен'

    market.status = 'closed'
    market.save(update_fields=['status'])

    # Уведомить всех трейдеров
    traders = UserPosition.objects.filter(
      market=market, shares__gt=0
    ).values_list('user_id', flat=True).distinct()

    for user_id in traders:
      NotificationService.create_notification(
        user_id=user_id,
        notification_type='market_closed',
        title=f'Торги закрыты: {market.title}',
        message='Маркет ожидает резолюции. '
                'Покупка и продажа больше невозможны.',
        link=f'/predictions/{market.slug}/',
      )

    return True, None


  resolve_market(market, winning_outcome_id, resolver, details=''):
    """
    Резолвить маркет: определить выигрышный исход.
    
    Параметры:
      market — маркет
      winning_outcome_id — UUID выигрышного исхода
      resolver — модератор
      details — подробности резолюции
    """

    # 1. ПРОВЕРКИ
    if market.status not in ('closed', 'active'):
      return False, 'Маркет должен быть закрыт или активен'

    try:
      winning_outcome = market.outcomes.get(id=winning_outcome_id)
    except Outcome.DoesNotExist:
      return False, 'Исход не найден'

    # Нельзя резолвить свой маркет (конфликт интересов)
    if market.created_by == resolver:
      # Только если суперадмин
      if not resolver.is_superuser:
        return False, 'Нельзя резолвить свой маркет'

    # Нельзя резолвить если у модератора есть позиция
    if UserPosition.objects.filter(
      user=resolver, market=market, shares__gt=0
    ).exists():
      if not resolver.is_superuser:
        return False, 'У вас есть позиция в этом маркете'

    # 2. АТОМАРНАЯ ТРАНЗАКЦИЯ
    with transaction.atomic():
      # Закрыть торги если ещё открыты
      if market.status == 'active':
        market.status = 'closed'

      # Пометить исходы
      for outcome in market.outcomes.all():
        outcome.is_winner = (outcome.id == winning_outcome_id)
        outcome.save(update_fields=['is_winner'])

      # Обновить маркет
      market.status = 'resolved'
      market.resolved_at = now()
      market.resolved_by = resolver
      market.resolution_details = details
      market.save()

      # Выплатить выигрыши
      settle_positions(market, winning_outcome)

    # 3. УВЕДОМЛЕНИЯ
    notify_resolution(market, winning_outcome)

    # 4. ЛОГ
    AdminActionLog.objects.create(
      admin_user=resolver,
      action_type='market_resolved',
      target_object_type='Market',
      target_object_id=market.id,
      description=(
        f'Маркет "{market.title}" резолвлен. '
        f'Результат: {winning_outcome.title}'
      ),
      details={
        'winning_outcome_id': str(winning_outcome_id),
        'total_payout': str(total_payout),
      },
    )

    return True, None


  settle_positions(market, winning_outcome):
    """
    Выплата выигрышей и обнуление проигрышных позиций.
    
    Правило:
      Каждая доля выигрышного исхода = $1.00
      Каждая доля проигрышного исхода = $0.00
    """

    total_payout = Decimal('0')

    # Все позиции в этом маркете
    positions = UserPosition.objects.filter(
      market=market,
      shares__gt=0,
      is_settled=False,
    ).select_related('user', 'outcome')

    for position in positions:
      if position.outcome == winning_outcome:
        # ВЫИГРЫШ: $1.00 за каждую долю
        payout = position.shares * Decimal('1.00')
        position.settlement_amount = payout
        total_payout += payout

        # Зачислить на баланс
        wallet = position.user.wallet
        wallet.credit(
          amount=payout,
          currency='USD',
          description=(
            f'Выигрыш: {position.shares:.0f} долей '
            f'"{winning_outcome.title}" в маркете '
            f'"{market.title}"'
          ),
          transaction_type='prediction_payout',
          reference_id=str(market.id),
        )
      else:
        # ПРОИГРЫШ: $0.00
        position.settlement_amount = Decimal('0')

      position.is_settled = True
      position.save()

    return total_payout


  notify_resolution(market, winning_outcome):
    """Уведомить всех участников."""

    positions = UserPosition.objects.filter(
      market=market,
      is_settled=True,
    ).select_related('user', 'outcome')

    for position in positions:
      if position.outcome == winning_outcome:
        # Выигрыш
        profit = position.settlement_amount - position.total_invested
        NotificationService.create_notification(
          user=position.user,
          notification_type='market_resolved',
          title=f'🎉 Вы выиграли!',
          message=(
            f'Маркет "{market.title}" разрешён. '
            f'Результат: {winning_outcome.title}. '
            f'Выплата: ${position.settlement_amount:.2f} '
            f'(прибыль: ${profit:.2f})'
          ),
          icon='🎉',
          link=f'/predictions/{market.slug}/',
          data={
            'payout': str(position.settlement_amount),
            'profit': str(profit),
          },
        )
      else:
        # Проигрыш
        NotificationService.create_notification(
          user=position.user,
          notification_type='market_resolved',
          title=f'Маркет разрешён',
          message=(
            f'Маркет "{market.title}" разрешён. '
            f'Результат: {winning_outcome.title}. '
            f'Ваша позиция ({position.outcome.title}) '
            f'не выиграла. Потеря: ${position.total_invested:.2f}'
          ),
          icon='📊',
          link=f'/predictions/{market.slug}/',
        )


  cancel_market(market, reason, canceller):
    """
    Отмена маркета. Все средства возвращаются.
    
    Причины:
      - Некорректная формулировка
      - Событие отменено
      - Дублирующий маркет
    """

    with transaction.atomic():
      # Вернуть средства всем трейдерам
      positions = UserPosition.objects.filter(
        market=market,
        is_settled=False,
      ).select_related('user')

      for position in positions:
        if position.total_invested > 0:
          wallet = position.user.wallet
          wallet.credit(
            amount=position.total_invested,
            currency='USD',
            description=(
              f'Возврат средств: маркет '
              f'"{market.title}" отменён'
            ),
            transaction_type='prediction_refund',
            reference_id=str(market.id),
          )

          position.settlement_amount = position.total_invested
          position.is_settled = True
          position.save()

      market.status = 'cancelled'
      market.resolution_details = f'Отменён: {reason}'
      market.resolved_by = canceller
      market.resolved_at = now()
      market.save()

    # Уведомить всех
    # ...

    return True, None
```

### Интерфейс резолюции (модератор)

```
URL: /admin/predictions/{market_id}/resolve/
Доступ: @staff_required + permission 'can_resolve_market'

  ┌──────────────────────────────────────────────────────┐
  │  ⚖️ Резолюция маркета                              │
  │                                                      │
  │  📊 "Трамп победит на выборах 2028?"                │
  │  Статус: ⏳ Торги закрыты                            │
  │  Закрыт: 05.11.2028                                 │
  │                                                      │
  │  ── Информация ──────────────────────────────────── │
  │  Трейдеров: 234 │ Объём: $12,345                    │
  │  YES: 65¢ (финальная цена) │ NO: 35¢                │
  │                                                      │
  │  Источник резолюции:                                 │
  │  "Официальные результаты, объявленные AP"            │
  │                                                      │
  │  ── Выберите результат ──────────────────────────── │
  │                                                      │
  │  ○ ✅ YES — Да                                      │
  │    Держателей: 178 │ Долей: 12,345                  │
  │    Выплата: $12,345.00                               │
  │                                                      │
  │  ○ ❌ NO — Нет                                      │
  │    Держателей: 56 │ Долей: 8,234                    │
  │    Выплата: $8,234.00                                │
  │                                                      │
  │  ── Или отменить ────────────────────────────────── │
  │                                                      │
  │  ○ 🚫 Отменить маркет (возврат всех средств)        │
  │                                                      │
  │  Подробности резолюции *                             │
  │  ┌────────────────────────────────────────────────┐ │
  │  │ Трамп набрал 312 голосов выборщиков,           │ │
  │  │ объявлен победителем AP 06.11.2028.            │ │
  │  └────────────────────────────────────────────────┘ │
  │                                                      │
  │  ⚠️ Это действие необратимо!                        │
  │  Будет выплачено: $12,345.00                         │
  │                                                      │
  │  [⚖️ Резолвить маркет]                              │
  │                                                      │
  │  ── Финансовая сводка ───────────────────────────── │
  │  Собрано комиссий: $246.90                           │
  │  Ликвидность пула: $1,000.00                         │
  │  Общий объём: $12,345.00                             │
  │  P&L платформы: +$246.90                             │
  │                                                      │
  └──────────────────────────────────────────────────────┘
```

### Оспаривание резолюции

```
URL: /predictions/{slug}/dispute/
Доступ: @login_required (только участники маркета)

Условия:
  - Маркет резолвлен < 48 часов назад
  - У пользователя была позиция
  - Пользователь НЕ выиграл (мотивация оспорить)
  - Максимум 1 оспаривание на пользователя на маркет

  ┌──────────────────────────────────────────────────┐
  │  ⚠️ Оспорить результат                         │
  │                                                  │
  │  Маркет: "Трамп победит на выборах 2028?"       │
  │  Результат: YES                                  │
  │                                                  │
  │  Почему вы считаете результат неверным?          │
  │  ┌──────────────────────────────────────────┐   │
  │  │ (обязательно, минимум 50 символов)       │   │
  │  │                                          │   │
  │  └──────────────────────────────────────────┘   │
  │                                                  │
  │  Ссылка на доказательство (опционально):         │
  │  ┌──────────────────────────────────────────┐   │
  │  │ https://...                               │   │
  │  └──────────────────────────────────────────┘   │
  │                                                  │
  │  [Отправить на рассмотрение]                    │
  │                                                  │
  │  ℹ️ Если будет подтверждено — маркет             │
  │  будет перерезолвлен. Если нет — результат      │
  │  останется без изменений.                        │
  │                                                  │
  └──────────────────────────────────────────────────┘

Модель Dispute:
  id: UUID
  market: ForeignKey → Market
  user: ForeignKey → User
  reason: TextField
  evidence_url: URLField, nullable
  status: choices (pending, reviewing, upheld, dismissed)
  reviewed_by: ForeignKey → User, nullable
  review_comment: TextField, blank
  created_at, resolved_at

Если dispute upheld (подтверждён):
  → Маркет переходит в status = 'disputed'
  → Старшый модератор перерезолвит
  → Если результат изменился:
    → Отменить старые выплаты (забрать деньги)
    → Сделать новые выплаты
    → Уведомить всех
```

### Celery задачи

```
close_expired_markets():
  Периодическая задача (каждую минуту).
  Найти маркеты где:
    status = 'active'
    AND closes_at <= now()
  Для каждого: close_market(market)

remind_pending_resolution():
  Периодическая задача (каждые 6 часов).
  Найти маркеты где:
    status = 'closed'
    AND closes_at < now() - 24 часа
    AND resolved_at IS NULL
  Отправить напоминание модераторам:
    "Маркет X ожидает резолюции уже 24+ часа"

cleanup_old_price_history():
  Периодическая задача (ежедневно).
  Удалить:
    interval='1m' старше 7 дней
    interval='5m' старше 30 дней
    interval='1h' старше 1 года
```

### Критерий готовности шага 7.4

```
□ close_market работает (вручную + автоматически)
□ resolve_market: выбор выигрышного исхода
□ Выплата выигрышей: $1.00 за долю
□ Проигрышные позиции обнуляются
□ Средства зачисляются на баланс
□ Уведомления: выигравшим и проигравшим
□ Нельзя резолвить свой маркет
□ Нельзя резолвить если есть позиция
□ cancel_market: возврат всех средств
□ Оспаривание: форма + модель Dispute
□ Celery: автозакрытие по дедлайну
□ Celery: напоминание о pending резолюции
□ AdminActionLog для каждой резолюции
□ Атомарные транзакции
□ Финансовая сводка для модератора
□ Мобильная адаптация
```

---

## ШАГ 7.5 — ФРОНТЕНД (СТРАНИЦЫ)

### Задача

```
Создай все страницы predictions:
главная, категории, страница маркета,
мои позиции, графики цен, комментарии.
```

### Структура URL

```
/predictions/                         # Главная
/predictions/category/{slug}/         # Категория
/predictions/{market_slug}/           # Страница маркета
/predictions/my/                      # Мои позиции
/predictions/my/history/              # История сделок
/predictions/leaderboard/             # Лидерборд

# API (HTMX)
/api/predictions/{id}/preview/        # Превью покупки
/api/predictions/{id}/buy/            # Покупка
/api/predictions/{id}/sell/           # Продажа
/api/predictions/{id}/prices/         # Текущие цены
/api/predictions/{id}/chart/          # Данные графика
/api/predictions/{id}/activity/       # Лента активности
/api/predictions/{id}/comments/       # Комментарии
/api/predictions/{id}/comments/add/   # Добавить комментарий
```

### Главная страница Predictions

```
URL: /predictions/

  ┌──────────────────────────────────────────────────────┐
  │  📊 Маркеты предсказаний                            │
  │                                                      │
  │  ── Категории ───────────────────────────────────── │
  │  [🏛️Политика] [⚽Спорт] [💰Крипто] [💻Тех]        │
  │  [🎬Развл.] [🔬Наука] [📈Экономика] [🌍Мир]       │
  │                                                      │
  │  ── 🔥 Горячие маркеты ─────────────────────────── │
  │                                                      │
  │  ┌─────────────────────┐ ┌─────────────────────┐   │
  │  │ [img]                │ │ [img]                │   │
  │  │ Трамп победит       │ │ BTC выше $150k      │   │
  │  │ на выборах 2028?    │ │ до конца 2026?      │   │
  │  │                     │ │                     │   │
  │  │ YES 65¢  NO 35¢    │ │ YES 42¢  NO 58¢    │   │
  │  │ [━━━━━━━●━━] 65%   │ │ [━━━━●━━━━━] 42%   │   │
  │  │                     │ │                     │   │
  │  │ 💰$12.3k │ 👥234   │ │ 💰$45.6k │ 👥567   │   │
  │  │ ⏰ 1,234 дня        │ │ ⏰ 645 дней         │   │
  │  └─────────────────────┘ └─────────────────────┘   │
  │                                                      │
  │  ── ⏰ Скоро закрываются ────────────────────────── │
  │                                                      │
  │  ┌──────────────────────────────────────────────┐   │
  │  │ ⚽ Реал победит Барселону?                   │   │
  │  │ YES 55¢ │ NO 45¢ │ 💰$2.3k │ ⏰ 3 часа     │   │
  │  └──────────────────────────────────────────────┘   │
  │  ┌──────────────────────────────────────────────┐   │
  │  │ 🎬 Оскар за лучший фильм 2025?              │   │
  │  │ Множественный │ 💰$8.9k │ ⏰ 2 дня          │   │
  │  └──────────────────────────────────────────────┘   │
  │                                                      │
  │  ── 📊 Все маркеты ─────────────────────────────── │
  │                                                      │
  │  Сортировка: [Новые|Популярные|Объём|Дедлайн]       │
  │  Статус: [Активные|Закрытые|Резолвленные]           │
  │  Поиск: [_________________________] 🔍              │
  │                                                      │
  │  (список маркетов карточками)                        │
  │                                                      │
  │  [Загрузить ещё] (HTMX бесконечный скролл)         │
  │                                                      │
  │  ── ✅ Недавно резолвленные ─────────────────────── │
  │                                                      │
  │  ┌──────────────────────────────────────────────┐   │
  │  │ ✅ ЕЦБ снизит ставку в марте 2025?          │   │
  │  │ Результат: YES │ Выплачено: $5,678          │   │
  │  │ Резолвлен: 2 дня назад                      │   │
  │  └──────────────────────────────────────────────┘   │
  │                                                      │
  └──────────────────────────────────────────────────────┘
```

### Страница маркета (детальная)

```
URL: /predictions/{market_slug}/

  ┌──────────────────────────────────────────────────────────────┐
  │                                                              │
  │  ┌────────────────────────────────┐  ┌────────────────────┐ │
  │  │  ОСНОВНАЯ ИНФОРМАЦИЯ (65%)    │  │ ТОРГОВАЯ ПАНЕЛЬ    │ │
  │  │                                │  │ (35%)              │ │
  │  │  🏛️ Политика                  │  │                    │ │
  │  │                                │  │ (описана в шаге    │ │
  │  │  Трамп победит на             │  │  7.3 — блок        │ │
  │  │  выборах 2028?                │  │  покупки/продажи)  │ │
  │  │                                │  │                    │ │
  │  │  YES 65¢ ████████████░░░░     │  │                    │ │
  │  │  NO  35¢ ██████░░░░░░░░░░     │  │                    │ │
  │  │                                │  │                    │ │
  │  │  💰 Объём: $12,345             │  │                    │ │
  │  │  👥 Трейдеров: 234             │  │                    │ │
  │  │  ⏰ Дедлайн: 05.11.2028       │  │                    │ │
  │  │  📅 Создан: 15.03.2025        │  │                    │ │
  │  │                                │  │                    │ │
  │  │  ── График цены ────────────  │  │                    │ │
  │  │                                │  │                    │ │
  │  │  $0.80 ┤                      │  │                    │ │
  │  │        │     ╱\               │  │                    │ │
  │  │  $0.65 ┤   ╱   \  ╱──        │  │                    │ │
  │  │        │  ╱     \╱            │  │                    │ │
  │  │  $0.50 ┤╱                     │  │                    │ │
  │  │        │                      │  │                    │ │
  │  │  $0.35 ┤                      │  │                    │ │
  │  │        └──────────────────    │  │                    │ │
  │  │        Mar  Apr  May  Jun     │  │                    │ │
  │  │                                │  │                    │ │
  │  │  Период: [24ч|7д|30д|Всё]     │  │                    │ │
  │  │  Линии: ☑YES ☑NO              │  │                    │ │
  │  │                                │  │                    │ │
  │  │  ── Описание ────────────── │  │                    │ │
  │  │                                │  │                    │ │
  │  │  Этот маркет разрешится       │  │                    │ │
  │  │  как YES если Дональд Трамп   │  │                    │ │
  │  │  официально будет объявлен    │  │                    │ │
  │  │  победителем президентских    │  │                    │ │
  │  │  выборов США 2028 года.       │  │                    │ │
  │  │                                │  │                    │ │
  │  │  Источник резолюции:          │  │                    │ │
  │  │  AP или Reuters.              │  │                    │ │
  │  │                                │  │                    │ │
  │  │  ── Лента активности ──────  │  │                    │ │
  │  │                                │  │                    │ │
  │  │  🟢 user123 купил 50 YES     │  │                    │ │
  │  │     за $32.50 • 5 мин назад  │  │                    │ │
  │  │                                │  │                    │ │
  │  │  🔴 player456 продал 30 NO   │  │                    │ │
  │  │     за $8.70 • 12 мин назад  │  │                    │ │
  │  │                                │  │                    │ │
  │  │  🟢 trader789 купил 100 YES  │  │                    │ │
  │  │     за $65.00 • 1 час назад  │  │                    │ │
  │  │                                │  │                    │ │
  │  │  [Показать ещё]               │  │                    │ │
  │  │                                │  │                    │ │
  │  │  ── Комментарии (47) ──────  │  │                    │ │
  │  │                                │  │                    │ │
  │  │  Оставить комментарий:        │  │                    │ │
  │  │  ┌──────────────────────────┐│  │                    │ │
  │  │  │                          ││  │                    │ │
  │  │  └──────────────────────────┘│  │                    │ │
  │  │  [Отправить]                  │  │                    │ │
  │  │                                │  │                    │ │
  │  │  🟢 expert42 (YES: 200 долей) │  │                    │ │
  │  │  По всем опросам Трамп        │  │                    │ │
  │  │  лидирует с отрывом 8%.      │  │                    │ │
  │  │  👍 12 • Ответить • 2ч назад │  │                    │ │
  │  │                                │  │                    │ │
  │  │    ↳ analyzer99               │  │                    │ │
  │  │    Опросы часто ошибаются.    │  │                    │ │
  │  │    В 2016 тоже лидировал.     │  │                    │ │
  │  │    👍 5 • 1ч назад            │  │                    │ │
  │  │                                │  │                    │ │
  │  │  🔴 skeptic77 (NO: 50 долей)  │  │                    │ │
  │  │  Рано делать выводы, до       │  │                    │ │
  │  │  выборов 3 года.             │  │                    │ │
  │  │  👍 8 • Ответить • 5ч назад  │  │                    │ │
  │  │                                │  │                    │ │
  │  │  [Загрузить ещё комментарии]  │  │                    │ │
  │  │                                │  │                    │ │
  │  └────────────────────────────────┘  └────────────────────┘ │
  │                                                              │
  │  ── Похожие маркеты ─────────────────────────────────────── │
  │  ┌──────────┐ ┌──────────┐ ┌──────────┐                    │
  │  │ Кто пре- │ │ Респуб-  │ │ Демократ │                    │
  │  │ зидент   │ │ ликанцы  │ │ получат  │                    │
  │  │ после    │ │ выиграют │ │ Сенат?   │                    │
  │  │ Трампа?  │ │ Палату?  │ │          │                    │
  │  └──────────┘ └──────────┘ └──────────┘                    │
  │                                                              │
  └──────────────────────────────────────────────────────────────┘

Мобильная версия:
  Торговая панель → внизу экрана (fixed bottom)
  Свёрнута в кнопку "Торговать"
  При клике → раскрывается снизу (bottom sheet)
```

### Страница "Мои позиции"

```
URL: /predictions/my/

  ┌──────────────────────────────────────────────────────┐
  │  📊 Мои предсказания                                │
  │                                                      │
  │  ── Сводка ──────────────────────────────────────── │
  │  💰 Инвестировано: $1,234  │ 📈 P&L: +$234 (+19%) │
  │  🏆 Точность: 62%         │ 📊 Маркетов: 15       │
  │                                                      │
  │  [Активные|Закрытые|Резолвленные|Все]                │
  │                                                      │
  │  ── Активные позиции ────────────────────────────── │
  │                                                      │
  │  ┌──────────────────────────────────────────────┐   │
  │  │ 🏛️ Трамп победит на выборах 2028?           │   │
  │  │                                              │   │
  │  │ Позиция: YES                                 │   │
  │  │ Долей: 150 │ Средняя цена: 58¢              │   │
  │  │ Инвестировано: $87.00                        │   │
  │  │ Текущая стоимость: $97.50 (65¢/доля)         │   │
  │  │ P&L: +$10.50 (+12.1%) 📈                    │   │
  │  │ Потенциальная выплата: $150.00               │   │
  │  │                                              │   │
  │  │ [Купить ещё] [Продать]    ⏰ 1,234 дня      │   │
  │  └──────────────────────────────────────────────┘   │
  │                                                      │
  │  ┌──────────────────────────────────────────────┐   │
  │  │ 💰 BTC выше $150k до конца 2026?             │   │
  │  │                                              │   │
  │  │ Позиция: NO                                  │   │
  │  │ Долей: 80 │ Средняя цена: 55¢               │   │
  │  │ Инвестировано: $44.00                        │   │
  │  │ Текущая стоимость: $46.40 (58¢/доля)         │   │
  │  │ P&L: +$2.40 (+5.5%) 📈                      │   │
  │  │                                              │   │
  │  │ [Купить ещё] [Продать]    ⏰ 645 дней       │   │
  │  └──────────────────────────────────────────────┘   │
  │                                                      │
  │  ── Резолвленные ────────────────────────────────── │
  │                                                      │
  │  ┌──────────────────────────────────────────────┐   │
  │  │ ✅ ЕЦБ снизит ставку в марте?               │   │
  │  │ Позиция: YES (выиграл) │ Доли: 200          │   │
  │  │ Инвестировано: $130 │ Выплата: $200          │   │
  │  │ Прибыль: +$70.00 (+53.8%) 🎉                │   │
  │  └──────────────────────────────────────────────┘   │
  │                                                      │
  │  ┌──────────────────────────────────────────────┐   │
  │  │ ❌ SpaceX запустит Starship в феврале?        │   │
  │  │ Позиция: YES (проиграл) │ Доли: 50          │   │
  │  │ Инвестировано: $40 │ Выплата: $0             │   │
  │  │ Убыток: -$40.00 (-100%) 📉                  │   │
  │  └──────────────────────────────────────────────┘   │
  │                                                      │
  └──────────────────────────────────────────────────────┘
```

### График цен (реализация)

```
Технология: HTML Canvas через Chart.js (CDN)
  ИЛИ: Lightweight Charts от TradingView (бесплатно)
  Рекомендация: Lightweight Charts — красивее,
  легче, создан для финансовых графиков.

<script src="https://unpkg.com/lightweight-charts/dist/lightweight-charts.standalone.production.js"></script>

Данные для графика:
  HTMX запрос:
  hx-get="/api/predictions/{id}/chart/?period=7d&outcome=yes"
  
  Ответ (JSON):
  {
    "data": [
      {"time": "2025-03-15", "value": 0.50},
      {"time": "2025-03-16", "value": 0.52},
      {"time": "2025-03-17", "value": 0.58},
      ...
    ]
  }

Отображение:
  - Линейный график (area chart)
  - YES: зелёная линия, зелёная заливка под ней
  - NO: красная линия (опционально)
  - Ось Y: $0.00 — $1.00
  - Ось X: время
  - Тултип при наведении: цена + дата + объём
  - Переключатели периода: 24ч, 7д, 30д, Всё
  - Тёмная тема (фон графика = фон страницы)
```

### Комментарии (реализация)

```
Добавление комментария:
  HTMX: hx-post="/api/predictions/{id}/comments/add/"
  Тело: {text: "...", parent_id: null}
  Ответ: HTML фрагмент нового комментария
  hx-swap: "afterbegin" в #comments-list

Загрузка комментариев:
  Первые 20 при загрузке страницы.
  "Загрузить ещё":
    hx-get="/api/predictions/{id}/comments/?page=2"
    hx-trigger="click"
    hx-swap="afterend"

Ответы:
  При клике "Ответить" → показать форму под комментарием
  parent_id = id комментария
  Максимум 1 уровень вложенности

Лайки:
  hx-post="/api/predictions/comments/{id}/like/"
  Toggle: лайк / убрать лайк
  Обновить счётчик

Позиция автора:
  Рядом с именем показывать позицию:
  🟢 expert42 (YES: 200 долей)
  🔴 skeptic77 (NO: 50 долей)
  ⚪ viewer (нет позиции)

Модерация:
  Модератор видит кнопку [🗑️ Скрыть]
  При скрытии: текст заменяется на
  "Комментарий скрыт модератором"

Ограничения:
  - Максимум 2000 символов
  - Rate limit: 1 комментарий в 30 секунд
  - Минимум trust_level 2 для комментариев
  - Нельзя комментировать резолвленные маркеты
    старше 7 дней
```

### Критерий готовности шага 7.5

```
□ Главная /predictions/: категории, горячие, скоро закрываются
□ Страница категории /predictions/category/{slug}/
□ Страница маркета: полная информация
□ Торговая панель: покупка/продажа (HTMX)
□ Превью сделки при вводе суммы
□ График цен (Lightweight Charts)
□ Переключение периодов графика (24ч, 7д, 30д, всё)
□ Данные графика из PriceHistory
□ Лента активности (последние сделки)
□ Комментарии: добавление, ответы, лайки
□ Позиция автора рядом с комментарием
□ Модерация комментариев
□ Страница "Мои позиции": активные + резолвленные
□ P&L по каждой позиции
□ Сводка общей статистики
□ Похожие маркеты (та же категория)
□ Поиск маркетов
□ Фильтрация и сортировка
□ Бесконечный скролл (HTMX)
□ Мобильная адаптация (торговая панель = bottom sheet)
□ Страницы ошибок (маркет не найден)
□ Резолвленный маркет: показать результат + выплаты
□ Счётчик просмотров
□ HTMX: обновление цен каждые 10 секунд
```

---

## ШАГ 7.6 — ЛИДЕРБОРД, АНАЛИТИКА, АВТОМАТИЗАЦИЯ

### Задача

```
Лидерборд лучших трейдеров.
Автопометка горячих маркетов.
Обновление статистики.
Связь с UserStats.
```

### Лидерборд

```
URL: /predictions/leaderboard/

  ┌──────────────────────────────────────────────────────┐
  │  🏆 Лидерборд предсказаний                         │
  │                                                      │
  │  Период: [Неделя|Месяц|Всё время]                   │
  │  Метрика: [Прибыль|Точность|Объём]                  │
  │                                                      │
  │  ── Топ-10 по прибыли (этот месяц) ──────────────  │
  │                                                      │
  │  🥇 1. expert42                                     │
  │     Прибыль: +$1,234 │ Точность: 72%               │
  │     Маркетов: 23 │ Лучшая: +$456 (BTC > $100k)     │
  │                                                      │
  │  🥈 2. trader_pro                                   │
  │     Прибыль: +$987 │ Точность: 68%                 │
  │     Маркетов: 45 │ Лучшая: +$234                   │
  │                                                      │
  │  🥉 3. prediction_king                              │
  │     Прибыль: +$765 │ Точность: 65%                 │
  │     Маркетов: 18 │ Лучшая: +$321                   │
  │                                                      │
  │  4.  analyst99         +$543  │ 61% │ 32 маркета   │
  │  5.  lucky_guesser     +$432  │ 58% │ 67 маркетов  │
  │  ...                                                │
  │  10. newbie123         +$123  │ 55% │ 8 маркетов   │
  │                                                      │
  │  ── Ваше место ──────────────────────────────────── │
  │  42. you_username      +$45   │ 52% │ 5 маркетов   │
  │                                                      │
  └──────────────────────────────────────────────────────┘

Расчёт лидерборда:
  Celery задача (каждый час):
    Для каждого пользователя с позициями:
      - Посчитать realized_pnl за период
      - Посчитать accuracy (% правильных предсказаний)
      - Посчитать объём торгов
    Кешировать в Redis на 1 час

  Метрики:
    Прибыль = сумма всех realized_pnl + settlement_amount
              минус total_invested для резолвленных маркетов
    Точность = выигранные_позиции / все_резолвленные_позиции * 100
    Объём = сумма total_invested по всем позициям

Приватность:
  Если пользователь скрыл профиль:
    → Показывать как "Игрок ***"
  Если is_hidden_from_leaderboard:
    → Не показывать вообще
```

### Автопометка горячих маркетов

```
Celery задача update_hot_markets() (каждые 15 минут):

  Критерии "горячего" маркета (любой из):
    1. Объём торгов за последние 24ч > $500
    2. Количество сделок за 24ч > 20
    3. Изменение цены > 10% за 24ч
    4. Количество новых комментариев за 24ч > 10

  Логика:
    1. Сбросить is_hot для всех маркетов
    2. Найти маркеты по критериям
    3. Установить is_hot = True
    4. Максимум 20 горячих одновременно
    5. Сортировать по "горячести" (комбинация критериев)
```

### Обновление UserStats

```
При каждой сделке (buy/sell):
  update_prediction_stats.delay(user_id)

При каждой резолюции:
  update_prediction_stats.delay(user_id) для всех участников

Celery задача update_prediction_stats(user_id):
  stats = user.stats

  positions = UserPosition.objects.filter(user_id=user_id)

  # Все предсказания
  stats.total_predictions = positions.count()

  # Правильные (выигранные)
  stats.correct_predictions = positions.filter(
    is_settled=True,
    outcome__is_winner=True,
  ).count()

  # Точность
  settled = positions.filter(is_settled=True).count()
  if settled > 0:
    stats.prediction_accuracy = (
      stats.correct_predictions / settled * 100
    )

  stats.save()
```

### Виджеты для главной страницы DOD

```
На главной странице сайта (/):

  Секция "📊 Популярные предсказания":
    3-4 карточки горячих маркетов
    HTMX: hx-get="/api/predictions/hot/"
    hx-trigger="load, every 60s"

  Секция "Последние резолюции":
    2-3 карточки недавно резолвленных
    hx-get="/api/predictions/resolved/"
```

### Критерий готовности шага 7.6

```
□ Лидерборд: топ по прибыли, точности, объёму
□ Фильтрация по периоду (неделя, месяц, всё время)
□ Приватность в лидерборде
□ Показ позиции текущего пользователя
□ Автопометка горячих маркетов (Celery)
□ Критерии горячести настраиваемы
□ UserStats обновляется при каждой сделке/резолюции
□ Виджеты на главной странице
□ Кеширование лидерборда в Redis
□ Cleanup старых PriceHistory (Celery)
□ Все периодические задачи настроены в Celery Beat
```

---

## 📊 ОБЩИЙ ЧЕКЛИСТ ЭТАПА 7

```
МОДЕЛИ:
  □ Category (10 предзаполненных)
  □ Market (все поля + методы)
  □ Outcome (бинарный + множественный)
  □ AMMPool (CPMM)
  □ UserPosition
  □ Trade
  □ PriceHistory
  □ Comment + CommentLike
  □ MarketActivity
  □ Dispute

СОЗДАНИЕ МАРКЕТОВ:
  □ Форма создания (модератор)
  □ Бинарные маркеты (YES/NO)
  □ Множественные маркеты (2-20 исходов)
  □ Настройка начальных вероятностей
  □ Настройка ликвидности
  □ Черновики + публикация
  □ Редактирование с ограничениями
  □ Отмена маркета

ТОРГОВАЯ СИСТЕМА:
  □ AMM (CPMM) ценообразование
  □ Покупка долей (buy_shares)
  □ Продажа долей (sell_shares)
  □ Комиссия платформы
  □ Расчёт slippage
  □ Превью сделки
  □ Атомарные транзакции
  □ Связь с кошельком (списание/зачисление)
  □ UserPosition: avg_buy_price, P&L
  □ Проверка лимитов (trust level)

РЕЗОЛЮЦИЯ:
  □ Закрытие торгов (авто + вручную)
  □ Выбор выигрышного исхода (модератор)
  □ Выплата $1.00 за выигрышную долю
  □ Обнуление проигрышных позиций
  □ Уведомления всем участникам
  □ Отмена маркета (возврат средств)
  □ Оспаривание результата
  □ Нельзя резолвить свой маркет / с позицией

ФРОНТЕНД:
  □ Главная predictions: категории, горячие, поиск
  □ Страница маркета: полная информация
  □ Торговая панель (HTMX)
  □ График цен (Lightweight Charts)
  □ Лента активности
  □ Комментарии + лайки + ответы
  □ Мои позиции: активные + история
  □ Лидерборд

АВТОМАТИЗАЦИЯ (CELERY):
  □ Автозакрытие по дедлайну (каждую минуту)
  □ Обновление PriceHistory (каждую минуту)
  □ Автопометка горячих маркетов (каждые 15 мин)
  □ Обновление лидерборда (каждый час)
  □ Напоминание о pending резолюции (каждые 6ч)
  □ Cleanup PriceHistory (ежедневно)
  □ Обновление UserStats

БЕЗОПАСНОСТЬ:
  □ Rate limiting на сделки
  □ Проверка баланса
  □ Проверка trust level лимитов
  □ CSRF на всех формах
  □ Атомарность транзакций
  □ Модерация комментариев
  □ AdminActionLog для всех действий

ИНТЕРФЕЙС:
  □ Тёмная тема DOD
  □ HTMX интерактивность
  □ Мобильная адаптация
  □ Обновление цен в реальном времени (polling)
  □ Bottom sheet для торговли на мобильных
```

---

```
╔══════════════════════════════════════════════════════╗
║                                                      ║
║   ЭТАП 7 ЗАВЕРШЁН                                   ║
║                                                      ║
║   Следующий: ЭТАП 8                                 ║
║   Партнёрская программа (реферальная система)       ║
║                                                      ║
║   Продолжить?                                       ║
║                                                      ║
╚══════════════════════════════════════════════════════╝
```