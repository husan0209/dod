import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.predictions.models import MarketCategory

categories_data = [
    ("Политика", "Politics", "politics", "🏛️", "События в мировой политике", "#3498db", 1),
    ("Крипто", "Cryptocurrency", "crypto", "🪙", "Прогнозы о криптовалютах", "#f39c12", 2),
    ("Спорт", "Sports", "sports", "⚽", "Спортивные события и матчи", "#e74c3c", 3),
    ("Технология", "Technology", "technology", "🤖", "Технологические инновации", "#9b59b6", 4),
    ("Мир", "World", "world", "🌍", "Глобальные события", "#16a085", 5),
    ("Экономика", "Economics", "economics", "💹", "Экономические показатели", "#27ae60", 6),
    ("Развлечения", "Entertainment", "entertainment", "🎬", "Кинематография и развлечения", "#e67e22", 7),
    ("Наука", "Science", "science", "🔬", "Научные открытия", "#3498db", 8),
    ("Игры", "Gaming", "gaming", "🎮", "Киберспорт и видеоигры", "#c0392b", 9),
    ("Социум", "Social", "social", "👥", "Социальные события и тренды", "#2980b9", 10),
]

print("📋 Создание категорий маркетов...")
for name, name_en, slug, icon, desc, color, sort in categories_data:
    cat, created = MarketCategory.objects.get_or_create(
        slug=slug,
        defaults={
            'name': name,
            'name_en': name_en,
            'icon': icon,
            'description': desc,
            'color': color,
            'sort_order': sort,
            'is_active': True,
        }
    )
    status = "создана" if created else "уже существует"
    print(f"  ✅ {name} ({icon}) - {status}")

print(f"\n✨ Всего категорий в базе: {MarketCategory.objects.count()}")
