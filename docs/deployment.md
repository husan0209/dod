# docs/deployment.md

## Инструкция по деплою DOD Platform

### 1. Требования к серверу
- Ubuntu 22.04+
- 4 CPU, 8GB RAM (минимум)
- 100GB SSD
- Домен с DNS

### 2. Установка Docker
```bash
curl -fsSL https://get.docker.com | sh
systemctl enable docker
systemctl start docker
```

### 3. Docker Compose
```bash
apt-get install -y docker-compose-plugin
```

### 4. Клонирование и настройка .env
```bash
git clone <repo> /opt/dod
cd /opt/dod
cp .env.production.example .env.production
# Отредактируйте .env.production с реальными значениями
```

### 5. SSL сертификат (Certbot)
```bash
apt-get install -y certbot
certbot certonly --standalone -d yourdomain.com
```

### 6. Запуск docker compose
```bash
docker compose -f docker-compose.prod.yml up -d --build
```

### 7. Первоначальная настройка
- Создание суперадмина:
  ```bash
  docker compose -f docker-compose.prod.yml exec web python manage.py createsuperuser
  ```
- Загрузка fixtures:
  ```bash
  docker compose -f docker-compose.prod.yml exec web python manage.py loaddata initial_data
  ```
- Настройка Telegram бота:
  - Установите webhook: https://yourdomain.com/tg/bot/webhook/

### 8. Обновление платформы
```bash
cd /opt/dod
git pull origin main
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml exec web python manage.py migrate
```

### 9. Откат
```bash
./deploy/scripts/rollback.sh
```
