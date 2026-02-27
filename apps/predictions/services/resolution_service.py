from django.db import transaction
from django.utils import timezone

from apps.wallet.services.transaction_service import TransactionService

from ..models import Market, UserPosition


def notify(user, message):
    # Placeholder: implement notification system (email, push, etc.)
    pass


class ResolutionService:
    """
    Резолвинг маркетов и расчёт позиций.
    """

    @staticmethod
    @transaction.atomic
    def resolve_market(market_id, resolution, resolved_by, evidence, evidence_url=None):
        """
        Разрешить маркет.
        resolution: 'yes' или 'no'
        """
        market = PredictionMarket.objects.select_for_update().get(id=market_id)
        
        if market.status not in ('active', 'pending_resolution'):
            raise ValueError("Market cannot be resolved")

        market.status = 'resolved'
        market.resolution = resolution
        market.resolved_by = resolved_by
        market.resolved_at = timezone.now()
        market.resolution_evidence = evidence
        market.resolution_evidence_url = evidence_url

        # Set final prices
        if resolution == 'yes':
            market.yes_price = 1.00
            market.no_price = 0.00
        else:
            market.yes_price = 0.00
            market.no_price = 1.00

        market.save()

        # Рассчитать все позиции
        ResolutionService.settle_all_positions(market)

        # Уведомить всех трейдеров (placeholder)
        # In real implementation, notify all users with positions

        return market

    @staticmethod
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

                TransactionService.deposit(
                    wallet=position.user.wallet,
                    currency_code='USD',
                    amount=payout,
                    type='win',
                    description=f"Prediction Market: {market.question[:50]} → {winning_side.upper()}",
                    reference_type='prediction_resolution',
                    reference_id=str(market.market_id)
                )

                position.settlement_amount = payout
                notify(position.user, f"🏆 Маркет разрешён! Вы получили ${position.settlement_amount:.2f}")
            else:
                # ПРОИГРЫШ: акции = $0.00
                position.settlement_amount = 0
                notify(position.user, f"❌ Маркет разрешён как {winning_side.upper()}. Ваши {position.side.upper()} акции = $0")

            position.is_settled = True
            position.save()

    @staticmethod
    @transaction.atomic
    def void_market(market_id, admin_user, reason):
        """
        Аннулировать маркет (вернуть всем деньги).
        """
        market = PredictionMarket.objects.select_for_update().get(id=market_id)
        market.status = 'voided'
        market.resolution_evidence = reason
        market.resolved_by = admin_user
        market.resolved_at = timezone.now()
        market.save()

        positions = Position.objects.filter(
            market=market, shares__gt=0, is_settled=False
        ).select_related('user__wallet')

        for position in positions:
            # Вернуть total_invested - total_returned
            refund_amount = position.total_invested - position.total_returned

            if refund_amount > 0:
                TransactionService.deposit(
                    wallet=position.user.wallet,
                    currency_code='USD',
                    amount=refund_amount,
                    type='refund',
                    description=f"Prediction Market Voided: {market.question[:50]}",
                    reference_type='prediction_void',
                    reference_id=str(market.market_id)
                )

            position.is_settled = True
            position.settlement_amount = refund_amount
            position.save()

            notify(position.user, f"🚫 Маркет аннулирован. Возвращено ${refund_amount:.2f}")

    @staticmethod
    def dispute_resolution(market_id, user, reason, evidence_url):
        """
        Оспорить результат.
        """
        market = PredictionMarket.objects.get(id=market_id)
        if market.status != 'resolved':
            raise ValueError("Market is not resolved")

        # Check if within dispute window
        from ..models import PredictionSettings
        settings = PredictionSettings.get_settings()
        dispute_window = timezone.timedelta(hours=settings.resolution_dispute_window_hours)
        
        if timezone.now() > market.resolved_at + dispute_window:
            raise ValueError("Dispute window has expired")

        # Check if user has position
        has_position = Position.objects.filter(
            user=user, market=market, shares__gt=0
        ).exists()
        if not has_position:
            raise ValueError("User has no position in this market")

        MarketDispute.objects.create(
            market=market,
            user=user,
            reason=reason,
            evidence_url=evidence_url
        )

        market.status = 'disputed'
        market.save()

        # Уведомить админов (placeholder)
        # notify_admins(f"New dispute for market {market.market_id}")
