from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict

logger = logging.getLogger(__name__)


class BasePaymentProvider(ABC):
    def __init__(self, provider_settings: Dict[str, Any]):
        self.provider_settings = provider_settings

    @abstractmethod
    def create_deposit(self, order_id, amount, currency, description, success_url, fail_url, customer_email) -> Dict:
        raise NotImplementedError

    @abstractmethod
    def check_deposit_status(self, provider_order_id) -> Dict:
        raise NotImplementedError

    @abstractmethod
    def create_payout(self, payout_id, amount, currency, payment_details) -> Dict:
        raise NotImplementedError

    @abstractmethod
    def check_payout_status(self, provider_payout_id) -> Dict:
        raise NotImplementedError

    @abstractmethod
    def verify_webhook_signature(self, payload, headers) -> bool:
        raise NotImplementedError

    @abstractmethod
    def parse_webhook(self, payload, headers) -> Dict:
        raise NotImplementedError

    def _log_api_call(self, method: str, endpoint: str, request_data: Dict, response_data: Dict, status_code: int, duration_ms: int):
        logger.info(
            "payment api call",
            extra={
                "provider": self.provider_settings.get("code"),
                "method": method,
                "endpoint": endpoint,
                "status_code": status_code,
                "duration_ms": duration_ms,
            },
        )
