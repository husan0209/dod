import csv
from datetime import timedelta
from decimal import Decimal

from django.contrib import messages
from django.core.paginator import Paginator
from django.db import models, transaction as db_transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.accounts.models import AdminActionLog
from apps.dashboard.decorators import require_permission
from apps.wallet.models import Transaction, WithdrawalRequest, WalletBalance


@require_permission('finance', 'view_transactions')
def finance_overview(request):
    """Finance overview dashboard with real metrics."""
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = today_start - timedelta(days=1)

    # Today's metrics
    today_stats = Transaction.objects.filter(
        status="completed",
        created_at__gte=today_start,
    ).aggregate(
        deposits_total=models.Sum("amount_usd", filter=models.Q(type="deposit")),
        deposits_count=models.Count("id", filter=models.Q(type="deposit")),
        withdrawals_total=models.Sum("amount_usd", filter=models.Q(type="withdrawal")),
        withdrawals_count=models.Count("id", filter=models.Q(type="withdrawal")),
        bets_total=models.Sum("amount_usd", filter=models.Q(type="bet")),
        wins_total=models.Sum("amount_usd", filter=models.Q(type="win")),
        fees_total=models.Sum("amount_usd", filter=models.Q(type="fee")),
    )

    deposits_total = today_stats["deposits_total"] or Decimal("0")
    withdrawals_total = today_stats["withdrawals_total"] or Decimal("0")
    bets_total = today_stats["bets_total"] or Decimal("0")
    wins_total = today_stats["wins_total"] or Decimal("0")
    fees_total = today_stats["fees_total"] or Decimal("0")
    net_flow = deposits_total - withdrawals_total
    ggr = bets_total - wins_total

    # Yesterday comparison
    yesterday_stats = Transaction.objects.filter(
        status="completed",
        created_at__gte=yesterday_start,
        created_at__lt=today_start,
    ).aggregate(
        deposits_total=models.Sum("amount_usd", filter=models.Q(type="deposit")),
        withdrawals_total=models.Sum("amount_usd", filter=models.Q(type="withdrawal")),
    )
    yesterday_deposits = yesterday_stats["deposits_total"] or Decimal("0")
    yesterday_withdrawals = yesterday_stats["withdrawals_total"] or Decimal("0")

    deposits_change = _calc_change(deposits_total, yesterday_deposits)
    withdrawals_change = _calc_change(withdrawals_total, yesterday_withdrawals)

    # Pending withdrawals
    pending_qs = WithdrawalRequest.objects.filter(
        status__in=["pending", "manual_review"]
    )
    pending_withdrawals_count = pending_qs.count()
    pending_withdrawals_amount = pending_qs.aggregate(
        total=models.Sum("amount")
    )["total"] or Decimal("0")

    # Suspicious (high/critical risk) withdrawals
    suspicious_count = pending_qs.filter(
        risk_level__in=["high", "critical"]
    ).count()

    # Large withdrawals (>$5000)
    large_count = pending_qs.filter(amount__gte=5000).count()

    # 7 day chart data
    chart_data = []
    for i in range(6, -1, -1):
        day = today_start - timedelta(days=i)
        day_end = day + timedelta(days=1)
        day_stats = Transaction.objects.filter(
            status="completed",
            created_at__gte=day,
            created_at__lt=day_end,
        ).aggregate(
            dep=models.Sum("amount_usd", filter=models.Q(type="deposit")),
            wd=models.Sum("amount_usd", filter=models.Q(type="withdrawal")),
        )
        chart_data.append({
            'date': day.strftime('%d.%m'),
            'deposits': float(day_stats["dep"] or 0),
            'withdrawals': float(day_stats["wd"] or 0),
        })

    context = {
        'deposits_today': deposits_total,
        'deposits_count': today_stats["deposits_count"] or 0,
        'withdrawals_today': withdrawals_total,
        'withdrawals_count': today_stats["withdrawals_count"] or 0,
        'net_flow': net_flow,
        'ggr_today': ggr,
        'fees_today': fees_total,
        'deposits_change': deposits_change,
        'withdrawals_change': withdrawals_change,
        'pending_withdrawals_count': pending_withdrawals_count,
        'pending_withdrawals_amount': pending_withdrawals_amount,
        'suspicious_count': suspicious_count,
        'large_count': large_count,
        'chart_data': chart_data,
    }

    return render(request, 'dashboard/finance/overview.html', context)


@require_permission('finance', 'view_transactions')
def withdrawals_queue(request):
    """Withdrawal approval queue with filters."""
    status_filter = request.GET.get('status', 'pending')
    risk_filter = request.GET.get('risk', '')

    qs = WithdrawalRequest.objects.select_related(
        "user", "currency", "wallet"
    ).order_by("created_at")

    if status_filter == 'pending':
        qs = qs.filter(status__in=["pending", "manual_review"])
    elif status_filter == 'approved':
        qs = qs.filter(status__in=["approved", "auto_approved", "processing"])
    elif status_filter == 'completed':
        qs = qs.filter(status="completed")
    elif status_filter == 'rejected':
        qs = qs.filter(status__in=["rejected", "cancelled"])
    # else: all

    if risk_filter:
        qs = qs.filter(risk_level=risk_filter)

    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'risk_filter': risk_filter,
        'pending_count': WithdrawalRequest.objects.filter(
            status__in=["pending", "manual_review"]
        ).count(),
    }

    return render(request, 'dashboard/finance/withdrawals.html', context)


@require_permission('finance', 'approve_withdrawals')
@require_POST
def withdrawal_action(request, withdrawal_id):
    """Approve or reject a withdrawal request."""
    wr = get_object_or_404(WithdrawalRequest, id=withdrawal_id)
    action = request.POST.get('action')
    comment = request.POST.get('comment', '')

    data_before = {
        'status': wr.status,
        'risk_level': wr.risk_level,
    }

    if action == 'approve':
        wr.status = 'approved'
        wr.reviewed_by = request.user
        wr.reviewed_at = timezone.now()
        wr.review_comment = comment
        wr.save()
        msg = f'Вывод #{wr.request_id} одобрен'
        messages.success(request, msg)

    elif action == 'reject':
        reason = request.POST.get('reason', 'Отклонено администратором')
        wr.status = 'rejected'
        wr.reviewed_by = request.user
        wr.reviewed_at = timezone.now()
        wr.review_comment = comment
        wr.rejection_reason = reason
        wr.save()

        # Unfreeze the balance
        try:
            balance = WalletBalance.objects.get(
                wallet=wr.wallet, currency=wr.currency
            )
            balance.unfreeze(wr.amount)
            balance.save()
        except (WalletBalance.DoesNotExist, Exception):
            pass

        msg = f'Вывод #{wr.request_id} отклонён'
        messages.warning(request, msg)
    else:
        messages.error(request, 'Неизвестное действие')
        return redirect('dashboard:finance_withdrawals')

    # Log action
    AdminActionLog.objects.create(
        admin_user=request.user,
        action_type=f'withdrawal_{action}',
        module='finance',
        action_category='withdrawal',
        description=f'{action} withdrawal #{wr.request_id} '
                    f'({wr.amount} {wr.currency_id}) for {wr.user.username}',
        target_user=wr.user,
        ip_address=request.META.get('REMOTE_ADDR'),
        data_before=data_before,
        data_after={'status': wr.status},
        is_successful=True,
    )

    return redirect('dashboard:finance_withdrawals')


@require_permission('finance', 'view_transactions')
def transactions_list(request):
    """All transactions list with filters and search."""
    tx_type = request.GET.get('type', '')
    tx_status = request.GET.get('status', '')
    search = request.GET.get('q', '').strip()
    period = request.GET.get('period', 'today')

    qs = Transaction.objects.select_related('user', 'currency').order_by('-created_at')

    # Period filter
    now = timezone.now()
    if period == 'today':
        qs = qs.filter(created_at__date=now.date())
    elif period == 'week':
        qs = qs.filter(created_at__gte=now - timedelta(days=7))
    elif period == 'month':
        qs = qs.filter(created_at__gte=now - timedelta(days=30))

    if tx_type:
        qs = qs.filter(type=tx_type)
    if tx_status:
        qs = qs.filter(status=tx_status)
    if search:
        qs = qs.filter(
            models.Q(transaction_id__icontains=search) |
            models.Q(user__username__icontains=search) |
            models.Q(user__email__icontains=search) |
            models.Q(description__icontains=search)
        )

    paginator = Paginator(qs, 50)
    page_obj = paginator.get_page(request.GET.get('page'))

    # Summary stats
    summary = qs.aggregate(
        total_amount=models.Sum('amount_usd'),
        count=models.Count('id'),
    )

    context = {
        'page_obj': page_obj,
        'type_filter': tx_type,
        'status_filter': tx_status,
        'period_filter': period,
        'search_query': search,
        'total_amount': summary['total_amount'] or 0,
        'total_count': summary['count'] or 0,
    }

    return render(request, 'dashboard/finance/transactions.html', context)


@require_permission('finance', 'export_data')
def transactions_export(request):
    """Export transactions as CSV."""
    period = request.GET.get('period', 'month')
    now = timezone.now()

    qs = Transaction.objects.select_related('user', 'currency').order_by('-created_at')
    if period == 'today':
        qs = qs.filter(created_at__date=now.date())
    elif period == 'week':
        qs = qs.filter(created_at__gte=now - timedelta(days=7))
    elif period == 'month':
        qs = qs.filter(created_at__gte=now - timedelta(days=30))

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="transactions_{now.strftime("%Y%m%d")}.csv"'
    response.write('\ufeff')  # BOM for Excel

    writer = csv.writer(response)
    writer.writerow([
        'ID', 'Дата', 'Пользователь', 'Тип', 'Валюта',
        'Сумма', 'Сумма USD', 'Статус', 'Описание'
    ])

    for tx in qs[:10000]:
        writer.writerow([
            tx.transaction_id,
            tx.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            tx.user.username if tx.user else '-',
            tx.get_type_display() if hasattr(tx, 'get_type_display') else tx.type,
            tx.currency_id,
            tx.amount,
            tx.amount_usd,
            tx.status,
            tx.description or '',
        ])

    return response


def _calc_change(current, previous):
    """Calculate percentage change."""
    if previous and previous > 0:
        return round(float((current - previous) / previous * 100), 1)
    return 0
