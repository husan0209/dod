import uuid
from decimal import Decimal
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.wallet.models import Currency, Transaction, WalletSettings, WithdrawalRequest
from apps.wallet.services.conversion_service import ConversionService
from apps.wallet.services.transaction_service import InsufficientFundsError, TransactionService
from apps.wallet.services.wallet_service import WalletService
from apps.wallet.services.withdrawal_service import WithdrawalService, WithdrawalValidationError


class WalletServiceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email=f"u{uuid.uuid4().hex[:6]}@example.com",
            username=f"user_{uuid.uuid4().hex[:6]}",
            password="pass1234",
            kyc_status="approved",
            trust_level=3,
        )
        patcher = patch("apps.wallet.tasks.process_withdrawal_task.delay")
        self.addCleanup(patcher.stop)
        self.mock_celery = patcher.start()
        # ensure base currencies
        self.usd, _ = Currency.objects.get_or_create(
            code="USD",
            defaults={
                "name": "US Dollar",
                "symbol": "$",
                "type": "fiat",
                "decimal_places": 2,
                "rate_to_usd": Decimal("1.0"),
            },
        )
        self.eur, _ = Currency.objects.get_or_create(
            code="EUR",
            defaults={
                "name": "Euro",
                "symbol": "€",
                "type": "fiat",
                "decimal_places": 2,
                "rate_to_usd": Decimal("1.2"),
            },
        )
        self.wallet = WalletService.create_wallet(self.user)
        # make user not "new" for withdrawal delay checks
        self.user.created_at = timezone.now() - timedelta(days=2)
        self.user.save(update_fields=["created_at"])

    def test_deposit_and_withdraw(self):
        txn = TransactionService.deposit(self.wallet, currency_code="USD", amount=Decimal("50"))
        self.assertEqual(txn.amount, Decimal("50"))
        self.assertEqual(self.wallet.get_balance("USD"), Decimal("50"))
        txn_w = TransactionService.withdraw(self.wallet, currency_code="USD", amount=Decimal("20"))
        self.assertEqual(txn_w.amount, Decimal("20"))
        self.assertEqual(self.wallet.get_balance("USD"), Decimal("30"))

    def test_withdraw_insufficient(self):
        with self.assertRaises(InsufficientFundsError):
            TransactionService.withdraw(self.wallet, currency_code="USD", amount=Decimal("5"))

    def test_freeze_unfreeze(self):
        TransactionService.deposit(self.wallet, currency_code="USD", amount=Decimal("40"))
        TransactionService.freeze_funds(
            self.wallet,
            currency_code="USD",
            amount=Decimal("10"),
            reference_type="bet",
            reference_id="bet1",
        )
        balance = self.wallet.balances.get(currency_id="USD")
        self.assertEqual(balance.available, Decimal("30"))
        self.assertEqual(balance.frozen, Decimal("10"))
        TransactionService.unfreeze_funds(
            self.wallet,
            currency_code="USD",
            amount=Decimal("10"),
            reference_type="bet",
            reference_id="bet1",
        )
        balance.refresh_from_db()
        self.assertEqual(balance.available, Decimal("40"))
        self.assertEqual(balance.frozen, Decimal("0"))

    def test_conversion_execute(self):
        TransactionService.deposit(self.wallet, currency_code="USD", amount=Decimal("100"))
        order = ConversionService.execute_conversion(self.wallet, "USD", "EUR", Decimal("50"))
        self.assertEqual(order.from_amount, Decimal("50"))
        usd_balance = self.wallet.balances.get(currency_id="USD")
        eur_balance = self.wallet.balances.get(currency_id="EUR")
        self.assertLess(usd_balance.available, Decimal("100"))
        self.assertGreater(eur_balance.available, Decimal("0"))

    def test_conversion_same_currency_fails(self):
        with self.assertRaises(ValueError):
            ConversionService.execute_conversion(self.wallet, "USD", "USD", Decimal("10"))

    def test_withdrawal_request_auto_approve(self):
        TransactionService.deposit(self.wallet, currency_code="USD", amount=Decimal("200"))
        WalletSettings.get_settings()  # ensure singleton exists
        payment_details = {"card_number": "4111 1111 1111 1111"}
        with patch("apps.wallet.tasks.process_withdrawal_task.delay") as mock_task:
            req = WithdrawalService.create_withdrawal_request(
                self.wallet,
                currency_code="USD",
                amount=Decimal("20"),
                payment_method="card",
                payment_details=payment_details,
                ip_address="127.0.0.1",
            )
        self.assertIn(req.status, {"auto_approved", "manual_review"})
        if req.status == "auto_approved":
            mock_task.assert_called_once()
        self.assertEqual(req.currency.code, "USD")

    def test_withdrawal_pending_exists(self):
        TransactionService.deposit(self.wallet, currency_code="USD", amount=Decimal("20"))
        payment_details = {"wallet_id": "w1"}
        with patch("apps.wallet.tasks.process_withdrawal_task.delay"):
            WithdrawalService.create_withdrawal_request(
                self.wallet,
                currency_code="USD",
                amount=Decimal("10"),
                payment_method="ewallet",
                payment_details=payment_details,
                ip_address="127.0.0.1",
            )
        with self.assertRaises(WithdrawalValidationError):
            WithdrawalService.create_withdrawal_request(
                self.wallet,
                currency_code="USD",
                amount=Decimal("5"),
                payment_method="ewallet",
                payment_details=payment_details,
                ip_address="127.0.0.1",
            )

    def _create_manual_review_withdrawal(self, amount=Decimal("30")) -> WithdrawalRequest:
        self.user.trust_level = 1
        self.user.save(update_fields=["trust_level"])
        TransactionService.deposit(self.wallet, currency_code="USD", amount=Decimal("200"))
        with patch("apps.wallet.tasks.process_withdrawal_task.delay"):
            req = WithdrawalService.create_withdrawal_request(
                self.wallet,
                currency_code="USD",
                amount=amount,
                payment_method="card",
                payment_details={"card_number": "4000"},
                ip_address="127.0.0.1",
            )
        return req

    def test_withdrawal_approve_and_process(self):
        req = self._create_manual_review_withdrawal()
        self.assertEqual(req.status, "manual_review")
        WithdrawalService.approve_withdrawal(str(req.id), self.user, comment="ok")
        req.refresh_from_db()
        self.assertIn(req.status, {"approved", "completed"})
        if req.status != "completed":
            with patch("apps.wallet.tasks.process_withdrawal_task.delay"):
                pass  # avoid celery
            WithdrawalService.process_withdrawal(str(req.id))
            req.refresh_from_db()
        self.assertEqual(req.status, "completed")
        self.assertIsNotNone(req.transaction)
        balance = self.wallet.balances.get(currency_id="USD")
        self.assertLess(balance.available, Decimal("200"))

    def test_withdrawal_reject_unfreezes(self):
        req = self._create_manual_review_withdrawal()
        req.status = "manual_review"
        req.save(update_fields=["status"])
        balance = self.wallet.balances.get(currency_id="USD")
        available_before = balance.available
        req = WithdrawalService.reject_withdrawal(str(req.id), self.user, reason="test", comment="no")
        req.refresh_from_db()
        balance.refresh_from_db()
        self.assertEqual(req.status, "rejected")
        self.assertEqual(balance.available, available_before + req.amount)
        self.assertEqual(balance.frozen, Decimal("0"))
