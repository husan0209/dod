#!/bin/sh
set -e

echo "Waiting for PostgreSQL..."
while ! nc -z "$DB_HOST" "$DB_PORT"; do
  sleep 0.5
done
echo "PostgreSQL is available"

echo "Waiting for Redis..."
while ! nc -z "$REDIS_HOST" 6379; do
  sleep 0.5
done
echo "Redis is available"

echo "Applying migrations..."
python manage.py migrate --noinput

echo "Loading fixtures (if any)..."
python manage.py loaddata initial_data || true

echo "Starting application..."
exec "$@"
