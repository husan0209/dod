from __future__ import annotations

import hashlib
from decimal import Decimal

from apps.payments.providers.base import BasePaymentProvider


class RUkassaProvider(BasePaymentProvider):
    STATUS_MAP = {
        "WAIT": "pending",
        "PAID": "completed",
        "CANCEL": "cancelled",
        "FAIL": "failed",
    }

    def create_deposit(self, order_id, amount, currency, description, success_url, fail_url, customer_email):
        # Placeholder HTTP call; return mapped structure
        return {
            "provider_order_id": f"rk-{order_id}",
            "payment_url": "https://pay.rukassa.is/mock",
            "status": "pending",
            "raw_response": {},
        }

    def check_deposit_status(self, provider_order_id):
        # Placeholder for polling API
        return {"status": "pending", "raw_response": {}}

    def create_payout(self, payout_id, amount, currency, payment_details):
        return {"provider_payout_id": f"rkpay-{payout_id}", "status": "processing", "raw_response": {}}

    def check_payout_status(self, provider_payout_id):
        return {"status": "processing", "raw_response": {}}

    def verify_webhook_signature(self, payload, headers):
        webhook_secret = self.provider_settings.get("webhook_secret") or ""
        shop_id = self.provider_settings.get("merchant_id") or ""
        amount = str(payload.get("amount", ""))
        order_id = payload.get("order_id", "")
        sign_src = f"{shop_id}{amount}{order_id}{webhook_secret}"
        expected = hashlib.md5(sign_src.encode("utf-8")).hexdigest()
        received = str(payload.get("sign", ""))
        return expected == received

    def parse_webhook(self, payload, headers):
        status_raw = payload.get("status")
        mapped_status = self.STATUS_MAP.get(status_raw, "pending")
        amount = Decimal(str(payload.get("in_amount") or payload.get("amount") or "0"))
        return {
            "event_type": "deposit_completed" if mapped_status == "completed" else "deposit_update",
            "order_id": payload.get("order_id"),
            "provider_order_id": payload.get("id") or payload.get("order_id"),
            "status": mapped_status,
            "amount": amount,
            "currency": payload.get("currency") or payload.get("method"),
            "raw_data": payload,
        }
