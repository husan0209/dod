from django.utils.timezone import now
from datetime import timedelta
from django.db.models import F, Q

from apps.referral.models import *
from utils.helpers import get_client_ip, get_country_from_ip, get_device_type
from apps.accounts.services.notification_service import NotificationService
from apps.referral.services.antifraud_service import AntiFraudService

from apps.sports.models import Bet
from apps.casino.models import GameSession
from apps.predictions.models import Trade

class ReferralService:

    @staticmethod
    def process_referral_click(request, code_or_slug):
        """
        Обработка клика по реферальной ссылке.
        URL: /r/{code_or_slug}/
        
        1. Определить партнёра
        2. Записать клик
        3. Сохранить в сессии/cookie
        4. Редирект на регистрацию
        """

        from django.shortcuts import redirect

        # Найти партнёра
        partner = None
        promo_link = None

        # Сначала ищем по PromoLink slug
        try:
            promo_link = PromoLink.objects.get(
                slug=code_or_slug, is_active=True
            )
            partner = promo_link.partner
        except PromoLink.DoesNotExist:
            # Потом по referral_code пользователя
            try:
                partner = User.objects.get(
                    referral_code=code_or_slug, is_active=True
                )
            except User.DoesNotExist:
                # Невалидная ссылка → просто редирект на регистрацию
                return redirect('accounts:register')

        # Проверка: партнёр не заблокирован
        partner_profile = partner.partner_profile
        if not partner_profile.is_partner_active or partner_profile.is_suspended:
            return redirect('accounts:register')

        # Записать клик
        ip = get_client_ip(request)
        ua = request.META.get('HTTP_USER_AGENT', '')
        referer = request.META.get('HTTP_REFERER', '')

        # Проверить уникальность клика (по IP за 24ч)
        is_unique = not PromoLinkClick.objects.filter(
            promo_link=promo_link,
            ip_address=ip,
            created_at__gte=now() - timedelta(hours=24),
        ).exists() if promo_link else True

        if promo_link:
            PromoLinkClick.objects.create(
                promo_link=promo_link,
                ip_address=ip,
                country=get_country_from_ip(ip),
                user_agent=ua,
                device_type=get_device_type(ua),
                referer=referer,
                is_unique=is_unique,
            )

            # Обновить счётчик кликов
            if is_unique:
                PromoLink.objects.filter(id=promo_link.id).update(
                    clicks=F('clicks') + 1
                )

        # Сохранить в сессии и cookie
        request.session['referral_code'] = partner.referral_code
        request.session['promo_link_id'] = str(promo_link.id) if promo_link else None

        # Cookie на 30 дней (если сессия истечёт)
        response = redirect('accounts:register')
        response.set_cookie(
            'ref',
            partner.referral_code,
            max_age=30 * 24 * 60 * 60,  # 30 дней
            httponly=True,
            samesite='Lax',
        )

        return response

    @staticmethod
    def process_referral_registration(new_user, request):
        """
        Вызывается ПОСЛЕ успешной регистрации нового пользователя.
        Привязывает реферала к партнёру.
        """

        # Получить реферальный код
        referral_code = (
            request.session.get('referral_code')
            or request.COOKIES.get('ref')
            or request.POST.get('referral_code')
        )

        if not referral_code:
            return None  # Пришёл не по реферальной ссылке

        # Найти партнёра
        try:
            partner = User.objects.get(referral_code=referral_code)
        except User.DoesNotExist:
            return None

        # АНТИФРОД ПРОВЕРКИ
        fraud_flags = AntiFraudService.check_registration(
            partner, new_user, request
        )

        if 'blocked' in fraud_flags:
            # Критический фрод → не засчитывать
            return None

        # Определить уровень
        level = 1  # Прямой реферал

        # Проверить: партнёр сам является рефералом?
        # Если да → создать запись 2-го уровня
        level2_partner = None
        if partner.referred_by:
            settings = ReferralSettings.get_settings()
            if settings.level2_enabled:
                level2_partner = partner.referred_by

        # Получить промо-ссылку
        promo_link_id = request.session.get('promo_link_id')
        promo_link = None
        if promo_link_id:
            try:
                promo_link = PromoLink.objects.get(id=promo_link_id)
            except PromoLink.DoesNotExist:
                pass

        ip = get_client_ip(request)

        # Создать запись реферала (1-й уровень)
        referral = Referral.objects.create(
            partner=partner,
            referral=new_user,
            referral_code_used=referral_code,
            source=request.GET.get('utm_source', ''),
            promo_link=promo_link,
            registration_ip=ip,
            registration_country=get_country_from_ip(ip),
            registration_device=get_device_type(
                request.META.get('HTTP_USER_AGENT', '')
            ),
            level=1,
            is_suspicious=bool(fraud_flags),
            fraud_flags=fraud_flags,
        )

        # Обновить User.referred_by
        new_user.referred_by = partner
        new_user.save(update_fields=['referred_by'])

        # Обновить статистику партнёра
        partner_profile = partner.partner_profile
        partner_profile.total_referrals = F('total_referrals') + 1
        partner_profile.monthly_referrals = F('monthly_referrals') + 1
        partner_profile.save(update_fields=[
            'total_referrals', 'monthly_referrals'
        ])

        # Обновить PromoLink статистику
        if promo_link:
            PromoLink.objects.filter(id=promo_link.id).update(
                registrations=F('registrations') + 1,
            )
            # Обновить конверсию
            promo_link.refresh_from_db()
            if promo_link.clicks > 0:
                promo_link.conversion_rate = (
                    promo_link.registrations / promo_link.clicks * 100
                )
                promo_link.save(update_fields=['conversion_rate'])

        # Бонус за регистрацию (если есть)
        tier = partner_profile.tier
        if tier.signup_bonus > 0 and not referral.is_suspicious:
            from apps.referral.services.commission_service import CommissionService
            CommissionService.create_commission(
                partner=partner,
                referral=referral,
                commission_type='signup_bonus',
                amount=tier.signup_bonus,
                description=f'Бонус за регистрацию {new_user.username}',
            )

        # Создать реферала 2-го уровня
        if level2_partner:
            Referral.objects.create(
                partner=level2_partner,
                referral=new_user,
                referral_code_used=referral_code,
                level=2,
                registration_ip=ip,
                is_suspicious=bool(fraud_flags),
                fraud_flags=fraud_flags,
            )

            level2_profile = level2_partner.partner_profile
            level2_profile.total_level2_referrals = (
                F('total_level2_referrals') + 1
            )
            level2_profile.save(update_fields=['total_level2_referrals'])

        # Уведомление партнёру
        NotificationService.create_notification(
            user=partner,
            notification_type='new_referral',
            title='🤝 Новый реферал!',
            message=f'Пользователь {new_user.username} '
                    f'зарегистрировался по вашей ссылке.',
            icon='🤝',
            link='/partners/',
        )

        # Очистить сессию
        if 'referral_code' in request.session:
            del request.session['referral_code']
        if 'promo_link_id' in request.session:
            del request.session['promo_link_id']

        return referral

    @staticmethod
    def qualify_referral(referral):
        """
        Квалифицировать реферала.
        Вызывается когда реферал выполняет условия:
          - Депозит >= min_deposit_to_qualify
          - Ставок >= min_bets_to_qualify
          - Оборот >= min_wagered_to_qualify
        """
        if referral.is_qualified:
            return  # Уже квалифицирован

        settings = ReferralSettings.get_settings()
        user = referral.referral

        # Проверить условия
        if referral.total_deposits < settings.min_deposit_to_qualify:
            return
        if referral.total_bets < settings.min_wagered_to_qualify:
            return
        # Количество ставок — считать из моделей ставок
        bets_count = (
            Bet.objects.filter(user=user).count() +
            GameSession.objects.filter(user=user).count() +
            Trade.objects.filter(user=user, trade_type='buy').count()
        )
        if bets_count < settings.min_bets_to_qualify:
            return

        referral.is_qualified = True
        referral.qualified_at = now()
        referral.status = 'active'
        referral.save(update_fields=['is_qualified', 'qualified_at', 'status'])

        # Обновить партнёрскую статистику
        partner_profile = referral.partner.partner_profile
        partner_profile.referrals_with_deposit = Referral.objects.filter(
            partner=referral.partner,
            is_qualified=True,
            level=1,
        ).count()
        partner_profile.save(update_fields=['referrals_with_deposit'])

        # Уведомление
        NotificationService.create_notification(
            user=referral.partner,
            notification_type='referral_qualified',
            title='✅ Реферал квалифицирован!',
            message=f'{user.username} выполнил условия. '
                    f'Теперь вы получаете комиссию от его активности.',
            icon='✅',
            link='/partners/referrals/',
        )