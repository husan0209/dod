from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse
from apps.wallet.models import Currency, Wallet
from apps.wallet.services.wallet_service import WalletService

User = get_user_model()

class WithdrawConfirmViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="password123",
            two_fa_method="email",
            is_2fa_enabled=True
        )
        self.usd, _ = Currency.objects.get_or_create(code="USD")
        self.usd.name = "US Dollar"
        self.usd.symbol = "$"
        self.usd.type = "fiat"
        self.usd.decimal_places = 2
        self.usd.rate_to_usd = Decimal("1.0")
        self.usd.is_active = True
        self.usd.is_withdrawal_enabled = True
        self.usd.min_withdrawal = Decimal("10.00")
        self.usd.save()

        self.wallet = WalletService.create_wallet(self.user)
        # Give some balance
        balance_obj = WalletService.get_or_create_balance(self.wallet, "USD")
        balance_obj.available = Decimal("100.00")
        balance_obj.save()
        
        from apps.wallet.models import WalletSettings
        settings_obj = WalletSettings.get_settings()
        settings_obj.new_account_withdrawal_delay_hours = 0
        settings_obj.max_daily_withdrawal_usd = Decimal("100000.00")
        settings_obj.save()
        
        from django.core.cache import cache
        cache.clear()
        
        logged_in = self.client.login(email="test@example.com", password="password123")
        self.assertTrue(logged_in)
        
        self.url = reverse("wallet:withdraw_confirm")
        
        # Setup session data
        session = self.client.session
        session["withdrawal_pending"] = {
            "currency_code": "USD",
            "amount": "50.00",
            "payment_method": "card",
            "payment_details": {"card_number": "1234"},
            "ip_address": "127.0.0.1",
            "user_agent": "test-agent",
        }
        session.save()

    def test_view_renders_correctly(self):
        try:
            response = self.client.get(self.url)
        except Exception as e:
            print(f"DEBUG: Rendering failed with {type(e).__name__}: {e}")
            raise e
        
        if response.status_code == 302:
            print(f"DEBUG: Redirected to {response.url}")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "wallet/withdraw_confirm.html")
        self.assertContains(response, "USD")
        self.assertContains(response, "50.00")

    def test_invalid_otp_fails(self):
        response = self.client.post(self.url, {"otp_code": "wrong"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Неверный код подтверждения")

    def test_valid_email_otp_submits_withdrawal(self):
        # View logic for email: is_valid = len(otp_code) == 6 and otp_code.isdigit()
        response = self.client.post(self.url, {"otp_code": "123456"}, follow=True)
        
        from apps.wallet.models import WithdrawalRequest
        exists = WithdrawalRequest.objects.filter(user=self.user).exists()
        if not exists:
            # Maybe it stayed on the page with an error
            print(f"DEBUG: Response status: {response.status_code}")
            if hasattr(response, 'context') and 'error' in response.context:
                print(f"DEBUG: View Error: {response.context['error']}")
            else:
                print(f"DEBUG: Content Snippet: {response.content[:500].decode('utf-8', errors='ignore')}")

        self.assertTrue(exists)
        req = WithdrawalRequest.objects.get(user=self.user)
        # Check if the last redirect in the chain was to withdrawal_status
        self.assertEqual(response.redirect_chain[-1][0], reverse("wallet:withdrawal_status", kwargs={"request_id": req.id}))

    def test_redirect_if_no_pending_withdrawal(self):
        session = self.client.session
        del session["withdrawal_pending"]
        session.save()
        
        response = self.client.get(self.url)
        self.assertRedirects(response, reverse("wallet:withdraw"))
