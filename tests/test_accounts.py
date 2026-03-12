"""
Unit tests for accounts app.
"""

import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestUserModel:
    """Tests for User model."""

    def test_create_user(self):
        """Test creating a regular user."""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        assert user.username == 'testuser'
        assert user.email == 'test@example.com'
        assert user.check_password('testpass123')
        assert not user.is_staff
        assert not user.is_superuser

    def test_create_superuser(self):
        """Test creating a superuser."""
        user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='admin123'
        )
        assert user.is_staff
        assert user.is_superuser

    def test_user_username_unique(self):
        """Test that usernames must be unique."""
        User.objects.create_user(
            username='duplicate',
            email='first@example.com',
            password='pass123'
        )
        
        with pytest.raises(Exception):  # IntegrityError
            User.objects.create_user(
                username='duplicate',
                email='second@example.com',
                password='pass123'
            )

    def test_user_email_unique(self):
        """Test that emails must be unique."""
        User.objects.create_user(
            username='user1',
            email='duplicate@example.com',
            password='pass123'
        )
        
        with pytest.raises(Exception):  # IntegrityError
            User.objects.create_user(
                username='user2',
                email='duplicate@example.com',
                password='pass123'
            )

    def test_user_str_representation(self):
        """Test user string representation."""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass'
        )
        assert str(user) == 'testuser'

    def test_user_email_verification(self):
        """Test email verification flag."""
        user = User.objects.create_user(
            username='test',
            email='test@example.com',
            password='pass'
        )
        assert not user.is_email_verified  # type: ignore
        
        user.is_email_verified = True  # type: ignore
        user.save()
        assert user.is_email_verified  # type: ignore

    def test_user_2fa_disabled_by_default(self):
        """Test 2FA is disabled by default."""
        user = User.objects.create_user(
            username='test',
            email='test@example.com',
            password='pass'
        )
        
        assert not user.is_2fa_enabled  # type: ignore
        
        user.is_2fa_enabled = True  # type: ignore
        user.two_fa_method = 'totp'  # type: ignore
        user.save()
        
        user.refresh_from_db()
        assert user.is_2fa_enabled  # type: ignore
        assert user.two_fa_method == 'totp'  # type: ignore


@pytest.mark.django_db
class TestUserAuthentication:
    """Tests for user authentication."""

    def test_user_can_login(self, authenticated_client, authenticated_user):
        """Test that authenticated user is logged in."""
        response = authenticated_client.get('/')
        assert response.status_code in (200, 302)

    def test_inactive_user_cannot_login(self, api_client):
        """Test that inactive user cannot login."""
        user = User.objects.create_user(
            username='inactive',
            email='inactive@example.com',
            password='pass123'
        )
        user.is_active = False
        user.save()
        
        success = api_client.login(username='inactive', password='pass123')
        assert not success

    def test_wrong_password_fails(self, api_client):
        """Test that wrong password fails login."""
        User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='correctpass'
        )
        
        success = api_client.login(username='testuser', password='wrongpass')
        assert not success

    def test_nonexistent_user_fails(self, api_client):
        """Test that nonexistent user cannot login."""
        success = api_client.login(username='nonexistent', password='pass')
        assert not success
