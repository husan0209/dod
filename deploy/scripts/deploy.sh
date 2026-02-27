#!/bin/bash
set -e

ENVIRONMENT=${1:-staging}
APP_DIR="/opt/dod"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
COMPOSE_FILE="docker-compose.${ENVIRONMENT}.yml"

echo "═══ Деплой DOD ($ENVIRONMENT) ═══"
echo "Время: $TIMESTAMP"

# 1. Бéкап текущей версии
echo "1. Создание бэкапа..."
cd $APP_DIR
git rev-parse HEAD > /tmp/dod_prev_commit
docker compose -f $COMPOSE_FILE exec -T db \
  pg_dump -U $DB_USER $DB_NAME | gzip > \
  deploy/backups/pre-deploy-${TIMESTAMP}.sql.gz

# 2. Получить новый код
echo "2. Обновление кода..."
git pull origin $(git branch --show-current)

# 3. Собрать и запустить
echo "3. Сборка и запуск..."
docker compose -f $COMPOSE_FILE build --no-cache web
docker compose -f $COMPOSE_FILE up -d

# 4. Миграции
echo "4. Применение миграций..."
docker compose -f $COMPOSE_FILE exec -T web \
  python manage.py migrate --noinput

# 5. Collectstatic
echo "5. Сборка статики..."
docker compose -f $COMPOSE_FILE exec -T web \
  python manage.py collectstatic --noinput

# 6. Health check
echo "6. Проверка здоровья..."
sleep 10
for i in $(seq 1 5); do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
    https://yourdomain.com/health/)
  if [ "$STATUS" = "200" ]; then
    echo "✅ Health check OK"
    break
  fi
  echo "⚠️ Попытка $i: статус $STATUS"
  sleep 5
done

if [ "$STATUS" != "200" ]; then
  echo "❌ Health check FAILED. Откат..."
  ./deploy/scripts/rollback.sh
  exit 1
fi

echo "═══ Деплой завершён успешно ═══"
