#!/usr/bin/env python
"""Debug the predictions index error"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from apps.predictions.views import IndexView

User = get_user_model()
testuser = User.objects.get(username='testuser')

# Create request
factory = RequestFactory()
request = factory.get('/predictions/')
request.user = testuser

# Try to get the view
try:
    view = IndexView.as_view()
    response = view(request)
    print(f"✅ IndexView returned status: {response.status_code}")
except Exception as e:
    print(f"❌ Error in IndexView:")
    print(f"   Error type: {type(e).__name__}")
    print(f"   Error message: {str(e)}")
    import traceback
    traceback.print_exc()
