"""
Unit tests for wallet app.
"""

import pytest
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.db import models
from apps.wallet.models import Wallet, WalletBalance, Transaction, Currency

User = get_user_model()


@pytest.mark.django_db
class TestWalletModel:
    """Tests for Wallet model."""

    def test_wallet_created_with_user(self):
        """Test that wallet is automatically created with user."""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='pass'
        )
        
        wallet = Wallet.objects.get(user=user)
        assert wallet is not None
        assert wallet.user == user

    def test_wallet_balance_creation(self):
        """Test creating wallet balance."""
        user = User.objects.create_user(
            username='test',
            email='test@example.com',
            password='pass'
        )
        wallet = Wallet.objects.get(user=user)
        
        # Create Currency first
        currency = Currency.objects.get_or_create(
            code='USD',
            defaults={'name': 'US Dollar', 'symbol': '$', 'type': 'fiat', 'decimal_places': 2}
        )[0]
        
        balance = WalletBalance.objects.create(
            wallet=wallet,
            currency=currency,
            available=Decimal('100.00')
        )
        
        assert balance.currency.code == 'USD'
        assert balance.available == Decimal('100.00')

    def test_get_balance_by_currency(self):
        """Test getting balance by currency."""
        user = User.objects.create_user(
            username='test',
            email='test@example.com',
            password='pass'
        )
        wallet = Wallet.objects.get(user=user)
        
        currency = Currency.objects.get_or_create(
            code='USD',
            defaults={'name': 'US Dollar', 'symbol': '$', 'type': 'fiat', 'decimal_places': 2}
        )[0]
        
        WalletBalance.objects.create(
            wallet=wallet,
            currency=currency,
            available=Decimal('100.00')
        )
        
        balance = wallet.get_balance('USD')
        assert balance == Decimal('100.00')

    def test_insufficient_balance_raises_error(self):
        """Test that withdrawing more than balance raises error."""
        user = User.objects.create_user(
            username='test',
            email='test@example.com',
            password='pass'
        )
        wallet = Wallet.objects.get(user=user)
        
        currency = Currency.objects.get_or_create(
            code='USD',
            defaults={'name': 'US Dollar', 'symbol': '$', 'type': 'fiat', 'decimal_places': 2}
        )[0]
        
        balance_obj = WalletBalance.objects.create(
            wallet=wallet,
            currency=currency,
            available=Decimal('50.00')
        )
        
        # Attempt to withdraw more than available
        with pytest.raises(ValueError):
            balance_obj.debit(Decimal('100.00'))


@pytest.mark.django_db
class TestWalletTransactions:
    """Tests for wallet transactions."""

    def test_deposit_transaction(self):
        """Test creating a deposit transaction."""
        user = User.objects.create_user(
            username='test',
            email='test@example.com',
            password='pass'
        )
        wallet = Wallet.objects.get(user=user)
        currency = Currency.objects.get_or_create(
            code='USD',
            defaults={'name': 'US Dollar', 'symbol': '$', 'type': 'fiat', 'decimal_places': 2}
        )[0]
        
        transaction = Transaction.objects.create(
            wallet=wallet,
            user=user,
            type='deposit',
            currency=currency,
            amount=Decimal('50.00'),
            amount_usd=Decimal('50.00'),
            balance_before=Decimal('0.00'),
            balance_after=Decimal('50.00'),
            status='completed',
            description='Test deposit'
        )
        
        assert transaction.type == 'deposit'
        assert transaction.status == 'completed'
        assert transaction.amount == Decimal('50.00')

    def test_withdrawal_transaction(self):
        """Test creating a withdrawal transaction."""
        user = User.objects.create_user(
            username='test',
            email='test@example.com',
            password='pass'
        )
        wallet = Wallet.objects.get(user=user)
        currency = Currency.objects.get_or_create(
            code='USD',
            defaults={'name': 'US Dollar', 'symbol': '$', 'type': 'fiat', 'decimal_places': 2}
        )[0]
        
        transaction = Transaction.objects.create(
            wallet=wallet,
            user=user,
            type='withdrawal',
            currency=currency,
            amount=Decimal('25.00'),
            amount_usd=Decimal('25.00'),
            balance_before=Decimal('100.00'),
            balance_after=Decimal('75.00'),
            status='pending',
            description='Test withdrawal'
        )
        
        assert transaction.type == 'withdrawal'
        assert transaction.status == 'pending'

    def test_transaction_history(self):
        """Test retrieving transaction history."""
        user = User.objects.create_user(
            username='test',
            email='test@example.com',
            password='pass'
        )
        wallet = Wallet.objects.get(user=user)
        
        # Create currencies
        usd = Currency.objects.get_or_create(
            code='USD',
            defaults={'name': 'US Dollar', 'symbol': '$', 'type': 'fiat', 'decimal_places': 2}
        )[0]
        eur = Currency.objects.get_or_create(
            code='EUR',
            defaults={'name': 'Euro', 'symbol': '€', 'type': 'fiat', 'decimal_places': 2}
        )[0]
        
        # Create multiple transactions
        Transaction.objects.create(
            wallet=wallet,
            user=user,
            type='deposit',
            currency=usd,
            amount=Decimal('50.00'),
            amount_usd=Decimal('50.00'),
            balance_before=Decimal('0.00'),
            balance_after=Decimal('50.00'),
            status='completed'
        )
        Transaction.objects.create(
            wallet=wallet,
            user=user,
            type='deposit',
            currency=eur,
            amount=Decimal('40.00'),
            amount_usd=Decimal('43.00'),
            balance_before=Decimal('0.00'),
            balance_after=Decimal('40.00'),
            status='completed'
        )
        
        transactions = wallet.transaction_set.all()  # type: ignore
        assert transactions.count() == 2
        assert transactions[0].currency.code in ['USD', 'EUR']


@pytest.mark.django_db
class TestMultipleCurrencies:
    """Tests for multiple currency support."""

    def test_multiple_currency_balances(self):
        """Test maintaining multiple currency balances."""
        user = User.objects.create_user(
            username='test',
            email='test@example.com',
            password='pass'
        )
        wallet = Wallet.objects.get(user=user)
        
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
        WalletBalance.objects.create(
            wallet=wallet,
            currency=usd,
            available=Decimal('100.00')
        )
        WalletBalance.objects.create(
            wallet=wallet,
            currency=eur,
            available=Decimal('80.00')
        )
        WalletBalance.objects.create(
            wallet=wallet,
            currency=btc,
            available=Decimal('0.5')
        )
        
        balances = wallet.balances.all()  # type: ignore
        assert balances.count() == 3
        
        currencies = [b.currency.code for b in balances]
        assert 'USD' in currencies
        assert 'EUR' in currencies
        assert 'BTC' in currencies
