from __future__ import annotations

import json
from typing import Callable

from django.http import JsonResponse, HttpRequest
from django.views.decorators.csrf import csrf_exempt

from apps.payments.services.payment_service import PaymentService
from apps.payments.services.payout_service import PayoutService
from apps.payments.services.antifraud_service import AntiFraudService
from apps.payments.webhooks.rukassa_webhook import handle_rukassa_webhook
from apps.payments.webhooks.nowpayments_webhook import handle_nowpayments_webhook


@csrf_exempt
def rukassa_webhook(request: HttpRequest):
    return _handle_webhook(request, handle_rukassa_webhook)


@csrf_exempt
def nowpayments_webhook(request: HttpRequest):
    return _handle_webhook(request, handle_nowpayments_webhook)


@csrf_exempt
def nowpayments_payout_webhook(request: HttpRequest):
    # Reuse same handler with context if needed later
    return _handle_webhook(request, handle_nowpayments_webhook)


def _handle_webhook(request: HttpRequest, handler: Callable):
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "invalid json"}, status=400)

    headers = {k.lower(): v for k, v in request.headers.items()}
    ip_address = request.META.get("REMOTE_ADDR", "")

    result = handler(payload=payload, headers=headers, ip_address=ip_address)
    return JsonResponse(result.get("body", {}), status=result.get("status", 200))
