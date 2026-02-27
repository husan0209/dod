from celery import shared_task
from django.utils.timezone import now
from datetime import timedelta
from django.db.models import Sum, F, Count, Q

from apps.referral.models import *
from apps.referral.services.commission_service import CommissionService, PartnerTierService
from apps.referral.services.antifraud_service import AntiFraudService
from apps.notifications.services import NotificationService


# ── ЕЖЕДНЕВНЫЕ ──────────────────────────────────

@shared_task
def calculate_daily_commissions():
    """02:00 UTC. Расчёт комиссий за вчера."""
    CommissionService.calculate_daily_commissions()


@shared_task
def daily_fraud_check():
    """03:00 UTC. Проверка на фрод."""
    AntiFraudService.daily_fraud_check()


@shared_task
def update_referral_activity():
    """04:00 UTC. Обновить статусы активности рефералов."""
    # Кто был активен за 30 дней → is_active = True
    Referral.objects.filter(
        last_active_at__gte=now() - timedelta(days=30),
        is_active=False,
        status='churned',
    ).update(is_active=True, status='active')

    # Кто не был → is_active = False, status = 'churned'
    Referral.objects.filter(
        last_active_at__lt=now() - timedelta(days=30),
        is_active=True,
    ).update(is_active=False, status='churned')

    # Обновить active_referrals для каждого партнёра
    partners = PartnerProfile.objects.all()
    for profile in partners:
        profile.active_referrals = Referral.objects.filter(
            partner=profile.user,
            is_active=True,
            is_qualified=True,
            level=1,
        ).count()
        profile.save(update_fields=['active_referrals'])


@shared_task
def send_daily_commission_summary():
    """06:00 UTC. Суммарное уведомление о комиссиях за день."""
    yesterday = now().date() - timedelta(days=1)
    
    partners_with_commissions = Commission.objects.filter(
        period_start=yesterday,
        net_amount__gt=0,
        status='approved',
    ).values('partner').annotate(
        total=Sum('net_amount'),
        count=Count('id'),
    )

    for pc in partners_with_commissions:
        partner = User.objects.get(id=pc['partner'])
        NotificationService.create_notification(
            user=partner,
            notification_type='referral_commission',
            title=f'💰 Комиссия за {yesterday.strftime("%d.%m")}',
            message=f'Начислено: ${pc["total"]:.2f} '
                    f'от {pc["count"]} рефералов.',
            icon='💰',
            link='/partners/',
        )


# ── ЕЖЕМЕСЯЧНЫЕ ─────────────────────────────────

@shared_task
def reset_monthly_stats():
    """1-е число, 00:01 UTC. Сбросить месячные счётчики."""
    PartnerTierService.reset_monthly_stats()


@shared_task
def check_tier_downgrades():
    """1-е число, 00:30 UTC. Проверка понижения уровней."""
    PartnerTierService.check_downgrade()


# ── КАЖДЫЙ ЧАС ──────────────────────────────────

@shared_task
def check_tier_upgrades():
    """Каждый час. Проверка повышения уровней."""
    profiles = PartnerProfile.objects.filter(
        is_partner_active=True,
    ).select_related('tier', 'user')

    for profile in profiles:
        PartnerTierService.check_and_upgrade(profile.user)


@shared_task
def update_promo_link_stats():
    """Каждый час. Обновить статистику промо-ссылок."""
    links = PromoLink.objects.filter(is_active=True)
    for link in links:
        # Пересчитать из Referral
        stats = Referral.objects.filter(
            promo_link=link,
        ).aggregate(
            regs=Count('id'),
            deps=Count('id', filter=Q(total_deposits__gt=0)),
            total_dep=Sum('total_deposits'),
            total_ggr=Sum('total_ggr'),
            total_earned=Sum('total_commission_earned'),
        )
        link.registrations = stats['regs'] or 0
        link.deposits = stats['deps'] or 0
        link.total_deposit_amount = stats['total_dep'] or 0
        link.total_ggr = stats['total_ggr'] or 0
        link.total_earned = stats['total_earned'] or 0
        if link.clicks > 0:
            link.conversion_rate = link.registrations / link.clicks * 100
        if link.registrations > 0:
            link.deposit_rate = link.deposits / link.registrations * 100
        link.save()


# ── CELERY BEAT CONFIG ───────────────────────────

# This would be in config/celery.py
# But for reference:
# CELERY_BEAT_SCHEDULE = {
#   'calculate-daily-commissions': {
#     'task': 'apps.referral.tasks.calculate_daily_commissions',
#     'schedule': crontab(hour=2, minute=0),
#   },
#   'daily-fraud-check': {
#     'task': 'apps.referral.tasks.daily_fraud_check',
#     'schedule': crontab(hour=3, minute=0),
#   },
#   'update-referral-activity': {
#     'task': 'apps.referral.tasks.update_referral_activity',
#     'schedule': crontab(hour=4, minute=0),
#   },
#   'send-daily-commission-summary': {
#     'task': 'apps.referral.tasks.send_daily_commission_summary',
#     'schedule': crontab(hour=6, minute=0),
#   },
#   'reset-monthly-stats': {
#     'task': 'apps.referral.tasks.reset_monthly_stats',
#     'schedule': crontab(day_of_month=1, hour=0, minute=1),
#   },
#   'check-tier-downgrades': {
#     'task': 'apps.referral.tasks.check_tier_downgrades',
#     'schedule': crontab(day_of_month=1, hour=0, minute=30),
#   },
#   'check-tier-upgrades': {
#     'task': 'apps.referral.tasks.check_tier_upgrades',
#     'schedule': crontab(minute=0),  # каждый час
#   },
#   'update-promo-link-stats': {
#     'task': 'apps.referral.tasks.update_promo_link_stats',
#     'schedule': crontab(minute=15),  # каждый час в :15
#   },
# }