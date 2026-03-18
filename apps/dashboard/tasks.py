from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from apps.accounts.models import AdminActionLog
from apps.dashboard.services.security_service import SecurityService

@shared_task
def cleanup_old_logs():
    """Delete admin action logs older than 90 days."""
    cutoff = timezone.now() - timedelta(days=90)
    deleted_count, _ = AdminActionLog.objects.filter(created_at__lt=cutoff).delete()
    return f"Deleted {deleted_count} old admin action logs."

@shared_task
def perform_security_scan():
    """Run security anomaly detection and log results."""
    anomalies = SecurityService.detect_anomalies()
    for anomaly in anomalies:
        SecurityService.log_security_event(
            event_type=anomaly['type'],
            description=anomaly['description'],
            severity=anomaly['severity'],
            meta=anomaly['meta']
        )
    return f"Security scan complete. Found {len(anomalies)} anomalies."

@shared_task
def generate_daily_admin_report():
    """Summary of admin activity for the last 24h."""
    yesterday = timezone.now() - timedelta(days=1)
    actions_count = AdminActionLog.objects.filter(created_at__gte=yesterday).count()
    # In real world, this would send an email to superadmins
    return f"Daily Admin Report: {actions_count} actions performed in the last 24h."
