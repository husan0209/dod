# docs/launch-checklist.md

## Чеклист запуска DOD Platform

### ПЕРЕД ЗАПУСКОМ

#### Инфраструктура
- Сервер арендован и настроен
- Домен куплен и DNS настроен
- SSL сертификат получен
- Docker + Docker Compose установлены
- Firewall настроен (22, 80, 443)
- Fail2Ban активен
- SSH ключи (пароль отключён)

#### Приложение
- .env.production заполнен
- SECRET_KEY сгенерирован
- DEBUG = False
- ALLOWED_HOSTS настроен
- Все миграции применены
- Fixtures загружены
- collectstatic выполнен
- Суперадмин создан

#### Интеграции
- SMTP настроен (email работает)
- NOWpayments API ключи (production)
- RUkassa ключи (production)
- Google OAuth настроен
- Telegram бот: webhook установлен
- Telegram Mini App: URL настроен
- Sentry DSN настроен

#### Мониторинг
- Prometheus собирает метрики
- Grafana дашборды настроены
- Алерты настроены (Telegram / email)
- Health check работает

#### Бэкапы
- Cron задача настроена (каждые 6 часов)
- S3 хранилище настроено
- Тестовый restore прошёл

#### Безопасность
- Security audit пройден
- bandit: 0 high severity
- safety: 0 vulnerabilities
- SSL Labs: A+ рейтинг
- Security headers: все на месте

#### Тестирование
- Все юнит-тесты проходят
- Integration тесты проходят
- Нагрузочный тест: OK
- Тестовый депозит (staging)
- Тестовая ставка (staging)
- Тестовый вывод (staging)
- Telegram Mini App: тест (staging)

#### Документация
- README.md написан
- deployment.md написан
- runbook.md написан
- security.md написан
- api.md написан

### ЗАПУСК
- docker compose -f docker-compose.prod.yml up -d
- Health check: 200 OK
- Тестовый логин
- Тестовый депозит
- Мониторинг: метрики приходят
- Бот Telegram: /start работает
- Mini App: открывается из Telegram
