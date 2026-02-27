from django.shortcuts import render

from apps.dashboard.decorators import require_permission


@require_permission('predictions', 'view')
def predictions_overview(request):
    """Predictions management overview"""
    # Placeholder metrics - in real implementation, query actual data
    context = {
        'active_markets': 12,
        'positions_today': 567,
        'ggr_predictions': 1234.56,
        'markets_resolved_today': 3,
    }
    
    return render(request, 'dashboard/predictions/overview.html', context)
