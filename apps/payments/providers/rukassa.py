from __future__ import annotations

import hashlib
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


class RUkassaProvider(BasePaymentProvider):
    """
    RUkassa API Integration
    
    API Documentation: https://rukassa.is/api-documentation
    
    Supported Methods:
    - bank_card: Visa, MasterCard, МИР
    - sbp: Fast Payment System
    - qiwi: QIWI Wallet
    - yoomoney: ЮMoney
    - mobile: Mobile payments
    
    Webhook Signature: MD5(shop_id:order_id:amount:status:secret)
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
        Create a deposit order with RUkassa.
        
        API Endpoint: POST /api/v1/create
        """
        endpoint = "/api/v1/create"
        
        # Generate signature for request
        signature = self._generate_signature(order_id, amount, currency)
        
        data = {
            "shop_id": self.merchant_id,
            "order_id": order_id,
            "amount": str(amount),
            "currency": currency,
            "method": payment_method_code,
            "email": user_email,
            "success_url": success_url,
            "fail_url": fail_url,
            "sign": signature
        }
        
        try:
            response = self._make_request("POST", endpoint, data=data)
            
            return DepositResponse(
                success=True,
                provider_order_id=response.get("payment_id", ""),
                payment_url=response.get("payment_url", ""),
                expires_at=timezone.now() + timedelta(minutes=30),
                raw_response=response
            )
        except ProviderAPIError as e:
            logger.error(f"RUkassa create_deposit failed: {e}")
            return DepositResponse(
                success=False,
                provider_order_id="",
                error_message=str(e),
                raw_response=e.response_data
            )
        except Exception as e:
            logger.error(f"RUkassa create_deposit unexpected error: {e}")
            return DepositResponse(
                success=False,
                provider_order_id="",
                error_message=str(e)
            )
    
    def check_deposit_status(self, provider_order_id: str) -> StatusResponse:
        """
        Query RUkassa for deposit status.
        
        API Endpoint: GET /api/v1/status/{payment_id}
        """
        endpoint = f"/api/v1/status/{provider_order_id}"
        
        try:
            response = self._make_request("GET", endpoint)
            
            return StatusResponse(
                status=self._map_status(response.get("status", "")),
                provider_status=response.get("status", ""),
                amount_received=Decimal(str(response.get("amount_received", 0))),
                completed_at=self._parse_datetime(response.get("completed_at"))
            )
        except Exception as e:
            logger.error(f"RUkassa check_deposit_status failed: {e}")
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
        Create a payout order with RUkassa.
        
        API Endpoint: POST /api/v1/payout
        """
        endpoint = "/api/v1/payout"
        
        # Generate signature for payout request
        signature = self._generate_payout_signature(payout_id, amount, currency)
        
        data = {
            "shop_id": self.merchant_id,
            "payout_id": payout_id,
            "amount": str(amount),
            "currency": currency,
            "method": payment_details.get("method", ""),
            "account": payment_details.get("account", ""),
            "sign": signature
        }
        
        try:
            response = self._make_request("POST", endpoint, data=data)
            
            return PayoutResponse(
                success=response.get("success", False),
                provider_payout_id=response.get("payout_id", ""),
                status=self._map_status(response.get("status", "")),
                raw_response=response
            )
        except ProviderAPIError as e:
            logger.error(f"RUkassa create_payout failed: {e}")
            return PayoutResponse(
                success=False,
                provider_payout_id="",
                status="failed",
                error_message=str(e),
                raw_response=e.response_data
            )
        except Exception as e:
            logger.error(f"RUkassa create_payout unexpected error: {e}")
            return PayoutResponse(
                success=False,
                provider_payout_id="",
                status="failed",
                error_message=str(e)
            )
    
    def check_payout_status(self, provider_payout_id: str) -> StatusResponse:
        """
        Query RUkassa for payout status.
        
        API Endpoint: GET /api/v1/payout/status/{payout_id}
        """
        endpoint = f"/api/v1/payout/status/{provider_payout_id}"
        
        try:
            response = self._make_request("GET", endpoint)
            
            return StatusResponse(
                status=self._map_status(response.get("status", "")),
                provider_status=response.get("status", ""),
                amount_received=Decimal(str(response.get("amount", 0))),
                completed_at=self._parse_datetime(response.get("completed_at"))
            )
        except Exception as e:
            logger.error(f"RUkassa check_payout_status failed: {e}")
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
        Verify RUkassa webhook signature using MD5.
        
        Signature format: MD5(shop_id:order_id:amount:status:secret)
        """
        try:
            expected = self._generate_webhook_signature(
                shop_id=payload.get("shop_id", ""),
                order_id=payload.get("order_id", ""),
                amount=str(payload.get("amount", "")),
                status=payload.get("status", "")
            )
            return signature == expected
        except Exception as e:
            logger.error(f"RUkassa signature verification failed: {e}")
            return False
    
    def parse_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse RUkassa webhook payload into standardized format.
        """
        return {
            "order_id": payload.get("order_id", ""),
            "provider_order_id": payload.get("payment_id", ""),
            "status": self._map_status(payload.get("status", "")),
            "amount": Decimal(str(payload.get("amount", 0))),
            "currency": payload.get("currency", ""),
            "provider_status": payload.get("status", "")
        }
    
    def _map_status(self, provider_status: str) -> str:
        """
        Map RUkassa-specific status to internal status.
        
        RUkassa statuses:
        - new: Order created
        - pending: Awaiting payment
        - processing: Payment being processed
        - success: Payment completed
        - failed: Payment failed
        - expired: Order expired
        - cancelled: Order cancelled
        """
        mapping = {
            "new": "created",
            "pending": "pending",
            "processing": "processing",
            "success": "completed",
            "failed": "failed",
            "expired": "expired",
            "cancelled": "cancelled",
            "wait": "pending",  # Alternative status
            "paid": "completed",  # Alternative status
            "cancel": "cancelled",  # Alternative status
            "fail": "failed"  # Alternative status
        }
        return mapping.get(provider_status.lower(), "pending")
    
    def _generate_signature(self, order_id: str, amount: Decimal, currency: str) -> str:
        """
        Generate signature for deposit creation request.
        
        Format: MD5(merchant_id:order_id:amount:currency:secret)
        """
        string = f"{self.merchant_id}:{order_id}:{amount}:{currency}:{self.webhook_secret}"
        return hashlib.md5(string.encode()).hexdigest()
    
    def _generate_payout_signature(self, payout_id: str, amount: Decimal, currency: str) -> str:
        """
        Generate signature for payout creation request.
        
        Format: MD5(merchant_id:payout_id:amount:currency:secret)
        """
        string = f"{self.merchant_id}:{payout_id}:{amount}:{currency}:{self.webhook_secret}"
        return hashlib.md5(string.encode()).hexdigest()
    
    def _generate_webhook_signature(
        self,
        shop_id: str,
        order_id: str,
        amount: str,
        status: str
    ) -> str:
        """
        Generate expected webhook signature for verification.
        
        Format: MD5(shop_id:order_id:amount:status:secret)
        """
        string = f"{shop_id}:{order_id}:{amount}:{status}:{self.webhook_secret}"
        return hashlib.md5(string.encode()).hexdigest()
    
    def _parse_datetime(self, datetime_str: str) -> datetime:
        """Parse datetime string from RUkassa API response."""
        if not datetime_str:
            return None
        
        try:
            # Try ISO format first
            return datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            return None
