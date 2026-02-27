from django.utils.timezone import now
from datetime import timedelta
from django.db.models import Count, Q

from apps.referral.models import *
from utils.helpers import get_client_ip, get_country_from_ip
from apps.accounts.services.notification_service import NotificationService


class AntiFraudService:

    @staticmethod
    def check_registration(partner, new_user, request):
        """
        Проверка при регистрации реферала.
        Возвращает список флагов.
        Пустой список = чисто.
        """

        flags = []
        ip = get_client_ip(request)
        settings = ReferralSettings.get_settings()

        # 1. Self-referral (свой же код)
        if partner.email == new_user.email:
            flags.append('self_referral')
            return ['blocked']  # Критический

        # 2. Тот же IP что у партнёра
        if ip == partner.last_login_ip or ip == partner.registration_ip:
            flags.append('same_ip_as_partner')

        # 3. Слишком много рефералов с этого IP
        same_ip_count = Referral.objects.filter(
            partner=partner,
            registration_ip=ip,
        ).count()
        if same_ip_count >= settings.max_referrals_per_ip:
            flags.append('too_many_from_ip')
            if same_ip_count >= settings.max_referrals_per_ip * 2:
                return ['blocked']

        # 4. Слишком быстрые регистрации
        recent_registrations = Referral.objects.filter(
            partner=partner,
            registered_at__gte=now() - timedelta(
                seconds=settings.min_time_between_registrations
            ),
        ).count()
        if recent_registrations > 0:
            flags.append('rapid_registration')

        # 5. Слишком много за день
        today_count = Referral.objects.filter(
            partner=partner,
            registered_at__date=now().date(),
        ).count()
        if today_count >= settings.max_referrals_per_day:
            flags.append('daily_limit_exceeded')

        # 6. Одинаковый user_agent (fingerprint)
        ua = request.META.get('HTTP_USER_AGENT', '')
        # Assuming LoginHistory exists, but for simplicity, skip or assume
        # same_ua_count = ... from LoginHistory
        same_ua_count = 0  # TODO: implement
        if same_ua_count > 5:
            flags.append('same_device_fingerprint')

        # 7. Подозрительный email домен
        email_domain = new_user.email.split('@')[1].lower()
        disposable_domains = [
            'tempmail.com', 'guerrillamail.com', 'throwaway.email',
            'mailinator.com', 'yopmail.com', 'trashmail.com',
            '10minutemail.com', 'temp-mail.org',
            # ... расширяемый список
        ]
        if email_domain in disposable_domains:
            flags.append('disposable_email')

        # 8. Страна не совпадает (подозрительно, не блокируем)
        user_country = get_country_from_ip(ip)
        partner_country = partner.country
        if partner_country and user_country and partner_country != user_country:
            # Не флаг сам по себе, но в комбинации с другими
            pass

        # Решение
        if len(flags) >= 3:
            flags.append('high_risk')
            if settings.auto_block_on_fraud:
                flags.append('blocked')

        return flags

    @staticmethod
    def daily_fraud_check():
        """
        Celery задача. Ежедневная проверка на фрод.
        Анализирует паттерны за последние 24 часа.
        """

        yesterday = now().date() - timedelta(days=1)

        # 1. Партнёры с аномально высоким количеством регистраций
        suspicious_partners = (
            Referral.objects
            .filter(registered_at__date=yesterday)
            .values('partner')
            .annotate(count=Count('id'))
            .filter(count__gt=20)  # > 20 за день
        )

        for sp in suspicious_partners:
            partner = User.objects.get(id=sp['partner'])
            AntiFraudService.flag_partner(partner, 'high_registration_volume',
                                           f'{sp["count"]} регистраций за день')

        # 2. Рефералы без активности
        inactive_referrals = Referral.objects.filter(
            registered_at__lt=now() - timedelta(days=7),
            total_deposits=0,
            status='registered',
        )

        # Партнёры с > 80% неактивных рефералов
        partner_stats = (
            Referral.objects
            .filter(level=1)
            .values('partner')
            .annotate(
                total=Count('id'),
                inactive=Count('id', filter=Q(
                    total_deposits=0,
                    registered_at__lt=now() - timedelta(days=7),
                )),
            )
        )

        for ps in partner_stats:
            if ps['total'] >= 10:
                inactive_rate = ps['inactive'] / ps['total']
                if inactive_rate > 0.8:
                    partner = User.objects.get(id=ps['partner'])
                    AntiFraudService.flag_partner(partner, 'high_inactive_rate',
                                                   f'{inactive_rate*100:.0f}% неактивных')

        # 3. Рефералы которые сразу выводят
        # TODO: check withdrawals

        # 4. Одинаковые паттерны ставок
        # TODO: complex check

    @staticmethod
    def flag_partner(partner, flag_type, details):
        """Пометить партнёра для ручной проверки."""
        profile = partner.partner_profile
        profile.is_suspended = True
        profile.suspension_reason = f'{flag_type}: {details}'
        profile.save(update_fields=['is_suspended', 'suspension_reason'])

        # Уведомление админам
        NotificationService.create_notification(
            user=None,  # Системное, для всех админов
            notification_type='system',
            title=f'⚠️ Подозрительный партнёр: {partner.username}',
            message=f'Флаг: {flag_type}. {details}',
            icon='⚠️',
            link=f'/admin/referral/partner/{partner.id}/',
        )

    @staticmethod
    def manual_review(partner, admin, action, reason=''):
        """
        Ручное решение админа после проверки.
        action: 'approve' | 'block' | 'suspend'
        """

        profile = partner.partner_profile

        if action == 'approve':
            profile.is_suspended = False
            profile.suspension_reason = ''
            profile.save()

        elif action == 'block':
            profile.is_partner_active = False
            profile.is_suspended = False
            profile.suspension_reason = reason
            profile.save()

            # Аннулировать незаработанные комиссии
            Commission.objects.filter(
                partner=partner,
                status='pending',
            ).update(status='cancelled')

            NotificationService.create_notification(
                user=partner,
                notification_type='system',
                title='Партнёрская программа приостановлена',
                message=f'Ваше участие в партнёрской программе '
                        f'приостановлено. Причина: {reason}. '
                        f'Обратитесь в поддержку.',
                icon='🚫',
            )

        elif action == 'suspend':
            profile.is_suspended = True
            profile.suspension_reason = reason
            profile.save()