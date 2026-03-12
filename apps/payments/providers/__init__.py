"""
Payment Provider SDK

This module provides a unified interface for integrating with payment providers.
It includes:
- BasePaymentProvider: Abstract base class for all providers
- DepositResponse, PayoutResponse, StatusResponse: Standardized response dataclasses
- ProviderAPIError: Custom exception for provider API errors
- get_provider_instance(): Factory function to instantiate providers
"""

from apps.payments.providers.base import (
    BasePaymentProvider,
    DepositResponse,
    PayoutResponse,
    StatusResponse,
    ProviderAPIError
)
from apps.payments.providers.rukassa import RUkassaProvider
from apps.payments.providers.nowpayments import NOWPaymentsProvider


# Provider registry mapping provider codes to their implementation classes
PROVIDER_REGISTRY = {
    "rukassa": RUkassaProvider,
    "nowpayments": NOWPaymentsProvider,
}


class DummyProvider(BasePaymentProvider):
    """
    Dummy provider for testing and development.
    Returns mock responses without calling real APIs.
    """
    
    def __init__(self, provider_settings: dict):
        super().__init__(provider_settings)

    def create_deposit(self, **kwargs):
        from decimal import Decimal
        return DepositResponse(
            success=True,
            provider_order_id=f"prov-{kwargs.get('order_id', '0')}",
            payment_url="https://example.com/pay",
            amount=kwargs.get('amount', Decimal('0')),
            raw_response={}
        )

    def check_deposit_status(self, provider_order_id):
        return StatusResponse(
            status="pending",
            provider_status="pending"
        )

    def create_payout(self, **kwargs):
        return PayoutResponse(
            success=True,
            provider_payout_id=f"pay-{kwargs.get('payout_id', '0')}",
            status="processing",
            raw_response={}
        )

    def check_payout_status(self, provider_payout_id):
        return StatusResponse(
            status="processing",
            provider_status="processing"
        )

    def verify_webhook_signature(self, payload, signature, headers):
        return True

    def parse_webhook(self, payload):
        from decimal import Decimal
        return {
            "order_id": payload.get("order_id", "unknown"),
            "provider_order_id": payload.get("provider_order_id", "unknown"),
            "status": "completed",
            "amount": Decimal(payload.get("amount", "0")),
            "currency": payload.get("currency", "USD"),
            "provider_status": "completed"
        }


def get_provider_instance(provider) -> BasePaymentProvider:
    """
    Factory function to instantiate the appropriate provider implementation.
    
    Args:
        provider: PaymentProvider model instance or dict with provider settings
    
    Returns:
        Instance of the appropriate provider class (RUkassaProvider, NOWPaymentsProvider, etc.)
    
    Example:
        >>> provider = PaymentProvider.objects.get(code='rukassa')
        >>> provider_instance = get_provider_instance(provider)
        >>> response = provider_instance.create_deposit(...)
    """
    # Extract provider code
    if hasattr(provider, 'code'):
        code = provider.code.lower()
    elif isinstance(provider, dict):
        code = provider.get('code', '').lower()
    else:
        code = str(provider).lower()
    
    # Build provider settings dictionary
    if hasattr(provider, '__dict__'):
        # It's a model instance
        settings = {
            "code": code,
            "api_key": getattr(provider, "api_key", None),
            "api_secret": getattr(provider, "api_secret", None),
            "merchant_id": getattr(provider, "merchant_id", None),
            "webhook_secret": getattr(provider, "webhook_secret", None),
            "api_base_url": getattr(provider, "api_base_url", None),
            "extra_settings": getattr(provider, "extra_settings", {}) or {},
        }
    elif isinstance(provider, dict):
        # It's already a settings dict
        settings = provider
    else:
        # Fallback
        settings = {"code": code}
    
    # Get provider class from registry
    provider_class = PROVIDER_REGISTRY.get(code)
    
    if provider_class:
        return provider_class(settings)
    else:
        # Return dummy provider for unknown codes
        return DummyProvider(settings)


# Export all public interfaces
__all__ = [
    'BasePaymentProvider',
    'DepositResponse',
    'PayoutResponse',
    'StatusResponse',
    'ProviderAPIError',
    'RUkassaProvider',
    'NOWPaymentsProvider',
    'DummyProvider',
    'get_provider_instance',
    'PROVIDER_REGISTRY',
]
