from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.template.loader import render_to_string
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from django.db import models

from apps.accounts.models import User, AdminActionLog
from apps.wallet.models import Transaction, WithdrawalRequest, KYCVerification
from apps.dashboard.decorators import require_permission
from apps.support.models import Ticket


@login_required
@require_permission('dashboard', 'view')
def stats_view(request):
    """Return dashboard stats HTML fragment"""
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = today_start - timedelta(days=1)
    
    # Current metrics
    online_users = User.objects.filter(is_online=True).count()
    deposits_today = Transaction.objects.filter(
        type='deposit',
        status='completed',
        created_at__gte=today_start
    ).aggregate(
        count=models.Count('id'),
        total=models.Sum('amount_usd')
    )
    withdrawals_today = Transaction.objects.filter(
        type='withdrawal',
        status='completed',
        created_at__gte=today_start
    ).aggregate(
        count=models.Count('id'),
        total=models.Sum('amount_usd')
    )
    
    # GGR calculations (simplified)
    sports_ggr = Transaction.objects.filter(
        type='bet_win',
        created_at__gte=today_start
    ).aggregate(total=models.Sum('amount_usd'))['total'] or Decimal('0')
    
    casino_ggr = Transaction.objects.filter(
        type='casino_win',
        created_at__gte=today_start
    ).aggregate(total=models.Sum('amount_usd'))['total'] or Decimal('0')
    
    predictions_ggr = Transaction.objects.filter(
        type='prediction_win',
        created_at__gte=today_start
    ).aggregate(total=models.Sum('amount_usd'))['total'] or Decimal('0')
    
    total_ggr = sports_ggr + casino_ggr + predictions_ggr
    net_flow = (deposits_today['total'] or Decimal('0')) - (withdrawals_today['total'] or Decimal('0'))
    
    # Attention items
    withdrawals_pending = WithdrawalRequest.objects.filter(
        status__in=["pending", "manual_review", "auto_approved", "approved", "processing"],
        created_at__lt=now - timedelta(hours=12),
    ).count()
    
    kyc_pending = KYCVerification.objects.filter(
        status="pending",
        created_at__lt=now - timedelta(hours=24),
    ).count()
    
    tickets_sla_violated = Ticket.objects.filter(
        status__in=['open', 'in_progress'],
        created_at__lt=now - timedelta(hours=24)
    ).count()
    
    open_tickets = Ticket.objects.filter(status__in=['open', 'in_progress']).count()
    
    # Recent admin actions
    recent_actions = AdminActionLog.objects.select_related('admin_user').order_by('-created_at')[:5]
    
    context = {
        'online_users': online_users,
        'deposits_today': deposits_today['total'] or Decimal('0'),
        'withdrawals_today': withdrawals_today['total'] or Decimal('0'),
        'sports_ggr': sports_ggr,
        'casino_ggr': casino_ggr,
        'predictions_ggr': predictions_ggr,
        'total_ggr': total_ggr,
        'net_flow': net_flow,
        'new_registrations_today': User.objects.filter(date_joined__gte=today_start).count(),
        'open_tickets': open_tickets,
        'withdrawals_pending': withdrawals_pending,
        'kyc_pending': kyc_pending,
        'tickets_sla_violated': tickets_sla_violated,
        'recent_actions': recent_actions,
        'updated_at': now,
    }
    
    html = render_to_string('dashboard/main/stats.html', context)
    return HttpResponse(html)


@login_required
@require_permission('dashboard', 'view')
def global_search_view(request):
    """Global search API"""
    query = request.GET.get('q', '').strip()

    user_results = []
    ticket_results = []
    if query:
        # Search users
        users = User.objects.filter(
            models.Q(email__icontains=query) |
            models.Q(username__icontains=query)
        )[:5]
        for user in users:
            user_results.append({
                'title': user.username,
                'subtitle': user.email,
                'url': f'/admin-panel/users/{user.id}/'
            })
        
        # Search tickets (if available)
        if Ticket:
            tickets = Ticket.objects.filter(
                models.Q(title__icontains=query) |
                models.Q(description__icontains=query)
            )[:3]
            for ticket in tickets:
                ticket_results.append({
                    'title': f'#{ticket.ticket_number}' if getattr(ticket, 'ticket_number', None) else f'Ticket #{ticket.id}',
                    'subtitle': ticket.title,
                    'url': f'/support/operator/tickets/{ticket.id}/'
                })
    
    context = {
        'query': query,
        'user_results': user_results,
        'ticket_results': ticket_results,
    }
    
    html = render_to_string('dashboard/search_results.html', context)
    return HttpResponse(html)
