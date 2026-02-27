

# 📋 ТЗ ПРОЕКТА DOD — ЭТАП 4

# СТАВКИ НА СПОРТ

```
╔══════════════════════════════════════════════════════╗
║                                                      ║
║   ПРОЕКТ:    DOD                                    ║
║   ЭТАП:      4 из 12                                ║
║   НАЗВАНИЕ:  Ставки на спорт                        ║
║   ЗАВИСИТ:   Этапы 1-3 (accounts, wallet, payments) ║
║                                                      ║
║   ЦЕЛЬ:      Полноценный букмекер. Пользователь     ║
║              видит матчи, коэффициенты, делает      ║
║              ставки (одиночные, экспресс),          ║
║              кэшаут, расчёт ставок, история.        ║
║              Как у 1xBet — полный набор маркетов.   ║
║                                                      ║
╚══════════════════════════════════════════════════════╝
```

---

## 📌 КОНТЕКСТ ДЛЯ ИИ-АГЕНТА

```
Ты продолжаешь разработку проекта DOD.
Этапы 1-3 готовы: авторизация, кошелёк, платежи.

Сейчас ты создаёшь модуль ставок на спорт.
Это ГЛАВНЫЙ модуль платформы по объёму функционала.

Источник данных:
  На старте: бесплатный API + ручной ввод через админку.
  Бесплатные API:
    - API-Football (football): 100 запросов/день (free)
    - TheOddsAPI: 500 запросов/мес (free)
    - Если лимит исчерпан → ручной ввод модератором.
  Потом: платный API провайдер (когда будет бюджет).

Виды спорта:
  Футбол, баскетбол, теннис, хоккей,
  MMA/UFC, киберспорт (CS2, Dota 2, LoL),
  волейбол, бокс, настольный теннис и другие.

Типы ставок (как у 1xBet):
  - Одиночная (single)
  - Экспресс (accumulator/combo)
  - Система (system) — позже

Маркеты:
  - Победитель (1X2 или 12)
  - Двойной шанс (1X, X2, 12)
  - Тотал (больше/меньше)
  - Фора (гандикап)
  - Обе забьют (обе команды забьют)
  - Точный счёт
  - Тотал по таймам
  - Индивидуальный тотал
  - И другие

Важно:
  - Все денежные операции через TransactionService
  - Ставка → freeze средств
  - Выигрыш → settle + credit
  - Проигрыш → settle (списание frozen)
  - Коэффициент фиксируется в момент ставки
  - Нельзя ставить на начавшийся матч (prematch)
  - Live ставки — пока НЕ делаем (позже)
```

---

## ШАГ 4.1 — МОДЕЛИ СТАВОК НА СПОРТ

### Задача

```
Создай приложение sports со всеми моделями
для полноценного букмекера.
```

### Структура приложения

```
apps/sports/
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
│   ├── betting_service.py       # Приём ставок
│   ├── settlement_service.py    # Расчёт ставок
│   ├── odds_service.py          # Управление коэффициентами
│   ├── cashout_service.py       # Кэшаут
│   ├── feed_service.py          # Получение данных из API
│   └── statistics_service.py    # Статистика пользователя
├── providers/
│   ├── __init__.py
│   ├── base.py                  # Абстрактный провайдер данных
│   ├── api_football.py          # API-Football
│   ├── the_odds_api.py          # TheOddsAPI
│   └── manual.py                # Ручной ввод
├── templatetags/
│   ├── __init__.py
│   └── sports_tags.py
├── tests/
│   └── ...
├── templates/
│   └── sports/
│       └── (шаблоны)
├── fixtures/
│   ├── sports.json              # Начальные виды спорта
│   └── leagues.json             # Начальные лиги
└── migrations/
    └── __init__.py
```

### Модель Sport (models.py)

```
class Sport(models.Model):

    Назначение:
      Вид спорта. Справочник.
      Футбол, баскетбол, теннис и т.д.

    Поля:
    ─────
    id:
      тип: AutoField, primary key

    name:
      тип: CharField, max 100
      Примеры: 'Футбол', 'Баскетбол', 'Теннис'

    name_en:
      тип: CharField, max 100
      Примеры: 'Football', 'Basketball', 'Tennis'

    slug:
      тип: SlugField, уникальный
      Примеры: 'football', 'basketball', 'tennis'
      Для URL: /sports/football/

    icon:
      тип: CharField, max 50
      Emoji или CSS класс
      '⚽', '🏀', '🎾', '🏒', '🥊', '🎮'

    sort_order:
      тип: IntegerField, default=0
      Порядок в sidebar и списке

    is_active:
      тип: BooleanField, default=True

    is_popular:
      тип: BooleanField, default=False
      Популярные → показываются первыми

    events_count:
      тип: IntegerField, default=0
      Кэшированное количество активных событий
      Обновляется периодически

    external_id:
      тип: CharField, max 50, nullable
      ID в API провайдере (API-Football: league_id)

    Meta:
      verbose_name = 'Вид спорта'
      ordering = ['sort_order', 'name']

    Начальные данные (fixtures):
      ⚽ Футбол (football) — sort 1, popular
      🏀 Баскетбол (basketball) — sort 2, popular
      🎾 Теннис (tennis) — sort 3, popular
      🏒 Хоккей (hockey) — sort 4
      🥊 MMA/UFC (mma) — sort 5, popular
      🎮 Киберспорт (esports) — sort 6, popular
      🏐 Волейбол (volleyball) — sort 7
      🥊 Бокс (boxing) — sort 8
      🏓 Настольный теннис (table-tennis) — sort 9
      ⚾ Бейсбол (baseball) — sort 10
      🏈 Американский футбол (american-football) — sort 11
      🏉 Регби (rugby) — sort 12
```

### Модель Country (models.py)

```
class Country(models.Model):

    Назначение:
      Страна для группировки лиг.
      "Англия", "Испания", "Международные".

    Поля:
    ─────
    id:
      тип: AutoField

    name:
      тип: CharField, max 100
      'Англия', 'Испания', 'Россия'

    name_en:
      тип: CharField, max 100

    code:
      тип: CharField, max 5
      ISO код: 'GB', 'ES', 'RU'

    flag:
      тип: CharField, max 10
      Emoji флаг: '🇬🇧', '🇪🇸', '🇷🇺'

    sort_order:
      тип: IntegerField, default=0

    is_active:
      тип: BooleanField, default=True

    Meta:
      ordering = ['sort_order', 'name']
```

### Модель League (models.py)

```
class League(models.Model):

    Назначение:
      Лига/турнир внутри вида спорта.
      "Английская Премьер-Лига", "Ла Лига", "НБА".

    Поля:
    ─────
    id:
      тип: AutoField

    sport:
      тип: ForeignKey → Sport
      related_name: 'leagues'

    country:
      тип: ForeignKey → Country, nullable
      Для международных турниров = null

    name:
      тип: CharField, max 200
      'Английская Премьер-Лига'

    name_en:
      тип: CharField, max 200
      'English Premier League'

    short_name:
      тип: CharField, max 50
      'АПЛ', 'EPL'

    slug:
      тип: SlugField

    logo:
      тип: ImageField, nullable
      Логотип лиги

    season:
      тип: CharField, max 20
      '2024/2025', '2025'

    is_active:
      тип: BooleanField, default=True

    is_popular:
      тип: BooleanField, default=False
      Популярные лиги наверху

    events_count:
      тип: IntegerField, default=0

    sort_order:
      тип: IntegerField, default=0

    external_id:
      тип: CharField, max 50, nullable
      ID в API провайдере

    Meta:
      verbose_name = 'Лига'
      ordering = ['-is_popular', 'sort_order', 'name']
      unique_together = ['sport', 'slug', 'season']
```

### Модель Team (models.py)

```
class Team(models.Model):

    Назначение:
      Команда или участник.
      "Реал Мадрид", "Лейкерс", "Конор Макгрегор".

    Поля:
    ─────
    id:
      тип: AutoField

    sport:
      тип: ForeignKey → Sport

    name:
      тип: CharField, max 200
      'Реал Мадрид'

    name_en:
      тип: CharField, max 200
      'Real Madrid'

    short_name:
      тип: CharField, max 50
      'Реал', 'RMA'

    logo:
      тип: ImageField, nullable

    country:
      тип: ForeignKey → Country, nullable

    is_active:
      тип: BooleanField, default=True

    external_id:
      тип: CharField, max 50, nullable

    Meta:
      verbose_name = 'Команда'
      ordering = ['name']
```

### Модель Event (models.py)

```
class Event(models.Model):

    Назначение:
      Спортивное событие (матч).
      "Реал Мадрид — Барселона"
      Центральная модель модуля.

    Поля:
    ─────
    id:
      тип: UUID, primary key

    sport:
      тип: ForeignKey → Sport
      related_name: 'events'

    league:
      тип: ForeignKey → League
      related_name: 'events'

    home_team:
      тип: ForeignKey → Team
      related_name: 'home_events'

    away_team:
      тип: ForeignKey → Team
      related_name: 'away_events'

    name:
      тип: CharField, max 300
      Генерируется автоматически: "Реал Мадрид — Барселона"

    slug:
      тип: SlugField, nullable

    start_time:
      тип: DateTimeField
      Время начала матча (UTC)
      ИНДЕКС для быстрых запросов

    end_time:
      тип: DateTimeField, nullable
      Время окончания (заполняется после)

    status:
      тип: CharField
      choices:
        ('scheduled', 'Запланирован')
        ('prematch', 'Премматч')           # Ставки принимаются
        ('live', 'Идёт')                    # Матч идёт (live не делаем пока)
        ('suspended', 'Приостановлен')      # Ставки заморожены
        ('finished', 'Завершён')            # Результат известен
        ('cancelled', 'Отменён')            # Матч отменён
        ('postponed', 'Перенесён')          # Матч перенесён
      default: 'scheduled'

    home_score:
      тип: IntegerField, nullable
      Счёт домашней команды

    away_score:
      тип: IntegerField, nullable
      Счёт гостевой команды

    result_details:
      тип: JSONField, default=dict
      Детали результата:
      Для футбола:
        {
          "home_score": 3,
          "away_score": 1,
          "ht_home_score": 1,     # первый тайм
          "ht_away_score": 0,
          "home_corners": 7,
          "away_corners": 4,
          "home_cards_yellow": 2,
          "away_cards_yellow": 3,
          "home_cards_red": 0,
          "away_cards_red": 0
        }
      Для баскетбола:
        {
          "home_score": 112,
          "away_score": 105,
          "q1_home": 28, "q1_away": 30,
          "q2_home": 25, "q2_away": 22,
          "q3_home": 30, "q3_away": 28,
          "q4_home": 29, "q4_away": 25
        }
      Для тенниса:
        {
          "sets": [[6,4], [3,6], [7,5]],
          "winner": "home"
        }

    is_featured:
      тип: BooleanField, default=False
      Топ матч (показывается на главной)

    is_boosted:
      тип: BooleanField, default=False
      Повышенные коэффициенты (промо)

    views_count:
      тип: IntegerField, default=0
      Сколько раз просмотрен

    bets_count:
      тип: IntegerField, default=0
      Сколько ставок сделано

    total_stake:
      тип: DecimalField, default=0
      Общая сумма ставок (в USD)

    markets_count:
      тип: IntegerField, default=0
      Количество доступных маркетов

    data_source:
      тип: CharField
      choices:
        ('api_football', 'API-Football')
        ('the_odds_api', 'TheOddsAPI')
        ('manual', 'Ручной ввод')
      default: 'manual'

    external_id:
      тип: CharField, max 100, nullable
      ID в API провайдере

    settled_at:
      тип: DateTimeField, nullable
      Когда был рассчитан

    settled_by:
      тип: ForeignKey → User, nullable
      Кто рассчитал (для ручного расчёта)

    notes:
      тип: TextField, nullable
      Заметки админа

    created_at:
      тип: DateTimeField, auto_now_add

    updated_at:
      тип: DateTimeField, auto_now

    Методы:
    ───────
    __str__():
      "Реал Мадрид — Барселона"

    is_bettable():
      True если status == 'prematch' и start_time > now

    is_started():
      True если start_time <= now

    is_settled():
      True если status == 'finished' и settled_at != None

    get_time_until_start():
      Возвращает timedelta до начала
      "через 2ч 30мин"

    get_formatted_score():
      "3 : 1" или "— : —" если ещё не начался

    save():
      При сохранении автоматически генерировать name:
        f"{home_team.name} — {away_team.name}"

    Meta:
      verbose_name = 'Событие'
      ordering = ['start_time']
      indexes:
        - sport + status + start_time
        - league + start_time
        - status
        - start_time
        - is_featured
```

### Модель Market (models.py)

```
class Market(models.Model):

    Назначение:
      Тип ставки на событие.
      "Победитель", "Тотал 2.5", "Фора -1.5"

    Поля:
    ─────
    id:
      тип: UUID, primary key

    event:
      тип: ForeignKey → Event
      related_name: 'markets'

    market_type:
      тип: ForeignKey → MarketType
      Тип маркета из справочника

    name:
      тип: CharField, max 200
      Отображаемое название
      "Исход матча", "Тотал 2.5", "Фора 1 (-1.5)"

    sort_order:
      тип: IntegerField, default=0

    parameter:
      тип: DecimalField, nullable
      Параметр маркета:
        Тотал 2.5 → parameter = 2.5
        Фора -1.5 → parameter = -1.5
        Победитель → parameter = null

    status:
      тип: CharField
      choices:
        ('open', 'Открыт')          # Ставки принимаются
        ('suspended', 'Приостановлен')  # Временно нельзя ставить
        ('closed', 'Закрыт')         # Ставки не принимаются
        ('settled', 'Рассчитан')     # Результат определён
        ('void', 'Аннулирован')      # Возврат ставок
      default: 'open'

    is_main:
      тип: BooleanField, default=False
      Главный маркет (показывается в списке матчей)
      Обычно "Победитель" (1X2)

    settled_at:
      тип: DateTimeField, nullable

    created_at:
      тип: DateTimeField, auto_now_add

    Meta:
      verbose_name = 'Маркет'
      ordering = ['sort_order']
      indexes:
        - event + status
        - event + is_main
```

### Модель MarketType (models.py)

```
class MarketType(models.Model):

    Назначение:
      Справочник типов маркетов.
      Не зависит от конкретного события.

    Поля:
    ─────
    id:
      тип: AutoField

    code:
      тип: CharField, max 50, уникальный
      Примеры: '1x2', 'total', 'handicap',
               'both_to_score', 'double_chance',
               'exact_score', 'ht_ft', 'first_goal'

    name:
      тип: CharField, max 100
      'Исход матча (1X2)'

    name_en:
      тип: CharField, max 100
      'Match Result (1X2)'

    description:
      тип: TextField
      Описание для пользователя

    sport:
      тип: ForeignKey → Sport, nullable
      null = подходит для всех видов спорта

    has_parameter:
      тип: BooleanField, default=False
      True для тотала (2.5, 3.5) и форы (-1.5, +0.5)

    outcomes_template:
      тип: JSONField
      Шаблон исходов для этого типа маркета
      
      Примеры:
      '1x2':
        [
          {"code": "home", "name": "П1", "name_en": "Home"},
          {"code": "draw", "name": "Ничья", "name_en": "Draw"},
          {"code": "away", "name": "П2", "name_en": "Away"}
        ]
      'total':
        [
          {"code": "over", "name": "Больше {param}", "name_en": "Over {param}"},
          {"code": "under", "name": "Меньше {param}", "name_en": "Under {param}"}
        ]
      'handicap':
        [
          {"code": "home", "name": "Ф1 ({param})", "name_en": "H1 ({param})"},
          {"code": "away", "name": "Ф2 ({param_inv})", "name_en": "H2 ({param_inv})"}
        ]
      'both_to_score':
        [
          {"code": "yes", "name": "Да", "name_en": "Yes"},
          {"code": "no", "name": "Нет", "name_en": "No"}
        ]
      'double_chance':
        [
          {"code": "1x", "name": "1X", "name_en": "1X"},
          {"code": "12", "name": "12", "name_en": "12"},
          {"code": "x2", "name": "X2", "name_en": "X2"}
        ]
      'exact_score':
        [
          {"code": "1-0", "name": "1:0"},
          {"code": "2-0", "name": "2:0"},
          {"code": "2-1", "name": "2:1"},
          {"code": "0-0", "name": "0:0"},
          {"code": "1-1", "name": "1:1"},
          {"code": "0-1", "name": "0:1"},
          {"code": "0-2", "name": "0:2"},
          {"code": "1-2", "name": "1:2"},
          {"code": "other", "name": "Другой"}
        ]

    sort_order:
      тип: IntegerField, default=0

    is_active:
      тип: BooleanField, default=True

    is_popular:
      тип: BooleanField, default=False
      Популярные маркеты показываются первыми

    Meta:
      verbose_name = 'Тип маркета'
      ordering = ['sort_order']

    Начальные данные:
      Код           | Название            | Параметр | Спорт
      ──────────────┼─────────────────────┼──────────┼──────
      1x2           | Исход матча         | нет      | все
      12            | Победитель          | нет      | basket/tennis
      total         | Тотал               | да       | все
      handicap      | Фора                | да       | все
      both_to_score | Обе забьют          | нет      | футбол
      double_chance | Двойной шанс        | нет      | футбол
      exact_score   | Точный счёт         | нет      | футбол
      ht_result     | Результат 1 тайма   | нет      | футбол
      total_corners | Тотал угловых       | да       | футбол
      total_cards   | Тотал карточек      | да       | футбол
      first_goal    | Первый гол          | нет      | футбол
      ind_total_h   | Инд. тотал хозяев   | да       | все
      ind_total_a   | Инд. тотал гостей   | да       | все
      odd_even      | Чёт/нечёт          | нет      | все
      winner_round  | Победитель раунда   | нет      | MMA
      method_victory| Метод победы        | нет      | MMA
      map_winner    | Победитель на карте | нет      | киберспорт
```

### Модель Outcome (models.py)

```
class Outcome(models.Model):

    Назначение:
      Конкретный исход в маркете с коэффициентом.
      "П1 — 2.10", "Ничья — 3.40", "П2 — 3.20"

    Поля:
    ─────
    id:
      тип: UUID, primary key

    market:
      тип: ForeignKey → Market
      related_name: 'outcomes'

    code:
      тип: CharField, max 50
      Код исхода: 'home', 'draw', 'away', 'over', 'under'

    name:
      тип: CharField, max 100
      Отображаемое название: 'П1', 'Ничья', 'Больше 2.5'

    odd:
      тип: DecimalField, max_digits=10, decimal_places=3
      Текущий коэффициент: 2.100

    odd_initial:
      тип: DecimalField, max_digits=10, decimal_places=3
      Начальный коэффициент (для аналитики)

    odd_previous:
      тип: DecimalField, max_digits=10, decimal_places=3, nullable
      Предыдущий коэффициент (для показа изменений)

    odd_direction:
      тип: CharField
      choices:
        ('up', '↑ Вырос')
        ('down', '↓ Упал')
        ('same', '= Не изменился')
      default: 'same'
      Обновляется при изменении коэффициента

    result:
      тип: CharField
      choices:
        ('pending', 'Ожидает')
        ('won', 'Выиграл')
        ('lost', 'Проиграл')
        ('void', 'Аннулирован')     # Возврат
        ('half_won', 'Выиграл 50%')  # Для азиатских фор
        ('half_lost', 'Проиграл 50%')
      default: 'pending'

    is_active:
      тип: BooleanField, default=True
      False = нельзя ставить на этот исход

    is_suspended:
      тип: BooleanField, default=False
      Временно заблокирован

    max_stake:
      тип: DecimalField, nullable
      Максимальная ставка на этот исход (USD)
      null = глобальный лимит

    total_stake:
      тип: DecimalField, default=0
      Сумма всех ставок на этот исход

    bets_count:
      тип: IntegerField, default=0

    sort_order:
      тип: IntegerField, default=0

    settled_at:
      тип: DateTimeField, nullable

    Meta:
      verbose_name = 'Исход'
      ordering = ['sort_order']
      indexes:
        - market + is_active
        - result
```

### Модель Bet (models.py)

```
class Bet(models.Model):

    Назначение:
      Ставка пользователя.
      Может быть одиночной (1 исход) или экспресс (несколько).

    Поля:
    ─────
    id:
      тип: UUID, primary key

    bet_id:
      тип: CharField, max 50, уникальный
      Человекочитаемый ID
      Формат: BET-{timestamp}-{random6}
      Пример: BET-20250315-K8M2N4

    user:
      тип: ForeignKey → User
      related_name: 'bets'

    wallet:
      тип: ForeignKey → Wallet

    bet_type:
      тип: CharField
      choices:
        ('single', 'Одиночная')
        ('combo', 'Экспресс')
        ('system', 'Система')    # Позже
      default: 'single'

    currency:
      тип: ForeignKey → Currency
      В какой валюте сделана ставка

    stake:
      тип: DecimalField
      Сумма ставки

    stake_usd:
      тип: DecimalField
      Эквивалент в USD

    total_odd:
      тип: DecimalField, max_digits=15, decimal_places=3
      Общий коэффициент
      Для single: коэффициент исхода
      Для combo: произведение всех коэффициентов

    potential_win:
      тип: DecimalField
      Потенциальный выигрыш = stake × total_odd

    actual_win:
      тип: DecimalField, default=0
      Фактический выигрыш (заполняется при расчёте)

    profit:
      тип: DecimalField, default=0
      Чистая прибыль = actual_win - stake
      Может быть отрицательной (проигрыш)

    status:
      тип: CharField
      choices:
        ('pending', 'Ожидает')          # Ставка активна
        ('won', 'Выиграла')
        ('lost', 'Проиграла')
        ('partial_won', 'Частично выиграла')  # Экспресс с возвратом
        ('void', 'Аннулирована')         # Возврат ставки
        ('cashed_out', 'Кэшаут')         # Досрочный расчёт
        ('cancelled', 'Отменена')        # Отмена админом
      default: 'pending'

    items_count:
      тип: IntegerField
      Количество исходов в ставке
      1 для single, 2+ для combo

    items_won:
      тип: IntegerField, default=0
      Сколько исходов выиграло

    items_lost:
      тип: IntegerField, default=0
      Сколько проиграло

    items_void:
      тип: IntegerField, default=0
      Сколько аннулировано

    items_pending:
      тип: IntegerField
      Сколько ещё не рассчитано

    cashout_available:
      тип: BooleanField, default=True
      Доступен ли кэшаут

    cashout_amount:
      тип: DecimalField, nullable
      Текущая сумма кэшаута (пересчитывается)

    cashout_used_at:
      тип: DateTimeField, nullable
      Когда воспользовался кэшаутом

    freeze_transaction:
      тип: ForeignKey → Transaction, nullable
      Транзакция заморозки средств

    win_transaction:
      тип: ForeignKey → Transaction, nullable
      Транзакция зачисления выигрыша

    settled_at:
      тип: DateTimeField, nullable
      Когда рассчитана

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
    __str__():
      "BET-20250315-K8M2N4: $50.00 x2.10 = $105.00 (pending)"

    is_settled():
      True если status not in ('pending',)

    is_cashout_available():
      True если:
        - cashout_available == True
        - status == 'pending'
        - items_pending > 0
        - items_lost == 0

    calculate_cashout_amount():
      Рассчитать текущий кэшаут.
      Формула:
        base = stake
        for each settled item that won:
          base *= item.odd_at_placement
        for each pending item:
          base *= current_odd * CASHOUT_FACTOR
        cashout = base * CASHOUT_MARGIN (например 0.9)
      Вернуть cashout

    recalculate():
      Пересчитать статус ставки после расчёта одного из событий.

    Meta:
      verbose_name = 'Ставка'
      ordering = ['-created_at']
      indexes:
        - user + created_at
        - user + status
        - status
        - bet_id
        - created_at
```

### Модель BetItem (models.py)

```
class BetItem(models.Model):

    Назначение:
      Одна позиция в ставке.
      Для single: 1 BetItem.
      Для combo: 2+ BetItem.

    Поля:
    ─────
    id:
      тип: UUID, primary key

    bet:
      тип: ForeignKey → Bet
      related_name: 'items'

    event:
      тип: ForeignKey → Event

    market:
      тип: ForeignKey → Market

    outcome:
      тип: ForeignKey → Outcome

    odd_at_placement:
      тип: DecimalField, max_digits=10, decimal_places=3
      Коэффициент на момент ставки
      ФИКСИРУЕТСЯ и НЕ МЕНЯЕТСЯ

    odd_current:
      тип: DecimalField, nullable
      Текущий коэффициент (для сравнения)

    result:
      тип: CharField
      choices: pending, won, lost, void, half_won, half_lost
      default: 'pending'

    event_name:
      тип: CharField, max 300
      Название события (кэшировано)
      "Реал Мадрид — Барселона"
      Чтобы было видно даже если событие удалено

    market_name:
      тип: CharField, max 200
      "Исход матча (1X2)"

    outcome_name:
      тип: CharField, max 100
      "П1" или "Больше 2.5"

    event_start_time:
      тип: DateTimeField
      Время начала события (кэшировано)

    settled_at:
      тип: DateTimeField, nullable

    Meta:
      verbose_name = 'Позиция в ставке'
      ordering = ['event_start_time']
```

### Модель BetSettings (models.py)

```
class BetSettings(models.Model):

    Назначение:
      Глобальные настройки ставок.
      Singleton. Управляется через админку.

    Поля:
    ─────
    min_stake_usd:
      тип: DecimalField
      Минимальная ставка (в USD)
      default=0.50

    max_stake_usd:
      тип: DecimalField
      Максимальная ставка (в USD)
      default=50000

    max_potential_win_usd:
      тип: DecimalField
      Максимальный выигрыш с одной ставки (в USD)
      default=100000

    max_combo_items:
      тип: IntegerField
      Максимум событий в экспрессе
      default=20

    min_combo_items:
      тип: IntegerField
      Минимум событий в экспрессе
      default=2

    min_odd:
      тип: DecimalField
      Минимальный допустимый коэффициент
      default=1.01

    max_odd:
      тип: DecimalField
      Максимальный допустимый коэффициент
      default=1000.0

    cashout_enabled:
      тип: BooleanField, default=True

    cashout_margin:
      тип: DecimalField
      Маржа кэшаута (0.85 = 85% от справедливой цены)
      default=0.90

    cashout_min_amount_usd:
      тип: DecimalField
      default=1.00

    max_bets_per_event_per_user:
      тип: IntegerField
      Максимум ставок на одно событие от одного пользователя
      default=50

    delay_before_start_minutes:
      тип: IntegerField
      За сколько минут до начала закрывать ставки
      default=1

    auto_settle_enabled:
      тип: BooleanField, default=True
      Автоматический расчёт ставок

    odds_change_notification:
      тип: BooleanField, default=True
      Уведомлять при изменении коэффициентов

    Meta:
      verbose_name = 'Настройки ставок'
```

### Модель OddHistory (models.py)

```
class OddHistory(models.Model):

    Назначение:
      История изменений коэффициентов.
      Для графика движения линии.

    Поля:
    ─────
    id:
      тип: BigAutoField

    outcome:
      тип: ForeignKey → Outcome
      related_name: 'history'

    odd_before:
      тип: DecimalField

    odd_after:
      тип: DecimalField

    changed_by:
      тип: CharField
      choices:
        ('api', 'API провайдер')
        ('admin', 'Админ')
        ('system', 'Система')

    changed_at:
      тип: DateTimeField, auto_now_add

    Meta:
      ordering = ['-changed_at']
      indexes:
        - outcome + changed_at
```

### Файл admin.py

```
SportAdmin:
  list_display: icon, name, slug, events_count, is_active, is_popular, sort_order
  list_editable: is_active, is_popular, sort_order
  prepopulated_fields: {'slug': ('name_en',)}

LeagueAdmin:
  list_display: name, sport, country, season, events_count,
                is_active, is_popular
  list_filter: sport, country, is_active, is_popular, season
  search_fields: name, name_en
  list_editable: is_active, is_popular

TeamAdmin:
  list_display: name, sport, country, is_active
  list_filter: sport, country
  search_fields: name, name_en

EventAdmin:
  list_display: name, sport, league, start_time, status,
                home_score, away_score, markets_count,
                bets_count, total_stake, is_featured
  list_filter: sport, league, status, is_featured,
               data_source, start_time
  search_fields: name, home_team__name, away_team__name
  date_hierarchy: start_time
  readonly_fields: bets_count, total_stake, views_count

  inlines: [MarketInline]

  Действия:
    - Открыть ставки (status → prematch)
    - Приостановить ставки (status → suspended)
    - Закрыть ставки (status → live)
    - Рассчитать событие (откроет форму результата)
    - Отменить событие (вернуть все ставки)
    - Отметить как featured

  Кастомная страница расчёта:
    При нажатии "Рассчитать":
    Показать форму:
      - Счёт: домашняя [___] : [___] гостевая
      - Детали (зависит от спорта)
      - Кнопка: [Рассчитать все ставки]
    При подтверждении:
      - SettlementService.settle_event()

MarketInline:
  model: Market
  extra: 0
  show_change_link: True

MarketAdmin:
  list_display: name, event, market_type, status, parameter
  list_filter: status, market_type
  inlines: [OutcomeInline]

OutcomeInline:
  model: Outcome
  extra: 0
  fields: code, name, odd, result, is_active

OutcomeAdmin:
  list_display: name, market, odd, odd_direction, result,
                is_active, bets_count, total_stake
  list_filter: result, is_active
  list_editable: odd, result, is_active

BetAdmin:
  list_display: bet_id, user, bet_type, currency, stake,
                total_odd, potential_win, actual_win,
                status, items_count, created_at
  list_filter: status, bet_type, currency, created_at
  search_fields: bet_id, user__email, user__username
  readonly_fields: bet_id, total_odd, potential_win,
                   freeze_transaction, win_transaction
  date_hierarchy: created_at
  inlines: [BetItemInline]

  Действия:
    - Отменить ставки (void + возврат)
    - Рассчитать вручную

BetItemInline:
  model: BetItem
  extra: 0
  readonly_fields: event_name, market_name, outcome_name,
                   odd_at_placement
  fields: event_name, market_name, outcome_name,
          odd_at_placement, result

BetSettingsAdmin:
  Singleton
  Все поля редактируемые
```

### Критерий готовности шага 4.1

```
□ Модель Sport + fixtures (12 видов спорта)
□ Модель Country + fixtures
□ Модель League
□ Модель Team
□ Модель Event (все поля и методы)
□ Модель MarketType + fixtures (15+ типов)
□ Модель Market
□ Модель Outcome
□ Модель Bet (single, combo)
□ Модель BetItem
□ Модель BetSettings (singleton)
□ Модель OddHistory
□ Все миграции применены
□ Admin: все модели с фильтрами, поиском, действиями
□ Кастомная страница расчёта событий в админке
□ Fixtures загружены
```

---

## ШАГ 4.2 — СЕРВИСЫ СТАВОК

### BettingService (services/betting_service.py)

```
class BettingService:

    Назначение:
      Приём и обработка ставок.
      САМЫЙ КРИТИЧНЫЙ СЕРВИС.
      Все операции АТОМАРНЫЕ.

    Методы:
    ───────

    @staticmethod
    def place_single_bet(user, outcome_id, stake,
                          currency_code, ip_address, user_agent):
      
      Одиночная ставка.
      
      Логика (АТОМАРНО — transaction.atomic + select_for_update):

        1. ПОЛУЧИТЬ ДАННЫЕ:
           outcome = Outcome.select_for_update().get(id=outcome_id)
           market = outcome.market
           event = market.event
           settings = BetSettings.get_settings()

        2. ВАЛИДАЦИЯ:
           
           a) Событие:
              - event.status == 'prematch'
                Иначе: "Ставки на это событие закрыты"
              - event.start_time > now + delay_before_start
                Иначе: "Событие скоро начнётся, ставки закрыты"

           b) Маркет:
              - market.status == 'open'
                Иначе: "Маркет закрыт"

           c) Исход:
              - outcome.is_active == True
              - outcome.is_suspended == False
                Иначе: "Исход временно недоступен"

           d) Коэффициент:
              - outcome.odd >= settings.min_odd
              - outcome.odd <= settings.max_odd
                Иначе: "Некорректный коэффициент"

           e) Ставка:
              - stake >= min_stake (в валюте ставки)
                Иначе: "Минимальная ставка: $X"
              - stake <= max_stake
                Иначе: "Максимальная ставка: $X"
              - stake <= outcome.max_stake (если задан)
                Иначе: "Максимум на этот исход: $X"

           f) Потенциальный выигрыш:
              potential_win = stake × outcome.odd
              - potential_win <= settings.max_potential_win_usd
                (пересчитать в USD)
                Иначе: "Максимальный выигрыш: $X. 
                         Уменьшите ставку."

           g) Лимит ставок на событие:
              user_bets_on_event = Bet.filter(
                user=user, items__event=event, status='pending'
              ).count()
              - user_bets_on_event < settings.max_bets_per_event
                Иначе: "Лимит ставок на это событие достигнут"

           h) Баланс:
              wallet = user.wallet
              - wallet.has_sufficient_balance(currency_code, stake)
                Иначе: "Недостаточно средств. 
                         Баланс: $X. Нужно: $Y"

           i) Кошелёк:
              - wallet.is_frozen == False
                Иначе: "Кошелёк заморожен"

        3. ЗАМОРОЗИТЬ СРЕДСТВА:
           freeze_tx = TransactionService.freeze_funds(
             wallet=wallet,
             currency_code=currency_code,
             amount=stake,
             reference_type='bet',
             reference_id=bet_id
           )

        4. СОЗДАТЬ СТАВКУ:
           bet = Bet.create(
             bet_id=generate_id("BET"),
             user=user,
             wallet=wallet,
             bet_type='single',
             currency=currency,
             stake=stake,
             stake_usd=stake_to_usd,
             total_odd=outcome.odd,
             potential_win=stake * outcome.odd,
             status='pending',
             items_count=1,
             items_pending=1,
             cashout_available=settings.cashout_enabled,
             freeze_transaction=freeze_tx,
             ip_address=ip_address,
             user_agent=user_agent
           )

        5. СОЗДАТЬ BetItem:
           BetItem.create(
             bet=bet,
             event=event,
             market=market,
             outcome=outcome,
             odd_at_placement=outcome.odd,
             event_name=str(event),
             market_name=market.name,
             outcome_name=outcome.name,
             event_start_time=event.start_time
           )

        6. ОБНОВИТЬ СЧЁТЧИКИ:
           outcome.bets_count += 1
           outcome.total_stake += stake_usd
           event.bets_count += 1
           event.total_stake += stake_usd

        7. ВЕРНУТЬ:
           {
             "bet_id": bet.bet_id,
             "status": "pending",
             "stake": stake,
             "odd": outcome.odd,
             "potential_win": potential_win,
             "event": str(event),
             "outcome": outcome.name,
             "message": "✅ Ставка принята!"
           }

      ОШИБКИ (все наследуются от BettingError):
        - EventNotBettableError
        - MarketClosedError
        - OutcomeSuspendedError
        - InsufficientFundsError
        - StakeLimitError
        - WinLimitError
        - BetLimitError
        - OddChangedError
        - WalletFrozenError


    @staticmethod
    def place_combo_bet(user, items, stake,
                         currency_code, ip_address, user_agent):
      
      Экспресс (комбо) ставка.
      items = [{"outcome_id": "..."}, {"outcome_id": "..."}, ...]
      
      Логика (АТОМАРНО):

        1. ВАЛИДАЦИЯ КОЛИЧЕСТВА:
           - len(items) >= settings.min_combo_items (2)
           - len(items) <= settings.max_combo_items (20)

        2. ВАЛИДАЦИЯ КАЖДОГО ИСХОДА:
           Для каждого item в items:
             - Та же валидация что для single
               (событие, маркет, исход, коэффициент)

        3. ПРОВЕРКА КОНФЛИКТОВ:
           В экспрессе нельзя:
           - Два исхода из одного события
             Иначе: "Нельзя добавить два исхода 
                      из одного матча в экспресс"
           - Два противоречащих исхода
             Пример: П1 и П2 на один матч

        4. РАССЧИТАТЬ ОБЩИЙ КОЭФФИЦИЕНТ:
           total_odd = 1.0
           for item in items:
             total_odd *= item.odd
           
           Проверить: total_odd <= settings.max_odd

        5. ПРОВЕРИТЬ ПОТЕНЦИАЛЬНЫЙ ВЫИГРЫШ:
           potential_win = stake × total_odd
           Проверить лимит

        6. ПРОВЕРИТЬ БАЛАНС:
           wallet.has_sufficient_balance(currency, stake)

        7. ЗАМОРОЗИТЬ СРЕДСТВА

        8. СОЗДАТЬ BET (bet_type='combo')

        9. СОЗДАТЬ BetItem для каждого исхода

        10. ОБНОВИТЬ СЧЁТЧИКИ

        11. ВЕРНУТЬ результат


    @staticmethod
    def validate_bet_slip(items):
      
      Валидация купона ПЕРЕД размещением.
      Вызывается при добавлении исхода в купон (HTMX).
      НЕ замораживает деньги.
      
      Возвращает:
        {
          "valid": True/False,
          "items": [
            {
              "outcome_id": "...",
              "event": "Реал — Барса",
              "outcome": "П1",
              "odd": 2.10,
              "valid": True,
              "error": null
            },
            ...
          ],
          "total_odd": 6.30,
          "conflicts": [],
          "errors": []
        }


    @staticmethod
    def cancel_bet(bet_id, admin_user, reason):
      
      Отмена ставки администратором.
      
      Логика:
        1. Bet.status → 'cancelled'
        2. Разморозить средства → TransactionService.unfreeze
        3. Создать Transaction type='refund'
        4. Уведомить пользователя
```

### SettlementService (services/settlement_service.py)

```
class SettlementService:

    Назначение:
      Расчёт ставок после завершения события.

    Методы:
    ───────

    @staticmethod
    def settle_event(event_id, result_data, settled_by=None):
      
      Рассчитать все ставки на событие.
      
      Параметры:
        event_id: UUID события
        result_data: {
          "home_score": 3,
          "away_score": 1,
          ... (детали по спорту)
        }
        settled_by: User (админ) или None (автоматически)

      Логика:

        1. ОБНОВИТЬ СОБЫТИЕ:
           event.status = 'finished'
           event.home_score = result_data['home_score']
           event.away_score = result_data['away_score']
           event.result_details = result_data
           event.end_time = now
           event.settled_by = settled_by

        2. ДЛЯ КАЖДОГО МАРКЕТА СОБЫТИЯ:
           settle_market(market, result_data)

        3. РАССЧИТАТЬ ВСЕ СТАВКИ:
           affected_bets = Bet.filter(
             items__event=event,
             status='pending'
           ).distinct()
           
           for bet in affected_bets:
             settle_bet(bet)

        4. event.settled_at = now


    @staticmethod
    def settle_market(market, result_data):
      
      Определить результат каждого исхода в маркете.
      
      Логика зависит от market_type:

        '1x2' (Исход матча):
          home_score = result_data['home_score']
          away_score = result_data['away_score']
          if home_score > away_score:
            outcomes['home'].result = 'won'
            outcomes['draw'].result = 'lost'
            outcomes['away'].result = 'lost'
          elif home_score == away_score:
            outcomes['home'].result = 'lost'
            outcomes['draw'].result = 'won'
            outcomes['away'].result = 'lost'
          else:
            outcomes['home'].result = 'lost'
            outcomes['draw'].result = 'lost'
            outcomes['away'].result = 'won'

        'total' (Тотал):
          total_goals = home_score + away_score
          parameter = market.parameter  # 2.5
          if total_goals > parameter:
            outcomes['over'].result = 'won'
            outcomes['under'].result = 'lost'
          elif total_goals < parameter:
            outcomes['over'].result = 'lost'
            outcomes['under'].result = 'won'
          else:  # точно равен (целый тотал: 2.0, 3.0)
            outcomes['over'].result = 'void'
            outcomes['under'].result = 'void'

        'handicap' (Фора):
          parameter = market.parameter  # -1.5
          adjusted_home = home_score + parameter
          if adjusted_home > away_score:
            outcomes['home'].result = 'won'
            outcomes['away'].result = 'lost'
          elif adjusted_home < away_score:
            outcomes['home'].result = 'lost'
            outcomes['away'].result = 'won'
          else:
            outcomes['home'].result = 'void'
            outcomes['away'].result = 'void'

        'both_to_score' (Обе забьют):
          if home_score > 0 and away_score > 0:
            outcomes['yes'].result = 'won'
            outcomes['no'].result = 'lost'
          else:
            outcomes['yes'].result = 'lost'
            outcomes['no'].result = 'won'

        'double_chance' (Двойной шанс):
          if home_score > away_score:
            # Победа хозяев
            outcomes['1x'].result = 'won'
            outcomes['12'].result = 'won'
            outcomes['x2'].result = 'lost'
          elif home_score == away_score:
            # Ничья
            outcomes['1x'].result = 'won'
            outcomes['12'].result = 'lost'
            outcomes['x2'].result = 'won'
          else:
            # Победа гостей
            outcomes['1x'].result = 'lost'
            outcomes['12'].result = 'won'
            outcomes['x2'].result = 'won'

        'exact_score' (Точный счёт):
          score_key = f"{home_score}-{away_score}"
          for outcome in outcomes:
            if outcome.code == score_key:
              outcome.result = 'won'
            else:
              outcome.result = 'lost'

        И так далее для каждого типа маркета...

      После определения результатов:
        market.status = 'settled'
        market.settled_at = now
        Для каждого outcome: outcome.settled_at = now


    @staticmethod
    def settle_bet(bet):
      
      Рассчитать конкретную ставку.
      
      Логика (АТОМАРНО):

        1. Обновить BetItem результаты:
           for item in bet.items.all():
             item.result = item.outcome.result
             item.settled_at = now if result != 'pending' else None

        2. Подсчитать:
           items_won = bet.items.filter(result='won').count()
           items_lost = bet.items.filter(result='lost').count()
           items_void = bet.items.filter(result='void').count()
           items_pending = bet.items.filter(result='pending').count()

        3. Если есть pending → ставка ещё не может быть рассчитана
           (для экспресса: ждём все события)
           Обновить счётчики и выйти

        4. Определить результат ставки:

           SINGLE:
             if item.result == 'won':
               bet.status = 'won'
               bet.actual_win = bet.stake × item.odd_at_placement
             elif item.result == 'lost':
               bet.status = 'lost'
               bet.actual_win = 0
             elif item.result == 'void':
               bet.status = 'void'
               bet.actual_win = bet.stake  # Возврат

           COMBO:
             if items_lost > 0:
               bet.status = 'lost'
               bet.actual_win = 0
             elif items_pending > 0:
               # Ещё ждём
               return
             elif items_void > 0 and items_won > 0:
               # Пересчитать коэфф без void
               adjusted_odd = 1.0
               for item in bet.items.all():
                 if item.result == 'won':
                   adjusted_odd *= item.odd_at_placement
                 # void пропускаем (коэфф 1.0)
               bet.status = 'won' if adjusted_odd > 1 else 'void'
               bet.actual_win = bet.stake × adjusted_odd
             elif all items won:
               bet.status = 'won'
               bet.actual_win = bet.stake × bet.total_odd
             elif all items void:
               bet.status = 'void'
               bet.actual_win = bet.stake

        5. Рассчитать profit:
           bet.profit = bet.actual_win - bet.stake

        6. ДЕНЕЖНЫЕ ОПЕРАЦИИ:
           
           if bet.status == 'won':
             # Забрать из frozen + зачислить выигрыш
             TransactionService.settle_bet(
               wallet=bet.wallet,
               currency=bet.currency.code,
               frozen_amount=bet.stake,
               win_amount=bet.actual_win,
               reference_type='bet',
               reference_id=bet.bet_id
             )
           
           elif bet.status == 'lost':
             # Забрать из frozen (деньги нам)
             TransactionService.settle_bet(
               wallet=bet.wallet,
               currency=bet.currency.code,
               frozen_amount=bet.stake,
               win_amount=0,
               reference_type='bet',
               reference_id=bet.bet_id
             )
           
           elif bet.status == 'void':
             # Разморозить (вернуть)
             TransactionService.unfreeze_funds(
               wallet=bet.wallet,
               currency=bet.currency.code,
               amount=bet.stake,
               reference_type='bet',
               reference_id=bet.bet_id
             )

        7. bet.settled_at = now
        8. bet.cashout_available = False

        9. Уведомить пользователя:
           if bet.status == 'won':
             "🏆 Ставка выиграла! +$105.00"
           elif bet.status == 'lost':
             "❌ Ставка проиграла: Реал — Барса"
           elif bet.status == 'void':
             "↩️ Ставка аннулирована: возврат $50.00"


    @staticmethod
    def void_event(event_id, admin_user, reason):
      
      Аннулировать событие (отмена матча).
      ВСЕ ставки возвращаются.
      
      Логика:
        1. event.status = 'cancelled'
        2. Все маркеты → status = 'void'
        3. Все outcomes → result = 'void'
        4. Все ставки → settle_bet() (вернут деньги)
```

### CashoutService (services/cashout_service.py)

```
class CashoutService:

    Назначение:
      Досрочный расчёт ставки (кэшаут).
      Пользователь может забрать часть выигрыша
      до окончания события.

    Методы:
    ───────

    @staticmethod
    def calculate_cashout(bet):
      
      Рассчитать текущий кэшаут.
      
      Формула:
        cashout_value = stake
        
        for item in bet.items:
          if item.result == 'won':
            cashout_value *= item.odd_at_placement
          elif item.result == 'pending':
            current_odd = item.outcome.odd  # текущий
            cashout_value *= current_odd
          elif item.result == 'void':
            # Не влияет (коэфф 1.0)
            pass
          elif item.result == 'lost':
            return 0  # Кэшаут невозможен

        # Применить маржу (платформа берёт 10%)
        margin = BetSettings.get_settings().cashout_margin  # 0.90
        cashout_value *= margin

        # Округлить
        cashout_value = round(cashout_value, 2)

        # Минимум
        if cashout_value < settings.cashout_min_amount:
          return 0

        return cashout_value

      Пример:
        Ставка $50, коэфф 2.10
        Текущий коэфф стал 1.50 (команда ведёт)
        Справедливый кэшаут = $50 × 1.50 = $75
        С маржой 90%: $75 × 0.90 = $67.50
        Пользователь получает $67.50 вместо $50 ставки
        (мог бы получить $105 если выиграет)


    @staticmethod
    def execute_cashout(bet_id, user):
      
      Выполнить кэшаут.
      
      Логика (АТОМАРНО):
        1. bet = Bet.select_for_update().get(id=bet_id)
        2. Проверить: bet.user == user
        3. Проверить: bet.is_cashout_available()
        4. Рассчитать: cashout_amount = calculate_cashout(bet)
        5. Проверить: cashout_amount > 0

        6. Забрать frozen + зачислить кэшаут:
           TransactionService.settle_bet(
             wallet=bet.wallet,
             currency=bet.currency.code,
             frozen_amount=bet.stake,
             win_amount=cashout_amount,
             reference_type='cashout',
             reference_id=bet.bet_id
           )

        7. Обновить ставку:
           bet.status = 'cashed_out'
           bet.actual_win = cashout_amount
           bet.profit = cashout_amount - bet.stake
           bet.cashout_amount = cashout_amount
           bet.cashout_used_at = now
           bet.cashout_available = False
           bet.settled_at = now

        8. Уведомить пользователя:
           "💰 Кэшаут: +$67.50 (ставка BET-...)"
```

### OddsService (services/odds_service.py)

```
class OddsService:

    Назначение:
      Управление коэффициентами.
      Обновление из API.
      Ручное изменение.

    Методы:
    ───────

    @staticmethod
    def update_odd(outcome_id, new_odd, changed_by='admin'):
      
      Обновить коэффициент.
      
      Логика:
        1. outcome = Outcome.get(id=outcome_id)
        2. old_odd = outcome.odd
        3. Записать в OddHistory(old, new, changed_by)
        4. outcome.odd_previous = old_odd
        5. outcome.odd = new_odd
        6. outcome.odd_direction = 'up' if new > old else 'down'
        7. Сохранить
        8. Пересчитать кэшаут для всех pending ставок на этот исход


    @staticmethod
    def create_markets_for_event(event, odds_data=None):
      
      Создать маркеты и исходы для события.
      
      Если odds_data из API:
        Использовать полученные коэффициенты
      Если odds_data нет (ручной ввод):
        Создать маркеты с пустыми коэффициентами
        Админ заполнит потом

      Логика:
        1. Определить доступные маркеты по виду спорта
        2. Для каждого MarketType:
           a) Создать Market
           b) Создать Outcomes из outcomes_template
           c) Если есть odds_data → заполнить odd
        3. Обновить event.markets_count


    @staticmethod
    def bulk_update_odds(event_id, odds_data):
      
      Обновить коэффициенты из API данных.
      Пакетное обновление.
      
      odds_data формат:
        {
          "1x2": {"home": 2.10, "draw": 3.40, "away": 3.20},
          "total_2.5": {"over": 1.85, "under": 1.95},
          "handicap_-1.5": {"home": 3.50, "away": 1.28}
        }
```

### FeedService (services/feed_service.py)

```
class FeedService:

    Назначение:
      Получение данных из внешних API.
      Создание событий и обновление коэффициентов.

    Методы:
    ───────

    @staticmethod
    def sync_events_from_api(sport_slug, date=None):
      
      Celery задача. Синхронизация событий.
      
      Логика:
        1. Определить провайдера для спорта
        2. Получить список матчей на дату
        3. Для каждого матча:
           - Если уже есть в БД (external_id) → обновить
           - Если нет → создать Event + Markets + Outcomes
        4. Обновить events_count в Sport и League

    @staticmethod
    def sync_odds_from_api(event_id):
      
      Обновить коэффициенты для события.

    @staticmethod
    def sync_results_from_api(event_id):
      
      Получить результат матча из API.
      Если finished → settle_event()
```

### StatisticsService (services/statistics_service.py)

```
class StatisticsService:

    Назначение:
      Статистика пользователя по ставкам.

    Методы:
    ───────

    @staticmethod
    def get_user_stats(user, period='all'):
      
      Возвращает:
        {
          "total_bets": 147,
          "total_stake": "$7,350.00",
          "total_won": "$8,200.00",
          "total_profit": "+$850.00",
          "win_rate": "48.9%",
          "roi": "+11.6%",
          "average_odd": 2.34,
          "average_stake": "$50.00",
          "best_win": "$2,340.00",
          "worst_loss": "$500.00",
          "longest_win_streak": 7,
          "longest_loss_streak": 5,
          "by_sport": [
            {"sport": "Футбол", "bets": 80, "profit": "+$400"},
            {"sport": "Баскетбол", "bets": 45, "profit": "+$300"},
          ],
          "by_bet_type": {
            "single": {"count": 120, "profit": "+$500"},
            "combo": {"count": 27, "profit": "+$350"}
          },
          "monthly_chart": [
            {"month": "Январь", "profit": 200},
            {"month": "Февраль", "profit": -100},
            {"month": "Март", "profit": 750},
          ]
        }
```

### Критерий готовности шага 4.2

```
□ BettingService.place_single_bet — полная валидация + заморозка
□ BettingService.place_combo_bet — проверка конфликтов
□ BettingService.validate_bet_slip
□ BettingService.cancel_bet
□ SettlementService.settle_event — расчёт всех маркетов
□ SettlementService.settle_market — для каждого типа маркета
□ SettlementService.settle_bet — single и combo
□ SettlementService.void_event — отмена с возвратом
□ CashoutService.calculate_cashout — формула
□ CashoutService.execute_cashout — атомарно
□ OddsService.update_odd + история
□ OddsService.create_markets_for_event
□ FeedService — синхронизация из API
□ StatisticsService — статистика пользователя
□ Все операции атомарные
□ Все денежные операции через TransactionService
□ Уведомления при выигрыше/проигрыше
```

---

## ШАГ 4.3 — СТРАНИЦЫ СТАВОК

### Структура шаблонов

```
templates/sports/
├── index.html               # Главная спорта
├── sport_detail.html        # Вид спорта (футбол)
├── league_detail.html       # Лига (АПЛ)
├── event_detail.html        # Детали матча
├── my_bets.html             # Мои ставки
├── bet_detail.html          # Детали ставки
├── bet_history.html         # История ставок
├── statistics.html          # Статистика
├── components/
│   ├── event_card.html      # Карточка матча
│   ├── event_row.html       # Строка матча в списке
│   ├── bet_slip.html        # Купон ставки (sidebar)
│   ├── market_block.html    # Блок маркета
│   ├── outcome_button.html  # Кнопка коэффициента
│   ├── bet_card.html        # Карточка ставки в "Мои ставки"
│   ├── sport_sidebar.html   # Сайдбар видов спорта
│   ├── live_score.html      # Текущий счёт
│   └── odd_change.html      # Индикатор изменения коэффициента
└── admin/
    └── settle_event.html    # Форма расчёта события
```

### Главная страница спорта

```
URL: /sports/

  ┌──────────────────────────────────────────────────────────┐
  │                                                          │
  │  ┌─────────────┐  ┌──────────────────────────────────┐  │
  │  │ СПОРТ       │  │ ⚽ Ставки на спорт               │  │
  │  │             │  │                                    │  │
  │  │ ⚽ Футбол 42│  │ 🔥 Топ матчи                     │  │
  │  │ 🏀 Баскет 18│  │ ┌──────────────────────────────┐ │  │
  │  │ 🎾 Теннис 15│  │ │ ⚽ АПЛ                       │ │  │
  │  │ 🏒 Хоккей 8 │  │ │ Ман Сити — Ливерпуль         │ │  │
  │  │ 🥊 MMA    5 │  │ │ Сегодня 22:00               │ │  │
  │  │ 🎮 Кибер 12│  │ │ П1 [2.10] X [3.40] П2 [3.20]│ │  │
  │  │             │  │ │ +47 маркетов                 │ │  │
  │  │ ЛИГИ        │  │ └──────────────────────────────┘ │  │
  │  │             │  │ ┌──────────────────────────────┐ │  │
  │  │ 🏴 АПЛ     │  │ │ ⚽ Ла Лига                   │ │  │
  │  │ 🇪🇸 Ла Лига│  │ │ Реал Мадрид — Барселона      │ │  │
  │  │ 🇩🇪 Бундес │  │ │ Завтра 20:00                │ │  │
  │  │ 🇮🇹 Серия А│  │ │ П1 [1.95] X [3.60] П2 [3.80]│ │  │
  │  │ 🇫🇷 Лига 1 │  │ │ +52 маркетов                 │ │  │
  │  │ 🏆 ЛЧ      │  │ └──────────────────────────────┘ │  │
  │  │             │  │                                    │  │
  │  │ СЕГОДНЯ     │  │ ── Сегодня ─────────────────────  │  │
  │  │ 25 матчей   │  │                                    │  │
  │  │             │  │ ⚽ АПЛ                            │  │
  │  │ ЗАВТРА      │  │ Арсенал — Тоттенхэм  16:30       │  │
  │  │ 32 матча    │  │ [2.05] [3.50] [3.30]   +35       │  │
  │  │             │  │                                    │  │
  │  │             │  │ Челси — Ман Юнайтед    19:00      │  │
  │  │             │  │ [2.20] [3.30] [3.10]   +41       │  │
  │  │             │  │                                    │  │
  │  │             │  │ 🏀 НБА                           │  │
  │  │             │  │ Lakers — Warriors       04:00     │  │
  │  │             │  │ [1.75] [2.05]           +28       │  │
  │  │             │  │                                    │  │
  │  └─────────────┘  └──────────────────────────────────┘  │
  │                                                          │
  └──────────────────────────────────────────────────────────┘

  Левый sidebar (sport_sidebar.html):
    - Список видов спорта с количеством событий
    - Популярные лиги
    - Фильтры: Сегодня / Завтра / Все
    - Поиск по командам

  При клике на коэффициент:
    → Добавить в купон (bet_slip)
    → Кнопка подсвечивается зелёным
    → Купон появляется справа (или внизу на мобильных)

  HTMX:
    - Клик на коэффициент → hx-post добавить в купон
    - Фильтры → hx-get обновить список
    - Коэффициенты обновляются каждые 60 сек
```

### Детальная страница события

```
URL: /sports/event/{event_id}/

  ┌──────────────────────────────────────────────────────────┐
  │                                                          │
  │  ⚽ Английская Премьер-Лига                             │
  │  ─────────────────────────────────────────────          │
  │                                                          │
  │  ┌────────────────────────────────────────────────────┐ │
  │  │                                                    │ │
  │  │  Ман Сити          —          Ливерпуль            │ │
  │  │  [ЛОГО]           VS         [ЛОГО]               │ │
  │  │                                                    │ │
  │  │  📅 Сегодня, 22:00 (через 3ч 15мин)              │ │
  │  │  📺 Стадион: Этихад                               │ │
  │  │                                                    │ │
  │  └────────────────────────────────────────────────────┘ │
  │                                                          │
  │  [Все 52] [Популярные] [Голы] [Тотал] [Форы]          │
  │                                                          │
  │  ── Исход матча ──────────────────────────────────────  │
  │  ┌──────────┐  ┌──────────┐  ┌──────────┐            │
  │  │ П1       │  │ Ничья    │  │ П2       │            │
  │  │ 2.10  ↑  │  │ 3.40     │  │ 3.20  ↓  │            │
  │  └──────────┘  └──────────┘  └──────────┘            │
  │                                                          │
  │  ── Двойной шанс ────────────────────────────────────  │
  │  ┌──────────┐  ┌──────────┐  ┌──────────┐            │
  │  │ 1X       │  │ 12       │  │ X2       │            │
  │  │ 1.35     │  │ 1.30     │  │ 1.65     │            │
  │  └──────────┘  └──────────┘  └──────────┘            │
  │                                                          │
  │  ── Тотал ───────────────────────────────────────────  │
  │  ┌──────────────────┐  ┌──────────────────┐           │
  │  │ Больше 2.5  1.85 │  │ Меньше 2.5  1.95 │           │
  │  └──────────────────┘  └──────────────────┘           │
  │  ┌──────────────────┐  ┌──────────────────┐           │
  │  │ Больше 3.5  3.20 │  │ Меньше 3.5  1.33 │           │
  │  └──────────────────┘  └──────────────────┘           │
  │                                                          │
  │  ── Фора ────────────────────────────────────────────  │
  │  ┌──────────────────┐  ┌──────────────────┐           │
  │  │ Ф1 (-1.5)   3.50 │  │ Ф2 (+1.5)   1.28 │           │
  │  └──────────────────┘  └──────────────────┘           │
  │                                                          │
  │  ── Обе забьют ──────────────────────────────────────  │
  │  ┌──────────────────┐  ┌──────────────────┐           │
  │  │ Да          1.75 │  │ Нет          2.05 │           │
  │  └──────────────────┘  └──────────────────┘           │
  │                                                          │
  │  ── Точный счёт ─────────────────────────────────────  │
  │  ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐          │
  │  │1:0 │ │2:0 │ │2:1 │ │3:0 │ │3:1 │ │3:2 │          │
  │  │7.50│ │11.0│ │8.50│ │21.0│ │15.0│ │26.0│          │
  │  └────┘ └────┘ └────┘ └────┘ └────┘ └────┘          │
  │  ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐          │
  │  │0:0 │ │1:1 │ │2:2 │ │0:1 │ │0:2 │ │1:2 │          │
  │  │9.00│ │6.50│ │17.0│ │8.00│ │13.0│ │9.50│          │
  │  └────┘ └────┘ └────┘ └────┘ └────┘ └────┘          │
  │                                                          │
  │  И другие маркеты...                                    │
  │                                                          │
  └──────────────────────────────────────────────────────────┘

  Кнопка коэффициента:
    - Обычное состояние: bg-dod-card, белый текст
    - При наведении: bg чуть светлее
    - Выбрана (в купоне): bg-dod-accent, зелёная
    - Заблокирована: серая, не кликабельная
    - Стрелка ↑ (рост) — зелёная
    - Стрелка ↓ (падение) — красная

  HTMX:
    При клике на коэффициент:
      hx-post="/sports/api/bet-slip/add/"
      hx-vals='{"outcome_id": "..."}'
      hx-target="#bet-slip"
      hx-swap="outerHTML"
```

### Купон ставки (bet_slip.html)

```
Позиция: правый sidebar на десктопе, 
         нижняя панель на мобильных.
Всегда видим если есть исходы.

  ┌──────────────────────────────┐
  │  📋 Купон ставки            │
  │                              │
  │  ○ Одиночная  ● Экспресс   │
  │                              │
  │  ┌──────────────────────┐   │
  │  │ ⚽ Ман Сити — Ливер. │   │
  │  │ Исход: П1            │   │
  │  │ Коэфф: 2.10      ✕  │   │
  │  ├──────────────────────┤   │
  │  │ ⚽ Реал — Барса      │   │
  │  │ Тотал: Больше 2.5   │   │
  │  │ Коэфф: 1.85      ✕  │   │
  │  └──────────────────────┘   │
  │                              │
  │  Общий коэфф: 3.885        │
  │                              │
  │  Сумма ставки:              │
  │  ┌────────────────────────┐ │
  │  │ $              50.00   │ │
  │  └────────────────────────┘ │
  │  [$10] [$25] [$50] [$100]  │
  │                              │
  │  Возможный выигрыш:         │
  │  $194.25                    │
  │                              │
  │  [   Сделать ставку    ]    │
  │                              │
  │  [Очистить купон]           │
  │                              │
  └──────────────────────────────┘

  HTMX:
    Добавление: hx-post="/sports/api/bet-slip/add/"
    Удаление: hx-delete="/sports/api/bet-slip/remove/{id}/"
    Сумма: hx-post="/sports/api/bet-slip/calculate/"
           hx-trigger="keyup changed delay:300ms"
    Ставка: hx-post="/sports/api/bet-slip/place/"

  При размещении:
    - Кнопка блокируется
    - Показать спиннер
    - При успехе: "✅ Ставка принята!" + очистить купон
    - При ошибке: показать текст ошибки красным
    - Обновить баланс в navbar

  Хранение купона:
    В сессии Django (session)
    Структура:
      session['bet_slip'] = {
        "mode": "combo",  # single или combo
        "items": [
          {"outcome_id": "...", "odd": 2.10},
          {"outcome_id": "...", "odd": 1.85}
        ],
        "stake": 50.00
      }
```

### Мои ставки

```
URL: /my-bets/

  ┌──────────────────────────────────────────────────────────┐
  │  📋 Мои ставки                                          │
  │                                                          │
  │  [Активные (5)] [История] [Статистика]                  │
  │                                                          │
  │  ── Активные ставки ──────────────────────────────────  │
  │                                                          │
  │  ┌──────────────────────────────────────────────────┐   │
  │  │ BET-20250315-K8M2N4                Экспресс     │   │
  │  │                                                  │   │
  │  │ ✅ ⚽ Ман Сити — Ливер.    П1       2.10  ✓     │   │
  │  │ ⏳ ⚽ Реал — Барса        Б. 2.5    1.85  ●     │   │
  │  │                                                  │   │
  │  │ Ставка: $50.00    Коэфф: 3.885                 │   │
  │  │ Возм. выигрыш: $194.25                          │   │
  │  │                                                  │   │
  │  │ 💰 Кэшаут: $87.50  [Забрать]                   │   │
  │  │                                                  │   │
  │  │ Сделана: 15.03.2025 14:30                       │   │
  │  └──────────────────────────────────────────────────┘   │
  │                                                          │
  │  ┌──────────────────────────────────────────────────┐   │
  │  │ BET-20250315-M2N4P6                Одиночная    │   │
  │  │                                                  │   │
  │  │ ⏳ 🏀 Lakers — Warriors   П1       1.75  ●     │   │
  │  │                                                  │   │
  │  │ Ставка: $100.00    Коэфф: 1.750                │   │
  │  │ Возм. выигрыш: $175.00                          │   │
  │  │                                                  │   │
  │  │ 💰 Кэшаут: $112.00  [Забрать]                  │   │
  │  │                                                  │   │
  │  └──────────────────────────────────────────────────┘   │
  │                                                          │
  └──────────────────────────────────────────────────────────┘

  Статусы:
    ⏳ — ожидает (событие не началось)
    🔄 — в процессе (событие идёт)
    ✅ — этот исход выиграл
    ❌ — этот исход проиграл
    ↩️ — аннулирован (void)

  Кэшаут:
    Обновляется HTMX каждые 30 сек
    hx-get="/sports/api/cashout/{bet_id}/"
    При нажатии "Забрать":
      hx-post="/sports/api/cashout/{bet_id}/execute/"
      Подтверждение: "Забрать $87.50?"
```

### Критерий готовности шага 4.3

```
□ /sports/ — главная с sidebar, топ матчи, фильтры
□ /sports/{sport}/ — события по виду спорта
□ /sports/league/{league_id}/ — события по лиге
□ /sports/event/{event_id}/ — детали матча со всеми маркетами
□ Купон ставки (bet_slip) — добавление, удаление, расчёт
□ Размещение ставки (single и combo) через HTMX
□ /my-bets/ — активные ставки с кэшаутом
□ /my-bets/history/ — история с фильтрами
□ /my-bets/{bet_id}/ — детали ставки
□ /my-bets/statistics/ — статистика
□ Кнопки коэффициентов с индикацией изменений
□ Поиск по командам и событиям
□ Все страницы: тёмная тема, мобильная адаптация
□ HTMX: купон, кэшаут, фильтры без перезагрузки
```

---

## ШАГ 4.4 — CELERY ЗАДАЧИ + ИНТЕГРАЦИЯ API

### Файл tasks.py

```
sync_football_events():
    Каждые 6 часов.
    Получить матчи из API-Football на ближайшие 7 дней.
    Создать/обновить Event, Market, Outcome.
    Обновить коэффициенты.

sync_odds():
    Каждые 30 минут.
    Обновить коэффициенты из TheOddsAPI.
    Для всех prematch событий.

check_event_results():
    Каждые 5 минут.
    Для событий где start_time < now - 2 часа и status != 'finished':
      Проверить результат в API.
      Если finished → settle_event().

close_expired_events():
    Каждую минуту.
    События где start_time < now и status == 'prematch':
      → status = 'live' (или 'suspended')
      → Закрыть все маркеты.
      → Закрыть все исходы.

recalculate_cashouts():
    Каждые 5 минут.
    Для всех pending ставок:
      Пересчитать cashout_amount.

daily_betting_report():
    Каждый день в 09:00.
    Отчёт:
      - Всего ставок: N
      - Общая сумма: $X
      - Выплачено: $Y
      - GGR (доход): $Z
      - Топ событие по ставкам
      - Топ пользователь по ставкам

cleanup_old_bet_slips():
    Каждый час.
    Удалить из сессий купоны старше 24 часов.

update_events_count():
    Каждые 30 минут.
    Обновить events_count в Sport и League.
```

### Критерий готовности шага 4.4

```
□ Sync события из API-Football
□ Sync коэффициенты из TheOddsAPI
□ Автоматическая проверка результатов
□ Автоматическое закрытие ставок при начале матча
□ Автоматический расчёт ставок
□ Пересчёт кэшаутов
□ Ежедневный отчёт
□ Обработка ошибок API
□ Fallback на ручной ввод при недоступности API
```

---

## 📊 ОБЩИЙ ЧЕКЛИСТ ЭТАПА 4

```
МОДЕЛИ:
  □ Sport (12 видов спорта)
  □ Country
  □ League
  □ Team
  □ Event (полная модель с result_details)
  □ MarketType (15+ типов)
  □ Market
  □ Outcome (с историей коэффициентов)
  □ Bet (single + combo)
  □ BetItem
  □ BetSettings (singleton)
  □ OddHistory

СЕРВИСЫ:
  □ BettingService (place_single, place_combo, validate, cancel)
  □ SettlementService (settle_event, settle_market, settle_bet, void)
  □ CashoutService (calculate, execute)
  □ OddsService (update, create_markets, bulk_update)
  □ FeedService (sync events, odds, results)
  □ StatisticsService

СТРАНИЦЫ:
  □ /sports/ — главная
  □ /sports/{sport}/ — по виду спорта
  □ /sports/league/{id}/ — по лиге
  □ /sports/event/{id}/ — детали матча (все маркеты)
  □ Купон ставки (sidebar)
  □ /my-bets/ — активные ставки
  □ /my-bets/history/ — история
  □ /my-bets/{id}/ — детали
  □ /my-bets/statistics/ — статистика

ФУНКЦИОНАЛ:
  □ Одиночная ставка
  □ Экспресс ставка (с проверкой конфликтов)
  □ Кэшаут (расчёт + выполнение)
  □ Расчёт ставок (авто + ручной)
  □ Отмена события (void)
  □ Изменение коэффициентов
  □ Поиск по командам
  □ Фильтры (спорт, лига, дата)

ИНТЕГРАЦИЯ:
  □ API-Football (события)
  □ TheOddsAPI (коэффициенты)
  □ Ручной ввод через админку
  □ Автоматическая синхронизация

CELERY:
  □ Sync событий
  □ Sync коэффициентов
  □ Проверка результатов
  □ Закрытие ставок при начале
  □ Пересчёт кэшаутов
  □ Ежедневный отчёт

БЕЗОПАСНОСТЬ:
  □ Атомарные операции
  □ Заморозка средств при ставке
  □ Коэффициент фиксируется
  □ Валидация всех параметров
  □ Rate limiting
  □ Лимиты ставок (мин/макс)

АДМИНКА:
  □ Управление спортами и лигами
  □ Управление событиями
  □ Управление маркетами и коэффициентами
  □ Расчёт событий (кастомная форма)
  □ Просмотр ставок
  □ Настройки ставок
```

---

```
╔══════════════════════════════════════════════════════╗
║                                                      ║
║   ЭТАП 4 ЗАВЕРШЁН                                   ║
║                                                      ║
║   Следующий: ЭТАП 5                                 ║
║   Казино (Crash, Slots, Roulette, Mines, Dice,      ║
║   Plinko + Provably Fair)                            ║
║                                                      ║
║   Продолжить?                                       ║
║                                                      ║
╚══════════════════════════════════════════════════════╝
```