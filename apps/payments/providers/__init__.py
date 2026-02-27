from apps.payments.providers.rukassa import RUkassaProvider
from apps.payments.providers.nowpayments import NOWPaymentsProvider
from apps.payments.providers.base import BasePaymentProvider


class DummyProvider(BasePaymentProvider):
    def __init__(self, code: str = "dummy"):
        super().__init__({"code": code})

    def create_deposit(self, **kwargs):
        return {
            "provider_order_id": f"prov-{kwargs.get('order_id', '0')}",
            "payment_url": "https://example.com/pay",
            "status": "created",
            "raw_response": {},
        }

    def check_deposit_status(self, provider_order_id):
        return {"status": "pending", "raw_response": {}}

    def create_payout(self, **kwargs):
        return {"provider_payout_id": f"pay-{kwargs.get('payout_id', '0')}", "status": "processing", "raw_response": {}}

    def check_payout_status(self, provider_payout_id):
        return {"status": "processing", "raw_response": {}}

    def verify_webhook_signature(self, payload, headers):
        return True

    def parse_webhook(self, payload, headers):
        return {"event_type": "unknown", "raw_data": payload}


def get_provider_instance(provider) -> BasePaymentProvider:
    code = getattr(provider, "code", "").lower()
    settings = {
        "code": code,
        "api_key": getattr(provider, "api_key", None),
        "api_secret": getattr(provider, "api_secret", None),
        "merchant_id": getattr(provider, "merchant_id", None),
        "webhook_secret": getattr(provider, "webhook_secret", None),
        "extra_settings": getattr(provider, "extra_settings", {}) or {},
    }
    if code == "rukassa":
        return RUkassaProvider(settings)
    if code == "nowpayments":
        return NOWPaymentsProvider(settings)
    return DummyProvider(code=code or "dummy")
