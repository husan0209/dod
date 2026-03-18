import json
import os
from django.core.management.base import BaseCommand
from apps.casino.models import GameType
from django.conf import settings

class Command(BaseCommand):
    help = 'Load games configuration from games-config.json'

    def handle(self, *args, **options):
        # games-config.json is located in frontend/public of the source project
        config_path = r"D:\casino-full_stack\frontend\public\games-config.json"
        
        if not os.path.exists(config_path):
            self.stdout.write(self.style.ERROR(f'Config file not found: {config_path}'))
            return

        with open(config_path, 'r', encoding='utf-8') as f:
            games_data = json.load(f)

        created_count = 0
        updated_count = 0

        for game in games_data:
            game_code = game['id']
            # Only ViperPro and Canada games
            if game['type'] not in ['viperpro', 'canada']:
                continue

            defaults = {
                'name': game['name'],
                'name_en': game['name'],
                'description': game.get('description', ''),
                'icon': 'gamepad', # Use a default icon
                'house_edge': 100 - game.get('rtp', 96.0),
                'rtp': game.get('rtp', 96.0),
                'min_bet': game.get('minBet', 0.10),
                'max_bet': game.get('maxBet', 10000),
                'max_win_multiplier': 1000, # Default
                'is_active': game.get('isActive', True),
                'is_popular': game.get('isPopular', False),
                'is_new': game.get('isNew', False),
            }

            obj, created = GameType.objects.update_or_create(
                code=game_code,
                defaults=defaults
            )

            # Note: We need to handle thumbnail separately because it's an ImageField.
            # Usually ImageField expects a file path relative to MEDIA_ROOT. 
            # If the static games provide thumbnails in static/, we might need a custom approach or just a char field. 
            # We'll set a custom attribute or just update the thumbnail later if needed.
            
            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(self.style.SUCCESS(f'Successfully loaded games. Created: {created_count}, Updated: {updated_count}'))
