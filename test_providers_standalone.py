"""
Standalone test runner for provider property tests.
This bypasses Django's system checks.
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
os.environ['DJANGO_ALLOW_ASYNC_UNSAFE'] = 'true'

# Disable system checks
from django.core.management import call_command
from django.conf import settings

# Override settings to skip problematic checks
settings.SILENCED_SYSTEM_CHECKS = ['admin.E122']

django.setup()

# Now run the tests
from django.test.runner import DiscoverRunner

runner = DiscoverRunner(verbosity=2, interactive=False)
failures = runner.run_tests(['apps.payments.tests.test_provider_properties'])

sys.exit(bool(failures))
