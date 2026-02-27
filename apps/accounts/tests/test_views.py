from django.test import Client, TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()


class HealthViewTests(TestCase):
    def test_health_returns_ok(self):
        client = Client()
        url = reverse('accounts-health')
        resp = client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"status": "ok"})


class AuthViewTests(TestCase):
    def test_login_page_get(self):
        response = self.client.get(reverse('account_login'))
        self.assertEqual(response.status_code, 200)

    def test_registration_page_get(self):
        response = self.client.get(reverse('account_signup'))
        self.assertEqual(response.status_code, 200)

    def test_profile_authenticated(self):
        user = User.objects.create_user(email='profile@example.com', username='profiletest', password='pass12345')
        self.client.login(email='profile@example.com', password='pass12345')
        response = self.client.get(reverse('account_profile'))
        self.assertEqual(response.status_code, 200)

    def test_profile_unauthenticated_redirect(self):
        response = self.client.get(reverse('account_profile'))
        self.assertEqual(response.status_code, 302)  # redirect to login

    # Add tests for editing profile and notifications if views exist
