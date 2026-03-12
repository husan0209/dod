from django.test import TestCase, Client
from apps.dashboard.models import AdminRole, AdminProfile
from apps.accounts.models import User


class AnalyticsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
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
        self.user.is_staff = True
        self.user.is_2fa_enabled = True
        self.user.save()
        self.admin_profile = AdminProfile.objects.create(
            user=self.user, 
            role=self.superadmin_role
        )

    def test_stats_view_with_permission(self):
        self.client.force_login(self.user)
        session = self.client.session
        session['admin_2fa_verified'] = True
        session.save()
        response = self.client.get('/admin-panel/api/stats/')
        self.assertEqual(response.status_code, 200)
