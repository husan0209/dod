from django.test import TestCase

from ..models import Market, Outcome, UserPosition, Trade

from django.contrib.auth import get_user_model

User = get_user_model()


class TradingTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        # TODO: create market, outcome for tests

    def test_trade_creation(self):
        # Placeholder test
        self.assertTrue(True)
