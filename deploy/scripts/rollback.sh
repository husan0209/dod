#!/bin/bash
set -e

APP_DIR="/opt/dod"
COMPOSE_FILE="docker-compose.prod.yml"

echo "═══ ОТКАТ DOD ═══"

cd $APP_DIR

# Откат к предыдущему коммиту
PREV_COMMIT=$(cat /tmp/dod_prev_commit 2>/dev/null)

if [ -z "$PREV_COMMIT" ]; then
  echo "❌ Файл предыдущего коммита не найден"
  echo "Откат к предыдущему коммиту Git:"
  git log --oneline -5
  echo "Используйте: git checkout <commit>"
  exit 1
fi

echo "Откат к коммиту: $PREV_COMMIT"
git checkout $PREV_COMMIT

# Пересобрать
docker compose -f $COMPOSE_FILE up -d --build

# Восстановить базу (если нужно)
LATEST_BACKUP=$(ls -t deploy/backups/pre-deploy-*.sql.gz | head -1)
if [ -n "$LATEST_BACKUP" ]; then
  echo "Доступен бэкап: $LATEST_BACKUP"
  echo "Для восстановления базы:"
  echo "  ./deploy/backups/restore.sh $LATEST_BACKUP"
fi

echo "═══ Откат завершён ═══"
