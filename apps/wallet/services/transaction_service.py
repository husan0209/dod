from decimal import Decimal
from typing import Optional

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.wallet.models import Currency, Transaction, Wallet, WalletBalance

from apps.referral.models import Referral
from apps.referral.services.commission_service import CommissionService
from apps.referral.services.referral_service import ReferralService


class WalletFrozenError(Exception):
    pass


class CurrencyDisabledError(Exception):
    pass


class InsufficientFundsError(Exception):
    pass


class InvalidAmountError(Exception):
    pass


class TransactionService:
    @staticmethod
    def _get_balance_locked(wallet: Wallet, currency: Currency) -> WalletBalance:
        return (
            WalletBalance.objects.select_for_update()
            .select_related("currency")
            .get(wallet=wallet, currency=currency)
        )

    @staticmethod
    def _create_transaction(
        *,
        wallet: Wallet,
        user,
        currency: Currency,
        txn_type: str,
        amount: Decimal,
        amount_usd: Decimal,
        fee_amount: Decimal = Decimal("0"),
        balance_before: Decimal,
        balance_after: Decimal,
        description: str = "",
        metadata: Optional[dict] = None,
        ip_address: Optional[str] = None,
        created_by=None,
        reference_type: Optional[str] = None,
        reference_id: Optional[str] = None,
        status: str = "completed",
    ) -> Transaction:
        return Transaction.objects.create(
            wallet=wallet,
            user=user,
            type=txn_type,
            currency=currency,
            amount=amount,
            amount_usd=amount_usd,
            fee_amount=fee_amount,
            balance_before=balance_before,
            balance_after=balance_after,
            description=description,
            metadata=metadata or {},
            ip_address=ip_address,
            created_by=created_by,
            reference_type=reference_type,
            reference_id=reference_id,
            status=status,
        )

    @staticmethod
    def _validate_wallet_currency(wallet: Wallet, currency: Currency, *, for_deposit=False, for_withdrawal=False):
        if wallet.is_frozen:
            raise WalletFrozenError("Wallet is frozen")
        if for_deposit and not currency.is_deposit_enabled:
            raise CurrencyDisabledError("Deposits disabled for this currency")
        if for_withdrawal and not currency.is_withdrawal_enabled:
            raise CurrencyDisabledError("Withdrawals disabled for this currency")

    @staticmethod
    def deposit(
        wallet: Wallet,
        *,
        currency_code: str,
        amount: Decimal,
        fee_amount: Decimal = Decimal("0"),
        description: str = "",
        metadata: Optional[dict] = None,
        ip_address: Optional[str] = None,
        txn_type: str = "deposit",
        created_by=None,
        reference_type: Optional[str] = None,
        reference_id: Optional[str] = None,
    ) -> Transaction:
        currency = Currency.objects.get(code=currency_code)
        if amount <= 0:
            raise InvalidAmountError("Amount must be positive")
        TransactionService._validate_wallet_currency(wallet, currency, for_deposit=True)
        with transaction.atomic():
            balance = WalletBalance.objects.select_for_update().get_or_create(wallet=wallet, currency=currency)[0]
            balance_before = balance.available
            balance.credit(amount)
            balance_after = balance.available
            balance.save(update_fields=["available", "updated_at"])
            amount_usd = currency.convert_to_usd(amount)
            txn = TransactionService._create_transaction(
                wallet=wallet,
                user=wallet.user,
                currency=currency,
                txn_type=txn_type,
                amount=amount,
                amount_usd=amount_usd,
                balance_before=balance_before,
                balance_after=balance_after,
                fee_amount=fee_amount,
                description=description,
                metadata=metadata,
                ip_address=ip_address,
                created_by=created_by,
                reference_type=reference_type,
                reference_id=reference_id,
            )
            Wallet.objects.filter(pk=wallet.pk).update(total_deposited=F("total_deposited") + amount_usd)

            CommissionService.process_first_deposit(wallet.user, amount_usd)
            try:
                referral = Referral.objects.get(referral=wallet.user, level=1)
                referral.total_deposits += amount_usd
                referral.save(update_fields=['total_deposits'])
            except Referral.DoesNotExist:
                pass

            return txn

    @staticmethod
    def withdraw(
        wallet: Wallet,
        *,
        currency_code: str,
        amount: Decimal,
        fee_amount: Decimal = Decimal("0"),
        description: str = "",
        metadata: Optional[dict] = None,
        ip_address: Optional[str] = None,
        txn_type: str = "withdrawal",
        created_by=None,
        reference_type: Optional[str] = None,
        reference_id: Optional[str] = None,
    ) -> Transaction:
        currency = Currency.objects.get(code=currency_code)
        if amount <= 0:
            raise InvalidAmountError("Amount must be positive")
        TransactionService._validate_wallet_currency(wallet, currency, for_withdrawal=True)
        with transaction.atomic():
            balance = TransactionService._get_balance_locked(wallet, currency)
            if balance.available < amount:
                raise InsufficientFundsError("Недостаточно средств")
            balance_before = balance.available
            balance.debit(amount)
            balance_after = balance.available
            balance.save(update_fields=["available", "updated_at"])
            amount_usd = currency.convert_to_usd(amount)
            txn = TransactionService._create_transaction(
                wallet=wallet,
                user=wallet.user,
                currency=currency,
                txn_type=txn_type,
                amount=amount,
                amount_usd=amount_usd,
                balance_before=balance_before,
                balance_after=balance_after,
                fee_amount=fee_amount,
                description=description,
                metadata=metadata,
                ip_address=ip_address,
                created_by=created_by,
                reference_type=reference_type,
                reference_id=reference_id,
            )
            if txn_type in {"bet"}:
                Wallet.objects.filter(pk=wallet.pk).update(total_wagered=F("total_wagered") + amount_usd)
            elif txn_type in {"withdrawal"}:
                Wallet.objects.filter(pk=wallet.pk).update(total_withdrawn=F("total_withdrawn") + amount_usd)
            return txn

    @staticmethod
    def freeze_funds(wallet: Wallet, *, currency_code: str, amount: Decimal, reference_type: str, reference_id: str) -> Transaction:
        currency = Currency.objects.get(code=currency_code)
        if amount <= 0:
            raise InvalidAmountError("Amount must be positive")
        TransactionService._validate_wallet_currency(wallet, currency, for_withdrawal=True)
        with transaction.atomic():
            balance = TransactionService._get_balance_locked(wallet, currency)
            if balance.available < amount:
                raise InsufficientFundsError("Недостаточно средств")
            balance_before = balance.available
            balance.freeze(amount)
            balance_after = balance.available
            balance.save(update_fields=["available", "frozen", "updated_at"])
            amount_usd = currency.convert_to_usd(amount)
            return TransactionService._create_transaction(
                wallet=wallet,
                user=wallet.user,
                currency=currency,
                txn_type="freeze",
                amount=amount,
                amount_usd=amount_usd,
                balance_before=balance_before,
                balance_after=balance_after,
                reference_type=reference_type,
                reference_id=reference_id,
            )

    @staticmethod
    def unfreeze_funds(wallet: Wallet, *, currency_code: str, amount: Decimal, reference_type: str, reference_id: str) -> Transaction:
        currency = Currency.objects.get(code=currency_code)
        if amount <= 0:
            raise InvalidAmountError("Amount must be positive")
        with transaction.atomic():
            balance = TransactionService._get_balance_locked(wallet, currency)
            balance_before = balance.available
            balance.unfreeze(amount)
            balance_after = balance.available
            balance.save(update_fields=["available", "frozen", "updated_at"])
            amount_usd = currency.convert_to_usd(amount)
            return TransactionService._create_transaction(
                wallet=wallet,
                user=wallet.user,
                currency=currency,
                txn_type="unfreeze",
                amount=amount,
                amount_usd=amount_usd,
                balance_before=balance_before,
                balance_after=balance_after,
                reference_type=reference_type,
                reference_id=reference_id,
            )

    @staticmethod
    def settle_bet(wallet: Wallet, *, currency_code: str, frozen_amount: Decimal, win_amount: Decimal, reference_type: str, reference_id: str) -> Transaction:
        currency = Currency.objects.get(code=currency_code)
        with transaction.atomic():
            balance = TransactionService._get_balance_locked(wallet, currency)
            balance_before = balance.available
            balance.settle_frozen(frozen_amount)
            amount_usd_frozen = currency.convert_to_usd(frozen_amount)
            Wallet.objects.filter(pk=wallet.pk).update(total_wagered=F("total_wagered") + amount_usd_frozen)
            try:
                referral = Referral.objects.get(referral=wallet.user, level=1)
                referral.total_bets += amount_usd_frozen
                referral.save(update_fields=['total_bets'])
                ReferralService.qualify_referral(referral)
            except Referral.DoesNotExist:
                pass
            txn_type = "bet"
            amount = frozen_amount
            if win_amount and win_amount > 0:
                balance.credit(win_amount)
                txn_type = "win"
                amount = win_amount
                Wallet.objects.filter(pk=wallet.pk).update(total_won=F("total_won") + currency.convert_to_usd(win_amount))
            balance_after = balance.available
            balance.save(update_fields=["available", "frozen", "updated_at"])
            return TransactionService._create_transaction(
                wallet=wallet,
                user=wallet.user,
                currency=currency,
                txn_type=txn_type,
                amount=amount,
                amount_usd=currency.convert_to_usd(amount),
                balance_before=balance_before,
                balance_after=balance_after,
                reference_type=reference_type,
                reference_id=reference_id,
            )

    @staticmethod
    def complete_withdrawal(wallet: Wallet, *, currency_code: str, amount: Decimal, reference_id: str, ip_address: Optional[str] = None) -> Transaction:
        currency = Currency.objects.get(code=currency_code)
        with transaction.atomic():
            balance = TransactionService._get_balance_locked(wallet, currency)
            if balance.frozen < amount:
                raise InsufficientFundsError("Недостаточно замороженных средств")
            balance_before = balance.available
            balance.settle_frozen(amount)
            balance_after = balance.available
            balance.save(update_fields=["available", "frozen", "updated_at"])
            amount_usd = currency.convert_to_usd(amount)
            txn = TransactionService._create_transaction(
                wallet=wallet,
                user=wallet.user,
                currency=currency,
                txn_type="withdrawal",
                amount=amount,
                amount_usd=amount_usd,
                balance_before=balance_before,
                balance_after=balance_after,
                ip_address=ip_address,
                reference_type="withdrawal_request",
                reference_id=reference_id,
            )
            Wallet.objects.filter(pk=wallet.pk).update(total_withdrawn=F("total_withdrawn") + amount_usd)
            return txn

    @staticmethod
    def admin_adjustment(wallet: Wallet, *, currency_code: str, amount: Decimal, is_credit: bool, admin_user, reason: str) -> Transaction:
        txn_type = "adjustment"
        if is_credit:
            return TransactionService.deposit(
                wallet,
                currency_code=currency_code,
                amount=amount,
                description=reason,
                created_by=admin_user,
                txn_type=txn_type,
            )
        return TransactionService.withdraw(
            wallet,
            currency_code=currency_code,
            amount=amount,
            description=reason,
            created_by=admin_user,
            txn_type=txn_type,
        )
