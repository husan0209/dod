from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta

from apps.dashboard.services.analytics_service import AnalyticsService
from apps.dashboard.decorators import require_permission


@login_required
@require_permission('analytics', 'view')
def analytics_overview(request):
    """Main analytics dashboard."""
    # Days filter (default 7)
    days = int(request.GET.get('days', 7))
    
    financials = AnalyticsService.get_financial_summary(days=days)
    users = AnalyticsService.get_user_activity(days=days)
    charts = AnalyticsService.get_revenue_chart_data(days=days)
    
    return render(request, 'dashboard/analytics/overview.html', {
        'financials': financials,
        'users': users,
        'charts': charts,
        'days': days
    })


@login_required
@require_permission('analytics', 'view_financial_reports')
def financial_report(request):
    """Detailed financial report with breakdowns."""
    days = int(request.GET.get('days', 30))
    financials = AnalyticsService.get_financial_summary(days=days)
    
    # Simple breakdown for the table
    breakdown = [
        {'name': 'Casino GGR', 'value': financials['casino_ggr'], 'type': 'revenue'},
        {'name': 'Sports GGR', 'value': financials['sports_ggr'], 'type': 'revenue'},
        {'name': 'Deposits', 'value': financials['deposits'], 'type': 'flow'},
        {'name': 'Withdrawals', 'value': financials['withdrawals'], 'type': 'flow'},
        {'name': 'Net Flow', 'value': financials['net_flow'], 'type': 'kpi'},
    ]
    
    return render(request, 'dashboard/analytics/financial.html', {
        'financials': financials,
        'breakdown': breakdown,
        'days': days
    })


@login_required
@require_permission('analytics', 'view_user_analytics')
def user_analytics(request):
    """Deep dive into user cohorts and activity."""
    days = int(request.GET.get('days', 30))
    stats = AnalyticsService.get_user_activity(days=days)
    
    return render(request, 'dashboard/analytics/users.html', {
        'stats': stats,
        'days': days
    })
