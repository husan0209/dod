"""
Property-Based Tests for Payment Provider SDK

These tests validate universal properties that must hold for all provider implementations.
Uses hypothesis for property-based testing with minimum 100 iterations per test.
"""

from __future__ import annotations

from decimal import Decimal
from datetime import datetime
from typing import Dict, Any

from hypothesis import given, strategies as st, settings
from hypothesis.extra.django import TestCase

from apps.payments.providers import (
    BasePaymentProvider,
    DepositResponse,
    PayoutResponse,
    StatusResponse,
    ProviderAPIError,
    DummyProvider,
    get_provider_instance
)


# Custom strategies for payment-related data
@st.composite
def decimal_amount(draw, min_value=0.01, max_value=100000.00):
    """Generate valid decimal amounts for payments."""
    return Decimal(str(draw(st.floats(
        min_value=min_value,
        max_value=max_value,
        allow_nan=False,
        allow_infinity=False
    )))).quantize(Decimal("0.01"))


@st.composite
def currency_code(draw):
    """Generate valid currency codes."""
    return draw(st.sampled_from(['USD', 'RUB', 'EUR', 'BTC', 'ETH', 'USDT']))


@st.composite
def order_id(draw):
    """Generate valid order IDs."""
    return f"order-{draw(st.integers(min_value=1000, max_value=999999))}"


@st.composite
def email_address(draw):
    """Generate valid email addresses."""
    username = draw(st.text(alphabet=st.characters(whitelist_categories=('Ll', 'Nd')), min_size=3, max_size=10))
    domain = draw(st.sampled_from(['example.com', 'test.com', 'mail.com']))
    return f"{username}@{domain}"


class ProviderResponseStandardizationTests(TestCase):
    """
    Property 18: Provider response standardization
    
    For any provider's create_deposit method, the response must contain 
    the required fields: success, provider_order_id, and either payment_url 
    or crypto_address.
    
    Validates: Requirements 3.4
    """
    
    @given(
        order_id=order_id(),
        amount=decimal_amount(),
        currency=currency_code(),
        payment_method=st.text(min_size=3, max_size=20),
        user_email=email_address(),
    )
    @settings(max_examples=100, deadline=None)
    def test_deposit_response_has_required_fields(
        self,
        order_id: str,
        amount: Decimal,
        currency: str,
        payment_method: str,
        user_email: str
    ):
        """
        Property: All deposit responses must have required fields.
        
        For any valid deposit creation parameters, the DepositResponse must:
        1. Have a 'success' boolean field
        2. Have a 'provider_order_id' string field
        3. Have either 'payment_url' OR 'crypto_address' (at least one)
        """
        # Create a dummy provider instance
        provider = DummyProvider({"code": "test"})
        
        # Call create_deposit
        response = provider.create_deposit(
            order_id=order_id,
            amount=amount,
            currency=currency,
            payment_method_code=payment_method,
            user_email=user_email,
            success_url="https://example.com/success",
            fail_url="https://example.com/fail"
        )
        
        # Verify response is a DepositResponse instance
        self.assertIsInstance(response, DepositResponse)
        
        # Verify required fields exist
        self.assertIsInstance(response.success, bool)
        self.assertIsNotNone(response.provider_order_id)
        self.assertIsInstance(response.provider_order_id, str)
        self.assertGreater(len(response.provider_order_id), 0)
        
        # Verify at least one payment method is provided
        has_payment_method = (
            response.payment_url is not None or 
            response.crypto_address is not None
        )
        self.assertTrue(
            has_payment_method,
            "Response must have either payment_url or crypto_address"
        )
    
    @given(
        payout_id=order_id(),
        amount=decimal_amount(),
        currency=currency_code(),
    )
    @settings(max_examples=100, deadline=None)
    def test_payout_response_has_required_fields(
        self,
        payout_id: str,
        amount: Decimal,
        currency: str
    ):
        """
        Property: All payout responses must have required fields.
        
        For any valid payout creation parameters, the PayoutResponse must:
        1. Have a 'success' boolean field
        2. Have a 'provider_payout_id' string field
        3. Have a 'status' string field
        """
        provider = DummyProvider({"code": "test"})
        
        response = provider.create_payout(
            payout_id=payout_id,
            amount=amount,
            currency=currency,
            payment_details={"method": "card", "account": "1234"}
        )
        
        # Verify response is a PayoutResponse instance
        self.assertIsInstance(response, PayoutResponse)
        
        # Verify required fields
        self.assertIsInstance(response.success, bool)
        self.assertIsNotNone(response.provider_payout_id)
        self.assertIsInstance(response.provider_payout_id, str)
        self.assertGreater(len(response.provider_payout_id), 0)
        self.assertIsNotNone(response.status)
        self.assertIsInstance(response.status, str)
        self.assertIn(
            response.status,
            ['processing', 'completed', 'failed', 'pending', 'created'],
            "Status must be a valid payment status"
        )
    
    @given(provider_order_id=order_id())
    @settings(max_examples=100, deadline=None)
    def test_status_response_has_required_fields(self, provider_order_id: str):
        """
        Property: All status check responses must have required fields.
        
        For any status check, the StatusResponse must:
        1. Have a 'status' string field (internal status)
        2. Have a 'provider_status' string field (provider's original status)
        """
        provider = DummyProvider({"code": "test"})
        
        response = provider.check_deposit_status(provider_order_id)
        
        # Verify response is a StatusResponse instance
        self.assertIsInstance(response, StatusResponse)
        
        # Verify required fields
        self.assertIsNotNone(response.status)
        self.assertIsInstance(response.status, str)
        self.assertIsNotNone(response.provider_status)
        self.assertIsInstance(response.provider_status, str)
        
        # Verify status is a valid internal status
        valid_statuses = [
            'created', 'pending', 'processing', 'completed',
            'failed', 'expired', 'cancelled', 'refunded'
        ]
        self.assertIn(
            response.status,
            valid_statuses,
            f"Status must be one of {valid_statuses}"
        )
    
    @given(
        payload=st.dictionaries(
            keys=st.text(min_size=1, max_size=20),
            values=st.one_of(st.text(), st.integers(), st.decimals(allow_nan=False, allow_infinity=False))
        )
    )
    @settings(max_examples=100, deadline=None)
    def test_webhook_parsing_returns_standardized_format(self, payload: Dict[str, Any]):
        """
        Property: All webhook parsing must return standardized format.
        
        For any webhook payload, the parse_webhook method must return a dictionary with:
        1. 'order_id' field
        2. 'provider_order_id' field
        3. 'status' field
        4. 'amount' field
        5. 'currency' field
        6. 'provider_status' field
        """
        provider = DummyProvider({"code": "test"})
        
        # Add required fields to payload if not present
        test_payload = {
            "order_id": "test-order",
            "provider_order_id": "prov-123",
            "amount": "100.00",
            "currency": "USD",
            **payload
        }
        
        result = provider.parse_webhook(test_payload)
        
        # Verify result is a dictionary
        self.assertIsInstance(result, dict)
        
        # Verify required fields exist
        required_fields = [
            'order_id',
            'provider_order_id',
            'status',
            'amount',
            'currency',
            'provider_status'
        ]
        
        for field in required_fields:
            self.assertIn(
                field,
                result,
                f"Webhook parsing result must contain '{field}' field"
            )
        
        # Verify amount is Decimal
        self.assertIsInstance(result['amount'], Decimal)
    
    @given(
        signature=st.text(min_size=10, max_size=100),
        payload=st.dictionaries(
            keys=st.text(min_size=1, max_size=20),
            values=st.text()
        )
    )
    @settings(max_examples=100, deadline=None)
    def test_signature_verification_returns_boolean(
        self,
        signature: str,
        payload: Dict[str, Any]
    ):
        """
        Property: Signature verification must always return a boolean.
        
        For any signature and payload, verify_webhook_signature must return
        either True or False, never None or raise an exception.
        """
        provider = DummyProvider({"code": "test"})
        
        result = provider.verify_webhook_signature(
            payload=payload,
            signature=signature,
            headers={}
        )
        
        # Verify result is boolean
        self.assertIsInstance(result, bool)
        self.assertIn(result, [True, False])


class RUkassaSignatureVerificationTests(TestCase):
    """
    Property 14: RUkassa signature verification
    
    For any webhook payload with valid signature, RUkassa provider must correctly
    verify the signature. For any payload with invalid signature, it must reject it.
    
    Validates: Requirements 1.5, 6.5
    """
    
    @given(
        shop_id=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Ll', 'Lu', 'Nd'))),
        order_id=order_id(),
        amount=decimal_amount(min_value=1.00, max_value=10000.00),
        status=st.sampled_from(['new', 'pending', 'processing', 'success', 'failed', 'expired', 'cancelled']),
        webhook_secret=st.text(min_size=10, max_size=100, alphabet=st.characters(whitelist_categories=('Ll', 'Lu', 'Nd', 'P', 'S')))
    )
    @settings(max_examples=100, deadline=None)
    def test_valid_signature_is_accepted(
        self,
        shop_id: str,
        order_id: str,
        amount: Decimal,
        status: str,
        webhook_secret: str
    ):
        """
        Property: Valid signatures must always be accepted.
        
        For any webhook payload with a correctly computed MD5 signature,
        the verify_webhook_signature method must return True.
        
        Signature format: MD5(shop_id:order_id:amount:status:secret)
        """
        import hashlib
        
        # Create provider with the webhook secret
        provider_settings = {
            "code": "rukassa",
            "api_key": "test_key",
            "api_secret": "test_secret",
            "merchant_id": shop_id,
            "webhook_secret": webhook_secret,
            "api_base_url": "https://api.rukassa.is"
        }
        
        from apps.payments.providers import RUkassaProvider
        provider = RUkassaProvider(provider_settings)
        
        # Create webhook payload
        payload = {
            "shop_id": shop_id,
            "order_id": order_id,
            "amount": str(amount),
            "status": status,
            "payment_id": f"pay-{order_id}",
            "currency": "RUB"
        }
        
        # Generate valid signature using the same algorithm as the provider
        signature_string = f"{shop_id}:{order_id}:{amount}:{status}:{webhook_secret}"
        valid_signature = hashlib.md5(signature_string.encode()).hexdigest()
        
        # Verify signature
        result = provider.verify_webhook_signature(
            payload=payload,
            signature=valid_signature,
            headers={}
        )
        
        # Assert that valid signature is accepted
        self.assertTrue(
            result,
            f"Valid signature should be accepted. Signature: {valid_signature}, "
            f"String: {signature_string}"
        )
    
    @given(
        shop_id=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Ll', 'Lu', 'Nd'))),
        order_id=order_id(),
        amount=decimal_amount(min_value=1.00, max_value=10000.00),
        status=st.sampled_from(['new', 'pending', 'processing', 'success', 'failed', 'expired', 'cancelled']),
        webhook_secret=st.text(min_size=10, max_size=100, alphabet=st.characters(whitelist_categories=('Ll', 'Lu', 'Nd', 'P', 'S'))),
        invalid_signature=st.text(min_size=32, max_size=32, alphabet=st.characters(whitelist_categories=('Ll', 'Nd')))
    )
    @settings(max_examples=100, deadline=None)
    def test_invalid_signature_is_rejected(
        self,
        shop_id: str,
        order_id: str,
        amount: Decimal,
        status: str,
        webhook_secret: str,
        invalid_signature: str
    ):
        """
        Property: Invalid signatures must always be rejected.
        
        For any webhook payload with an incorrect signature,
        the verify_webhook_signature method must return False.
        """
        import hashlib
        
        # Create provider with the webhook secret
        provider_settings = {
            "code": "rukassa",
            "api_key": "test_key",
            "api_secret": "test_secret",
            "merchant_id": shop_id,
            "webhook_secret": webhook_secret,
            "api_base_url": "https://api.rukassa.is"
        }
        
        from apps.payments.providers import RUkassaProvider
        provider = RUkassaProvider(provider_settings)
        
        # Create webhook payload
        payload = {
            "shop_id": shop_id,
            "order_id": order_id,
            "amount": str(amount),
            "status": status,
            "payment_id": f"pay-{order_id}",
            "currency": "RUB"
        }
        
        # Generate the correct signature to ensure our invalid one is different
        signature_string = f"{shop_id}:{order_id}:{amount}:{status}:{webhook_secret}"
        correct_signature = hashlib.md5(signature_string.encode()).hexdigest()
        
        # Skip test if randomly generated invalid signature happens to match correct one
        if invalid_signature == correct_signature:
            return
        
        # Verify signature with invalid signature
        result = provider.verify_webhook_signature(
            payload=payload,
            signature=invalid_signature,
            headers={}
        )
        
        # Assert that invalid signature is rejected
        self.assertFalse(
            result,
            f"Invalid signature should be rejected. Invalid: {invalid_signature}, "
            f"Correct: {correct_signature}"
        )
    
    @given(
        shop_id=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Ll', 'Lu', 'Nd'))),
        order_id=order_id(),
        amount=decimal_amount(min_value=1.00, max_value=10000.00),
        status=st.sampled_from(['new', 'pending', 'processing', 'success', 'failed', 'expired', 'cancelled']),
        webhook_secret=st.text(min_size=10, max_size=100, alphabet=st.characters(whitelist_categories=('Ll', 'Lu', 'Nd', 'P', 'S'))),
        wrong_secret=st.text(min_size=10, max_size=100, alphabet=st.characters(whitelist_categories=('Ll', 'Lu', 'Nd', 'P', 'S')))
    )
    @settings(max_examples=100, deadline=None)
    def test_signature_with_wrong_secret_is_rejected(
        self,
        shop_id: str,
        order_id: str,
        amount: Decimal,
        status: str,
        webhook_secret: str,
        wrong_secret: str
    ):
        """
        Property: Signatures computed with wrong secret must be rejected.
        
        For any webhook payload where the signature was computed using a different
        secret than the provider's configured secret, verification must fail.
        
        This ensures that webhooks from attackers who don't know the secret
        will always be rejected.
        """
        import hashlib
        
        # Skip if secrets happen to be the same
        if webhook_secret == wrong_secret:
            return
        
        # Create provider with the correct webhook secret
        provider_settings = {
            "code": "rukassa",
            "api_key": "test_key",
            "api_secret": "test_secret",
            "merchant_id": shop_id,
            "webhook_secret": webhook_secret,
            "api_base_url": "https://api.rukassa.is"
        }
        
        from apps.payments.providers import RUkassaProvider
        provider = RUkassaProvider(provider_settings)
        
        # Create webhook payload
        payload = {
            "shop_id": shop_id,
            "order_id": order_id,
            "amount": str(amount),
            "status": status,
            "payment_id": f"pay-{order_id}",
            "currency": "RUB"
        }
        
        # Generate signature using WRONG secret (simulating attacker)
        signature_string = f"{shop_id}:{order_id}:{amount}:{status}:{wrong_secret}"
        wrong_signature = hashlib.md5(signature_string.encode()).hexdigest()
        
        # Verify signature
        result = provider.verify_webhook_signature(
            payload=payload,
            signature=wrong_signature,
            headers={}
        )
        
        # Assert that signature with wrong secret is rejected
        self.assertFalse(
            result,
            f"Signature computed with wrong secret should be rejected. "
            f"Correct secret: {webhook_secret}, Wrong secret: {wrong_secret}"
        )
    
    @given(
        shop_id=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Ll', 'Lu', 'Nd'))),
        order_id=order_id(),
        original_amount=decimal_amount(min_value=1.00, max_value=10000.00),
        tampered_amount=decimal_amount(min_value=1.00, max_value=10000.00),
        status=st.sampled_from(['new', 'pending', 'processing', 'success', 'failed', 'expired', 'cancelled']),
        webhook_secret=st.text(min_size=10, max_size=100, alphabet=st.characters(whitelist_categories=('Ll', 'Lu', 'Nd', 'P', 'S')))
    )
    @settings(max_examples=100, deadline=None)
    def test_tampered_payload_is_rejected(
        self,
        shop_id: str,
        order_id: str,
        original_amount: Decimal,
        tampered_amount: Decimal,
        status: str,
        webhook_secret: str
    ):
        """
        Property: Tampered payloads must be rejected.
        
        For any webhook where the payload has been modified after signature
        generation (e.g., amount changed), verification must fail.
        
        This ensures that attackers cannot modify webhook data without
        detection.
        """
        import hashlib
        
        # Skip if amounts happen to be the same
        if original_amount == tampered_amount:
            return
        
        # Create provider
        provider_settings = {
            "code": "rukassa",
            "api_key": "test_key",
            "api_secret": "test_secret",
            "merchant_id": shop_id,
            "webhook_secret": webhook_secret,
            "api_base_url": "https://api.rukassa.is"
        }
        
        from apps.payments.providers import RUkassaProvider
        provider = RUkassaProvider(provider_settings)
        
        # Generate signature for ORIGINAL amount
        signature_string = f"{shop_id}:{order_id}:{original_amount}:{status}:{webhook_secret}"
        signature = hashlib.md5(signature_string.encode()).hexdigest()
        
        # Create payload with TAMPERED amount (different from original)
        tampered_payload = {
            "shop_id": shop_id,
            "order_id": order_id,
            "amount": str(tampered_amount),  # Tampered!
            "status": status,
            "payment_id": f"pay-{order_id}",
            "currency": "RUB"
        }
        
        # Verify signature with tampered payload
        result = provider.verify_webhook_signature(
            payload=tampered_payload,
            signature=signature,
            headers={}
        )
        
        # Assert that tampered payload is rejected
        self.assertFalse(
            result,
            f"Tampered payload should be rejected. Original amount: {original_amount}, "
            f"Tampered amount: {tampered_amount}"
        )


class ProviderFactoryTests(TestCase):
    """Tests for the provider factory function."""
    
    @given(provider_code=st.sampled_from(['rukassa', 'nowpayments', 'dummy', 'unknown']))
    @settings(max_examples=50, deadline=None)
    def test_get_provider_instance_returns_provider(self, provider_code: str):
        """
        Property: Factory function must always return a provider instance.
        
        For any provider code, get_provider_instance must return an instance
        that implements BasePaymentProvider interface.
        """
        provider_settings = {
            "code": provider_code,
            "api_key": "test_key",
            "api_secret": "test_secret",
            "merchant_id": "test_merchant",
            "webhook_secret": "test_webhook_secret",
        }
        
        provider = get_provider_instance(provider_settings)
        
        # Verify it's a BasePaymentProvider instance
        self.assertIsInstance(provider, BasePaymentProvider)
        
        # Verify it has all required methods
        self.assertTrue(hasattr(provider, 'create_deposit'))
        self.assertTrue(hasattr(provider, 'check_deposit_status'))
        self.assertTrue(hasattr(provider, 'create_payout'))
        self.assertTrue(hasattr(provider, 'check_payout_status'))
        self.assertTrue(hasattr(provider, 'verify_webhook_signature'))
        self.assertTrue(hasattr(provider, 'parse_webhook'))
        
        # Verify all methods are callable
        self.assertTrue(callable(provider.create_deposit))
        self.assertTrue(callable(provider.check_deposit_status))
        self.assertTrue(callable(provider.create_payout))
        self.assertTrue(callable(provider.check_payout_status))
        self.assertTrue(callable(provider.verify_webhook_signature))
        self.assertTrue(callable(provider.parse_webhook))
