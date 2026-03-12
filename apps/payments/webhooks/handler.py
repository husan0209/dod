"""
Webhook handler for payment providers.

Handles incoming webhooks from payment providers with comprehensive security:
- IP whitelisting
- Signature verification
- Comprehensive logging
- Idempotency
"""

import json
import time
import logging
import ipaddress
from typing import Dict, Any, Optional

from django.http import HttpResponse, HttpRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator

from apps.payments.models import WebhookLog, PaymentProvider
from apps.payments.providers import get_provider_instance
from apps.payments.services.payment_service import PaymentService
from apps.payments.services.payout_service import PayoutService

logger = logging.getLogger(__name__)


class WebhookHandler:
    """
    Handles incoming webhooks from payment providers.
    
    Security measures:
    - IP whitelisting
    - Signature verification
    - Comprehensive logging
    - Idempotency
    """
    
    # Provider IP whitelists
    # These should be kept up to date with provider documentation
    IP_WHITELISTS = {
        "rukassa": [
            "185.71.76.0/27",
            "185.71.77.0/27",
            "77.83.247.0/27"
        ],
        "nowpayments": [
            "18.209.98.55",
            "52.200.159.85",
            "54.236.28.238"
        ]
    }
    
    def __init__(self):
        self.payment_service = PaymentService()
        self.payout_service = PayoutService()
    
    @method_decorator(csrf_exempt)
    @method_decorator(require_POST)
    def handle_deposit_webhook(self, request: HttpRequest, provider_code: str) -> HttpResponse:
        """
        Handle deposit webhook from provider.
        
        Steps:
        1. Log webhook
        2. Verify IP
        3. Verify signature
        4. Parse webhook
        5. Process confirmation
        6. Return response
        
        Args:
            request: Django HTTP request
            provider_code: Provider code (rukassa, nowpayments)
            
        Returns:
            HttpResponse with appropriate status code
        """
        start_time = time.perf_counter()
        
        # Parse payload
        try:
            if request.content_type == 'application/json':
                payload = json.loads(request.body.decode('utf-8'))
            else:
                # Form-encoded data
                payload = dict(request.POST)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.error(f"Failed to parse webhook payload: {e}")
            return HttpResponse("Bad Request", status=400)
        
        headers = dict(request.headers)
        ip_address = self._get_client_ip(request)
        
        # Create webhook log
        webhook_log = WebhookLog.objects.create(
            provider=provider_code,
            event_type="deposit",
            payload=payload,
            headers=headers,
            ip_address=ip_address
        )
        
        try:
            # Verify IP
            if not self._verify_ip(ip_address, provider_code):
                webhook_log.is_valid_signature = False
                webhook_log.processing_result = "ip_rejected"
                webhook_log.response_code = 403
                webhook_log.save()
                logger.warning(
                    f"Webhook from non-whitelisted IP: {ip_address} for provider {provider_code}"
                )
                return HttpResponse("Forbidden", status=403)
            
            # Get provider instance
            try:
                provider = PaymentProvider.objects.get(code=provider_code)
            except PaymentProvider.DoesNotExist:
                webhook_log.processing_result = "provider_not_found"
                webhook_log.response_code = 404
                webhook_log.save()
                logger.error(f"Provider not found: {provider_code}")
                return HttpResponse("Not Found", status=404)
            
            provider_instance = get_provider_instance(provider)
            
            # Verify signature
            signature = self._extract_signature(headers, payload, provider_code)
            is_valid = provider_instance.verify_webhook_signature(payload, signature, headers)
            
            webhook_log.signature = signature
            webhook_log.is_valid_signature = is_valid
            
            if not is_valid:
                webhook_log.processing_result = "signature_invalid"
                webhook_log.response_code = 401
                webhook_log.save()
                logger.warning(
                    f"Invalid webhook signature from {provider_code}, IP: {ip_address}"
                )
                return HttpResponse("Unauthorized", status=401)
            
            # Parse webhook
            webhook_data = provider_instance.parse_webhook(payload)
            webhook_log.related_order_id = webhook_data.get("order_id", "")
            
            # Process confirmation
            processed = self.payment_service.process_webhook_confirmation(
                provider_code,
                webhook_data
            )
            
            webhook_log.is_processed = processed
            webhook_log.processing_result = "success" if processed else "duplicate"
            webhook_log.response_code = 200
            
            logger.info(
                f"Deposit webhook processed: provider={provider_code}, "
                f"order_id={webhook_data.get('order_id')}, "
                f"status={webhook_data.get('status')}, "
                f"processed={processed}"
            )
            
        except Exception as e:
            webhook_log.processing_result = "error"
            webhook_log.processing_error = str(e)
            webhook_log.response_code = 500
            webhook_log.save()
            logger.error(
                f"Webhook processing error: provider={provider_code}, error={e}",
                exc_info=True
            )
            return HttpResponse("Internal Server Error", status=500)
        
        finally:
            processing_time = int((time.perf_counter() - start_time) * 1000)
            webhook_log.processing_time_ms = max(processing_time, 1)  # Ensure at least 1ms
            webhook_log.save()
        
        return HttpResponse("OK", status=200)
    
    @method_decorator(csrf_exempt)
    @method_decorator(require_POST)
    def handle_payout_webhook(self, request: HttpRequest, provider_code: str) -> HttpResponse:
        """
        Handle payout webhook from provider.
        
        Similar to deposit webhook but for payouts.
        
        Args:
            request: Django HTTP request
            provider_code: Provider code (rukassa, nowpayments)
            
        Returns:
            HttpResponse with appropriate status code
        """
        start_time = time.perf_counter()
        
        # Parse payload
        try:
            if request.content_type == 'application/json':
                payload = json.loads(request.body.decode('utf-8'))
            else:
                # Form-encoded data
                payload = dict(request.POST)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.error(f"Failed to parse payout webhook payload: {e}")
            return HttpResponse("Bad Request", status=400)
        
        headers = dict(request.headers)
        ip_address = self._get_client_ip(request)
        
        # Create webhook log
        webhook_log = WebhookLog.objects.create(
            provider=provider_code,
            event_type="payout",
            payload=payload,
            headers=headers,
            ip_address=ip_address
        )
        
        try:
            # Verify IP
            if not self._verify_ip(ip_address, provider_code):
                webhook_log.is_valid_signature = False
                webhook_log.processing_result = "ip_rejected"
                webhook_log.response_code = 403
                webhook_log.save()
                logger.warning(
                    f"Payout webhook from non-whitelisted IP: {ip_address} for provider {provider_code}"
                )
                return HttpResponse("Forbidden", status=403)
            
            # Get provider instance
            try:
                provider = PaymentProvider.objects.get(code=provider_code)
            except PaymentProvider.DoesNotExist:
                webhook_log.processing_result = "provider_not_found"
                webhook_log.response_code = 404
                webhook_log.save()
                logger.error(f"Provider not found: {provider_code}")
                return HttpResponse("Not Found", status=404)
            
            provider_instance = get_provider_instance(provider)
            
            # Verify signature
            signature = self._extract_signature(headers, payload, provider_code)
            is_valid = provider_instance.verify_webhook_signature(payload, signature, headers)
            
            webhook_log.signature = signature
            webhook_log.is_valid_signature = is_valid
            
            if not is_valid:
                webhook_log.processing_result = "signature_invalid"
                webhook_log.response_code = 401
                webhook_log.save()
                logger.warning(
                    f"Invalid payout webhook signature from {provider_code}, IP: {ip_address}"
                )
                return HttpResponse("Unauthorized", status=401)
            
            # Parse webhook
            webhook_data = provider_instance.parse_webhook(payload)
            webhook_log.related_order_id = webhook_data.get("payout_id", webhook_data.get("extra_id", ""))
            
            # Process confirmation
            processed = self.payout_service.process_webhook_confirmation(
                provider_code,
                webhook_data
            )
            
            webhook_log.is_processed = processed
            webhook_log.processing_result = "success" if processed else "duplicate"
            webhook_log.response_code = 200
            
            logger.info(
                f"Payout webhook processed: provider={provider_code}, "
                f"payout_id={webhook_log.related_order_id}, "
                f"status={webhook_data.get('status')}, "
                f"processed={processed}"
            )
            
        except Exception as e:
            webhook_log.processing_result = "error"
            webhook_log.processing_error = str(e)
            webhook_log.response_code = 500
            webhook_log.save()
            logger.error(
                f"Payout webhook processing error: provider={provider_code}, error={e}",
                exc_info=True
            )
            return HttpResponse("Internal Server Error", status=500)
        
        finally:
            processing_time = int((time.perf_counter() - start_time) * 1000)
            webhook_log.processing_time_ms = max(processing_time, 1)  # Ensure at least 1ms
            webhook_log.save()
        
        return HttpResponse("OK", status=200)
    
    def _verify_ip(self, ip_address: str, provider_code: str) -> bool:
        """
        Verify IP is in provider's whitelist.
        
        Args:
            ip_address: Client IP address
            provider_code: Provider code
            
        Returns:
            True if IP is whitelisted, False otherwise
        """
        whitelist = self.IP_WHITELISTS.get(provider_code, [])
        if not whitelist:
            # No whitelist configured - allow all (for development/testing)
            logger.warning(f"No IP whitelist configured for provider {provider_code}")
            return True
        
        try:
            client_ip = ipaddress.ip_address(ip_address)
            
            for allowed in whitelist:
                if '/' in allowed:
                    # CIDR notation (network range)
                    if client_ip in ipaddress.ip_network(allowed):
                        return True
                else:
                    # Single IP address
                    if str(client_ip) == allowed:
                        return True
            
            return False
            
        except ValueError as e:
            logger.error(f"Invalid IP address format: {ip_address}, error: {e}")
            return False
    
    def _extract_signature(self, headers: Dict, payload: Dict, provider_code: str) -> str:
        """
        Extract signature from headers or payload based on provider.
        
        Args:
            headers: Request headers
            payload: Request payload
            provider_code: Provider code
            
        Returns:
            Signature string
        """
        if provider_code == "rukassa":
            # RUkassa sends signature in payload as 'sign' field
            return payload.get("sign", "")
        elif provider_code == "nowpayments":
            # NOWpayments sends signature in header
            return headers.get("X-Nowpayments-Sig", headers.get("x-nowpayments-sig", ""))
        
        # Unknown provider - try common locations
        return (
            headers.get("X-Signature", "") or
            headers.get("Signature", "") or
            payload.get("signature", "") or
            payload.get("sign", "")
        )
    
    def _get_client_ip(self, request: HttpRequest) -> str:
        """
        Get client IP from request, considering proxies.
        
        Checks X-Forwarded-For header first (for proxied requests),
        then falls back to REMOTE_ADDR.
        
        Args:
            request: Django HTTP request
            
        Returns:
            Client IP address as string
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            # X-Forwarded-For can contain multiple IPs, take the first one
            return x_forwarded_for.split(',')[0].strip()
        
        return request.META.get('REMOTE_ADDR', '')


# Create a singleton instance for use in URL routing
webhook_handler = WebhookHandler()
