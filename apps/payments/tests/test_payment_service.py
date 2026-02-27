from __future__ import annotations

from decimal import Decimal
from datetime import timedelta

from django.test import TestCase, override_settings
from django.utils import timezone

from apps.accounts.models import User
from apps.payments.models import DepositOrder, PaymentMethod, PaymentProvider
from apps.payments.services.payment_service import PaymentService
from apps.wallet.models import Currency, WalletBalance
from apps.wallet.services.wallet_service import WalletService
from apps.wallet.models import Transaction


@override_settings(ROOT_URLCONF="apps.payments.tests.urls_stub")
class PaymentServiceTests(TestCase):
    fixtures = ["payments_providers_methods.json"]

    def setUp(self):
        self.user = User.objects.create(email="user@example.com", username="user")
        self.wallet = WalletService.create_wallet(self.user)
        self.currency_usd = Currency.objects.get(code="USD")
        self.provider = PaymentProvider.objects.get(code="rukassa")
        self.method_card = PaymentMethod.objects.get(provider=self.provider, code="card")

    def _create_deposit_order(self, amount: Decimal = Decimal("100")) -> DepositOrder:
        return DepositOrder.objects.create(
            user=self.user,
            wallet=self.wallet,
            provider=self.provider,
            payment_method=self.method_card,
            currency=self.currency_usd,
            amount=amount,
            amount_usd=amount,
            fee_amount=Decimal("0"),
            status="created",
            ip_address="127.0.0.1",
            user_agent="test",
            expires_at=timezone.now() + timedelta(minutes=30),
        )

    def test_complete_deposit_idempotent(self):
        deposit = self._create_deposit_order(Decimal("50"))

        first = PaymentService.complete_deposit(deposit.order_id, Decimal("60"))
        self.assertEqual(first, "completed")

        deposit.refresh_from_db()
        # balance increased once
        balance = WalletBalance.objects.get(wallet=self.wallet, currency=self.currency_usd)
        self.assertEqual(balance.available, Decimal("60"))
        self.assertIsNotNone(deposit.transaction)
        txn_id = deposit.transaction_id

        # second call should not create new transaction
        second = PaymentService.complete_deposit(deposit.order_id, Decimal("70"))
        self.assertEqual(second, "duplicate")
        balance.refresh_from_db()
        self.assertEqual(balance.available, Decimal("60"))
        deposit.refresh_from_db()
        self.assertEqual(deposit.transaction_id, txn_id)

    def test_get_available_methods_filters_by_currency(self):
        data_rub = PaymentService.get_available_deposit_methods(self.user, currency_code="RUB")
        providers = {entry["provider"] for entry in data_rub}
        self.assertEqual(providers, {"rukassa"})
        method_codes = {m["code"] for entry in data_rub for m in entry["methods"]}
        self.assertIn("card", method_codes)
        self.assertIn("sbp", method_codes)

        data_btc = PaymentService.get_available_deposit_methods(self.user, currency_code="BTC")
        providers_btc = {entry["provider"] for entry in data_btc}
        self.assertEqual(providers_btc, {"nowpayments"})
        method_codes_btc = {m["code"] for entry in data_btc for m in entry["methods"]}
        self.assertEqual(method_codes_btc, {"btc"})
