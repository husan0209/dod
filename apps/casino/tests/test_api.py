import hashlib
import hmac
import time
import uuid
from urllib.parse import urlencode

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse


@override_settings(CASINO_API_SECRET='test-casino-secret-at-least-32-bytes')
class CasinoApiAuthenticationTests(TestCase):
    def setUp(self):
        cache.clear()

    def tearDown(self):
        cache.clear()

    def signed_headers(self, path, request_id=None, timestamp=None, body=b''):
        timestamp = str(timestamp or int(time.time()))
        request_id = request_id or str(uuid.uuid4())
        message = '\n'.join((
            timestamp,
            'GET',
            path,
            hashlib.sha256(body).hexdigest(),
            request_id,
        ))
        signature = hmac.new(
            b'test-casino-secret-at-least-32-bytes', message.encode(), hashlib.sha256
        ).hexdigest()
        return {
            'HTTP_X_CASINO_TIMESTAMP': timestamp,
            'HTTP_X_CASINO_REQUEST_ID': request_id,
            'HTTP_X_CASINO_SIGNATURE': signature,
        }

    def test_unsigned_balance_request_is_rejected(self):
        response = self.client.get(reverse('casino:api_balance'))
        self.assertEqual(response.status_code, 401)

    @override_settings(CASINO_API_SECRET='')
    def test_api_is_disabled_without_a_configured_secret(self):
        response = self.client.get(reverse('casino:api_balance'))

        self.assertEqual(response.status_code, 503)

    def test_valid_signature_is_accepted_once(self):
        query = urlencode({'user_id': str(uuid.uuid4()), 'currency': 'USD'})
        path = f'{reverse("casino:api_balance")}?{query}'
        headers = self.signed_headers(path)

        first = self.client.get(path, **headers)
        replay = self.client.get(path, **headers)

        self.assertEqual(first.status_code, 404)
        self.assertEqual(replay.status_code, 409)

    def test_stale_signature_is_rejected(self):
        path = reverse('casino:api_balance')
        headers = self.signed_headers(path, timestamp=int(time.time()) - 301)

        response = self.client.get(path, **headers)

        self.assertEqual(response.status_code, 401)
