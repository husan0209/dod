from django.test import TestCase, Client
from apps.dashboard.models import AdminRole, AdminProfile
from apps.accounts.models import User
from django.urls import reverse


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
        self.user.is_2fa_enabled = True
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
        session = self.client.session
        session['admin_2fa_verified'] = True
        session.save()
        response = self.client.get('/admin-panel/')
        self.assertEqual(response.status_code, 200)

    def test_dashboard_requires_2fa_verification(self):
        self.client.force_login(self.user)

        response = self.client.get('/admin-panel/')

        self.assertRedirects(response, '/admin-panel/verify-2fa/', fetch_redirect_response=False)

    def test_dashboard_requires_2fa_to_remain_enabled(self):
        self.client.force_login(self.user)
        session = self.client.session
        session['admin_2fa_verified'] = True
        session.save()
        self.user.is_2fa_enabled = False
        self.user.save(update_fields=['is_2fa_enabled'])

        response = self.client.get('/admin-panel/')

        self.assertRedirects(response, '/admin-panel/verify-2fa/', fetch_redirect_response=False)

    def test_settings_view_permission_cannot_update_settings(self):
        role = AdminRole.objects.create(
            name='Settings viewer',
            slug='settings-viewer',
            permissions={'settings': {'view': True}},
        )
        user = User.objects.create_user(
            email='viewer@example.com',
            username='viewer',
            password='pass',
            is_staff=True,
            is_2fa_enabled=True,
        )
        AdminProfile.objects.create(user=user, role=role)
        self.client.force_login(user)
        session = self.client.session
        session['admin_2fa_verified'] = True
        session.save()

        get_response = self.client.get(reverse('dashboard:platform_settings'))
        post_response = self.client.post(
            reverse('dashboard:platform_settings'),
            {'site_name': 'Unauthorized change'},
        )

        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(post_response.status_code, 403)
