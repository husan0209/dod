from __future__ import annotations

import hashlib
import hmac
import json
from decimal import Decimal

from apps.payments.providers.base import BasePaymentProvider


class NOWPaymentsProvider(BasePaymentProvider):
    STATUS_MAP = {
        "waiting": "pending",
        "confirming": "processing",
        "confirmed": "processing",
        "sending": "processing",
        "finished": "completed",
        "failed": "failed",
        "expired": "expired",
        "refunded": "refunded",
    }

    def create_deposit(self, order_id, amount, currency, description, success_url, fail_url, customer_email):
        return {
            "provider_order_id": f"np-{order_id}",
            "payment_url": "https://nowpayments.io/payment/mock",
            "status": "pending",
            "raw_response": {},
        }

    def check_deposit_status(self, provider_order_id):
        return {"status": "pending", "raw_response": {}}

    def create_payout(self, payout_id, amount, currency, payment_details):
        return {"provider_payout_id": f"nppay-{payout_id}", "status": "processing", "raw_response": {}}

    def check_payout_status(self, provider_payout_id):
        return {"status": "processing", "raw_response": {}}

    def verify_webhook_signature(self, payload, headers):
        ipn_secret = self.provider_settings.get("webhook_secret") or ""
        sorted_payload = {k: payload[k] for k in sorted(payload)}
        json_string = json.dumps(sorted_payload, separators=(",", ":"))
        digest = hmac.new(ipn_secret.encode("utf-8"), msg=json_string.encode("utf-8"), digestmod=hashlib.sha512).hexdigest()
        received = headers.get("x-nowpayments-sig") or headers.get("x-nowpayments-signature")
        return digest == (received or "")

    def parse_webhook(self, payload, headers):
        status_raw = payload.get("payment_status") or payload.get("status")
        mapped_status = self.STATUS_MAP.get(status_raw, "pending")
        amount = Decimal(str(payload.get("price_amount") or payload.get("outcome_amount") or "0"))
        received_amount = payload.get("pay_amount") or payload.get("actually_paid")
        amount_received = Decimal(str(received_amount)) if received_amount is not None else None
        return {
            "event_type": "deposit_completed" if mapped_status == "completed" else "deposit_update",
            "order_id": payload.get("order_id"),
            "provider_order_id": payload.get("payment_id") or payload.get("order_id"),
            "status": mapped_status,
            "amount": amount,
            "amount_received": amount_received,
            "currency": (payload.get("pay_currency") or payload.get("price_currency") or "").upper(),
            "raw_data": payload,
        }
