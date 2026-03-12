"""
Сервис расчёта ставок после завершения события.
"""
import logging
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError

from apps.sports.models import (
    Bet, BetItem, Event, Market, Outcome, MarketType
)
from apps.wallet.services import TransactionService

logger = logging.getLogger(__name__)


class SettlementError(Exception):
    """Ошибка при расчёте ставок"""
    pass


class SettlementService:
    """Сервис расчёта ставок"""

    # Коэффициент при отмене ставки в экспрессе (возврат)
    VOID_ODD = Decimal('1.0')

    @staticmethod
    @transaction.atomic
    def settle_event(event_id, result_data, settled_by=None):
        """
        Рассчитать все ставки на событие.

        Args:
            event_id: UUID события
            result_data: dict с результатом события
            settled_by: User объект (админ) или None (автоматически)

        Returns:
            dict со статистикой расчёта
        """
        try:
            event = Event.objects.select_for_update().get(id=event_id)
        except Event.DoesNotExist:
            raise SettlementError("Событие не найдено")

        if event.status == 'finished':
            raise SettlementError("Событие уже рассчитано")

        # 1. Обновить событие
        event.status = 'finished'
        event.home_score = result_data.get('home_score')
        event.away_score = result_data.get('away_score')
        event.result_details = result_data
        event.end_time = timezone.now()
        event.settled_by = settled_by
        event.settled_at = timezone.now()
        event.save()

        logger.info(
            f"Событие {event_id} завершено: {event.home_score}:{event.away_score}"
        )

        # 2. Рассчитать все маркеты события
        for market in event.markets.all():
            SettlementService._settle_market(market, result_data)

        # 3. Рассчитать все ставки
        affected_bets = Bet.objects.filter(
            items__event=event,
            status='pending'
        ).distinct().select_for_update()

        settled_count = 0
        won_count = 0
        lost_count = 0
        void_count = 0

        for bet in affected_bets:
            try:
                SettlementService._settle_bet(bet)
                settled_count += 1

                if bet.status == 'won':
                    won_count += 1
                elif bet.status == 'lost':
                    lost_count += 1
                elif bet.status == 'void':
                    void_count += 1
            except Exception as e:
                logger.error(
                    f"Ошибка при расчёте ставки {bet.bet_id}: {str(e)}"
                )

        logger.info(
            f"Событие {event_id}: рассчитано {settled_count} ставок "
            f"(выиграно: {won_count}, проиграно: {lost_count}, аннулировано: {void_count})"
        )

        return {
            "event_id": str(event_id),
            "settled_count": settled_count,
            "won_count": won_count,
            "lost_count": lost_count,
            "void_count": void_count,
            "total_stake": float(event.total_stake),
            "message": f"✅ Событие рассчитано. Затронуто ставок: {settled_count}"
        }

    @staticmethod
    def _settle_market(market, result_data):
        """
        Определить результат каждого исхода в маркете.

        Args:
            market: Market объект
            result_data: dict с результатом события
        """
        home_score = result_data.get('home_score', 0)
        away_score = result_data.get('away_score', 0)
        market_type = market.market_type.code

        # Маршрутизация по типу маркета
        if market_type == '1x2':
            SettlementService._settle_1x2(market, home_score, away_score)
        elif market_type == '12':
            SettlementService._settle_12(market, home_score, away_score)
        elif market_type == 'total':
            SettlementService._settle_total(market, home_score, away_score)
        elif market_type == 'handicap':
            SettlementService._settle_handicap(market, home_score, away_score)
        elif market_type == 'both_to_score':
            SettlementService._settle_both_to_score(market, home_score, away_score)
        elif market_type == 'double_chance':
            SettlementService._settle_double_chance(market, home_score, away_score)
        elif market_type == 'exact_score':
            SettlementService._settle_exact_score(market, home_score, away_score)
        elif market_type == 'ht_result':
            ht_home = result_data.get('ht_home_score', 0)
            ht_away = result_data.get('ht_away_score', 0)
            SettlementService._settle_1x2(market, ht_home, ht_away)
        else:
            # По умолчанию тип 1x2
            SettlementService._settle_1x2(market, home_score, away_score)

        # Отметить маркет рассчитанным
        market.status = 'settled'
        market.settled_at = timezone.now()
        market.save()

    @staticmethod
    def _settle_1x2(market, home_score, away_score):
        """Расчёт маркета 1X2 (Исход матча)"""
        outcomes = {o.code: o for o in market.outcomes.all()}

        if home_score > away_score:
            if 'home' in outcomes:
                outcomes['home'].result = 'won'
            if 'draw' in outcomes:
                outcomes['draw'].result = 'lost'
            if 'away' in outcomes:
                outcomes['away'].result = 'lost'
        elif home_score == away_score:
            if 'home' in outcomes:
                outcomes['home'].result = 'lost'
            if 'draw' in outcomes:
                outcomes['draw'].result = 'won'
            if 'away' in outcomes:
                outcomes['away'].result = 'lost'
        else:
            if 'home' in outcomes:
                outcomes['home'].result = 'lost'
            if 'draw' in outcomes:
                outcomes['draw'].result = 'lost'
            if 'away' in outcomes:
                outcomes['away'].result = 'won'

        for outcome in outcomes.values():
            outcome.settled_at = timezone.now()
            outcome.save()

    @staticmethod
    def _settle_12(market, home_score, away_score):
        """Расчёт маркета 12 (Победитель для баскетбола/тенниса)"""
        outcomes = {o.code: o for o in market.outcomes.all()}

        if home_score > away_score:
            if 'home' in outcomes:
                outcomes['home'].result = 'won'
            if 'away' in outcomes:
                outcomes['away'].result = 'lost'
        else:
            if 'home' in outcomes:
                outcomes['home'].result = 'lost'
            if 'away' in outcomes:
                outcomes['away'].result = 'won'

        for outcome in outcomes.values():
            outcome.settled_at = timezone.now()
            outcome.save()

    @staticmethod
    def _settle_total(market, home_score, away_score):
        """Расчёт маркета Total (Тотал)"""
        total_goals = home_score + away_score
        parameter = market.parameter
        outcomes = {o.code: o for o in market.outcomes.all()}

        if parameter is None:
            logger.warning(f"Market {market.id} has no parameter")
            return

        if total_goals > parameter:
            if 'over' in outcomes:
                outcomes['over'].result = 'won'
            if 'under' in outcomes:
                outcomes['under'].result = 'lost'
        elif total_goals < parameter:
            if 'over' in outcomes:
                outcomes['over'].result = 'lost'
            if 'under' in outcomes:
                outcomes['under'].result = 'won'
        else:
            # Точное совпадение - обычно void (возврат)
            if 'over' in outcomes:
                outcomes['over'].result = 'void'
            if 'under' in outcomes:
                outcomes['under'].result = 'void'

        for outcome in outcomes.values():
            outcome.settled_at = timezone.now()
            outcome.save()

    @staticmethod
    def _settle_handicap(market, home_score, away_score):
        """Расчёт маркета Handicap (Фора)"""
        parameter = market.parameter
        outcomes = {o.code: o for o in market.outcomes.all()}

        if parameter is None:
            logger.warning(f"Market {market.id} has no parameter")
            return

        adjusted_home = home_score + parameter

        if adjusted_home > away_score:
            if 'home' in outcomes:
                outcomes['home'].result = 'won'
            if 'away' in outcomes:
                outcomes['away'].result = 'lost'
        elif adjusted_home < away_score:
            if 'home' in outcomes:
                outcomes['home'].result = 'lost'
            if 'away' in outcomes:
                outcomes['away'].result = 'won'
        else:
            if 'home' in outcomes:
                outcomes['home'].result = 'void'
            if 'away' in outcomes:
                outcomes['away'].result = 'void'

        for outcome in outcomes.values():
            outcome.settled_at = timezone.now()
            outcome.save()

    @staticmethod
    def _settle_both_to_score(market, home_score, away_score):
        """Расчёт маркета Both to Score (Обе забьют)"""
        outcomes = {o.code: o for o in market.outcomes.all()}

        if home_score > 0 and away_score > 0:
            if 'yes' in outcomes:
                outcomes['yes'].result = 'won'
            if 'no' in outcomes:
                outcomes['no'].result = 'lost'
        else:
            if 'yes' in outcomes:
                outcomes['yes'].result = 'lost'
            if 'no' in outcomes:
                outcomes['no'].result = 'won'

        for outcome in outcomes.values():
            outcome.settled_at = timezone.now()
            outcome.save()

    @staticmethod
    def _settle_double_chance(market, home_score, away_score):
        """Расчёт маркета Double Chance (Двойной шанс)"""
        outcomes = {o.code: o for o in market.outcomes.all()}

        if home_score > away_score:
            # Победа хозяев
            if '1x' in outcomes:
                outcomes['1x'].result = 'won'
            if '12' in outcomes:
                outcomes['12'].result = 'won'
            if 'x2' in outcomes:
                outcomes['x2'].result = 'lost'
        elif home_score == away_score:
            # Ничья
            if '1x' in outcomes:
                outcomes['1x'].result = 'won'
            if '12' in outcomes:
                outcomes['12'].result = 'lost'
            if 'x2' in outcomes:
                outcomes['x2'].result = 'won'
        else:
            # Победа гостей
            if '1x' in outcomes:
                outcomes['1x'].result = 'lost'
            if '12' in outcomes:
                outcomes['12'].result = 'won'
            if 'x2' in outcomes:
                outcomes['x2'].result = 'won'

        for outcome in outcomes.values():
            outcome.settled_at = timezone.now()
            outcome.save()

    @staticmethod
    def _settle_exact_score(market, home_score, away_score):
        """Расчёт маркета Exact Score (Точный счёт)"""
        score_key = f"{home_score}-{away_score}"
        outcomes = market.outcomes.all()

        for outcome in outcomes:
            if outcome.code == score_key or outcome.code == f"{home_score}:{away_score}":
                outcome.result = 'won'
            elif outcome.code != 'other':
                outcome.result = 'lost'
            else:
                # 'other' выигрывает если счёта нет в списке
                outcome.result = 'won' if score_key not in [o.code for o in outcomes] else 'lost'

            outcome.settled_at = timezone.now()
            outcome.save()

    @staticmethod
    @transaction.atomic
    def _settle_bet(bet):
        """
        Рассчитать конкретную ставку.

        Args:
            bet: Bet объект
        """
        # 1. Обновить BetItem результаты
        for item in bet.items.all():
            if item.outcome.result != 'pending':
                item.result = item.outcome.result
                item.settled_at = timezone.now()
                item.save()

        # 2. Подсчитать результаты
        items_won = bet.items.filter(result='won').count()
        items_lost = bet.items.filter(result='lost').count()
        items_void = bet.items.filter(result='void').count()
        items_pending = bet.items.filter(result='pending').count()

        # 3. Если есть ещё ожидающие события - не рассчитываем
        if items_pending > 0:
            bet.items_won = items_won
            bet.items_lost = items_lost
            bet.items_void = items_void
            bet.items_pending = items_pending
            bet.save()
            return

        # 4. Определить результат ставки
        if bet.bet_type == 'single':
            SettlementService._settle_single_bet(bet, items_won, items_lost, items_void)
        else:  # combo, system
            SettlementService._settle_combo_bet(bet, items_won, items_lost, items_void)

        # 5. Денежные операции
        SettlementService._process_payment(bet)

        # 6. Установить время расчёта
        bet.settled_at = timezone.now()
        bet.cashout_available = False
        bet.items_won = items_won
        bet.items_lost = items_lost
        bet.items_void = items_void
        bet.items_pending = items_pending
        bet.save()

        # 7. Уведомить пользователя
        SettlementService._notify_user(bet)

        logger.info(f"Ставка {bet.bet_id} рассчитана: статус={bet.status}")

    @staticmethod
    def _settle_single_bet(bet, items_won, items_lost, items_void):
        """Расчёт одиночной ставки"""
        if items_won == 1:
            bet.status = 'won'
            item = bet.items.get(result='won')
            bet.actual_win = bet.stake * item.odd_at_placement
        elif items_lost == 1:
            bet.status = 'lost'
            bet.actual_win = Decimal('0.00')
        elif items_void == 1:
            bet.status = 'void'
            bet.actual_win = bet.stake  # Возврат
        else:
            bet.status = 'void'
            bet.actual_win = bet.stake

        bet.profit = bet.actual_win - bet.stake

    @staticmethod
    def _settle_combo_bet(bet, items_won, items_lost, items_void):
        """Расчёт экспресс-ставки"""
        if items_lost > 0:
            # Есть проигравшие исходы - вся ставка проиграла
            bet.status = 'lost'
            bet.actual_win = Decimal('0.00')
        elif items_void > 0 and items_won > 0:
            # Есть аннулированные (void) исходы - пересчитать коэффициент
            adjusted_odd = Decimal('1.0')
            for item in bet.items.all():
                if item.result == 'won':
                    adjusted_odd *= item.odd_at_placement
                # void = коэффициент 1.0, не влияет

            if adjusted_odd > 1:
                bet.status = 'won'
                bet.actual_win = bet.stake * adjusted_odd
            else:
                bet.status = 'void'
                bet.actual_win = bet.stake
        elif items_won == bet.items_count and items_void == 0:
            # Все выиграли
            bet.status = 'won'
            bet.actual_win = bet.stake * bet.total_odd
        elif items_void == bet.items_count:
            # Все аннулировано
            bet.status = 'void'
            bet.actual_win = bet.stake
        else:
            # Неопределённое состояние
            bet.status = 'pending'
            bet.actual_win = Decimal('0.00')

        bet.profit = bet.actual_win - bet.stake

    @staticmethod
    def _process_payment(bet):
        """Обработать денежные операции"""
        if bet.status == 'won':
            # Выигрыш: забрать frozen и зачислить выигрыш
            TransactionService.settle_bet(
                wallet=bet.wallet,
                currency_code=bet.currency.code,
                frozen_amount=bet.stake,
                win_amount=bet.actual_win,
                reference_type='bet',
                reference_id=bet.bet_id
            )
        elif bet.status == 'lost':
            # Проигрыш: забрать frozen
            TransactionService.settle_bet(
                wallet=bet.wallet,
                currency_code=bet.currency.code,
                frozen_amount=bet.stake,
                win_amount=Decimal('0.00'),
                reference_type='bet',
                reference_id=bet.bet_id
            )
        elif bet.status == 'void':
            # Возврат: разморозить
            if bet.freeze_transaction:
                TransactionService.unfreeze_funds(
                    transaction_id=bet.freeze_transaction.id,
                    reason="Ставка аннулирована"
                )

    @staticmethod
    def _notify_user(bet):
        """Отправить уведомление пользователю о результате"""
        # TODO: Отправить уведомление через систему уведомлений
        if bet.status == 'won':
            message = f"🏆 Ставка {bet.bet_id} выиграла! +${bet.actual_win:.2f}"
        elif bet.status == 'lost':
            message = f"❌ Ставка {bet.bet_id} проиграла"
        elif bet.status == 'void':
            message = f"↩️ Ставка {bet.bet_id} аннулирована. Возврат: ${bet.actual_win:.2f}"
        else:
            message = f"Ставка {bet.bet_id}: статус {bet.status}"

        logger.info(f"Уведомление пользователю {bet.user.id}: {message}")

    @staticmethod
    @transaction.atomic
    def void_event(event_id, admin_user, reason):
        """
        Аннулировать событие (отмена матча).
        ВСЕ ставки возвращаются.

        Args:
            event_id: UUID события
            admin_user: User объект админа
            reason: Причина аннулирования

        Returns:
            dict со статистикой
        """
        try:
            event = Event.objects.select_for_update().get(id=event_id)
        except Event.DoesNotExist:
            raise SettlementError("Событие не найдено")

        event.status = 'cancelled'
        event.settled_at = timezone.now()
        event.settled_by = admin_user
        event.save()

        # Аннулировать все маркеты и исходы
        for market in event.markets.all():
            market.status = 'void'
            market.settled_at = timezone.now()
            market.save()

            for outcome in market.outcomes.all():
                outcome.result = 'void'
                outcome.settled_at = timezone.now()
                outcome.save()

        # Вернуть все ставки
        affected_bets = Bet.objects.filter(
            items__event=event,
            status='pending'
        ).distinct()

        voided_count = 0
        for bet in affected_bets:
            # Отметить все items как void
            bet.items.all().update(result='void', settled_at=timezone.now())

            # Установить ставку как void
            bet.status = 'void'
            bet.actual_win = bet.stake
            bet.profit = Decimal('0.00')
            bet.settled_at = timezone.now()
            bet.cashout_available = False
            bet.save()

            # Разморозить средства
            if bet.freeze_transaction:
                TransactionService.unfreeze_funds(
                    transaction_id=bet.freeze_transaction.id,
                    reason=f"Событие отменено: {reason}"
                )

            voided_count += 1

        logger.info(
            f"Событие {event_id} аннулировано. Возвращено ставок: {voided_count}"
        )

        return {
            "event_id": str(event_id),
            "status": "cancelled",
            "voided_bets": voided_count,
            "message": f"✅ Событие аннулировано. Возвращено ставок: {voided_count}"
        }
