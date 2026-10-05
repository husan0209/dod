from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from .services import get_odds_feed, get_prediction_feed


class IntegrationFeedTests(TestCase):
    def setUp(self):
        cache.clear()

    def tearDown(self):
        cache.clear()

    @override_settings(THE_ODDS_API_KEY='')
    def test_odds_feed_uses_explicitly_labeled_demo_data_without_key(self):
        feed = get_odds_feed()

        self.assertEqual(feed['mode'], 'demo')
        self.assertIn('Demo', feed['events'][0]['home'])

    @override_settings(THE_ODDS_API_KEY='test-key', THE_ODDS_API_SPORT='soccer_epl')
    @patch('apps.integrations.services.requests.get')
    def test_odds_feed_fetches_configured_provider(self, get):
        get.return_value = Mock(
            json=Mock(return_value=[{'home_team': 'A', 'away_team': 'B'}]),
            raise_for_status=Mock(),
        )

        feed = get_odds_feed(force_refresh=True)

        self.assertEqual(feed['mode'], 'live')
        self.assertEqual(feed['events'][0]['home'], 'A')
        self.assertEqual(feed['events'][0]['away'], 'B')
        self.assertEqual(get.call_args.kwargs['params']['apiKey'], 'test-key')
        self.assertEqual(get.call_args.kwargs['timeout'], 8)

    @patch('apps.integrations.services.requests.get')
    def test_prediction_feed_maps_only_valid_public_markets(self, get):
        get.return_value = Mock(
            json=Mock(return_value=[
                {
                    'question': 'Will the demo pass?',
                    'probability': 0.73,
                    'url': 'https://manifold.markets/example/demo',
                    'volume': 100,
                    'isResolved': False,
                    'outcomeType': 'BINARY',
                },
                {
                    'question': 'Unsafe external link',
                    'probability': 0.5,
                    'url': 'https://manifold.markets.evil.example/attacker',
                    'isResolved': False,
                    'outcomeType': 'BINARY',
                },
                {
                    'question': 'Resolved market',
                    'probability': 1,
                    'url': 'https://manifold.markets/example/resolved',
                    'isResolved': True,
                    'outcomeType': 'BINARY',
                },
                {
                    'question': 'Not a binary market',
                    'probability': 0.5,
                    'url': 'https://manifold.markets/example/multiple-choice',
                    'isResolved': False,
                    'outcomeType': 'MULTIPLE_CHOICE',
                },
            ]),
            raise_for_status=Mock(),
        )

        feed = get_prediction_feed(force_refresh=True)

        self.assertEqual(feed['mode'], 'live')
        self.assertEqual(len(feed['markets']), 1)
        self.assertEqual(feed['markets'][0]['probability'], 73.0)

    def test_demo_hub_requires_login(self):
        response = self.client.get(reverse('integrations:demo_hub'))

        self.assertEqual(response.status_code, 302)

    @override_settings(THE_ODDS_API_KEY='')
    @patch('apps.integrations.services.requests.get')
    def test_demo_hub_renders_feeds_for_authenticated_user(self, get):
        get.return_value = Mock(
            json=Mock(return_value=[
                {
                    'question': 'Will the demo pass?',
                    'probability': 0.73,
                    'url': 'https://manifold.markets/example/demo',
                    'isResolved': False,
                    'outcomeType': 'BINARY',
                },
            ]),
            raise_for_status=Mock(),
        )
        user = get_user_model().objects.create_user(
            email='integration-test@example.com',
            username='integration-test',
            password='TestPass123!',
        )
        self.client.force_login(user)

        response = self.client.get(reverse('integrations:demo_hub'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ДЕМО-КОЭФФИЦИЕНТЫ')
        self.assertContains(response, 'Will the demo pass?')
        self.assertContains(response, 'Открыть локальный слот')
