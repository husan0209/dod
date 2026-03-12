"""
Tests for fee calculation methods in PaymentService.

This test file validates:
- Fee calculation order (fee_fixed first, then fee_percent)
- Deposit total calculation for UI display
- Withdrawal net calculation for UI display
- Decimal places formatting based on currency configuration
"""

from decimal import Decimal
from django.test import TestCase

from apps.payments.services.payment_service import PaymentService
from apps.payments.models import PaymentProvider, PaymentMethod
from apps.wallet.models import Currency


class TestFeeCalculation(TestCase):
    """Test fee calculation methods."""

    def setUp(self):
        """Set up test data."""
        # Create test currency with 2 decimal places (like USD)
        self.currency_usd = Currency.objects.create(
            code="USD",
            name="US Dollar",
            symbol="$",
            type="fiat",
            decimal_places=2,
            rate_to_usd=Decimal("1.0"),
            min_deposit=Decimal("10"),
            min_withdrawal=Decimal("10"),
        )

        # Create test currency with 8 decimal places (like BTC)
        self.currency_btc = Currency.objects.create(
            code="BTC",
            name="Bitcoin",
            symbol="₿",
            type="crypto",
            decimal_places=8,
            rate_to_usd=Decimal("50000.0"),
            min_deposit=Decimal("0.0001"),
            min_withdrawal=Decimal("0.0001"),
        )

        # Create test provider
        self.provider = PaymentProvider.objects.create(
            code="test_provider",
            name="Test Provider",
            api_key="test_key",
            api_secret="test_secret",
            webhook_secret="test_webhook",
            is_active=True,
        )

        # Create payment method with both fixed and percent fees
        self.payment_method_usd = PaymentMethod.objects.create(
            provider=self.provider,
            code="test_card",
            name="Test Card",
            description="Test card payment",
            icon="card",
            currency=self.currency_usd,
            type="both",
            min_amount=Decimal("10"),
            max_amount=Decimal("10000"),
            fee_percent=Decimal("3.5"),  # 3.5%
            fee_fixed=Decimal("2.0"),    # $2 fixed
            processing_time="Instant",
        )

        # Create payment method for crypto with different fees
        self.payment_method_btc = PaymentMethod.objects.create(
            provider=self.provider,
            code="test_btc",
            name="Test BTC",
            description="Test BTC payment",
            icon="btc",
            currency=self.currency_btc,
            type="both",
            min_amount=Decimal("0.001"),
            max_amount=Decimal("10"),
            fee_percent=Decimal("1.0"),      # 1%
            fee_fixed=Decimal("0.0001"),     # 0.0001 BTC fixed
            processing_time="10-30 minutes",
        )

    def test_calculate_fee_order(self):
        """Test that fee_fixed is applied first, then fee_percent on original amount."""
        amount = Decimal("100")
        
        # Expected: fee_fixed (2.0) + (amount * fee_percent / 100)
        # = 2.0 + (100 * 3.5 / 100) = 2.0 + 3.5 = 5.5
        fee = PaymentService._calculate_fee(amount, self.payment_method_usd)
        
        expected_fee = Decimal("2.0") + (Decimal("100") * Decimal("3.5") / Decimal("100"))
        self.assertEqual(fee, expected_fee)
        self.assertEqual(fee, Decimal("5.5"))

    def test_calculate_fee_with_zero_fixed(self):
        """Test fee calculation when fee_fixed is zero."""
        # Temporarily modify payment method
        self.payment_method_usd.fee_fixed = Decimal("0")
        
        amount = Decimal("100")
        fee = PaymentService._calculate_fee(amount, self.payment_method_usd)
        
        # Expected: 0 + (100 * 3.5 / 100) = 3.5
        self.assertEqual(fee, Decimal("3.5"))

    def test_calculate_fee_with_zero_percent(self):
        """Test fee calculation when fee_percent is zero."""
        # Temporarily modify payment method
        self.payment_method_usd.fee_percent = Decimal("0")
        
        amount = Decimal("100")
        fee = PaymentService._calculate_fee(amount, self.payment_method_usd)
        
        # Expected: 2.0 + (100 * 0 / 100) = 2.0
        self.assertEqual(fee, Decimal("2.0"))

    def test_calculate_deposit_total(self):
        """Test deposit total calculation for UI display."""
        amount = Decimal("100")
        
        result = PaymentService.calculate_deposit_total(amount, self.payment_method_usd)
        
        # Verify structure
        self.assertIn("amount", result)
        self.assertIn("fee", result)
        self.assertIn("total", result)
        self.assertIn("formatted_total", result)
        
        # Verify values
        self.assertEqual(result["amount"], Decimal("100"))
        self.assertEqual(result["fee"], Decimal("5.5"))
        self.assertEqual(result["total"], Decimal("105.5"))
        
        # Verify formatting with currency decimal places (2 for USD)
        self.assertEqual(result["formatted_total"], Decimal("105.50"))

    def test_calculate_deposit_total_crypto(self):
        """Test deposit total calculation for crypto with 8 decimal places."""
        amount = Decimal("0.01")  # 0.01 BTC
        
        result = PaymentService.calculate_deposit_total(amount, self.payment_method_btc)
        
        # Fee: 0.0001 + (0.01 * 1 / 100) = 0.0001 + 0.0001 = 0.0002
        # Total: 0.01 + 0.0002 = 0.0102
        self.assertEqual(result["amount"], Decimal("0.01"))
        self.assertEqual(result["fee"], Decimal("0.0002"))
        self.assertEqual(result["total"], Decimal("0.0102"))
        
        # Verify formatting with 8 decimal places
        self.assertEqual(result["formatted_total"], Decimal("0.01020000"))

    def test_calculate_withdrawal_net(self):
        """Test withdrawal net calculation for UI display."""
        amount = Decimal("100")
        
        result = PaymentService.calculate_withdrawal_net(amount, self.payment_method_usd)
        
        # Verify structure
        self.assertIn("amount", result)
        self.assertIn("fee", result)
        self.assertIn("net", result)
        self.assertIn("formatted_net", result)
        
        # Verify values
        # Fee: 2.0 + (100 * 3.5 / 100) = 5.5
        # Net: 100 - 5.5 = 94.5
        self.assertEqual(result["amount"], Decimal("100"))
        self.assertEqual(result["fee"], Decimal("5.5"))
        self.assertEqual(result["net"], Decimal("94.5"))
        
        # Verify formatting with currency decimal places (2 for USD)
        self.assertEqual(result["formatted_net"], Decimal("94.50"))

    def test_calculate_withdrawal_net_crypto(self):
        """Test withdrawal net calculation for crypto with 8 decimal places."""
        amount = Decimal("0.01")  # 0.01 BTC
        
        result = PaymentService.calculate_withdrawal_net(amount, self.payment_method_btc)
        
        # Fee: 0.0001 + (0.01 * 1 / 100) = 0.0001 + 0.0001 = 0.0002
        # Net: 0.01 - 0.0002 = 0.0098
        self.assertEqual(result["amount"], Decimal("0.01"))
        self.assertEqual(result["fee"], Decimal("0.0002"))
        self.assertEqual(result["net"], Decimal("0.0098"))
        
        # Verify formatting with 8 decimal places
        self.assertEqual(result["formatted_net"], Decimal("0.00980000"))

    def test_calculate_withdrawal_net_negative_protection(self):
        """Test that withdrawal net never goes negative."""
        # Create a scenario where fee would exceed amount
        amount = Decimal("1")  # $1
        
        # Temporarily set high fees
        self.payment_method_usd.fee_fixed = Decimal("10")  # $10 fixed
        self.payment_method_usd.fee_percent = Decimal("50")  # 50%
        
        result = PaymentService.calculate_withdrawal_net(amount, self.payment_method_usd)
        
        # Fee would be: 10 + (1 * 50 / 100) = 10.5
        # Net would be: 1 - 10.5 = -9.5, but should be clamped to 0
        self.assertEqual(result["fee"], Decimal("10.5"))
        self.assertEqual(result["net"], Decimal("0"))
        self.assertEqual(result["formatted_net"], Decimal("0.00"))

    def test_decimal_places_formatting_fiat(self):
        """Test that fiat currency amounts are formatted with 2 decimal places."""
        amount = Decimal("100.123456")
        
        result = PaymentService.calculate_deposit_total(amount, self.payment_method_usd)
        
        # Should be rounded to 2 decimal places
        self.assertEqual(len(str(result["formatted_total"]).split(".")[-1]), 2)

    def test_decimal_places_formatting_crypto(self):
        """Test that crypto amounts are formatted with 8 decimal places."""
        amount = Decimal("0.123456789")
        
        result = PaymentService.calculate_deposit_total(amount, self.payment_method_btc)
        
        # Should be formatted to 8 decimal places
        self.assertEqual(len(str(result["formatted_total"]).split(".")[-1]), 8)

    def test_fee_calculation_precision(self):
        """Test that fee calculation maintains proper precision."""
        amount = Decimal("123.456789")
        
        fee = PaymentService._calculate_fee(amount, self.payment_method_usd)
        
        # Fee should be calculated with high precision (8 decimal places)
        # Fee: 2.0 + (123.456789 * 3.5 / 100) = 2.0 + 4.32098615 = 6.32098615
        expected = Decimal("2.0") + (Decimal("123.456789") * Decimal("3.5") / Decimal("100"))
        self.assertEqual(fee, expected.quantize(Decimal("0.00000001")))
