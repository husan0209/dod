from django.test import TestCase
from apps.dashboard.models import AdminRole, AdminProfile
from apps.accounts.models import User


class PermissionTestCase(TestCase):
    def setUp(self):
        self.superadmin_role = AdminRole.objects.create(
            name='Superadmin', 
            slug='superadmin', 
            permissions={'dashboard': {'view': True}}
        )
        self.user = User.objects.create_user(
            email='test@example.com', 
            username='test', 
            password='pass'
        )
        self.admin_profile = AdminProfile.objects.create(
            user=self.user, 
            role=self.superadmin_role
        )

    def test_superadmin_has_permission(self):
        self.assertTrue(self.admin_profile.has_permission('dashboard', 'view'))

    def test_non_superadmin_without_permission(self):
        role = AdminRole.objects.create(
            name='Test', 
            slug='test', 
            permissions={}
        )
        other_user = User.objects.create_user(
            email='test2@example.com',
            username='test2',
            password='pass'
        )
        profile = AdminProfile.objects.create(
            user=other_user,
            role=role
        )
        self.assertFalse(profile.has_permission('dashboard', 'view'))
