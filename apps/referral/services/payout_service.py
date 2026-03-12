from decimal import Decimal
from typing import TYPE_CHECKING, Optional, Dict
from django.utils.timezone import now
from django.db import transaction
from django.contrib.auth import get_user_model

from apps.referral.models import PartnerPayout, Commission, ReferralSettings
from utils.helpers import get_client_ip

if TYPE_CHECKING:
    from apps.referral.models import PartnerProfile

User = get_user_model()


class PayoutService:
    """
    Сервис для обработки выплат партнёрам.
    """

    @staticmethod
    def process_payout_request(user, amount, payout_method, payout_details, ip_address=None):
        """
        Обработать запрос на выплату.
        
        Args:
            user: User instance
            amount: Decimal amount to withdraw
            payout_method: 'game_balance', 'wallet', 'usdt', 'bank_card'
            payout_details: JSON field with additional data
            ip_address: IP address of requester
            
        Returns:
            PartnerPayout instance
            
        Raises:
            ValueError: If validation fails
        """
        profile = getattr(user, 'partner_profile', None)
        if not profile:
            raise ValueError('Partner profile not found')
        
        settings = ReferralSettings.get_settings()
        
        # Валидация
        if amount <= 0:
            raise ValueError('Сумма должна быть больше нуля')
        
        if amount > profile.balance:
            raise ValueError(f'Недостаточно средств. Доступно: ${profile.balance}')
        
        if amount < profile.tier.min_payout_amount:
            raise ValueError(f'Минимальная сумма для вывода: ${profile.tier.min_payout_amount}')
        
        # Проверить метод вывода
        if payout_method == 'game_balance' and not settings.payout_to_game_balance:
            raise ValueError('Этот метод вывода недоступен')
        
        if payout_method == 'wallet' and not settings.payout_to_wallet:
            raise ValueError('Этот метод вывода недоступен')
        
        if payout_method == 'usdt' and not settings.payout_direct_crypto:
            raise ValueError('Этот метод вывода недоступен')
        
        # Проверить детали для некоторых методов
        if payout_method in ['usdt', 'bank_card'] and not payout_details:
            raise ValueError(f'Требуются реквизиты для {payout_method}')
        
        # Рассчитать комиссию
        fee = PayoutService._calculate_payout_fee(amount, payout_method)
        net_amount = amount - fee
        
        # Создать запрос на выплату
        with transaction.atomic():
            payout = PartnerPayout.objects.create(
                partner=user,
                amount=amount,
                fee=fee,
                net_amount=net_amount,
                payout_method=payout_method,
                payout_details=payout_details if isinstance(payout_details, dict) else {},
                ip_address=ip_address,
            )
            
            # Зарезервировать средства на балансе
            profile.balance -= amount
            profile.save(update_fields=['balance'])
            
            # Привязать комиссии к выплате
            pending_commissions = Commission.objects.filter(
                partner=user,
                payout__isnull=True,
                status='approved'
            )
            
            total_reserved = Decimal('0')
            commissions_to_update = []
            for commission in pending_commissions:
                if total_reserved + commission.net_amount <= amount:
                    commissions_to_update.append(commission.id)
                    total_reserved += commission.net_amount
            
            # Batch update commissions
            if commissions_to_update:
                Commission.objects.filter(id__in=commissions_to_update).update(payout_id=payout.id)
        
        return payout

    @staticmethod
    def _calculate_payout_fee(amount, method):
        """
        Рассчитать комиссию за вывод.
        """
        if method == 'game_balance':
            return Decimal('0')  # Без комиссии
        elif method == 'wallet':
            return Decimal(str(amount)) * Decimal('0.02')  # 2%
        elif method == 'usdt':
            return Decimal('0')  # Без комиссии (блокчейн сеть платит доноры)
        elif method == 'bank_card':
            return Decimal(str(amount)) * Decimal('0.03')  # 3%
        
        return Decimal('0')

    @staticmethod
    def approve_payout(payout, processed_by):
        """
        Одобрить выплату (админ).
        """
        payout.status = 'processing'
        payout.processed_by = processed_by
        payout.processed_at = now()
        payout.save(update_fields=['status', 'processed_by', 'processed_at'])

    @staticmethod
    def complete_payout(payout):
        """
        Завершить выплату.
        """
        payout.status = 'completed'
        payout.save(update_fields=['status'])
        
        # Обновить статистику партнёра
        profile = getattr(payout.partner, 'partner_profile', None)
        if profile:
            profile.total_withdrawn += payout.amount
            profile.save(update_fields=['total_withdrawn', 'last_payout_at'])

    @staticmethod
    def reject_payout(payout, reason, processed_by):
        """
        Отклонить выплату и вернуть средства.
        """
        with transaction.atomic():
            payout.status = 'rejected'
            payout.rejection_reason = reason
            payout.processed_by = processed_by
            payout.processed_at = now()
            payout.save()
            
            # Вернуть средства
            profile = getattr(payout.partner, 'partner_profile', None)
            if profile:
                profile.balance += payout.amount
                profile.save(update_fields=['balance'])
            
            # Открепить комиссии
            Commission.objects.filter(payout=payout).update(payout=None)

    @staticmethod
    def auto_complete_payouts_for_game_balance():
        """
        Celery задача: автоматически завершить выплаты на игровой баланс.
        Вывод на игровой баланс не требует обработки, сразу завершается.
        """
        pending_payouts = PartnerPayout.objects.filter(
            status='pending',
            payout_method='game_balance'
        )
        
        for payout in pending_payouts:
            payout.status = 'completed'
            payout.processed_at = now()
            payout.save(update_fields=['status', 'processed_at'])
            
            # Обновить статистику
            profile = getattr(payout.partner, 'partner_profile', None)
            if profile:
                profile.total_withdrawn += payout.amount
                profile.last_payout_at = now()
                profile.save(update_fields=['total_withdrawn', 'last_payout_at'])
