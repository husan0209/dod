"""
Сервис обработки кэшаута (досрочного расчёта) ставок.
"""
import logging
from decimal import Decimal
from django.db import transaction
from django.utils import timezone

from apps.sports.models import Bet, BetSettings
from apps.wallet.services import TransactionService

logger = logging.getLogger(__name__)


class CashoutError(Exception):
    """Ошибка при кэшауте"""
    pass


class CashoutService:
    """Сервис обработки кэшаута"""

    @staticmethod
    def calculate_cashout_amount(bet):
        """
        Рассчитать текущую сумму кэшаута для ставки.

        Args:
            bet: Bet объект

        Returns:
            Decimal сумма кэшаута или 0 если недоступен
        """
        if not bet.is_cashout_available():
            return Decimal('0.00')

        settings = BetSettings.get_settings()
        return bet.calculate_cashout_amount()

    @staticmethod
    @transaction.atomic
    def place_cashout(bet_id, user):
        """
        Принять кэшаут для ставки.

        Args:
            bet_id: UUID ставки
            user: User объект

        Returns:
            dict с результатом
        """
        try:
            bet = Bet.objects.select_for_update().get(id=bet_id)
        except Bet.DoesNotExist:
            raise CashoutError("Ставка не найдена")

        # Проверить что это ставка пользователя
        if bet.user.id != user.id:
            raise CashoutError("Это не ваша ставка")

        # Проверить доступность кэшаута
        if not bet.is_cashout_available():
            raise CashoutError("Кэшаут недоступен для этой ставки")

        # Рассчитать сумму
        cashout_amount = CashoutService.calculate_cashout_amount(bet)

        if cashout_amount <= 0:
            raise CashoutError(
                f"Сумма кэшаута слишком мала (минимум: ${BetSettings.get_settings().cashout_min_amount_usd})"
            )

        # Выполнить кэшаут
        bet.status = 'cashed_out'
        bet.cashout_amount = cashout_amount
        bet.cashout_used_at = timezone.now()
        bet.actual_win = cashout_amount
        bet.profit = cashout_amount - bet.stake
        bet.settled_at = timezone.now()
        bet.cashout_available = False
        bet.save()

        # Обработать платёж
        if bet.freeze_transaction:
            TransactionService.unfreeze_funds(
                transaction_id=bet.freeze_transaction.id,
                reason="Кэшаут"
            )

        # Зачислить сумму кэшаута
        TransactionService.create_transaction(
            wallet=bet.wallet,
            transaction_type='cashout',
            currency_code=bet.currency.code,
            amount=cashout_amount,
            reference_type='bet',
            reference_id=bet.bet_id,
            description=f"Кэшаут ставки {bet.bet_id}"
        )

        logger.info(
            f"Кэшаут выполнен: ставка {bet.bet_id}, "
            f"сумма: ${cashout_amount:.2f}"
        )

        return {
            "success": True,
            "bet_id": str(bet.bet_id),
            "cashout_amount": float(cashout_amount),
            "profit": float(bet.profit),
            "currency": bet.currency.code,
            "message": f"✅ Кэшаут завершён! +${cashout_amount:.2f}"
        }

    @staticmethod
    def get_cashout_info(bet):
        """
        Получить информацию о кэшауте для ставки.

        Args:
            bet: Bet объект

        Returns:
            dict с информацией
        """
        cashout_amount = CashoutService.calculate_cashout_amount(bet)
        cashout_available = bet.is_cashout_available()

        return {
            "bet_id": str(bet.bet_id),
            "available": cashout_available,
            "amount": float(cashout_amount),
            "currency": bet.currency.code,
            "potential_win": float(bet.potential_win),
            "profit_if_cashout": float(cashout_amount - bet.stake),
            "profit_if_win": float(bet.potential_win - bet.stake),
            "items_pending": bet.items_pending,
            "items_won": bet.items_won,
            "items_lost": bet.items_lost,
        }
