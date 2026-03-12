from __future__ import annotations

from apps.payments.models import PaymentProvider, WebhookLog
from apps.payments.providers import get_provider_instance
from apps.payments.services.payment_service import PaymentService


def handle_rukassa_webhook(*, payload, headers, ip_address: str):
    provider = PaymentProvider.objects.filter(code="rukassa", is_active=True).first()
    if not provider:
        return {"status": 400, "body": {"error": "provider not configured"}}

    provider_client = get_provider_instance(provider)
    signature = payload.get("sign", "") if isinstance(payload, dict) else ""
    valid_signature = provider_client.verify_webhook_signature(payload, signature, headers)

    log = WebhookLog.objects.create(
        provider="rukassa",
        event_type="deposit",
        payload=payload,
        headers=headers,
        ip_address=ip_address,
        signature=payload.get("sign") if isinstance(payload, dict) else None,
        is_valid_signature=valid_signature,
    )

    if not valid_signature:
        log.processing_result = "invalid_signature"
        log.response_code = 400
        log.save(update_fields=["processing_result", "response_code"])
        return {"status": 400, "body": {"error": "invalid signature"}}

    parsed = provider_client.parse_webhook(payload)
    log.related_order_id = parsed.get("order_id")

    if parsed.get("status") == "completed":
        result = PaymentService.complete_deposit(parsed.get("order_id"), parsed.get("amount"))
        log.is_processed = True
        log.processing_result = result
    else:
        log.is_processed = False
        log.processing_result = "ignored"

    log.response_code = 200
    log.save(update_fields=["related_order_id", "is_processed", "processing_result", "response_code"])

    return {"status": 200, "body": {"ok": True}}
