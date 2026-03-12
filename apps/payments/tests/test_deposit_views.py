"""
Unit tests for deposit views.

Requirements: 14.1, 14.2, 14.6
"""
from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from apps.payments.models import PaymentProvider, PaymentMethod, DepositOrder
from apps.wallet.models import Currency, Wallet

User = get_user_model()


class DepositViewsTestCase(TestCase):
    """Test deposit views functionality."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Get wallet (created automatically by signal)
        self.wallet = Wallet.objects.get(user=self.user)
        
        # Get or create test currency
        self.currency, _ = Currency.objects.get_or_create(
            code='USD',
            defaults={
                'name': 'US Dollar',
                'symbol': '$',
                'type': 'fiat',
                'decimal_places': 2,
                'rate_to_usd': Decimal('1.0'),
                'is_active': True
            }
        )
        
        # Create test provider
        self.provider = PaymentProvider.objects.create(
            code='test_provider',
            name='Test Provider',
            type='fiat',
            description='Test payment provider',
            icon='💳',
            api_base_url='https://api.test.com',
            api_key='test_key',
            is_active=True,
            is_deposit_enabled=True,
            processing_time='Instant'
        )
        
        # Create test payment method
        self.payment_method = PaymentMethod.objects.create(
            provider=self.provider,
            code='test_card',
            name='Test Card',
            description='Test card payment',
            icon='💳',
            currency=self.currency,
            type='deposit',
            min_amount=Decimal('10.00'),
            max_amount=Decimal('10000.00'),
            fee_percent=Decimal('2.5'),
            fee_fixed=Decimal('0.50'),
            processing_time='Instant',
            is_active=True
        )
        
        # Login user
        self.client.login(username='testuser', password='testpass123')

    def test_deposit_page_renders_providers(self):
        """Test deposit page displays available providers and methods."""
        response = self.client.get(reverse('payments:deposit_page'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'payments/deposit.html')
        self.assertIn('fiat_providers', response.context)
        self.assertIn('crypto_providers', response.context)
        
        # Check that our test provider is in the context
        fiat_providers = response.context['fiat_providers']
        self.assertEqual(len(fiat_providers), 1)
        self.assertEqual(fiat_providers[0]['provider'].code, 'test_provider')

    @patch('apps.payments.views.PaymentService.create_deposit')
    def test_create_deposit_creates_order_and_redirects(self, mock_create_deposit):
        """Test create_deposit creates order and redirects to payment page."""
        # Mock the service response
        mock_create_deposit.return_value = {
            'deposit_id': 'DEP-123456',
            'payment_url': 'https://payment.test.com/pay/123',
            'status': 'pending'
        }
        
        # Submit deposit form
        response = self.client.post(reverse('payments:create_deposit'), {
            'payment_method_id': str(self.payment_method.id),
            'amount': '100.00',
            'currency': 'USD'
        })
        
        # Check that service was called
        mock_create_deposit.assert_called_once()
        
        # Check redirect to payment URL
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, 'https://payment.test.com/pay/123')

    def test_deposit_success_displays_transaction_details(self):
        """Test deposit success page displays transaction details."""
        # Create a completed deposit order
        deposit = DepositOrder.objects.create(
            user=self.user,
            wallet=self.wallet,
            provider=self.provider,
            payment_method=self.payment_method,
            currency=self.currency,
            amount=Decimal('100.00'),
            amount_usd=Decimal('100.00'),
            fee_amount=Decimal('2.50'),
            status='completed',
            ip_address='127.0.0.1',
            expires_at='2024-12-31 23:59:59'
        )
        
        # Visit success page
        response = self.client.get(
            reverse('payments:deposit_success') + f'?order={deposit.order_id}'
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'payments/deposit_success.html')
        self.assertEqual(response.context['deposit'].id, deposit.id)
        self.assertContains(response, deposit.order_id)
        self.assertContains(response, '100.00')

    def test_deposit_failure_displays_error(self):
        """Test deposit failure page displays error information."""
        # Create a failed deposit order
        deposit = DepositOrder.objects.create(
            user=self.user,
            wallet=self.wallet,
            provider=self.provider,
            payment_method=self.payment_method,
            currency=self.currency,
            amount=Decimal('100.00'),
            amount_usd=Decimal('100.00'),
            fee_amount=Decimal('2.50'),
            status='failed',
            ip_address='127.0.0.1',
            expires_at='2024-12-31 23:59:59'
        )
        
        # Visit failure page
        response = self.client.get(
            reverse('payments:deposit_failure') + f'?order={deposit.order_id}'
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'payments/deposit_failure.html')
        self.assertEqual(response.context['deposit'].id, deposit.id)
        self.assertContains(response, deposit.order_id)

    def test_deposit_page_requires_login(self):
        """Test deposit page requires authentication."""
        # Logout
        self.client.logout()
        
        # Try to access deposit page
        response = self.client.get(reverse('payments:deposit_page'))
        
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_create_deposit_validates_amount(self):
        """Test create_deposit validates amount against limits."""
        # Try to create deposit with amount below minimum
        response = self.client.post(reverse('payments:create_deposit'), {
            'payment_method_id': str(self.payment_method.id),
            'amount': '5.00',  # Below min_amount of 10.00
            'currency': 'USD'
        })
        
        # Should show error (not redirect)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'payments/deposit.html')
