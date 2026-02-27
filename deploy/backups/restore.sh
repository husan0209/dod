#!/bin/bash
set -e

BACKUP_FILE=$1
if [ -z "$BACKUP_FILE" ]; then
  echo "Использование: ./restore.sh <backup_file.dump>"
  echo "Доступные бэкапы:"
  ls -la /opt/dod/deploy/backups/data/db_*.dump
  exit 1
fi

echo "═══ ВОССТАНОВЛЕНИЕ DOD ═══"
echo "Файл: $BACKUP_FILE"
echo "ВНИМАНИЕ: Текущие данные будут перезаписаны!"
read -p "Продолжить? (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
  exit 0
fi

# 1. Остановить приложение
echo "1. Остановка приложения..."
docker compose -f /opt/dod/docker-compose.prod.yml \
  stop web channels celery_worker celery_beat

# 2. Восстановить базу
echo "2. Восстановление базы..."
docker compose -f /opt/dod/docker-compose.prod.yml \
  exec -T db pg_restore -U $DB_USER \
  --clean --if-exists -d $DB_NAME < "$BACKUP_FILE"

# 3. Запустить приложение
echo "3. Запуск приложения..."
docker compose -f /opt/dod/docker-compose.prod.yml \
  up -d

echo "═══ Восстановление завершено ═══"
