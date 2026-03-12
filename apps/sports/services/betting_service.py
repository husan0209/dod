"""
Сервис приёма и обработки ставок.
КРИТИЧНЫЙ сервис - все операции АТОМАРНЫЕ.
"""
import uuid
import logging
from decimal import Decimal
from django.db import transaction, models
from django.utils import timezone
from django.core.exceptions import ValidationError

from apps.sports.models import (
    Bet, BetItem, Event, Market, Outcome, BetSettings, Sport
)
from apps.wallet.services import TransactionService
from apps.wallet.models import Wallet, Currency

logger = logging.getLogger(__name__)


class BettingError(Exception):
    """Базовый класс для ошибок ставок"""
    pass


class EventNotBettableError(BettingError):
    """Событие не доступно для ставок"""
    pass


class MarketClosedError(BettingError):
    """Маркет закрыт"""
    pass


class OutcomeSuspendedError(BettingError):
    """Исход приостановлен"""
    pass


class InsufficientFundsError(BettingError):
    """Недостаточно средств"""
    pass


class StakeLimitError(BettingError):
    """Превышен лимит ставки"""
    pass


class WinLimitError(BettingError):
    """Превышен максимальный выигрыш"""
    pass


class BetLimitError(BettingError):
    """Превышен лимит ставок на событие"""
    pass


class OddChangedError(BettingError):
    """Коэффициент изменился"""
    pass


class WalletFrozenError(BettingError):
    """Кошелёк заморожен"""
    pass


class BettingService:
    """Сервис обработки ставок"""

    @staticmethod
    def _generate_bet_id():
        """Генерировать уникальный ID ставки"""
        timestamp = timezone.now().strftime('%Y%m%d')
        random_part = ''.join(str(uuid.uuid4()).split('-')[0][:6].upper())
        return f"BET-{timestamp}-{random_part}"

    @staticmethod
    def _validate_event(event):
        """Валидировать событие"""
        if not event or event.status != 'prematch':
            raise EventNotBettableError("Ставки на это событие закрыты")
        
        settings = BetSettings.get_settings()
        time_until_start = event.start_time - timezone.now()
        delay_seconds = settings.delay_before_start_minutes * 60
        
        if time_until_start.total_seconds() <= delay_seconds:
            raise EventNotBettableError(
                f"Событие уже началось. Ставки закрыты за {settings.delay_before_start_minutes} мин. до начала"
            )

    @staticmethod
    def _validate_market(market):
        """Валидировать маркет"""
        if market.status != 'open':
            raise MarketClosedError("Маркет закрыт")

    @staticmethod
    def _validate_outcome(outcome, max_stake_usd=None):
        """Валидировать исход"""
        if not outcome.is_active:
            raise OutcomeSuspendedError("Исход недоступен")
        
        if outcome.is_suspended:
            raise OutcomeSuspendedError("Исход временно приостановлен")
        
        settings = BetSettings.get_settings()
        if outcome.odd < settings.min_odd or outcome.odd > settings.max_odd:
            raise OddChangedError("Коэффициент вышел за допустимые пределы")

    @staticmethod
    def _validate_stake(stake, currency, potential_win_usd, outcome=None):
        """Валидировать сумму ставки"""
        settings = BetSettings.get_settings()
        
        # Минимум и максимум ставки
        if stake < settings.min_stake_usd:
            raise StakeLimitError(
                f"Минимальная ставка: ${settings.min_stake_usd}"
            )
        
        if stake > settings.max_stake_usd:
            raise StakeLimitError(
                f"Максимальная ставка: ${settings.max_stake_usd}"
            )
        
        # Проверить максимум для исхода
        if outcome and outcome.max_stake and stake > outcome.max_stake:
            raise StakeLimitError(
                f"Максимум на этот исход: ${outcome.max_stake}"
            )
        
        # Максимальный выигрыш
        if potential_win_usd > settings.max_potential_win_usd:
            raise WinLimitError(
                f"Максимальный выигрыш: ${settings.max_potential_win_usd}. "
                f"Уменьшите ставку или коэффициент превышен"
            )

    @staticmethod
    def _validate_wallet(wallet, currency_code, stake):
        """Валидировать кошелёк"""
        if wallet.is_frozen:
            raise WalletFrozenError("Ваш кошелёк заморожен. Обратитесь в поддержку")
        
        if not wallet.has_sufficient_balance(currency_code, stake):
            balance = wallet.get_balance(currency_code)
            raise InsufficientFundsError(
                f"Недостаточно средств. Баланс: ${balance}. Требуется: ${stake}"
            )

    @staticmethod
    def _validate_user_event_limit(user, event):
        """Проверить лимит ставок на событие"""
        settings = BetSettings.get_settings()
        user_bets_count = Bet.objects.filter(
            user=user,
            items__event=event,
            status='pending'
        ).distinct().count()
        
        if user_bets_count >= settings.max_bets_per_event_per_user:
            raise BetLimitError(
                f"Вы уже сделали {user_bets_count} ставок на это событие"
            )

    @staticmethod
    @transaction.atomic
    def place_single_bet(user, outcome_id, stake, currency_code, ip_address, user_agent=None):
        """
        Разместить одиночную ставку.

        Args:
            user: User object
            outcome_id: UUID исхода
            stake: Decimal сумма ставки в валюте
            currency_code: Код валюты (USD, EUR и т.д.)
            ip_address: IP адрес пользователя
            user_agent: User-Agent браузера

        Returns:
            dict с результатом

        Raises:
            BettingError и наследники
        """
        # 1. Получить данные с блокировкой
        try:
            outcome = Outcome.objects.select_for_update().get(id=outcome_id)
        except Outcome.DoesNotExist:
            raise BettingError("Исход не найден")

        market = outcome.market
        event = market.event
        settings = BetSettings.get_settings()
        wallet = user.wallet

        try:
            currency = Currency.objects.get(code=currency_code)
        except Currency.DoesNotExist:
            raise BettingError(f"Валюта {currency_code} не поддерживается")

        # 2. Валидация
        BettingService._validate_event(event)
        BettingService._validate_market(market)
        BettingService._validate_outcome(outcome, outcome.max_stake)
        
        # Конвертировать ставку в USD
        stake_decimal = Decimal(str(stake))
        stake_usd = wallet.convert_to_usd(currency_code, stake_decimal)
        potential_win_usd = stake_usd * outcome.odd
        
        BettingService._validate_stake(
            stake_usd, currency, potential_win_usd, outcome
        )
        BettingService._validate_wallet(wallet, currency_code, stake_decimal)
        BettingService._validate_user_event_limit(user, event)

        # 3. Заморозить средства
        freeze_tx = TransactionService.freeze_funds(
            wallet=wallet,
            currency_code=currency_code,
            amount=stake_decimal,
            reference_type='bet',
            description=f"Ставка на {event}"
        )

        # 4. Создать ставку
        bet_id = BettingService._generate_bet_id()
        bet = Bet.objects.create(
            bet_id=bet_id,
            user=user,
            wallet=wallet,
            bet_type='single',
            currency=currency,
            stake=stake_decimal,
            stake_usd=stake_usd,
            total_odd=outcome.odd,
            potential_win=stake_usd * outcome.odd,
            status='pending',
            items_count=1,
            items_pending=1,
            cashout_available=settings.cashout_enabled,
            freeze_transaction=freeze_tx,
            ip_address=ip_address,
            user_agent=user_agent or ''
        )

        # 5. Создать BetItem
        BetItem.objects.create(
            bet=bet,
            event=event,
            market=market,
            outcome=outcome,
            odd_at_placement=outcome.odd,
            event_name=str(event),
            market_name=market.name,
            outcome_name=outcome.name,
            event_start_time=event.start_time
        )

        # 6. Обновить счётчики
        outcome.bets_count += 1
        outcome.total_stake += stake_usd
        outcome.save(update_fields=['bets_count', 'total_stake'])

        event.bets_count += 1
        event.total_stake += stake_usd
        event.save(update_fields=['bets_count', 'total_stake'])

        logger.info(
            f"Ставка размещена: {bet_id} (пользователь: {user.id}, "
            f"ставка: ${stake_usd}, коэффициент: {outcome.odd})"
        )

        # 7. Вернуть результат
        return {
            "success": True,
            "bet_id": bet.bet_id,
            "status": "pending",
            "stake": float(stake_decimal),
            "stake_usd": float(stake_usd),
            "odd": float(outcome.odd),
            "potential_win": float(bet.potential_win),
            "event": str(event),
            "outcome": outcome.name,
            "market": market.name,
            "message": f"✅ Ставка принята! Потенциальный выигрыш: ${bet.potential_win}"
        }

    @staticmethod
    @transaction.atomic
    def place_combo_bet(user, items, stake, currency_code, ip_address, user_agent=None):
        """
        Разместить экспресс (комбо) ставку.

        Args:
            user: User object
            items: List[{"outcome_id": "..."}]
            stake: Decimal сумма ставки в валюте
            currency_code: Код валюты
            ip_address: IP адрес
            user_agent: User-Agent

        Returns:
            dict с результатом

        Raises:
            BettingError и наследники
        """
        settings = BetSettings.get_settings()
        wallet = user.wallet

        # 1. Валидация количества
        if len(items) < settings.min_combo_items:
            raise BettingError(
                f"Минимум событий в экспрессе: {settings.min_combo_items}"
            )

        if len(items) > settings.max_combo_items:
            raise BettingError(
                f"Максимум событий в экспрессе: {settings.max_combo_items}"
            )

        try:
            currency = Currency.objects.get(code=currency_code)
        except Currency.DoesNotExist:
            raise BettingError(f"Валюта {currency_code} не поддерживается")

        stake_decimal = Decimal(str(stake))

        # 2-3. Валидировать каждый исход и проверить конфликты
        outcomes = []
        event_ids = []
        total_odd = Decimal('1.0')

        for item_data in items:
            try:
                outcome = Outcome.objects.select_for_update().get(
                    id=item_data['outcome_id']
                )
            except Outcome.DoesNotExist:
                raise BettingError("Один из исходов не найден")

            event = outcome.market.event
            event_ids.append(event.id)

            # Валидировать
            BettingService._validate_event(event)
            BettingService._validate_market(outcome.market)
            BettingService._validate_outcome(outcome)

            outcomes.append(outcome)
            total_odd *= outcome.odd

        # Проверить конфликты (два исхода из одного события)
        if len(event_ids) != len(set(event_ids)):
            raise BettingError(
                "Нельзя добавить два исхода из одного события в экспресс"
            )

        # Проверить максимальный коэффициент
        if total_odd > settings.max_odd:
            raise BettingError(
                f"Общий коэффициент превышен. Максимум: {settings.max_odd}"
            )

        # 4-5. Проверить потенциальный выигрыш
        stake_usd = wallet.convert_to_usd(currency_code, stake_decimal)
        potential_win_usd = stake_usd * total_odd

        BettingService._validate_stake(
            stake_usd, currency, potential_win_usd
        )
        BettingService._validate_wallet(wallet, currency_code, stake_decimal)

        # 6. Заморозить средства
        freeze_tx = TransactionService.freeze_funds(
            wallet=wallet,
            currency_code=currency_code,
            amount=stake_decimal,
            reference_type='bet',
            description=f"Экспресс ставка ({len(items)} событий)"
        )

        # 7. Создать ставку
        bet_id = BettingService._generate_bet_id()
        bet = Bet.objects.create(
            bet_id=bet_id,
            user=user,
            wallet=wallet,
            bet_type='combo',
            currency=currency,
            stake=stake_decimal,
            stake_usd=stake_usd,
            total_odd=total_odd,
            potential_win=stake_usd * total_odd,
            status='pending',
            items_count=len(outcomes),
            items_pending=len(outcomes),
            cashout_available=settings.cashout_enabled,
            freeze_transaction=freeze_tx,
            ip_address=ip_address,
            user_agent=user_agent or ''
        )

        # 8. Создать BetItem для каждого исхода
        for outcome in outcomes:
            event = outcome.market.event
            BetItem.objects.create(
                bet=bet,
                event=event,
                market=outcome.market,
                outcome=outcome,
                odd_at_placement=outcome.odd,
                event_name=str(event),
                market_name=outcome.market.name,
                outcome_name=outcome.name,
                event_start_time=event.start_time
            )

        # 9. Обновить счётчики
        for outcome in outcomes:
            outcome.bets_count += 1
            outcome.total_stake += stake_usd
            outcome.save(update_fields=['bets_count', 'total_stake'])

        for event_id in set(event_ids):
            event = Event.objects.get(id=event_id)
            event.bets_count += 1
            event.total_stake += stake_usd
            event.save(update_fields=['bets_count', 'total_stake'])

        logger.info(
            f"Экспресс ставка размещена: {bet_id} ({len(items)} событий, "
            f"коэффициент: {total_odd})"
        )

        return {
            "success": True,
            "bet_id": bet.bet_id,
            "status": "pending",
            "stake": float(stake_decimal),
            "stake_usd": float(stake_usd),
            "total_odd": float(total_odd),
            "potential_win": float(bet.potential_win),
            "items_count": len(outcomes),
            "message": f"✅ Экспресс принята! {len(outcomes)} событий, потенциальный выигрыш: ${bet.potential_win}"
        }

    @staticmethod
    @transaction.atomic
    def cancel_bet(bet_id, admin_user, reason):
        """
        Отменить ставку администратором.

        Args:
            bet_id: UUID ставки
            admin_user: User объект админа
            reason: Причина отмены

        Returns:
            dict с результатом
        """
        try:
            bet = Bet.objects.select_for_update().get(id=bet_id)
        except Bet.DoesNotExist:
            raise BettingError("Ставка не найдена")

        if bet.status != 'pending':
            raise BettingError("Можно отменить только активные ставки")

        # Отменить ставку
        bet.status = 'cancelled'
        bet.settled_at = timezone.now()

        # Разморозить средства
        if bet.freeze_transaction:
            TransactionService.unfreeze_funds(
                transaction_id=bet.freeze_transaction.id,
                reason=f"Отмена ставки : {reason}"
            )

        bet.save()

        logger.info(
            f"Ставка отменена: {bet.bet_id} (админ: {admin_user.id}, "
            f"причина: {reason})"
        )

        return {
            "success": True,
            "bet_id": bet.bet_id,
            "status": "cancelled",
            "message": f"✅ Ставка {bet.bet_id} отменена"
        }

    @staticmethod
    def validate_bet_slip(items):
        """
        Валидировать купон перед размещением.
        НЕ замораживает деньги.

        Args:
            items: List[{"outcome_id": "..."}]

        Returns:
            dict с информацией о валидации
        """
        validated_items = []
        total_odd = Decimal('1.0')
        conflicts = []
        errors = []
        event_ids = []

        for item_data in items:
            outcome_id = item_data.get('outcome_id')
            try:
                outcome = Outcome.objects.get(id=outcome_id)
            except Outcome.DoesNotExist:
                errors.append(f"Исход {outcome_id} не найден")
                continue

            event = outcome.market.event
            event_ids.append((event.id, outcome.id))

            # Проверить валидность
            item_valid = True
            item_error = None

            try:
                BettingService._validate_event(event)
                BettingService._validate_market(outcome.market)
                BettingService._validate_outcome(outcome)
            except BettingError as e:
                item_valid = False
                item_error = str(e)

            validated_items.append({
                "outcome_id": str(outcome_id),
                "event": str(event),
                "outcome": outcome.name,
                "odd": float(outcome.odd),
                "valid": item_valid,
                "error": item_error
            })

            if item_valid:
                total_odd *= outcome.odd

        # Проверить конфликты (несколько исходов из одного события)
        event_id_counts = {}
        for event_id, outcome_id in event_ids:
            if event_id not in event_id_counts:
                event_id_counts[event_id] = []
            event_id_counts[event_id].append(outcome_id)

        for event_id, outcome_ids in event_id_counts.items():
            if len(outcome_ids) > 1:
                conflicts.append(
                    f"Несколько исходов из события ID {event_id}"
                )

        return {
            "valid": not errors and not conflicts,
            "items": validated_items,
            "total_odd": float(total_odd) if len(items) > 0 else 1.0,
            "conflicts": conflicts,
            "errors": errors
        }
