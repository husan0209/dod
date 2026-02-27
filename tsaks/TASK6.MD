

# 📋 ТЗ ПРОЕКТА DOD — ЭТАП 6

# PREDICTION MARKET (МАРКЕТЫ ПРЕДСКАЗАНИЙ)

```
╔══════════════════════════════════════════════════════╗
║                                                      ║
║   ПРОЕКТ:    DOD                                    ║
║   ЭТАП:      6 из 12                                ║
║   НАЗВАНИЕ:  Prediction Market                      ║
║   ЗАВИСИТ:   Этапы 1-5                              ║
║                                                      ║
║   ЦЕЛЬ:      Маркеты предсказаний как Polymarket.   ║
║              Пользователи покупают акции YES/NO.    ║
║              Цена отражает вероятность события.     ║
║              AMM для автоматического ценообразования.║
║              Модератор создаёт и резолвит маркеты.  ║
║              Комментарии, графики, портфель.        ║
║                                                      ║
╚══════════════════════════════════════════════════════╝
```

---

## 📌 КОНТЕКСТ ДЛЯ ИИ-АГЕНТА

```
Ты продолжаешь разработку проекта DOD.
Этапы 1-5 готовы.

Prediction Market — это рынок предсказаний.

КАК ЭТО РАБОТАЕТ:

  1. Модератор создаёт маркет:
     Вопрос: "Bitcoin достигнет $200K до конца 2025?"

  2. Два исхода: YES и NO
     Цена YES + цена NO = всегда $1.00
     Если YES стоит $0.70 → рынок считает вероятность 70%

  3. Пользователи покупают акции:
     Купить YES за $0.70 → если да, получишь $1.00 (+$0.30)
     Купить NO за $0.30 → если нет, получишь $1.00 (+$0.70)

  4. Цена меняется по формуле AMM:
     Больше покупают YES → цена YES растёт
     Больше покупают NO → цена NO растёт

  5. Модератор резолвит маркет:
     Событие произошло → YES = $1.00, NO = $0.00
     Не произошло → YES = $0.00, NO = $1.00
     Все позиции автоматически рассчитываются

  AMM ФОРМУЛА (Constant Product Market Maker):
     yes_pool × no_pool = K (константа)
     Цена YES = no_pool / (yes_pool + no_pool)
     Цена NO = yes_pool / (yes_pool + no_pool)

  ВАЖНО:
     Все деньги через TransactionService
     Покупка акций → списание из кошелька
     Продажа акций → зачисление в кошелёк
     Резолвинг → автоматическое зачисление выигрышей
```

---

## ШАГ 6.1 — МОДЕЛИ PREDICTION MARKET

### Структура приложения

```
apps/predictions/
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
│   ├── market_service.py         # Создание, управление
│   ├── amm_service.py            # AMM ценообразование
│   ├── trading_service.py        # Покупка/продажа
│   ├── resolution_service.py     # Резолвинг маркетов
│   └── analytics_service.py      # Аналитика, графики
├── templatetags/
│   ├── __init__.py
│   └── prediction_tags.py
├── tests/
│   └── ...
├── templates/
│   └── predictions/
│       ├── index.html
│       ├── market_detail.html
│       ├── create_market.html
│       ├── portfolio.html
│       ├── leaderboard.html
│       ├── history.html
│       └── components/
│           ├── market_card.html
│           ├── price_chart.html
│           ├── trade_form.html
│           ├── order_book.html
│           ├── comments.html
│           └── position_card.html
└── migrations/
    └── __init__.py
```

### Модель MarketCategory (models.py)

```
class MarketCategory(models.Model):

    Назначение:
      Категория маркетов предсказаний.

    Поля:
    ─────
    id:
      тип: AutoField

    name:
      тип: CharField, max 100
      'Политика', 'Криптовалюты', 'Спорт'

    name_en:
      тип: CharField, max 100
      'Politics', 'Crypto', 'Sports'

    slug:
      тип: SlugField, уникальный

    icon:
      тип: CharField, max 50
      '🏛️', '₿', '⚽', '💻', '🌍', '🎬'

    description:
      тип: TextField, nullable

    color:
      тип: CharField, max 7
      HEX цвет: '#FF6B6B', '#4ECDC4'

    markets_count:
      тип: IntegerField, default=0

    sort_order:
      тип: IntegerField, default=0

    is_active:
      тип: BooleanField, default=True

    Meta:
      ordering = ['sort_order']

    Начальные данные:
      🏛️ Политика (politics)
      ₿ Криптовалюты (crypto)
      ⚽ Спорт (sports)
      💻 Технологии (technology)
      🌍 Мировые события (world)
      📈 Экономика (economy)
      🎬 Развлечения (entertainment)
      🔬 Наука (science)
      🎮 Игры (gaming)
      📱 Социальные сети (social)
```

### Модель PredictionMarket (models.py)

```
class PredictionMarket(models.Model):

    Назначение:
      Маркет предсказания.
      Центральная модель.
      "Bitcoin достигнет $200K до конца 2025?"

    Поля:
    ─────
    id:
      тип: UUID, primary key

    market_id:
      тип: CharField, max 50, уникальный
      Формат: PM-{timestamp}-{random6}
      Пример: PM-20250315-A7B3C2

    question:
      тип: CharField, max 500
      Вопрос маркета
      "Bitcoin достигнет $200K до конца 2025?"
      Должен быть однозначно интерпретируемым
      Должен иметь чёткий ответ YES или NO

    question_en:
      тип: CharField, max 500, nullable

    description:
      тип: TextField
      Подробное описание и правила резолвинга
      "Маркет будет разрешён как YES, если цена BTC
       на CoinGecko превысит $200,000 хотя бы на
       одну минуту до 31 декабря 2025 23:59 UTC."

    description_en:
      тип: TextField, nullable

    category:
      тип: ForeignKey → MarketCategory
      related_name: 'markets'

    thumbnail:
      тип: ImageField, nullable
      Превью изображение маркета

    source_url:
      тип: URLField, nullable
      Ссылка на источник для проверки результата
      "https://www.coingecko.com/en/coins/bitcoin"

    resolution_source:
      тип: TextField, nullable
      Описание как будет определён результат
      "Цена BTC на CoinGecko API"

    tags:
      тип: JSONField, default=list
      Теги: ["bitcoin", "crypto", "price"]

    created_by:
      тип: ForeignKey → User
      Кто создал маркет (модератор/админ)

    status:
      тип: CharField
      choices:
        ('draft', 'Черновик')
        ('pending_review', 'На модерации')
        ('active', 'Активный')
        ('trading_halted', 'Торги приостановлены')
        ('pending_resolution', 'Ожидает резолвинга')
        ('resolved', 'Разрешён')
        ('voided', 'Аннулирован')
        ('disputed', 'Оспаривается')
      default: 'draft'

    resolution:
      тип: CharField, nullable
      choices:
        ('yes', 'YES')
        ('no', 'NO')
      Заполняется при резолвинге

    resolved_by:
      тип: ForeignKey → User, nullable
      Кто резолвил

    resolved_at:
      тип: DateTimeField, nullable

    resolution_evidence:
      тип: TextField, nullable
      Доказательства при резолвинге
      "Цена BTC достигла $201,345 15 марта 2025
       в 14:32 UTC (скриншот + API данные)"

    resolution_evidence_url:
      тип: URLField, nullable
      Ссылка на доказательство

    close_date:
      тип: DateTimeField
      Дата закрытия торгов
      После этой даты нельзя покупать/продавать

    resolution_date:
      тип: DateTimeField
      Ожидаемая дата резолвинга
      Может отличаться от close_date

    yes_pool:
      тип: DecimalField, max_digits=18, decimal_places=8
      Пул YES в AMM
      Начальное значение = initial_liquidity

    no_pool:
      тип: DecimalField, max_digits=18, decimal_places=8
      Пул NO в AMM

    constant_k:
      тип: DecimalField, max_digits=36, decimal_places=16
      K = yes_pool × no_pool
      Константа AMM

    initial_liquidity:
      тип: DecimalField
      Начальная ликвидность (в USD)
      default=10000
      Определяет глубину рынка

    yes_price:
      тип: DecimalField, max_digits=10, decimal_places=4
      Текущая цена YES ($0.0001 - $0.9999)
      Кэшируется, пересчитывается при каждой сделке

    no_price:
      тип: DecimalField, max_digits=10, decimal_places=4
      Текущая цена NO

    volume_usd:
      тип: DecimalField, default=0
      Общий объём торгов (USD)

    volume_24h_usd:
      тип: DecimalField, default=0
      Объём за последние 24 часа

    trades_count:
      тип: IntegerField, default=0
      Общее количество сделок

    unique_traders:
      тип: IntegerField, default=0
      Уникальные трейдеры

    yes_holders:
      тип: IntegerField, default=0
      Количество держателей YES

    no_holders:
      тип: IntegerField, default=0
      Количество держателей NO

    total_yes_shares:
      тип: DecimalField, default=0
      Всего выпущено YES акций

    total_no_shares:
      тип: DecimalField, default=0
      Всего выпущено NO акций

    liquidity_usd:
      тип: DecimalField, default=0
      Текущая ликвидность (USD)

    is_featured:
      тип: BooleanField, default=False
      Показывать на главной

    is_trending:
      тип: BooleanField, default=False
      В трендах

    views_count:
      тип: IntegerField, default=0

    comments_count:
      тип: IntegerField, default=0

    likes_count:
      тип: IntegerField, default=0

    sort_order:
      тип: IntegerField, default=0

    created_at:
      тип: DateTimeField, auto_now_add

    updated_at:
      тип: DateTimeField, auto_now

    Методы:
    ───────
    __str__():
      return self.question[:80]

    is_tradeable():
      return (
        self.status == 'active'
        and self.close_date > now()
      )

    is_closed():
      return self.close_date <= now() or self.status != 'active'

    is_resolved():
      return self.status == 'resolved'

    get_yes_probability():
      return float(self.yes_price) * 100
      # 0.70 → 70%

    get_no_probability():
      return float(self.no_price) * 100

    get_time_until_close():
      return self.close_date - now()
      # "через 5 дней"

    get_implied_odds():
      # Конвертация в букмекерские коэффициенты
      return {
        "yes": round(1 / float(self.yes_price), 2),
        "no": round(1 / float(self.no_price), 2)
      }
      # yes_price=0.70 → odd=1.43
      # no_price=0.30 → odd=3.33

    recalculate_prices():
      total = self.yes_pool + self.no_pool
      self.yes_price = self.no_pool / total
      self.no_price = self.yes_pool / total

    Meta:
      verbose_name = 'Маркет предсказания'
      ordering = ['-is_featured', '-volume_24h_usd', '-created_at']
      indexes:
        - status + close_date
        - category + status
        - is_featured
        - is_trending
        - created_at
        - volume_24h_usd
```

### Модель Position (models.py)

```
class Position(models.Model):

    Назначение:
      Позиция пользователя в маркете.
      Сколько акций YES или NO он держит.

    Поля:
    ─────
    id:
      тип: UUID, primary key

    user:
      тип: ForeignKey → User
      related_name: 'prediction_positions'

    market:
      тип: ForeignKey → PredictionMarket
      related_name: 'positions'

    side:
      тип: CharField
      choices: [('yes', 'YES'), ('no', 'NO')]

    shares:
      тип: DecimalField, max_digits=18, decimal_places=8
      Количество акций
      НЕ МОЖЕТ быть отрицательным

    avg_price:
      тип: DecimalField, max_digits=10, decimal_places=4
      Средняя цена покупки

    total_invested:
      тип: DecimalField
      Всего вложено (USD)

    total_returned:
      тип: DecimalField, default=0
      Всего получено обратно (от продаж)

    realized_pnl:
      тип: DecimalField, default=0
      Реализованный PnL (от продаж)

    is_settled:
      тип: BooleanField, default=False
      Рассчитана ли позиция после резолвинга

    settlement_amount:
      тип: DecimalField, default=0
      Сколько получил при резолвинге

    created_at:
      тип: DateTimeField, auto_now_add

    updated_at:
      тип: DateTimeField, auto_now

    Методы:
    ───────
    current_value():
      Текущая стоимость позиции
      if side == 'yes':
        return shares × market.yes_price
      else:
        return shares × market.no_price

    unrealized_pnl():
      return current_value() - total_invested + total_returned

    total_pnl():
      return realized_pnl + unrealized_pnl()

    pnl_percent():
      if total_invested == 0: return 0
      return (total_pnl() / total_invested) × 100

    potential_payout():
      # Если маркет разрешится в пользу этой стороны
      return shares × 1.00  # Каждая акция = $1.00

    Meta:
      unique_together = ['user', 'market', 'side']
      verbose_name = 'Позиция'
```

### Модель Trade (models.py)

```
class Trade(models.Model):

    Назначение:
      Каждая сделка (покупка/продажа акций).
      Журнал всех торговых операций.
      Неизменяемый.

    Поля:
    ─────
    id:
      тип: UUID, primary key

    trade_id:
      тип: CharField, max 50, уникальный
      Формат: TRD-{timestamp}-{random6}

    user:
      тип: ForeignKey → User

    market:
      тип: ForeignKey → PredictionMarket
      related_name: 'trades'

    position:
      тип: ForeignKey → Position, nullable

    action:
      тип: CharField
      choices:
        ('buy', 'Покупка')
        ('sell', 'Продажа')

    side:
      тип: CharField
      choices: [('yes', 'YES'), ('no', 'NO')]

    shares:
      тип: DecimalField
      Количество акций

    price:
      тип: DecimalField
      Цена за акцию на момент сделки

    total_cost:
      тип: DecimalField
      Общая стоимость сделки
      buy: сколько заплатил
      sell: сколько получил

    fee_amount:
      тип: DecimalField, default=0
      Комиссия платформы

    price_before:
      тип: DecimalField
      Цена ДО сделки

    price_after:
      тип: DecimalField
      Цена ПОСЛЕ сделки

    yes_price_after:
      тип: DecimalField

    no_price_after:
      тип: DecimalField

    transaction:
      тип: ForeignKey → Transaction, nullable
      Связь с транзакцией кошелька

    ip_address:
      тип: GenericIPAddressField

    created_at:
      тип: DateTimeField, auto_now_add

    Meta:
      verbose_name = 'Сделка'
      ordering = ['-created_at']
      indexes:
        - market + created_at
        - user + created_at
```

### Модель PriceHistory (models.py)

```
class PriceHistory(models.Model):

    Назначение:
      История цен для построения графиков.
      Записывается каждые 15 минут + при каждой сделке.

    Поля:
    ─────
    id:
      тип: BigAutoField

    market:
      тип: ForeignKey → PredictionMarket
      related_name: 'price_history'

    yes_price:
      тип: DecimalField

    no_price:
      тип: DecimalField

    volume:
      тип: DecimalField, default=0
      Объём за период

    source:
      тип: CharField
      choices:
        ('trade', 'Сделка')
        ('periodic', 'Периодическая запись')

    timestamp:
      тип: DateTimeField, auto_now_add

    Meta:
      ordering = ['-timestamp']
      indexes:
        - market + timestamp
```

### Модель MarketComment (models.py)

```
class MarketComment(models.Model):

    Назначение:
      Комментарии пользователей под маркетом.
      Обсуждение, аргументы за и против.

    Поля:
    ─────
    id:
      тип: UUID, primary key

    market:
      тип: ForeignKey → PredictionMarket
      related_name: 'comments'

    user:
      тип: ForeignKey → User
      related_name: 'market_comments'

    parent:
      тип: ForeignKey → self, nullable
      Для ответов на комментарии (вложенность)

    text:
      тип: TextField
      Максимум 2000 символов

    side_prediction:
      тип: CharField, nullable
      choices: [('yes', 'YES'), ('no', 'NO')]
      Мнение автора (необязательно)
      Показывается бейджем: "🟢 YES" или "🔴 NO"

    likes_count:
      тип: IntegerField, default=0

    is_pinned:
      тип: BooleanField, default=False
      Закреплённый комментарий (модератор)

    is_deleted:
      тип: BooleanField, default=False
      Мягкое удаление

    created_at:
      тип: DateTimeField, auto_now_add

    updated_at:
      тип: DateTimeField, auto_now

    Meta:
      ordering = ['-is_pinned', '-likes_count', '-created_at']
```

### Модель MarketLike (models.py)

```
class MarketLike(models.Model):

    market:
      тип: ForeignKey → PredictionMarket
    user:
      тип: ForeignKey → User
    created_at:
      тип: DateTimeField, auto_now_add

    Meta:
      unique_together = ['market', 'user']
```

### Модель CommentLike (models.py)

```
class CommentLike(models.Model):

    comment:
      тип: ForeignKey → MarketComment
    user:
      тип: ForeignKey → User
    created_at:
      тип: DateTimeField, auto_now_add

    Meta:
      unique_together = ['comment', 'user']
```

### Модель MarketDispute (models.py)

```
class MarketDispute(models.Model):

    Назначение:
      Оспаривание результата маркета.
      Если пользователь не согласен с резолвингом.

    Поля:
    ─────
    id:
      тип: UUID, primary key

    market:
      тип: ForeignKey → PredictionMarket

    user:
      тип: ForeignKey → User

    reason:
      тип: TextField
      Причина оспаривания

    evidence_url:
      тип: URLField, nullable

    status:
      тип: CharField
      choices:
        ('pending', 'На рассмотрении')
        ('accepted', 'Принято')
        ('rejected', 'Отклонено')
      default: 'pending'

    reviewed_by:
      тип: ForeignKey → User, nullable

    review_comment:
      тип: TextField, nullable

    created_at:
      тип: DateTimeField, auto_now_add

    Meta:
      verbose_name = 'Оспаривание'
```

### Модель PredictionSettings (models.py)

```
class PredictionSettings(models.Model):

    Назначение:
      Глобальные настройки Prediction Market.
      Singleton.

    Поля:
    ─────
    is_enabled:
      тип: BooleanField, default=True

    trading_fee_percent:
      тип: DecimalField
      Комиссия с каждой сделки
      default=1.0 (1%)

    min_trade_amount_usd:
      тип: DecimalField
      Минимальная сумма сделки
      default=1.00

    max_trade_amount_usd:
      тип: DecimalField
      Максимальная сумма одной сделки
      default=10000

    default_initial_liquidity:
      тип: DecimalField
      Начальная ликвидность новых маркетов
      default=10000

    max_position_usd:
      тип: DecimalField
      Максимальная позиция одного пользователя в маркете
      default=50000

    resolution_dispute_window_hours:
      тип: IntegerField
      Часы после резолвинга когда можно оспорить
      default=24

    min_market_duration_hours:
      тип: IntegerField
      Минимальная длительность маркета
      default=24

    auto_close_before_resolution_hours:
      tип: IntegerField
      За сколько часов до резолвинга закрыть торги
      default=1

    allow_user_market_proposals:
      тип: BooleanField, default=False
      Могут ли пользователи предлагать маркеты

    Meta:
      verbose_name = 'Настройки Prediction Market'
```

### Критерий готовности шага 6.1

```
□ MarketCategory (10 категорий с fixtures)
□ PredictionMarket (полная модель с AMM)
□ Position (позиции пользователей)
□ Trade (журнал сделок)
□ PriceHistory (для графиков)
□ MarketComment (с вложенностью)
□ MarketLike, CommentLike
□ MarketDispute (оспаривание)
□ PredictionSettings (singleton)
□ Все миграции
□ Admin настроен
```

---

## ШАГ 6.2 — AMM И ТОРГОВЫЕ СЕРВИСЫ

### AMMService (services/amm_service.py)

```
class AMMService:

    Назначение:
      Automated Market Maker.
      Constant Product формула: yes_pool × no_pool = K
      
      Как это работает:
        Пул начинается: yes=10000, no=10000, K=100000000
        Цена YES = no / (yes + no) = 0.5000 (50%)
        Цена NO = yes / (yes + no) = 0.5000 (50%)
        
        Кто-то покупает YES за $100:
        → $100 добавляется в no_pool
        → no_pool = 10100
        → yes_pool = K / no_pool = 100000000 / 10100 = 9900.99
        → shares = 10000 - 9900.99 = 99.01 акций YES
        → Новая цена YES = 10100 / (9900.99 + 10100) = 0.5050 (50.5%)

    Методы:
    ───────

    @staticmethod
    def calculate_buy_price(market, side, amount):
      
      Рассчитать сколько акций получит покупатель.
      НЕ ИЗМЕНЯЕТ пулы (preview).
      
      Параметры:
        market: PredictionMarket
        side: 'yes' или 'no'
        amount: сумма покупки (USD)
      
      Логика:
        if side == 'yes':
          # Добавляем деньги в no_pool
          new_no_pool = market.no_pool + amount
          new_yes_pool = market.constant_k / new_no_pool
          shares = market.yes_pool - new_yes_pool
        else:
          new_yes_pool = market.yes_pool + amount
          new_no_pool = market.constant_k / new_yes_pool
          shares = market.no_pool - new_no_pool

        avg_price = amount / shares
        
        # Новые цены после сделки
        total = new_yes_pool + new_no_pool
        new_yes_price = new_no_pool / total
        new_no_price = new_yes_pool / total

        # Price impact (насколько сделка двигает цену)
        if side == 'yes':
          price_impact = (new_yes_price - float(market.yes_price))
                          / float(market.yes_price) * 100
        else:
          price_impact = (new_no_price - float(market.no_price))
                          / float(market.no_price) * 100

        return {
          "shares": round(shares, 8),
          "avg_price": round(avg_price, 4),
          "total_cost": amount,
          "new_yes_price": round(new_yes_price, 4),
          "new_no_price": round(new_no_price, 4),
          "price_impact_percent": round(price_impact, 2),
          "potential_payout": round(shares, 2),
          "potential_profit": round(shares - amount, 2),
          "potential_roi_percent": round(
            (shares - amount) / amount * 100, 2
          )
        }


    @staticmethod
    def calculate_sell_price(market, side, shares):
      
      Рассчитать сколько получит продавец.
      НЕ ИЗМЕНЯЕТ пулы (preview).
      
      Логика:
        if side == 'yes':
          new_yes_pool = market.yes_pool + shares
          new_no_pool = market.constant_k / new_yes_pool
          payout = market.no_pool - new_no_pool
        else:
          new_no_pool = market.no_pool + shares
          new_yes_pool = market.constant_k / new_no_pool
          payout = market.yes_pool - new_yes_pool

        avg_price = payout / shares
        
        total = new_yes_pool + new_no_pool
        new_yes_price = new_no_pool / total
        new_no_price = new_yes_pool / total

        return {
          "shares_sold": shares,
          "payout": round(payout, 8),
          "avg_price": round(avg_price, 4),
          "new_yes_price": round(new_yes_price, 4),
          "new_no_price": round(new_no_price, 4)
        }


    @staticmethod
    def execute_buy(market, side, amount):
      
      Выполнить покупку. ИЗМЕНЯЕТ пулы.
      Вызывается ТОЛЬКО из TradingService (внутри atomic).
      
      Логика:
        preview = calculate_buy_price(market, side, amount)
        
        if side == 'yes':
          market.no_pool += Decimal(str(amount))
          market.yes_pool = market.constant_k / market.no_pool
        else:
          market.yes_pool += Decimal(str(amount))
          market.no_pool = market.constant_k / market.yes_pool
        
        market.recalculate_prices()
        market.save()
        
        return preview


    @staticmethod
    def execute_sell(market, side, shares):
      
      Выполнить продажу. ИЗМЕНЯЕТ пулы.
      
      Логика:
        preview = calculate_sell_price(market, side, shares)
        
        if side == 'yes':
          market.yes_pool += Decimal(str(shares))
          market.no_pool = market.constant_k / market.yes_pool
        else:
          market.no_pool += Decimal(str(shares))
          market.yes_pool = market.constant_k / market.no_pool
        
        market.recalculate_prices()
        market.save()
        
        return preview
```

### TradingService (services/trading_service.py)

```
class TradingService:

    Назначение:
      Покупка и продажа акций.
      Связывает AMM с кошельком.

    Методы:
    ───────

    @staticmethod
    def buy_shares(user, market_id, side, amount,
                    currency_code, ip_address):
      
      Купить акции YES или NO.
      
      Логика (АТОМАРНО — select_for_update):

        1. ВАЛИДАЦИЯ:
           - market.is_tradeable()
           - PredictionSettings.is_enabled
           - amount >= min_trade_amount
           - amount <= max_trade_amount
           - side in ('yes', 'no')
           - Баланс достаточный
           - Позиция не превысит max_position

        2. РАССЧИТАТЬ КОМИССИЮ:
           fee = amount × trading_fee_percent / 100
           net_amount = amount - fee

        3. РАССЧИТАТЬ ПОКУПКУ (AMM):
           market = PredictionMarket.select_for_update()
           result = AMMService.execute_buy(market, side, net_amount)
           shares = result['shares']

        4. СПИСАТЬ ДЕНЬГИ:
           tx = TransactionService.withdraw(
             wallet=user.wallet,
             currency=currency_code,
             amount=amount,  # полная сумма включая комиссию
             type='bet',
             description=f"Покупка {shares:.2f} {side.upper()} "
                        f"акций: {market.question[:50]}",
             reference_type='prediction_trade'
           )

        5. ОБНОВИТЬ ПОЗИЦИЮ:
           position, created = Position.get_or_create(
             user=user, market=market, side=side
           )
           
           if not created:
             # Средневзвешенная цена
             total_shares = position.shares + shares
             position.avg_price = (
               (position.avg_price × position.shares +
                result['avg_price'] × shares) / total_shares
             )
           else:
             position.avg_price = result['avg_price']
           
           position.shares += shares
           position.total_invested += amount
           position.save()

        6. СОЗДАТЬ TRADE:
           Trade.create(
             trade_id=generate_id("TRD"),
             user=user,
             market=market,
             position=position,
             action='buy',
             side=side,
             shares=shares,
             price=result['avg_price'],
             total_cost=amount,
             fee_amount=fee,
             price_before=old_price,
             price_after=result[f'{side}_price_after'],
             yes_price_after=result['new_yes_price'],
             no_price_after=result['new_no_price'],
             transaction=tx,
             ip_address=ip_address
           )

        7. ОБНОВИТЬ СТАТИСТИКУ:
           market.volume_usd += amount
           market.trades_count += 1
           market.save()

        8. ЗАПИСАТЬ ИСТОРИЮ ЦЕН:
           PriceHistory.create(
             market=market,
             yes_price=market.yes_price,
             no_price=market.no_price,
             volume=amount,
             source='trade'
           )

        9. ВЕРНУТЬ:
           {
             "trade_id": trade.trade_id,
             "shares": shares,
             "avg_price": result['avg_price'],
             "total_cost": amount,
             "fee": fee,
             "new_yes_price": market.yes_price,
             "new_no_price": market.no_price,
             "position_shares": position.shares,
             "potential_payout": shares,
             "message": f"✅ Куплено {shares:.2f} {side.upper()} акций"
           }


    @staticmethod
    def sell_shares(user, market_id, side, shares,
                     currency_code, ip_address):
      
      Продать акции YES или NO.
      
      Логика (АТОМАРНО):

        1. ВАЛИДАЦИЯ:
           - market.is_tradeable()
           - position = Position.get(user, market, side)
           - position.shares >= shares
           - shares > 0

        2. РАССЧИТАТЬ ПРОДАЖУ (AMM):
           market = PredictionMarket.select_for_update()
           result = AMMService.execute_sell(market, side, shares)
           payout = result['payout']

        3. РАССЧИТАТЬ КОМИССИЮ:
           fee = payout × trading_fee_percent / 100
           net_payout = payout - fee

        4. ЗАЧИСЛИТЬ ДЕНЬГИ:
           tx = TransactionService.deposit(
             wallet=user.wallet,
             currency=currency_code,
             amount=net_payout,
             type='win',
             description=f"Продажа {shares:.2f} {side.upper()} "
                        f"акций: {market.question[:50]}",
             reference_type='prediction_trade'
           )

        5. ОБНОВИТЬ ПОЗИЦИЮ:
           position.shares -= shares
           position.total_returned += net_payout
           
           # Реализованный PnL
           cost_basis = position.avg_price × shares
           position.realized_pnl += net_payout - cost_basis
           
           if position.shares <= 0:
             position.shares = 0
           
           position.save()

        6. СОЗДАТЬ TRADE (action='sell')

        7. ОБНОВИТЬ СТАТИСТИКУ

        8. ВЕРНУТЬ результат


    @staticmethod
    def preview_buy(market_id, side, amount):
      
      Предпросмотр покупки (без выполнения).
      Для HTMX: показать сколько получит.
      
      market = PredictionMarket.get(id=market_id)
      return AMMService.calculate_buy_price(market, side, amount)


    @staticmethod
    def preview_sell(market_id, side, shares):
      
      Предпросмотр продажи.
      
      market = PredictionMarket.get(id=market_id)
      return AMMService.calculate_sell_price(market, side, shares)
```

### ResolutionService (services/resolution_service.py)

```
class ResolutionService:

    Назначение:
      Резолвинг маркетов и расчёт позиций.

    Методы:
    ───────

    @staticmethod
    def resolve_market(market_id, resolution, resolved_by,
                        evidence, evidence_url=None):
      
      Разрешить маркет.
      resolution: 'yes' или 'no'
      
      Логика (АТОМАРНО):

        1. market = PredictionMarket.select_for_update()
        2. Проверить: status in ('active', 'pending_resolution')
        3. market.status = 'resolved'
        4. market.resolution = resolution
        5. market.resolved_by = resolved_by
        6. market.resolved_at = now
        7. market.resolution_evidence = evidence
        8. market.resolution_evidence_url = evidence_url
        9. market.yes_price = 1.00 if resolution == 'yes' else 0.00
        10. market.no_price = 0.00 if resolution == 'yes' else 1.00

        11. РАССЧИТАТЬ ВСЕ ПОЗИЦИИ:
            settle_all_positions(market)

        12. Уведомить всех трейдеров


    @staticmethod
    def settle_all_positions(market):
      
      Рассчитать все позиции после резолвинга.
      
      Логика:
        winning_side = market.resolution  # 'yes' или 'no'
        
        positions = Position.filter(
          market=market, shares__gt=0, is_settled=False
        )
        
        for position in positions:
          
          if position.side == winning_side:
            # ВЫИГРЫШ: каждая акция = $1.00
            payout = position.shares × 1.00
            
            TransactionService.deposit(
              wallet=position.user.wallet,
              currency_code='USD',
              amount=payout,
              type='win',
              description=f"Prediction Market: {market.question[:50]} "
                         f"→ {winning_side.upper()}",
              reference_type='prediction_resolution',
              reference_id=market.market_id
            )
            
            position.settlement_amount = payout
          
          else:
            # ПРОИГРЫШ: акции = $0.00
            position.settlement_amount = 0
          
          position.is_settled = True
          position.save()

          # Уведомить
          if position.settlement_amount > 0:
            notify(position.user,
              f"🏆 Маркет разрешён! Вы получили "
              f"${position.settlement_amount:.2f}")
          else:
            notify(position.user,
              f"❌ Маркет разрешён как {winning_side.upper()}. "
              f"Ваши {position.side.upper()} акции = $0")


    @staticmethod
    def void_market(market_id, admin_user, reason):
      
      Аннулировать маркет (вернуть всем деньги).
      
      Логика:
        1. market.status = 'voided'
        2. Для каждой позиции:
           Вернуть total_invested - total_returned
           (то что ещё вложено)
        3. Уведомить всех


    @staticmethod
    def dispute_resolution(market_id, user, reason, evidence_url):
      
      Оспорить результат.
      
      Логика:
        1. Проверить: market.status == 'resolved'
        2. Проверить: now < resolved_at + dispute_window
        3. Проверить: user имеет позицию в маркете
        4. Создать MarketDispute
        5. market.status = 'disputed'
        6. Уведомить админов
```

### MarketService (services/market_service.py)

```
class MarketService:

    Методы:
    ───────

    @staticmethod
    def create_market(question, description, category_id,
                       close_date, resolution_date,
                       initial_liquidity, created_by,
                       thumbnail=None, source_url=None,
                       resolution_source=None, tags=None,
                       question_en=None, description_en=None):
      
      Создать новый маркет.
      
      Логика:
        1. Валидация:
           - question не пустой, <= 500 символов
           - close_date > now + min_market_duration
           - resolution_date >= close_date
           - initial_liquidity > 0
           - category существует

        2. Создать маркет:
           yes_pool = initial_liquidity
           no_pool = initial_liquidity
           constant_k = yes_pool × no_pool
           yes_price = 0.5000 (начальная 50/50)
           no_price = 0.5000
           status = 'active' (если создал админ/модератор)
                    'pending_review' (если пользователь предложил)

        3. Обновить category.markets_count

        4. Записать начальную PriceHistory

        5. Вернуть маркет


    @staticmethod
    def get_trending_markets(limit=10):
      
      Трендовые маркеты.
      
      Критерии:
        - status == 'active'
        - Сортировка по volume_24h_usd DESC
        - Или по изменению цены за 24 часа


    @staticmethod
    def get_closing_soon(limit=10):
      
      Маркеты которые скоро закрываются.
      close_date в ближайшие 48 часов.


    @staticmethod
    def get_recently_resolved(limit=10):
      
      Недавно разрешённые.
      resolved_at за последние 7 дней.


    @staticmethod
    def search_markets(query, category=None, status=None):
      
      Поиск по вопросу, тегам, описанию.


    @staticmethod
    def close_expired_markets():
      
      Celery задача.
      Маркеты где close_date < now и status == 'active':
        → status = 'pending_resolution'
```

### AnalyticsService (services/analytics_service.py)

```
class AnalyticsService:

    @staticmethod
    def get_user_portfolio(user):
      
      Портфель пользователя.
      
      Возвращает:
        {
          "total_invested": 1500.00,
          "current_value": 1750.00,
          "total_pnl": +250.00,
          "total_pnl_percent": +16.67,
          "realized_pnl": +100.00,
          "unrealized_pnl": +150.00,
          "active_positions": [
            {
              "market": "Bitcoin $200K?",
              "side": "YES",
              "shares": 100,
              "avg_price": 0.65,
              "current_price": 0.78,
              "invested": 65.00,
              "current_value": 78.00,
              "pnl": +13.00,
              "pnl_percent": +20.0,
              "potential_payout": 100.00
            },
            ...
          ],
          "settled_positions": [...],
          "total_trades": 47,
          "win_rate": 62.5
        }


    @staticmethod
    def get_market_chart_data(market_id, period='7d'):
      
      Данные для графика цены.
      
      Возвращает:
        {
          "timestamps": [...],
          "yes_prices": [...],
          "no_prices": [...],
          "volumes": [...]
        }


    @staticmethod
    def get_leaderboard(period='all'):
      
      Таблица лидеров.
      
      Возвращает:
        [
          {"rank": 1, "user": "Us***", "pnl": +5000, "trades": 200, "win_rate": 68},
          {"rank": 2, "user": "An***", "pnl": +3200, ...},
          ...
        ]
```

### Критерий готовности шага 6.2

```
□ AMMService: calculate_buy, calculate_sell, execute_buy, execute_sell
□ TradingService: buy_shares, sell_shares, preview_buy, preview_sell
□ ResolutionService: resolve, settle_positions, void, dispute
□ MarketService: create, trending, closing_soon, search
□ AnalyticsService: portfolio, chart_data, leaderboard
□ Все операции атомарные
□ Все деньги через TransactionService
□ Комиссии рассчитываются
□ Позиции обновляются корректно
□ PriceHistory записывается
□ Уведомления при резолвинге
```

---

## ШАГ 6.3 — СТРАНИЦЫ PREDICTION MARKET

### Главная

```
URL: /predictions/

  ┌──────────────────────────────────────────────────────────┐
  │  📊 Prediction Market                                   │
  │                                                          │
  │  Категории:                                             │
  │  [Все] [🏛️Политика] [₿Крипто] [⚽Спорт] [💻Технол.]  │
  │  [🌍Мир] [📈Эконом.] [🎬Развлеч.] [🔬Наука]          │
  │                                                          │
  │  [🔥Трендовые] [⏰Закрываются скоро] [✅Разрешённые]  │
  │                                                          │
  │  Поиск: [________________________________] [🔍]        │
  │                                                          │
  │  ── 🔥 Трендовые маркеты ────────────────────────────  │
  │                                                          │
  │  ┌──────────────────────────────────────────────────┐   │
  │  │ ₿ Крипто                                        │   │
  │  │                                                  │   │
  │  │ Bitcoin достигнет $200K до конца 2025?           │   │
  │  │                                                  │   │
  │  │ ┌──────────────┐  ┌──────────────┐              │   │
  │  │ │  🟢 YES      │  │  🔴 NO       │              │   │
  │  │ │  $0.72 (72%) │  │  $0.28 (28%) │              │   │
  │  │ │  [Купить]    │  │  [Купить]    │              │   │
  │  │ └──────────────┘  └──────────────┘              │   │
  │  │                                                  │   │
  │  │ 📊 Объём: $45,230  👥 342 трейдера              │   │
  │  │ ⏰ Закрытие: 15 дек 2025                        │   │
  │  │                                                  │   │
  │  │ [────────────────●──────] мини-график цены      │   │
  │  │                                                  │   │
  │  └──────────────────────────────────────────────────┘   │
  │                                                          │
  │  ┌──────────────────────────────────────────────────┐   │
  │  │ 🏛️ Политика                                     │   │
  │  │ Трамп выиграет выборы 2028?                     │   │
  │  │ 🟢 YES $0.35 (35%)  🔴 NO $0.65 (65%)         │   │
  │  │ 📊 $23,100  👥 189                              │   │
  │  └──────────────────────────────────────────────────┘   │
  │                                                          │
  │  [Показать больше...]                                   │
  │                                                          │
  └──────────────────────────────────────────────────────────┘

  HTMX:
    Категории: hx-get="/predictions/?category=crypto"
    Фильтры: hx-get="/predictions/?filter=trending"
    Поиск: hx-get="/predictions/?q=bitcoin"
    Все обновляют #markets-list без перезагрузки
```

### Детальная страница маркета

```
URL: /predictions/{market_id}/

  ┌──────────────────────────────────────────────────────────┐
  │                                                          │
  │  ₿ Крипто > Bitcoin                                     │
  │                                                          │
  │  Bitcoin достигнет $200K до конца 2025?                 │
  │                                                          │
  │  ┌────────────────────────────────────────────────────┐ │
  │  │                                                    │ │
  │  │  🟢 YES: $0.72 (72%)    🔴 NO: $0.28 (28%)       │ │
  │  │                                                    │ │
  │  │  ┌────────────────────────────────────────────┐   │ │
  │  │  │         📈 ГРАФИК ЦЕНЫ                     │   │ │
  │  │  │                           _/\              │   │ │
  │  │  │                     ___/\/    \            │   │ │
  │  │  │                 ___/           \_          │   │ │
  │  │  │            ___/                  \_       │   │ │
  │  │  │   0.50 ___/                       \__    │   │ │
  │  │  │  /                                       │   │ │
  │  │  │ [1Д] [7Д] [1М] [3М] [Всё]              │   │ │
  │  │  └────────────────────────────────────────────┘   │ │
  │  │                                                    │ │
  │  │  📊 Объём: $45,230                               │ │
  │  │  📊 24ч: $3,450                                  │ │
  │  │  👥 Трейдеров: 342                               │ │
  │  │  🟢 YES холдеров: 210                            │ │
  │  │  🔴 NO холдеров: 132                             │ │
  │  │  ⏰ Закрытие: 15 дек 2025 (через 275 дней)      │ │
  │  │  💰 Ликвидность: $10,000                        │ │
  │  │                                                    │ │
  │  └────────────────────────────────────────────────────┘ │
  │                                                          │
  │  ── Торговля ──────────────────────────────────────────│
  │                                                          │
  │  ┌────────────────────────────────────────────────────┐ │
  │  │                                                    │ │
  │  │  [● Купить]  [○ Продать]                          │ │
  │  │                                                    │ │
  │  │  Исход:                                           │ │
  │  │  [🟢 YES $0.72]  [🔴 NO $0.28]                   │ │
  │  │                                                    │ │
  │  │  Сумма: [$          100.00]                       │ │
  │  │  [$10] [$25] [$50] [$100] [$500]                 │ │
  │  │                                                    │ │
  │  │  ── Предпросмотр ──                              │ │
  │  │  Вы получите: 138.89 YES акций                   │ │
  │  │  Средняя цена: $0.7200                           │ │
  │  │  Комиссия: $1.00 (1%)                            │ │
  │  │  Если YES победит: +$38.89 (+38.9%)              │ │
  │  │  Если NO победит: -$100.00 (-100%)               │ │
  │  │  Price impact: 0.3%                              │ │
  │  │                                                    │ │
  │  │  [      Купить 138.89 YES      ]                 │ │
  │  │                                                    │ │
  │  └────────────────────────────────────────────────────┘ │
  │                                                          │
  │  ── Моя позиция ──────────────────────────────────────│
  │  (если есть)                                           │
  │  ┌────────────────────────────────────────────────────┐ │
  │  │ 🟢 YES: 250 акций                                │ │
  │  │ Средняя цена: $0.65                               │ │
  │  │ Инвестировано: $162.50                            │ │
  │  │ Текущая стоимость: $180.00                        │ │
  │  │ PnL: +$17.50 (+10.8%) 📈                         │ │
  │  │ Если YES: +$87.50 (+53.8%)                        │ │
  │  │                                                    │ │
  │  │ [Продать часть] [Продать всё]                     │ │
  │  └────────────────────────────────────────────────────┘ │
  │                                                          │
  │  ── Описание ──────────────────────────────────────────│
  │  Маркет будет разрешён как YES, если цена BTC          │
  │  на CoinGecko превысит $200,000 хотя бы на             │
  │  одну минуту до 31 декабря 2025 23:59 UTC.             │
  │                                                          │
  │  Источник: coingecko.com/en/coins/bitcoin               │
  │                                                          │
  │  ── Последние сделки ──────────────────────────────────│
  │  │ Время  │ Трейдер │ Действие      │ Сумма  │ Цена │ │
  │  │ 14:30  │ Us***   │ Купил YES     │ $100   │ $0.72│ │
  │  │ 14:25  │ An***   │ Продал NO     │ 50 шт  │ $0.28│ │
  │  │ 14:20  │ Ko***   │ Купил NO      │ $200   │ $0.27│ │
  │                                                          │
  │  ── Комментарии (23) ─────────────────────────────────│
  │                                                          │
  │  Написать: [________________________________] [Отпр.]  │
  │  Моё мнение: [○ YES] [○ NO] [● Без мнения]           │
  │                                                          │
  │  📌 Модератор:                                         │
  │  "Напоминаю: учитывается пиковая цена, а не..."       │
  │  ❤️ 15   💬 3 ответа                                  │
  │                                                          │
  │  Us*** 🟢YES:                                           │
  │  "ETF приток рекордный, $200K реально"                 │
  │  ❤️ 8   💬 1 ответ                                    │
  │                                                          │
  │  An*** 🔴NO:                                            │
  │  "Слишком оптимистично, макс $150K"                    │
  │  ❤️ 5                                                  │
  │                                                          │
  └──────────────────────────────────────────────────────────┘

  HTMX:
    Торговая форма:
      При изменении суммы или стороны:
        hx-get="/predictions/api/preview/"
        hx-trigger="keyup changed delay:300ms"
        hx-target="#trade-preview"
      
      При покупке:
        hx-post="/predictions/api/trade/"
        hx-target="#trade-result"

    График:
      Рисуется через JavaScript (Chart.js или lightweight-charts)
      Данные: hx-get="/predictions/api/chart/{market_id}/?period=7d"

    Комментарии:
      hx-post="/predictions/api/comment/"
      hx-target="#comments-list"
      hx-swap="afterbegin"
```

### Портфель

```
URL: /predictions/portfolio/

  ┌──────────────────────────────────────────────────────────┐
  │  📊 Мой портфель                                        │
  │                                                          │
  │  ┌──────────────────────────────────────────────────┐   │
  │  │ Вложено     Стоимость    PnL          Win Rate  │   │
  │  │ $1,500      $1,750       +$250 (+17%) 62.5%    │   │
  │  └──────────────────────────────────────────────────┘   │
  │                                                          │
  │  [Активные (5)]  [Завершённые (12)]                    │
  │                                                          │
  │  ── Активные позиции ──────────────────────────────── │
  │                                                          │
  │  ┌──────────────────────────────────────────────────┐   │
  │  │ Bitcoin $200K?                                   │   │
  │  │ 🟢 YES: 250 акций × $0.72 = $180.00            │   │
  │  │ Вложено: $162.50 │ PnL: +$17.50 (+10.8%) 📈    │   │
  │  │ [Продать] [Подробнее]                            │   │
  │  ├──────────────────────────────────────────────────┤   │
  │  │ Трамп 2028?                                     │   │
  │  │ 🔴 NO: 500 акций × $0.65 = $325.00             │   │
  │  │ Вложено: $300.00 │ PnL: +$25.00 (+8.3%) 📈     │   │
  │  │ [Продать] [Подробнее]                            │   │
  │  └──────────────────────────────────────────────────┘   │
  │                                                          │
  │  ── Завершённые ───────────────────────────────────── │
  │  │ Маркет              │ Сторона │ Вложено │ Получено│ │
  │  │ ETH $10K 2024?      │ 🟢 YES │ $100    │ $142.00│ │
  │  │ ЧМ Аргентина?       │ 🔴 NO  │ $50     │ $0     │ │
  │                                                          │
  └──────────────────────────────────────────────────────────┘
```

### Таблица лидеров

```
URL: /predictions/leaderboard/

  ┌──────────────────────────────────────────────────────────┐
  │  🏆 Таблица лидеров                                    │
  │                                                          │
  │  Период: [7 дней] [30 дней] [Всё время]               │
  │                                                          │
  │  │ # │ Трейдер   │ PnL        │ Сделок │ Win Rate │    │
  │  │ 1 │ 🥇 Us***  │ +$5,230    │ 234    │ 68.4%    │    │
  │  │ 2 │ 🥈 An***  │ +$3,180    │ 189    │ 61.2%    │    │
  │  │ 3 │ 🥉 Ko***  │ +$2,450    │ 156    │ 59.8%    │    │
  │  │ 4 │    Ma***  │ +$1,890    │ 210    │ 55.3%    │    │
  │  │ 5 │    Di***  │ +$1,230    │ 98     │ 63.1%    │    │
  │  │ ...                                              │    │
  │  │ 47│    Вы     │ +$250      │ 23     │ 62.5%    │    │
  │                                                          │
  └──────────────────────────────────────────────────────────┘
```

### Создание маркета (модератор)

```
URL: /predictions/create/
Доступ: модератор или админ

  ┌──────────────────────────────────────────────────────────┐
  │  📝 Создать маркет                                      │
  │                                                          │
  │  Вопрос (RU):                                           │
  │  ┌────────────────────────────────────────────────────┐ │
  │  │ Bitcoin достигнет $200K до конца 2025?             │ │
  │  └────────────────────────────────────────────────────┘ │
  │  ⚠️ Должен иметь однозначный ответ YES или NO          │
  │                                                          │
  │  Вопрос (EN) — необязательно:                          │
  │  ┌────────────────────────────────────────────────────┐ │
  │  │ Will Bitcoin reach $200K by end of 2025?           │ │
  │  └────────────────────────────────────────────────────┘ │
  │                                                          │
  │  Описание и правила:                                    │
  │  ┌────────────────────────────────────────────────────┐ │
  │  │ Маркет будет разрешён как YES, если...            │ │
  │  └────────────────────────────────────────────────────┘ │
  │                                                          │
  │  Категория: [₿ Крипто ▼]                               │
  │  Источник: [https://coingecko.com/...]                  │
  │  Теги: [bitcoin, crypto, price]                         │
  │  Превью: [📷 Загрузить]                                │
  │                                                          │
  │  Закрытие торгов: [15.12.2025 23:59]                   │
  │  Дата резолвинга: [31.12.2025 23:59]                   │
  │                                                          │
  │  Начальная ликвидность: [$10,000]                       │
  │  (определяет глубину рынка)                             │
  │                                                          │
  │  [Создать маркет]                                       │
  │                                                          │
  └──────────────────────────────────────────────────────────┘
```

### Критерий готовности шага 6.3

```
□ /predictions/ — главная с категориями, фильтрами, поиском
□ /predictions/{id}/ — детали с графиком, торговлей, комментариями
□ /predictions/portfolio/ — портфель пользователя
□ /predictions/leaderboard/ — таблица лидеров
□ /predictions/history/ — история сделок
□ /predictions/create/ — создание маркета (модератор)
□ Торговая форма с preview (HTMX)
□ График цены (Chart.js)
□ Комментарии с лайками
□ Мини-графики на карточках
□ Все страницы: тёмная тема, мобильная адаптация
```

---

## ШАГ 6.4 — CELERY + ADMIN

### Файл tasks.py

```
close_expired_markets():
    Каждые 5 минут.
    Маркеты где close_date < now и status == 'active':
      → status = 'pending_resolution'
      → Уведомить модераторов: "Маркет ожидает резолвинга"

update_volume_24h():
    Каждые 15 минут.
    Для каждого активного маркета:
      volume_24h = sum(trades за 24 часа)
      
record_periodic_prices():
    Каждые 15 минут.
    Для каждого активного маркета:
      PriceHistory.create(
        market, yes_price, no_price, source='periodic'
      )

update_trending():
    Каждый час.
    Топ 10 по volume_24h → is_trending = True
    Остальные → is_trending = False

notify_closing_soon():
    Каждые 6 часов.
    Маркеты закрывающиеся через 24 часа:
      Уведомить пользователей с позициями

daily_prediction_report():
    Каждый день в 09:00.
    Отчёт:
      - Новых маркетов: N
      - Резолвленных: N
      - Общий объём: $X
      - Комиссии: $Y
      - Топ маркеты

cleanup_old_price_history():
    Каждый день.
    Удалить PriceHistory старше 365 дней
    (оставить только дневные точки)

check_resolution_overdue():
    Каждые 6 часов.
    Маркеты где resolution_date < now и status == 'pending_resolution':
      Более 24 часов → КРИТИЧЕСКОЕ уведомление модераторам
```

### Файл admin.py

```
MarketCategoryAdmin:
  list_display: icon, name, markets_count, is_active, sort_order
  list_editable: is_active, sort_order

PredictionMarketAdmin:
  list_display: question[:50], category, status, yes_price, no_price,
                volume_usd, trades_count, close_date, created_at
  list_filter: status, category, is_featured, is_trending, close_date
  search_fields: question, question_en, tags
  readonly_fields: market_id, yes_pool, no_pool, constant_k,
                   volume_usd, trades_count, unique_traders
  date_hierarchy: created_at

  fieldsets:
    Основное: question, description, category, thumbnail
    Английский: question_en, description_en
    AMM: yes_pool, no_pool, constant_k, yes_price, no_price
    Статистика: volume_usd, trades_count, unique_traders
    Даты: close_date, resolution_date
    Резолвинг: status, resolution, resolved_by, resolution_evidence
    Настройки: is_featured, initial_liquidity, source_url, tags

  Действия:
    - Резолвить как YES
    - Резолвить как NO
    - Аннулировать
    - Приостановить торги
    - Возобновить торги
    - Отметить featured

  Кастомная страница резолвинга:
    При нажатии "Резолвить":
      Показать:
        - Вопрос маркета
        - Текущие цены
        - Количество позиций
        - Поле "Доказательства"
        - Поле "Ссылка на источник"
        - Кнопки: [✅ YES] [❌ NO] [🚫 Аннулировать]
        - ⚠️ "Это действие необратимо. N пользователей будут затронуты."

PositionAdmin:
  list_display: user, market, side, shares, avg_price,
                total_invested, is_settled
  list_filter: side, is_settled
  search_fields: user__email, market__question
  readonly_fields: settlement_amount

TradeAdmin:
  list_display: trade_id, user, market, action, side,
                shares, price, total_cost, created_at
  list_filter: action, side
  search_fields: trade_id, user__email
  readonly_fields: ВСЕ
  date_hierarchy: created_at

MarketCommentAdmin:
  list_display: user, market, text[:50], likes_count,
                is_pinned, is_deleted
  list_filter: is_pinned, is_deleted, side_prediction
  search_fields: text, user__email
  actions: Закрепить, Удалить

MarketDisputeAdmin:
  list_display: market, user, status, created_at
  list_filter: status
  actions: Принять, Отклонить

PredictionSettingsAdmin:
  Singleton
```

### Критерий готовности шага 6.4

```
□ Celery: close_expired, update_volume, record_prices
□ Celery: update_trending, notify_closing
□ Celery: daily_report, cleanup, check_overdue
□ Admin: все модели настроены
□ Admin: кастомная страница резолвинга
□ Admin: действия (резолвить, аннулировать)
□ Уведомления модераторам
```

---

## 📊 ОБЩИЙ ЧЕКЛИСТ ЭТАПА 6

```
МОДЕЛИ:
  □ MarketCategory (10 категорий)
  □ PredictionMarket (AMM, цены, статистика)
  □ Position (позиции пользователей)
  □ Trade (журнал сделок)
  □ PriceHistory (для графиков)
  □ MarketComment (с вложенностью)
  □ MarketLike, CommentLike
  □ MarketDispute
  □ PredictionSettings (singleton)

СЕРВИСЫ:
  □ AMMService (buy/sell preview + execute)
  □ TradingService (buy/sell shares)
  □ ResolutionService (resolve, settle, void, dispute)
  □ MarketService (create, search, trending)
  □ AnalyticsService (portfolio, charts, leaderboard)

СТРАНИЦЫ:
  □ /predictions/ — главная
  □ /predictions/{id}/ — детали + график + торговля
  □ /predictions/portfolio/ — портфель
  □ /predictions/leaderboard/ — лидеры
  □ /predictions/history/ — история
  □ /predictions/create/ — создание (модератор)

ФУНКЦИОНАЛ:
  □ AMM ценообразование (CPMM)
  □ Покупка YES/NO
  □ Продажа YES/NO
  □ Предпросмотр сделки
  □ Резолвинг маркета
  □ Автоматический расчёт позиций
  □ Аннулирование маркета
  □ Оспаривание результата
  □ Комментарии + лайки
  □ График цен (Chart.js)
  □ Портфель с PnL
  □ Таблица лидеров
  □ Поиск и фильтры

CELERY:
  □ Закрытие expired маркетов
  □ Обновление volume_24h
  □ Запись PriceHistory
  □ Обновление trending
  □ Уведомления о закрытии
  □ Ежедневный отчёт

ФИНАНСЫ:
  □ Через TransactionService
  □ Комиссия с каждой сделки
  □ Корректный расчёт позиций
  □ PnL (realized + unrealized)

АДМИНКА:
  □ Управление маркетами
  □ Резолвинг (кастомная форма)
  □ Модерация комментариев
  □ Обработка оспариваний
  □ Настройки
```

---

```
╔══════════════════════════════════════════════════════╗
║                                                      ║
║   ЭТАП 6 ЗАВЕРШЁН                                   ║
║                                                      ║
║   Следующий: ЭТАП 7                                 ║
║   Партнёрская программа (Реферальная система)       ║
║                                                      ║
║   Продолжить?                                       ║
║                                                      ║
╚══════════════════════════════════════════════════════╝
```