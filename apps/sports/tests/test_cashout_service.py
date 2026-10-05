from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase

from apps.sports.services.cashout_service import CashoutService


class CashoutServiceTests(TestCase):
    @patch('apps.sports.services.cashout_service.TransactionService.settle_bet')
    @patch('apps.sports.services.cashout_service.BetSettings.get_settings')
    @patch('apps.sports.services.cashout_service.Bet.objects')
    def test_cashout_settles_frozen_stake_and_credits_cashout(
        self, bets, get_settings, settle_bet
    ):
        user = SimpleNamespace(id=1)
        bet = SimpleNamespace(
            id='bet-pk',
            bet_id='BET-1',
            user=user,
            wallet=SimpleNamespace(),
            currency=SimpleNamespace(code='USD'),
            stake=Decimal('10.00'),
            freeze_transaction=object(),
            is_cashout_available=lambda: True,
            save=lambda: None,
        )
        bets.select_for_update.return_value.get.return_value = bet
        get_settings.return_value.cashout_min_amount_usd = Decimal('1.00')

        with patch.object(
            CashoutService, 'calculate_cashout_amount', return_value=Decimal('8.50')
        ):
            result = CashoutService.place_cashout('bet-pk', user)

        settle_bet.assert_called_once_with(
            wallet=bet.wallet,
            currency_code='USD',
            frozen_amount=Decimal('10.00'),
            win_amount=Decimal('8.50'),
            reference_type='bet_cashout',
            reference_id='BET-1',
        )
        self.assertEqual(bet.status, 'cashed_out')
        self.assertEqual(result['cashout_amount'], 8.5)
