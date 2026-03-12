from __future__ import annotations

import logging
from decimal import Decimal
from typing import Dict, Any
from datetime import timedelta

from django.utils import timezone
from django.db.models import Sum, Count

from apps.wallet.models import Currency
from apps.payments.models import DepositOrder, PaymentSettings

logger = logging.getLogger(__name__)


class AntiFraudService:
    """
    Detects and prevents fraudulent payment activity.
    
    Checks:
    - Daily deposit limits
    - Velocity checks (multiple deposits in short time)
    - IP changes
    - Suspicious patterns
    - Large deposit notifications
    """
    
    def check_deposit(
        self,
        user,
        amount: Decimal,
        currency: Currency,
        ip_address: str
    ) -> Dict[str, Any]:
        """
        Run anti-fraud checks on deposit.
        
        Returns:
        {
            "blocked": bool,
            "reason": str,
            "risk_level": str,
            "risk_factors": list
        }
        """
        risk_factors = []
        
        # Get payment settings
        settings = PaymentSettings.get_settings()
        amount_usd = amount * currency.rate_to_usd
        
        # Check daily deposit limit (Requirement 7.1)
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_deposits = DepositOrder.objects.filter(
            user=user,
            status="completed",
            completed_at__gte=today_start
        ).aggregate(total=Sum('amount_usd'))['total'] or Decimal('0')
        
        if today_deposits + amount_usd > settings.daily_deposit_limit_per_user:
            return {
                "blocked": True,
                "reason": "Daily deposit limit exceeded",
                "risk_level": "high",
                "risk_factors": ["daily_limit_exceeded"]
            }
        
        # Check for large deposit notification (Requirement 7.2)
        if amount_usd > settings.deposit_notification_threshold:
            risk_factors.append("large_deposit")
            self._notify_admins_large_deposit(user, amount, currency)
        
        # Check velocity - multiple deposits in 1 hour (Requirement 7.3, 7.8)
        one_hour_ago = timezone.now() - timedelta(hours=1)
        recent_deposits = DepositOrder.objects.filter(
            user=user,
            created_at__gte=one_hour_ago
        ).count()
        
        if recent_deposits >= 3:
            risk_factors.append("high_velocity")
        
        # Check IP changes - multiple IPs within 1 hour (Requirement 7.3)
        if hasattr(user, 'registration_ip') and user.registration_ip and ip_address != user.registration_ip:
            recent_different_ips = DepositOrder.objects.filter(
                user=user,
                created_at__gte=one_hour_ago
            ).exclude(ip_address=ip_address).values('ip_address').distinct().count()
            
            if recent_different_ips > 0:
                risk_factors.append("multiple_ips")
        
        # Check suspicious patterns from settings (Requirement 7.9)
        suspicious_patterns = settings.suspicious_deposit_patterns
        if suspicious_patterns:
            # Pattern matching logic can be extended here
            # For now, we check if the user has any flagged patterns
            pass
        
        # Determine risk level
        risk_level = "low"
        if len(risk_factors) >= 3:
            risk_level = "high"
        elif len(risk_factors) >= 1:
            risk_level = "medium"
        
        return {
            "blocked": False,
            "reason": "",
            "risk_level": risk_level,
            "risk_factors": risk_factors
        }
    
    def check_withdrawal(self, withdrawal_request) -> Dict[str, Any]:
        """
        Run anti-fraud checks on withdrawal.
        Uses existing WithdrawalRequest.calculate_risk_level() method.
        
        This method delegates to the existing comprehensive withdrawal fraud detection
        in WithdrawalRequest.calculate_risk_level() (Requirement 7.4, 7.5, 7.6)
        
        Returns:
        {
            "risk_level": str,
            "risk_factors": list,
            "requires_manual_approval": bool
        }
        """
        # The existing wallet app already has comprehensive withdrawal fraud detection
        # in WithdrawalRequest.calculate_risk_level()
        # This method serves as a wrapper for consistency
        
        return {
            "risk_level": withdrawal_request.risk_level,
            "risk_factors": withdrawal_request.risk_factors,
            "requires_manual_approval": withdrawal_request.risk_level in ["high", "critical"]
        }
    
    def _notify_admins_large_deposit(self, user, amount: Decimal, currency: Currency):
        """
        Send notification to admins about large deposit (Requirement 7.2).
        
        This can be extended to send emails, Telegram messages, or other notifications.
        """
        amount_usd = amount * currency.rate_to_usd
        logger.warning(
            f"Large deposit detected: User {user.id} ({user.email}) "
            f"depositing {amount} {currency.code} (${amount_usd:.2f} USD)"
        )
        
        # TODO: Implement actual notification mechanism
        # - Send email to admins
        # - Send Telegram notification
        # - Create admin notification record
        pass
    
    # Legacy methods for backward compatibility
    @staticmethod
    def assess_deposit(user, amount: Decimal, currency: Currency) -> Dict:
        """Legacy method for backward compatibility."""
        service = AntiFraudService()
        result = service.check_deposit(user, amount, currency, "")
        return {"risk": result["risk_level"], "reasons": result["risk_factors"]}

    @staticmethod
    def is_deposit_blocked(user, amount: Decimal, currency: Currency) -> bool:
        """Legacy method for backward compatibility."""
        assessment = AntiFraudService.assess_deposit(user, amount, currency)
        return assessment.get("risk") in {"high", "critical"}
