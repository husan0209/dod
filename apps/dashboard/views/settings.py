from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db import models
from django.utils.text import slugify

from apps.core.models import PlatformSettings, Banner, Promotion, StaticPage
from apps.dashboard.models import AdminRole
from apps.dashboard.decorators import require_permission


@login_required
@require_permission('settings', 'view')
def platform_settings(request):
    """Global platform settings view."""
    settings = PlatformSettings.get_settings()
    
    if request.method == 'POST':
        # Simple implementation for saving settings
        settings.site_name = request.POST.get('site_name', settings.site_name)
        settings.is_maintenance_mode = request.POST.get('is_maintenance_mode') == 'on'
        settings.maintenance_message = request.POST.get('maintenance_message', settings.maintenance_message)
        settings.referral_commission_percent = request.POST.get('referral_commission', settings.referral_commission_percent)
        settings.min_withdrawal_usd = request.POST.get('min_withdrawal', settings.min_withdrawal_usd)
        settings.require_kyc_for_withdrawal = request.POST.get('require_kyc') == 'on'
        settings.support_email = request.POST.get('support_email', settings.support_email)
        settings.telegram_support_link = request.POST.get('telegram_support', settings.telegram_support_link)
        
        settings.save()

        messages.success(request, 'Настройки успешно сохранены')
        return redirect('dashboard:platform_settings')

    return render(request, 'dashboard/settings/platform_settings.html', {
        'settings': settings
    })


# --- Banners ---

@login_required
@require_permission('content', 'view')
def banners_list(request):
    banners = Banner.objects.all()
    return render(request, 'dashboard/content/banners_list.html', {'banners': banners})


@login_required
@require_permission('content', 'edit')
def banner_create(request):
    if request.method == 'POST':
        # Hand-handle file upload and fields
        Banner.objects.create(
            title=request.POST.get('title'),
            subtitle=request.POST.get('subtitle', ''),
            image=request.FILES.get('image'),
            link=request.POST.get('link', ''),
            location=request.POST.get('location', 'main'),
            is_active=request.POST.get('is_active') == 'on',
            sort_order=request.POST.get('sort_order', 0)
        )
        messages.success(request, 'Баннер создан')
        return redirect('dashboard:banners_list')
    return render(request, 'dashboard/content/banner_form.html')


# --- Promotions ---

@login_required
@require_permission('content', 'view')
def promotions_list(request):
    promotions = Promotion.objects.all()
    return render(request, 'dashboard/content/promotions_list.html', {'promotions': promotions})


# --- Static Pages ---

@login_required
@require_permission('content', 'view')
def static_pages_list(request):
    pages = StaticPage.objects.all()
    return render(request, 'dashboard/content/static_pages_list.html', {'pages': pages})


@login_required
@require_permission('content', 'edit')
def static_page_edit(request, page_id):
    page = get_object_or_404(StaticPage, id=page_id)
    if request.method == 'POST':
        page.title = request.POST.get('title')
        page.content = request.POST.get('content')
        page.is_active = request.POST.get('is_active') == 'on'
        page.save()
        messages.success(request, f'Страница "{page.title}" сохранена')
        return redirect('dashboard:static_pages_list')
    return render(request, 'dashboard/content/static_page_form.html', {'page': page})


# --- Admin Roles ---

@login_required
@require_permission('settings', 'view')
def roles_list(request):
    roles = AdminRole.objects.all().order_by('-level')
    return render(request, 'dashboard/settings/roles_list.html', {'roles': roles})


@login_required
@require_permission('settings', 'edit')
def role_detail(request, role_id):
    role = get_object_or_404(AdminRole, id=role_id)
    if request.method == 'POST':
        # Simple placeholder for permission updates
        messages.info(request, 'Обновление прав в разработке')
        return redirect('dashboard:roles_list')
    return render(request, 'dashboard/settings/role_detail.html', {'role': role})
