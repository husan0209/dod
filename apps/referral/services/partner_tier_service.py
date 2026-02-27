from django.utils.timezone import now
from django.db.models import Q, F

from ..models import PartnerProfile, PartnerTier
from apps.notifications.services import NotificationService


class PartnerTierService:
    """
    Управление уровнями партнёров: повышение, понижение, сброс статистики.
    """

    @staticmethod
    def check_and_upgrade(user):
        """
        Проверить и повысить уровень партнёра.
        Вызывается каждый час для всех активных партнёров.
        """
        try:
            profile = user.partner_profile
        except PartnerProfile.DoesNotExist:
            return

        if not profile.is_partner_active:
            return

        current_tier = profile.tier
        next_tier = PartnerTier.objects.filter(
            sort_order__gt=current_tier.sort_order,
            is_active=True
        ).order_by('sort_order').first()

        if not next_tier:
            return  # Уже максимальный уровень

        # Проверить условия
        meets_referrals = profile.total_referrals >= next_tier.min_referrals
        meets_ggr = profile.monthly_ggr >= next_tier.min_monthly_ggr

        if meets_referrals and meets_ggr:
            # Повысить уровень
            old_tier = profile.tier
            profile.tier = next_tier
            profile.tier_changed_at = now()
            profile.save(update_fields=['tier', 'tier_changed_at'])

            # Уведомление
            NotificationService.create_notification(
                user=user,
                notification_type='tier_upgrade',
                title=f'🎉 Повышение уровня!',
                message=f'Поздравляем! Вы перешли с уровня "{old_tier.name}" '
                       f'на уровень "{next_tier.name}".',
                icon='🎉',
                link='/partners/',
            )

            # Рекурсивно проверить следующий уровень
            PartnerTierService.check_and_upgrade(user)

    @staticmethod
    def check_downgrade():
        """
        Проверить и понизить уровни партнёров.
        Вызывается ежемесячно.
        """
        profiles = PartnerProfile.objects.filter(
            is_partner_active=True
        ).select_related('tier', 'user')

        for profile in profiles:
            current_tier = profile.tier

            # Проверить условия текущего уровня
            meets_referrals = profile.total_referrals >= current_tier.min_referrals
            meets_ggr = profile.monthly_ggr >= current_tier.min_monthly_ggr

            if not (meets_referrals and meets_ggr):
                # Найти подходящий уровень ниже
                lower_tier = PartnerTier.objects.filter(
                    sort_order__lt=current_tier.sort_order,
                    min_referrals__lte=profile.total_referrals,
                    min_monthly_ggr__lte=profile.monthly_ggr,
                    is_active=True
                ).order_by('-sort_order').first()

                if lower_tier and lower_tier != current_tier:
                    # Понизить уровень
                    old_tier = profile.tier
                    profile.tier = lower_tier
                    profile.tier_changed_at = now()
                    profile.save(update_fields=['tier', 'tier_changed_at'])

                    # Уведомление
                    NotificationService.create_notification(
                        user=profile.user,
                        notification_type='tier_downgrade',
                        title=f'📉 Понижение уровня',
                        message=f'Ваш уровень понижен с "{old_tier.name}" '
                               f'на "{lower_tier.name}" из-за несоответствия условиям.',
                        icon='📉',
                        link='/partners/',
                    )

    @staticmethod
    def reset_monthly_stats():
        """
        Сброс месячных счётчиков статистики.
        Вызывается 1-го числа каждого месяца в 00:01.
        """
        PartnerProfile.objects.filter(
            is_partner_active=True
        ).update(
            monthly_ggr=0,
            monthly_earned=0,
            monthly_referrals=0,
        )

        # Сбросить лучшие показатели если текущий месяц лучше
        # (опционально, можно добавить логику для обновления best_month_*)

    @staticmethod
    def get_tier_progress(profile):
        """
        Получить прогресс к следующему уровню.
        Возвращает dict с процентами и описаниями.
        """
        current_tier = profile.tier
        next_tier = PartnerTier.objects.filter(
            sort_order__gt=current_tier.sort_order,
            is_active=True
        ).order_by('sort_order').first()

        if not next_tier:
            return {
                'next_tier': None,
                'referrals_progress': 100,
                'ggr_progress': 100,
                'overall_progress': 100,
                'message': 'Максимальный уровень достигнут!'
            }

        # Прогресс по рефералам
        if next_tier.min_referrals > 0:
            referrals_progress = min(100, (profile.total_referrals / next_tier.min_referrals) * 100)
        else:
            referrals_progress = 100

        # Прогресс по GGR
        if next_tier.min_monthly_ggr > 0:
            ggr_progress = min(100, (profile.monthly_ggr / next_tier.min_monthly_ggr) * 100)
        else:
            ggr_progress = 100

        # Общий прогресс (минимум из двух)
        overall_progress = min(referrals_progress, ggr_progress)

        return {
            'next_tier': next_tier,
            'referrals_progress': round(referrals_progress, 1),
            'ggr_progress': round(ggr_progress, 1),
            'overall_progress': round(overall_progress, 1),
            'message': f'До уровня "{next_tier.name}": '
                      f'рефералов {profile.total_referrals}/{next_tier.min_referrals}, '
                      f'GGR ${profile.monthly_ggr:.0f}/${next_tier.min_monthly_ggr:.0f}'
        }
