#!/bin/bash

# Скрипт установки и загрузки начальных данных для модуля ставок на спорт

echo "🎯 Установка модуля ставок на спорт..."

# 1. Применить миграции
echo "📝 Применение миграций..."
python manage.py migrate

# 2. Загрузить фиксчеры
echo "📥 Загрузка начальных данных..."
python manage.py loaddata fixtures/sports_initial.json

# 3. Создать системные настройки ставок
echo "⚙️  Создание настроек ставок..."
python manage.py shell << EOF
from apps.sports.models import BetSettings

# Создать или получить единственный объект настроек
settings, created = BetSettings.objects.get_or_create(id=1)
if created:
    print("✅ Настройки ставок созданы")
else:
    print("✅ Настройки ставок уже существуют")
EOF

echo "🎉 Установка завершена!"
echo ""
echo "📖 Документация по использованию:"
echo "   - Список спорта: http://localhost:8000/sports/"
echo "   - Admin панель: http://localhost:8000/admin/"
echo "   - Администратор может:"
echo "     • Создавать события и маркеты"
echo "     • Открывать/закрывать ставки"
echo "     • Рассчитывать события"
echo "     • Отменять ставки"
