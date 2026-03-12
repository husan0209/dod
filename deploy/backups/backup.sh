#!/bin/bash
# deploy/backups/backup.sh
# Full backup script for DOD platform

set -e

APP_DIR="/opt/dod"
BACKUP_DIR="${APP_DIR}/deploy/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="dod_backup_${TIMESTAMP}"
COMPOSE_FILE="docker-compose.prod.yml"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}═══ DOD BACKUP ═══${NC}"
echo "Time: $TIMESTAMP"
echo "Backup: $BACKUP_NAME"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# 1. PostgreSQL Dump
echo -e "${YELLOW}[1/3] Backing up PostgreSQL...${NC}"
cd "$APP_DIR"
docker compose -f "$COMPOSE_FILE" exec -T db \
  pg_dump -U "${DB_USER}" "${DB_NAME}" | \
  gzip -9 > "${BACKUP_DIR}/${BACKUP_NAME}_db.sql.gz"
echo -e "${GREEN}✓ Database backup completed${NC}"

# 2. Redis Snapshot
echo -e "${YELLOW}[2/3] Backing up Redis...${NC}"
docker compose -f "$COMPOSE_FILE" exec -T redis \
  redis-cli -a "${REDIS_PASSWORD}" BGSAVE || true
sleep 2
docker compose -f "$COMPOSE_FILE" cp redis:/data/dump.rdb "${BACKUP_DIR}/${BACKUP_NAME}_redis.rdb" || true
echo -e "${GREEN}✓ Redis backup completed${NC}"

# 3. Backup environment and configuration
echo -e "${YELLOW}[3/3] Backing up configuration...${NC}"
tar -czf "${BACKUP_DIR}/${BACKUP_NAME}_config.tar.gz" \
  -C "$APP_DIR" .env.production deploy/nginx/ssl || true
echo -e "${GREEN}✓ Configuration backup completed${NC}"

# Cleanup old backups (keep last 7 days)
echo -e "${YELLOW}Cleaning up old backups (older than 7 days)...${NC}"
find "$BACKUP_DIR" -name "dod_backup_*" -mtime +7 -delete

# Create backup manifest
cat > "${BACKUP_DIR}/${BACKUP_NAME}_manifest.txt" << EOF
Backup Name: $BACKUP_NAME
Timestamp: $TIMESTAMP
Database: dod_backup_${TIMESTAMP}_db.sql.gz
Redis: dod_backup_${TIMESTAMP}_redis.rdb
Config: dod_backup_${TIMESTAMP}_config.tar.gz
Host: $(hostname)
Size: $(du -sh "$BACKUP_DIR" | cut -f1)
EOF

echo -e "${GREEN}═══ BACKUP COMPLETED ═══${NC}"
echo "Location: $BACKUP_DIR"
echo "Total backups: $(ls -1 ${BACKUP_DIR}/dod_backup_* 2>/dev/null | wc -l)"

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
