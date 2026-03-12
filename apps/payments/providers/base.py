from __future__ import annotations

import logging
import requests
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class ProviderAPIError(Exception):
    """Custom exception for provider API errors."""
    
    def __init__(self, message: str, provider: str = None, status_code: int = None, response_data: Dict = None):
        self.message = message
        self.provider = provider
        self.status_code = status_code
        self.response_data = response_data or {}
        super().__init__(self.message)
    
    def __str__(self):
        return f"ProviderAPIError({self.provider}): {self.message}"


@dataclass
class DepositResponse:
    """Standardized response from provider's create_deposit method."""
    success: bool
    provider_order_id: str
    payment_url: Optional[str] = None
    crypto_address: Optional[str] = None
    crypto_network: Optional[str] = None
    amount: Optional[Decimal] = None
    expires_at: Optional[datetime] = None
    error_message: Optional[str] = None
    raw_response: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PayoutResponse:
    """Standardized response from provider's create_payout method."""
    success: bool
    provider_payout_id: str
    status: str  # 'processing', 'completed', 'failed'
    error_message: Optional[str] = None
    raw_response: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StatusResponse:
    """Standardized response from provider's status check methods."""
    status: str  # Internal status mapping
    provider_status: str
    amount_received: Optional[Decimal] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class BasePaymentProvider(ABC):
    """
    Abstract base class for payment provider implementations.
    
    All payment providers must implement this interface to ensure
    consistent behavior across different payment systems.
    """
    
    def __init__(self, provider_settings: Dict[str, Any]):
        self.provider_settings = provider_settings
        self.code = provider_settings.get("code", "unknown")
        self.api_key = provider_settings.get("api_key")
        self.api_secret = provider_settings.get("api_secret")
        self.merchant_id = provider_settings.get("merchant_id")
        self.webhook_secret = provider_settings.get("webhook_secret")
        self.api_base_url = provider_settings.get("api_base_url", "")
        self.extra_settings = provider_settings.get("extra_settings", {})
        self.timeout = 30  # 30 seconds timeout

    @abstractmethod
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
        Create a deposit order with the provider.
        
        Args:
            order_id: Unique order identifier
            amount: Deposit amount
            currency: Currency code (e.g., 'RUB', 'USD')
            payment_method_code: Provider-specific payment method code
            user_email: User's email address
            success_url: URL to redirect on successful payment
            fail_url: URL to redirect on failed payment
            **kwargs: Additional provider-specific parameters
        
        Returns:
            DepositResponse with payment details
        """
        raise NotImplementedError

    @abstractmethod
    def check_deposit_status(self, provider_order_id: str) -> StatusResponse:
        """
        Query the provider for deposit status.
        
        Args:
            provider_order_id: Provider's order identifier
        
        Returns:
            StatusResponse with current status
        """
        raise NotImplementedError

    @abstractmethod
    def create_payout(
        self,
        payout_id: str,
        amount: Decimal,
        currency: str,
        payment_details: Dict[str, Any],
        **kwargs
    ) -> PayoutResponse:
        """
        Create a payout order with the provider.
        
        Args:
            payout_id: Unique payout identifier
            amount: Payout amount
            currency: Currency code
            payment_details: Payment destination details (card, wallet, etc.)
            **kwargs: Additional provider-specific parameters
        
        Returns:
            PayoutResponse with payout details
        """
        raise NotImplementedError

    @abstractmethod
    def check_payout_status(self, provider_payout_id: str) -> StatusResponse:
        """
        Query the provider for payout status.
        
        Args:
            provider_payout_id: Provider's payout identifier
        
        Returns:
            StatusResponse with current status
        """
        raise NotImplementedError

    @abstractmethod
    def verify_webhook_signature(
        self,
        payload: Dict[str, Any],
        signature: str,
        headers: Dict[str, str]
    ) -> bool:
        """
        Verify webhook signature authenticity.
        
        Args:
            payload: Webhook payload data
            signature: Signature from webhook
            headers: HTTP headers from webhook request
        
        Returns:
            True if signature is valid, False otherwise
        """
        raise NotImplementedError

    @abstractmethod
    def parse_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse webhook payload into standardized format.
        
        Args:
            payload: Raw webhook payload
        
        Returns:
            Dictionary with standardized fields:
            - order_id: Internal order identifier
            - provider_order_id: Provider's order identifier
            - status: Internal status
            - amount: Payment amount
            - currency: Currency code
            - provider_status: Original provider status
        """
        raise NotImplementedError

    def _map_status(self, provider_status: str) -> str:
        """
        Map provider-specific status to internal status.
        
        Internal statuses: created, pending, processing, completed, 
                          failed, expired, cancelled, refunded
        
        Args:
            provider_status: Provider's status string
        
        Returns:
            Internal status string
        """
        # Default mapping - override in subclasses
        mapping = {
            "new": "created",
            "pending": "pending",
            "processing": "processing",
            "success": "completed",
            "completed": "completed",
            "failed": "failed",
            "expired": "expired",
            "cancelled": "cancelled",
            "refunded": "refunded"
        }
        return mapping.get(provider_status.lower(), "pending")

    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Make HTTP request to provider API with error handling.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            data: Request body data
            headers: HTTP headers
            params: URL query parameters
        
        Returns:
            Response data as dictionary
        
        Raises:
            ProviderAPIError: On API errors or timeouts
        """
        url = f"{self.api_base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        headers = headers or {}
        
        start_time = time.time()
        
        try:
            response = requests.request(
                method=method,
                url=url,
                json=data if method in ["POST", "PUT", "PATCH"] else None,
                params=params,
                headers=headers,
                timeout=self.timeout
            )
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Log API call
            self._log_api_call(
                method=method,
                endpoint=endpoint,
                request_data=data or {},
                response_data=response.json() if response.content else {},
                status_code=response.status_code,
                duration_ms=duration_ms
            )
            
            # Check for HTTP errors
            if response.status_code >= 400:
                error_data = response.json() if response.content else {}
                raise ProviderAPIError(
                    message=f"API request failed with status {response.status_code}",
                    provider=self.code,
                    status_code=response.status_code,
                    response_data=error_data
                )
            
            return response.json() if response.content else {}
            
        except requests.Timeout:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(
                f"Provider API timeout after {duration_ms}ms",
                extra={
                    "provider": self.code,
                    "method": method,
                    "endpoint": endpoint,
                    "timeout": self.timeout
                }
            )
            raise ProviderAPIError(
                message=f"API request timed out after {self.timeout} seconds",
                provider=self.code,
                status_code=408
            )
        except requests.RequestException as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(
                f"Provider API request failed: {str(e)}",
                extra={
                    "provider": self.code,
                    "method": method,
                    "endpoint": endpoint,
                    "duration_ms": duration_ms
                }
            )
            raise ProviderAPIError(
                message=f"API request failed: {str(e)}",
                provider=self.code
            )

    def _log_api_call(
        self,
        method: str,
        endpoint: str,
        request_data: Dict,
        response_data: Dict,
        status_code: int,
        duration_ms: int
    ):
        """Log API call details for debugging and monitoring."""
        logger.info(
            "payment api call",
            extra={
                "provider": self.code,
                "method": method,
                "endpoint": endpoint,
                "status_code": status_code,
                "duration_ms": duration_ms,
            },
        )
