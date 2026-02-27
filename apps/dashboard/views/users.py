from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils.translation import gettext as _

from apps.dashboard.decorators import require_permission
from apps.accounts.models import User


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
