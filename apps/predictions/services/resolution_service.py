from decimal import Decimal
from django.db import transaction
from django.utils import timezone

from apps.wallet.services.transaction_service import TransactionService
from ..models import PredictionMarket, Position, PredictionSettings, MarketDispute


class ResolutionService:
    """
    Резолвинг маркетов и расчёт позиций.
    """

    @staticmethod
    @transaction.atomic
    def resolve_market(market_id, resolution, resolved_by, evidence, evidence_url=None):
        """
        Разрешить маркет.
        """
        try:
            market = PredictionMarket.objects.select_for_update().get(id=market_id)
        except PredictionMarket.DoesNotExist:
            raise ValueError("Маркет не найден")

        if market.status in ('resolved', 'voided', 'cancelled'):
            raise ValueError(f"Маркет уже в статусе: {market.status}")

        if resolution not in ('yes', 'no'):
            raise ValueError("Некорректное значение резолюции")

        # Обновить маркет
        market.status = 'resolved'
        market.resolution = resolution
        market.resolved_by = resolved_by
        market.resolved_at = timezone.now()
        market.resolution_evidence = evidence
        market.resolution_evidence_url = evidence_url

        # Установить цены на 1.00 и 0.00
        if resolution == 'yes':
            market.yes_price = Decimal('1.00')
            market.no_price = Decimal('0.00')
        else:  # 'no'
            market.yes_price = Decimal('0.00')
            market.no_price = Decimal('1.00')

        market.save()

        # Рассчитать все позиции
        ResolutionService.settle_all_positions(market)

        return {
            "market_id": str(market.id),
            "question": market.question,
            "resolution": resolution,
            "resolved_at": market.resolved_at.isoformat()
        }

    @staticmethod
    @transaction.atomic
    def settle_all_positions(market):
        """
        Рассчитать все позиции после резолвинга.
        """
        winning_side = market.resolution

        positions = Position.objects.filter(
            market=market, shares__gt=0, is_settled=False
        ).select_related('user__wallet')

        for position in positions:
            if position.side == winning_side:
                # ВЫИГРЫШ: каждая акция = $1.00
                payout = position.shares * Decimal('1.00')
                position.settlement_amount = payout

                try:
                    TransactionService.deposit(
                        wallet=position.user.wallet,
                        currency_code='USD',
                        amount=float(payout),
                        type='win',
                        description=f"Prediction Market: {market.question[:50]} → {winning_side.upper()}",
                        reference_type='prediction_resolution',
                        reference_id=market.market_id
                    )
                except Exception as e:
                    print(f"Error depositing settlement: {str(e)}")

            else:
                # ПРОИГРЫШ: акции = $0.00
                position.settlement_amount = Decimal('0')

            position.is_settled = True
            position.save()

    @staticmethod
    @transaction.atomic
    def void_market(market_id, admin_user, reason):
        """
        Аннулировать маркет (вернуть всем деньги).
        """
        try:
            market = PredictionMarket.objects.select_for_update().get(id=market_id)
        except PredictionMarket.DoesNotExist:
            raise ValueError("Маркет не найден")

        market.status = 'voided'
        market.resolution_evidence = f"Маркет аннулирован. Причина: {reason}"
        market.resolved_by = admin_user
        market.resolved_at = timezone.now()
        market.save()

        positions = Position.objects.filter(
            market=market, is_settled=False
        ).select_related('user__wallet')

        for position in positions:
            # Вернуть инвестированную сумму
            refund_amount = position.total_invested - position.total_returned

            if refund_amount > Decimal('0'):
                try:
                    TransactionService.deposit(
                        wallet=position.user.wallet,
                        currency_code='USD',
                        amount=float(refund_amount),
                        type='refund',
                        description=f"Prediction Market refund: {market.question[:50]}",
                        reference_type='prediction_void',
                        reference_id=market.market_id
                    )
                except Exception as e:
                    print(f"Error refunding: {str(e)}")

            position.is_settled = True
            position.settlement_amount = refund_amount
            position.save()

        return {
            "market_id": str(market.id),
            "status": "voided",
            "reason": reason
        }

    @staticmethod
    @transaction.atomic
    def dispute_resolution(market_id, user, reason, evidence_url):
        """
        Оспорить результат маркета.
        """
        try:
            market = PredictionMarket.objects.get(id=market_id)
        except PredictionMarket.DoesNotExist:
            raise ValueError("Маркет не найден")

        if market.status != 'resolved':
            raise ValueError("Можно оспаривать только разрешённые маркеты")

        settings = PredictionSettings.get_settings()
        dispute_window = timezone.timedelta(hours=settings.resolution_dispute_window_hours)
        
        if timezone.now() > market.resolved_at + dispute_window:
            raise ValueError(f"Окно оспаривания истекло ({settings.resolution_dispute_window_hours} часов)")

        has_position = Position.objects.filter(
            user=user, market=market, shares__gt=0
        ).exists()
        
        if not has_position:
            raise ValueError("Для оспаривания вы должны иметь позицию в маркете")

        dispute = MarketDispute.objects.create(
            market=market,
            user=user,
            reason=reason,
            evidence_url=evidence_url
        )

        market.status = 'disputed'
        market.save(update_fields=['status'])

        return {
            "dispute_id": str(dispute.id),
            "market_id": str(market.id),
            "status": "pending_review"
        }

    @staticmethod
    def close_expired_markets():
        """Закрыть истекшие маркеты и перевести в ожидание резолюции."""
        now = timezone.now()
        updated = PredictionMarket.objects.filter(
            status='active',
            close_date__lt=now
        ).update(status='pending_resolution')

        return updated

    @staticmethod
    def review_dispute(dispute_id, admin_user, approved):
        """
        Рассмотреть спор по маркету.
        """
        try:
            dispute = MarketDispute.objects.get(id=dispute_id)
        except MarketDispute.DoesNotExist:
            raise ValueError("Dispute not found")

        dispute.reviewed = True
        dispute.reviewed_at = timezone.now()
        dispute.reviewed_by = admin_user
        dispute.approved = approved
        dispute.save()

        market = dispute.market

        if approved:
            # Отменить результат и вернуть деньги
            ResolutionService.void_market(market.id, admin_user, "Dispute approved")
            return {
                "status": "approved",
                "action": "market_voided"
            }
        else:
            # Подтвердить результат
            market.status = 'resolved'
            market.save(update_fields=['status'])
            return {
                "status": "rejected",
                "action": "resolution_confirmed"
            }

