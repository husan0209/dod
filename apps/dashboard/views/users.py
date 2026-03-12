from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils.translation import gettext as _
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST

from apps.dashboard.decorators import require_permission
from apps.accounts.models import User, AdminActionLog, TOTPDevice, BackupCode


@require_permission('users', 'view')
def user_list(request):
    """User management list view"""
    # Get filters
    search = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    kyc_filter = request.GET.get('kyc', '')
    trust_filter = request.GET.get('trust', '')
    registration_method = request.GET.get('registration_method', '')
    sort_by = request.GET.get('sort', '-date_joined')
    
    # Base queryset
    users = User.objects.all()
    
    # Apply filters
    if search:
        users = users.filter(
            Q(email__icontains=search) |
            Q(username__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)
        )
    
    if status_filter:
        if status_filter == 'active':
            users = users.filter(is_active=True)
        elif status_filter == 'inactive':
            users = users.filter(is_active=False)
    
    if kyc_filter:
        users = users.filter(kyc_status=kyc_filter)
    
    if trust_filter:
        users = users.filter(trust_level=int(trust_filter))
    
    if registration_method:
        users = users.filter(registration_method=registration_method)
    
    # Sort
    users = users.order_by(sort_by)
    
    # Pagination
    paginator = Paginator(users, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search': search,
        'status_filter': status_filter,
        'kyc_filter': kyc_filter,
        'trust_filter': trust_filter,
        'registration_method': registration_method,
        'sort_by': sort_by,
    }
    
    return render(request, 'dashboard/users/list.html', context)


@require_permission('users', 'view')
def user_detail(request, user_id):
    """User detail view"""
    user = get_object_or_404(User, id=user_id)
    
    context = {
        'user': user,
    }
    
    return render(request, 'dashboard/users/detail.html', context)


def _log_user_change(*, request, target_user: User, action_type: str, description: str, data_before=None, data_after=None, is_successful: bool = True, error_message: str = ""):
    AdminActionLog.objects.create(
        admin_user=request.user,
        target_user=target_user,
        action_type=action_type,
        module='users',
        action_category=action_type,
        description=description,
        ip_address=request.META.get('REMOTE_ADDR'),
        data_before=data_before,
        data_after=data_after,
        is_successful=is_successful,
        error_message=error_message,
    )


@require_POST
@csrf_protect
@require_permission('users', 'view')
def users_bulk_action(request):
    action = (request.POST.get('action') or '').strip()
    raw_ids = request.POST.getlist('user_ids')
    if not action or not raw_ids:
        messages.error(request, 'Выберите действие и пользователей.')
        return redirect('dashboard:users')

    users_qs = User.objects.filter(id__in=raw_ids)
    target_users = list(users_qs)
    if not target_users:
        messages.error(request, 'Пользователи не найдены.')
        return redirect('dashboard:users')

    admin_profile = getattr(request, 'admin_profile', None) or getattr(request.user, 'admin_profile', None)

    if action in {'ban', 'unban'} and not admin_profile.has_permission('users', 'ban'):
        messages.error(request, 'Недостаточно прав для блокировки.')
        return redirect('dashboard:users')
    if action in {'trust_up'} and not admin_profile.has_permission('users', 'change_trust_level'):
        messages.error(request, 'Недостаточно прав для изменения Trust.')
        return redirect('dashboard:users')

    try:
        with transaction.atomic():
            if action == 'ban':
                for u in target_users:
                    before = {'is_active': u.is_active}
                    if u.is_active:
                        u.is_active = False
                        u.save(update_fields=['is_active', 'updated_at'])
                    after = {'is_active': u.is_active}
                    _log_user_change(
                        request=request,
                        target_user=u,
                        action_type='ban',
                        description=f'Пользователь заблокирован: {u.email}',
                        data_before=before,
                        data_after=after,
                    )
                messages.success(request, f'Заблокировано: {len(target_users)}')
            elif action == 'unban':
                for u in target_users:
                    before = {'is_active': u.is_active}
                    if not u.is_active:
                        u.is_active = True
                        u.save(update_fields=['is_active', 'updated_at'])
                    after = {'is_active': u.is_active}
                    _log_user_change(
                        request=request,
                        target_user=u,
                        action_type='unban',
                        description=f'Пользователь разблокирован: {u.email}',
                        data_before=before,
                        data_after=after,
                    )
                messages.success(request, f'Разблокировано: {len(target_users)}')
            elif action == 'trust_up':
                for u in target_users:
                    before = {'trust_level': u.trust_level}
                    if u.trust_level < 5:
                        u.trust_level = min(5, u.trust_level + 1)
                        u.save(update_fields=['trust_level', 'updated_at'])
                    after = {'trust_level': u.trust_level}
                    _log_user_change(
                        request=request,
                        target_user=u,
                        action_type='trust_up',
                        description=f'Trust повышен: {u.email}',
                        data_before=before,
                        data_after=after,
                    )
                messages.success(request, f'Обновлено Trust: {len(target_users)}')
            else:
                messages.error(request, 'Неизвестное массовое действие.')
    except Exception as e:
        messages.error(request, f'Ошибка выполнения: {e}')

    return redirect(request.META.get('HTTP_REFERER') or 'dashboard:users')


@require_POST
@csrf_protect
@require_permission('users', 'view')
def user_action(request, user_id):
    user = get_object_or_404(User, id=user_id)
    action = (request.POST.get('action') or '').strip()

    admin_profile = getattr(request, 'admin_profile', None) or getattr(request.user, 'admin_profile', None)

    try:
        if action == 'ban':
            if not admin_profile.has_permission('users', 'ban'):
                messages.error(request, 'Недостаточно прав для блокировки.')
                return redirect('dashboard:user_detail', user_id=user.id)
            before = {'is_active': user.is_active}
            user.is_active = False
            user.save(update_fields=['is_active', 'updated_at'])
            after = {'is_active': user.is_active}
            _log_user_change(request=request, target_user=user, action_type='ban', description='Блокировка пользователя', data_before=before, data_after=after)
            messages.success(request, 'Пользователь заблокирован.')

        elif action == 'unban':
            if not admin_profile.has_permission('users', 'ban'):
                messages.error(request, 'Недостаточно прав для разблокировки.')
                return redirect('dashboard:user_detail', user_id=user.id)
            before = {'is_active': user.is_active}
            user.is_active = True
            user.save(update_fields=['is_active', 'updated_at'])
            after = {'is_active': user.is_active}
            _log_user_change(request=request, target_user=user, action_type='unban', description='Разблокировка пользователя', data_before=before, data_after=after)
            messages.success(request, 'Пользователь разблокирован.')

        elif action == 'reset_2fa':
            if not admin_profile.has_permission('users', 'reset_2fa'):
                messages.error(request, 'Недостаточно прав для сброса 2FA.')
                return redirect('dashboard:user_detail', user_id=user.id)
            before = {'is_2fa_enabled': user.is_2fa_enabled, 'two_fa_method': user.two_fa_method}
            TOTPDevice.objects.filter(user=user).delete()
            BackupCode.objects.filter(user=user).delete()
            user.is_2fa_enabled = False
            user.two_fa_method = None
            user.save(update_fields=['is_2fa_enabled', 'two_fa_method', 'updated_at'])
            after = {'is_2fa_enabled': user.is_2fa_enabled, 'two_fa_method': user.two_fa_method}
            _log_user_change(request=request, target_user=user, action_type='reset_2fa', description='Сброс 2FA', data_before=before, data_after=after)
            messages.success(request, '2FA сброшена.')

        elif action == 'set_trust':
            if not admin_profile.has_permission('users', 'change_trust_level'):
                messages.error(request, 'Недостаточно прав для изменения Trust.')
                return redirect('dashboard:user_detail', user_id=user.id)
            raw_level = (request.POST.get('trust_level') or '').strip()
            level = int(raw_level)
            if level not in {1, 2, 3, 4, 5}:
                raise ValueError('Invalid trust level')
            before = {'trust_level': user.trust_level}
            user.trust_level = level
            user.save(update_fields=['trust_level', 'updated_at'])
            after = {'trust_level': user.trust_level}
            _log_user_change(request=request, target_user=user, action_type='set_trust', description=f'Установка Trust: {level}', data_before=before, data_after=after)
            messages.success(request, 'Trust обновлён.')

        elif action == 'adjust_balance':
            if not admin_profile.has_permission('users', 'change_balance'):
                messages.error(request, 'Недостаточно прав для изменения баланса.')
                return redirect('dashboard:user_detail', user_id=user.id)
            raw_amount = (request.POST.get('amount') or '').strip().replace(',', '.')
            mode = (request.POST.get('mode') or 'credit').strip()
            reason = (request.POST.get('reason') or '').strip()[:500]
            if not raw_amount:
                raise ValueError('Amount is required')
            amount = Decimal(raw_amount)
            if amount <= 0:
                raise ValueError('Amount must be positive')
            before = {'balance': str(user.balance)}
            with transaction.atomic():
                user_locked = User.objects.select_for_update().get(id=user.id)
                if mode == 'credit':
                    user_locked.balance = user_locked.balance + amount
                elif mode == 'debit':
                    if user_locked.balance < amount:
                        raise ValueError('Недостаточно средств для списания')
                    user_locked.balance = user_locked.balance - amount
                else:
                    raise ValueError('Invalid mode')
                user_locked.save(update_fields=['balance', 'updated_at'])
                user.refresh_from_db(fields=['balance'])
            after = {'balance': str(user.balance)}
            _log_user_change(
                request=request,
                target_user=user,
                action_type='adjust_balance',
                description=f'Корректировка баланса ({mode}): {amount}. {reason}'.strip(),
                data_before=before,
                data_after=after,
            )
            messages.success(request, 'Баланс обновлён.')

        else:
            messages.error(request, 'Неизвестное действие.')

    except (ValueError, InvalidOperation) as e:
        messages.error(request, str(e) or 'Неверные данные.')
        _log_user_change(
            request=request,
            target_user=user,
            action_type=action or 'unknown',
            description='Ошибка выполнения действия',
            is_successful=False,
            error_message=str(e),
        )
    except Exception as e:
        messages.error(request, 'Ошибка выполнения действия.')
        _log_user_change(
            request=request,
            target_user=user,
            action_type=action or 'unknown',
            description='Ошибка выполнения действия',
            is_successful=False,
            error_message=str(e),
        )

    return redirect('dashboard:user_detail', user_id=user.id)
