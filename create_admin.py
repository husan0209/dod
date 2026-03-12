#!/usr/bin/env python
"""Create admin superuser for DOD project"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

# Delete existing admin user
User.objects.filter(username='admin').delete()

# Create new admin user
admin = User.objects.create_superuser(
    username='admin',
    email='admin@dod.local',
    password='Admin123!@#'
)

print("✅ Admin user created successfully!")
print(f"Username: admin")
print(f"Password: Admin123!@#")
print(f"Email: admin@dod.local")
