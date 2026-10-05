from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import TestCase
from django.utils import timezone

from apps.sports.models import Bet, BetItem, BetSettings, Event, Outcome
from apps.sports.services.betting_service import BettingService
from apps.sports.services.settlement_service import SettlementService
from apps.wallet.models import Currency


class BettingServicePlacementTests(TestCase):
    def setUp(self):
        self.wallet = SimpleNamespace(
            convert_to_usd=lambda currency_code, amount: amount,
        )
        self.user = SimpleNamespace(id='user-1', wallet=self.wallet)
        self.currency = SimpleNamespace(code='USD')
        self.settings = SimpleNamespace(
            cashout_enabled=True,
            min_combo_items=2,
            max_combo_items=8,
            max_odd=Decimal('100'),
        )
        self.events = {}
        self.outcomes = {}

    def make_outcome(self, outcome_id, event_id):
        event = SimpleNamespace(
            id=event_id,
            status='prematch',
            start_time=timezone.now(),
            bets_count=0,
            total_stake=Decimal('0'),
            save=Mock(),
        )
        market = SimpleNamespace(event=event, status='open', name='Winner')
        outcome = SimpleNamespace(
            id=outcome_id,
            market=market,
            odd=Decimal('2'),
            max_stake=None,
            is_active=True,
            is_suspended=False,
            bets_count=0,
            total_stake=Decimal('0'),
            name='Home',
            save=Mock(),
        )
        self.events[event_id] = event
        self.outcomes[outcome_id] = outcome
        return outcome

    def mock_placement_dependencies(self, bet_id):
        outcome_lookup = patch.object(Outcome.objects, 'select_for_update')
        lookup = outcome_lookup.start()
        lookup.return_value.get.side_effect = (
            lambda id: self.outcomes[id]
        )
        self.addCleanup(outcome_lookup.stop)

        currency_lookup = patch.object(Currency.objects, 'get', return_value=self.currency)
        currency_lookup.start()
        self.addCleanup(currency_lookup.stop)

        settings_lookup = patch.object(
            BetSettings, 'get_settings', return_value=self.settings
        )
        settings_lookup.start()
        self.addCleanup(settings_lookup.stop)

        freeze_funds = patch(
            'apps.sports.services.betting_service.TransactionService.freeze_funds'
        )
        freeze_mock = freeze_funds.start()
        self.addCleanup(freeze_funds.stop)

        bet_create = patch.object(Bet.objects, 'create')
        bet_create_mock = bet_create.start()
        self.addCleanup(bet_create.stop)

        item_create = patch.object(BetItem.objects, 'create')
        item_create.start()
        self.addCleanup(item_create.stop)

        bet_id_generator = patch.object(
            BettingService, '_generate_bet_id', return_value=bet_id
        )
        bet_id_generator.start()
        self.addCleanup(bet_id_generator.stop)

        for validator in (
            '_validate_event',
            '_validate_market',
            '_validate_outcome',
            '_validate_stake',
            '_validate_wallet',
            '_validate_user_event_limit',
        ):
            validator_patch = patch.object(BettingService, validator)
            validator_patch.start()
            self.addCleanup(validator_patch.stop)

        return freeze_mock

    def test_single_bet_freezes_funds_with_its_bet_reference(self):
        self.make_outcome('outcome-1', 'event-1')
        freeze_funds = self.mock_placement_dependencies('BET-SINGLE')

        BettingService.place_single_bet(
            self.user, 'outcome-1', Decimal('5'), 'USD', '127.0.0.1'
        )

        freeze_funds.assert_called_once_with(
            wallet=self.wallet,
            currency_code='USD',
            amount=Decimal('5'),
            reference_type='bet',
            reference_id='BET-SINGLE',
        )

    def test_combo_bet_freezes_funds_with_its_bet_reference(self):
        self.make_outcome('outcome-1', 'event-1')
        self.make_outcome('outcome-2', 'event-2')
        event_lookup = patch.object(Event.objects, 'get')
        event_mock = event_lookup.start()
        event_mock.side_effect = lambda id: self.events[id]
        self.addCleanup(event_lookup.stop)
        freeze_funds = self.mock_placement_dependencies('BET-COMBO')

        BettingService.place_combo_bet(
            self.user,
            [{'outcome_id': 'outcome-1'}, {'outcome_id': 'outcome-2'}],
            Decimal('5'),
            'USD',
            '127.0.0.1',
        )

        freeze_funds.assert_called_once_with(
            wallet=self.wallet,
            currency_code='USD',
            amount=Decimal('5'),
            reference_type='bet',
            reference_id='BET-COMBO',
        )

    @patch('apps.sports.services.betting_service.TransactionService.unfreeze_funds')
    @patch.object(Bet.objects, 'select_for_update')
    def test_cancelling_bet_unfreezes_using_wallet_service_contract(
        self, bets, unfreeze_funds
    ):
        bet = SimpleNamespace(
            status='pending',
            freeze_transaction=object(),
            wallet=self.wallet,
            currency=self.currency,
            stake=Decimal('5'),
            bet_id='BET-CANCEL',
            save=Mock(),
        )
        bets.return_value.get.return_value = bet

        BettingService.cancel_bet(
            'bet-pk', SimpleNamespace(id='admin-1'), 'requested by user'
        )

        unfreeze_funds.assert_called_once_with(
            wallet=self.wallet,
            currency_code='USD',
            amount=Decimal('5'),
            reference_type='bet_cancel',
            reference_id='BET-CANCEL',
        )

    @patch('apps.sports.services.settlement_service.TransactionService.unfreeze_funds')
    def test_void_settlement_unfreezes_using_wallet_service_contract(self, unfreeze_funds):
        bet = SimpleNamespace(
            status='void',
            freeze_transaction=object(),
            wallet=self.wallet,
            currency=self.currency,
            stake=Decimal('5'),
            bet_id='BET-VOID',
        )

        SettlementService._process_payment(bet)

        unfreeze_funds.assert_called_once_with(
            wallet=self.wallet,
            currency_code='USD',
            amount=Decimal('5'),
            reference_type='bet_void',
            reference_id='BET-VOID',
        )
