import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings.development'

import django
django.setup()

from django.test import RequestFactory
from apps.casino.views import index
from apps.accounts.models import User
import traceback

factory = RequestFactory()
request = factory.get('/casino/')
request.user = User.objects.first()

if not request.user:
    print('No user found')
else:
    print(f'User: {request.user.email}')
    try:
        response = index(request)
        print(f'Response status: {response.status_code}')
    except Exception as e:
        print(f'Error: {type(e).__name__}: {e}')
        traceback.print_exc()
