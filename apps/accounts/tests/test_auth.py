from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()


class AuthTests(TestCase):
    def test_registration_success(self):
        response = self.client.post(reverse('account_signup'), {
            'email': 'new@example.com',
            'username': 'newuser',
            'password1': 'pass12345',
            'password2': 'pass12345',
        })
        self.assertEqual(response.status_code, 302)  # redirect after signup
        self.assertTrue(User.objects.filter(email='new@example.com').exists())

    def test_registration_duplicate_email_error(self):
        User.objects.create_user(email='dup@example.com', username='dup1', password='pass12345')
        response = self.client.post(reverse('account_signup'), {
            'email': 'dup@example.com',
            'username': 'dup2',
            'password1': 'pass12345',
            'password2': 'pass12345',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'already registered')

    def test_login_correct_password(self):
        User.objects.create_user(email='login@example.com', username='logintest', password='pass12345')
        response = self.client.post(reverse('account_login'), {
            'login': 'login@example.com',
            'password': 'pass12345',
        })
        self.assertEqual(response.status_code, 302)  # redirect after login

    def test_login_wrong_password_error(self):
        User.objects.create_user(email='wrong@example.com', username='wrongtest', password='pass12345')
        response = self.client.post(reverse('account_login'), {
            'login': 'wrong@example.com',
            'password': 'wrongpass',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'incorrect')

    # Add more tests for 2FA, password reset, etc. as per spec
