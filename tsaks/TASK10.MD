

# 📋 ТЗ ПРОЕКТА DOD — ЭТАП 10

# АДМИН-ПАНЕЛЬ (ПОЛНАЯ)

```
╔══════════════════════════════════════════════════════╗
║                                                      ║
║   ПРОЕКТ:    DOD                                    ║
║   ЭТАП:      10 из 12                               ║
║   НАЗВАНИЕ:  Админ-панель                           ║
║   ЗАВИСИТ:   Этапы 1-9 (полностью завершены)        ║
║   ЦЕЛЬ:      Единая панель управления всей          ║
║              платформой: пользователи, финансы,      ║
║              контент, спорт, казино, predictions,    ║
║              поддержка, аналитика, настройки,        ║
║              роли и права, логи, отчёты              ║
║                                                      ║
╚══════════════════════════════════════════════════════╝
```

---

## 📌 КОНТЕКСТ ДЛЯ ИИ-АГЕНТА

```
Этапы 1-9 выполнены. У тебя есть:
  - Всё: авторизация, профиль, KYC, кошелёк, платежи,
    спорт, казино, predictions, партнёрка, поддержка,
    уведомления, Telegram бот
  - Базовые админ-интерфейсы в каждом приложении
    (Django Admin + кастомные страницы модерации KYC,
    маркетов, выплат)

В этом этапе ты строишь ЕДИНУЮ кастомную
админ-панель которая заменяет Django Admin.
Отдельное SPA-подобное приложение с навигацией,
дашбордом, глубоким управлением каждым модулем.

Админ-панель — это отдельное Django app (apps/dashboard)
с собственными шаблонами, URL namespace, middleware.
НЕ использует стандартный Django Admin
(он остаётся как fallback для суперадмина).

Этот этап включает 6 шагов.
Каждый шаг — отдельная задача.
Выполняй строго по порядку.
```

---

## ШАГ 10.1 — ПРИЛОЖЕНИЕ, РОЛИ, ПРАВА

### Задача

```
Создай приложение dashboard с системой ролей
и гранулярных прав доступа. Middleware проверки.
Логирование действий. Базовый layout.
```

### Структура приложения

```
apps/dashboard/
├── __init__.py
├── models.py
├── admin.py
├── views/
│   ├── __init__.py
│   ├── main.py              # Дашборд, навигация
│   ├── users.py             # Управление пользователями
│   ├── finance.py           # Финансы, транзакции, выводы
│   ├── sports.py            # Спорт, матчи, ставки
│   ├── casino.py            # Казино, игры, раунды
│   ├── predictions.py       # Маркеты, резолюция
│   ├── referral.py          # Партнёрская программа
│   ├── support.py           # Поддержка, тикеты
│   ├── content.py           # Контент, баннеры, промо
│   ├── analytics.py         # Аналитика, отчёты
│   ├── settings.py          # Настройки платформы
│   └── logs.py              # Логи, аудит
├── urls.py
├── forms.py
├── middleware.py
├── decorators.py
├── mixins.py
├── services/
│   ├── __init__.py
│   ├── analytics_service.py
│   ├── report_service.py
│   └── audit_service.py
├── templatetags/
│   ├── __init__.py
│   └── dashboard_tags.py
├── templates/
│   └── dashboard/
│       ├── base.html          # Базовый шаблон админки
│       ├── sidebar.html
│       ├── navbar.html
│       ├── main/
│       ├── users/
│       ├── finance/
│       ├── sports/
│       ├── casino/
│       ├── predictions/
│       ├── referral/
│       ├── support/
│       ├── content/
│       ├── analytics/
│       ├── settings/
│       └── logs/
├── tests/
│   ├── __init__.py
│   ├── test_permissions.py
│   ├── test_views.py
│   └── test_analytics.py
└── migrations/
    └── __init__.py
```

### Модель AdminRole (Роли)

```
class AdminRole(models.Model):

    Назначение:
      Роли администраторов.
      Каждая роль имеет набор прав.
      Пользователю назначается одна роль.

    Поля:
    ─────
    id:
      тип: AutoField, primary key

    name:
      тип: CharField, max 50, уникальный
      Название роли
      Пример: "Суперадмин", "Админ", "Модератор",
      "Финансовый менеджер", "Оператор поддержки"

    slug:
      тип: SlugField, уникальный

    description:
      тип: TextField, blank=True
      Описание обязанностей роли

    # Права (гранулярные)
    permissions:
      тип: JSONField, default=dict
      Структура:
      {
        "dashboard": {
          "view": true
        },
        "users": {
          "view": true,
          "edit": true,
          "ban": true,
          "delete": false,
          "change_balance": false,
          "reset_2fa": true,
          "change_trust_level": true,
          "view_sensitive_data": false
        },
        "finance": {
          "view_transactions": true,
          "approve_withdrawals": true,
          "approve_withdrawals_limit": 1000,
          "reject_withdrawals": true,
          "manual_deposit": false,
          "adjust_balance": false,
          "view_reports": true,
          "export_data": false
        },
        "kyc": {
          "view": true,
          "review": true,
          "approve": true,
          "reject": true
        },
        "sports": {
          "view": true,
          "create_events": true,
          "edit_events": true,
          "manage_odds": true,
          "settle_bets": true,
          "void_bets": false
        },
        "casino": {
          "view": true,
          "manage_games": false,
          "view_rounds": true,
          "adjust_rtp": false
        },
        "predictions": {
          "view": true,
          "create_markets": true,
          "edit_markets": true,
          "resolve_markets": true,
          "cancel_markets": false
        },
        "referral": {
          "view": true,
          "manage_partners": true,
          "approve_payouts": true,
          "change_tiers": false,
          "block_partners": true
        },
        "support": {
          "view_tickets": true,
          "handle_tickets": true,
          "handle_chats": true,
          "escalate": true,
          "view_all_tickets": false,
          "manage_faq": true,
          "manage_quick_replies": true
        },
        "content": {
          "manage_banners": true,
          "manage_promotions": true,
          "manage_pages": true,
          "send_notifications": false
        },
        "analytics": {
          "view_dashboard": true,
          "view_reports": true,
          "export_reports": false,
          "view_financial_reports": false
        },
        "settings": {
          "view": false,
          "edit_general": false,
          "edit_limits": false,
          "edit_payment_methods": false,
          "manage_roles": false,
          "manage_admins": false
        },
        "logs": {
          "view_admin_logs": true,
          "view_user_logs": true,
          "view_system_logs": false
        }
      }

    # Иерархия
    level:
      тип: IntegerField, default=0
      Чем выше → больше полномочий
      0 = оператор, 10 = модератор, 50 = админ,
      100 = суперадмин

    is_system:
      тип: BooleanField, default=False
      True = системная роль (нельзя удалить)
      Суперадмин — системная

    is_active:
      тип: BooleanField, default=True

    created_at:
      тип: DateTimeField, auto_now_add=True

    Meta:
      verbose_name = 'Роль администратора'
      verbose_name_plural = 'Роли администраторов'
      ordering = ['-level']

    Предзаполнение (fixtures):

      1. 💎 Суперадмин (superadmin, level=100, is_system=True)
         Все права = true, без ограничений

      2. 🔷 Админ (admin, level=50)
         Всё кроме: manage_roles, manage_admins,
         delete users, adjust_balance, view_sensitive_data

      3. 🔶 Модератор (moderator, level=10)
         KYC, predictions, support, content, referral
         Без: finance, sports odds, casino RTP, settings

      4. 💰 Финансовый менеджер (finance_manager, level=20)
         finance (всё), KYC, users (view),
         withdrawals, reports

      5. ⚽ Спорт-менеджер (sports_manager, level=15)
         sports (всё), users (view), bets

      6. 🎧 Оператор поддержки (support_operator, level=5)
         support (handle_tickets, handle_chats),
         users (view basic), FAQ
```

### Модель AdminProfile (Профиль администратора)

```
class AdminProfile(models.Model):

    Назначение:
      Расширение User для администраторов.
      Связь с ролью. Дополнительные настройки.

    Поля:
    ─────
    user:
      тип: OneToOneField → User
      on_delete: CASCADE
      related_name: 'admin_profile'

    role:
      тип: ForeignKey → AdminRole
      on_delete: PROTECT

    # Кастомные права (переопределяют роль)
    custom_permissions:
      тип: JSONField, default=dict
      Индивидуальные переопределения.
      Если указано — перекрывает значение из роли.
      Пример: {"finance": {"approve_withdrawals_limit": 5000}}

    # Настройки
    receive_admin_notifications:
      тип: BooleanField, default=True

    notification_channels:
      тип: JSONField, default=dict
      {
        "email": true,
        "telegram": true,
        "dashboard": true
      }

    # Рабочие часы (для авторасписания)
    work_schedule:
      тип: JSONField, default=dict
      {
        "mon": {"start": "09:00", "end": "18:00"},
        "tue": {"start": "09:00", "end": "18:00"},
        ...
        "sat": null,
        "sun": null
      }

    # Статистика
    total_actions:
      тип: IntegerField, default=0
      Общее количество действий

    last_action_at:
      тип: DateTimeField, nullable

    # IP whitelist (опционально)
    ip_whitelist:
      тип: JSONField, default=list
      Список разрешённых IP
      Пустой = без ограничений

    # Активность
    is_admin_active:
      тип: BooleanField, default=True
      Активен как администратор

    deactivated_at:
      тип: DateTimeField, nullable

    deactivated_reason:
      тип: TextField, blank=True

    created_at:
      тип: DateTimeField, auto_now_add=True

    Meta:
      verbose_name = 'Профиль администратора'

    Методы:

      has_permission(module, action):
        """Проверка права."""
        # Суперадмин — всё можно
        if self.role.slug == 'superadmin':
          return True

        # Проверить кастомные права
        if module in self.custom_permissions:
          custom = self.custom_permissions[module]
          if action in custom:
            return custom[action]

        # Проверить права роли
        role_perms = self.role.permissions
        if module in role_perms:
          return role_perms[module].get(action, False)

        return False

      get_permission_value(module, action):
        """Получить значение права (может быть число)."""
        # Для approve_withdrawals_limit и подобных
        if module in self.custom_permissions:
          custom = self.custom_permissions[module]
          if action in custom:
            return custom[action]

        role_perms = self.role.permissions
        if module in role_perms:
          return role_perms[module].get(action)

        return None
```

### Расширение AdminActionLog

```
Модель AdminActionLog уже есть (из этапа 2).
Расширить поля:

    # Добавить
    module:
      тип: CharField, max 50
      Модуль: 'users', 'finance', 'sports', 'casino',
      'predictions', 'referral', 'support', 'settings'

    action_category:
      тип: CharField, max 50
      Более точная категория внутри модуля

    # Данные до и после (для аудита)
    data_before:
      тип: JSONField, nullable
      Состояние объекта ДО действия

    data_after:
      тип: JSONField, nullable
      Состояние объекта ПОСЛЕ действия

    # Результат
    is_successful:
      тип: BooleanField, default=True

    error_message:
      тип: TextField, blank=True

    # Время выполнения
    duration_ms:
      тип: IntegerField, default=0
      Сколько времени заняло действие (мс)
```

### Middleware

```
# apps/dashboard/middleware.py

class AdminAccessMiddleware:
    """
    Middleware для admin-панели.
    Проверяет:
      1. Пользователь авторизован
      2. Пользователь is_staff
      3. У пользователя есть AdminProfile
      4. AdminProfile активен
      5. IP в whitelist (если задан)
      6. 2FA пройдена (для admin обязательна)
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Только для URL /admin-panel/
        if not request.path.startswith('/admin-panel/'):
            return self.get_response(request)

        # 1. Авторизация
        if not request.user.is_authenticated:
            return redirect('accounts:login')

        # 2. Staff
        if not request.user.is_staff:
            return HttpResponseForbidden('Доступ запрещён')

        # 3. AdminProfile
        try:
            admin_profile = request.user.admin_profile
        except AdminProfile.DoesNotExist:
            return HttpResponseForbidden(
                'Профиль администратора не настроен'
            )

        # 4. Активен
        if not admin_profile.is_admin_active:
            return HttpResponseForbidden(
                'Доступ администратора деактивирован'
            )

        # 5. IP whitelist
        if admin_profile.ip_whitelist:
            ip = get_client_ip(request)
            if ip not in admin_profile.ip_whitelist:
                # Логировать попытку
                AdminActionLog.objects.create(
                    admin_user=request.user,
                    action_type='unauthorized_access',
                    module='security',
                    description=f'Попытка входа с IP {ip} '
                                f'(не в whitelist)',
                    ip_address=ip,
                    is_successful=False,
                )
                return HttpResponseForbidden(
                    'Доступ с данного IP запрещён'
                )

        # 6. 2FA (для админки всегда)
        if request.user.is_2fa_enabled:
            if not request.session.get('admin_2fa_verified'):
                return redirect('dashboard:verify-2fa')

        # Прикрепить профиль к request
        request.admin_profile = admin_profile

        return self.get_response(request)


class AdminActionLogMiddleware:
    """
    Логирование ВСЕХ POST/PUT/DELETE запросов
    в админ-панели.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.path.startswith('/admin-panel/'):
            return self.get_response(request)

        if request.method in ('POST', 'PUT', 'DELETE', 'PATCH'):
            start_time = time.time()
            response = self.get_response(request)
            duration = int((time.time() - start_time) * 1000)

            # Логировать
            AdminActionLog.objects.create(
                admin_user=request.user,
                action_type=f'{request.method} {request.path}',
                module=extract_module(request.path),
                ip_address=get_client_ip(request),
                duration_ms=duration,
                is_successful=(200 <= response.status_code < 400),
            )

            return response

        return self.get_response(request)
```

### Декораторы прав

```
# apps/dashboard/decorators.py

def require_permission(module, action):
    """
    Декоратор проверки права.
    
    Использование:
    @require_permission('users', 'edit')
    def edit_user_view(request, user_id):
        ...
    """
    def decorator(view_func):
        @functools.wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not hasattr(request, 'admin_profile'):
                return HttpResponseForbidden('Нет профиля')

            if not request.admin_profile.has_permission(module, action):
                AdminActionLog.objects.create(
                    admin_user=request.user,
                    action_type='permission_denied',
                    module=module,
                    description=f'Отказано: {module}.{action}',
                    ip_address=get_client_ip(request),
                    is_successful=False,
                )
                return HttpResponseForbidden(
                    f'Недостаточно прав: {module}.{action}'
                )

            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_role_level(min_level):
    """
    Декоратор минимального уровня роли.
    
    Использование:
    @require_role_level(50)  # Только админ+
    def dangerous_action(request):
        ...
    """
    def decorator(view_func):
        @functools.wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not hasattr(request, 'admin_profile'):
                return HttpResponseForbidden()

            if request.admin_profile.role.level < min_level:
                return HttpResponseForbidden(
                    'Недостаточный уровень доступа'
                )

            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
```

### Базовый layout админки

```
# templates/dashboard/base.html

Структура:

  ┌──────────────────────────────────────────────────────────────┐
  │  NAVBAR (top)                                                │
  │  DOD Admin │ 🔍 Поиск │ 🔔(3) │ 👤 Admin Name (role) │ ⚙️ │
  ├──────────┬───────────────────────────────────────────────────┤
  │          │                                                   │
  │ SIDEBAR  │  CONTENT AREA                                     │
  │          │                                                   │
  │ 📊 Дашб. │  {% block content %}{% endblock %}               │
  │ 👥 Польз.│                                                   │
  │ 💰 Финан.│                                                   │
  │ ⚽ Спорт │                                                   │
  │ 🎰 Казино│                                                   │
  │ 📊 Predic│                                                   │
  │ 🤝 Партн.│                                                   │
  │ 🎧 Подд. │                                                   │
  │ 📄 Конт. │                                                   │
  │ 📈 Анал. │                                                   │
  │ ⚙️ Наст. │                                                   │
  │ 📋 Логи  │                                                   │
  │          │                                                   │
  └──────────┴───────────────────────────────────────────────────┘

Sidebar:
  Каждый пункт показывается ТОЛЬКО если у роли есть
  право view на этот модуль.
  
  {% if admin_profile.has_permission('users', 'view') %}
    <a href="{% url 'dashboard:users' %}">👥 Пользователи</a>
  {% endif %}

  Активный пункт подсвечивается.
  Подменю раскрываются при клике.
  На мобильных — бургер.

Цветовая схема:
  Такая же как основной сайт (тёмная тема DOD).
  Но sidebar чуть темнее.
  Акцентный цвет для admin — синий (отличать от пользовательской).

Navbar:
  Поиск: глобальный поиск (пользователи, тикеты, транзакции)
  Уведомления: админские уведомления (новые KYC, SLA, фрод)
  Профиль: имя + роль + выпадающее меню
```

### Критерий готовности шага 10.1

```
□ Приложение dashboard создано
□ Модель AdminRole: все поля + fixtures (6 ролей)
□ Модель AdminProfile: связь с ролью + права
□ AdminActionLog расширен (module, data_before/after)
□ AdminAccessMiddleware: все проверки
□ AdminActionLogMiddleware: логирование POST/PUT/DELETE
□ Декоратор require_permission работает
□ Декоратор require_role_level работает
□ Базовый layout: sidebar + navbar + content
□ Sidebar показывает только доступные пункты
□ Глобальный поиск (заглушка)
□ 2FA обязательна для входа в админку
□ IP whitelist работает
□ URL namespace: /admin-panel/
```

---

## ШАГ 10.2 — ДАШБОРД + УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ

### Задача

```
Главный дашборд с метриками в реальном времени.
Полное управление пользователями: просмотр,
редактирование, блокировка, баланс, история.
```

### Главный дашборд

```
URL: /admin-panel/
Доступ: @require_permission('dashboard', 'view')

  ┌──────────────────────────────────────────────────────────────┐
  │  📊 Дашборд DOD                     Обновлено: только что  │
  │                                                              │
  │  ── Сейчас ────────────────────────────────────────────────  │
  │                                                              │
  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
  │  │ 🟢 1,234 │ │ 💰 $45.6k│ │ 📈 $12.3k│ │ 🎧 5     │       │
  │  │ Онлайн   │ │ Депозиты │ │ GGR      │ │ Тикетов  │       │
  │  │ сейчас   │ │ сегодня  │ │ сегодня  │ │ открытых │       │
  │  │ ↑12%     │ │ ↑23%     │ │ ↑8%      │ │ ↓3       │       │
  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
  │                                                              │
  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
  │  │ 👥 89    │ │ 💸 $23.4k│ │ 🎰 $8.9k │ │ ⚠️ 3     │       │
  │  │ Новых    │ │ Выводы   │ │ Казино   │ │ Подозрит.│       │
  │  │ регистр. │ │ ожидают  │ │ GGR      │ │ выводы   │       │
  │  │ сегодня  │ │          │ │ сегодня  │ │          │       │
  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
  │                                                              │
  │  HTMX: hx-get="/api/admin/stats/" hx-trigger="every 30s"   │
  │                                                              │
  │  ── Графики ───────────────────────────────────────────────  │
  │                                                              │
  │  ┌───────────────────────────┐ ┌──────────────────────────┐ │
  │  │ 💰 Доходы vs Расходы     │ │ 👥 Регистрации           │ │
  │  │ (линейный, 7 дней)       │ │ (столбчатый, 7 дней)     │ │
  │  │                           │ │                          │ │
  │  │ ╱──╲    ╱──               │ │ ██                       │ │
  │  │╱    ╲──╱                  │ │ ██ ██                    │ │
  │  │                           │ │ ██ ██ ██    ██           │ │
  │  │ ── GGR  ── Выплаты       │ │ ██ ██ ██ ██ ██ ██ ██    │ │
  │  └───────────────────────────┘ └──────────────────────────┘ │
  │                                                              │
  │  ── Требуют внимания ──────────────────────────────────────  │
  │                                                              │
  │  🔴 3 вывода ожидают одобрения > 12 часов                   │
  │  🟡 5 KYC заявок ожидают > 24 часов                         │
  │  🟡 2 тикета с нарушенным SLA                               │
  │  🔴 1 подозрительный партнёр на проверке                    │
  │  🟡 3 маркета ожидают резолюции > 48 часов                  │
  │                                                              │
  │  ── Последние действия админов ─────────────────────────── │
  │                                                              │
  │  👤 Алексей одобрил вывод $500 (user456) • 5 мин назад     │
  │  👤 Мария одобрила KYC (player789) • 12 мин назад          │
  │  👤 Дмитрий резолвил маркет "BTC>100k" • 1 час назад       │
  │  👤 Система: SLA нарушен тикет #0042 • 2 часа назад        │
  │                                                              │
  │  ── Финансовая сводка (сегодня) ────────────────────────── │
  │                                                              │
  │  ┌──────────────────────────────────────────────────────┐   │
  │  │ Депозиты:     $45,678   │ Выводы:     $23,456      │   │
  │  │ GGR Спорт:    $12,345   │ GGR Казино:  $8,901      │   │
  │  │ GGR Predict:   $2,345   │ Комиссии:    $1,234      │   │
  │  │ ──────────────────────────────────────────────────  │   │
  │  │ NGR (чистый доход):  $22,345                        │   │
  │  │ Партнёрские выплаты: -$3,456                        │   │
  │  │ Бонусы:              -$1,234                        │   │
  │  │ ──────────────────────────────────────────────────  │   │
  │  │ Итого прибыль:       $17,655  📈 +12% vs вчера     │   │
  │  └──────────────────────────────────────────────────────┘   │
  │                                                              │
  └──────────────────────────────────────────────────────────────┘

Все метрики обновляются через HTMX каждые 30 секунд.
Графики — Chart.js или Lightweight Charts.
Данные кешируются в Redis на 30 секунд.
```

### Управление пользователями

```
URL: /admin-panel/users/
Доступ: @require_permission('users', 'view')

  ┌──────────────────────────────────────────────────────────────┐
  │  👥 Пользователи                     Всего: 12,345         │
  │                                                              │
  │  Поиск: [email / username / ID / телефон ________] 🔍       │
  │                                                              │
  │  Фильтры:                                                   │
  │  Статус: [Все|Активные|Заблокированные|Деактивированные]    │
  │  KYC: [Все|Без KYC|На проверке|Одобрена|Отклонена]         │
  │  Trust: [Все|1|2|3|4|5]                                     │
  │  Регистрация: [Все|Email|Google|Telegram|Телефон]           │
  │  Период: [Сегодня|Неделя|Месяц|Всё|Кастом]                 │
  │  2FA: [Все|Включена|Выключена]                              │
  │  Баланс: [Все|> $100|> $1000|> $10000]                     │
  │  Сортировка: [Дата↓|Баланс↓|Ставки↓|Депозит↓]             │
  │                                                              │
  │  [📥 Экспорт CSV] [📥 Экспорт Excel]                       │
  │                                                              │
  │  ┌──────────────────────────────────────────────────────┐   │
  │  │ ☐ │ 👤 │ Email            │ Username │ Баланс      │   │
  │  │   │    │                  │          │             │   │
  │  │ ☐ │ 🟢 │ user@mail.com   │ user456  │ $1,234.56  │   │
  │  │   │    │ 🇷🇺 │ Trust: 3  │ KYC: ✅  │ Спорт+Каз  │   │
  │  │   │    │ Рег: 10.03.2025 │ Online   │ Деп: $5k   │   │
  │  │                                                      │   │
  │  │ ☐ │ 🔴 │ bad@mail.com    │ cheater1 │ $0.00      │   │
  │  │   │    │ 🇺🇦 │ Trust: 1  │ KYC: ❌  │ Забанен    │   │
  │  │   │    │ Рег: 01.03.2025 │ Offline  │ Деп: $50   │   │
  │  └──────────────────────────────────────────────────────┘   │
  │                                                              │
  │  Массовые действия (выбранные):                             │
  │  [Заблокировать] [Разблокировать] [Изменить Trust Level]    │
  │  [Сбросить 2FA] [Отправить уведомление]                     │
  │                                                              │
  │  [1] [2] [3] ... [247]  (пагинация, 50 на страницу)        │
  │                                                              │
  └──────────────────────────────────────────────────────────────┘
```

### Детальная карточка пользователя

```
URL: /admin-panel/users/{user_id}/
Доступ: @require_permission('users', 'view')

  ┌──────────────────────────────────────────────────────────────┐
  │  👤 Пользователь: user456                                   │
  │                                                              │
  │  ┌────────┐  email: user@example.com ✅                     │
  │  │ AVATAR │  телефон: +7 (999) 123-45-67 ✅                 │
  │  │        │  Иван Петров │ 🇷🇺 Россия                       │
  │  └────────┘  Рег: 10.03.2025 через Email                    │
  │              IP рег: 95.161.xx.xx (Москва)                   │
  │              Trust: 🟡 Проверенный (3)                       │
  │              KYC: ✅ Одобрена (16.03.2025)                   │
  │              2FA: ✅ TOTP                                     │
  │              Реферер: partner_pro (DOD-X7K9M2)               │
  │              Последний вход: 2 часа назад                    │
  │              Статус: 🟢 Онлайн                               │
  │                                                              │
  │  ── Вкладки ───────────────────────────────────────────────  │
  │  [Обзор|Финансы|Ставки|Казино|Predictions|Безопасность|     │
  │   Поддержка|Партнёрка|Логи]                                 │
  │                                                              │
  │  ── ВКЛАДКА: Обзор ────────────────────────────────────────  │
  │                                                              │
  │  💰 Баланс: $1,234.56                                       │
  │  📊 Всего депозитов: $5,000                                  │
  │  📤 Всего выводов: $3,200                                    │
  │  🎮 Всего ставок: 342                                        │
  │  🏆 Выигрышей: 168 (49.1%)                                   │
  │  📈 GGR (для платформы): $1,800                              │
  │                                                              │
  │  ── Действия администратора ────────────────────────────── │
  │                                                              │
  │  [✏️ Редактировать профиль]                                  │
  │    (имя, email, телефон, страна, язык)                       │
  │                                                              │
  │  [💰 Корректировка баланса]                                  │
  │    (require_permission: 'finance', 'adjust_balance')         │
  │    Сумма: [____] Причина: [________________]                │
  │    [Начислить] [Списать]                                     │
  │                                                              │
  │  [🔒 Заблокировать]                                          │
  │    Причина: [________________]                               │
  │    Срок: [Навсегда|1 день|7 дней|30 дней]                   │
  │    [Заблокировать]                                           │
  │                                                              │
  │  [🔓 Разблокировать] (если заблокирован)                     │
  │                                                              │
  │  [🔄 Сбросить 2FA]                                           │
  │    ⚠️ Пользователь потеряет доступ к 2FA                    │
  │    [Подтвердить сброс]                                       │
  │                                                              │
  │  [📊 Изменить Trust Level]                                   │
  │    Текущий: 3 → Новый: [▼]                                  │
  │    Причина: [________________]                               │
  │    [Применить]                                               │
  │                                                              │
  │  [📧 Отправить уведомление]                                  │
  │    Тема: [________________]                                  │
  │    Текст: [________________]                                 │
  │    Каналы: ☑ Сайт ☑ Email ☐ Telegram                        │
  │    [Отправить]                                               │
  │                                                              │
  │  [🔑 Войти как пользователь]                                 │
  │    (require_role_level: 100, только суперадмин)              │
  │    Открывает сайт от лица пользователя                       │
  │    Все действия логируются                                   │
  │                                                              │
  │  ── ВКЛАДКА: Финансы ──────────────────────────────────────  │
  │                                                              │
  │  Баланс по валютам:                                          │
  │  USD: $1,234.56 │ EUR: €0.00 │ BTC: 0.00000000             │
  │  RUB: ₽0.00 │ USDT: 0.00 │ ...                             │
  │                                                              │
  │  История транзакций:                                         │
  │  Фильтры: [Все|Депозиты|Выводы|Ставки|Выигрыши|Комиссии]  │
  │                                                              │
  │  ┌──────┬────────┬──────────┬──────────┬──────────┐         │
  │  │ Дата │ Тип    │ Сумма    │ Статус   │ Детали   │         │
  │  ├──────┼────────┼──────────┼──────────┼──────────┤         │
  │  │ 20.03│ Депозит│ +$100.00 │ ✅       │ RUkassa  │         │
  │  │ 20.03│ Ставка │ -$50.00  │ В игре   │ Реал-Бар │         │
  │  │ 19.03│ Выигрыш│ +$210.00 │ ✅       │ Crash x3 │         │
  │  │ 19.03│ Вывод  │ -$300.00 │ ⏳       │ USDT     │         │
  │  └──────┴────────┴──────────┴──────────┴──────────┘         │
  │                                                              │
  │  ── ВКЛАДКА: Ставки (Спорт) ───────────────────────────── │
  │  Все ставки пользователя с деталями                          │
  │                                                              │
  │  ── ВКЛАДКА: Казино ────────────────────────────────────── │
  │  Все раунды казино с деталями                                │
  │                                                              │
  │  ── ВКЛАДКА: Predictions ──────────────────────────────── │
  │  Все позиции и сделки                                        │
  │                                                              │
  │  ── ВКЛАДКА: Безопасность ─────────────────────────────── │
  │  История входов │ Сессии │ KYC │ Linked accounts             │
  │                                                              │
  │  ── ВКЛАДКА: Поддержка ────────────────────────────────── │
  │  Все тикеты пользователя                                     │
  │                                                              │
  │  ── ВКЛАДКА: Партнёрка ────────────────────────────────── │
  │  Реферальная информация (кто привёл, кого привёл)            │
  │                                                              │
  │  ── ВКЛАДКА: Логи ─────────────────────────────────────── │
  │  Все действия с этим пользователем (админские)               │
  │                                                              │
  └──────────────────────────────────────────────────────────────┘

Каждое действие:
  1. Проверяет permission
  2. Логирует в AdminActionLog (с data_before/data_after)
  3. Уведомляет пользователя (если нужно)
  4. HTMX: без перезагрузки
```

### Критерий готовности шага 10.2

```
□ Дашборд: все метрики в реальном времени (HTMX 30s)
□ Дашборд: графики (доход, регистрации)
□ Дашборд: блок "Требуют внимания"
□ Дашборд: последние действия админов
□ Дашборд: финансовая сводка
□ Пользователи: список с фильтрами и поиском
□ Пользователи: массовые действия
□ Пользователи: экспорт CSV/Excel
□ Карточка пользователя: все вкладки
□ Действие: редактирование профиля
□ Действие: корректировка баланса (с причиной)
□ Действие: блокировка/разблокировка (с причиной и сроком)
□ Действие: сброс 2FA
□ Действие: изменение Trust Level
□ Действие: отправка уведомления
□ Действие: "Войти как пользователь" (суперадмин)
□ Вкладка Финансы: все транзакции с фильтрами
□ Все действия проверяют permissions
□ Все действия логируются в AdminActionLog
□ HTMX: действия без перезагрузки
```

---

## ШАГ 10.3 — ФИНАНСЫ + СПОРТ + КАЗИНО + PREDICTIONS

### Задача

```
Админ-интерфейс для управления финансами,
спортивными событиями, казино и маркетами.
Объединяет и расширяет модерацию из этапов 3-7.
```

### Финансовый модуль

```
URL: /admin-panel/finance/
Доступ: @require_permission('finance', 'view_transactions')

Подразделы:

  /admin-panel/finance/             → Финансовый обзор
  /admin-panel/finance/deposits/    → Депозиты
  /admin-panel/finance/withdrawals/ → Выводы (очередь)
  /admin-panel/finance/transactions/→ Все транзакции
  /admin-panel/finance/reports/     → Финансовые отчёты

Финансовый обзор:
  ┌──────────────────────────────────────────────────┐
  │  💰 Финансы                                     │
  │                                                  │
  │  ── Сегодня ──────────────────────────────────  │
  │  Депозиты: $45,678 (234 шт)                    │
  │  Выводы: $23,456 (89 шт)                       │
  │  Нет-поток: +$22,222                            │
  │                                                  │
  │  ── Ожидают действия ─────────────────────────  │
  │  ⏳ Выводов на одобрение: 12 ($23,456)          │
  │  🔴 Подозрительных: 3 ($4,567)                  │
  │  🟡 Крупных (>$5k): 2 ($15,000)                │
  │                                                  │
  │  ── Платёжные системы ────────────────────────  │
  │  NOWpayments: ✅ Работает │ $12,345 сегодня     │
  │  RUkassa:     ✅ Работает │ $33,333 сегодня     │
  │                                                  │
  │  ── Баланс платформы ─────────────────────────  │
  │  Горячий кошелёк BTC: 1.234 BTC                 │
  │  Горячий кошелёк USDT: $45,678                  │
  │  RUkassa баланс: ₽2,345,678                     │
  │                                                  │
  └──────────────────────────────────────────────────┘

Очередь выводов:
  (Расширение интерфейса из этапа 4)

  ┌──────────────────────────────────────────────────┐
  │  Фильтры: [Все|Ожидают|Подозрительные|Крупные]  │
  │                                                  │
  │  ┌──────────────────────────────────────────┐   │
  │  │ 🟡 #W-12345 │ user456 │ $500            │   │
  │  │ USDT TRC20 │ Trust: 3 │ KYC: ✅          │   │
  │  │ Депозит: $5k │ Ставки: 234 │ GGR: $1.2k │   │
  │  │ ⏱️ 3 часа назад                          │   │
  │  │ Флаги: нет                                │   │
  │  │ [✅ Одобрить] [❌ Отклонить] [👤 Профиль] │   │
  │  └──────────────────────────────────────────┘   │
  │                                                  │
  │  ┌──────────────────────────────────────────┐   │
  │  │ 🔴 #W-12346 │ newuser1 │ $2,000          │   │
  │  │ Банк.карта │ Trust: 1 │ KYC: ❌           │   │
  │  │ Депозит: $2k │ Ставки: 3 │ GGR: -$200   │   │
  │  │ ⏱️ 12 часов назад                        │   │
  │  │ ⚠️ Флаги: новый аккаунт, мало ставок,   │   │
  │  │    GGR отрицательный                      │   │
  │  │ [✅ Одобрить] [❌ Отклонить] [🔍 Проверка]│   │
  │  └──────────────────────────────────────────┘   │
  │                                                  │
  └──────────────────────────────────────────────────┘

Финансовые отчёты:
  - GGR по дням/неделям/месяцам
  - NGR (Net Gaming Revenue)
  - Депозиты vs Выводы
  - По платёжным методам
  - По валютам
  - По странам
  - Прогнозы (тренд)
  - Экспорт CSV/Excel/PDF
```

### Спортивный модуль

```
URL: /admin-panel/sports/
Доступ: @require_permission('sports', 'view')

Подразделы:
  /admin-panel/sports/              → Обзор
  /admin-panel/sports/events/       → События/матчи
  /admin-panel/sports/events/create/→ Создать событие
  /admin-panel/sports/bets/         → Ставки
  /admin-panel/sports/live/         → Live матчи
  /admin-panel/sports/results/      → Результаты

Обзор:
  Активных матчей: N
  Ставок сегодня: N ($XXX)
  GGR спорт сегодня: $XXX
  Live сейчас: N матчей

Управление событиями:
  - Создание вручную (команды, дата, вид спорта)
  - Импорт из API (если подключён)
  - Установка коэффициентов
  - Изменение коэффициентов (live)
  - Приостановка приёма ставок
  - Ввод результатов
  - Автоматический расчёт ставок по результатам
  - Отмена матча (возврат ставок)

Управление ставками:
  - Все ставки с фильтрами
  - Отмена конкретной ставки (void)
  - Ручной расчёт
  - Подозрительные ставки (аномальные суммы/паттерны)
```

### Казино модуль

```
URL: /admin-panel/casino/
Доступ: @require_permission('casino', 'view')

Подразделы:
  /admin-panel/casino/             → Обзор
  /admin-panel/casino/games/       → Управление играми
  /admin-panel/casino/rounds/      → Раунды (история)
  /admin-panel/casino/fairness/    → Provably Fair проверка

Обзор:
  Активных игроков: N
  Раундов сегодня: N
  GGR казино сегодня: $XXX
  По играм: Crash $X │ Mines $X │ Dice $X │ ...

Управление играми:
  - Включить/выключить конкретную игру
  - Настроить параметры (мин/макс ставка)
  - Настроить house edge (осторожно!)
  - Просмотр RTP (Return to Player) за период
  - Seed management (для Provably Fair)

Раунды:
  - Все раунды с фильтрами
  - Проверка Provably Fair
  - Подозрительные паттерны
```

### Predictions модуль

```
URL: /admin-panel/predictions/
Доступ: @require_permission('predictions', 'view')

(Расширение интерфейса из этапа 7)

Подразделы:
  /admin-panel/predictions/          → Обзор
  /admin-panel/predictions/markets/  → Все маркеты
  /admin-panel/predictions/create/   → Создать маркет
  /admin-panel/predictions/resolve/  → Ожидают резолюции
  /admin-panel/predictions/disputes/ → Оспаривания

Всё что было в этапе 7 для модератора,
но интегрировано в единую админ-панель.
```

### Критерий готовности шага 10.3

```
□ Финансы: обзор с метриками
□ Финансы: очередь выводов (расширенная)
□ Финансы: все транзакции с фильтрами
□ Финансы: отчёты (GGR, NGR, по методам, валютам)
□ Финансы: экспорт отчётов
□ Спорт: обзор
□ Спорт: управление событиями (CRUD)
□ Спорт: установка коэффициентов
□ Спорт: ввод результатов + расчёт ставок
□ Спорт: отмена матча
□ Спорт: все ставки с фильтрами
□ Казино: обзор
□ Казино: управление играми (вкл/выкл, параметры)
□ Казино: RTP статистика
□ Казино: все раунды
□ Predictions: интеграция из этапа 7
□ Все проверяют permissions
□ Все логируются
```

---

## ШАГ 10.4 — КОНТЕНТ + НАСТРОЙКИ ПЛАТФОРМЫ

### Задача

```
Управление контентом: баннеры, промо-акции,
статические страницы. Глобальные настройки
платформы. Управление ролями и администраторами.
```

### Модель Banner

```
class Banner(models.Model):

    Назначение:
      Баннеры на главной странице и в разделах.

    Поля:
    ─────
    id: UUID, primary key

    title:
      тип: CharField, max 200

    title_en:
      тип: CharField, max 200, blank=True

    # Где показывать
    placement:
      тип: CharField
      choices:
        ('hero', 'Главный баннер (hero)')
        ('sidebar', 'Боковая панель')
        ('sports', 'Раздел спорт')
        ('casino', 'Раздел казино')
        ('predictions', 'Раздел predictions')
        ('popup', 'Всплывающий')

    # Изображение
    image_desktop:
      тип: ImageField
      upload_to: 'banners/'
      Для десктопа (1200×400 или по формату)

    image_mobile:
      тип: ImageField, nullable
      upload_to: 'banners/'
      Для мобильных (800×600)

    # Ссылка
    link_url:
      тип: URLField, blank=True
      Куда ведёт клик

    link_target:
      тип: CharField
      choices: ('_self', 'В этом окне'), ('_blank', 'В новом окне')
      default: '_self'

    # Расписание
    start_date:
      тип: DateTimeField
      Когда начать показывать

    end_date:
      тип: DateTimeField, nullable
      Когда прекратить (null = бессрочно)

    # Таргетинг
    target_countries:
      тип: JSONField, default=list
      Пустой = все страны

    target_languages:
      тип: JSONField, default=list
      Пустой = все языки

    target_new_users_only:
      тип: BooleanField, default=False
      Показывать только новым пользователям (< 7 дней)

    # Статистика
    impressions:
      тип: IntegerField, default=0

    clicks:
      тип: IntegerField, default=0

    # Порядок и статус
    sort_order:
      тип: IntegerField, default=0

    is_active:
      тип: BooleanField, default=True

    created_by:
      тип: ForeignKey → User, nullable

    created_at:
      тип: DateTimeField, auto_now_add=True

    Meta:
      ordering = ['sort_order', '-created_at']
```

### Модель Promotion (Промо-акции)

```
class Promotion(models.Model):

    Назначение:
      Промо-акции и бонусы (будущее).
      Пока заглушка для управления.

    Поля:
    ─────
    id: UUID
    title: CharField
    title_en: CharField
    description: TextField
    description_en: TextField
    promo_type: CharField
      choices:
        ('welcome_bonus', 'Приветственный бонус')
        ('deposit_bonus', 'Бонус за депозит')
        ('free_bet', 'Фрибет')
        ('cashback', 'Кэшбэк')
        ('tournament', 'Турнир')
        ('custom', 'Другое')

    image: ImageField
    start_date: DateTimeField
    end_date: DateTimeField, nullable
    terms_and_conditions: TextField
    is_active: BooleanField
    created_by: ForeignKey → User

    Meta:
      ordering = ['-created_at']
```

### Модель StaticPage (Статические страницы)

```
class StaticPage(models.Model):

    Назначение:
      Статические страницы: О нас, Правила,
      Политика конфиденциальности, Ответственная игра.

    Поля:
    ─────
    id: UUID
    title: CharField, max 200
    title_en: CharField, blank=True
    slug: SlugField, unique
    content: TextField (Markdown или HTML)
    content_en: TextField, blank=True
    meta_description: CharField, max 300, blank=True
    is_active: BooleanField, default=True
    show_in_footer: BooleanField, default=False
    sort_order: IntegerField, default=0
    created_by: ForeignKey → User
    created_at, updated_at

    Предзаполнение:
      - О нас (/about/)
      - Правила и условия (/terms/)
      - Политика конфиденциальности (/privacy/)
      - Ответственная игра (/responsible-gaming/)
      - AML Политика (/aml-policy/)
```

### Глобальные настройки платформы

```
URL: /admin-panel/settings/
Доступ: @require_permission('settings', 'view')

Модель PlatformSettings (синглтон):

  # Общие
  site_name: "DOD"
  site_url: "https://dod.com"
  support_email: "support@dod.com"
  maintenance_mode: BooleanField, default=False
  maintenance_message: TextField

  # Регистрация
  registration_enabled: BooleanField, default=True
  registration_methods: JSONField
    ["email", "google", "telegram", "phone"]
  require_email_verification: BooleanField, default=True
  min_age: IntegerField, default=18

  # Финансы
  min_deposit: JSONField
    {"USD": 10, "EUR": 10, "RUB": 500, "BTC": 0.0001, ...}
  min_withdrawal: JSONField
    {"USD": 20, "EUR": 20, "RUB": 1000, ...}
  withdrawal_fee: JSONField
    {"USD": 0, "EUR": 0, "BTC": 0.0001, "USDT": 1, ...}
  auto_withdrawal_enabled: BooleanField, default=True
  auto_withdrawal_max: DecimalField, default=100

  # Лимиты
  max_bet_amount: DecimalField, default=10000
  max_single_withdrawal: DecimalField, default=50000
  max_daily_withdrawal: DecimalField, default=100000

  # Казино
  casino_enabled: BooleanField, default=True
  crash_enabled: BooleanField, default=True
  mines_enabled: BooleanField, default=True
  dice_enabled: BooleanField, default=True
  plinko_enabled: BooleanField, default=True
  roulette_enabled: BooleanField, default=True
  slots_enabled: BooleanField, default=True

  # Спорт
  sports_enabled: BooleanField, default=True
  live_betting_enabled: BooleanField, default=True
  max_accumulator_legs: IntegerField, default=20

  # Predictions
  predictions_enabled: BooleanField, default=True
  default_market_fee: DecimalField, default=2.00
  default_initial_liquidity: DecimalField, default=1000

  # Партнёрская
  referral_enabled: BooleanField, default=True
  level2_enabled: BooleanField, default=True

  # Безопасность
  force_2fa_for_withdrawals: BooleanField, default=True
  session_timeout_minutes: IntegerField, default=30
  max_login_attempts: IntegerField, default=5
  lockout_minutes: IntegerField, default=15

  # Дизайн
  primary_color: CharField, default="#00e701"
  logo_url: ImageField, nullable
  favicon_url: ImageField, nullable

Интерфейс настроек:
  Разделены по секциям.
  Каждая секция — аккордеон.
  Сохранение отдельно для каждой секции (HTMX).
  Каждое изменение логируется (AdminActionLog).
  Важные изменения (maintenance_mode, registration_enabled)
  → уведомление всем админам.
```

### Управление администраторами

```
URL: /admin-panel/settings/admins/
Доступ: @require_permission('settings', 'manage_admins')

  ┌──────────────────────────────────────────────────────────────┐
  │  👥 Администраторы                                          │
  │                                                              │
  │  [➕ Добавить администратора]                                │
  │                                                              │
  │  ┌──────────────────────────────────────────────────────┐   │
  │  │ 💎 superadmin │ admin@dod.com │ Суперадмин          │   │
  │  │    Онлайн │ Действий: 1,234 │ Посл: 5 мин назад    │   │
  │  │    [Настройки]                                       │   │
  │  └──────────────────────────────────────────────────────┘   │
  │                                                              │
  │  ┌──────────────────────────────────────────────────────┐   │
  │  │ 🔷 alexey │ alexey@dod.com │ Админ                  │   │
  │  │    Онлайн │ Действий: 567 │ Посл: 12 мин назад     │   │
  │  │    [Настройки] [Изменить роль] [Деактивировать]     │   │
  │  └──────────────────────────────────────────────────────┘   │
  │                                                              │
  │  ┌──────────────────────────────────────────────────────┐   │
  │  │ 🔶 maria │ maria@dod.com │ Модератор                │   │
  │  │    Оффлайн │ Действий: 234 │ Посл: вчера            │   │
  │  │    [Настройки] [Изменить роль] [Деактивировать]     │   │
  │  └──────────────────────────────────────────────────────┘   │
  │                                                              │
  └──────────────────────────────────────────────────────────────┘

Добавление администратора:
  1. Выбрать существующего пользователя (поиск)
  2. Назначить роль
  3. Настроить кастомные права (опционально)
  4. Настроить IP whitelist (опционально)
  5. Установить is_staff = True
  6. Создать AdminProfile
  7. Уведомить пользователя

Настройки администратора:
  - Изменить роль
  - Кастомные права (переопределения)
  - IP whitelist
  - Рабочие часы
  - Уведомления
  - Деактивация (с причиной)

Управление ролями:
URL: /admin-panel/settings/roles/
Доступ: @require_permission('settings', 'manage_roles')

  - Список ролей
  - Создание новой роли
  - Редактирование прав роли (JSON editor или UI чекбоксы)
  - Удаление роли (только если нет пользователей)
  - Нельзя удалить системные роли

UI для прав:
  ┌──────────────────────────────────────────────────┐
  │  ✏️ Роль: Модератор                             │
  │                                                  │
  │  ── Пользователи ──────────────────────────────│
  │  ☑ Просмотр                                    │
  │  ☑ Редактирование                              │
  │  ☑ Блокировка                                  │
  │  ☐ Удаление                                    │
  │  ☐ Корректировка баланса                       │
  │  ☑ Сброс 2FA                                   │
  │  ☑ Изменение Trust Level                       │
  │  ☐ Просмотр чувствительных данных              │
  │                                                  │
  │  ── Финансы ────────────────────────────────── │
  │  ☑ Просмотр транзакций                         │
  │  ☐ Одобрение выводов                           │
  │  ☐ Ручной депозит                              │
  │  ...                                             │
  │                                                  │
  │  [Сохранить]                                    │
  │                                                  │
  └──────────────────────────────────────────────────┘
```

### Критерий готовности шага 10.4

```
□ Модель Banner: CRUD + расписание + таргетинг
□ Модель Promotion: CRUD (заглушка для будущего)
□ Модель StaticPage: CRUD + Markdown
□ PlatformSettings: синглтон со всеми настройками
□ Настройки по секциям + HTMX сохранение
□ Каждое изменение настроек логируется
□ Maintenance mode работает
□ Управление администраторами: добавление/деактивация
□ Кастомные права для каждого администратора
□ IP whitelist для администраторов
□ Управление ролями: CRUD + UI чекбоксы
□ Системные роли защищены от удаления
□ Баннеры отображаются на сайте (с таргетингом)
□ Статические страницы доступны по URL
```

---

## ШАГ 10.5 — АНАЛИТИКА И ОТЧЁТЫ

### Задача

```
Глубокая аналитика платформы.
Финансовые отчёты. Пользовательская аналитика.
Игровая аналитика. Экспорт данных.
```

### Аналитический дашборд

```
URL: /admin-panel/analytics/
Доступ: @require_permission('analytics', 'view_dashboard')

Подразделы:
  /admin-panel/analytics/            → Обзор
  /admin-panel/analytics/users/      → Пользовательская
  /admin-panel/analytics/financial/  → Финансовая
  /admin-panel/analytics/gaming/     → Игровая
  /admin-panel/analytics/retention/  → Удержание
  /admin-panel/analytics/reports/    → Отчёты

Обзор:
  Период: [Сегодня|Вчера|7 дней|30 дней|Кастом]

  Ключевые метрики:

  ┌──────────────────────────────────────────┐
  │ Метрика         │ Значение │ Δ vs пред.  │
  ├──────────────────┼──────────┼─────────────┤
  │ Регистрации     │ 89       │ ↑ 12%       │
  │ DAU             │ 1,234    │ ↑ 5%        │
  │ MAU             │ 8,567    │ ↑ 8%        │
  │ Депозиты        │ $45,678  │ ↑ 23%       │
  │ Выводы          │ $23,456  │ ↓ 5%        │
  │ GGR             │ $22,222  │ ↑ 15%       │
  │ NGR             │ $17,655  │ ↑ 12%       │
  │ ARPU            │ $18.02   │ ↑ 3%        │
  │ Конверсия рег→деп│ 34.5%   │ ↑ 2%        │
  │ Ставок          │ 5,678    │ ↑ 10%       │
  │ Ср. чек ставки  │ $45.20   │ ↓ 1%        │
  └──────────────────┴──────────┴─────────────┘

  DAU = Daily Active Users
  MAU = Monthly Active Users
  ARPU = Average Revenue Per User
  GGR = Gross Gaming Revenue
  NGR = Net Gaming Revenue (GGR - бонусы - комиссии)

Пользовательская аналитика:
  - Регистрации по дням (график)
  - Регистрации по источникам (email/google/telegram/phone)
  - Регистрации по странам (карта)
  - Конверсия: рег → первый деп → первая ставка → 2-я ставка
  - Когорты: удержание по неделям/месяцам
  - Активность по часам дня (heatmap)
  - Устройства (desktop/mobile/tablet)

Финансовая аналитика:
  - Доход по дням/неделям/месяцам (график)
  - GGR по продуктам (спорт/казино/predictions)
  - Депозиты по методам оплаты
  - Средний депозит, медианный депозит
  - LTV (Lifetime Value) пользователя
  - Отток (churn rate)

Игровая аналитика:
  - Популярность игр (pie chart)
  - RTP по играм за период
  - Самые прибыльные/убыточные игры
  - Спорт: популярные виды, лиги, типы ставок
  - Predictions: популярные категории, объёмы

Отчёты:
  - Финансовый отчёт (ежемесячный)
  - Отчёт по пользователям
  - Отчёт по играм
  - Отчёт по партнёрам
  - Отчёт по поддержке
  - Кастомный отчёт (выбор метрик + период)
  - Экспорт: CSV, Excel, PDF
  - Запланированные отчёты (email ежедневно/еженедельно)
```

### AnalyticsService

```
AnalyticsService:

  get_dashboard_metrics(period):
    """
    Основные метрики для дашборда.
    Кешируется в Redis на 5 минут.
    """

    cache_key = f'admin_metrics:{period}'
    cached = cache.get(cache_key)
    if cached:
      return cached

    start, end = get_period_dates(period)
    prev_start, prev_end = get_previous_period(start, end)

    metrics = {
      'registrations': User.objects.filter(
        date_joined__range=(start, end)
      ).count(),

      'dau': User.objects.filter(
        last_activity__date=date.today()
      ).count(),

      'deposits': Transaction.objects.filter(
        type='deposit',
        status='completed',
        created_at__range=(start, end),
      ).aggregate(
        total=Sum('amount_usd'),
        count=Count('id'),
      ),

      'withdrawals': ...,

      'ggr': calculate_total_ggr(start, end),

      # ... все метрики
    }

    # Сравнение с предыдущим периодом
    prev_metrics = { ... }
    for key in metrics:
      current = metrics[key]
      previous = prev_metrics.get(key, 0)
      if isinstance(current, dict):
        continue
      if previous > 0:
        metrics[f'{key}_change'] = (
          (current - previous) / previous * 100
        )
      else:
        metrics[f'{key}_change'] = 0

    cache.set(cache_key, metrics, 300)
    return metrics


  get_cohort_retention(cohort_date, weeks=12):
    """
    Когортный анализ удержания.
    cohort_date — неделя/месяц регистрации.
    """
    users = User.objects.filter(
      date_joined__week=cohort_date.isocalendar()[1],
      date_joined__year=cohort_date.year,
    )
    total = users.count()
    if total == 0:
      return []

    retention = []
    for week in range(weeks):
      week_start = cohort_date + timedelta(weeks=week)
      week_end = week_start + timedelta(weeks=1)
      active = users.filter(
        last_activity__range=(week_start, week_end)
      ).count()
      retention.append({
        'week': week,
        'active': active,
        'rate': active / total * 100,
      })

    return retention


  generate_financial_report(month, year):
    """
    Ежемесячный финансовый отчёт.
    Celery задача.
    """
    start = date(year, month, 1)
    end = (start + timedelta(days=32)).replace(day=1)

    report = {
      'period': f'{month:02d}/{year}',

      'deposits': {
        'total': ...,
        'count': ...,
        'by_method': ...,
        'by_currency': ...,
        'by_country': ...,
      },

      'withdrawals': { ... },

      'ggr': {
        'sport': ...,
        'casino': ...,
        'predictions': ...,
        'total': ...,
      },

      'ngr': ...,  # GGR - бонусы - партнёрские

      'users': {
        'new_registrations': ...,
        'first_time_depositors': ...,
        'active_users': ...,
        'churned_users': ...,
      },

      'support': {
        'tickets': ...,
        'avg_resolution_time': ...,
        'avg_rating': ...,
      },

      'partners': {
        'commissions_paid': ...,
        'new_referrals': ...,
      },
    }

    # Сохранить как файл
    # Отправить на email админам

    return report
```

### Критерий готовности шага 10.5

```
□ Аналитический дашборд: все ключевые метрики
□ Сравнение с предыдущим периодом (Δ%)
□ Графики: доход, регистрации, активность
□ Пользовательская аналитика: источники, страны, устройства
□ Конверсионная воронка
□ Когортный анализ удержания
□ Финансовая аналитика: GGR, NGR, LTV
□ Игровая аналитика: популярность, RTP
□ Отчёты: финансовый, пользовательский, игровой
□ Кастомный отчёт (выбор метрик)
□ Экспорт: CSV, Excel, PDF
□ Запланированные отчёты (email)
□ Кеширование метрик в Redis
□ Celery: генерация ежемесячного отчёта
```

---

## ШАГ 10.6 — ЛОГИ, АУДИТ, БЕЗОПАСНОСТЬ

### Задача

```
Полный аудит-трейл всех действий.
Системные логи. Безопасность админ-панели.
Глобальный поиск.
```

### Страница логов

```
URL: /admin-panel/logs/
Доступ: @require_permission('logs', 'view_admin_logs')

Подразделы:
  /admin-panel/logs/admin/    → Действия администраторов
  /admin-panel/logs/user/     → Действия пользователей
  /admin-panel/logs/system/   → Системные логи
  /admin-panel/logs/security/ → Безопасность

Действия администраторов:
  ┌──────────────────────────────────────────────────────────────┐
  │  📋 Логи администраторов                                    │
  │                                                              │
  │  Фильтры:                                                   │
  │  Админ: [Все ▼] │ Модуль: [Все ▼] │ Период: [Сегодня ▼]   │
  │  Действие: [Все ▼] │ Результат: [Все|Успех|Ошибка]         │
  │  Поиск: [____________________] 🔍                           │
  │                                                              │
  │  ┌────────┬──────────┬────────────┬──────────┬──────────┐   │
  │  │ Время  │ Админ    │ Действие   │ Объект   │ Рез.     │   │
  │  ├────────┼──────────┼────────────┼──────────┼──────────┤   │
  │  │ 14:30  │ Алексей  │ Одобрил    │ Вывод    │ ✅       │   │
  │  │        │ (Админ)  │ вывод $500 │ #W-12345 │          │   │
  │  │        │ IP: 1.2. │            │ user456  │          │   │
  │  ├────────┼──────────┼────────────┼──────────┼──────────┤   │
  │  │ 14:25  │ Мария    │ Одобрила   │ KYC      │ ✅       │   │
  │  │        │ (Модер.) │ KYC        │ #K-567   │          │   │
  │  │        │ IP: 3.4. │            │ player78 │          │   │
  │  ├────────┼──────────┼────────────┼──────────┼──────────┤   │
  │  │ 14:20  │ Система  │ SLA наруш. │ Тикет    │ ⚠️       │   │
  │  │        │          │ автоэскал. │ #T-0042  │          │   │
  │  └────────┴──────────┴────────────┴──────────┴──────────┘   │
  │                                                              │
  │  При клике на строку → детали:                              │
  │  ┌──────────────────────────────────────────────────────┐   │
  │  │ Действие: Одобрение вывода                           │   │
  │  │ Админ: Алексей (admin) │ IP: 1.2.3.4                │   │
  │  │ Время: 20.03.2025 14:30:45 │ Длительность: 234ms    │   │
  │  │ Модуль: finance │ Тип: withdrawal_approved           │   │
  │  │                                                      │   │
  │  │ Объект: Withdrawal #W-12345                          │   │
  │  │ Пользователь: user456                                │   │
  │  │                                                      │   │
  │  │ До:                                                  │   │
  │  │ {"status": "pending", "amount": 500}                 │   │
  │  │                                                      │   │
  │  │ После:                                               │   │
  │  │ {"status": "approved", "amount": 500,                │   │
  │  │  "processed_by": "alexey"}                           │   │
  │  └──────────────────────────────────────────────────────┘   │
  │                                                              │
  │  [📥 Экспорт логов]                                         │
  │                                                              │
  └──────────────────────────────────────────────────────────────┘

Логи безопасности:
  - Неудачные попытки входа в админку
  - Попытки доступа с запрещённых IP
  - Отказы в правах (permission denied)
  - Изменения ролей и прав
  - Изменения критических настроек
  - Подозрительные паттерны (много действий за короткое время)
```

### Глобальный поиск

```
URL: /api/admin/search/?q=...
Доступ: любой администратор

Ищет по:
  - Пользователи (email, username, ID, телефон)
  - Тикеты (номер, тема)
  - Транзакции (ID, номер)
  - Маркеты (название)
  - Выводы (ID)
  - KYC заявки (ID)

Результаты группируются по типу:

  ┌──────────────────────────────────────────────────┐
  │  🔍 Результаты поиска: "user456"                │
  │                                                  │
  │  👥 Пользователи (1)                            │
  │  └ user456 │ user@example.com │ $1,234           │
  │                                                  │
  │  📋 Тикеты (2)                                  │
  │  └ #DOD-20250320-0042 │ "Вывод не приходит"     │
  │  └ #DOD-20250315-0015 │ "Не могу войти"         │
  │                                                  │
  │  💰 Транзакции (3)                              │
  │  └ Депозит $100 │ 20.03.2025                    │
  │  └ Вывод $500 │ 19.03.2025                      │
  │  └ Ставка $50 │ 20.03.2025                      │
  │                                                  │
  └──────────────────────────────────────────────────┘

HTMX:
  hx-get="/api/admin/search/?q=..."
  hx-trigger="keyup changed delay:300ms"
  hx-target="#search-results"
  Показывать в dropdown под поиском в navbar.
```

### Безопасность админ-панели

```
Дополнительные меры:

1. 2FA обязательна для ВСЕХ администраторов
   При попытке войти без 2FA → принудительная настройка

2. Сессия админ-панели:
   Отдельная от пользовательской сессии
   Таймаут: 30 минут бездействия (настраивается)
   При входе в админку → отдельная проверка 2FA

3. IP whitelist:
   Суперадмин настраивает для каждого админа
   Если IP не в списке → отказ + лог + уведомление

4. Аномалии:
   Celery задача (каждые 5 минут):
   - Админ сделал > 100 действий за час → уведомление
   - Админ работает в нерабочее время → уведомление
   - Админ одобрил > 10 выводов за 10 мин → уведомление
   - Два админа вошли с одного IP → уведомление

5. Критические действия:
   Для некоторых действий требуется подтверждение
   от другого администратора (4 eyes principle):
   - Удаление пользователя
   - Корректировка баланса > $10,000
   - Изменение роли суперадмина
   - Отключение 2FA другого админа
   - Изменение критических настроек

6. Логирование:
   КАЖДЫЙ запрос к админ-панели логируется
   POST/PUT/DELETE → детальный лог с data_before/after
   GET → краткий лог (кто что смотрел)
```

### Celery задачи

```
# apps/dashboard/tasks.py

# Каждые 30 секунд
update_realtime_metrics():
  """Обновить метрики дашборда в Redis."""

# Каждые 5 минут
check_admin_anomalies():
  """Проверка аномальной активности админов."""

check_attention_items():
  """Обновить список 'Требуют внимания'."""

# Каждый час
update_analytics_cache():
  """Обновить кэш аналитики."""

# Ежедневно
generate_daily_admin_report():
  """Отчёт о действиях админов за день."""

cleanup_old_logs():
  """Удалить детальные логи старше 1 года."""
  # Агрегированные логи хранятся навсегда.

# Ежемесячно
generate_monthly_report():
  """Полный месячный отчёт."""
```

### Критерий готовности шага 10.6

```
□ Логи админов: все действия с фильтрами
□ Детали лога: data_before / data_after
□ Логи безопасности: неудачные входы, отказы
□ Логи системные (Celery задачи, ошибки)
□ Глобальный поиск (пользователи, тикеты, транзакции)
□ HTMX: результаты поиска в dropdown
□ 2FA обязательна для всех админов
□ Отдельная сессия админки (30 мин таймаут)
□ IP whitelist работает
□ Аномалии: уведомления при подозрительном
□ 4 eyes principle для критических действий
□ Каждый запрос логируется
□ Экспорт логов
□ Celery: обновление метрик, аномалии, отчёты
□ Cleanup старых логов
```

---

## 📊 ОБЩИЙ ЧЕКЛИСТ ЭТАПА 10

```
РОЛИ И ПРАВА:
  □ Модель AdminRole (6 предустановленных ролей)
  □ Модель AdminProfile (связь + кастомные права)
  □ Гранулярные права (JSON, ~50 отдельных прав)
  □ Декораторы require_permission, require_role_level
  □ Middleware: проверка доступа + логирование

ДАШБОРД:
  □ Метрики реального времени (HTMX 30s)
  □ Графики (доход, регистрации)
  □ "Требуют внимания" (выводы, KYC, SLA, фрод)
  □ Последние действия админов
  □ Финансовая сводка

ПОЛЬЗОВАТЕЛИ:
  □ Список с фильтрами и поиском
  □ Массовые действия
  □ Экспорт CSV/Excel
  □ Детальная карточка (10 вкладок)
  □ Все действия: редакт, бан, баланс, 2FA, trust
  □ "Войти как пользователь" (суперадмин)

ФИНАНСЫ:
  □ Обзор с метриками
  □ Очередь выводов (расширенная)
  □ Все транзакции
  □ Отчёты (GGR, NGR, по методам, валютам, странам)
  □ Экспорт

СПОРТ:
  □ Управление событиями (CRUD)
  □ Коэффициенты
  □ Результаты + расчёт
  □ Все ставки

КАЗИНО:
  □ Управление играми
  □ RTP статистика
  □ Все раунды

PREDICTIONS:
  □ Интеграция из этапа 7

КОНТЕНТ:
  □ Баннеры (CRUD + расписание + таргетинг)
  □ Промо-акции (CRUD)
  □ Статические страницы (CRUD)

НАСТРОЙКИ:
  □ PlatformSettings (все секции)
  □ Управление администраторами
  □ Управление ролями (CRUD + UI)
  □ Maintenance mode

АНАЛИТИКА:
  □ Ключевые метрики + сравнение
  □ Пользовательская аналитика
  □ Финансовая аналитика
  □ Игровая аналитика
  □ Когортный анализ
  □ Отчёты (финансовый, пользователь, игры)
  □ Экспорт CSV/Excel/PDF
  □ Запланированные отчёты

ЛОГИ И АУДИТ:
  □ Логи администраторов (все действия)
  □ data_before / data_after
  □ Логи безопасности
  □ Глобальный поиск
  □ Экспорт логов

БЕЗОПАСНОСТЬ:
  □ 2FA обязательна для всех админов
  □ Отдельная сессия (30 мин)
  □ IP whitelist
  □ Аномалии (уведомления)
  □ 4 eyes principle
  □ Каждый запрос логируется

CELERY:
  □ Обновление метрик (30 сек)
  □ Аномалии (5 мин)
  □ "Требуют внимания" (5 мин)
  □ Кэш аналитики (1 час)
  □ Ежедневный отчёт
  □ Ежемесячный отчёт
  □ Cleanup логов

ИНТЕРФЕЙС:
  □ Единый layout (sidebar + navbar + content)
  □ Тёмная тема
  □ HTMX интерактивность
  □ Chart.js графики
  □ Мобильная адаптация
  □ Sidebar показывает только доступные пункты
```

---

```
╔══════════════════════════════════════════════════════╗
║                                                      ║
║   ЭТАП 10 ЗАВЕРШЁН                                  ║
║                                                      ║
║   Следующий: ЭТАП 11                                ║
║   Telegram Mini App                                 ║
║                                                      ║
║   Продолжить?                                       ║
║                                                      ║
╚══════════════════════════════════════════════════════╝
```