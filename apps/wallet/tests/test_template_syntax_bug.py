"""
Bug Condition Exploration Test for Wallet Template Syntax Error

This test demonstrates the bug exists on unfixed code by attempting to render
the wallet overview template with pending withdrawals. The test MUST FAIL on
unfixed code with a TemplateSyntaxError containing "Could not parse the remainder: ':isSelectedCrypto:8'".

**Validates: Requirements 2.1, 2.2**
"""
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse
from django.template import TemplateSyntaxError
from apps.wallet.models import Currency, WithdrawalRequest
from apps.wallet.services.wallet_service import WalletService

User = get_user_model()


class WalletTemplateSyntaxBugTest(TestCase):
    """
    Property-based test that demonstrates the template syntax bug exists.
    
    This test encodes the expected behavior: the template should render
    successfully without raising TemplateSyntaxError, and pending withdrawal
    amounts should display with 8 decimal places.
    
    On unfixed code, this test FAILS with TemplateSyntaxError, proving the bug exists.
    """

    def setUp(self):
        """Set up test user, wallet, and currencies."""
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="password123",
            two_fa_method="email",
            is_2fa_enabled=False
        )
        
        # Create BTC currency for testing
        self.btc, _ = Currency.objects.get_or_create(code="BTC")
        self.btc.name = "Bitcoin"
        self.btc.symbol = "₿"
        self.btc.type = "crypto"
        self.btc.decimal_places = 8
        self.btc.rate_to_usd = Decimal("45000.00")
        self.btc.is_active = True
        self.btc.is_withdrawal_enabled = True
        self.btc.min_withdrawal = Decimal("0.001")
        self.btc.save()
        
        # Create wallet
        self.wallet = WalletService.create_wallet(self.user)
        
        # Log in
        logged_in = self.client.login(email="test@example.com", password="password123")
        self.assertTrue(logged_in)

    @given(
        amount=st.decimals(
            min_value=Decimal("0.00000001"),
            max_value=Decimal("10"),
            places=8,
            allow_nan=False,
            allow_infinity=False
        )
    )
    @settings(
        max_examples=10,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much]
    )
    def test_pending_withdrawal_template_renders_without_syntax_error(self, amount):
        """
        Property: Template renders successfully without TemplateSyntaxError
        
        For any pending withdrawal amount, the wallet overview template
        should render without raising a TemplateSyntaxError.
        
        On unfixed code: FAILS with TemplateSyntaxError (proves bug exists)
        On fixed code: PASSES (template renders successfully)
        """
        # Create a pending withdrawal with the generated amount
        withdrawal = WithdrawalRequest.objects.create(
            user=self.user,
            currency=self.btc,
            amount=amount,
            status="pending",
            request_id=f"test-{amount}",
            destination_address="1A1z7agoat2GPFH7pPmmCH5yV8KfZoxVg"
        )
        
        # Attempt to render the wallet overview page
        # This should NOT raise TemplateSyntaxError on fixed code
        try:
            response = self.client.get(reverse("wallet:overview"))
            self.assertEqual(response.status_code, 200)
        except TemplateSyntaxError as e:
            # On unfixed code, this is expected to fail with the specific error
            error_msg = str(e)
            self.assertIn("Could not parse the remainder", error_msg)
            self.assertIn("isSelectedCrypto:8", error_msg)
            raise

    def test_pending_withdrawal_displays_with_8_decimal_places(self):
        """
        Property: Pending withdrawal amounts display with 8 decimal places
        
        When a pending withdrawal is rendered, the amount should be formatted
        with exactly 8 decimal places.
        
        On unfixed code: FAILS with TemplateSyntaxError (proves bug exists)
        On fixed code: PASSES (amounts display with 8 decimals)
        """
        # Create a pending withdrawal with a specific amount
        amount = Decimal("0.12345678")
        withdrawal = WithdrawalRequest.objects.create(
            user=self.user,
            currency=self.btc,
            amount=amount,
            status="pending",
            request_id="test-specific",
            destination_address="1A1z7agoat2GPFH7pPmmCH5yV8KfZoxVg"
        )
        
        # Render the page
        try:
            response = self.client.get(reverse("wallet:overview"))
            self.assertEqual(response.status_code, 200)
            
            # Check that the amount is displayed with 8 decimal places
            content = response.content.decode()
            self.assertIn("0.12345678", content)
        except TemplateSyntaxError as e:
            # On unfixed code, this is expected to fail
            error_msg = str(e)
            self.assertIn("Could not parse the remainder", error_msg)
            self.assertIn("isSelectedCrypto:8", error_msg)
            raise

    def test_html_output_contains_properly_formatted_amounts(self):
        """
        Property: HTML output contains properly formatted amounts
        
        The rendered HTML should contain withdrawal amounts formatted
        with the correct number of decimal places (e.g., "0.12345678").
        
        On unfixed code: FAILS with TemplateSyntaxError (proves bug exists)
        On fixed code: PASSES (HTML contains formatted amounts)
        """
        # Create multiple pending withdrawals with different amounts
        amounts = [
            Decimal("0.00000001"),  # Minimum amount
            Decimal("1.5"),          # Amount with trailing zeros
            Decimal("0.12345678"),   # Full precision amount
        ]
        
        for i, amount in enumerate(amounts):
            WithdrawalRequest.objects.create(
                user=self.user,
                currency=self.btc,
                amount=amount,
                status="pending",
                request_id=f"test-{i}",
                destination_address="1A1z7agoat2GPFH7pPmmCH5yV8KfZoxVg"
            )
        
        # Render the page
        try:
            response = self.client.get(reverse("wallet:overview"))
            self.assertEqual(response.status_code, 200)
            
            content = response.content.decode()
            
            # Verify that amounts are displayed with proper formatting
            # floatformat:8 should display amounts with 8 decimal places
            self.assertIn("0.00000001", content)
            self.assertIn("1.50000000", content)
            self.assertIn("0.12345678", content)
        except TemplateSyntaxError as e:
            # On unfixed code, this is expected to fail
            error_msg = str(e)
            self.assertIn("Could not parse the remainder", error_msg)
            self.assertIn("isSelectedCrypto:8", error_msg)
            raise
