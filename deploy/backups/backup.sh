#!/bin/bash
set -e

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/opt/dod/deploy/backups/data"
DB_NAME=${DB_NAME:-dod_production}
RETENTION_DAYS=${BACKUP_RETENTION_DAYS:-30}
TAG=${1:-scheduled}

mkdir -p $BACKUP_DIR

echo "═══ Бэкап DOD ($TAG) ═══"
echo "Время: $TIMESTAMP"

# 1. Database dump
echo "1. Бэкап PostgreSQL..."
docker compose -f /opt/dod/docker-compose.prod.yml \
  exec -T db pg_dump -U $DB_USER $DB_NAME \
  --format=custom --compress=9 \
  > "$BACKUP_DIR/db_${TAG}_${TIMESTAMP}.dump"

DB_SIZE=$(du -sh "$BACKUP_DIR/db_${TAG}_${TIMESTAMP}.dump" | cut -f1)
echo "   Размер: $DB_SIZE"

# 2. Media files
echo "2. Бэкап медиа..."
tar czf "$BACKUP_DIR/media_${TAG}_${TIMESTAMP}.tar.gz" \
  -C /opt/dod media/ 2>/dev/null || true

# 3. Env files
echo "3. Бэкап конфигов..."
cp /opt/dod/.env.production \
  "$BACKUP_DIR/env_${TAG}_${TIMESTAMP}.env"

# 4. Upload to S3 (если настроен)
if [ -n "$BACKUP_S3_BUCKET" ]; then
  echo "4. Загрузка в S3..."
  aws s3 cp "$BACKUP_DIR/db_${TAG}_${TIMESTAMP}.dump" \
    "s3://$BACKUP_S3_BUCKET/db/" \
    --endpoint-url "$BACKUP_S3_ENDPOINT"
  aws s3 cp "$BACKUP_DIR/media_${TAG}_${TIMESTAMP}.tar.gz" \
    "s3://$BACKUP_S3_BUCKET/media/" \
    --endpoint-url "$BACKUP_S3_ENDPOINT"
fi

# 5. Cleanup старых бэкапов
echo "5. Удаление старых бэкапов (> ${RETENTION_DAYS} дней)..."
find $BACKUP_DIR -type f -mtime +$RETENTION_DAYS -delete

echo "═══ Бэкап завершён ═══"
