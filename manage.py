#!/usr/bin/env python
import os
import sys
from pathlib import Path

from dotenv import load_dotenv


def main():
    base_dir = Path(__file__).resolve().parent
    load_dotenv(base_dir / '.env')
    if 'test' in sys.argv:
        os.environ.setdefault('CELERY_BROKER_URL', 'memory://')
        os.environ.setdefault('CELERY_RESULT_BACKEND', 'cache+memory://')
        os.environ.setdefault('REDIS_URL', 'redis://localhost:0')
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
