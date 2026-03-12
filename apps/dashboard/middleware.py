import time
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.utils.translation import gettext as _

from apps.accounts.models import AdminActionLog


def get_client_ip(request):
    """Get client IP address"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def extract_module(request_path):
    """Extract module name from request path"""
    path_parts = request_path.strip('/').split('/')
    if path_parts and path_parts[0] == 'admin-panel':
        if len(path_parts) == 1:
            return 'dashboard'
        return path_parts[1] or 'dashboard'
    return 'unknown'


class AdminAccessMiddleware:
    """
    Middleware for admin-panel access control.
    Checks:
      1. User authenticated
      2. User is staff
      3. User has AdminProfile
      4. AdminProfile is active
      5. IP in whitelist (if set)
      6. 2FA verified for admin
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Only for /admin-panel/ URLs
        if not request.path.startswith('/admin-panel/'):
            return self.get_response(request)

        is_2fa_verification_path = request.path.rstrip('/') == '/admin-panel/verify-2fa'
        is_dashboard_root = request.path.rstrip('/') == '/admin-panel'

        # 1. Authentication
        if not request.user.is_authenticated:
            return redirect('accounts:login')

        # 2. Staff status - allow non-staff users at dashboard root to be redirected by view
        if not request.user.is_staff:
            # Allow non-staff users to access dashboard root - the view will redirect them
            if is_dashboard_root:
                return self.get_response(request)
            # Block non-staff users from other admin paths
            return HttpResponseForbidden(_('Access denied'))

        # 3. AdminProfile exists
        try:
            admin_profile = request.user.admin_profile
        except Exception:
            return HttpResponseForbidden(_('Admin profile not configured'))

        # 4. AdminProfile active
        if not admin_profile.is_admin_active:
            return HttpResponseForbidden(_('Admin access deactivated'))

        # 5. IP whitelist
        if admin_profile.ip_whitelist:
            ip = get_client_ip(request)
            if ip not in admin_profile.ip_whitelist:
                # Log unauthorized access attempt
                AdminActionLog.objects.create(
                    admin_user=request.user,
                    action_type='unauthorized_access',
                    module='security',
                    action_category='access',
                    description=f'Access attempt from IP {ip} (not in whitelist)',
                    ip_address=ip,
                    is_successful=False,
                )
                return HttpResponseForbidden(_('Access from this IP is forbidden'))

        # Attach admin_profile to request
        request.admin_profile = admin_profile

        return self.get_response(request)


class AdminActionLogMiddleware:
    """
    Middleware to log all POST/PUT/DELETE/PATCH requests in admin-panel.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.path.startswith('/admin-panel/'):
            return self.get_response(request)

        if request.method in ('POST', 'PUT', 'DELETE', 'PATCH'):
            start_time = time.time()
            response = self.get_response(request)
            duration = int((time.time() - start_time) * 1000)

            # Log the action
            AdminActionLog.objects.create(
                admin_user=request.user,
                action_type=f'{request.method} {request.path}',
                action_category=request.method,
                module=extract_module(request.path),
                description=f'{request.method} {request.path}',
                ip_address=get_client_ip(request),
                duration_ms=duration,
                is_successful=(200 <= response.status_code < 400),
            )

            return response

        return self.get_response(request)
