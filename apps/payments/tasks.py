"""
Celery background tasks for payment system.

This module contains all background tasks for:
- Checking pending deposits and payouts
- Expiring old deposits
- Retrying failed payouts
- Generating reports
- Provider health checks
- Reconciliation
- Cleanup operations
"""

import logging
from datetime import timedelta
from decimal import Decimal
from typing import Dict, Any

from celery import shared_task
from django.db.models import Sum, Count, Q
from django.utils import timezone

from apps.payments.models import (
    DepositOrder,
    PayoutOrder,
    WebhookLog,
    PaymentProvider,
    PaymentSettings,
)
from apps.payments.services.payment_service import PaymentService
from apps.payments.services.payout_service import PayoutService
from apps.payments.providers import get_provider_instance

logger = logging.getLogger(__name__)


@shared_task(name='apps.payments.tasks.check_pending_deposits')
def check_pending_deposits():
    """
    Check status of pending deposits.
    
    This task queries provider APIs for status updates on deposits
    that are still pending. This serves as a backup mechanism in case
    webhooks fail or are delayed.
    
    Schedule: Every 5 minutes
    Requirements: 9.1
    """
    try:
        logger.info("Starting check_pending_deposits task")
        PaymentService.check_pending_deposits()
        logger.info("Completed check_pending_deposits task")
    except Exception as e:
        logger.error(f"Error in check_pending_deposits task: {e}", exc_info=True)
        raise


@shared_task(name='apps.payments.tasks.check_pending_payouts')
def check_pending_payouts():
    """
    Check status of pending payouts.
    
    This task queries provider APIs for status updates on payouts
    that are still processing. This serves as a backup mechanism in case
    webhooks fail or are delayed.
    
    Schedule: Every 5 minutes
    Requirements: 9.2
    """
    try:
        logger.info("Starting check_pending_payouts task")
        
        pending_payouts = PayoutOrder.objects.filter(
            status__in=["pending", "processing"]
        ).select_related('provider', 'currency', 'withdrawal_request')
        
        logger.info(f"Checking {pending_payouts.count()} pending payouts")
        
        for payout in pending_payouts:
            try:
                provider_instance = get_provider_instance(payout.provider)
                status_response = provider_instance.check_payout_status(payout.provider_payout_id)
                
                if status_response.status == "completed":
                    # Process as if webhook arrived
                    PayoutService.process_webhook_confirmation(
                        payout.provider.code,
                        {
                            "payout_id": payout.payout_id,
                            "status": "completed",
                            "provider_status": status_response.provider_status,
                        }
                    )
                    logger.info(f"Payout {payout.payout_id} completed via status check")
                elif status_response.status in ["failed", "cancelled"]:
                    payout.status = status_response.status
                    payout.provider_status = status_response.provider_status
                    payout.error_message = status_response.error_message or ""
                    payout.save(update_fields=["status", "provider_status", "error_message", "updated_at"])
                    logger.info(f"Payout {payout.payout_id} marked as {status_response.status}")
                    
            except Exception as e:
                logger.error(f"Error checking payout {payout.payout_id}: {e}", exc_info=True)
        
        logger.info("Completed check_pending_payouts task")
    except Exception as e:
        logger.error(f"Error in check_pending_payouts task: {e}", exc_info=True)
        raise


@shared_task(name='apps.payments.tasks.expire_old_deposits')
def expire_old_deposits():
    """
    Expire deposits that haven't been paid within the expiration window.
    
    Deposits have a 30-minute expiration window (60 minutes for crypto).
    This task marks expired deposits so they don't remain in pending state forever.
    
    Schedule: Every 10 minutes
    Requirements: 9.3
    """
    try:
        logger.info("Starting expire_old_deposits task")
        PaymentService.expire_old_deposits()
        logger.info("Completed expire_old_deposits task")
    except Exception as e:
        logger.error(f"Error in expire_old_deposits task: {e}", exc_info=True)
        raise


@shared_task(name='apps.payments.tasks.retry_failed_payouts')
def retry_failed_payouts():
    """
    Retry failed payouts with exponential backoff.
    
    Payouts can fail due to temporary provider issues. This task
    retries failed payouts up to max_retries times with increasing
    delays (1 min, 5 min, 15 min).
    
    Schedule: Every minute
    Requirements: 9.4
    """
    try:
        logger.info("Starting retry_failed_payouts task")
        PayoutService.retry_failed_payouts()
        logger.info("Completed retry_failed_payouts task")
    except Exception as e:
        logger.error(f"Error in retry_failed_payouts task: {e}", exc_info=True)
        raise


@shared_task(name='apps.payments.tasks.generate_daily_reports')
def generate_daily_reports():
    """
    Generate daily payment reports.
    
    Creates comprehensive reports with:
    - Total deposits and withdrawals
    - Fees collected
    - Provider breakdown
    - Success rates
    - Average processing times
    
    Schedule: Daily at 00:05
    Requirements: 9.5
    """
    try:
        logger.info("Starting generate_daily_reports task")
        
        # Calculate date range for yesterday
        today = timezone.now().date()
        yesterday = today - timedelta(days=1)
        start_time = timezone.make_aware(timezone.datetime.combine(yesterday, timezone.datetime.min.time()))
        end_time = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()))
        
        # Aggregate deposit statistics
        deposit_stats = DepositOrder.objects.filter(
            created_at__gte=start_time,
            created_at__lt=end_time
        ).aggregate(
            total_count=Count('id'),
            completed_count=Count('id', filter=Q(status='completed')),
            total_amount=Sum('amount_usd', filter=Q(status='completed')),
            total_fees=Sum('fee_amount', filter=Q(status='completed')),
        )
        
        # Aggregate payout statistics
        payout_stats = PayoutOrder.objects.filter(
            created_at__gte=start_time,
            created_at__lt=end_time
        ).aggregate(
            total_count=Count('id'),
            completed_count=Count('id', filter=Q(status='completed')),
            total_amount=Sum('amount', filter=Q(status='completed')),
            total_fees=Sum('fee_amount', filter=Q(status='completed')),
        )
        
        # Provider breakdown
        provider_breakdown = {}
        for provider in PaymentProvider.objects.filter(is_active=True):
            provider_deposits = DepositOrder.objects.filter(
                provider=provider,
                created_at__gte=start_time,
                created_at__lt=end_time,
                status='completed'
            ).aggregate(
                count=Count('id'),
                amount=Sum('amount_usd')
            )
            
            provider_payouts = PayoutOrder.objects.filter(
                provider=provider,
                created_at__gte=start_time,
                created_at__lt=end_time,
                status='completed'
            ).aggregate(
                count=Count('id'),
                amount=Sum('amount')
            )
            
            provider_breakdown[provider.code] = {
                'deposits': provider_deposits,
                'payouts': provider_payouts,
            }
        
        # Calculate success rates
        deposit_success_rate = 0
        if deposit_stats['total_count'] > 0:
            deposit_success_rate = (deposit_stats['completed_count'] / deposit_stats['total_count']) * 100
        
        payout_success_rate = 0
        if payout_stats['total_count'] > 0:
            payout_success_rate = (payout_stats['completed_count'] / payout_stats['total_count']) * 100
        
        # Build report
        report = {
            'date': yesterday.isoformat(),
            'deposits': {
                'total_count': deposit_stats['total_count'],
                'completed_count': deposit_stats['completed_count'],
                'total_amount_usd': float(deposit_stats['total_amount'] or 0),
                'total_fees_usd': float(deposit_stats['total_fees'] or 0),
                'success_rate': round(deposit_success_rate, 2),
            },
            'payouts': {
                'total_count': payout_stats['total_count'],
                'completed_count': payout_stats['completed_count'],
                'total_amount_usd': float(payout_stats['total_amount'] or 0),
                'total_fees_usd': float(payout_stats['total_fees'] or 0),
                'success_rate': round(payout_success_rate, 2),
            },
            'provider_breakdown': provider_breakdown,
            'net_revenue': float((deposit_stats['total_fees'] or 0) + (payout_stats['total_fees'] or 0)),
        }
        
        logger.info(f"Daily report generated: {report}")
        
        # TODO: Store report in database or send to administrators
        # For now, just log it
        
        logger.info("Completed generate_daily_reports task")
        return report
        
    except Exception as e:
        logger.error(f"Error in generate_daily_reports task: {e}", exc_info=True)
        raise


@shared_task(name='apps.payments.tasks.provider_health_checks')
def provider_health_checks():
    """
    Perform health checks on payment providers.
    
    Checks each provider's API status endpoint to ensure they are operational.
    If a provider fails health check, it is disabled and administrators are notified.
    
    Schedule: Every 15 minutes
    Requirements: 9.6, 9.7
    """
    try:
        logger.info("Starting provider_health_checks task")
        
        providers = PaymentProvider.objects.filter(is_active=True)
        
        for provider in providers:
            try:
                provider_instance = get_provider_instance(provider)
                
                # Attempt a simple API call to check health
                # Most providers have a status or ping endpoint
                # For now, we'll use a simple timeout check on their base URL
                import requests
                response = requests.get(
                    provider.api_base_url,
                    timeout=10,
                    headers={'User-Agent': 'DOD-HealthCheck/1.0'}
                )
                
                if response.status_code >= 500:
                    # Server error - provider might be down
                    logger.warning(
                        f"Provider {provider.code} health check failed: "
                        f"HTTP {response.status_code}"
                    )
                    
                    # Disable provider
                    provider.is_active = False
                    provider.save(update_fields=['is_active', 'updated_at'])
                    
                    # TODO: Notify administrators
                    logger.critical(
                        f"ADMIN ALERT: Provider {provider.code} disabled due to health check failure"
                    )
                else:
                    logger.info(f"Provider {provider.code} health check passed")
                    
            except requests.Timeout:
                logger.warning(f"Provider {provider.code} health check timed out")
                # Don't disable on timeout - might be temporary
            except Exception as e:
                logger.error(
                    f"Error checking health for provider {provider.code}: {e}",
                    exc_info=True
                )
        
        logger.info("Completed provider_health_checks task")
        
    except Exception as e:
        logger.error(f"Error in provider_health_checks task: {e}", exc_info=True)
        raise


@shared_task(name='apps.payments.tasks.reconciliation_check')
def reconciliation_check():
    """
    Perform daily reconciliation of payment records.
    
    Compares internal records with provider transaction reports to identify
    discrepancies. Any mismatches are flagged for manual review.
    
    Schedule: Daily at 02:00
    Requirements: 9.8, 9.9
    """
    try:
        logger.info("Starting reconciliation_check task")
        
        # Calculate date range for yesterday
        today = timezone.now().date()
        yesterday = today - timedelta(days=1)
        start_time = timezone.make_aware(timezone.datetime.combine(yesterday, timezone.datetime.min.time()))
        end_time = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()))
        
        discrepancies = []
        
        # Check deposits
        deposits = DepositOrder.objects.filter(
            completed_at__gte=start_time,
            completed_at__lt=end_time,
            status='completed'
        ).select_related('provider')
        
        for deposit in deposits:
            try:
                # Query provider for this transaction
                provider_instance = get_provider_instance(deposit.provider)
                status_response = provider_instance.check_deposit_status(deposit.provider_order_id)
                
                # Compare amounts
                if status_response.amount_received and status_response.amount_received != deposit.amount_received:
                    discrepancy = {
                        'type': 'deposit',
                        'order_id': deposit.order_id,
                        'provider_order_id': deposit.provider_order_id,
                        'internal_amount': float(deposit.amount_received),
                        'provider_amount': float(status_response.amount_received),
                        'difference': float(deposit.amount_received - status_response.amount_received),
                    }
                    discrepancies.append(discrepancy)
                    logger.warning(f"Reconciliation discrepancy found: {discrepancy}")
                    
            except Exception as e:
                logger.error(
                    f"Error reconciling deposit {deposit.order_id}: {e}",
                    exc_info=True
                )
        
        # Check payouts
        payouts = PayoutOrder.objects.filter(
            completed_at__gte=start_time,
            completed_at__lt=end_time,
            status='completed'
        ).select_related('provider')
        
        for payout in payouts:
            try:
                # Query provider for this transaction
                provider_instance = get_provider_instance(payout.provider)
                status_response = provider_instance.check_payout_status(payout.provider_payout_id)
                
                # Verify status matches
                if status_response.status != 'completed':
                    discrepancy = {
                        'type': 'payout',
                        'payout_id': payout.payout_id,
                        'provider_payout_id': payout.provider_payout_id,
                        'internal_status': payout.status,
                        'provider_status': status_response.status,
                    }
                    discrepancies.append(discrepancy)
                    logger.warning(f"Reconciliation discrepancy found: {discrepancy}")
                    
            except Exception as e:
                logger.error(
                    f"Error reconciling payout {payout.payout_id}: {e}",
                    exc_info=True
                )
        
        if discrepancies:
            logger.critical(
                f"ADMIN ALERT: {len(discrepancies)} reconciliation discrepancies found. "
                f"Manual review required."
            )
            # TODO: Send detailed report to administrators
        else:
            logger.info("Reconciliation check completed - no discrepancies found")
        
        logger.info("Completed reconciliation_check task")
        return {
            'date': yesterday.isoformat(),
            'discrepancies_count': len(discrepancies),
            'discrepancies': discrepancies,
        }
        
    except Exception as e:
        logger.error(f"Error in reconciliation_check task: {e}", exc_info=True)
        raise


@shared_task(name='apps.payments.tasks.cleanup_old_webhook_logs')
def cleanup_old_webhook_logs():
    """
    Clean up old webhook logs.
    
    Deletes webhook logs older than 90 days to prevent database bloat.
    Logs are deleted in batches to avoid long-running transactions.
    
    Schedule: Daily at 03:00
    Requirements: 9.10
    """
    try:
        logger.info("Starting cleanup_old_webhook_logs task")
        
        # Calculate cutoff date (90 days ago)
        cutoff_date = timezone.now() - timedelta(days=90)
        
        # Delete in batches of 1000 to avoid long transactions
        batch_size = 1000
        total_deleted = 0
        
        while True:
            # Get IDs of logs to delete
            old_logs = WebhookLog.objects.filter(
                created_at__lt=cutoff_date
            ).values_list('id', flat=True)[:batch_size]
            
            old_log_ids = list(old_logs)
            
            if not old_log_ids:
                break
            
            # Delete batch
            deleted_count = WebhookLog.objects.filter(id__in=old_log_ids).delete()[0]
            total_deleted += deleted_count
            
            logger.info(f"Deleted {deleted_count} webhook logs (total: {total_deleted})")
            
            # Small delay between batches
            import time
            time.sleep(0.1)
        
        logger.info(f"Completed cleanup_old_webhook_logs task - deleted {total_deleted} logs")
        return {'deleted_count': total_deleted}
        
    except Exception as e:
        logger.error(f"Error in cleanup_old_webhook_logs task: {e}", exc_info=True)
        raise
