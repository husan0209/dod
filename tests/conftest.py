"""
pytest configuration for DOD project.
"""

import os
import django
import pytest
from django.conf import settings

# Configure Django settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.test")

# Setup Django
django.setup()

@pytest.fixture(scope="session")
def django_db_setup():
    """Override django_db_setup to use test database."""
    settings.DATABASES['default'] = {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'dod_test'),
        'USER': os.getenv('DB_USER', 'dod_test'),
        'PASSWORD': os.getenv('DB_PASSWORD', 'test'),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': '5432',
    }

@pytest.fixture
def api_client():
    """Fixture to provide Django test client."""
    from django.test import Client
    return Client()

@pytest.fixture
def authenticated_user(db):
    """Fixture to create and return an authenticated user."""
    from apps.accounts.models import User
    user = User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )
    return user

@pytest.fixture
def authenticated_client(api_client, authenticated_user):
    """Fixture to provide an authenticated test client."""
    api_client.force_login(authenticated_user)
    return api_client

@pytest.fixture
def admin_user(db):
    """Fixture to create an admin user."""
    from apps.accounts.models import User
    user = User.objects.create_superuser(
        username='admin',
        email='admin@example.com',
        password='admin123'
    )
    return user

@pytest.fixture
def admin_client(api_client, admin_user):
    """Fixture to provide an authenticated admin test client."""
    api_client.force_login(admin_user)
    return api_client

@pytest.mark.django_db
def test_database_connection():
    """Test that database is properly configured."""
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute('SELECT 1')
        assert cursor.fetchone() is not None
