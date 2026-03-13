from django.shortcuts import render
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from django.db import models

from apps.accounts.models import AdminActionLog
from apps.wallet.models import Transaction, WithdrawalRequest
from apps.dashboard.decorators import require_permission


@require_permission('finance', 'view_transactions')
def finance_overview(request):
    """Finance overview dashboard"""
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Today's metrics
    today_stats = Transaction.objects.filter(
        status="completed",
        created_at__gte=today_start,
        type__in=["deposit", "withdrawal"],
    ).aggregate(
        deposits_total=models.Sum("amount_usd", filter=models.Q(type="deposit")),
        deposits_count=models.Count("id", filter=models.Q(type="deposit")),
        withdrawals_total=models.Sum("amount_usd", filter=models.Q(type="withdrawal")),
        withdrawals_count=models.Count("id", filter=models.Q(type="withdrawal")),
    )
    deposits_total = today_stats["deposits_total"] or Decimal("0")
    withdrawals_total = today_stats["withdrawals_total"] or Decimal("0")
    net_flow = deposits_total - withdrawals_total
    
    # Pending withdrawals
    pending = WithdrawalRequest.objects.filter(
        status__in=["pending", "manual_review", "auto_approved", "approved", "processing"]
    ).aggregate(
        count=models.Count("id"),
        total=models.Sum(
            models.ExpressionWrapper(
                models.F("amount") * models.F("currency__rate_to_usd"),
                output_field=models.DecimalField(max_digits=18, decimal_places=2),
            )
        ),
    )
    pending_withdrawals_count = pending["count"] or 0
    pending_withdrawals_amount = pending["total"] or Decimal("0")
    
    context = {
        'deposits_today': deposits_total,
        'deposits_count': today_stats["deposits_count"] or 0,
        'withdrawals_today': withdrawals_total,
        'withdrawals_count': today_stats["withdrawals_count"] or 0,
        'net_flow': net_flow,
        'pending_withdrawals_count': pending_withdrawals_count,
        'pending_withdrawals_amount': pending_withdrawals_amount,
    }
    
    return render(request, 'dashboard/finance/overview.html', context)


@require_permission('finance', 'view_transactions')
def withdrawals_queue(request):
    """Withdrawal approval queue"""
    withdrawals = WithdrawalRequest.objects.filter(
        status__in=["pending", "manual_review"]
    ).select_related("user", "currency").annotate(
        amount_usd=models.ExpressionWrapper(
            models.F("amount") * models.F("currency__rate_to_usd"),
            output_field=models.DecimalField(max_digits=18, decimal_places=2),
        )
    ).order_by("created_at")
    
    context = {
        'withdrawals': withdrawals,
    }
    
    return render(request, 'dashboard/finance/withdrawals.html', context)


@require_permission('finance', 'view_transactions')
def transactions_list(request):
    """All transactions list"""
    transactions = Transaction.objects.all().order_by('-created_at')[:100]  # Limit for performance
    
    context = {
        'transactions': transactions,
    }
    
    return render(request, 'dashboard/finance/transactions.html', context)
