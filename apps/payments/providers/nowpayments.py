from __future__ import annotations

import hmac
import hashlib
import json
import logging
from decimal import Decimal
from typing import Dict, Any
from datetime import datetime, timedelta
from django.utils import timezone

from apps.payments.providers.base import (
    BasePaymentProvider,
    DepositResponse,
    PayoutResponse,
    StatusResponse,
    ProviderAPIError
)

logger = logging.getLogger(__name__)


class NOWPaymentsProvider(BasePaymentProvider):
    """
    NOWpayments API Integration
    
    API Documentation: https://documenter.getpostman.com/view/7907941/S1a32n38
    
    Supported Cryptocurrencies: BTC, ETH, USDT, TON, and 200+ others
    
    Features:
    - Auto-conversion to stablecoins
    - Partial payment tracking
    - Multiple cryptocurrency support
    
    Webhook Signature: HMAC SHA-512
    """
    
    def create_deposit(
        self,
        order_id: str,
        amount: Decimal,
        currency: str,
        payment_method_code: str,
        user_email: str,
        success_url: str,
        fail_url: str,
        **kwargs
    ) -> DepositResponse:
        """
        Create a deposit order with NOWpayments.
        
        API Endpoint: POST /v1/payment
        
        Args:
            order_id: Unique order identifier
            amount: Deposit amount
            currency: Price currency (e.g., 'USD', 'RUB')
            payment_method_code: Cryptocurrency code (e.g., 'btc', 'eth', 'usdttrc20')
            user_email: User's email address
            success_url: URL to redirect on successful payment
            fail_url: URL to redirect on failed payment
            **kwargs: Additional parameters (webhook_url)
        
        Returns:
            DepositResponse with crypto payment details
        """
        endpoint = "/v1/payment"
        
        # Auto-conversion to stablecoin if configured
        pay_currency = payment_method_code
        if self.extra_settings.get("auto_convert_to_stablecoin"):
            pay_currency = self.extra_settings.get("default_stablecoin", "usdttrc20")
        
        data = {
            "price_amount": str(amount),
            "price_currency": currency,
            "pay_currency": pay_currency,
            "order_id": order_id,
            "order_description": f"Deposit {order_id}",
            "ipn_callback_url": kwargs.get("webhook_url", ""),
            "success_url": success_url,
            "cancel_url": fail_url
        }
        
        headers = {"x-api-key": self.api_key}
        
        try:
            response = self._make_request("POST", endpoint, data=data, headers=headers)
            
            return DepositResponse(
                success=True,
                provider_order_id=str(response.get("payment_id", "")),
                payment_url=response.get("invoice_url", ""),
                crypto_address=response.get("pay_address", ""),
                crypto_network=response.get("network", ""),
                amount=Decimal(str(response.get("pay_amount", 0))),
                expires_at=self._parse_datetime(response.get("expiration_estimate_date")),
                raw_response=response
            )
        except ProviderAPIError as e:
            logger.error(f"NOWpayments create_deposit failed: {e}")
            return DepositResponse(
                success=False,
                provider_order_id="",
                error_message=str(e),
                raw_response=e.response_data
            )
        except Exception as e:
            logger.error(f"NOWpayments create_deposit unexpected error: {e}")
            return DepositResponse(
                success=False,
                provider_order_id="",
                error_message=str(e)
            )
    
    def check_deposit_status(self, provider_order_id: str) -> StatusResponse:
        """
        Query NOWpayments for deposit status.
        
        API Endpoint: GET /v1/payment/{payment_id}
        """
        endpoint = f"/v1/payment/{provider_order_id}"
        headers = {"x-api-key": self.api_key}
        
        try:
            response = self._make_request("GET", endpoint, headers=headers)
            
            return StatusResponse(
                status=self._map_status(response.get("payment_status", "")),
                provider_status=response.get("payment_status", ""),
                amount_received=Decimal(str(response.get("actually_paid", 0))),
                completed_at=self._parse_datetime(response.get("updated_at"))
            )
        except Exception as e:
            logger.error(f"NOWpayments check_deposit_status failed: {e}")
            return StatusResponse(
                status="pending",
                provider_status="unknown",
                error_message=str(e)
            )
    
    def create_payout(
        self,
        payout_id: str,
        amount: Decimal,
        currency: str,
        payment_details: Dict[str, Any],
        **kwargs
    ) -> PayoutResponse:
        """
        Create a payout order with NOWpayments.
        
        API Endpoint: POST /v1/payout
        
        Args:
            payout_id: Unique payout identifier
            amount: Payout amount
            currency: Cryptocurrency code (e.g., 'btc', 'eth')
            payment_details: Must contain 'crypto_address' key
            **kwargs: Additional parameters (webhook_url)
        
        Returns:
            PayoutResponse with payout details
        """
        endpoint = "/v1/payout"
        
        data = {
            "withdrawals": [{
                "address": payment_details.get("crypto_address", ""),
                "currency": currency,
                "amount": str(amount),
                "ipn_callback_url": kwargs.get("webhook_url", ""),
                "extra_id": payout_id
            }]
        }
        
        headers = {"x-api-key": self.api_key}
        
        try:
            response = self._make_request("POST", endpoint, data=data, headers=headers)
            
            # NOWpayments returns array of withdrawals
            withdrawals = response.get("withdrawals", [])
            if not withdrawals:
                raise ProviderAPIError(
                    message="No withdrawal data in response",
                    provider=self.code,
                    response_data=response
                )
            
            withdrawal = withdrawals[0]
            
            return PayoutResponse(
                success=True,
                provider_payout_id=str(withdrawal.get("id", "")),
                status=self._map_status(withdrawal.get("status", "")),
                raw_response=response
            )
        except ProviderAPIError as e:
            logger.error(f"NOWpayments create_payout failed: {e}")
            return PayoutResponse(
                success=False,
                provider_payout_id="",
                status="failed",
                error_message=str(e),
                raw_response=e.response_data
            )
        except Exception as e:
            logger.error(f"NOWpayments create_payout unexpected error: {e}")
            return PayoutResponse(
                success=False,
                provider_payout_id="",
                status="failed",
                error_message=str(e)
            )
    
    def check_payout_status(self, provider_payout_id: str) -> StatusResponse:
        """
        Query NOWpayments for payout status.
        
        API Endpoint: GET /v1/payout/{payout_id}
        """
        endpoint = f"/v1/payout/{provider_payout_id}"
        headers = {"x-api-key": self.api_key}
        
        try:
            response = self._make_request("GET", endpoint, headers=headers)
            
            return StatusResponse(
                status=self._map_status(response.get("status", "")),
                provider_status=response.get("status", ""),
                amount_received=Decimal(str(response.get("amount", 0))),
                completed_at=self._parse_datetime(response.get("updated_at"))
            )
        except Exception as e:
            logger.error(f"NOWpayments check_payout_status failed: {e}")
            return StatusResponse(
                status="processing",
                provider_status="unknown",
                error_message=str(e)
            )
    
    def verify_webhook_signature(
        self,
        payload: Dict[str, Any],
        signature: str,
        headers: Dict[str, str]
    ) -> bool:
        """
        Verify NOWpayments webhook signature using HMAC SHA-512.
        
        The signature is computed as HMAC SHA-512 of the JSON payload
        using the webhook secret as the key.
        
        Args:
            payload: Webhook payload data
            signature: Signature from webhook (x-nowpayments-sig header)
            headers: HTTP headers from webhook request
        
        Returns:
            True if signature is valid, False otherwise
        """
        try:
            # Serialize payload to JSON with consistent formatting
            message = json.dumps(payload, separators=(',', ':'), sort_keys=True)
            
            # Compute HMAC SHA-512
            expected = hmac.new(
                self.webhook_secret.encode('utf-8'),
                message.encode('utf-8'),
                hashlib.sha512
            ).hexdigest()
            
            # Use constant-time comparison to prevent timing attacks
            return hmac.compare_digest(signature, expected)
        except Exception as e:
            logger.error(f"NOWpayments signature verification failed: {e}")
            return False
    
    def parse_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse NOWpayments webhook payload into standardized format.
        
        NOWpayments webhook includes:
        - payment_id: Provider's payment identifier
        - order_id: Our internal order identifier
        - payment_status: Current payment status
        - pay_amount: Amount to be paid in crypto
        - actually_paid: Amount actually received (for partial payments)
        - pay_currency: Cryptocurrency used
        
        Returns:
            Dictionary with standardized fields
        """
        return {
            "order_id": payload.get("order_id", ""),
            "provider_order_id": str(payload.get("payment_id", "")),
            "status": self._map_status(payload.get("payment_status", "")),
            "amount": Decimal(str(payload.get("actually_paid", payload.get("pay_amount", 0)))),
            "currency": payload.get("pay_currency", ""),
            "provider_status": payload.get("payment_status", "")
        }
    
    def _map_status(self, provider_status: str) -> str:
        """
        Map NOWpayments-specific status to internal status.
        
        NOWpayments statuses:
        - waiting: Waiting for payment
        - confirming: Payment received, awaiting confirmations
        - confirmed: Payment confirmed
        - sending: Payout being sent
        - partially_paid: Partial payment received
        - finished: Payment completed
        - failed: Payment failed
        - refunded: Payment refunded
        - expired: Payment expired
        """
        mapping = {
            "waiting": "pending",
            "confirming": "processing",
            "confirmed": "completed",
            "sending": "processing",
            "partially_paid": "processing",
            "finished": "completed",
            "failed": "failed",
            "refunded": "refunded",
            "expired": "expired"
        }
        return mapping.get(provider_status.lower(), "pending")
    
    def _parse_datetime(self, datetime_str: str) -> datetime:
        """
        Parse datetime string from NOWpayments API response.
        
        NOWpayments typically returns ISO 8601 format timestamps.
        """
        if not datetime_str:
            return None
        
        try:
            # Try ISO format first
            return datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            try:
                # Try parsing as timestamp
                return datetime.fromtimestamp(float(datetime_str), tz=timezone.utc)
            except (ValueError, TypeError):
                return None
