from django.shortcuts import render
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from django.db import models

from apps.accounts.models import AdminActionLog
from apps.wallet.models import Transaction
from apps.dashboard.decorators import require_permission

# Try to import optional models
try:
    from apps.payments.models import Withdrawal
except ImportError:
    Withdrawal = None


@require_permission('finance', 'view_transactions')
def finance_overview(request):
    """Finance overview dashboard"""
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Today's metrics
    deposits_today = Transaction.objects.filter(
        type='deposit',
        status='completed',
        created_at__gte=today_start
    ).aggregate(
        total=models.Sum('amount_usd'),
        count=models.Count('id')
    )
    
    withdrawals_today = Transaction.objects.filter(
        type='withdrawal',
        status='completed',
        created_at__gte=today_start
    ).aggregate(
        total=models.Sum('amount_usd'),
        count=models.Count('id')
    )
    
    net_flow = (deposits_today['total'] or Decimal('0')) - (withdrawals_today['total'] or Decimal('0'))
    
    # Pending withdrawals
    pending_withdrawals_count = 0
    pending_withdrawals_amount = Decimal('0')
    if Withdrawal:
        pending = Withdrawal.objects.filter(status='pending').aggregate(
            count=models.Count('id'),
            total=models.Sum('amount_usd')
        )
        pending_withdrawals_count = pending['count'] or 0
        pending_withdrawals_amount = pending['total'] or Decimal('0')
    
    context = {
        'deposits_today': deposits_today['total'] or Decimal('0'),
        'deposits_count': deposits_today['count'] or 0,
        'withdrawals_today': withdrawals_today['total'] or Decimal('0'),
        'withdrawals_count': withdrawals_today['count'] or 0,
        'net_flow': net_flow,
        'pending_withdrawals_count': pending_withdrawals_count,
        'pending_withdrawals_amount': pending_withdrawals_amount,
    }
    
    return render(request, 'dashboard/finance/overview.html', context)


@require_permission('finance', 'view_transactions')
def withdrawals_queue(request):
    """Withdrawal approval queue"""
    if not Withdrawal:
        context = {'withdrawals': [], 'error': 'Withdrawal model not available'}
        return render(request, 'dashboard/finance/withdrawals.html', context)
    
    withdrawals = Withdrawal.objects.filter(status='pending').order_by('created_at')
    
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
