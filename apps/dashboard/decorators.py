import functools
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.urls import reverse
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


def require_permission(module, action):
    """
    Decorator to check admin permission.

    Usage:
    @require_permission('users', 'edit')
    def edit_user_view(request, user_id):
        ...
    """
    def decorator(view_func):
        @functools.wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Get admin_profile from request or user
            admin_profile = getattr(request, 'admin_profile', None)
            if not admin_profile:
                try:
                    admin_profile = request.user.admin_profile
                except Exception:
                    return HttpResponseForbidden(_('No admin profile'))
            
            request.admin_profile = admin_profile

            if not admin_profile.has_permission(module, action):
                AdminActionLog.objects.create(
                    admin_user=request.user,
                    action_type='permission_denied',
                    module=module,
                    action_category='permission',
                    description=f'Denied: {module}.{action}',
                    ip_address=get_client_ip(request),
                    is_successful=False,
                )
                return HttpResponseForbidden(
                    _(f'Insufficient rights: {module}.{action}')
                )

            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_role_level(min_level):
    """
    Decorator to check minimum role level.

    Usage:
    @require_role_level(50)  # Only admin+
    def dangerous_action(request):
        ...
    """
    def decorator(view_func):
        @functools.wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Get admin_profile from request or user
            admin_profile = getattr(request, 'admin_profile', None)
            if not admin_profile:
                try:
                    admin_profile = request.user.admin_profile
                except Exception:
                    return HttpResponseForbidden()
            
            request.admin_profile = admin_profile

            if admin_profile.role.level < min_level:
                return HttpResponseForbidden(
                    _('Insufficient access level')
                )

            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
