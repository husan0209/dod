

# 📋 ТЗ ПРОЕКТА DOD — ЭТАП 5

# КАЗИНО (СВОИ ИГРЫ + PROVABLY FAIR)

```
╔══════════════════════════════════════════════════════╗
║                                                      ║
║   ПРОЕКТ:    DOD                                    ║
║   ЭТАП:      5 из 12                                ║
║   НАЗВАНИЕ:  Казино                                 ║
║   ЗАВИСИТ:   Этапы 1-4                              ║
║                                                      ║
║   ЦЕЛЬ:      6 своих игр: Crash, Slots, Roulette,  ║
║              Mines, Dice, Plinko.                   ║
║              Provably Fair для каждой игры.          ║
║              Живая лента выигрышей.                 ║
║              Подготовка к интеграции провайдеров.   ║
║                                                      ║
╚══════════════════════════════════════════════════════╝
```

---

## 📌 КОНТЕКСТ ДЛЯ ИИ-АГЕНТА

```
Ты продолжаешь разработку проекта DOD.
Этапы 1-4 (авторизация, кошелёк, платежи, спорт) готовы.

Сейчас ты создаёшь модуль казино с 6 играми.
Все игры — СВОИ, написаны нами.
Позже добавятся провайдеры (Pragmatic Play, Evolution).

КЛЮЧЕВЫЕ ПРИНЦИПЫ:

  1. Криптографический RNG:
     ТОЛЬКО import secrets
     НИКОГДА import random
     secrets.token_bytes() для генерации

  2. Provably Fair:
     Каждая игра ДОКАЗУЕМО честная.
     Пользователь может проверить результат.
     Схема: server_seed + client_seed + nonce → результат
     Server seed хешируется ДО игры.
     После игры seed раскрывается.

  3. House Edge (преимущество казино):
     Crash: 3%
     Slots: 4% (RTP 96%)
     Roulette: 2.7% (один 0)
     Mines: 2%
     Dice: 2%
     Plinko: 3%
     Настраивается через админку.

  4. Все операции через TransactionService:
     Ставка → freeze или сразу debit
     Выигрыш → credit
     Проигрыш → средства остаются списанными

  5. Антифрод:
     Лимиты ставок
     Детекция ботов
     Логирование всех игр
```

---

## ШАГ 5.1 — МОДЕЛИ КАЗИНО

### Структура приложения

```
apps/casino/
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
│   ├── casino_service.py         # Общая логика
│   └── provably_fair.py          # Provably Fair система
├── games/
│   ├── __init__.py
│   ├── base.py                   # Абстрактная игра
│   ├── crash.py                  # Crash
│   ├── slots.py                  # Slots
│   ├── roulette.py               # Roulette
│   ├── mines.py                  # Mines
│   ├── dice.py                   # Dice
│   └── plinko.py                 # Plinko
├── templatetags/
│   ├── __init__.py
│   └── casino_tags.py
├── tests/
│   └── ...
├── templates/
│   └── casino/
│       ├── index.html            # Главная казино
│       ├── crash.html
│       ├── slots.html
│       ├── roulette.html
│       ├── mines.html
│       ├── dice.html
│       ├── plinko.html
│       ├── fairness.html         # Проверка честности
│       ├── history.html          # История игр
│       └── components/
│           ├── game_card.html
│           ├── bet_form.html
│           ├── recent_bets.html
│           ├── big_wins.html
│           └── fairness_check.html
└── migrations/
    └── __init__.py
```

### Модель GameType (models.py)

```
class GameType(models.Model):

    Назначение:
      Справочник типов игр.

    Поля:
    ─────
    code:
      тип: CharField, max 50, primary key
      Значения: 'crash', 'slots', 'roulette',
                'mines', 'dice', 'plinko'

    name:
      тип: CharField, max 100
      'Crash', 'Слоты', 'Рулетка', 'Mines', 'Dice', 'Plinko'

    name_en:
      тип: CharField, max 100

    description:
      тип: TextField
      Описание игры для пользователя

    icon:
      тип: CharField, max 50
      '📈', '🎰', '🎡', '💣', '🎲', '📌'

    thumbnail:
      тип: ImageField, nullable
      Превью картинка игры

    house_edge:
      тип: DecimalField, max_digits=5, decimal_places=2
      Преимущество казино в процентах
      Crash: 3.00, Slots: 4.00, Roulette: 2.70

    rtp:
      тип: DecimalField, max_digits=5, decimal_places=2
      Return To Player = 100 - house_edge
      Crash: 97.00, Slots: 96.00, Roulette: 97.30

    min_bet:
      тип: DecimalField
      Минимальная ставка (USD)
      default=0.10

    max_bet:
      тип: DecimalField
      Максимальная ставка (USD)
      default=10000

    max_win_multiplier:
      тип: DecimalField
      Максимальный множитель выигрыша
      Crash: 1000000, Slots: 5000, Roulette: 36
      Mines: 25, Dice: 9900, Plinko: 1000

    is_active:
      тип: BooleanField, default=True

    is_popular:
      тип: BooleanField, default=False

    is_new:
      тип: BooleanField, default=False
      Показывать бейдж "NEW"

    total_bets:
      тип: BigIntegerField, default=0
      Всего ставок сделано

    total_wagered_usd:
      тип: DecimalField, default=0
      Всего поставлено (USD)

    total_won_usd:
      тип: DecimalField, default=0
      Всего выплачено (USD)

    sort_order:
      тип: IntegerField, default=0

    created_at:
      тип: DateTimeField, auto_now_add

    Meta:
      verbose_name = 'Тип игры'
      ordering = ['sort_order']
```

### Модель GameSession (models.py)

```
class GameSession(models.Model):

    Назначение:
      Каждая игра = одна GameSession.
      Хранит ВСЕ данные игры.
      Неизменяемый после завершения.

    Поля:
    ─────
    id:
      тип: UUID, primary key

    game_id:
      тип: CharField, max 50, уникальный
      Формат: {GAME}-{timestamp}-{random6}
      Пример: CRA-20250315-A7B3C2 (crash)
              SLO-20250315-K8M2N4 (slots)
              ROU-20250315-X4Y5Z6 (roulette)

    user:
      тип: ForeignKey → User
      related_name: 'casino_games'

    wallet:
      тип: ForeignKey → Wallet

    game_type:
      тип: ForeignKey → GameType

    currency:
      тип: ForeignKey → Currency

    bet_amount:
      тип: DecimalField
      Сумма ставки

    bet_amount_usd:
      тип: DecimalField

    win_amount:
      тип: DecimalField, default=0
      Сумма выигрыша (0 если проиграл)

    win_multiplier:
      тип: DecimalField, default=0
      Множитель выигрыша (2.5x, 10x, 36x)

    profit:
      тип: DecimalField, default=0
      win_amount - bet_amount

    status:
      тип: CharField
      choices:
        ('active', 'Активна')          # Для Crash, Mines (игра идёт)
        ('won', 'Выигрыш')
        ('lost', 'Проигрыш')
        ('cashout', 'Кэшаут')          # Для Crash
        ('cancelled', 'Отменена')
      default: 'active'

    game_data:
      тип: JSONField, default=dict
      Данные конкретной игры
      
      Crash:
        {
          "crash_point": 2.47,
          "cashout_at": 2.10,        # null если не успел
          "auto_cashout": 2.00       # null если ручной
        }
      
      Slots:
        {
          "reels": [[3,1,5], [2,3,1], [5,5,5]],
          "paylines": [
            {"line": 1, "symbols": [5,5,5], "multiplier": 50}
          ],
          "total_multiplier": 50,
          "free_spins_won": 0
        }
      
      Roulette:
        {
          "winning_number": 17,
          "winning_color": "black",
          "bets": [
            {"type": "red", "amount": 10, "won": false, "payout": 0},
            {"type": "number_17", "amount": 5, "won": true, "payout": 180}
          ]
        }
      
      Mines:
        {
          "field_size": 25,           # 5x5
          "mines_count": 5,
          "mines_positions": [3,7,12,18,22],  # Скрыто до конца
          "revealed": [0,1,4,5,8],
          "current_multiplier": 1.58,
          "is_mine_hit": false
        }
      
      Dice:
        {
          "target": 50.00,           # Цель (0-100)
          "condition": "over",       # over или under
          "result": 67.34,           # Результат
          "multiplier": 2.00,
          "win_chance": 50.00        # % шанса
        }
      
      Plinko:
        {
          "rows": 16,
          "risk": "medium",          # low, medium, high
          "path": [1,0,1,1,0,0,1,0,1,1,0,1,0,0,1,1],
          "landing_position": 8,
          "multiplier": 3.0
        }

    server_seed:
      тип: CharField, max 64
      Серверный seed (hex)
      РАСКРЫВАЕТСЯ после игры

    server_seed_hash:
      тип: CharField, max 64
      SHA-256 хеш server_seed
      ПОКАЗЫВАЕТСЯ ДО игры

    client_seed:
      тип: CharField, max 64
      Клиентский seed (устанавливает пользователь)

    nonce:
      тип: BigIntegerField
      Порядковый номер игры для пользователя
      Увеличивается на 1 с каждой игрой

    is_verified:
      тип: BooleanField, default=False
      Проверил ли пользователь честность

    bet_transaction:
      тип: ForeignKey → Transaction, nullable
      Транзакция списания ставки

    win_transaction:
      тип: ForeignKey → Transaction, nullable
      Транзакция зачисления выигрыша

    ip_address:
      тип: GenericIPAddressField

    started_at:
      тип: DateTimeField, auto_now_add

    completed_at:
      тип: DateTimeField, nullable

    Meta:
      verbose_name = 'Игровая сессия'
      ordering = ['-started_at']
      indexes:
        - user + started_at
        - game_type + started_at
        - status
        - game_id
```

### Модель CrashGame (models.py)

```
class CrashGame(models.Model):

    Назначение:
      Общая раунд Crash игры.
      ОДИН раунд = МНОГО игроков.
      Все видят одну и ту же точку краша.

    Поля:
    ─────
    id:
      тип: UUID, primary key

    round_id:
      тип: CharField, max 50, уникальный
      Формат: CRASH-{number}
      Пример: CRASH-000001

    crash_point:
      тип: DecimalField, max_digits=10, decimal_places=2
      Точка краша: 1.00, 2.47, 100.50, 1000.00

    status:
      тип: CharField
      choices:
        ('waiting', 'Ожидание ставок')    # 10 сек
        ('running', 'Идёт')                # коэфф растёт
        ('crashed', 'Упал')                # раунд окончен
      default: 'waiting'

    server_seed:
      тип: CharField, max 64

    server_seed_hash:
      тип: CharField, max 64

    previous_game:
      тип: ForeignKey → self, nullable
      Предыдущий раунд (для цепочки)

    chain_hash:
      тип: CharField, max 64
      Хеш цепочки: SHA256(server_seed + previous_hash)
      Для доказательства что seed не менялся

    players_count:
      тип: IntegerField, default=0

    total_bet:
      тип: DecimalField, default=0

    total_payout:
      тип: DecimalField, default=0

    started_at:
      тип: DateTimeField, nullable
      Когда начал расти коэффициент

    crashed_at:
      тип: DateTimeField, nullable
      Когда упал

    created_at:
      тип: DateTimeField, auto_now_add

    Meta:
      verbose_name = 'Раунд Crash'
      ordering = ['-created_at']
```

### Модель CrashBet (models.py)

```
class CrashBet(models.Model):

    Назначение:
      Ставка конкретного игрока в раунде Crash.

    Поля:
    ─────
    id:
      тип: UUID, primary key

    crash_game:
      тип: ForeignKey → CrashGame
      related_name: 'bets'

    game_session:
      тип: OneToOneField → GameSession

    user:
      тип: ForeignKey → User

    bet_amount:
      тип: DecimalField

    currency:
      тип: ForeignKey → Currency

    auto_cashout:
      тип: DecimalField, nullable
      Авто-кэшаут на коэффициенте X

    cashout_at:
      тип: DecimalField, nullable
      На каком коэффициенте забрал

    win_amount:
      тип: DecimalField, default=0

    status:
      тип: CharField
      choices:
        ('active', 'В игре')
        ('cashed_out', 'Забрал')
        ('busted', 'Не успел')
      default: 'active'

    cashed_out_at:
      тип: DateTimeField, nullable

    created_at:
      тип: DateTimeField, auto_now_add

    Meta:
      verbose_name = 'Ставка в Crash'
```

### Модель UserSeed (models.py)

```
class UserSeed(models.Model):

    Назначение:
      Текущие seeds пользователя для Provably Fair.
      Каждый пользователь имеет свою пару seeds.

    Поля:
    ─────
    id:
      тип: UUID, primary key

    user:
      тип: OneToOneField → User
      related_name: 'game_seed'

    server_seed:
      тип: CharField, max 64
      Текущий серверный seed (СКРЫТ от пользователя)

    server_seed_hash:
      тип: CharField, max 64
      SHA-256 хеш server_seed (ВИДИМ пользователю)

    client_seed:
      тип: CharField, max 64
      Клиентский seed (пользователь может менять)
      default: случайная строка

    nonce:
      тип: BigIntegerField, default=0
      Счётчик игр. +1 с каждой игрой.

    previous_server_seed:
      тип: CharField, max 64, nullable
      Предыдущий seed (раскрыт после смены)

    previous_server_seed_hash:
      тип: CharField, max 64, nullable

    created_at:
      тип: DateTimeField, auto_now_add

    updated_at:
      тип: DateTimeField, auto_now

    Meta:
      verbose_name = 'Seed пользователя'
```

### Модель CasinoSettings (models.py)

```
class CasinoSettings(models.Model):

    Назначение:
      Глобальные настройки казино.
      Singleton.

    Поля:
    ─────
    is_enabled:
      тип: BooleanField, default=True

    maintenance_message:
      тип: TextField, nullable

    crash_enabled:
      тип: BooleanField, default=True
    crash_min_bet:
      тип: DecimalField, default=0.10
    crash_max_bet:
      тип: DecimalField, default=10000
    crash_house_edge:
      тип: DecimalField, default=3.00
    crash_max_multiplier:
      тип: DecimalField, default=1000000
    crash_round_wait_time:
      тип: IntegerField, default=10
      Секунды ожидания между раундами

    slots_enabled:
      тип: BooleanField, default=True
    slots_min_bet:
      тип: DecimalField, default=0.10
    slots_max_bet:
      тип: DecimalField, default=5000
    slots_rtp:
      тип: DecimalField, default=96.00

    roulette_enabled:
      тип: BooleanField, default=True
    roulette_min_bet:
      тип: DecimalField, default=0.10
    roulette_max_bet:
      тип: DecimalField, default=10000

    mines_enabled:
      тип: BooleanField, default=True
    mines_min_bet:
      тип: DecimalField, default=0.10
    mines_max_bet:
      тип: DecimalField, default=5000

    dice_enabled:
      тип: BooleanField, default=True
    dice_min_bet:
      тип: DecimalField, default=0.10
    dice_max_bet:
      тип: DecimalField, default=10000

    plinko_enabled:
      тип: BooleanField, default=True
    plinko_min_bet:
      тип: DecimalField, default=0.10
    plinko_max_bet:
      тип: DecimalField, default=5000

    max_concurrent_games:
      тип: IntegerField, default=5
      Максимум одновременных игр (для Mines)

    show_recent_bets:
      тип: BooleanField, default=True

    show_big_wins:
      тип: BooleanField, default=True

    big_win_threshold_usd:
      тип: DecimalField, default=100
      Порог для ленты больших выигрышей

    Meta:
      verbose_name = 'Настройки казино'
```

### Критерий готовности шага 5.1

```
□ GameType (6 игр с настройками)
□ GameSession (универсальная для всех игр)
□ CrashGame (раунды)
□ CrashBet (ставки в раунде)
□ UserSeed (Provably Fair seeds)
□ CasinoSettings (singleton)
□ Все миграции
□ Admin настроен
□ Fixtures для GameType
```

---

## ШАГ 5.2 — PROVABLY FAIR СИСТЕМА

### Файл services/provably_fair.py

```
class ProvablyFairService:

    Назначение:
      Доказуемо честная генерация результатов.
      
      ПРИНЦИП:
        1. Сервер генерирует server_seed ДО игры
        2. Пользователю показывается ХЕШ server_seed
        3. Пользователь может задать свой client_seed
        4. Результат = f(server_seed, client_seed, nonce)
        5. ПОСЛЕ игры server_seed раскрывается
        6. Любой может проверить: hash(seed) == показанный хеш
        7. Результат вычислим и неизменяем

    Методы:
    ───────

    @staticmethod
    def generate_server_seed():
      
      Генерировать новый серверный seed.
      
      seed = secrets.token_hex(32)
      # 64 символа hex = 256 бит энтропии
      return seed


    @staticmethod
    def hash_seed(seed):
      
      SHA-256 хеш seed.
      
      import hashlib
      return hashlib.sha256(seed.encode()).hexdigest()


    @staticmethod
    def generate_client_seed():
      
      Сгенерировать дефолтный client_seed.
      
      return secrets.token_hex(16)
      # 32 символа hex


    @staticmethod
    def get_or_create_user_seed(user):
      
      Получить или создать seeds для пользователя.
      
      seed, created = UserSeed.objects.get_or_create(
        user=user,
        defaults={
          'server_seed': generate_server_seed(),
          'client_seed': generate_client_seed(),
          'nonce': 0
        }
      )
      if created:
        seed.server_seed_hash = hash_seed(seed.server_seed)
        seed.save()
      return seed


    @staticmethod
    def rotate_server_seed(user):
      
      Сменить серверный seed.
      Старый seed РАСКРЫВАЕТСЯ.
      Новый seed генерируется, показывается только хеш.
      
      Вызывается:
        - Когда пользователь нажимает "Сменить seed"
        - Автоматически каждые 1000 игр (опционально)
      
      Логика:
        user_seed = UserSeed.get(user=user)
        
        # Сохранить старый (раскрыть)
        user_seed.previous_server_seed = user_seed.server_seed
        user_seed.previous_server_seed_hash = user_seed.server_seed_hash
        
        # Сгенерировать новый
        new_seed = generate_server_seed()
        user_seed.server_seed = new_seed
        user_seed.server_seed_hash = hash_seed(new_seed)
        
        # Сбросить nonce
        user_seed.nonce = 0
        
        user_seed.save()
        
        return {
          "revealed_seed": user_seed.previous_server_seed,
          "new_seed_hash": user_seed.server_seed_hash
        }


    @staticmethod
    def change_client_seed(user, new_client_seed):
      
      Пользователь меняет свой client_seed.
      
      Логика:
        user_seed = UserSeed.get(user=user)
        user_seed.client_seed = new_client_seed
        user_seed.save()


    @staticmethod
    def generate_game_result(server_seed, client_seed, nonce):
      
      Генерация случайного числа из seeds.
      Это ГЛАВНАЯ ФУНКЦИЯ. Все игры используют её.
      
      Алгоритм:
        1. combined = f"{server_seed}:{client_seed}:{nonce}"
        2. hmac_hash = HMAC-SHA256(server_seed, f"{client_seed}:{nonce}")
        3. Вернуть hmac_hash (hex строка 64 символа)
      
      Из этого hash можно извлекать числа:
        - Первые 8 hex → число 0-4294967295
        - Нормализовать → float 0.0-1.0
        - Использовать для генерации результата

      import hmac, hashlib
      
      message = f"{client_seed}:{nonce}"
      h = hmac.new(
        server_seed.encode(),
        message.encode(),
        hashlib.sha256
      ).hexdigest()
      
      return h


    @staticmethod
    def hash_to_float(hash_hex, offset=0):
      
      Извлечь float 0.0-1.0 из hex hash.
      offset позволяет извлекать несколько чисел из одного hash.
      
      # Берём 8 hex символов начиная с offset
      hex_part = hash_hex[offset*8 : offset*8 + 8]
      int_value = int(hex_part, 16)
      float_value = int_value / 0xFFFFFFFF  # 4294967295
      return float_value


    @staticmethod
    def hash_to_int(hash_hex, max_value, offset=0):
      
      Извлечь целое число 0 - (max_value-1).
      
      float_val = hash_to_float(hash_hex, offset)
      return int(float_val * max_value)


    @staticmethod
    def generate_crash_point(hash_hex, house_edge_percent=3):
      
      Генерация точки краша для Crash.
      
      Алгоритм:
        # Проверка на мгновенный краш (house edge)
        h = int(hash_hex[:13], 16)
        e = 2**52
        
        # house_edge% шанс на мгновенный краш (1.00x)
        if h % (100 / house_edge_percent) == 0:
          return 1.00
        
        # Формула: (100 * e - h) / (e - h) / 100
        crash_point = (100 * e - h) / (e - h) / 100
        
        # Ограничить и округлить
        crash_point = max(1.00, crash_point)
        crash_point = round(crash_point, 2)
        
        return crash_point

      Распределение:
        1.00x: ~3% (house edge)
        1.00-2.00x: ~49%
        2.00-10.00x: ~40%
        10.00-100.00x: ~7%
        100.00x+: ~1%


    @staticmethod
    def generate_dice_result(hash_hex):
      
      Генерация результата для Dice (0.00 - 99.99).
      
      float_val = hash_to_float(hash_hex)
      result = float_val * 10000
      result = math.floor(result) / 100
      return result  # 0.00 - 99.99


    @staticmethod
    def generate_roulette_result(hash_hex):
      
      Генерация числа для Roulette (0-36).
      
      return hash_to_int(hash_hex, 37)


    @staticmethod
    def generate_slots_reels(hash_hex, reels=5, rows=3, symbols=8):
      
      Генерация барабанов для Slots.
      
      result = []
      for reel in range(reels):
        reel_values = []
        for row in range(rows):
          offset = reel * rows + row
          symbol = hash_to_int(hash_hex, symbols, offset)
          reel_values.append(symbol)
        result.append(reel_values)
      return result


    @staticmethod
    def generate_mines_positions(hash_hex, field_size=25, mines_count=5):
      
      Генерация позиций мин для Mines.
      
      positions = set()
      offset = 0
      while len(positions) < mines_count:
        pos = hash_to_int(hash_hex, field_size, offset)
        positions.add(pos)
        offset += 1
        # Если не хватает энтропии → генерировать новый hash
        if offset >= 8:
          hash_hex = hash_seed(hash_hex)
          offset = 0
      return sorted(list(positions))


    @staticmethod
    def generate_plinko_path(hash_hex, rows=16):
      
      Генерация пути шарика для Plinko.
      
      path = []
      for i in range(rows):
        direction = hash_to_int(hash_hex, 2, i)
        path.append(direction)  # 0=лево, 1=право
      
      # Позиция = количество "право"
      landing = sum(path)
      return path, landing


    @staticmethod
    def verify_game(server_seed, server_seed_hash,
                     client_seed, nonce, game_type, game_data):
      
      Проверить честность игры.
      Любой может вызвать эту функцию.
      
      Логика:
        1. Проверить: SHA256(server_seed) == server_seed_hash
           Если нет → "Server seed не совпадает!"
        
        2. Вычислить result_hash = generate_game_result(
             server_seed, client_seed, nonce)
        
        3. Вычислить результат по типу игры:
           crash → generate_crash_point(result_hash)
           dice → generate_dice_result(result_hash)
           roulette → generate_roulette_result(result_hash)
           slots → generate_slots_reels(result_hash)
           mines → generate_mines_positions(result_hash, ...)
           plinko → generate_plinko_path(result_hash, ...)
        
        4. Сравнить с game_data
        
        5. Вернуть:
           {
             "verified": True/False,
             "server_seed_valid": True/False,
             "calculated_result": ...,
             "stored_result": ...,
             "match": True/False
           }
```

### Критерий готовности шага 5.2

```
□ generate_server_seed + hash_seed
□ generate_client_seed
□ get_or_create_user_seed
□ rotate_server_seed (раскрытие + новый)
□ change_client_seed
□ generate_game_result (HMAC-SHA256)
□ hash_to_float, hash_to_int
□ generate_crash_point (с house edge)
□ generate_dice_result (0-99.99)
□ generate_roulette_result (0-36)
□ generate_slots_reels (5x3)
□ generate_mines_positions
□ generate_plinko_path
□ verify_game (проверка честности)
□ Все функции детерминированные (одни входы → один выход)
□ Используется ТОЛЬКО secrets и hmac (не random!)
```

---

## ШАГ 5.3 — ЛОГИКА ИГР

### Абстрактная игра (games/base.py)

```
class BaseGame(ABC):

    Назначение:
      Общий интерфейс для всех игр.

    Абстрактные методы:
    ────────────────────

    @abstractmethod
    def validate_bet(self, user, bet_data):
      Валидация ставки перед игрой.
      Возвращает: (valid, error_message)

    @abstractmethod
    def play(self, user, bet_data):
      Запустить игру.
      Возвращает: GameSession

    @abstractmethod
    def get_result(self, game_session):
      Получить результат игры.
      Возвращает: dict с результатом

    Общие методы:
    ─────────────

    def create_game_session(self, user, game_type_code,
                             bet_amount, currency_code):
      
      Создать GameSession.
      Списать ставку.
      Получить seeds.
      
      Логика (АТОМАРНО):
        1. Проверить баланс
        2. Получить UserSeed
        3. Увеличить nonce
        4. Сгенерировать result_hash
        5. Списать ставку: TransactionService.withdraw(
             type='bet', reference_type='casino_game')
        6. Создать GameSession
        7. Вернуть game_session, result_hash


    def complete_game(self, game_session, win_amount, game_data):
      
      Завершить игру.
      Зачислить выигрыш (если есть).
      
      Логика (АТОМАРНО):
        1. game_session.game_data = game_data
        2. game_session.win_amount = win_amount
        3. game_session.win_multiplier = win_amount / bet_amount
        4. game_session.profit = win_amount - bet_amount
        5. game_session.completed_at = now
        
        if win_amount > 0:
          game_session.status = 'won'
          TransactionService.deposit(
            type='win', reference='casino_game',
            amount=win_amount
          )
        else:
          game_session.status = 'lost'
        
        6. Обновить статистику GameType
        7. Проверить big_win → уведомление
        8. Вернуть game_session
```

### Crash (games/crash.py)

```
class CrashGame:

    Назначение:
      Коэффициент растёт от 1.00x.
      Игрок должен забрать деньги до краша.
      Если не успел → проигрыш.
      МУЛЬТИПЛЕЕРНАЯ: все видят один раунд.

    Методы:
    ───────

    @staticmethod
    def create_round():
      
      Создать новый раунд Crash.
      
      Логика:
        1. server_seed = generate_server_seed()
        2. server_seed_hash = hash_seed(server_seed)
        3. result_hash = generate_game_result(
             server_seed, "crash_global", round_number)
        4. crash_point = generate_crash_point(result_hash)
        5. Создать CrashGame(
             crash_point=crash_point,
             server_seed=server_seed,
             server_seed_hash=server_seed_hash,
             status='waiting'
           )
        6. Вернуть crash_game


    @staticmethod
    def place_bet(user, crash_game_id, bet_amount,
                   currency_code, auto_cashout=None):
      
      Поставить в текущий раунд.
      
      Валидация:
        - crash_game.status == 'waiting'
        - bet_amount в пределах лимитов
        - user ещё не поставил в этот раунд
        - Баланс достаточный
        - auto_cashout >= 1.01 (если задан)
      
      Логика (АТОМАРНО):
        1. Списать ставку
        2. Создать GameSession
        3. Создать CrashBet(
             crash_game=crash_game,
             game_session=session,
             auto_cashout=auto_cashout,
             status='active'
           )
        4. crash_game.players_count += 1
        5. crash_game.total_bet += bet_amount


    @staticmethod
    def start_round(crash_game_id):
      
      Запустить раунд (коэффициент начинает расти).
      Вызывается через Celery после waiting time.
      
      crash_game.status = 'running'
      crash_game.started_at = now


    @staticmethod
    def cashout(user, crash_game_id, current_multiplier):
      
      Забрать деньги.
      
      Валидация:
        - crash_game.status == 'running'
        - current_multiplier <= crash_game.crash_point
        - crash_bet.status == 'active'
      
      Логика (АТОМАРНО):
        1. crash_bet.cashout_at = current_multiplier
        2. win_amount = bet_amount × current_multiplier
        3. Зачислить выигрыш
        4. crash_bet.status = 'cashed_out'
        5. crash_bet.win_amount = win_amount
        6. Обновить GameSession


    @staticmethod
    def end_round(crash_game_id):
      
      Раунд окончен (коэфф достиг crash_point).
      
      Логика:
        1. crash_game.status = 'crashed'
        2. crash_game.crashed_at = now
        
        3. Для всех active bets:
           crash_bet.status = 'busted'
           game_session.status = 'lost'
           game_session.win_amount = 0
        
        4. Авто-кэшаут:
           Для ставок с auto_cashout <= crash_point:
             Уже должны были сработать при start_round
             (проверка в simulate_round)
        
        5. crash_game.total_payout = sum выплат
        
        6. Создать следующий раунд через 5 сек


    @staticmethod
    def simulate_round(crash_game):
      
      Симуляция роста коэффициента.
      Серверная логика (не визуальная).
      
      Для WebSocket (позже):
        Каждые 100ms отправлять текущий множитель.
        Проверять auto_cashout.
      
      Пока (без WebSocket):
        При crash просто рассчитать все ставки.
        Авто-кэшаут: если auto_cashout <= crash_point → выигрыш.
```

### Slots (games/slots.py)

```
class SlotsGame(BaseGame):

    Настройки:
      reels: 5              # Барабанов
      rows: 3               # Строк
      symbols_count: 8       # Символов
      paylines: 20           # Линий выплат

    Символы:
      0: '🍒' (Cherry)      - самый частый
      1: '🍋' (Lemon)
      2: '🍊' (Orange)
      3: '🍇' (Grapes)
      4: '🔔' (Bell)
      5: '⭐' (Star)
      6: '💎' (Diamond)
      7: '7️⃣' (Seven)       - самый редкий

    Таблица выплат (multiplier за 3/4/5 совпадений):
      Символ | x3    | x4    | x5
      ───────┼───────┼───────┼──────
      🍒     | 2     | 5     | 10
      🍋     | 3     | 8     | 15
      🍊     | 4     | 10    | 20
      🍇     | 5     | 15    | 30
      🔔     | 8     | 25    | 50
      ⭐     | 10    | 40    | 100
      💎     | 25    | 100   | 500
      7️⃣     | 50    | 250   | 1000

    Веса символов (частота появления):
      🍒: 25%   🍋: 20%   🍊: 18%   🍇: 15%
      🔔: 10%   ⭐: 7%    💎: 3.5%  7️⃣: 1.5%
      
      Веса подобраны чтобы RTP ≈ 96%

    Методы:
    ───────

    def play(self, user, bet_amount, currency_code):
      
      Логика:
        1. create_game_session()
        2. Сгенерировать барабаны:
           reels = generate_slots_reels(result_hash)
           
           Применить веса:
           Для каждой позиции:
             raw = hash_to_float(hash, offset)
             symbol = weighted_random(raw, weights)
           
        3. Проверить выигрышные линии:
           wins = check_paylines(reels)
           total_multiplier = sum(wins.multipliers)
           win_amount = bet_amount × total_multiplier
        
        4. complete_game(session, win_amount, {
             "reels": reels,
             "paylines": wins,
             "total_multiplier": total_multiplier
           })

    def check_paylines(self, reels):
      
      Проверить 20 линий на выигрыш.
      
      Линии (на сетке 5x3):
        Линия 1: средняя горизонталь [1,1,1,1,1]
        Линия 2: верхняя [0,0,0,0,0]
        Линия 3: нижняя [2,2,2,2,2]
        Линия 4: V-форма [0,1,2,1,0]
        Линия 5: ^-форма [2,1,0,1,2]
        ... и другие стандартные линии

      Для каждой линии:
        Считать совпадения слева направо.
        Первый символ определяет какой ищем.
        3+ совпадений = выигрыш.
```

### Roulette (games/roulette.py)

```
class RouletteGame(BaseGame):

    Настройки:
      Числа: 0-36
      Красные: {1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36}
      Чёрные: {2,4,6,8,10,11,13,15,17,20,22,24,26,28,29,31,33,35}
      Зелёные: {0}

    Типы ставок и выплаты:
      Тип              | Пример        | Выплата
      ─────────────────┼───────────────┼────────
      Число            | 17            | 36x
      Красное/Чёрное   | red           | 2x
      Чёт/Нечёт        | even          | 2x
      1-18 / 19-36     | low           | 2x
      Дюжина (1-12)    | dozen_1       | 3x
      Колонка           | column_1      | 3x
      Сплит (2 числа)  | split_1_2     | 18x
      Стрит (3 числа)  | street_1_3    | 12x
      Угол (4 числа)   | corner_1_2_4_5| 9x
      Линия (6 чисел)  | line_1_6      | 6x

    Методы:
    ───────

    def play(self, user, bets, currency_code):
      
      bets = [
        {"type": "red", "amount": 10},
        {"type": "number", "number": 17, "amount": 5},
        {"type": "dozen_1", "amount": 10}
      ]
      
      Логика:
        1. Валидация всех ставок
        2. Общая сумма = sum всех ставок
        3. create_game_session(total_bet)
        4. winning_number = generate_roulette_result(hash)
        5. winning_color = get_color(winning_number)
        6. Для каждой ставки:
           - Определить выиграла или нет
           - Рассчитать выплату
        7. total_win = sum выплат
        8. complete_game(session, total_win, game_data)

    def check_bet_result(self, bet, winning_number):
      
      Проверить одну ставку.
      
      if bet.type == 'number':
        return winning_number == bet.number, 36
      elif bet.type == 'red':
        return winning_number in RED_NUMBERS, 2
      elif bet.type == 'black':
        return winning_number in BLACK_NUMBERS, 2
      elif bet.type == 'even':
        return winning_number > 0 and winning_number % 2 == 0, 2
      elif bet.type == 'odd':
        return winning_number % 2 == 1, 2
      elif bet.type == 'low':
        return 1 <= winning_number <= 18, 2
      elif bet.type == 'high':
        return 19 <= winning_number <= 36, 2
      elif bet.type == 'dozen_1':
        return 1 <= winning_number <= 12, 3
      elif bet.type == 'dozen_2':
        return 13 <= winning_number <= 24, 3
      elif bet.type == 'dozen_3':
        return 25 <= winning_number <= 36, 3
      ... и т.д.
```

### Mines (games/mines.py)

```
class MinesGame(BaseGame):

    Настройки:
      field_size: 25 (5×5)
      mines: 1-24 (выбирает пользователь)

    Множители (зависят от количества мин):
      Формула:
        probability = C(safe, opened) / C(total, opened)
        multiplier = (1 / probability) × (1 - house_edge)
      
      Пример (5 мин, 25 клеток):
        1 открыта: 1.04x
        2 открыты: 1.09x
        3 открыты: 1.14x
        5 открыт:  1.35x
        10 открыто: 2.43x
        15 открыто: 6.46x
        20 открыто: 79.31x

    Методы:
    ───────

    def start_game(self, user, bet_amount, mines_count,
                     currency_code):
      
      Начать игру (открытие клеток по одной).
      
      Логика:
        1. Валидация: mines_count 1-24
        2. create_game_session()
        3. mines_positions = generate_mines_positions(
             hash, field_size=25, mines_count=mines_count)
        4. game_session.game_data = {
             "field_size": 25,
             "mines_count": mines_count,
             "mines_positions": mines_positions,  # СКРЫТО
             "revealed": [],
             "current_multiplier": 1.00,
             "is_mine_hit": false
           }
        5. game_session.status = 'active'
        6. Вернуть game_session (БЕЗ mines_positions!)


    def reveal_cell(self, game_session_id, cell_index):
      
      Открыть клетку.
      
      Логика (АТОМАРНО):
        1. session = GameSession.select_for_update()
        2. Проверить: session.status == 'active'
        3. Проверить: cell_index not in revealed
        4. Проверить: 0 <= cell_index < 25
        
        5. Если cell_index in mines_positions:
           → МИНА! Проигрыш.
           session.game_data['is_mine_hit'] = True
           complete_game(session, win_amount=0, ...)
           Вернуть: {"mine": True, "mines_positions": [...]}
        
        6. Если не мина:
           session.game_data['revealed'].append(cell_index)
           Пересчитать multiplier
           session.game_data['current_multiplier'] = new_mult
           Вернуть: {
             "mine": False,
             "cell": cell_index,
             "current_multiplier": new_mult,
             "next_multiplier": next_mult
           }


    def cashout_mines(self, game_session_id, user):
      
      Забрать деньги (не открывая все клетки).
      
      Логика:
        1. session = GameSession.select_for_update()
        2. Проверить: status == 'active'
        3. Проверить: len(revealed) >= 1
        4. win_amount = bet_amount × current_multiplier
        5. complete_game(session, win_amount, ...)
        6. Раскрыть mines_positions пользователю
```

### Dice (games/dice.py)

```
class DiceGame(BaseGame):

    Настройки:
      range: 0.00 - 99.99
      house_edge: 2%

    Логика:
      Пользователь выбирает:
        target: число (0-99.99)
        condition: "over" или "under"
      
      win_chance:
        over: 99.99 - target
        under: target
      
      multiplier:
        (100 - house_edge) / win_chance
      
      Пример:
        target=50.00, over → шанс 49.99% → множитель 1.96x
        target=75.00, over → шанс 24.99% → множитель 3.92x
        target=95.00, over → шанс  4.99% → множитель 19.64x
        target=25.00, under → шанс 25.00% → множитель 3.92x

    Методы:
    ───────

    def play(self, user, bet_amount, target, condition,
              currency_code):
      
      Логика:
        1. Валидация:
           - target: 0.01 - 99.98
           - condition: 'over' или 'under'
           - win_chance >= 1% и <= 98%
        
        2. Рассчитать:
           win_chance = (99.99 - target) if over else target
           multiplier = 98.0 / win_chance  # 2% house edge
        
        3. create_game_session()
        4. result = generate_dice_result(hash)  # 0.00-99.99
        
        5. Определить выигрыш:
           if condition == 'over':
             won = result > target
           else:
             won = result < target
        
        6. win_amount = bet_amount × multiplier if won else 0
        7. complete_game(session, win_amount, {
             "target": target,
             "condition": condition,
             "result": result,
             "multiplier": multiplier,
             "win_chance": win_chance
           })
```

### Plinko (games/plinko.py)

```
class PlinkoGame(BaseGame):

    Настройки:
      rows: 8, 12, 16 (выбирает пользователь)
      risk: low, medium, high

    Множители (зависят от rows и risk):
      
      16 рядов, Medium risk:
      Позиция:  0    1    2    3    4    5    6    7    8
      Множ.:   110  41   10   5    3    1.5  1    0.5  0.3
      (зеркально: 8→0 = 0→8)
      
      Позиция 0 и 16 — крайние (редко) = большой множитель
      Позиция 8 — центр (часто) = маленький множитель

    Методы:
    ───────

    def play(self, user, bet_amount, rows, risk,
              currency_code):
      
      Логика:
        1. Валидация: rows in (8,12,16), risk in (low,medium,high)
        2. create_game_session()
        3. path, landing = generate_plinko_path(hash, rows)
        4. multiplier = get_multiplier(rows, risk, landing)
        5. win_amount = bet_amount × multiplier
        6. complete_game(session, win_amount, {
             "rows": rows,
             "risk": risk,
             "path": path,
             "landing_position": landing,
             "multiplier": multiplier
           })
```

### Критерий готовности шага 5.3

```
□ BaseGame абстрактный класс
□ Crash: create_round, place_bet, cashout, end_round
□ Slots: play с 20 paylines и weighted symbols
□ Roulette: play со всеми типами ставок
□ Mines: start_game, reveal_cell, cashout
□ Dice: play с over/under
□ Plinko: play с 3 уровнями риска
□ Все игры используют ProvablyFair
□ Все деньги через TransactionService
□ House edge правильный для каждой игры
□ Множители рассчитываются корректно
```

---

## ШАГ 5.4 — СТРАНИЦЫ КАЗИНО

### Главная казино

```
URL: /casino/

  ┌──────────────────────────────────────────────────────────┐
  │  🎰 Казино DOD                                          │
  │                                                          │
  │  🔥 Популярные                                          │
  │  ┌──────────┐ ┌──────────┐ ┌──────────┐                │
  │  │ 📈       │ │ 🎰       │ │ 🎡       │                │
  │  │ CRASH    │ │ SLOTS    │ │ ROULETTE │                │
  │  │ RTP 97%  │ │ RTP 96%  │ │ RTP 97.3%│                │
  │  │ [Играть] │ │ [Играть] │ │ [Играть] │                │
  │  └──────────┘ └──────────┘ └──────────┘                │
  │  ┌──────────┐ ┌──────────┐ ┌──────────┐                │
  │  │ 💣       │ │ 🎲       │ │ 📌       │                │
  │  │ MINES    │ │ DICE     │ │ PLINKO   │                │
  │  │ RTP 98%  │ │ RTP 98%  │ │ RTP 97%  │                │
  │  │ [Играть] │ │ [Играть] │ │ [Играть] │                │
  │  └──────────┘ └──────────┘ └──────────┘                │
  │                                                          │
  │  ── 🏆 Большие выигрыши ──────────────────────────────  │
  │  (бегущая строка)                                       │
  │  🎉 Us*** выиграл $2,340 в Crash (23.4x)               │
  │  🎉 An*** выиграл $1,200 в Slots (120x)                │
  │  🎉 Ma*** выиграл $890 в Mines (8.9x)                  │
  │                                                          │
  │  ── 📋 Последние ставки ──────────────────────────────  │
  │  │ Игра     │ Игрок  │ Ставка  │ Множ.  │ Выигрыш  │  │
  │  │ 📈 Crash │ Us***  │ $50     │ 2.47x  │ $123.50  │  │
  │  │ 🎲 Dice  │ An***  │ $100    │ 1.96x  │ $196.00  │  │
  │  │ 💣 Mines │ Ko***  │ $25     │ 0x     │ $0       │  │
  │  │ 🎰 Slots │ Ma***  │ $10     │ 15x    │ $150.00  │  │
  │  │ 🎡 Roul. │ Di***  │ $200    │ 2x     │ $400.00  │  │
  │                                                          │
  │  HTMX: обновляется каждые 5 сек                        │
  │                                                          │
  └──────────────────────────────────────────────────────────┘
```

### Страница Crash

```
URL: /casino/crash/

  ┌──────────────────────────────────────────────────────────┐
  │                                                          │
  │  📈 CRASH                                               │
  │                                                          │
  │  ┌────────────────────────────────────────────────────┐ │
  │  │                                                    │ │
  │  │                   2.47x                            │ │
  │  │                                                    │ │
  │  │          📈 (график роста коэффициента)            │ │
  │  │         /                                          │ │
  │  │        /                                           │ │
  │  │       /                                            │ │
  │  │      /                                             │ │
  │  │     /                                              │ │
  │  │ ___/                                               │ │
  │  │ 1.00x                                              │ │
  │  │                                                    │ │
  │  │  Хеш раунда: a7b3c2d4e5f6...                     │ │
  │  │                                                    │ │
  │  └────────────────────────────────────────────────────┘ │
  │                                                          │
  │  ┌────────────────────┐  ┌────────────────────────┐    │
  │  │ Ставка:            │  │ Авто-кэшаут:          │    │
  │  │ ┌────────────────┐ │  │ ┌────────────────────┐ │    │
  │  │ │ $        50.00 │ │  │ │ 2.00x              │ │    │
  │  │ └────────────────┘ │  │ └────────────────────┘ │    │
  │  │ [$1] [$5] [$10]   │  │ [1.5x] [2x] [5x] [10x]│    │
  │  │ [$50] [$100]      │  │                          │    │
  │  │                    │  │                          │    │
  │  │ [   Поставить   ]  │  │                          │    │
  │  │  или                │  │                          │    │
  │  │ [   Забрать ↑   ]  │  │                          │    │
  │  └────────────────────┘  └────────────────────────┘    │
  │                                                          │
  │  ── Игроки в этом раунде ──────────────────────────────│
  │  │ Игрок  │ Ставка │ Кэшаут │ Профит │                │
  │  │ Us***  │ $100   │ 2.10x  │ +$110  │ ✅             │
  │  │ An***  │ $50    │ —      │ —      │ 🎮 в игре     │
  │  │ Ko***  │ $200   │ 1.50x  │ +$100  │ ✅             │
  │                                                          │
  │  ── Предыдущие раунды ─────────────────────────────────│
  │  [2.47x] [1.00x] [5.23x] [1.87x] [12.50x] [1.00x]   │
  │  (зелёные если > 2x, красные если = 1.00x)            │
  │                                                          │
  └──────────────────────────────────────────────────────────┘

  Без WebSocket (пока):
    Crash работает в УПРОЩЁННОМ режиме.
    Раунд происходит мгновенно (не анимированно).
    Пользователь ставит → видит результат.
    Авто-кэшаут определяет выиграл ли.
    
    Кнопки:
      "Поставить" → отправляет ставку с auto_cashout
      Результат показывается сразу:
        Если auto_cashout <= crash_point → выигрыш
        Если auto_cashout > crash_point → проигрыш
        Если auto_cashout не задан → проигрыш (не успел)

  С WebSocket (Этап 10):
    Полная анимация роста в реальном времени.
    Кнопка "Забрать" в реальном времени.
    Все игроки видят один раунд.

  HTMX:
    Форма ставки: hx-post="/casino/crash/play/"
    Результат: заменяет блок с результатом
    История раундов: обновляется после каждого раунда
```

### Страница Mines

```
URL: /casino/mines/

  ┌──────────────────────────────────────────────────────────┐
  │  💣 MINES                                               │
  │                                                          │
  │  ┌────────────────┐  ┌────────────────────────────────┐ │
  │  │ Мин: [5 ▼]     │  │                                │ │
  │  │ Ставка: $10    │  │  ┌──┐ ┌──┐ ┌──┐ ┌──┐ ┌──┐   │ │
  │  │                │  │  │💎│ │? │ │? │ │💎│ │? │   │ │
  │  │ [Начать игру]  │  │  └──┘ └──┘ └──┘ └──┘ └──┘   │ │
  │  │                │  │  ┌──┐ ┌──┐ ┌──┐ ┌──┐ ┌──┐   │ │
  │  │ ── или ──      │  │  │? │ │? │ │💎│ │? │ │? │   │ │
  │  │                │  │  └──┘ └──┘ └──┘ └──┘ └──┘   │ │
  │  │ Текущий x:     │  │  ┌──┐ ┌──┐ ┌──┐ ┌──┐ ┌──┐   │ │
  │  │ 1.58x          │  │  │? │ │? │ │? │ │? │ │? │   │ │
  │  │                │  │  └──┘ └──┘ └──┘ └──┘ └──┘   │ │
  │  │ Следующий:     │  │  ┌──┐ ┌──┐ ┌──┐ ┌──┐ ┌──┐   │ │
  │  │ 1.76x          │  │  │? │ │? │ │? │ │? │ │? │   │ │
  │  │                │  │  └──┘ └──┘ └──┘ └──┘ └──┘   │ │
  │  │ Выигрыш:       │  │  ┌──┐ ┌──┐ ┌──┐ ┌──┐ ┌──┐   │ │
  │  │ $15.80         │  │  │? │ │? │ │? │ │? │ │? │   │ │
  │  │                │  │  └──┘ └──┘ └──┘ └──┘ └──┘   │ │
  │  │ [💰 Забрать    │  │                                │ │
  │  │  $15.80]       │  │                                │ │
  │  └────────────────┘  └────────────────────────────────┘ │
  │                                                          │
  └──────────────────────────────────────────────────────────┘

  HTMX:
    Клик на клетку:
      hx-post="/casino/mines/reveal/"
      hx-vals='{"cell": 5}'
      hx-target="#mines-field"
    
    Если 💎 → клетка открывается, множитель обновляется
    Если 💣 → все мины показываются, game over
    
    Забрать:
      hx-post="/casino/mines/cashout/"
```

### Страница Dice

```
URL: /casino/dice/

  ┌──────────────────────────────────────────────────────────┐
  │  🎲 DICE                                                │
  │                                                          │
  │  ┌────────────────────────────────────────────────────┐ │
  │  │                                                    │ │
  │  │  Результат: 67.34                                 │ │
  │  │                                                    │ │
  │  │  0 ─────────────────|────●───────────────── 99.99 │ │
  │  │                    50.00  67.34                    │ │
  │  │                     ▲                              │ │
  │  │                   цель                             │ │
  │  │                                                    │ │
  │  │  ████████████████░░░░░░████████████████████       │ │
  │  │  ◄── проигрыш ──►  ◄───── выигрыш ─────►        │ │
  │  │                                                    │ │
  │  └────────────────────────────────────────────────────┘ │
  │                                                          │
  │  Ставка: [$      50.00]                                 │
  │                                                          │
  │  Цель:   [═══════●═══════════] 50.00                   │
  │           0                  99.99                      │
  │                                                          │
  │  Режим:  [● Over]  [○ Under]                           │
  │                                                          │
  │  Шанс выигрыша: 49.99%                                 │
  │  Множитель: 1.96x                                      │
  │  Выигрыш: $98.00                                       │
  │                                                          │
  │  [        Бросить кости        ]                        │
  │                                                          │
  └──────────────────────────────────────────────────────────┘

  HTMX:
    Слайдер target:
      hx-get="/casino/dice/calculate/"
      hx-trigger="input changed delay:100ms"
      hx-target="#dice-stats"
      → пересчитывает шанс, множитель, выигрыш

    Бросить:
      hx-post="/casino/dice/play/"
      → показывает результат с анимацией
```

### Страница Roulette

```
URL: /casino/roulette/

  ┌──────────────────────────────────────────────────────────┐
  │  🎡 ROULETTE                                            │
  │                                                          │
  │  ┌────────────────────────────────────────────────────┐ │
  │  │         Последнее число: [17] (чёрное)            │ │
  │  │                                                    │ │
  │  │  История: [0][32][15][19][4][21][2][25][17]       │ │
  │  │           🟢 🔴  ⚫  🔴 ⚫ 🔴  ⚫ 🔴  ⚫        │ │
  │  └────────────────────────────────────────────────────┘ │
  │                                                          │
  │  ┌────────────────────────────────────────────────────┐ │
  │  │ Стол рулетки (сетка чисел 0-36)                   │ │
  │  │                                                    │ │
  │  │  [0]                                               │ │
  │  │  [1] [2] [3]      ← кликабельные                 │ │
  │  │  [4] [5] [6]                                      │ │
  │  │  [7] [8] [9]                                      │ │
  │  │  ...                                               │ │
  │  │  [34][35][36]                                      │ │
  │  │                                                    │ │
  │  │  [1-12] [13-24] [25-36]  ← дюжины                │ │
  │  │  [1-18] [EVEN] [RED] [BLACK] [ODD] [19-36]       │ │
  │  └────────────────────────────────────────────────────┘ │
  │                                                          │
  │  Ваши ставки:                                           │
  │  🔴 Красное: $10                                       │
  │  17: $5                                                 │
  │  Итого: $15                                             │
  │                                                          │
  │  [        Крутить        ]                              │
  │                                                          │
  └──────────────────────────────────────────────────────────┘

  Множественные ставки:
    Пользователь кликает на числа/зоны на столе.
    Каждый клик добавляет фишку ($1, $5, $10, $25, $100).
    Выбор фишки отдельной панелью.
    Все ставки отправляются одним запросом.
```

### Страница проверки честности (Fairness)

```
URL: /casino/fairness/

  ┌──────────────────────────────────────────────────────────┐
  │  🔒 Provably Fair — Проверка честности                  │
  │                                                          │
  │  ── Ваши текущие seeds ──────────────────────────────── │
  │                                                          │
  │  Server Seed Hash (текущий):                            │
  │  ┌────────────────────────────────────────────────────┐ │
  │  │ a7b3c2d4e5f67890abcdef1234567890abcdef1234567890.. │ │
  │  └────────────────────────────────────────────────────┘ │
  │  ⚠️ Server Seed будет раскрыт после смены              │
  │                                                          │
  │  Client Seed (ваш):                                     │
  │  ┌────────────────────────────────────┐                 │
  │  │ my_custom_seed_123                 │  [Изменить]    │
  │  └────────────────────────────────────┘                 │
  │                                                          │
  │  Nonce (номер игры): 47                                 │
  │                                                          │
  │  [Сменить Server Seed]                                  │
  │  ⚠️ Текущий seed будет раскрыт,                        │
  │     новый seed сгенерируется                            │
  │                                                          │
  │  ── Проверить игру ──────────────────────────────────── │
  │                                                          │
  │  Server Seed:                                           │
  │  ┌────────────────────────────────────────────────────┐ │
  │  │                                                    │ │
  │  └────────────────────────────────────────────────────┘ │
  │  Client Seed:                                           │
  │  ┌────────────────────────────────────────────────────┐ │
  │  │                                                    │ │
  │  └────────────────────────────────────────────────────┘ │
  │  Nonce:                                                 │
  │  ┌──────────┐                                          │
  │  │          │                                          │
  │  └──────────┘                                          │
  │  Игра: [Crash ▼]                                       │
  │                                                          │
  │  [Проверить]                                            │
  │                                                          │
  │  Результат:                                             │
  │  ┌────────────────────────────────────────────────────┐ │
  │  │ ✅ Проверка пройдена!                             │ │
  │  │                                                    │ │
  │  │ Hash совпадает: ✅                                │ │
  │  │ Вычисленный результат: 2.47x                      │ │
  │  │ Сохранённый результат: 2.47x                      │ │
  │  │ Совпадение: ✅                                    │ │
  │  └────────────────────────────────────────────────────┘ │
  │                                                          │
  │  ── Моя история (с раскрытыми seeds) ──────────────── │
  │                                                          │
  │  │ Игра   │ Nonce │ Результат │ Server Seed │ [✓]    │ │
  │  │ Crash  │ 46    │ 5.23x     │ a7b3c2...   │ [Пров.]│ │
  │  │ Dice   │ 45    │ 67.34     │ a7b3c2...   │ [Пров.]│ │
  │  │ Mines  │ 44    │ 1.58x     │ a7b3c2...   │ [Пров.]│ │
  │                                                          │
  └──────────────────────────────────────────────────────────┘
```

### История игр казино

```
URL: /casino/history/

  Фильтры: Игра [Все ▼] Период [7 дней ▼] Результат [Все ▼]

  │ Дата       │ Игра     │ Ставка  │ Множ.  │ Выигрыш │ Проверка │
  │ 15.03 14:30│ 📈 Crash │ $50.00  │ 2.47x  │ $123.50 │ [✓ Fair] │
  │ 15.03 14:25│ 🎲 Dice  │ $100.00 │ 0x     │ $0      │ [✓ Fair] │
  │ 15.03 14:20│ 💣 Mines │ $25.00  │ 3.20x  │ $80.00  │ [✓ Fair] │
  │ 15.03 14:15│ 🎰 Slots │ $10.00  │ 15x    │ $150.00 │ [✓ Fair] │
  │ 15.03 14:10│ 🎡 Roul. │ $200.00 │ 2x     │ $400.00 │ [✓ Fair] │

  При клике [✓ Fair]:
    Если seed ещё не раскрыт:
      "Seed будет раскрыт после смены. Сменить сейчас?"
    Если раскрыт:
      Показать форму проверки с предзаполненными полями

  Пагинация + экспорт CSV
```

### Критерий готовности шага 5.4

```
□ /casino/ — главная с 6 играми, лента выигрышей
□ /casino/crash/ — интерфейс Crash
□ /casino/slots/ — интерфейс Slots
□ /casino/roulette/ — интерфейс Roulette с полем
□ /casino/mines/ — интерфейс Mines (5x5 поле)
□ /casino/dice/ — интерфейс Dice со слайдером
□ /casino/plinko/ — интерфейс Plinko
□ /casino/fairness/ — проверка честности
□ /casino/history/ — история игр
□ Лента "Последние ставки" (HTMX обновление)
□ Лента "Большие выигрыши"
□ Все игры играбельны через HTMX
□ Тёмная тема, мобильная адаптация
```

---

## ШАГ 5.5 — CELERY + ЛЕНТА + СТАТИСТИКА

### Файл tasks.py

```
update_live_feed():
    Каждые 5 секунд.
    Кэшировать в Redis последние 50 ставок.
    Кэшировать последние 20 больших выигрышей.
    Для HTMX polling.

crash_game_loop():
    Основной цикл Crash.
    Без WebSocket (пока):
      Каждые crash_round_wait_time секунд:
        1. Закрыть текущий раунд
        2. Рассчитать все ставки
        3. Создать новый раунд
    
    С WebSocket (Этап 10):
      Непрерывный цикл:
        waiting → running → crashed → waiting

update_game_statistics():
    Каждые 30 минут.
    Обновить GameType:
      total_bets, total_wagered_usd, total_won_usd

daily_casino_report():
    Каждый день в 09:00.
    Отчёт:
      - GGR по каждой игре
      - Общий GGR
      - Самый большой выигрыш
      - Количество уникальных игроков
      - RTP фактический vs настроенный

cleanup_inactive_mines_games():
    Каждые 30 минут.
    Mines игры в статусе 'active' старше 1 часа:
      → Автоматический кэшаут (если есть открытые)
      → Или проигрыш (если ничего не открыл)

verify_rtp_integrity():
    Каждый день.
    Для каждой игры за последние 24 часа:
      actual_rtp = total_won / total_wagered × 100
      expected_rtp = GameType.rtp
      if abs(actual_rtp - expected_rtp) > 5:
        ALERT: "RTP аномалия!"
```

### Файл admin.py (дополнения)

```
GameTypeAdmin:
  list_display: code, name, house_edge, rtp, min_bet, max_bet,
                is_active, total_bets, total_wagered_usd
  list_editable: house_edge, min_bet, max_bet, is_active

GameSessionAdmin:
  list_display: game_id, user, game_type, currency, bet_amount,
                win_multiplier, win_amount, status, started_at
  list_filter: game_type, status, currency, started_at
  search_fields: game_id, user__email
  readonly_fields: game_data, server_seed, server_seed_hash,
                   client_seed, nonce
  date_hierarchy: started_at

CrashGameAdmin:
  list_display: round_id, crash_point, status, players_count,
                total_bet, total_payout, created_at
  list_filter: status
  readonly_fields: server_seed, crash_point

  Действия:
    - Принудительно завершить раунд

UserSeedAdmin:
  list_display: user, server_seed_hash, nonce, updated_at
  search_fields: user__email
  readonly_fields: server_seed (маскировано)

CasinoSettingsAdmin:
  Singleton. Все поля.
```

### Критерий готовности шага 5.5

```
□ Crash game loop (автоматические раунды)
□ Live feed (последние ставки, обновление 5 сек)
□ Big wins лента
□ Статистика по играм
□ Ежедневный отчёт казино
□ Очистка зависших Mines игр
□ Проверка RTP integrity
□ Админка: все модели настроены
□ Redis кэширование ленты
```

---

## 📊 ОБЩИЙ ЧЕКЛИСТ ЭТАПА 5

```
МОДЕЛИ:
  □ GameType (6 игр)
  □ GameSession (универсальная)
  □ CrashGame (раунды)
  □ CrashBet (ставки в раунде)
  □ UserSeed (Provably Fair)
  □ CasinoSettings (singleton)

PROVABLY FAIR:
  □ Генерация seeds
  □ HMAC-SHA256 результат
  □ Crash point с house edge
  □ Dice result
  □ Roulette result
  □ Slots reels
  □ Mines positions
  □ Plinko path
  □ Верификация (проверка)
  □ Ротация seeds
  □ Смена client seed

ИГРЫ:
  □ Crash (ставка, авто-кэшаут, раунды)
  □ Slots (5x3, 20 paylines, weighted symbols)
  □ Roulette (все типы ставок, множественные)
  □ Mines (5x5, reveal, cashout)
  □ Dice (over/under, слайдер)
  □ Plinko (3 риска, 3 размера)

СТРАНИЦЫ:
  □ /casino/ — главная, лента
  □ /casino/crash/
  □ /casino/slots/
  □ /casino/roulette/
  □ /casino/mines/
  □ /casino/dice/
  □ /casino/plinko/
  □ /casino/fairness/
  □ /casino/history/

ФИНАНСЫ:
  □ Все через TransactionService
  □ Списание при ставке
  □ Зачисление при выигрыше
  □ House edge корректный
  □ RTP мониторинг

CELERY:
  □ Crash loop
  □ Live feed обновление
  □ Статистика
  □ RTP integrity check
  □ Cleanup зависших игр
  □ Ежедневный отчёт

АДМИНКА:
  □ Все модели
  □ Настройки house edge / RTP
  □ Настройки лимитов
  □ Статистика
```

---

```
╔══════════════════════════════════════════════════════╗
║                                                      ║
║   ЭТАП 5 ЗАВЕРШЁН                                   ║
║                                                      ║
║   Следующий: ЭТАП 6                                 ║
║   Prediction Market                                  ║
║   (Маркеты предсказаний как Polymarket)             ║
║                                                      ║
║   Продолжить?                                       ║
║                                                      ║
╚══════════════════════════════════════════════════════╝
```