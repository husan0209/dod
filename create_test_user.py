#!/usr/bin/env python
"""Create test user account for DOD project"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

# Delete existing test user if exists
User.objects.filter(username='testuser').delete()

# Create new test user
test_user = User.objects.create_user(
    username='testuser',
    email='testuser@dod.local',
    password='Test123!@#'
)

print("✅ Test user created successfully!")
print(f"Username: testuser")
print(f"Email: testuser@dod.local")
print(f"Password: Test123!@#")
