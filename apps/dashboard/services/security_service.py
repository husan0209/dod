import logging
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, Sum
from apps.accounts.models import AdminActionLog, User, LoginHistory
from apps.wallet.models import WithdrawalRequest

logger = logging.getLogger(__name__)

class SecurityService:
    """Service for anomaly detection and security monitoring."""

    @staticmethod
    def detect_anomalies():
        """Scan for suspicious patterns in the last 24 hours."""
        now = timezone.now()
        since = now - timedelta(hours=24)
        anomalies = []

        # 1. Multiple failed logins from same IP
        failed_logins = LoginHistory.objects.filter(
            created_at__gte=since,
            is_successful=False
        ).values('ip_address').annotate(count=Count('id')).filter(count__gte=10)
        
        for item in failed_logins:
            anomalies.append({
                'type': 'brute_force_attempt',
                'severity': 'high',
                'description': f"10+ failed logins from IP {item['ip_address']}",
                'meta': {'ip': item['ip_address'], 'count': item['count']}
            })

        # 2. Large withdrawal bursts
        large_withdrawals = WithdrawalRequest.objects.filter(
            created_at__gte=since,
            amount_usd__gte=5000 # Threshold $5k
        ).count()
        
        if large_withdrawals >= 3:
            anomalies.append({
                'type': 'withdrawal_burst',
                'severity': 'critical',
                'description': f"{large_withdrawals} large withdrawals ($5000+) in 24h",
                'meta': {'count': large_withdrawals}
            })

        # 3. Multiple Admin 2FA failures
        admin_failures = AdminActionLog.objects.filter(
            created_at__gte=since,
            action_type='admin_2fa_failed'
        ).values('admin_user__username').annotate(count=Count('id')).filter(count__gte=3)

        for item in admin_failures:
            anomalies.append({
                'type': 'admin_compromise_attempt',
                'severity': 'critical',
                'description': f"3+ 2FA failures for admin {item['admin_user__username']}",
                'meta': {'user': item['admin_user__username'], 'count': item['count']}
            })

        return anomalies

    @staticmethod
    def log_security_event(event_type, description, severity='medium', meta=None):
        """Log a dedicated security event for audit."""
        logger.warning(f"SECURITY EVENT [{severity.upper()}]: {event_type} - {description}")
        # Could also send to Telegram/Email here
