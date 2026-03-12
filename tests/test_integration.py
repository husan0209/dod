"""
Integration tests for complete user flows.
"""

import pytest
from decimal import Decimal
from django.test import Client
from django.contrib.auth import get_user_model
from apps.wallet.models import Wallet, WalletBalance, Transaction, Currency

User = get_user_model()


@pytest.mark.django_db
class TestUserJourney:
    """End-to-end tests for complete user journeys."""

    def test_user_registration_and_login_journey(self, api_client):
        """Test complete registration and login flow."""
        # Step 1: Create user
        user = User.objects.create_user(
            username='newuser',
            email='newuser@example.com',
            password='securepass123'
        )
        
        # Step 2: User should exist
        assert User.objects.filter(username='newuser').exists()
        
        # Step 3: User should be able to login
        success = api_client.login(username='newuser', password='securepass123')
        assert success
        
        # Step 4: User should have wallet
        wallet = Wallet.objects.get(user=user)
        assert wallet is not None

    def test_user_wallet_deposit_journey(self, authenticated_user, authenticated_client):
        """Test user deposit and balance flow."""
        # Get user's wallet
        wallet = Wallet.objects.get(user=authenticated_user)
        
        # Create Currency
        currency = Currency.objects.get_or_create(
            code='USD',
            defaults={'name': 'US Dollar', 'symbol': '$', 'type': 'fiat', 'decimal_places': 2}
        )[0]
        
        # Step 1: Add initial balance
        balance, created = WalletBalance.objects.get_or_create(
            wallet=wallet,
            currency=currency,
            defaults={'available': Decimal('0.00')}
        )
        balance.available += Decimal('100.00')
        balance.save()
        
        # Step 2: Verify balance
        assert balance.available == Decimal('100.00')
        
        # Step 3: Create deposit transaction
        transaction = Transaction.objects.create(
            wallet=wallet,
            user=authenticated_user,
            type='deposit',
            currency=currency,
            amount=Decimal('100.00'),
            amount_usd=Decimal('100.00'),
            balance_before=Decimal('0.00'),
            balance_after=Decimal('100.00'),
            status='completed',
            description='Initial deposit'
        )
        
        # Step 4: Verify transaction
        assert transaction.status == 'completed'
        assert wallet.transaction_set.count() == 1  # type: ignore

    def test_user_withdrawal_journey(self, authenticated_user):
        """Test user withdrawal flow."""
        # Setup
        wallet = Wallet.objects.get(user=authenticated_user)
        currency = Currency.objects.get_or_create(
            code='USD',
            defaults={'name': 'US Dollar', 'symbol': '$', 'type': 'fiat', 'decimal_places': 2}
        )[0]
        
        # Add initial balance
        balance = WalletBalance.objects.create(
            wallet=wallet,
            currency=currency,
            available=Decimal('100.00')
        )
        
        # Request withdrawal
        initial_balance = balance.available
        withdrawal_amount = Decimal('25.00')
        
        transaction = Transaction.objects.create(
            wallet=wallet,
            user=authenticated_user,
            type='withdrawal',
            currency=currency,
            amount=withdrawal_amount,
            amount_usd=withdrawal_amount,
            balance_before=initial_balance,
            balance_after=initial_balance - withdrawal_amount,
            status='pending',
            description='Test withdrawal'
        )
        
        # Verify withdrawal was created
        assert transaction.amount == withdrawal_amount
        assert transaction.status == 'pending'
        
        # Simulate approval
        transaction.status = 'completed'
        transaction.save()
        
        # Update balance
        balance.available -= withdrawal_amount
        balance.save()
        
        # Verify final balance
        assert balance.available == Decimal('75.00')

    def test_multiple_currency_conversion_journey(self, authenticated_user):
        """Test wallet with multiple currencies."""
        wallet = Wallet.objects.get(user=authenticated_user)
        
        # Create currencies
        usd = Currency.objects.get_or_create(
            code='USD',
            defaults={'name': 'US Dollar', 'symbol': '$', 'type': 'fiat', 'decimal_places': 2}
        )[0]
        eur = Currency.objects.get_or_create(
            code='EUR',
            defaults={'name': 'Euro', 'symbol': '€', 'type': 'fiat', 'decimal_places': 2}
        )[0]
        btc = Currency.objects.get_or_create(
            code='BTC',
            defaults={'name': 'Bitcoin', 'symbol': '₿', 'type': 'crypto', 'decimal_places': 8}
        )[0]
        
        # Add multiple currencies
        usd_balance = WalletBalance.objects.create(
            wallet=wallet,
            currency=usd,
            available=Decimal('100.00')
        )
        
        eur_balance = WalletBalance.objects.create(
            wallet=wallet,
            currency=eur,
            available=Decimal('85.00')
        )
        
        btc_balance = WalletBalance.objects.create(
            wallet=wallet,
            currency=btc,
            available=Decimal('0.5')
        )
        
        # Verify all currencies present
        assert wallet.balances.count() == 3  # type: ignore
        
        # Simulate conversion transaction
        conversion = Transaction.objects.create(
            wallet=wallet,
            user=authenticated_user,
            type='conversion_debit',
            currency=usd,
            amount=Decimal('50.00'),
            amount_usd=Decimal('50.00'),
            balance_before=Decimal('100.00'),
            balance_after=Decimal('50.00'),
            status='completed',
            description='USD to EUR conversion'
        )
        
        # Update balance after conversion
        usd_balance.available -= Decimal('50.00')
        usd_balance.save()
        
        eur_balance.available += Decimal('47.50')  # Approximate conversion
        eur_balance.save()
        
        # Verify conversion
        assert usd_balance.available == Decimal('50.00')
        assert eur_balance.available == Decimal('132.50')


@pytest.mark.django_db
class TestCasinoFlow:
    """Tests for casino betting flow."""

    def test_user_casino_play_flow(self, authenticated_user):
        """Test casino game play flow."""
        wallet = Wallet.objects.get(user=authenticated_user)
        currency = Currency.objects.get_or_create(
            code='USD',
            defaults={'name': 'US Dollar', 'symbol': '$', 'type': 'fiat', 'decimal_places': 2}
        )[0]
        
        # Setup: Add balance
        balance = WalletBalance.objects.create(
            wallet=wallet,
            currency=currency,
            available=Decimal('100.00')
        )
        
        # Step 1: User places bet
        bet_amount = Decimal('10.00')
        
        # Step 2: Freeze balance for bet
        if balance.available >= bet_amount:
            balance.freeze(bet_amount)
            balance.save()
        
        # Step 3: Game resolves
        bet_result = 'WIN'
        payout_multiplier = Decimal('2.0')
        
        if bet_result == 'WIN':
            payout = bet_amount * payout_multiplier
            balance.unfreeze(bet_amount)
            balance.available += payout
        else:
            balance.settle_frozen(bet_amount)
        
        balance.save()
        
        # Verify final state
        expected_balance = Decimal('100.00') - bet_amount + (bet_amount * payout_multiplier)
        assert balance.available == expected_balance


@pytest.mark.django_db
class TestSportsFlow:
    """Tests for sports betting flow."""

    def test_user_sports_bet_flow(self, authenticated_user):
        """Test sports bet placement and settlement."""
        wallet = Wallet.objects.get(user=authenticated_user)
        currency = Currency.objects.get_or_create(
            code='USD',
            defaults={'name': 'US Dollar', 'symbol': '$', 'type': 'fiat', 'decimal_places': 2}
        )[0]
        
        # Setup balance
        balance = WalletBalance.objects.create(
            wallet=wallet,
            currency=currency,
            available=Decimal('200.00')
        )
        
        # Place bet
        bet_amount = Decimal('50.00')
        odds = Decimal('2.5')  # 2.50 decimal odds
        
        # Freeze bet amount
        if balance.available >= bet_amount:
            balance.freeze(bet_amount)
            balance.save()
        
        # Simulate bet settlement (won)
        winnings = bet_amount * odds
        balance.unfreeze(bet_amount)
        balance.available += winnings
        balance.save()
        
        # Verify settlement
        expected_balance = Decimal('200.00') - bet_amount + winnings
        assert balance.available == expected_balance
        assert balance.frozen == Decimal('0.00')
