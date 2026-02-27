# docs/runbook.md

## Runbook для команды DOD Platform

### ЕЖЕДНЕВНЫЕ ЗАДАЧИ
- Проверить Grafana дашборд
- Проверить очередь выводов
- Проверить логи ошибок

### ЕЖЕНЕДЕЛЬНЫЕ ЗАДАЧИ
- Проверить размер БД
- Проверить размер логов
- Обновить зависимости (pip)
- Проверить бэкапы

### ЕЖЕМЕСЯЧНЫЕ ЗАДАЧИ
- Обновить SSL (автоматически)
- Обновить Docker images
- Ротация секретов
- Security scan

### ЧАСТЫЕ ПРОБЛЕМЫ

**Проблема: 502 Bad Gateway**
Решение: docker compose restart web

**Проблема: Медленные запросы**
Решение: EXPLAIN ANALYZE, добавить индекс

**Проблема: Redis OOM**
Решение: redis-cli FLUSHDB (cache only)

**Проблема: Celery зависла**
Решение: docker compose restart celery_worker

**Проблема: Диск заполнился**
Решение: docker system prune, старые логи
