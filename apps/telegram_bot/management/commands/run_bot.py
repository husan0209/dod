"""
Management command to run the Telegram bot.
"""

from django.core.management.base import BaseCommand
from apps.telegram_bot.bot import run_bot


class Command(BaseCommand):
    help = 'Run the Telegram bot in polling mode'

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Starting Telegram bot...')
        )
        run_bot()
