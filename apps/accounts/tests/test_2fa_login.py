from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User


class TwoFactorLoginTests(TestCase):
    def test_login_with_enabled_2fa_requires_challenge_before_authentication(self):
        user = User.objects.create_user(
            email='twofa@example.com',
            username='twofa',
            password='SecurePass123!',
        )
        user.is_2fa_enabled = True
        user.save(update_fields=['is_2fa_enabled'])

        response = self.client.post(reverse('accounts:login'), {
            'username': user.email,
            'password': 'SecurePass123!',
        })

        self.assertRedirects(
            response, reverse('accounts:verify_2fa'), fetch_redirect_response=False
        )
        self.assertEqual(str(self.client.session['2fa_user_id']), str(user.pk))
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_login_clears_an_unfinished_challenge_for_another_account(self):
        pending_user = User.objects.create_user(
            email='pending@example.com',
            username='pending',
            password='SecurePass123!',
            is_2fa_enabled=True,
        )
        regular_user = User.objects.create_user(
            email='regular@example.com',
            username='regular',
            password='RegularPass123!',
        )
        session = self.client.session
        session['2fa_user_id'] = str(pending_user.pk)
        session['admin_2fa_verified'] = True
        session.save()

        response = self.client.post(reverse('accounts:login'), {
            'username': regular_user.email,
            'password': 'RegularPass123!',
        })

        self.assertEqual(response.status_code, 302)
        self.assertEqual(str(self.client.session['_auth_user_id']), str(regular_user.pk))
        self.assertNotIn('2fa_user_id', self.client.session)
        self.assertNotIn('admin_2fa_verified', self.client.session)

    @patch('apps.accounts.views.OTPService.verify_totp_code', return_value=(True, None))
    def test_successful_2fa_challenge_marks_admin_session_verified(self, verify_totp):
        user = User.objects.create_user(
            email='admin2fa@example.com',
            username='admin2fa',
            password='SecurePass123!',
            is_staff=True,
            is_2fa_enabled=True,
        )
        session = self.client.session
        session['2fa_user_id'] = str(user.pk)
        session.save()

        response = self.client.post(reverse('accounts:verify_2fa'), {
            'totp_code': '123456',
        })

        self.assertEqual(response.status_code, 302)
        self.assertTrue(self.client.session['admin_2fa_verified'])
        self.assertEqual(str(self.client.session['_auth_user_id']), str(user.pk))
        verify_totp.assert_called_once()
