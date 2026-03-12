# 📋 Документация модуля "Ставки на спорт" (Sports)

## 🎯 Обзор

Полнофункциональный модуль букмекерской платформы для ставок на спорт с поддержкой:
- ✅ Одиночных и экспресс-ставок
- ✅ Множественных видов спорта и лиг
- ✅ Различных типов маркетов (1X2, Тотал, Фора, и т.д.)
- ✅ Система коэффициентов с историей изменений
- ✅ Кэшаут (досрочный расчёт)
- ✅ Расчёт ставок с поддержкой различных видов спорта
- ✅ Интегрированное управление кошельком

---

## 📁 Структура приложения

```
apps/sports/
├── models.py              # Модели: Sport, Event, Market, Bet и т.д.
├── views.py               # Views: спорт, события, ставки, API endpoints
├── urls.py                # URL маршруты
├── admin.py               # Django Admin интерфейс
├── forms.py               # Django формы (placeholder)
├── signals.py             # Сигналы Django (placeholder)
├── tasks.py               # Celery задачи (async обработка)
├── services/
│   ├── betting_service.py      # 🎯 Приём ставок (BettingService)
│   ├── settlement_service.py   # 📊 Расчёт ставок (SettlementService)
│   ├── cashout_service.py      # 💰 Кэшаут (CashoutService)
│   ├── odds_service.py         # 📈 Управление коэффициентами (OddsService)
│   └── feed_service.py         # 🔄 Получение данных из API (TODO)
├── templates/
│   └── sports/
│       ├── sports_list.html           # Список видов спорта
│       ├── sport_detail.html          # Детали вида спорта
│       ├── event_detail.html          # 🎫 Детали события с купоном ставок
│       ├── events_upcoming.html       # Предстоящие события
│       ├── user_bets.html             # Мои ставки
│       ├── bet_detail.html            # Детали ставки
│       └── includes/
│           └── event_card_compact.html  # Компонент карточки события
├── fixtures/
│   └── sports_initial.json    # Начальные данные (виды спорта, лиги)
├── tests/
├── migrations/
└── apps.py
```

---

## 🚀 Быстрый старт

### Установка

```bash
# 1. Применить миграции
python manage.py migrate sports

# 2. Загрузить начальные данные
python manage.py loaddata fixtures/sports_initial.json

# 3. Зайти в админку и начать создавать события
# http://localhost:8000/admin/sports/
```

### Создание события (в админке)

1. **Sports → Events → Add Event**
2. Выбрать спорт, лигу, команды
3. Установить время начала
4. Установить статус **"prematch"** для приёма ставок
5. Добавить маркеты и исходы с коэффициентами

---

## 📊 Основные компоненты

### 1. **Models** (Модели)

#### `Sport` - Вид спорта
```python
Sport.objects.create(
    name="Футбол",
    name_en="Football",
    slug="football",
    icon="⚽",
    is_popular=True
)
```

#### `Event` - Спортивное событие (матч)
```python
Event(
    sport=football,
    league=premier_league,
    home_team=manchester_united,
    away_team=liverpool,
    start_time=timezone.now() + timedelta(days=1),
    status='prematch',
    is_bettable=True  # Метод
)
```

#### `Market` - Тип ставки
```
1X2, Total, Handicap, Both to Score и т.д.
```

#### `Bet` - Ставка пользователя
```python
# Одиночная ставка
bet = Bet(
    user=user,
    bet_type='single',  # или 'combo'
    stake=100,
    total_odd=2.10,
    potential_win=210,
    status='pending'  # pending → won/lost/void/cashed_out
)

# Методы:
bet.is_settled()              # True если не pending
bet.is_cashout_available()     # Доступен ли кэшаут
bet.calculate_cashout_amount() # Рассчитать сумму кэшаута
```

---

### 2. **Services** (Бизнес-логика)

#### 🎯 **BettingService** - Приём ставок

```python
from apps.sports.services.betting_service import BettingService

# Одиночная ставка
result = BettingService.place_single_bet(
    user=request.user,
    outcome_id='uuid-here',
    stake=100.00,
    currency_code='USD',
    ip_address=request.META.get('REMOTE_ADDR'),
    user_agent=request.META.get('HTTP_USER_AGENT')
)
# {
#   "success": True,
#   "bet_id": "BET-20250315-K8M2N4",
#   "message": "✅ Ставка принята!"
# }

# Экспресс
result = BettingService.place_combo_bet(
    user=request.user,
    items=[
        {"outcome_id": "uuid1"},
        {"outcome_id": "uuid2"},
        {"outcome_id": "uuid3"}
    ],
    stake=100.00,
    currency_code='USD',
    ip_address=request.META.get('REMOTE_ADDR')
)

# Валидация купона без размещения
validation = BettingService.validate_bet_slip([
    {"outcome_id": "uuid1"},
    {"outcome_id": "uuid2"}
])
# {
#   "valid": True/False,
#   "total_odd": 6.30,
#   "errors": [],
#   "conflicts": []
# }

# Отмена ставки (админ)
BettingService.cancel_bet(bet_id, admin_user, "Reason")
```

**Валидация ставок:**
- ✅ Событие в статусе `prematch`
- ✅ Маркет `open`
- ✅ Исход активен и не приостановлен
- ✅ Коэффициент в допустимом диапазоне
- ✅ Ставка в диапазоне min-max
- ✅ Недостаточно средств
- ✅ Лимит ставок на событие
- ✅ Никакого двойного принятия на событие в экспрессе

---

#### 📊 **SettlementService** - Расчёт ставок

```python
from apps.sports.services.settlement_service import SettlementService

# Рассчитать событие
result = SettlementService.settle_event(
    event_id=event_uuid,
    result_data={
        'home_score': 2,
        'away_score': 1,
        'ht_home_score': 1,  # Счёт 1-го тайма
        'ht_away_score': 0
    },
    settled_by=admin_user  # Кто рассчитал
)

# Отменить событие (вернуть все ставки)
SettlementService.void_event(
    event_id=event_uuid,
    admin_user=admin_user,
    reason="Match cancelled"
)
```

**Поддержка типов маркетов:**
- 1X2 (Исход)
- 12 (Победитель без ничьи)
- Total (Тотал)
- Handicap (Фора)
- Both to Score (Обе забьют)
- Double Chance (Двойной шанс)
- Exact Score (Точный счёт)
- HT Result (Результат 1 тайма)

---

#### 💰 **CashoutService** - Кэшаут

```python
from apps.sports.services.cashout_service import CashoutService

# Информация о кэшауте
info = CashoutService.get_cashout_info(bet)
# {
#   "available": True,
#   "amount": 125.50,  # Текущая предложение
#   "profit_if_cashout": 25.50,
#   "items_pending": 2
# }

# Выполнить кэшаут
result = CashoutService.place_cashout(bet_id, user)
# {
#   "success": True,
#   "cashout_amount": 125.50,
#   "message": "✅ Кэшаут завершён!"
# }
```

---

#### 📈 **OddsService** - Управление коэффициентами

```python
from apps.sports.services.odds_service import OddsService

# Обновить коэффициент
result = OddsService.update_odd(
    outcome_id='uuid-here',
    new_odd=2.50,
    changed_by='admin',  # или 'api', 'system'
    reason=''
)

# История коэффициентов
history = OddsService.get_odd_history(outcome_id, limit=50)

# Приостановить исход
OddsService.suspend_outcome(outcome_id, reason='Injury')

# Возобновить исход
OddsService.resume_outcome(outcome_id)

# Откатить коэффициент
OddsService.rollback_odds(outcome_id, steps=3)
```

---

### 3. **Views & API Endpoints**

#### Pages

| URL | View | Описание |
|-----|------|---------|
| `/sports/` | SportsListView | Список видов спорта |
| `/sports/<slug>/` | SportDetailView | Детали спорта с лигами |
| `/sports/events/<uuid>/` | EventDetailView | 🎫 Событие с купоном |
| `/sports/events/upcoming/` | EventsUpcomingView | Ближайшие события |
| `/sports/bets/` | UserBetsView | Мои ставки |
| `/sports/bets/<uuid>/` | BetDetailView | Детали ставки |

#### API Endpoints

```javascript
// Одиночная ставка
POST /sports/api/bets/single/
{
  outcome_id: "uuid",
  stake: 100,
  currency: "USD"
}

// Экспресс
POST /sports/api/bets/combo/
{
  items: [{outcome_id: "uuid1"}, {outcome_id: "uuid2"}],
  stake: 100,
  currency: "USD"
}

// Кэшаут
POST /sports/api/bets/{bet_id}/cashout/

// Валидация купона
GET /sports/api/bet-slip/validate/?items=[...]

// Маркеты события
GET /sports/api/events/{event_id}/markets/
```

---

### 4. **Admin Interface** (Админ-панель)

#### Возможности

✅ **Events**
- Просмотр и управление события
- Открыть/закрыть/приостановить ставки
- Отметить как избранное
- Рассчитать событие (вычислить результат)
- Отменить событие (вернуть ставки)
- Фильтры по спорту, лиге, статусу
- Иерархия дат для быстрой навигации

✅ **Markets**
- Создание маркетов для событий
- Внутристроковое редактирование коэффициентов
- Статусы маркета (open, suspended, closed)
- Inline редактирование исходов

✅ **Outcomes**
- Редактирование коэффициентов в реальном времени
- История изменений коэффициентов
- Визуальное отображение направления движения (↑/↓)
- Статусы результата (pending, won, lost, void)

✅ **Bets**
- Просмотр всех ставок с деталями
- Фильтры по пользователю, типу, статусу
- Отмена активных ставок
- Поиск по ID или email пользователя

✅ **Odds History**
- История всех изменений коэффициентов
- Timeline просмотра изменений

---

## 🎨 Frontend Components

### Компактная карточка события

```html
{% include 'sports/includes/event_card_compact.html' %}
```

### Купон ставок (в event_detail.html)

Интерактивный купон с:
- ✅ Добавлением/удалением исходов
- ✅ Автоматическим расчётом коэффициентов
- ✅ Выбором сумма и типа ставки
- ✅ Показом потенциального выигрыша
- ✅ Валидацией перед размещением

---

## ⚙️ Настройки (BetSettings)

```python
BetSettings.objects.get_or_create(id=1)

# Параметры:
min_stake_usd = 0.50           # Минимальная ставка
max_stake_usd = 50000          # Максимальная ставка
max_potential_win_usd = 100000 # Максимальный выигрыш с одной ставки
max_combo_items = 20           # Максимум событий в экспрессе
min_combo_items = 2            # Минимум
min_odd = 1.01                 # Мин коэффициент
max_odd = 1000.0               # Макс коэффициент
cashout_enabled = True         # Включен ли кэшаут
cashout_margin = 0.90          # Маржа кэшаута (90%)
cashout_min_amount = 1.00      # Минимальная сумма
delay_before_start_minutes = 1 # Закрытие ставок за 1 мин до начала
auto_settle_enabled = True     # Автоматический расчёт
```

---

## 🔄 Статусы и переходы

### Event Status
```
scheduled → prematch → [live | suspended] → finished
                ↓→ postponed
                ↓→ cancelled
```

### Bet Status
```
pending → [won | lost | void | cashed_out | cancelled]
```

### Market Status
```
open → [suspended | closed | settled | void]
```

---

## 🧪 Примеры использования

### Пример 1: Размещение одиночной ставки

```python
from apps.sports.services.betting_service import BettingService

try:
    result = BettingService.place_single_bet(
        user=request.user,
        outcome_id='12345678-1234-1234-1234-123456789012',
        stake=100,
        currency_code='USD',
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT')
    )
    print(f"Ставка {result['bet_id']} принята")
    
except BettingService.EventNotBettableError:
    print("Событие не доступно для ставок")
except BettingService.InsufficientFundsError as e:
    print(f"Недостаточно средств: {e}")
except BettingService.StakeLimitError as e:
    print(f"Ошибка ставки: {e}")
```

### Пример 2: Расчёт события

```python
from apps.sports.services.settlement_service import SettlementService

event = Event.objects.get(id='event-uuid')

result = SettlementService.settle_event(
    event_id=event.id,
    result_data={
        'home_score': 2,
        'away_score': 1,
        'ht_home_score': 1,
        'ht_away_score': 0
    },
    settled_by=admin_user
)

print(f"Рассчитано ставок: {result['settled_count']}")
print(f"Выигрыши: {result['won_count']}")
print(f"Проигрыши: {result['lost_count']}")
```

---

## 📱 UX Improvements

✨ **Реализованные улучшения:**

1. **Визуальные компоненты**
   - Цветные бейджи для статусов (pending 🔵, won ✅, lost ❌)
   - Эмодзи для быстрой визуальной идентификации
   - Адаптивный дизайн (мобильный-friendly)

2. **Интеракция**
   - Интерактивный купон ставок с real-time расчётом
   - AJAX для размещения ставок без перезагрузки
   - Валидация перед отправкой

3. **Информативность**
   - Статистика события (количество ставок, сумма)
   - История коэффициентов (визуализация движения)
   - Информация о потенциальном выигрыше

4. **Навигация**
   - Breadcrumbs для ориентации
   - Быстрые фильтры по статусу ставок
   - Поиск по ID/email

---

## 🔒 Безопасность

- ✅ **Transaction atomicity** - все операции с деньгами атомарные
- ✅ **Select for update** - блокировка рас при одновременных операциях
- ✅ **IP tracking** - сохранение IP адреса ставка для анти-фрода
- ✅ **User agent** - сохранение информации о браузере
- ✅ **Frozen funds** - замороженные средства на счёте
- ✅ **Permissions** - проверка прав доступа

---

## 🚀 Что ещё можно добавить

- [ ] Живые ставки (Live Betting)
- [ ] API провайдеры (API-Football, TheOddsAPI)
- [ ] WebSocket для real-time обновления коэффициентов
- [ ] Система бонусов для ставок
- [ ] Статистика и графики
- [ ] Аналитика (время ставок, популярные маркеты)
- [ ] Системные ставки (позже)
- [ ] Мобильное приложение

---

## 📞 Контакты и поддержка

Для вопросов по реализации свяжитесь с техподдержкой или откройте issue в репозитории.

---

**Версия:** 1.0  
**Дата:** 13 марта 2025  
**Статус:** ✅ Готово к использованию
