#!/usr/bin/env python
"""Debug the predictions index error with template rendering"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from django.test import RequestFactory, Client
from django.contrib.auth import get_user_model
from apps.predictions.views import IndexView

User = get_user_model()
testuser = User.objects.get(username='testuser')

# Create client and login
client = Client()
client.force_login(testuser)

# Try to access the page
try:
    response = client.get('/predictions/')
    print(f"✅ IndexView response status: {response.status_code}")
    if response.status_code >= 400:
        print(f"Content preview: {response.content[:500]}")
except Exception as e:
    print(f"❌ Error accessing /predictions/:")
    print(f"   Error type: {type(e).__name__}")
    print(f"   Error message: {str(e)}")
    import traceback
    traceback.print_exc()
