from decimal import Decimal
from django.utils.timezone import now, timedelta
from django.db.models import Sum, F
from django.db import transaction

from ..models import Commission, Referral, ReferralSettings, NegativeCarryover
from apps.sports.models import Bet
from apps.casino.models import GameSession
from apps.predictions.models import Trade


class CommissionService:
    """
    Расчёт и начисление комиссий партнёрам.
    """

    @staticmethod
    def calculate_daily_commissions():
        """
        Ежедневный расчёт комиссий.
        Вызывается Celery в 02:00 UTC.
        """
        yesterday = now().date() - timedelta(days=1)
        settings = ReferralSettings.get_settings()

        # Только квалифицированные рефералы
        qualified_referrals = Referral.objects.filter(
            is_qualified=True,
            status='active',
        ).select_related('partner__partner_profile', 'referral')

        for referral in qualified_referrals:
            try:
                with transaction.atomic():
                    CommissionService._calculate_referral_commission(
                        referral, yesterday, settings
                    )
            except Exception as e:
                # Логировать ошибку, но продолжить
                print(f"Error calculating commission for referral {referral.id}: {e}")
                continue

    @staticmethod
    def _calculate_referral_commission(referral, period_date, settings):
        """
        Расчёт комиссии для одного реферала за период.
        """
        partner = referral.partner
        partner_profile = partner.partner_profile
        user = referral.referral

        # Рассчитать GGR за период
        ggr = CommissionService._calculate_user_ggr(user, period_date)

        if ggr == 0:
            return  # Ничего не заработал

        # Проверить carryover
        carryover_amount = 0
        carryover, created = NegativeCarryover.objects.get_or_create(
            partner=partner,
            referral=referral,
            defaults={'amount': Decimal('0')}
        )

        effective_ggr = ggr
        if carryover.amount < 0:
            effective_ggr += carryover.amount
            if effective_ggr > 0:
                carryover.amount = 0  # Сбросить carryover
            else:
                carryover.amount = effective_ggr
                effective_ggr = 0
            carryover.save()

        if effective_ggr <= 0:
            # Создать комиссию с $0
            CommissionService.create_commission(
                partner=partner,
                referral=referral,
                commission_type='ggr',
                amount=Decimal('0'),
                referral_ggr=ggr,
                description=f'GGR: ${ggr:.2f}, carryover: ${carryover.amount:.2f}',
                period_start=period_date,
                period_end=period_date,
            )
            return

        # Рассчитать возраст реферала в месяцах
        age_months = CommissionService._get_referral_age_months(referral)

        # Получить ставку комиссии
        commission_rate = partner_profile.get_commission_rate(age_months)

        # Рассчитать комиссию
        gross_commission = effective_ggr * commission_rate / 100

        # Создать запись комиссии
        CommissionService.create_commission(
            partner=partner,
            referral=referral,
            commission_type='ggr',
            amount=gross_commission,
            referral_ggr=ggr,
            commission_rate=commission_rate,
            description=f'GGR: ${ggr:.2f}, ставка: {commission_rate}%, возраст: {age_months} мес',
            period_start=period_date,
            period_end=period_date,
        )

        # Зачислить на баланс партнёра
        partner_profile.balance = F('balance') + gross_commission
        partner_profile.total_earned = F('total_earned') + gross_commission
        partner_profile.monthly_earned = F('monthly_earned') + gross_commission
        partner_profile.save(update_fields=[
            'balance', 'total_earned', 'monthly_earned'
        ])

        # Обновить статистику реферала
        referral.total_ggr = F('total_ggr') + ggr
        referral.save(update_fields=['total_ggr'])

        # Обновить статистику партнёра
        partner_profile.total_referral_ggr = F('total_referral_ggr') + ggr
        partner_profile.monthly_ggr = F('monthly_ggr') + ggr
        partner_profile.save(update_fields=[
            'total_referral_ggr', 'monthly_ggr'
        ])

    @staticmethod
    def _calculate_user_ggr(user, period_date):
        """
        Рассчитать GGR пользователя за период.
        GGR = сумма ставок - сумма выигрышей
        """
        start_date = period_date
        end_date = period_date + timedelta(days=1)

        # Sports bets
        sports_ggr = Bet.objects.filter(
            user=user,
            created_at__date__gte=start_date,
            created_at__date__lt=end_date,
            status='settled'
        ).aggregate(
            total_bets=Sum('amount'),
            total_winnings=Sum('payout_amount')
        )

        sports_ggr_value = (
            (sports_ggr['total_bets'] or 0) -
            (sports_ggr['total_winnings'] or 0)
        )

        # Casino games
        casino_ggr = GameSession.objects.filter(
            user=user,
            created_at__date__gte=start_date,
            created_at__date__lt=end_date,
            status__in=['won', 'lost', 'cashout']
        ).aggregate(
            total_bets=Sum('bet_amount'),
            total_winnings=Sum('win_amount')
        )

        casino_ggr_value = (
            (casino_ggr['total_bets'] or 0) -
            (casino_ggr['total_winnings'] or 0)
        )

        # Prediction trades (только buy, т.к. sell не добавляет GGR)
        prediction_ggr = Trade.objects.filter(
            user=user,
            created_at__date__gte=start_date,
            created_at__date__lt=end_date,
            trade_type='buy'
        ).aggregate(
            total_cost=Sum('total_amount')
        )['total_cost'] or 0

        total_ggr = sports_ggr_value + casino_ggr_value + prediction_ggr

        return Decimal(str(total_ggr))

    @staticmethod
    def _get_referral_age_months(referral):
        """
        Рассчитать возраст реферала в месяцах.
        """
        from dateutil.relativedelta import relativedelta

        age = relativedelta(now().date(), referral.registered_at.date())
        return age.months + (age.years * 12)

    @staticmethod
    def create_commission(partner, referral, commission_type, amount,
                         referral_ggr=None, commission_rate=None,
                         description='', period_start=None, period_end=None):
        """
        Создать запись комиссии.
        """
        commission = Commission.objects.create(
            partner=partner,
            referral=referral,
            commission_type=commission_type,
            period_start=period_start,
            period_end=period_end,
            referral_ggr=referral_ggr or Decimal('0'),
            commission_rate=commission_rate or Decimal('0'),
            gross_amount=amount,
            net_amount=amount,  # Пока без adjustments
            description=description,
        )
        return commission

    @staticmethod
    def process_payout_request(partner, amount, payout_method, payout_details=None):
        """
        Обработать запрос на вывод.
        """
        from ..models import PartnerPayout

        partner_profile = partner.partner_profile

        if partner_profile.balance < amount:
            raise ValueError("Insufficient balance")

        if amount < partner_profile.tier.min_payout_amount:
            raise ValueError("Amount below minimum")

        # Создать запрос
        payout = PartnerPayout.objects.create(
            partner=partner,
            amount=amount,
            payout_method=payout_method,
            payout_details=payout_details,
        )

        # Заморозить средства
        partner_profile.balance = F('balance') - amount
        partner_profile.save(update_fields=['balance'])

        return payout

    @staticmethod
    def approve_payout(payout, processed_by):
        """
        Одобрить выплату (админ).
        """
        # Здесь интеграция с платёжными системами
        # Пока просто отметить как completed

        payout.status = 'completed'
        payout.processed_by = processed_by
        payout.processed_at = now()
        payout.save()

        # Для game_balance — зачислить на кошелёк
        if payout.payout_method == 'game_balance':
            from apps.wallet.services.transaction_service import TransactionService
            TransactionService.deposit(
                wallet=payout.partner.wallet,
                currency_code='USD',
                amount=payout.net_amount,
                type='partner_payout',
                description=f'Partner payout #{payout.id}',
                reference_type='partner_payout',
                reference_id=str(payout.id),
            )

        # Уведомление
        from apps.accounts.services.notification_service import NotificationService
        NotificationService.create_notification(
            user=payout.partner,
            notification_type='payout_completed',
            title='💰 Выплата одобрена!',
            message=f'Ваша выплата ${payout.amount:.2f} обработана.',
            icon='💰',
            link='/partners/payouts/',
        )

    @staticmethod
    def reject_payout(payout, reason, processed_by):
        """
        Отклонить выплату (админ).
        """
        payout.status = 'rejected'
        payout.rejection_reason = reason
        payout.processed_by = processed_by
        payout.processed_at = now()
        payout.save()

        # Вернуть средства
        payout.partner.partner_profile.balance = F('balance') + payout.amount
        payout.partner.partner_profile.save(update_fields=['balance'])

        # Уведомление
        from apps.accounts.services.notification_service import NotificationService
        NotificationService.create_notification(
            user=payout.partner,
            notification_type='payout_rejected',
            title='❌ Выплата отклонена',
            message=f'Ваша выплата ${payout.amount:.2f} отклонена: {reason}',
            icon='❌',
            link='/partners/payouts/',
        )

    @staticmethod
    def process_first_deposit(user, deposit_amount):
        """
        Вызывается при первом депозите реферала.
        Начисляет бонус за первый депозит партнёру.
        """
        try:
            referral = Referral.objects.get(
                referral=user, level=1
            )
        except Referral.DoesNotExist:
            return  # Не реферал

        if referral.first_deposit_at is not None:
            return  # Уже был первый депозит

        # Обновить реферала
        referral.first_deposit_amount = deposit_amount
        referral.first_deposit_at = now()
        referral.total_deposits += deposit_amount
        referral.status = 'deposited'
        referral.save()

        # Бонус за первый депозит
        partner_profile = referral.partner.partner_profile
        rate = partner_profile.tier.first_deposit_bonus_rate

        if rate > 0:
            bonus = deposit_amount * (rate / 100)
            
            CommissionService.create_commission(
                partner=referral.partner,
                referral=referral,
                commission_type='first_deposit',
                amount=bonus,
                referral_ggr=Decimal('0'),
                commission_rate=rate,
                description=f'Бонус за первый депозит {user.username}',
                period_start=now().date(),
                period_end=now().date(),
            )
            
            partner_profile.balance += bonus
            partner_profile.total_earned += bonus
            partner_profile.save(update_fields=['balance', 'total_earned'])

            from apps.accounts.services.notification_service import NotificationService
            NotificationService.create_notification(
                user=referral.partner,
                notification_type='referral_commission',
                title='💰 Бонус за первый депозит реферала!',
                message=f'{user.username} сделал первый депозит '
                        f'${deposit_amount:.2f}. '
                        f'Ваш бонус: ${bonus:.2f}',
                icon='💰',
                link='/partners/',
            )

        # Обновить PromoLink
        if referral.promo_link:
            PromoLink.objects.filter(id=referral.promo_link.id).update(
                deposits=F('deposits') + 1,
                total_deposit_amount=F('total_deposit_amount') + deposit_amount,
            )

        # Попробовать квалифицировать
        from apps.referral.services.referral_service import ReferralService
        ReferralService.qualify_referral(referral)


class PartnerTierService:
    """
    Управление уровнями партнёров.
    """

    @staticmethod
    def check_and_upgrade(partner):
        """
        Проверить и повысить уровень партнёра.
        Вызывается:
          - После каждой квалификации реферала
          - Ежедневно (Celery)
          - При начислении комиссии
        """

        profile = partner.partner_profile
        current_tier = profile.tier
        
        # Получить все уровни выше текущего
        higher_tiers = PartnerTier.objects.filter(
            sort_order__gt=current_tier.sort_order,
            is_active=True,
        ).order_by('sort_order')

        for tier in higher_tiers:
            if PartnerTierService.can_upgrade_to(profile, tier):
                old_tier = profile.tier
                profile.tier = tier
                profile.tier_changed_at = now()
                profile.save(update_fields=['tier', 'tier_changed_at'])

                from apps.accounts.services.notification_service import NotificationService
                NotificationService.create_notification(
                    user=partner,
                    notification_type='partner_tier_up',
                    title=f'🎉 Вы достигли уровня {tier.name}!',
                    message=f'Поздравляем! Ваш партнёрский уровень '
                            f'повышен с {old_tier.name} до {tier.name}. '
                            f'Новые комиссионные ставки уже активны.',
                    icon=tier.icon,
                    link='/partners/',
                )

                from apps.accounts.models import AdminActionLog
                AdminActionLog.objects.create(
                    admin_user=None,
                    action_type='partner_tier_changed',
                    target_user=partner,
                    description=f'Auto: {old_tier.name} → {tier.name}',
                    details={
                        'old_tier': old_tier.slug,
                        'new_tier': tier.slug,
                    },
                )
            else:
                break  # Если не можем на этот уровень, выше тоже нет

    @staticmethod
    def can_upgrade_to(profile, tier):
        """Проверить соответствие условиям уровня."""

        # Активные рефералы (квалифицированные)
        active_refs = Referral.objects.filter(
            partner=profile.user,
            is_qualified=True,
            level=1,
            status__in=['active', 'deposited'],
        ).count()

        if active_refs < tier.min_referrals:
            return False

        # Месячный GGR
        if profile.monthly_ggr < tier.min_monthly_ggr:
            return False

        return True

    @staticmethod
    def check_downgrade():
        """
        Celery задача (ежемесячно, 1-го числа).
        Проверить нужно ли понизить уровень партнёров.
        
        Если партнёр 2 месяца подряд не выполняет условия
        текущего уровня → понизить на 1 уровень.
        """

        profiles = PartnerProfile.objects.filter(
            is_partner_active=True,
            tier__sort_order__gt=1,  # Не стартовый
        ).select_related('tier', 'user')

        for profile in profiles:
            if not PartnerTierService.can_upgrade_to(profile, profile.tier):
                # Проверить: второй месяц подряд?
                # (нужно хранить историю — упрощённо: просто проверяем)
                lower_tier = PartnerTier.objects.filter(
                    sort_order__lt=profile.tier.sort_order,
                    is_active=True,
                ).order_by('-sort_order').first()

                if lower_tier:
                    old_tier = profile.tier
                    profile.tier = lower_tier
                    profile.tier_changed_at = now()
                    profile.save(update_fields=['tier', 'tier_changed_at'])

                    from apps.accounts.services.notification_service import NotificationService
                    NotificationService.create_notification(
                        user=profile.user,
                        notification_type='partner_tier_down',
                        title=f'Уровень партнёра изменён',
                        message=f'Ваш партнёрский уровень изменён '
                                f'с {old_tier.name} на {lower_tier.name}. '
                                f'Привлекайте больше рефералов для повышения.',
                        icon='📉',
                        link='/partners/',
                    )

    @staticmethod
    def reset_monthly_stats():
        """
        Celery задача (ежемесячно, 1-го числа 00:01 UTC).
        Сбросить месячные счётчики.
        """

        # Сохранить лучший месяц перед сбросом
        profiles = PartnerProfile.objects.filter(
            monthly_earned__gt=0
        )
        for profile in profiles:
            if profile.monthly_earned > profile.best_month_earnings:
                profile.best_month_earnings = profile.monthly_earned
                profile.best_month_date = now().date() - timedelta(days=1)
                profile.save(update_fields=[
                    'best_month_earnings', 'best_month_date'
                ])

        # Сбросить
        PartnerProfile.objects.all().update(
            monthly_ggr=0,
            monthly_earned=0,
            monthly_referrals=0,
        )