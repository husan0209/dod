from django.shortcuts import render

from apps.dashboard.decorators import require_permission


@require_permission('casino', 'view')
def casino_overview(request):
    """Casino management overview"""
    # Placeholder metrics - in real implementation, query actual data
    context = {
        'active_players': 234,
        'rounds_today': 3456,
        'ggr_casino': 7890.12,
        'crash_ggr': 1234.56,
        'mines_ggr': 2345.67,
        'dice_ggr': 3456.78,
    }
    
    return render(request, 'dashboard/casino/overview.html', context)
