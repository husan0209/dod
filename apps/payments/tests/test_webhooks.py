from __future__ import annotations

import hashlib
import hmac
import json
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase

from apps.payments.webhooks.rukassa_webhook import handle_rukassa_webhook
from apps.payments.webhooks.nowpayments_webhook import handle_nowpayments_webhook


class RUkassaWebhookTests(TestCase):
    fixtures = ["payments_providers_methods.json"]

    def _sign(self, shop_id: str, order_id: str, amount: str, status: str, secret: str) -> str:
        return hashlib.md5(f"{shop_id}:{order_id}:{amount}:{status}:{secret}".encode("utf-8")).hexdigest()

    def test_invalid_signature_returns_400(self):
        payload = {"order_id": "DEP-1", "amount": "100.00", "sign": "bad"}
        result = handle_rukassa_webhook(payload=payload, headers={}, ip_address="127.0.0.1")
        self.assertEqual(result["status"], 400)
        self.assertIn("error", result["body"])

    def test_valid_signature_calls_complete(self):
        shop_id = "CHANGE_ME"
        secret = "CHANGE_ME"
        payload = {
            "shop_id": shop_id,
            "order_id": "DEP-123",
            "amount": "150.00",
            "status": "PAID",
        }
        payload["sign"] = self._sign(shop_id, payload["order_id"], payload["amount"], payload["status"], secret)

        with patch("apps.payments.webhooks.rukassa_webhook.PaymentService.complete_deposit") as mock_complete:
            mock_complete.return_value = "completed"
            result = handle_rukassa_webhook(payload=payload, headers={}, ip_address="127.0.0.1")

        mock_complete.assert_called_once_with("DEP-123", Decimal("150.00"))
        self.assertEqual(result["status"], 200)


class NowPaymentsWebhookTests(TestCase):
    fixtures = ["payments_providers_methods.json"]

    def _sign(self, payload: dict, secret: str) -> str:
        sorted_payload = {k: payload[k] for k in sorted(payload)}
        json_string = json.dumps(sorted_payload, separators=(",", ":"))
        return hmac.new(secret.encode("utf-8"), msg=json_string.encode("utf-8"), digestmod=hashlib.sha512).hexdigest()

    def test_invalid_signature_returns_400(self):
        payload = {"order_id": "DEP-1", "payment_status": "finished"}
        result = handle_nowpayments_webhook(payload=payload, headers={}, ip_address="127.0.0.1")
        self.assertEqual(result["status"], 400)
        self.assertIn("error", result["body"])

    def test_valid_signature_calls_complete(self):
        secret = "CHANGE_ME"
        payload = {
            "order_id": "DEP-999",
            "payment_id": 5678,
            "payment_status": "finished",
            "price_amount": 100,
            "price_currency": "usd",
            "pay_currency": "btc",
            "pay_amount": 0.0015,
        }
        sig = self._sign(payload, secret)
        headers = {"x-nowpayments-sig": sig}

        with patch("apps.payments.webhooks.nowpayments_webhook.PaymentService.complete_deposit") as mock_complete:
            mock_complete.return_value = "completed"
            result = handle_nowpayments_webhook(payload=payload, headers=headers, ip_address="127.0.0.1")

        mock_complete.assert_called_once_with("DEP-999", Decimal("0.0015"))
        self.assertEqual(result["status"], 200)
