from django.shortcuts import render

from apps.dashboard.decorators import require_permission


@require_permission('sports', 'view')
def sports_overview(request):
    """Sports management overview"""
    # Placeholder metrics - in real implementation, query actual data
    context = {
        'active_events': 5,
        'bets_today': 1234,
        'ggr_sports': 5678.90,
        'live_matches': 3,
    }
    
    return render(request, 'dashboard/sports/overview.html', context)
