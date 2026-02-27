# docs/architecture.md

## Архитектура DOD Platform

### 1. Обзор архитектуры
Модульный монолит на базе Django.

### 2. Диаграмма компонентов
- Django backend
- PostgreSQL database
- Redis cache/broker
- Celery workers
- Nginx proxy
- Docker containers

### 3. Поток данных
User -> Nginx -> Django -> PostgreSQL
WebSocket через Channels
Celery для фоновых задач

### 4. База данных
ER-диаграмма: User, Wallet, Bet, Transaction, etc.

### 5. WebSocket архитектура
Channels + Redis для real-time updates

### 6. Celery задачи
Payments, notifications, analytics

### 7. Telegram интеграция
Bot API + Mini App

### 8. Масштабирование
Load balancer, read replicas, Redis cluster
