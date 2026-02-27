#!/bin/bash

# deploy/scripts/health-check.sh
# Проверка здоровья приложения после деплоя

URL=${1:-https://yourdomain.com/health/}

echo "Проверка здоровья: $URL"

STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$URL")

if [ "$STATUS" = "200" ]; then
  echo "✅ Health check passed"
  exit 0
else
  echo "❌ Health check failed with status $STATUS"
  exit 1
fi
