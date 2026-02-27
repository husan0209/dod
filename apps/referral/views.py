from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Sum, Count, Q
from django.utils.timezone import now
from datetime import timedelta
from decimal import Decimal

from .models import *
from .services.commission_service import CommissionService


@login_required
def dashboard(request):
    """Партнёрская панель - дашборд."""
    profile = request.user.partner_profile

    # Сводка
    total_balance = profile.balance
    total_referrals = profile.total_referrals
    monthly_ggr = profile.monthly_ggr
    monthly_earned = profile.monthly_earned

    # Текущий уровень и прогресс
    current_tier = profile.tier
    next_tier = PartnerTier.objects.filter(
        sort_order__gt=current_tier.sort_order,
        is_active=True
    ).order_by('sort_order').first()

    progress_percent = 0
    progress_text = ""
    if next_tier:
        active_refs = Referral.objects.filter(
            partner=request.user,
            is_qualified=True,
            level=1,
            status__in=['active', 'deposited'],
        ).count()
        progress_refs = min(active_refs / next_tier.min_referrals * 50, 50) if next_tier.min_referrals > 0 else 50
        progress_ggr = min(profile.monthly_ggr / next_tier.min_monthly_ggr * 50, 50) if next_tier.min_monthly_ggr > 0 else 50
        progress_percent = int(progress_refs + progress_ggr)
        progress_text = f"Нужно: {next_tier.min_referrals} рефералов (у вас: {active_refs}) + ${next_tier.min_monthly_ggr} GGR/мес (${profile.monthly_ggr})"

    # Последние рефералы
    recent_referrals = Referral.objects.filter(
        partner=request.user,
        level=1
    ).select_related('referral').order_by('-created_at')[:5]

    # Последние комиссии
    recent_commissions = Commission.objects.filter(
        partner=request.user
    ).select_related('referral__referral').order_by('-created_at')[:5]

    # График дохода (упрощённо, последние 30 дней)
    earnings_chart = []
    for i in range(30):
        date = now().date() - timedelta(days=29-i)
        daily_earned = Commission.objects.filter(
            partner=request.user,
            period_start=date,
            status='approved'
        ).aggregate(total=Sum('net_amount'))['total'] or 0
        earnings_chart.append({'date': date.strftime('%d.%m'), 'amount': float(daily_earned)})

    context = {
        'profile': profile,
        'total_balance': total_balance,
        'total_referrals': total_referrals,
        'monthly_ggr': monthly_ggr,
        'monthly_earned': monthly_earned,
        'current_tier': current_tier,
        'next_tier': next_tier,
        'progress_percent': progress_percent,
        'progress_text': progress_text,
        'recent_referrals': recent_referrals,
        'recent_commissions': recent_commissions,
        'earnings_chart': earnings_chart,
    }

    return render(request, 'referral/dashboard.html', context)


@login_required
def referrals(request):
    """Список рефералов."""
    profile = request.user.partner_profile

    # Фильтры
    status_filter = request.GET.get('status', '')
    level_filter = request.GET.get('level', '1')
    search = request.GET.get('search', '')

    referrals_query = Referral.objects.filter(
        partner=request.user
    ).select_related('referral', 'promo_link')

    if status_filter:
        referrals_query = referrals_query.filter(status=status_filter)

    if level_filter != 'all':
        referrals_query = referrals_query.filter(level=level_filter)

    if search:
        referrals_query = referrals_query.filter(
            Q(referral__username__icontains=search) |
            Q(referral__email__icontains=search)
        )

    referrals_list = referrals_query.order_by('-created_at')

    # Статистика
    total_count = referrals_list.count()
    deposited_count = referrals_list.filter(total_deposits__gt=0).count()
    active_count = referrals_list.filter(is_active=True).count()

    context = {
        'referrals': referrals_list,
        'total_count': total_count,
        'deposited_count': deposited_count,
        'active_count': active_count,
        'status_filter': status_filter,
        'level_filter': level_filter,
        'search': search,
    }

    return render(request, 'referral/referrals.html', context)


@login_required
def commissions(request):
    """История комиссий."""
    commissions_list = Commission.objects.filter(
        partner=request.user
    ).select_related('referral__referral').order_by('-created_at')

    context = {
        'commissions': commissions_list,
    }

    return render(request, 'referral/commissions.html', context)


@login_required
def payouts(request):
    """Выплаты партнёру."""
    payouts_list = PartnerPayout.objects.filter(
        partner=request.user
    ).order_by('-created_at')

    if request.method == 'POST':
        amount = Decimal(request.POST.get('amount', '0'))
        payout_method = request.POST.get('payout_method')
        payout_details = request.POST.get('payout_details', '')

        try:
            payout = CommissionService.process_payout_request(
                request.user, amount, payout_method, payout_details
            )
            messages.success(request, 'Запрос на выплату создан.')
            return redirect('referral:payouts')
        except ValueError as e:
            messages.error(request, str(e))

    context = {
        'payouts': payouts_list,
        'profile': request.user.partner_profile,
    }

    return render(request, 'referral/payouts.html', context)


@login_required
def promo(request):
    """Промо-материалы."""
    promo_links = PromoLink.objects.filter(
        partner=request.user
    ).order_by('-created_at')

    if request.method == 'POST':
        name = request.POST.get('name')
        slug = request.POST.get('slug')
        utm_source = request.POST.get('utm_source')
        utm_medium = request.POST.get('utm_medium')
        utm_campaign = request.POST.get('utm_campaign')

        PromoLink.objects.create(
            partner=request.user,
            name=name,
            slug=slug,
            utm_source=utm_source,
            utm_medium=utm_medium,
            utm_campaign=utm_campaign,
        )
        messages.success(request, 'Промо-ссылка создана.')
        return redirect('referral:promo')

    context = {
        'promo_links': promo_links,
    }

    return render(request, 'referral/promo.html', context)


@login_required
def stats(request):
    """Детальная статистика."""
    profile = request.user.partner_profile

    # Показатели
    total_earned = profile.total_earned
    total_withdrawn = profile.total_withdrawn
    balance = profile.balance
    total_referrals = profile.total_referrals

    deposited_refs = profile.referrals_with_deposit
    conversion_rate = (deposited_refs / total_referrals * 100) if total_referrals > 0 else 0
    total_ggr = profile.total_referral_ggr
    avg_ggr_per_ref = (total_ggr / total_referrals) if total_referrals > 0 else 0

    # По источникам
    source_stats = Referral.objects.filter(
        partner=request.user,
        level=1
    ).values('promo_link__name').annotate(
        clicks=Sum('promo_link__clicks') if 'promo_link__clicks' else 0,
        registrations=Count('id'),
        deposits=Count('id', filter=Q(total_deposits__gt=0)),
        total_deposit_amount=Sum('total_deposits'),
        total_ggr=Sum('total_ggr'),
        total_earned=Sum('total_commission_earned'),
    ).order_by('-total_earned')

    # По продуктам
    # TODO: calculate from models

    # Топ рефералы
    top_referrals = Referral.objects.filter(
        partner=request.user,
        level=1
    ).select_related('referral').order_by('-total_ggr')[:5]

    context = {
        'total_earned': total_earned,
        'total_withdrawn': total_withdrawn,
        'balance': balance,
        'total_referrals': total_referrals,
        'deposited_refs': deposited_refs,
        'conversion_rate': conversion_rate,
        'total_ggr': total_ggr,
        'avg_ggr_per_ref': avg_ggr_per_ref,
        'source_stats': source_stats,
        'top_referrals': top_referrals,
    }

    return render(request, 'referral/stats.html', context)


@login_required
def settings(request):
    """Настройки партнёра."""
    profile = request.user.partner_profile

    if request.method == 'POST':
        bio = request.POST.get('bio')
        website_url = request.POST.get('website_url')
        telegram_channel = request.POST.get('telegram_channel')
        custom_slug = request.POST.get('custom_slug')

        profile.bio = bio
        profile.website_url = website_url
        profile.telegram_channel = telegram_channel

        if custom_slug and custom_slug != profile.custom_slug:
            # Проверить уникальность
            if PromoLink.objects.filter(slug=custom_slug).exists() or User.objects.filter(referral_code=custom_slug).exists():
                messages.error(request, 'Этот slug уже занят.')
            else:
                profile.custom_slug = custom_slug

        profile.save()
        messages.success(request, 'Настройки сохранены.')
        return redirect('referral:settings')

    context = {
        'profile': profile,
    }

    return render(request, 'referral/settings.html', context)