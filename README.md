# DOD Platform (Dream of Digital)

![DOD Platform](static/img/logo-full.png)

## 📋 Обзор

**DOD Platform** — это современная, высокотехнологичная многофункциональная платформа для гемблинга и прогнозирования. Проект объединяет в себе классические ставки на спорт, инновационное онлайн-казино, рынки предсказаний (Prediction Markets) и глубокую интеграцию с Telegram.

Платформа построена на базе **Modular Monolith Architecture**, что обеспечивает высокую скорость разработки при сохранении масштабируемости и простоты деплоя.

---

## 🚀 Основные возможности

### 1. Аккаунты и Безопасность (Stage 1, 2)
- Гибридная авторизация: Email/пароль, OAuth (Google), Telegram (Seamless).
- Безопасность: 2FA (TOTP), шифрование данных, защита от Brute-force.
- KYC: Трехуровневая система верификации (Email -> Personal Data -> Documents).

### 2. Финансы и Платежи (Stage 3, 4)
- Мультивалютный кошелёк (USD, BTC, ETH, USDT, TON).
- Интеграция с платежными шлюзами: NOWPayments, RUkassa.
- Прямая интеграция с TON (Telegram Payments / TON Connect).
- Система автоматического и ручного вывода средств с антифрод-проверками.

### 3. Ставки на спорт (Stage 5)
- Широкая линия: Футбол, Баскетбол, Теннис, Киберспорт и др.
- Live ставки с обновлением коэффициентов в реальном времени через WebSockets.
- Комбинированные ставки (Экспрессы) с бонусными коэффициентами.
- Детальная статистика и результаты матчей.

### 4. Инновационное Казино (Stage 6)
- **Provably Fair**: Все игры используют алгоритмы доказуемой честности на базе HMAC-SHA256.
- Популярные игры: Crash, Mines, Dice, Plinko, Roulette, Slots.
- Плавные анимации и real-time взаимодействие.

### 5. Рынки Предсказаний (Stage 7)
- Торговля долями (Shares) в исходах реальных событий (Политика, Крипто, Шоу-бизнес).
- Автоматический Маркет-Мейкер (AMM) для ликвидности.
- Графики цен и книга ордеров.

### 6. Партнёрская программа (Stage 8)
- Многоуровневая система (Tiered System).
- Расчёт по модели GGR (Gross Gaming Revenue).
- Личный кабинет партнёра с детальной аналитикой и реферальными ссылками.

### 7. Поддержка и Уведомления (Stage 9)
- Внутренняя система тикетов и онлайн-чат.
- Многоканальные уведомления: Email, Telegram Bot, Browser Push.

### 8. Админ-Панель (Stage 10)
- Полный контроль над платформой: пользователи, транзакции, ставки, маркеты.
- Ролевая модель доступа (RBAC).
- Мониторинг подозрительной активности и управление лимитами.

### 9. Telegram Mini App (Stage 11)
- Полноценное приложение внутри Telegram.
- Веб-интерфейс, оптимизированный под мобильные устройства.
- Inline-бот для шаринга маркетов и ставок.

---

## 🛠 Технологический стек

- **Backend**: Python 3.12, Django 5.1, Django Rest Framework.
- **Real-time**: Django Channels, WebSockets (Daphne).
- **Frontend**: HTMX, TailwindCSS, AlpineJS, Vanilla JS.
- **База данных**: PostgreSQL 16.
- **Кэширование и Брокер**: Redis 7.
- **Задачи**: Celery, Celery Beat.
- **Инфраструктура**: Docker, Docker Compose, Nginx.
- **Мониторинг**: Prometheus, Grafana, Sentry.

---

## 📦 Структура проекта

```
DOD/
├── apps/               # Приложения проекта (модули)
│   ├── accounts/       # Пользователи и профили
│   ├── wallet/         # Кошелек и балансы
│   ├── payments/       # Платежные интеграции
│   ├── sports/         # Спортивный беттинг
│   ├── casino/         # Игры (Crash, Mines и др.)
│   ├── predictions/    # Рынки предсказаний
│   ├── referral/       # Партнерская программа
│   ├── support/        # Тикеты и чат
│   ├── dashboard/      # Админ-панель
│   ├── miniapp/        # Telegram Mini App
│   └── core/           # Общие утилиты и базовые модели
├── config/             # Настройки проекта (Django settings)
├── static/             # Статические файлы (CSS, JS, Images)
├── templates/          # HTML шаблоны (HTMX + Tailwind)
├── deploy/             # Конфигурации для деплоя
├── docker-compose.yml  # Файл конфигурации Docker
├── requirements.txt    # Зависимости Python
└── manage.py           # Точка входа Django
```

---

## 🏗 Быстрый старт

### Требования
- Docker & Docker Compose

### Установка

1. Склонируйте репозиторий:
   ```bash
   git clone https://github.com/your-repo/dod.git
   cd dod
   ```

2. Настройте переменные окружения:
   ```bash
   cp .env.example .env
   # Отредактируйте .env, указав секретные ключи и настройки
   ```

3. Запустите проект через Docker Compose:
   ```bash
   docker compose up -d --build
   ```

4. Выполните миграции и создайте суперпользователя:
   ```bash
   docker compose exec web python manage.py migrate
   docker compose exec web python manage.py createsuperuser
   ```

5. Платформа будет доступна по адресу: `http://localhost:8000`

### Production деплой

  Смотри: docs/deployment.md

---

## 📖 Документация

  docs/
    deployment.md     — Инструкция по деплою
    api.md            — API документация
    architecture.md   — Архитектура
    runbook.md        — Runbook для команды
    security.md       — Политика безопасности
    backup-restore.md — Бэкапы и восстановление

---

## 🔒 Безопасность

Если вы обнаружили уязвимость, пожалуйста, не создавайте публичный Issue. Напишите нам напрямую: `security@dod-platform.com`.

---

© 2025 DOD Platform. Все права защищены.
