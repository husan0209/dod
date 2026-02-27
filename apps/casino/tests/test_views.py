from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from decimal import Decimal


class CasinoViewsTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='testuser',
            email='test@example.com',
            password='password123'
        )
        self.client.force_login(self.user)

    def test_index_view(self):
        response = self.client.get(reverse('casino:index'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'casino/index.html')

    def test_crash_view(self):
        response = self.client.get(reverse('casino:crash'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'casino/crash.html')

    def test_dice_view(self):
        response = self.client.get(reverse('casino:dice'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'casino/dice.html')

    def test_fairness_view(self):
        response = self.client.get(reverse('casino:fairness'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'casino/fairness.html')

    def test_history_view(self):
        response = self.client.get(reverse('casino:history'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'casino/history.html')
