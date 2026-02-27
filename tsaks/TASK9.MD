

# 📋 ТЗ ПРОЕКТА DOD — ЭТАП 9

# ЧАТ ПОДДЕРЖКИ + РАСШИРЕННАЯ СИСТЕМА УВЕДОМЛЕНИЙ

```
╔══════════════════════════════════════════════════════╗
║                                                      ║
║   ПРОЕКТ:    DOD                                    ║
║   ЭТАП:      9 из 12                                ║
║   НАЗВАНИЕ:  Чат поддержки + Уведомления            ║
║   ЗАВИСИТ:   Этапы 1-8 (полностью завершены)        ║
║   ЦЕЛЬ:      Пользователь может обратиться в        ║
║              поддержку через чат или тикет,          ║
║              оператор отвечает в реальном времени,   ║
║              работает FAQ, автоответы, SLA,          ║
║              Telegram бот уведомлений,               ║
║              полная история обращений                ║
║                                                      ║
╚══════════════════════════════════════════════════════╝
```

---

## 📌 КОНТЕКСТ ДЛЯ ИИ-АГЕНТА

```
Этапы 1-8 выполнены. У тебя есть:
  - Полная авторизация + профиль + KYC
  - Кошелёк + платежи
  - Ставки на спорт + Казино + Predictions
  - Партнёрская программа
  - Базовая система уведомлений (Notification model,
    колокольчик, email, Telegram — из этапа 2)

В этом этапе ты строишь:
  1. Живой чат поддержки (WebSocket через Django Channels)
  2. Тикет-систему (для сложных вопросов)
  3. FAQ / База знаний
  4. Telegram бот (полноценный, для уведомлений)
  5. Расширение системы уведомлений
  6. Панель оператора поддержки

Django Channels уже подготовлен (requirements, docker).
Redis используется как channel layer.

Этот этап включает 6 шагов.
Каждый шаг — отдельная задача.
Выполняй строго по порядку.
```

---

## ШАГ 9.1 — ПРИЛОЖЕНИЕ И МОДЕЛИ

### Задача

```
Создай приложение support с моделями:
тикеты, сообщения, чат-сессии, FAQ,
шаблоны быстрых ответов, оценки.
Подготовь Django Channels.
```

### Структура приложения

```
apps/support/
├── __init__.py
├── models.py
├── managers.py
├── admin.py
├── views.py
├── urls.py
├── forms.py
├── signals.py
├── tasks.py
├── validators.py
├── consumers.py           # WebSocket consumers (Channels)
├── routing.py             # WebSocket URL routing
├── services/
│   ├── __init__.py
│   ├── ticket_service.py  # Логика тикетов
│   ├── chat_service.py    # Логика живого чата
│   ├── faq_service.py     # FAQ и автоответы
│   ├── assignment_service.py  # Распределение операторам
│   └── sla_service.py     # SLA мониторинг
├── templatetags/
│   ├── __init__.py
│   └── support_tags.py
├── tests/
│   ├── __init__.py
│   ├── test_models.py
│   ├── test_tickets.py
│   ├── test_chat.py
│   └── test_views.py
├── templates/
│   └── support/
│       └── (шаблоны — шаг 9.5)
└── migrations/
    └── __init__.py
```

### Настройка Django Channels

```
# config/settings/base.py (добавить/обновить)

INSTALLED_APPS += [
    'channels',
    'apps.support',
]

ASGI_APPLICATION = 'config.asgi.application'

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [(env('REDIS_HOST', default='redis'), 6379)],
            'capacity': 1500,
            'expiry': 60,
        },
    },
}


# config/asgi.py

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

django_asgi_app = get_asgi_application()

from apps.support.routing import websocket_urlpatterns

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(websocket_urlpatterns)
        )
    ),
})


# docker-compose.yml — обновить app service
services:
  app:
    command: daphne -b 0.0.0.0 -p 8000 config.asgi:application
    # ИЛИ для разработки:
    # command: python manage.py runserver 0.0.0.0:8000
    # (runserver поддерживает channels в dev)
```

### Модель Ticket

```
class Ticket(models.Model):

    Назначение:
      Тикет обращения в поддержку.
      Основная единица работы поддержки.
      Может быть создан через чат или форму.

    Поля:
    ─────
    id:
      тип: UUID, primary key

    ticket_number:
      тип: CharField, max 20, уникальный
      Человекочитаемый номер
      Формат: DOD-YYYYMMDD-NNNN
      Пример: DOD-20250320-0042
      Генерируется автоматически

    user:
      тип: ForeignKey → User
      on_delete: CASCADE
      related_name: 'tickets'
      Кто обратился

    # Категория
    category:
      тип: CharField
      choices:
        ('finance', 'Финансы и платежи')
        ('deposit', 'Проблема с депозитом')
        ('withdrawal', 'Проблема с выводом')
        ('account', 'Аккаунт и профиль')
        ('verification', 'Верификация (KYC)')
        ('sport_bet', 'Ставки на спорт')
        ('casino', 'Казино')
        ('prediction', 'Маркеты предсказаний')
        ('referral', 'Партнёрская программа')
        ('technical', 'Технические проблемы')
        ('security', 'Безопасность')
        ('complaint', 'Жалоба')
        ('suggestion', 'Предложение')
        ('other', 'Другое')

    # Описание
    subject:
      тип: CharField, max 200
      Тема обращения

    description:
      тип: TextField, max 5000
      Первое сообщение / описание проблемы
      Заполняется при создании тикета

    # Приоритет
    priority:
      тип: CharField
      choices:
        ('low', 'Низкий')
        ('medium', 'Средний')
        ('high', 'Высокий')
        ('critical', 'Критический')
      default: 'medium'

    # Автоопределение приоритета:
    #   'finance', 'withdrawal' → high
    #   'security' → critical
    #   'suggestion' → low
    #   остальные → medium

    # Статус
    status:
      тип: CharField
      choices:
        ('new', 'Новый')
        ('open', 'Открыт')
        ('in_progress', 'В работе')
        ('waiting_user', 'Ожидание ответа пользователя')
        ('waiting_admin', 'Ожидание ответа оператора')
        ('on_hold', 'На удержании')
        ('resolved', 'Решён')
        ('closed', 'Закрыт')
        ('reopened', 'Переоткрыт')
      default: 'new'

    # Тип (как создан)
    source:
      тип: CharField
      choices:
        ('form', 'Форма на сайте')
        ('chat', 'Живой чат')
        ('email', 'Email')
        ('telegram', 'Telegram')
        ('admin', 'Создан администратором')
      default: 'form'

    # Назначение
    assigned_to:
      тип: ForeignKey → User (staff), nullable
      on_delete: SET_NULL
      related_name: 'assigned_tickets'
      Оператор которому назначен

    assigned_at:
      тип: DateTimeField, nullable
      Когда назначен

    assigned_by:
      тип: ForeignKey → User (staff), nullable
      Кто назначил (система или другой оператор)

    # Связанные объекты (контекст)
    related_object_type:
      тип: CharField, max 50, blank=True
      Пример: 'Withdrawal', 'Bet', 'KYCDocument'

    related_object_id:
      тип: UUIDField, nullable
      ID связанного объекта

    # SLA
    first_response_at:
      тип: DateTimeField, nullable
      Когда первый раз ответил оператор
      Для расчёта SLA первого ответа

    resolved_at:
      тип: DateTimeField, nullable
      Когда решён

    closed_at:
      тип: DateTimeField, nullable

    # Теги (для аналитики)
    tags:
      тип: JSONField, default=list
      Пример: ["вывод", "криптовалюта", "задержка"]

    # Внутренние заметки
    internal_notes:
      тип: TextField, blank=True
      Видят только операторы

    # Оценка
    rating:
      тип: IntegerField, nullable
      1-5 звёзд
      Ставит пользователь после закрытия

    rating_comment:
      тип: TextField, blank=True, max 500
      Комментарий к оценке

    rated_at:
      тип: DateTimeField, nullable

    # Эскалация
    is_escalated:
      тип: BooleanField, default=False
      Эскалирован к старшему оператору / админу

    escalated_to:
      тип: ForeignKey → User (staff), nullable

    escalated_at:
      тип: DateTimeField, nullable

    escalation_reason:
      тип: TextField, blank=True

    # Мета
    ip_address:
      тип: GenericIPAddressField, nullable

    user_agent:
      тип: TextField, blank=True

    created_at:
      тип: DateTimeField, auto_now_add=True

    updated_at:
      тип: DateTimeField, auto_now=True

    Meta:
      verbose_name = 'Тикет'
      verbose_name_plural = 'Тикеты'
      ordering = ['-created_at']
      indexes:
        - status + priority + created_at
        - assigned_to + status
        - user + created_at
        - category + status
        - ticket_number

    Методы:
      __str__():
        return f'{self.ticket_number}: {self.subject}'

      time_since_creation():
        return now() - self.created_at

      time_to_first_response():
        if self.first_response_at:
          return self.first_response_at - self.created_at
        return None

      time_to_resolution():
        if self.resolved_at:
          return self.resolved_at - self.created_at
        return None

      is_sla_breached():
        sla = SLAConfig.get_for_priority(self.priority)
        if not self.first_response_at:
          return self.time_since_creation() > sla.first_response_time
        return False

      can_reopen():
        if self.status != 'closed':
          return False
        # Можно переоткрыть в течение 7 дней
        return (now() - self.closed_at).days <= 7

    Генерация ticket_number:
      def generate_ticket_number():
        today = date.today().strftime('%Y%m%d')
        last = Ticket.objects.filter(
          ticket_number__startswith=f'DOD-{today}'
        ).count()
        return f'DOD-{today}-{last + 1:04d}'
```

### Модель Message (Сообщения в тикете/чате)

```
class Message(models.Model):

    Назначение:
      Одно сообщение в тикете или чате.
      Используется и для тикетов и для живого чата.

    Поля:
    ─────
    id:
      тип: UUID, primary key

    ticket:
      тип: ForeignKey → Ticket
      on_delete: CASCADE
      related_name: 'messages'

    sender:
      тип: ForeignKey → User
      on_delete: CASCADE
      Отправитель (пользователь или оператор)

    # Тип отправителя
    sender_type:
      тип: CharField
      choices:
        ('user', 'Пользователь')
        ('operator', 'Оператор')
        ('system', 'Система')
        ('bot', 'Автоответ')

    # Содержимое
    text:
      тип: TextField, max 5000
      Текст сообщения
      HTML экранируется

    # Вложения
    # (через отдельную модель MessageAttachment)

    # Системные сообщения
    is_system_message:
      тип: BooleanField, default=False
      True для: "Тикет назначен оператору X",
      "Статус изменён на 'В работе'" и т.д.

    system_action:
      тип: CharField, max 50, blank=True
      Тип системного действия:
      'assigned', 'status_changed', 'escalated',
      'transferred', 'resolved', 'reopened'

    # Внутреннее (видит только поддержка)
    is_internal:
      тип: BooleanField, default=False
      Внутренняя заметка оператора
      Пользователь НЕ видит

    # Прочитано
    is_read_by_user:
      тип: BooleanField, default=False
      Прочитано пользователем

    is_read_by_operator:
      тип: BooleanField, default=False
      Прочитано оператором

    read_at:
      тип: DateTimeField, nullable

    # Мета
    ip_address:
      тип: GenericIPAddressField, nullable

    created_at:
      тип: DateTimeField, auto_now_add=True

    edited_at:
      тип: DateTimeField, nullable

    is_edited:
      тип: BooleanField, default=False

    Meta:
      verbose_name = 'Сообщение'
      ordering = ['created_at']
      indexes:
        - ticket + created_at
        - sender + created_at


class MessageAttachment(models.Model):

    Назначение:
      Вложения к сообщениям (скриншоты, документы).

    Поля:
    ─────
    id:
      тип: UUID, primary key

    message:
      тип: ForeignKey → Message
      on_delete: CASCADE
      related_name: 'attachments'

    file:
      тип: FileField
      upload_to: 'support/attachments/{ticket_id}/'

    original_filename:
      тип: CharField, max 255
      Оригинальное имя файла

    file_size:
      тип: IntegerField
      Размер в байтах

    file_type:
      тип: CharField, max 50
      MIME тип: 'image/png', 'application/pdf'

    is_image:
      тип: BooleanField, default=False

    thumbnail:
      тип: ImageField, nullable
      upload_to: 'support/attachments/thumbnails/'
      Для изображений: 200×200 превью

    created_at:
      тип: DateTimeField, auto_now_add=True

    Ограничения:
      Максимум файл: 10 МБ
      Форматы: jpg, png, gif, webp, pdf, doc, docx, txt
      Максимум вложений к одному сообщению: 5
      Максимум вложений в одном тикете: 20
```

### Модель ChatSession (Живой чат)

```
class ChatSession(models.Model):

    Назначение:
      Сессия живого чата.
      Привязана к тикету.
      Содержит WebSocket метаданные.

    Поля:
    ─────
    id:
      тип: UUID, primary key

    ticket:
      тип: OneToOneField → Ticket
      on_delete: CASCADE
      related_name: 'chat_session'

    user:
      тип: ForeignKey → User
      on_delete: CASCADE

    operator:
      тип: ForeignKey → User (staff), nullable
      on_delete: SET_NULL

    # Статус чата
    chat_status:
      тип: CharField
      choices:
        ('waiting', 'Ожидание оператора')
        ('active', 'Активный разговор')
        ('idle', 'Неактивен')
        ('ended', 'Завершён')
      default: 'waiting'

    # WebSocket
    user_channel_name:
      тип: CharField, max 255, blank=True
      Channel name для WebSocket пользователя

    operator_channel_name:
      тип: CharField, max 255, blank=True
      Channel name для WebSocket оператора

    # Очередь
    queue_position:
      тип: IntegerField, default=0
      Позиция в очереди (если ждёт оператора)

    queue_entered_at:
      тип: DateTimeField, nullable
      Когда встал в очередь

    # Статистика сессии
    operator_joined_at:
      тип: DateTimeField, nullable
      Когда оператор присоединился

    wait_time_seconds:
      тип: IntegerField, default=0
      Сколько ждал оператора

    messages_count:
      тип: IntegerField, default=0

    # Типизация (набирает текст)
    user_typing:
      тип: BooleanField, default=False
    operator_typing:
      тип: BooleanField, default=False

    # Мета
    started_at:
      тип: DateTimeField, auto_now_add=True

    ended_at:
      тип: DateTimeField, nullable

    ended_by:
      тип: CharField, max 20, blank=True
      choices: 'user', 'operator', 'system', 'timeout'

    Meta:
      verbose_name = 'Чат-сессия'
      ordering = ['-started_at']
      indexes:
        - chat_status
        - operator + chat_status
```

### Модель FAQ (База знаний)

```
class FAQCategory(models.Model):

    Назначение:
      Категория FAQ статей.

    Поля:
    ─────
    id:
      тип: UUID, primary key

    name:
      тип: CharField, max 100
    name_en:
      тип: CharField, max 100, blank=True

    slug:
      тип: SlugField, уникальный

    icon:
      тип: CharField, max 10

    sort_order:
      тип: IntegerField, default=0

    is_active:
      тип: BooleanField, default=True

    articles_count:
      тип: IntegerField, default=0

    Meta:
      ordering = ['sort_order']

    Предзаполнение:
      💰 Депозиты и выводы (deposits-withdrawals)
      👤 Аккаунт и профиль (account)
      🪪 Верификация (verification)
      ⚽ Ставки на спорт (sports-betting)
      🎰 Казино (casino)
      📊 Маркеты предсказаний (predictions)
      🤝 Партнёрская программа (referral)
      🔐 Безопасность (security)
      💻 Технические вопросы (technical)


class FAQArticle(models.Model):

    Назначение:
      Одна FAQ статья.

    Поля:
    ─────
    id:
      тип: UUID, primary key

    category:
      тип: ForeignKey → FAQCategory
      on_delete: CASCADE
      related_name: 'articles'

    question:
      тип: CharField, max 300
      Вопрос (RU)

    question_en:
      тип: CharField, max 300, blank=True
      Вопрос (EN)

    answer:
      тип: TextField, max 10000
      Ответ (RU). Поддержка Markdown.

    answer_en:
      тип: TextField, blank=True
      Ответ (EN)

    slug:
      тип: SlugField, уникальный

    # SEO
    meta_description:
      тип: CharField, max 200, blank=True

    # Статистика
    views_count:
      тип: IntegerField, default=0

    helpful_yes:
      тип: IntegerField, default=0
      "Это было полезно? Да"

    helpful_no:
      тип: IntegerField, default=0
      "Это было полезно? Нет"

    # Связь с тикетами
    related_ticket_categories:
      тип: JSONField, default=list
      Категории тикетов для автопредложения
      Пример: ['withdrawal', 'finance']

    # Ключевые слова для поиска
    keywords:
      тип: JSONField, default=list
      Пример: ['вывод', 'задержка', 'сроки', 'комиссия']

    sort_order:
      тип: IntegerField, default=0

    is_active:
      тип: BooleanField, default=True

    is_pinned:
      тип: BooleanField, default=False
      Закреплённая (показывается первой)

    created_by:
      тип: ForeignKey → User (staff), nullable

    created_at:
      тип: DateTimeField, auto_now_add=True
    updated_at:
      тип: DateTimeField, auto_now=True

    Meta:
      verbose_name = 'FAQ статья'
      ordering = ['-is_pinned', 'sort_order', '-views_count']
      indexes:
        - category + is_active + sort_order
        - is_active + views_count
```

### Модель QuickReply (Шаблоны ответов для операторов)

```
class QuickReply(models.Model):

    Назначение:
      Готовые шаблоны ответов для операторов.
      Для ускорения работы.

    Поля:
    ─────
    id:
      тип: UUID, primary key

    title:
      тип: CharField, max 100
      Краткое название для оператора
      Пример: "Приветствие", "Задержка вывода",
      "Запрос скриншота"

    text:
      тип: TextField, max 3000
      Текст ответа
      Поддержка переменных:
        {username} — имя пользователя
        {ticket_number} — номер тикета
        {operator_name} — имя оператора

    category:
      тип: CharField, max 50, blank=True
      Для фильтрации
      Пример: 'greeting', 'finance', 'technical'

    # Доступность
    is_global:
      тип: BooleanField, default=True
      True = для всех операторов
      False = только для создателя

    created_by:
      тип: ForeignKey → User (staff)

    usage_count:
      тип: IntegerField, default=0
      Сколько раз использован

    sort_order:
      тип: IntegerField, default=0

    is_active:
      тип: BooleanField, default=True

    created_at:
      тип: DateTimeField, auto_now_add=True

    Meta:
      verbose_name = 'Быстрый ответ'
      ordering = ['-usage_count']

    Предзаполнение:
      - "Приветствие": "Здравствуйте, {username}! Меня
        зовут {operator_name}. Чем могу помочь?"
      - "Запрос деталей": "Для решения вашего вопроса мне
        нужна дополнительная информация. Пожалуйста,
        уточните..."
      - "Задержка вывода": "Ваш вывод находится на проверке.
        Обработка занимает до 24 часов. Мы уведомим вас
        как только средства будут отправлены."
      - "Скриншот": "Пожалуйста, отправьте скриншот
        проблемы для более быстрого решения."
      - "KYC нужна": "Для вывода данной суммы необходимо
        пройти верификацию. Перейдите в раздел
        Безопасность → KYC."
      - "Завершение": "Рад был помочь! Если у вас
        возникнут ещё вопросы — обращайтесь.
        Хорошего дня, {username}!"
```

### Модель SLAConfig

```
class SLAConfig(models.Model):

    Назначение:
      Настройки SLA (Service Level Agreement)
      для каждого приоритета тикета.

    Поля:
    ─────
    priority:
      тип: CharField, primary key
      'low', 'medium', 'high', 'critical'

    # Первый ответ
    first_response_minutes:
      тип: IntegerField
      Максимум минут до первого ответа
      low: 480 (8 часов)
      medium: 240 (4 часа)
      high: 60 (1 час)
      critical: 15 (15 минут)

    # Время решения
    resolution_minutes:
      тип: IntegerField
      Максимум минут до решения
      low: 2880 (48 часов)
      medium: 1440 (24 часа)
      high: 480 (8 часов)
      critical: 120 (2 часа)

    # Живой чат
    chat_response_seconds:
      тип: IntegerField
      Максимум секунд до ответа в чате
      critical: 30
      high: 60
      medium: 120
      low: 300

    # Рабочие часы
    business_hours_only:
      тип: BooleanField, default=True
      Считать SLA только в рабочие часы
      low/medium: True
      high/critical: False (24/7)

    Meta:
      verbose_name = 'Настройки SLA'

    Предзаполнение (fixtures)
```

### Модель OperatorProfile (Профиль оператора)

```
class OperatorProfile(models.Model):

    Назначение:
      Расширение User для операторов поддержки.
      Содержит статус, нагрузку, статистику.

    Поля:
    ─────
    user:
      тип: OneToOneField → User
      on_delete: CASCADE
      related_name: 'operator_profile'

    # Статус оператора
    operator_status:
      тип: CharField
      choices:
        ('online', 'На линии')
        ('busy', 'Занят')
        ('away', 'Отошёл')
        ('offline', 'Оффлайн')
      default: 'offline'

    # Нагрузка
    max_concurrent_chats:
      тип: IntegerField, default=5
      Максимум одновременных чатов

    current_chats_count:
      тип: IntegerField, default=0
      Текущее количество активных чатов

    current_tickets_count:
      тип: IntegerField, default=0
      Тикеты в работе

    # Специализация
    categories:
      тип: JSONField, default=list
      Категории которые оператор обрабатывает
      Пример: ['finance', 'withdrawal', 'deposit']
      Пустой список = все категории

    # Разрешения
    can_handle_critical:
      тип: BooleanField, default=False
      Может обрабатывать критические тикеты

    can_escalate:
      тип: BooleanField, default=True

    can_close_tickets:
      тип: BooleanField, default=True

    can_transfer:
      тип: BooleanField, default=True
      Может передавать другому оператору

    # Статистика
    total_tickets_handled:
      тип: IntegerField, default=0

    total_chats_handled:
      тип: IntegerField, default=0

    avg_rating:
      тип: DecimalField(3, 2), default=0
      Средняя оценка (1-5)

    total_ratings:
      тип: IntegerField, default=0

    avg_first_response_seconds:
      тип: IntegerField, default=0
      Среднее время первого ответа

    avg_resolution_seconds:
      тип: IntegerField, default=0
      Среднее время решения

    # Смена
    shift_start:
      тип: TimeField, nullable
    shift_end:
      тип: TimeField, nullable

    # Мета
    last_status_change:
      тип: DateTimeField, auto_now=True

    Meta:
      verbose_name = 'Профиль оператора'

    Методы:
      is_available():
        return (
          self.operator_status == 'online'
          and self.current_chats_count < self.max_concurrent_chats
        )

      accept_chat():
        self.current_chats_count += 1
        self.save()

      release_chat():
        self.current_chats_count = max(0, self.current_chats_count - 1)
        self.save()
```

### Модель CannedAutoResponse (Автоответы)

```
class AutoResponse(models.Model):

    Назначение:
      Автоматические ответы на частые вопросы.
      Триггерятся по ключевым словам в тикете.
      Отправляются ДО подключения оператора.

    Поля:
    ─────
    id:
      тип: UUID, primary key

    name:
      тип: CharField, max 100
      Название для администратора

    # Условие срабатывания
    trigger_keywords:
      тип: JSONField
      Список ключевых слов (любое из них → срабатывание)
      Пример: ["не могу вывести", "вывод не приходит",
               "задержка вывода", "где мой вывод"]

    trigger_categories:
      тип: JSONField, default=list
      Категории тикетов в которых срабатывает
      Пример: ['withdrawal', 'finance']
      Пустой = все категории

    # Ответ
    response_text:
      тип: TextField, max 3000
      Текст автоответа

    # Связь с FAQ
    related_faq:
      тип: ForeignKey → FAQArticle, nullable
      Предложить статью из FAQ

    # Настройки
    is_active:
      тип: BooleanField, default=True

    priority:
      тип: IntegerField, default=0
      Если несколько подходят → берётся с высшим приоритетом

    # Статистика
    times_triggered:
      тип: IntegerField, default=0
    times_resolved:
      тип: IntegerField, default=0
      Сколько раз тикет закрылся после автоответа
      (значит помогло)

    created_at:
      тип: DateTimeField, auto_now_add=True

    Meta:
      verbose_name = 'Автоответ'
      ordering = ['-priority']
```

### Критерий готовности шага 9.1

```
□ Приложение support создано
□ Django Channels настроен + Redis channel layer
□ ASGI конфигурация
□ Модель Ticket: все поля + генерация номера
□ Модель Message + MessageAttachment
□ Модель ChatSession
□ Модель FAQCategory + FAQArticle (fixtures)
□ Модель QuickReply (fixtures)
□ Модель SLAConfig (fixtures)
□ Модель OperatorProfile
□ Модель AutoResponse
□ Все миграции применены
□ Django Admin: все модели
□ OperatorProfile создаётся для staff пользователей
□ Индексы для быстрых запросов
```

---

## ШАГ 9.2 — ТИКЕТ-СИСТЕМА

### Задача

```
Реализуй полный цикл тикета:
создание, ответы, смена статуса, назначение,
эскалация, закрытие, оценка.
Автоответы и предложение FAQ.
```

### TicketService

```
TicketService:

  create_ticket(user, category, subject, description,
                attachments=None, request=None):
    """
    Создание нового тикета.
    """

    # 1. Валидация
    if len(subject) < 5:
      return None, 'Тема слишком короткая (минимум 5 символов)'
    if len(description) < 20:
      return None, 'Опишите проблему подробнее (минимум 20 символов)'

    # Rate limit: максимум 5 тикетов в день
    today_tickets = Ticket.objects.filter(
      user=user, created_at__date=date.today()
    ).count()
    if today_tickets >= 5:
      return None, 'Превышен лимит обращений (5 в день)'

    # 2. Автоопределение приоритета
    priority = determine_priority(category, user)

    # 3. Создать тикет
    ticket = Ticket.objects.create(
      user=user,
      category=category,
      subject=subject,
      description=description,
      priority=priority,
      source='form',
      ip_address=get_client_ip(request) if request else None,
      user_agent=request.META.get('HTTP_USER_AGENT', '') if request else '',
    )

    # 4. Первое сообщение
    first_message = Message.objects.create(
      ticket=ticket,
      sender=user,
      sender_type='user',
      text=description,
      ip_address=ticket.ip_address,
    )

    # 5. Обработка вложений
    if attachments:
      for file in attachments[:5]:
        process_attachment(first_message, file)

    # 6. Автоответ
    auto_response = check_auto_response(ticket)
    if auto_response:
      Message.objects.create(
        ticket=ticket,
        sender=None,  # Бот
        sender_type='bot',
        text=auto_response.response_text,
        is_system_message=False,
      )
      auto_response.times_triggered += 1
      auto_response.save(update_fields=['times_triggered'])

    # 7. Предложить FAQ
    suggested_faqs = suggest_faq_articles(category, subject, description)

    # 8. Назначить оператора
    AssignmentService.auto_assign(ticket)

    # 9. Уведомления
    # Пользователю:
    NotificationService.create_notification(
      user=user,
      notification_type='ticket_created',
      title=f'Тикет #{ticket.ticket_number} создан',
      message=f'Ваше обращение принято. '
              f'Мы ответим в течение '
              f'{SLAConfig.get_for_priority(priority).first_response_minutes // 60} часов.',
      icon='📋',
      link=f'/support/tickets/{ticket.id}/',
    )

    # Операторам (через WebSocket):
    notify_operators_new_ticket(ticket)

    return ticket, None


  add_reply(ticket, sender, text, attachments=None,
            is_internal=False):
    """
    Добавить ответ в тикет.
    sender может быть user или operator.
    """

    sender_type = 'operator' if sender.is_staff else 'user'

    message = Message.objects.create(
      ticket=ticket,
      sender=sender,
      sender_type=sender_type,
      text=text,
      is_internal=is_internal,
    )

    if attachments:
      for file in attachments[:5]:
        process_attachment(message, file)

    # Обновить статус тикета
    if sender_type == 'operator' and not is_internal:
      # Оператор ответил
      if not ticket.first_response_at:
        ticket.first_response_at = now()
      ticket.status = 'waiting_user'
      ticket.save(update_fields=['first_response_at', 'status', 'updated_at'])

      # Уведомить пользователя
      NotificationService.create_notification(
        user=ticket.user,
        notification_type='ticket_reply',
        title=f'Ответ на тикет #{ticket.ticket_number}',
        message=text[:200] + ('...' if len(text) > 200 else ''),
        icon='💬',
        link=f'/support/tickets/{ticket.id}/',
      )

    elif sender_type == 'user':
      # Пользователь ответил
      ticket.status = 'waiting_admin'
      ticket.save(update_fields=['status', 'updated_at'])

      # Уведомить оператора (WebSocket)
      if ticket.assigned_to:
        notify_operator_new_message(ticket, message)

    # Обновить updated_at
    ticket.save(update_fields=['updated_at'])

    return message


  change_status(ticket, new_status, changed_by, reason=''):
    """Изменить статус тикета."""

    old_status = ticket.status
    ticket.status = new_status

    if new_status == 'resolved':
      ticket.resolved_at = now()
    elif new_status == 'closed':
      ticket.closed_at = now()
    elif new_status == 'reopened':
      ticket.resolved_at = None
      ticket.closed_at = None

    ticket.save()

    # Системное сообщение
    Message.objects.create(
      ticket=ticket,
      sender=changed_by,
      sender_type='system',
      text=f'Статус изменён: {old_status} → {new_status}'
           + (f'. Причина: {reason}' if reason else ''),
      is_system_message=True,
      system_action='status_changed',
    )

    # Уведомление пользователю
    if new_status == 'resolved':
      NotificationService.create_notification(
        user=ticket.user,
        notification_type='ticket_resolved',
        title=f'Тикет #{ticket.ticket_number} решён',
        message='Ваше обращение решено. Пожалуйста, '
                'оцените качество поддержки.',
        icon='✅',
        link=f'/support/tickets/{ticket.id}/',
      )


  escalate_ticket(ticket, escalated_by, reason, escalate_to=None):
    """Эскалация тикета."""

    ticket.is_escalated = True
    ticket.escalated_at = now()
    ticket.escalation_reason = reason
    ticket.priority = 'critical'

    if escalate_to:
      ticket.escalated_to = escalate_to
      ticket.assigned_to = escalate_to
    else:
      # Найти свободного старшего оператора
      senior = OperatorProfile.objects.filter(
        can_handle_critical=True,
        operator_status='online',
      ).order_by('current_tickets_count').first()
      if senior:
        ticket.escalated_to = senior.user
        ticket.assigned_to = senior.user

    ticket.save()

    Message.objects.create(
      ticket=ticket,
      sender=escalated_by,
      sender_type='system',
      text=f'Тикет эскалирован. Причина: {reason}',
      is_system_message=True,
      system_action='escalated',
    )

    # Уведомить эскалированному оператору
    if ticket.escalated_to:
      notify_operator_escalation(ticket)


  rate_ticket(ticket, user, rating, comment=''):
    """Оценка пользователем после решения."""

    if ticket.user != user:
      return False, 'Нельзя оценить чужой тикет'
    if ticket.status not in ('resolved', 'closed'):
      return False, 'Тикет ещё не решён'
    if ticket.rating is not None:
      return False, 'Вы уже оценили этот тикет'

    ticket.rating = rating  # 1-5
    ticket.rating_comment = comment
    ticket.rated_at = now()
    ticket.save(update_fields=['rating', 'rating_comment', 'rated_at'])

    # Обновить статистику оператора
    if ticket.assigned_to:
      op = ticket.assigned_to.operator_profile
      total_sum = op.avg_rating * op.total_ratings + rating
      op.total_ratings += 1
      op.avg_rating = total_sum / op.total_ratings
      op.save(update_fields=['avg_rating', 'total_ratings'])

    return True, None


  determine_priority(category, user):
    """Автоопределение приоритета."""
    if category == 'security':
      return 'critical'
    if category in ('withdrawal', 'deposit'):
      return 'high'
    if category in ('complaint', 'verification'):
      return 'high'
    if category in ('suggestion',):
      return 'low'
    # VIP пользователь → повышаем
    if user.trust_level >= 4:
      return 'high'
    return 'medium'


  check_auto_response(ticket):
    """Проверить есть ли подходящий автоответ."""
    text = f'{ticket.subject} {ticket.description}'.lower()

    responses = AutoResponse.objects.filter(is_active=True)
    for resp in responses:
      # Проверить категорию
      if resp.trigger_categories:
        if ticket.category not in resp.trigger_categories:
          continue

      # Проверить ключевые слова
      for keyword in resp.trigger_keywords:
        if keyword.lower() in text:
          return resp

    return None


  suggest_faq_articles(category, subject, description):
    """Предложить FAQ статьи по теме."""
    text = f'{subject} {description}'.lower()
    words = set(text.split())

    articles = FAQArticle.objects.filter(
      is_active=True,
      related_ticket_categories__contains=[category],
    )

    scored = []
    for article in articles:
      score = 0
      for keyword in article.keywords:
        if keyword.lower() in text:
          score += 1
      if score > 0:
        scored.append((article, score))

    scored.sort(key=lambda x: -x[1])
    return [a for a, s in scored[:3]]
```

### AssignmentService (Распределение)

```
AssignmentService:

  auto_assign(ticket):
    """
    Автоматическое назначение тикета оператору.
    Алгоритм: Round-robin с учётом специализации
    и нагрузки.
    """

    # 1. Найти подходящих операторов
    operators = OperatorProfile.objects.filter(
      operator_status='online',
    )

    # Если критический — только с разрешением
    if ticket.priority == 'critical':
      operators = operators.filter(can_handle_critical=True)

    # Фильтр по специализации
    specialized = operators.filter(
      categories__contains=[ticket.category]
    )
    if specialized.exists():
      operators = specialized

    # 2. Сортировать по нагрузке (меньше тикетов → приоритет)
    operators = operators.order_by('current_tickets_count')

    operator = operators.first()

    if operator:
      ticket.assigned_to = operator.user
      ticket.assigned_at = now()
      ticket.status = 'open'
      ticket.save(update_fields=[
        'assigned_to', 'assigned_at', 'status'
      ])

      operator.current_tickets_count += 1
      operator.save(update_fields=['current_tickets_count'])

      Message.objects.create(
        ticket=ticket,
        sender=operator.user,
        sender_type='system',
        text=f'Тикет назначен оператору',
        is_system_message=True,
        system_action='assigned',
      )

    return operator


  transfer_ticket(ticket, from_operator, to_operator, reason=''):
    """Передача тикета другому оператору."""

    old = ticket.assigned_to
    ticket.assigned_to = to_operator
    ticket.assigned_at = now()
    ticket.save(update_fields=['assigned_to', 'assigned_at'])

    # Обновить нагрузку
    if old and hasattr(old, 'operator_profile'):
      old.operator_profile.release_chat()
    to_operator.operator_profile.current_tickets_count += 1
    to_operator.operator_profile.save()

    Message.objects.create(
      ticket=ticket,
      sender=from_operator,
      sender_type='system',
      text=f'Тикет передан другому оператору'
           + (f'. Причина: {reason}' if reason else ''),
      is_system_message=True,
      system_action='transferred',
      is_internal=True,
    )
```

### Страница создания тикета (пользователь)

```
URL: /support/new/
Доступ: @login_required

  ┌──────────────────────────────────────────────────────┐
  │  📋 Новое обращение                                 │
  │                                                      │
  │  Прежде чем обращаться, проверьте FAQ:              │
  │  [🔍 Поиск по базе знаний _______________]         │
  │                                                      │
  │  Категория *                                        │
  │  ┌──────────────────────────────────────────────┐   │
  │  │ 💰 Финансы и платежи                       ▼ │   │
  │  └──────────────────────────────────────────────┘   │
  │                                                      │
  │  Тема *                                             │
  │  ┌──────────────────────────────────────────────┐   │
  │  │ Вывод не приходит более 24 часов             │   │
  │  └──────────────────────────────────────────────┘   │
  │                                                      │
  │  💡 Возможно вам поможет:                           │
  │  ┌──────────────────────────────────────────────┐   │
  │  │ 📖 Сроки обработки выводов                  │   │
  │  │ 📖 Почему мой вывод задерживается?           │   │
  │  └──────────────────────────────────────────────┘   │
  │  (HTMX: подгружается при вводе темы)               │
  │                                                      │
  │  Описание проблемы *                                │
  │  ┌──────────────────────────────────────────────┐   │
  │  │ Подробно опишите проблему...                 │   │
  │  │ Минимум 20 символов.                         │   │
  │  │                                              │   │
  │  │                                              │   │
  │  └──────────────────────────────────────────────┘   │
  │                                                      │
  │  📎 Прикрепить файлы (до 5, макс 10 МБ каждый)    │
  │  [📤 Выбрать файлы]                                │
  │                                                      │
  │  [Отправить обращение]                              │
  │                                                      │
  └──────────────────────────────────────────────────────┘

HTMX:
  При выборе категории и вводе темы:
    hx-get="/api/support/suggest-faq/"
    hx-trigger="keyup changed delay:500ms"
    hx-target="#faq-suggestions"
    Подгружает подходящие FAQ статьи
```

### Критерий готовности шага 9.2

```
□ Создание тикета: форма + валидация
□ Автоопределение приоритета
□ Автоответ при совпадении ключевых слов
□ Предложение FAQ при создании (HTMX)
□ Вложения: загрузка + валидация + thumbnail
□ Автоназначение оператору
□ Ответ оператора → уведомление пользователю
□ Ответ пользователя → уведомление оператору
□ Смена статуса: все переходы
□ Эскалация: с назначением старшему
□ Передача другому оператору
□ Оценка тикета (1-5 звёзд)
□ Обновление статистики оператора
□ Системные сообщения (назначен, статус, эскалация)
□ Rate limit: 5 тикетов в день
□ Генерация номера тикета (DOD-YYYYMMDD-NNNN)
□ Внутренние заметки (видны только операторам)
```

---

## ШАГ 9.3 — ЖИВОЙ ЧАТ (WEBSOCKET)

### Задача

```
Реализуй живой чат через Django Channels.
WebSocket соединение. Обмен сообщениями
в реальном времени. Очередь ожидания.
Индикатор "печатает". Переподключение.
```

### WebSocket Consumer

```
# apps/support/consumers.py

import json
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone


class ChatConsumer(AsyncJsonWebsocketConsumer):
    """
    WebSocket consumer для живого чата поддержки.
    
    Протокол сообщений (JSON):
    
    Клиент → Сервер:
      {"type": "message", "text": "Привет"}
      {"type": "typing", "is_typing": true}
      {"type": "read", "message_id": "uuid"}
      {"type": "end_chat"}
    
    Сервер → Клиент:
      {"type": "message", "data": {...}}
      {"type": "typing", "is_typing": true, "sender": "operator"}
      {"type": "read_receipt", "message_id": "uuid"}
      {"type": "operator_joined", "operator": {...}}
      {"type": "queue_update", "position": 3, "wait_time": "~5 мин"}
      {"type": "chat_ended", "reason": "operator"}
      {"type": "system", "text": "..."}
      {"type": "error", "message": "..."}
    """

    async def connect(self):
        """При подключении WebSocket."""
        self.user = self.scope['user']

        if not self.user.is_authenticated:
            await self.close(code=4001)
            return

        self.ticket_id = self.scope['url_route']['kwargs'].get('ticket_id')
        self.room_group_name = f'chat_{self.ticket_id}'

        # Проверить доступ
        has_access = await self.check_access()
        if not has_access:
            await self.close(code=4003)
            return

        # Присоединиться к группе
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name,
        )

        await self.accept()

        # Обновить channel name в ChatSession
        await self.update_channel_name()

        # Отправить историю сообщений
        history = await self.get_message_history()
        await self.send_json({
            'type': 'history',
            'messages': history,
        })

        # Если оператор — уведомить пользователя
        if self.user.is_staff:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'operator_joined_event',
                    'operator': {
                        'name': self.user.get_full_name() or self.user.username,
                        'avatar': self.user.get_avatar_url(),
                    },
                }
            )


    async def disconnect(self, close_code):
        """При отключении."""
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name,
        )

        # Обновить статус
        if self.user.is_staff:
            await self.set_operator_typing(False)
        else:
            await self.set_user_typing(False)


    async def receive_json(self, content):
        """Получение сообщения от клиента."""
        msg_type = content.get('type')

        if msg_type == 'message':
            await self.handle_message(content)
        elif msg_type == 'typing':
            await self.handle_typing(content)
        elif msg_type == 'read':
            await self.handle_read(content)
        elif msg_type == 'end_chat':
            await self.handle_end_chat()
        else:
            await self.send_json({
                'type': 'error',
                'message': 'Неизвестный тип сообщения',
            })


    async def handle_message(self, content):
        """Обработка нового сообщения."""
        text = content.get('text', '').strip()

        if not text:
            return

        if len(text) > 5000:
            await self.send_json({
                'type': 'error',
                'message': 'Сообщение слишком длинное (макс 5000)',
            })
            return

        # Rate limit: 1 сообщение в 2 секунды
        can_send = await self.check_rate_limit()
        if not can_send:
            await self.send_json({
                'type': 'error',
                'message': 'Слишком быстро. Подождите.',
            })
            return

        # Сохранить в БД
        message_data = await self.save_message(text)

        # Отправить всем в чате
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'data': message_data,
            }
        )

        # Сбросить typing
        if self.user.is_staff:
            await self.set_operator_typing(False)
        else:
            await self.set_user_typing(False)


    async def handle_typing(self, content):
        """Индикатор 'печатает'."""
        is_typing = content.get('is_typing', False)
        sender = 'operator' if self.user.is_staff else 'user'

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing_event',
                'is_typing': is_typing,
                'sender': sender,
            }
        )


    async def handle_read(self, content):
        """Пометка сообщения как прочитанного."""
        message_id = content.get('message_id')
        await self.mark_as_read(message_id)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'read_receipt_event',
                'message_id': message_id,
                'reader': 'operator' if self.user.is_staff else 'user',
            }
        )


    async def handle_end_chat(self):
        """Завершение чата."""
        ended_by = 'operator' if self.user.is_staff else 'user'
        await self.end_chat_session(ended_by)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_ended_event',
                'reason': ended_by,
            }
        )

    # ── Обработчики событий группы ──

    async def chat_message(self, event):
        """Отправка сообщения клиенту."""
        await self.send_json({
            'type': 'message',
            'data': event['data'],
        })

    async def typing_event(self, event):
        await self.send_json({
            'type': 'typing',
            'is_typing': event['is_typing'],
            'sender': event['sender'],
        })

    async def read_receipt_event(self, event):
        await self.send_json({
            'type': 'read_receipt',
            'message_id': event['message_id'],
            'reader': event['reader'],
        })

    async def operator_joined_event(self, event):
        await self.send_json({
            'type': 'operator_joined',
            'operator': event['operator'],
        })

    async def chat_ended_event(self, event):
        await self.send_json({
            'type': 'chat_ended',
            'reason': event['reason'],
        })

    async def queue_update_event(self, event):
        await self.send_json({
            'type': 'queue_update',
            'position': event['position'],
            'wait_time': event['wait_time'],
        })

    # ── Database операции ──

    @database_sync_to_async
    def check_access(self):
        """Проверка доступа к чату."""
        try:
            ticket = Ticket.objects.get(id=self.ticket_id)
            return (
              ticket.user == self.user
              or self.user.is_staff
            )
        except Ticket.DoesNotExist:
            return False

    @database_sync_to_async
    def save_message(self, text):
        """Сохранить сообщение в БД."""
        ticket = Ticket.objects.get(id=self.ticket_id)
        sender_type = 'operator' if self.user.is_staff else 'user'

        message = Message.objects.create(
            ticket=ticket,
            sender=self.user,
            sender_type=sender_type,
            text=text,
        )

        # Обновить тикет
        if sender_type == 'operator':
            if not ticket.first_response_at:
                ticket.first_response_at = timezone.now()
            ticket.status = 'waiting_user'
        else:
            ticket.status = 'waiting_admin'
        ticket.save(update_fields=['first_response_at', 'status', 'updated_at'])

        # Обновить ChatSession
        ChatSession.objects.filter(ticket=ticket).update(
            messages_count=models.F('messages_count') + 1,
        )

        return {
            'id': str(message.id),
            'text': message.text,
            'sender_type': sender_type,
            'sender_name': self.user.username,
            'sender_avatar': self.user.get_avatar_url(),
            'created_at': message.created_at.isoformat(),
            'attachments': [],
        }

    @database_sync_to_async
    def get_message_history(self):
        """Получить последние 50 сообщений."""
        ticket = Ticket.objects.get(id=self.ticket_id)
        messages = Message.objects.filter(
            ticket=ticket,
            is_internal=False,
        ).select_related('sender').order_by('-created_at')[:50]

        return [{
            'id': str(m.id),
            'text': m.text,
            'sender_type': m.sender_type,
            'sender_name': m.sender.username if m.sender else 'Система',
            'created_at': m.created_at.isoformat(),
            'is_system': m.is_system_message,
            'is_read': m.is_read_by_user if self.user.is_staff else m.is_read_by_operator,
        } for m in reversed(messages)]

    @database_sync_to_async
    def check_rate_limit(self):
        from django.core.cache import cache
        key = f'chat_rate:{self.user.id}'
        if cache.get(key):
            return False
        cache.set(key, True, 2)
        return True

    @database_sync_to_async
    def mark_as_read(self, message_id):
        if self.user.is_staff:
            Message.objects.filter(id=message_id).update(
                is_read_by_operator=True, read_at=timezone.now()
            )
        else:
            Message.objects.filter(id=message_id).update(
                is_read_by_user=True, read_at=timezone.now()
            )

    @database_sync_to_async
    def end_chat_session(self, ended_by):
        ChatSession.objects.filter(ticket_id=self.ticket_id).update(
            chat_status='ended',
            ended_at=timezone.now(),
            ended_by=ended_by,
        )
        if ended_by == 'operator':
            Ticket.objects.filter(id=self.ticket_id).update(
                status='resolved',
                resolved_at=timezone.now(),
            )

    @database_sync_to_async
    def update_channel_name(self):
        session = ChatSession.objects.filter(ticket_id=self.ticket_id).first()
        if session:
            if self.user.is_staff:
                session.operator_channel_name = self.channel_name
            else:
                session.user_channel_name = self.channel_name
            session.save()
```

### WebSocket Routing

```
# apps/support/routing.py

from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(
        r'ws/support/chat/(?P<ticket_id>[0-9a-f-]+)/$',
        consumers.ChatConsumer.as_asgi(),
    ),
]
```

### ChatService (Управление чатом)

```
ChatService:

  start_chat(user, category, initial_message, request=None):
    """
    Начать живой чат.
    Создаёт тикет + ChatSession + ставит в очередь.
    """

    # Проверить: есть ли уже активный чат
    active = ChatSession.objects.filter(
      user=user,
      chat_status__in=['waiting', 'active'],
    ).first()
    if active:
      return active.ticket, None  # Вернуть существующий

    # Создать тикет
    ticket, error = TicketService.create_ticket(
      user=user,
      category=category,
      subject=f'Чат: {initial_message[:50]}',
      description=initial_message,
      request=request,
    )
    if error:
      return None, error

    ticket.source = 'chat'
    ticket.save(update_fields=['source'])

    # Создать ChatSession
    session = ChatSession.objects.create(
      ticket=ticket,
      user=user,
      chat_status='waiting',
      queue_entered_at=timezone.now(),
    )

    # Попробовать назначить оператора сразу
    operator = AssignmentService.assign_to_chat(session)

    if operator:
      session.chat_status = 'active'
      session.operator = operator.user
      session.operator_joined_at = timezone.now()
      session.wait_time_seconds = 0
      session.save()
    else:
      # Поставить в очередь
      position = ChatSession.objects.filter(
        chat_status='waiting',
        queue_entered_at__lt=session.queue_entered_at,
      ).count() + 1
      session.queue_position = position
      session.save(update_fields=['queue_position'])

    return ticket, None


  get_queue_status():
    """Получить состояние очереди."""
    waiting = ChatSession.objects.filter(
      chat_status='waiting',
    ).count()

    avg_wait = ChatSession.objects.filter(
      chat_status='active',
      wait_time_seconds__gt=0,
      started_at__date=date.today(),
    ).aggregate(avg=Avg('wait_time_seconds'))['avg'] or 0

    online_operators = OperatorProfile.objects.filter(
      operator_status='online',
    ).count()

    return {
      'waiting': waiting,
      'avg_wait_seconds': int(avg_wait),
      'online_operators': online_operators,
      'estimated_wait': estimate_wait_time(waiting, online_operators),
    }


  process_queue():
    """
    Celery задача (каждые 10 секунд).
    Обрабатывает очередь: назначает операторов.
    """
    waiting_sessions = ChatSession.objects.filter(
      chat_status='waiting',
    ).order_by('queue_entered_at')

    for session in waiting_sessions:
      operator = AssignmentService.assign_to_chat(session)
      if operator:
        session.chat_status = 'active'
        session.operator = operator.user
        session.operator_joined_at = timezone.now()
        session.wait_time_seconds = (
          timezone.now() - session.queue_entered_at
        ).total_seconds()
        session.save()

        # Уведомить пользователя через WebSocket
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
          f'chat_{session.ticket_id}',
          {
            'type': 'operator_joined_event',
            'operator': {
              'name': operator.user.username,
            },
          }
        )
      else:
        # Обновить позицию в очереди
        new_position = ChatSession.objects.filter(
          chat_status='waiting',
          queue_entered_at__lt=session.queue_entered_at,
        ).count() + 1

        if new_position != session.queue_position:
          session.queue_position = new_position
          session.save(update_fields=['queue_position'])

          # Отправить обновление через WebSocket
          channel_layer = get_channel_layer()
          async_to_sync(channel_layer.group_send)(
            f'chat_{session.ticket_id}',
            {
              'type': 'queue_update_event',
              'position': new_position,
              'wait_time': estimate_wait_time(new_position, 0),
            }
          )
```

### Критерий готовности шага 9.3

```
□ WebSocket Consumer работает (connect/disconnect/receive)
□ Отправка/получение сообщений в реальном времени
□ Сохранение сообщений в БД
□ История сообщений при подключении
□ Индикатор "печатает" (typing)
□ Прочитано (read receipts)
□ Оператор присоединился (operator_joined)
□ Очередь ожидания (queue)
□ Обновление позиции в очереди
□ Завершение чата (с обеих сторон)
□ Rate limiting на сообщения (1 в 2 сек)
□ Проверка доступа (только участники)
□ Celery: обработка очереди (каждые 10 сек)
□ Автоназначение оператора
□ Переподключение при обрыве (фронт)
□ Системные сообщения
```

---

## ШАГ 9.4 — TELEGRAM БОТ УВЕДОМЛЕНИЙ

### Задача

```
Создай полноценный Telegram бот для DOD.
Привязка аккаунта. Уведомления.
Команды для проверки баланса и статуса.
```

### Структура

```
apps/telegram_bot/
├── __init__.py
├── bot.py               # Основной бот (python-telegram-bot)
├── handlers.py           # Обработчики команд
├── keyboards.py          # Клавиатуры
├── services.py           # Бизнес-логика
├── tasks.py              # Celery задачи отправки
├── webhook.py            # Django view для webhook
├── urls.py
└── management/
    └── commands/
        └── run_bot.py    # manage.py run_bot
```

### Зависимости

```
# requirements.txt (добавить)
python-telegram-bot==21.0
```

### Функционал бота

```
Команды:

  /start
    Приветствие + кнопка "Привязать аккаунт"
    Если уже привязан → показать меню

  /link
    Привязка аккаунта DOD.
    Генерирует одноразовый код (6 цифр).
    Пользователь вводит код на сайте DOD
    (или наоборот: на сайте генерируется код,
     вводится в боте).

    Поток:
    1. Пользователь пишет /link в боте
    2. Бот отвечает: "Перейдите на dod.com/settings/telegram
       и нажмите 'Привязать Telegram'.
       Вам будет показан 6-значный код.
       Отправьте его мне."
    3. Пользователь вводит код
    4. Бот проверяет код → привязывает telegram_id к User
    5. "Аккаунт привязан! Теперь вы будете получать
       уведомления."

  /unlink
    Отвязка аккаунта.

  /balance
    Показать баланс кошелька.
    "💰 Ваш баланс: $1,234.56"

  /bets
    Последние 5 ставок.
    "📋 Последние ставки:
     ⚽ Реал — Барса: П1 × 2.10 → ✅ +$21.00
     🎰 Crash x3.45 → ❌ -$10.00
     ..."

  /support
    "📋 Ваши тикеты:
     #DOD-20250320-0042 — В работе
     #DOD-20250319-0015 — Решён
     Создать новый тикет → dod.com/support/new/"

  /settings
    Настройки уведомлений.
    Inline клавиатура с чекбоксами:
    ☑ Безопасность
    ☑ Финансы
    ☑ Результаты ставок
    ☐ Промо-акции
    [Сохранить]

  /help
    Список всех команд.

  /referral
    "🤝 Ваша реферальная ссылка:
     https://dod.com/r/DOD-X7K9M2
     Рефералов: 35 | Заработано: $1,234"


Уведомления (отправляются ботом):

  🔐 Безопасность:
    "🔐 Вход с нового устройства
     Chrome, Windows • Москва, RU
     Время: 14:30
     Это вы? [Да] [Нет, заблокировать]"

  💰 Финансы:
    "💰 Депозит подтверждён
     +$100.00 на ваш счёт
     Баланс: $1,234.56"

    "💵 Вывод одобрен
     $500.00 → USDT TRC20
     Адрес: TJxk...7dF2"

  🎉 Ставки:
    "🎉 Ставка выиграла!
     ⚽ Реал Мадрид — Барселона
     П1 × 2.10
     Выигрыш: $210.00"

    "❌ Ставка проиграла
     🏀 Лейкерс — Бостон
     П2 × 1.85
     Потеря: $50.00"

  📊 Predictions:
    "📊 Маркет разрешён!
     Трамп победит на выборах 2028?
     Результат: YES
     Ваша выплата: $150.00 (+$63.00)"

  🤝 Реферальная:
    "🤝 Новый реферал!
     user456 зарегистрировался по вашей ссылке."

    "💰 Реферальная комиссия
     +$23.52 от user456
     Баланс партнёра: $234.50"

  📋 Поддержка:
    "💬 Ответ на тикет #DOD-20250320-0042
     Оператор написал:
     'Ваш вывод обрабатывается...'
     [Ответить на сайте]"

Inline кнопки в уведомлениях:
  [Открыть на сайте] → ссылка на dod.com
  [Это не я] → для входа с нового устройства
  [Ответить] → для тикетов
```

### Сервис отправки уведомлений в Telegram

```
# apps/telegram_bot/services.py

TelegramNotificationService:

  send_notification(user, title, message, buttons=None):
    """
    Отправить уведомление пользователю в Telegram.
    """
    if not user.telegram_id:
      return False

    # Проверить настройки
    if not user.notification_settings.get('telegram_notifications', False):
      return False

    from .tasks import send_telegram_message_task
    send_telegram_message_task.delay(
      chat_id=user.telegram_id,
      text=f'{title}\n\n{message}',
      buttons=buttons,
    )
    return True


# apps/telegram_bot/tasks.py

@shared_task(bind=True, max_retries=3)
def send_telegram_message_task(self, chat_id, text,
                                buttons=None, parse_mode='HTML'):
    """Celery задача отправки сообщения."""
    import telegram
    bot = telegram.Bot(token=settings.TELEGRAM_BOT_TOKEN)

    reply_markup = None
    if buttons:
      keyboard = []
      for btn in buttons:
        keyboard.append([
          telegram.InlineKeyboardButton(
            text=btn['text'],
            url=btn.get('url'),
            callback_data=btn.get('callback_data'),
          )
        ])
      reply_markup = telegram.InlineKeyboardMarkup(keyboard)

    try:
      bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode=parse_mode,
        reply_markup=reply_markup,
      )
    except telegram.error.Forbidden:
      # Пользователь заблокировал бота
      User.objects.filter(telegram_id=chat_id).update(
        telegram_id=None,
      )
    except Exception as exc:
      self.retry(exc=exc, countdown=30)
```

### Привязка аккаунта (на сайте)

```
URL: /settings/telegram/

  ┌──────────────────────────────────────────────────┐
  │  📱 Привязка Telegram                           │
  │                                                  │
  │  (если не привязан):                            │
  │                                                  │
  │  1. Откройте бота @DOD_bot в Telegram           │
  │     [Открыть бота →]                            │
  │                                                  │
  │  2. Отправьте боту команду /link                │
  │                                                  │
  │  3. Введите код ниже:                           │
  │  ┌────────────────────────────────────────┐     │
  │  │ 🔑 Ваш код: 847293                    │     │
  │  │ Действителен 10 минут                  │     │
  │  └────────────────────────────────────────┘     │
  │  [🔄 Новый код]                                 │
  │                                                  │
  │  (если привязан):                               │
  │                                                  │
  │  ✅ Telegram привязан: @username                │
  │  [Отвязать]                                     │
  │                                                  │
  └──────────────────────────────────────────────────┘
```

### Критерий готовности шага 9.4

```
□ Telegram бот создан и запускается
□ Webhook или polling настроен
□ /start — приветствие
□ /link — привязка аккаунта (код)
□ /unlink — отвязка
□ /balance — баланс
□ /bets — последние ставки
□ /support — тикеты
□ /settings — настройки уведомлений
□ /help — справка
□ /referral — реферальная ссылка
□ Отправка уведомлений через Celery
□ Все типы уведомлений с кнопками
□ Обработка блокировки бота пользователем
□ Страница привязки на сайте
□ Генерация одноразового кода
□ Retry при ошибках отправки
```

---

## ШАГ 9.5 — ФРОНТЕНД (СТРАНИЦЫ ПОДДЕРЖКИ)

### Задача

```
Создай все страницы поддержки:
центр помощи, FAQ, мои тикеты,
страница тикета, виджет живого чата,
панель оператора.
```

### Структура URL

```
# Пользовательские
/support/                          # Центр помощи
/support/faq/                      # FAQ
/support/faq/{category_slug}/      # Категория FAQ
/support/faq/{category}/{article}/ # Статья FAQ
/support/new/                      # Новый тикет
/support/tickets/                  # Мои тикеты
/support/tickets/{id}/             # Страница тикета
/support/chat/                     # Начать живой чат
/support/chat/{ticket_id}/         # Страница чата

# Панель оператора
/operator/                         # Дашборд оператора
/operator/tickets/                 # Тикеты в работе
/operator/tickets/{id}/            # Тикет (оператор)
/operator/chats/                   # Активные чаты
/operator/chat/{ticket_id}/        # Чат (оператор)
/operator/queue/                   # Очередь

# API (HTMX + WebSocket)
/api/support/suggest-faq/          # Предложение FAQ
/api/support/faq/{id}/helpful/     # Оценка FAQ
/api/support/ticket/{id}/reply/    # Ответ в тикет
/api/support/ticket/{id}/rate/     # Оценка тикета
/api/support/chat/start/           # Начать чат
/api/support/queue-status/         # Статус очереди
```

### Центр помощи

```
URL: /support/

  ┌──────────────────────────────────────────────────────────────┐
  │  💬 Центр помощи                                            │
  │                                                              │
  │  ┌──────────────────────────────────────────────────────┐   │
  │  │  🔍 Поиск по базе знаний...                          │   │
  │  └──────────────────────────────────────────────────────┘   │
  │  (HTMX: результаты появляются при вводе)                   │
  │                                                              │
  │  ── Популярные вопросы ────────────────────────────────────  │
  │                                                              │
  │  📖 Как пополнить счёт?                                     │
  │  📖 Сколько занимает вывод средств?                         │
  │  📖 Как пройти верификацию?                                 │
  │  📖 Как использовать реферальную ссылку?                    │
  │                                                              │
  │  ── Категории FAQ ─────────────────────────────────────────  │
  │                                                              │
  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
  │  │ 💰       │ │ 👤       │ │ 🪪       │ │ ⚽       │      │
  │  │ Депозиты │ │ Аккаунт  │ │ KYC      │ │ Ставки   │      │
  │  │ и выводы │ │          │ │          │ │          │      │
  │  │ 12 статей│ │ 8 статей │ │ 6 статей │ │ 15 стат. │      │
  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘      │
  │                                                              │
  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
  │  │ 🎰       │ │ 📊       │ │ 🤝       │ │ 🔐       │      │
  │  │ Казино   │ │ Predict. │ │ Партнёрка│ │ Безопасн.│      │
  │  │ 10 стат. │ │ 7 статей │ │ 9 статей │ │ 11 стат. │      │
  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘      │
  │                                                              │
  │  ── Не нашли ответ? ───────────────────────────────────────  │
  │                                                              │
  │  ┌─────────────────────┐  ┌─────────────────────┐          │
  │  │ 💬 Живой чат        │  │ 📋 Создать тикет    │          │
  │  │ Ответ за ~3 минуты  │  │ Ответ за ~4 часа    │          │
  │  │                     │  │                     │          │
  │  │ 🟢 Операторы онлайн │  │ Для сложных         │          │
  │  │ В очереди: 2        │  │ вопросов             │          │
  │  │                     │  │                     │          │
  │  │ [Начать чат →]      │  │ [Создать тикет →]   │          │
  │  └─────────────────────┘  └─────────────────────┘          │
  │                                                              │
  └──────────────────────────────────────────────────────────────┘
```

### Виджет живого чата (плавающая кнопка)

```
На ВСЕХ страницах сайта (если авторизован):

  Правый нижний угол:
  ┌──────┐
  │  💬  │  ← круглая кнопка (60×60px)
  │      │     зелёная если операторы онлайн
  └──────┘     серая если оффлайн

  При клике → разворачивается окно чата:

  ┌────────────────────────────────────┐
  │  💬 Чат с поддержкой    [─] [✕]  │
  │  ──────────────────────────────── │
  │                                    │
  │  (если нет активного чата):       │
  │                                    │
  │  Здравствуйте! 👋                 │
  │  Чем можем помочь?                │
  │                                    │
  │  Категория:                        │
  │  [💰 Финансы] [👤 Аккаунт]       │
  │  [🎰 Казино] [⚽ Ставки]         │
  │  [🔐 Безопасность] [Другое]      │
  │                                    │
  │  ┌──────────────────────────────┐ │
  │  │ Опишите вашу проблему...     │ │
  │  └──────────────────────────────┘ │
  │  [Начать чат]                     │
  │                                    │
  │  (если есть активный чат):        │
  │                                    │
  │  🟢 Оператор: Алексей             │
  │                                    │
  │  ┌──────────────────────────────┐ │
  │  │ 🤖 Здравствуйте! Чем могу   │ │
  │  │    помочь?        14:30     │ │
  │  │                              │ │
  │  │              Не могу вывести │ │
  │  │              средства  14:31│ │
  │  │                              │ │
  │  │ 👤 Добрый день! Уточните    │ │
  │  │    номер вашего вывода.     │ │
  │  │                    14:32 ✓✓ │ │
  │  │                              │ │
  │  │ Алексей печатает...          │ │
  │  └──────────────────────────────┘ │
  │                                    │
  │  ┌──────────────────────┐ [📎][→]│
  │  │ Введите сообщение... │         │
  │  └──────────────────────┘         │
  │                                    │
  └────────────────────────────────────┘

  Размер: 380×500px (десктоп)
  Мобильные: полноэкранный

  WebSocket: подключается при открытии окна
  Автопереподключение: при обрыве через 3 секунды
  Звук: при новом сообщении от оператора
  Бейдж: на кнопке чата (количество непрочитанных)
```

### Панель оператора

```
URL: /operator/
Доступ: @staff_required + is_support_operator

  ┌──────────────────────────────────────────────────────────────┐
  │  🎧 Панель оператора                                       │
  │                                                              │
  │  Статус: [🟢 На линии ▼]                                    │
  │  (online / busy / away / offline)                            │
  │                                                              │
  │  ── Сводка ────────────────────────────────────────────────  │
  │  💬 Активных чатов: 3/5                                     │
  │  📋 Тикетов в работе: 8                                     │
  │  ⏳ В очереди: 2 чата                                       │
  │  ⚠️ SLA нарушено: 1 тикет                                  │
  │  ⭐ Ваш рейтинг: 4.7/5.0                                   │
  │                                                              │
  │  ┌────────────────────┐  ┌──────────────────────────────┐   │
  │  │  ЧАТЫ (3)          │  │  ТЕКУЩИЙ ЧАТ                │   │
  │  │                    │  │                              │   │
  │  │  🟢 user456        │  │  👤 user456                  │   │
  │  │  "Не могу вывести" │  │  Категория: Финансы          │   │
  │  │  2 мин назад    ● │  │  Trust: 🟡 Проверенный       │   │
  │  │                    │  │  Баланс: $1,234              │   │
  │  │  🟢 player789      │  │                              │   │
  │  │  "Ставка не засчит"│  │  ── Чат ──────────────────  │   │
  │  │  5 мин назад       │  │                              │   │
  │  │                    │  │  (сообщения чата)            │   │
  │  │  🟡 trader123      │  │                              │   │
  │  │  "KYC отклонена"   │  │                              │   │
  │  │  12 мин назад      │  │  ── Быстрые ответы ──────  │   │
  │  │                    │  │  [Приветствие]               │   │
  │  │  ── ОЧЕРЕДЬ (2) ── │  │  [Задержка вывода]          │   │
  │  │                    │  │  [Запрос скриншота]          │   │
  │  │  ⏳ newuser1       │  │  [Завершение]               │   │
  │  │  ждёт 3 мин       │  │                              │   │
  │  │  [Принять]         │  │  ── Инфо о пользователе ──  │   │
  │  │                    │  │  Регистрация: 10.03.2025     │   │
  │  │  ⏳ newuser2       │  │  Депозитов: $500             │   │
  │  │  ждёт 1 мин       │  │  KYC: ✅ Одобрена            │   │
  │  │  [Принять]         │  │  Предыдущие тикеты: 2       │   │
  │  │                    │  │                              │   │
  │  │  ── ТИКЕТЫ (8) ── │  │  ── Действия ────────────  │   │
  │  │                    │  │  [Внутренняя заметка]        │   │
  │  │  🔴 #0042 critical│  │  [Передать]                  │   │
  │  │  📋 #0041 high    │  │  [Эскалировать]              │   │
  │  │  📋 #0040 medium  │  │  [Завершить чат]             │   │
  │  │  ...               │  │                              │   │
  │  └────────────────────┘  └──────────────────────────────┘   │
  │                                                              │
  └──────────────────────────────────────────────────────────────┘

Оператор работает со ВСЕМИ чатами в одном окне.
Переключение между чатами — клик в списке слева.
WebSocket для КАЖДОГО активного чата.
Звук при новом сообщении в неактивном чате.
Непрочитанные — синяя точка рядом с именем.
```

### Критерий готовности шага 9.5

```
□ Центр помощи: поиск, категории, популярные
□ FAQ: категории, статьи, поиск
□ FAQ: "Это было полезно?" (да/нет)
□ Страница создания тикета (с предложением FAQ)
□ Мои тикеты: список с фильтрами
□ Страница тикета: сообщения + ответ + вложения
□ Оценка тикета (1-5 звёзд)
□ Виджет чата: плавающая кнопка на всех страницах
□ Виджет чата: выбор категории + начало
□ Виджет чата: WebSocket сообщения
□ Виджет чата: typing индикатор
□ Виджет чата: вложения (фото)
□ Виджет чата: звук при новом сообщении
□ Виджет чата: бейдж непрочитанных
□ Виджет чата: мобильная версия (fullscreen)
□ Панель оператора: дашборд
□ Панель оператора: список чатов + очередь
□ Панель оператора: мульти-чат (переключение)
□ Панель оператора: быстрые ответы
□ Панель оператора: информация о пользователе
□ Панель оператора: действия (передать, эскалировать)
□ Панель оператора: тикеты в работе
□ Смена статуса оператора
□ HTMX + WebSocket
□ Мобильная адаптация
```

---

## ШАГ 9.6 — SLA, АНАЛИТИКА, CELERY ЗАДАЧИ

### Задача

```
SLA мониторинг и нарушения.
Аналитика поддержки для админа.
Все Celery задачи. Автозакрытие тикетов.
```

### SLA Service

```
SLAService:

  check_sla_violations():
    """
    Celery задача (каждые 5 минут).
    Проверяет нарушения SLA.
    """

    # 1. Нет первого ответа
    open_tickets = Ticket.objects.filter(
      status__in=['new', 'open', 'in_progress'],
      first_response_at__isnull=True,
    )

    for ticket in open_tickets:
      sla = SLAConfig.objects.get(priority=ticket.priority)
      deadline = ticket.created_at + timedelta(
        minutes=sla.first_response_minutes
      )

      if now() > deadline:
        if not ticket.is_escalated:
          # SLA нарушен → эскалировать
          TicketService.escalate_ticket(
            ticket=ticket,
            escalated_by=None,  # система
            reason=f'SLA первого ответа нарушен '
                   f'({sla.first_response_minutes} мин)',
          )

          # Уведомить всех операторов
          notify_all_operators_sla_breach(ticket)

    # 2. Нет решения
    in_progress = Ticket.objects.filter(
      status__in=['in_progress', 'waiting_user', 'waiting_admin'],
      resolved_at__isnull=True,
    )

    for ticket in in_progress:
      sla = SLAConfig.objects.get(priority=ticket.priority)
      deadline = ticket.created_at + timedelta(
        minutes=sla.resolution_minutes
      )

      if now() > deadline and not ticket.is_escalated:
        TicketService.escalate_ticket(
          ticket=ticket,
          escalated_by=None,
          reason=f'SLA решения нарушен '
                 f'({sla.resolution_minutes} мин)',
        )
```

### Автозакрытие тикетов

```
auto_close_resolved_tickets():
  """
  Celery задача (ежедневно).
  Закрыть тикеты со статусом 'resolved'
  если пользователь не ответил 3 дня.
  """

  tickets = Ticket.objects.filter(
    status='resolved',
    resolved_at__lt=now() - timedelta(days=3),
  )

  for ticket in tickets:
    TicketService.change_status(
      ticket, 'closed', changed_by=None,
      reason='Автозакрытие: нет ответа 3 дня',
    )

auto_close_idle_chats():
  """
  Celery задача (каждые 5 минут).
  Закрыть чаты без активности > 30 минут.
  """

  idle_sessions = ChatSession.objects.filter(
    chat_status='active',
    # Нет сообщений > 30 мин
  )

  for session in idle_sessions:
    last_message = Message.objects.filter(
      ticket=session.ticket,
    ).order_by('-created_at').first()

    if last_message and (now() - last_message.created_at).total_seconds() > 1800:
      session.chat_status = 'ended'
      session.ended_at = now()
      session.ended_by = 'timeout'
      session.save()

      # Системное сообщение
      Message.objects.create(
        ticket=session.ticket,
        sender=None,
        sender_type='system',
        text='Чат завершён из-за неактивности (30 минут).',
        is_system_message=True,
      )

      # Освободить оператора
      if session.operator:
        session.operator.operator_profile.release_chat()
```

### Аналитика поддержки

```
URL: /admin/support/analytics/
Доступ: @staff_required + manager

  ┌──────────────────────────────────────────────────────────────┐
  │  📊 Аналитика поддержки                                    │
  │                                                              │
  │  Период: [Сегодня|Неделя|Месяц|Кастом]                      │
  │                                                              │
  │  ── Общие показатели ──────────────────────────────────────  │
  │                                                              │
  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐   │
  │  │  234   │ │  89%   │ │ 12 мин │ │  4.5h  │ │ ⭐ 4.3 │   │
  │  │ Тикетов│ │ Решено │ │ 1й отв.│ │ Решение│ │ Оценка │   │
  │  └────────┘ └────────┘ └────────┘ └────────┘ └────────┘   │
  │                                                              │
  │  ── SLA ───────────────────────────────────────────────────  │
  │  Первый ответ в SLA: 94%                                    │
  │  Решение в SLA: 87%                                          │
  │  Нарушений SLA: 12                                           │
  │                                                              │
  │  ── По категориям ─────────────────────────────────────────  │
  │  💰 Финансы:      78 тикетов │ avg 3.2h │ ⭐ 4.5           │
  │  👤 Аккаунт:      45 тикетов │ avg 2.1h │ ⭐ 4.4           │
  │  🎰 Казино:       34 тикета  │ avg 1.5h │ ⭐ 4.2           │
  │  ...                                                         │
  │                                                              │
  │  ── По операторам ─────────────────────────────────────────  │
  │  Алексей:  89 тикетов │ avg 8 мин 1й │ ⭐ 4.7             │
  │  Мария:    67 тикетов │ avg 12 мин 1й │ ⭐ 4.5             │
  │  Дмитрий:  45 тикетов │ avg 15 мин 1й │ ⭐ 4.2             │
  │                                                              │
  │  ── Живой чат ─────────────────────────────────────────────  │
  │  Чатов сегодня: 56                                           │
  │  Среднее время ожидания: 2.3 мин                            │
  │  Среднее время чата: 8.5 мин                                │
  │  Отказы (ушли из очереди): 5 (8.9%)                         │
  │                                                              │
  │  ── Удовлетворённость ─────────────────────────────────────  │
  │  ⭐⭐⭐⭐⭐ — 45%                                           │
  │  ⭐⭐⭐⭐ — 30%                                              │
  │  ⭐⭐⭐ — 15%                                                │
  │  ⭐⭐ — 7%                                                   │
  │  ⭐ — 3%                                                     │
  │                                                              │
  │  ── FAQ эффективность ─────────────────────────────────────  │
  │  Просмотров FAQ: 1,234                                       │
  │  "Было полезно": 78%                                         │
  │  Тикетов после FAQ: 12% (отклонённых FAQ)                   │
  │                                                              │
  │  [📥 Экспорт отчёта]                                        │
  │                                                              │
  └──────────────────────────────────────────────────────────────┘
```

### Все Celery задачи

```
# apps/support/tasks.py

# ── КАЖДЫЕ 10 СЕКУНД ─────────────────────────
process_chat_queue():
  """Обработка очереди живого чата."""
  ChatService.process_queue()

# ── КАЖДЫЕ 5 МИНУТ ───────────────────────────
check_sla_violations():
  """Проверка нарушений SLA."""
  SLAService.check_sla_violations()

auto_close_idle_chats():
  """Закрыть неактивные чаты (30 мин)."""

update_operator_stats():
  """Обновить статистику операторов."""

# ── ЕЖЕДНЕВНО ────────────────────────────────
auto_close_resolved_tickets():
  """Закрыть resolved тикеты без ответа 3 дня."""

update_faq_stats():
  """Обновить статистику FAQ (views, helpful)."""

cleanup_old_attachments():
  """Удалить вложения из закрытых тикетов > 90 дней."""

generate_support_daily_report():
  """Генерация ежедневного отчёта для админа."""

# ── ПРИ СОБЫТИЯХ ─────────────────────────────
send_ticket_notification(ticket_id, notification_type):
  """Уведомление о тикете (email + telegram)."""

send_chat_offline_message(session_id):
  """Если чат завершён а пользователь оффлайн → email."""


# ── CELERY BEAT ──────────────────────────────
CELERY_BEAT_SCHEDULE += {
  'process-chat-queue': {
    'task': 'apps.support.tasks.process_chat_queue',
    'schedule': 10.0,  # каждые 10 секунд
  },
  'check-sla': {
    'task': 'apps.support.tasks.check_sla_violations',
    'schedule': crontab(minute='*/5'),
  },
  'auto-close-idle-chats': {
    'task': 'apps.support.tasks.auto_close_idle_chats',
    'schedule': crontab(minute='*/5'),
  },
  'auto-close-resolved': {
    'task': 'apps.support.tasks.auto_close_resolved_tickets',
    'schedule': crontab(hour=3, minute=0),
  },
  'support-daily-report': {
    'task': 'apps.support.tasks.generate_support_daily_report',
    'schedule': crontab(hour=7, minute=0),
  },
}
```

### Критерий готовности шага 9.6

```
□ SLA мониторинг: проверка каждые 5 минут
□ Автоэскалация при нарушении SLA
□ Уведомление операторам при нарушении SLA
□ Автозакрытие resolved тикетов (3 дня)
□ Автозакрытие idle чатов (30 минут)
□ Аналитика: общие показатели
□ Аналитика: по категориям
□ Аналитика: по операторам
□ Аналитика: SLA процент
□ Аналитика: живой чат (ожидание, отказы)
□ Аналитика: удовлетворённость (оценки)
□ Аналитика: FAQ эффективность
□ Экспорт отчёта
□ Ежедневный отчёт для админа (Celery)
□ Cleanup вложений (90 дней)
□ Все Celery задачи в Beat
```

---

## 📊 ОБЩИЙ ЧЕКЛИСТ ЭТАПА 9

```
МОДЕЛИ:
  □ Ticket (все поля + генерация номера)
  □ Message + MessageAttachment
  □ ChatSession
  □ FAQCategory + FAQArticle (fixtures)
  □ QuickReply (fixtures)
  □ SLAConfig (fixtures)
  □ OperatorProfile
  □ AutoResponse

ТИКЕТ-СИСТЕМА:
  □ Создание тикета (форма + валидация)
  □ Автоопределение приоритета
  □ Автоответ по ключевым словам
  □ Предложение FAQ (HTMX)
  □ Вложения (загрузка + валидация)
  □ Автоназначение оператору
  □ Ответы (user + operator)
  □ Внутренние заметки (только операторы)
  □ Смена статуса
  □ Эскалация
  □ Передача другому оператору
  □ Оценка (1-5 звёзд)
  □ Системные сообщения

ЖИВОЙ ЧАТ:
  □ Django Channels + Redis
  □ WebSocket Consumer
  □ Отправка/получение в реальном времени
  □ История сообщений
  □ Typing индикатор
  □ Read receipts
  □ Очередь ожидания
  □ Автоназначение оператора
  □ Завершение чата
  □ Автозакрытие по таймауту
  □ Rate limiting
  □ Переподключение

TELEGRAM БОТ:
  □ Бот создан и работает
  □ /start, /link, /unlink
  □ /balance, /bets, /support
  □ /settings, /help, /referral
  □ Привязка аккаунта (код)
  □ Все типы уведомлений
  □ Inline кнопки
  □ Retry при ошибках

FAQ:
  □ Категории + статьи
  □ Поиск по базе знаний
  □ "Это было полезно?" (да/нет)
  □ Популярные вопросы

ФРОНТЕНД:
  □ Центр помощи
  □ FAQ (категории + статьи)
  □ Создание тикета
  □ Мои тикеты (список + детальная)
  □ Виджет чата (плавающая кнопка)
  □ Мобильный чат (fullscreen)
  □ Панель оператора (дашборд)
  □ Панель оператора (мульти-чат)
  □ Быстрые ответы

SLA + АНАЛИТИКА:
  □ SLA мониторинг (каждые 5 мин)
  □ Автоэскалация
  □ Аналитика (все метрики)
  □ Экспорт отчётов

CELERY:
  □ Очередь чата (каждые 10 сек)
  □ SLA проверка (каждые 5 мин)
  □ Автозакрытие чатов (5 мин)
  □ Автозакрытие тикетов (ежедневно)
  □ Ежедневный отчёт
  □ Cleanup вложений
  □ Telegram уведомления

ИНТЕРФЕЙС:
  □ Тёмная тема DOD
  □ HTMX + WebSocket
  □ Мобильная адаптация
  □ Звуки уведомлений в чате
```

---

```
╔══════════════════════════════════════════════════════╗
║                                                      ║
║   ЭТАП 9 ЗАВЕРШЁН                                   ║
║                                                      ║
║   Следующий: ЭТАП 10                                ║
║   Админ-панель (полная)                             ║
║                                                      ║
║   Продолжить?                                       ║
║                                                      ║
╚══════════════════════════════════════════════════════╝
```