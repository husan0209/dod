from django.test import TestCase
from django.db import IntegrityError
from django.utils import timezone

from apps.accounts.models import (
    User,
    EmailVerification,
    PhoneVerification,
    BackupCode,
)


class UserModelTests(TestCase):
    def test_create_user_generates_referral_code(self):
        user = User.objects.create_user(email='test@example.com', username='tester', password='pass12345')
        self.assertTrue(user.referral_code)
        self.assertEqual(user.email, 'test@example.com')

    def test_balance_non_negative_constraint(self):
        user = User.objects.create_user(email='b@example.com', username='balance', password='pass12345')
        user.balance = -1
        with self.assertRaises(Exception):
            user.save()

    def test_user_is_email_verified_default_false(self):
        user = User.objects.create_user(email='email@example.com', username='emailtest', password='pass12345')
        self.assertFalse(user.is_email_verified)

    def test_user_is_phone_verified_default_false(self):
        user = User.objects.create_user(email='phone@example.com', username='phonetest', password='pass12345')
        self.assertFalse(user.is_phone_verified)

    def test_user_check_password_correct(self):
        user = User.objects.create_user(email='check@example.com', username='checktest', password='pass12345')
        self.assertTrue(user.check_password('pass12345'))

    def test_user_check_password_wrong(self):
        user = User.objects.create_user(email='wrong@example.com', username='wrongtest', password='pass12345')
        self.assertFalse(user.check_password('wrongpass'))

    def test_user_unique_email(self):
        User.objects.create_user(email='unique@example.com', username='unique1', password='pass12345')
        with self.assertRaises(IntegrityError):
            User.objects.create_user(email='unique@example.com', username='unique2', password='pass12345')

    def test_user_unique_username(self):
        User.objects.create_user(email='u1@example.com', username='uniqueuser', password='pass12345')
        with self.assertRaises(IntegrityError):
            User.objects.create_user(email='u2@example.com', username='uniqueuser', password='pass12345')

    def test_user_update_last_login(self):
        user = User.objects.create_user(email='login@example.com', username='logintest', password='pass12345')
        old_login = user.last_login
        user.update_last_login()
        user.refresh_from_db()
        self.assertNotEqual(user.last_login, old_login)

    def test_user_2fa_fields_default(self):
        user = User.objects.create_user(email='2fa@example.com', username='2fatest', password='pass12345')
        self.assertFalse(user.is_2fa_enabled)
        self.assertIsNone(user.two_fa_method)


class VerificationModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='v@example.com', username='verifier', password='pass12345')

    def test_email_verification_validity(self):
        token = EmailVerification.objects.create(user=self.user, email=self.user.email, token='abc')
        self.assertTrue(token.is_valid())

    def test_phone_verification_not_used_by_default(self):
        pv = PhoneVerification.objects.create(user=self.user, phone='+10000000000', code='123456')
        self.assertFalse(pv.is_used)

    def test_backup_code_hashing(self):
        bc = BackupCode.objects.create(user=self.user)
        bc.set_plain_code('123456')
        self.assertNotEqual(bc.code, '123456')
