from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods

from apps.dashboard.decorators import require_permission
from apps.accounts.forms import Verify2FAForm
from apps.accounts.services.otp_service import OTPService
from apps.accounts.models import AdminActionLog


def get_has_permission_fn(admin_profile):
    """Helper function to check permissions in templates"""
    def has_permission(permission_string):
        if not admin_profile or not permission_string:
            return False
        if '.' in str(permission_string):
            module, action = str(permission_string).split('.', 1)
            return admin_profile.has_permission(module, action)
        return False
    return has_permission


@login_required
def dashboard_view(request):
    """Main dashboard view - for both admin and regular users"""
    # Check if user is admin/staff
    if not request.user.is_staff and not request.user.is_superuser:
        # For regular users, redirect to casino home
        return redirect('casino:index')
    
    # For admin users, check permissions
    admin_profile = getattr(request.user, 'admin_profile', None)
    if not admin_profile:
        try:
            admin_profile = request.user.admin_profile
        except Exception:
            from django.http import HttpResponseForbidden
            from django.utils.translation import gettext as _
            return HttpResponseForbidden(_('No admin profile'))
    
    if not admin_profile.has_permission('dashboard', 'view'):
        from django.http import HttpResponseForbidden
        from django.utils.translation import gettext as _
        return HttpResponseForbidden(_('Insufficient rights: dashboard.view'))
    
    context = {
        'page_title': 'Дашборд',
        'has_permission': get_has_permission_fn(admin_profile),
    }
    return render(request, 'dashboard/main/dashboard.html', context)


@login_required
@csrf_protect
@require_http_methods(["GET", "POST"])
def verify_2fa_view(request):
    if not request.user.is_staff:
        return redirect('accounts:login')

    if not request.user.is_2fa_enabled:
        messages.error(request, 'Для входа в админ-панель нужно включить 2FA.')
        return redirect('accounts:setup_2fa')

    if request.method == 'POST':
        form = Verify2FAForm(request.POST)
        if form.is_valid():
            totp_code = form.cleaned_data.get('totp_code')
            backup_code = form.cleaned_data.get('backup_code')

            verified = False
            error = None
            if totp_code:
                verified, error = OTPService.verify_totp_code(request.user, totp_code)
            elif backup_code:
                verified, error = OTPService.verify_backup_code(request.user, backup_code)

            if verified:
                request.session['admin_2fa_verified'] = True
                AdminActionLog.objects.create(
                    admin_user=request.user,
                    action_type='admin_2fa_verified',
                    module='security',
                    action_category='2fa',
                    description='Admin 2FA verification passed',
                    ip_address=request.META.get('REMOTE_ADDR'),
                    is_successful=True,
                )
                return redirect('dashboard:dashboard')

            AdminActionLog.objects.create(
                admin_user=request.user,
                action_type='admin_2fa_failed',
                module='security',
                action_category='2fa',
                description='Admin 2FA verification failed',
                ip_address=request.META.get('REMOTE_ADDR'),
                is_successful=False,
                error_message=error or 'Invalid code',
            )
            messages.error(request, error or 'Неверный код')
    else:
        form = Verify2FAForm()

    return render(request, 'dashboard/verify_2fa.html', {'form': form})


@login_required
@require_permission('logs', 'view_admin_logs')
def logs_view(request):
    module = (request.GET.get('module') or '').strip()
    is_successful = (request.GET.get('ok') or '').strip()
    admin_id = request.GET.get('admin')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')

    qs = AdminActionLog.objects.select_related('admin_user', 'target_user').order_by('-created_at')
    
    if module:
        qs = qs.filter(module=module)
    if is_successful in {'1', '0'}:
        qs = qs.filter(is_successful=(is_successful == '1'))
    if admin_id:
        qs = qs.filter(admin_user_id=admin_id)
    if date_from:
        qs = qs.filter(created_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(created_at__date__lte=date_to)

    paginator = Paginator(qs, 50)
    page_obj = paginator.get_page(request.GET.get('page'))

    # For filter dropdown
    admins = User.objects.filter(is_staff=True).only('id', 'username')

    context = {
        'page_obj': page_obj,
        'module_filter': module,
        'ok_filter': is_successful,
        'admin_filter': admin_id,
        'date_from_filter': date_from,
        'date_to_filter': date_to,
        'admins': admins,
    }
    return render(request, 'dashboard/logs/overview.html', context)


@login_required
@require_permission('logs', 'view_admin_logs')
def log_detail(request, log_id):
    """Detailed view of an admin action log."""
    from django.shortcuts import get_object_or_404
    log = get_object_or_404(AdminActionLog, id=log_id)
    return render(request, 'dashboard/logs/log_detail.html', {'log': log})
