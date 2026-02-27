from django.test import TestCase, Client
from apps.dashboard.models import AdminRole, AdminProfile
from apps.accounts.models import User


class ViewTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.superadmin_role = AdminRole.objects.create(
            name='Superadmin', 
            slug='superadmin', 
            permissions={'dashboard': {'view': True}, 'users': {'view': True}}
        )
        self.user = User.objects.create_user(
            email='test@example.com', 
            username='test', 
            password='pass'
        )
        self.user.is_staff = True
        self.user.save()
        self.admin_profile = AdminProfile.objects.create(
            user=self.user, 
            role=self.superadmin_role
        )

    def test_dashboard_requires_login(self):
        response = self.client.get('/admin-panel/')
        self.assertEqual(response.status_code, 302)

    def test_dashboard_with_permission(self):
        self.client.force_login(self.user)
        response = self.client.get('/admin-panel/')
        self.assertEqual(response.status_code, 200)
