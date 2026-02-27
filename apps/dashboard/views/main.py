from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from apps.dashboard.decorators import require_permission


@login_required
@require_permission('dashboard', 'view')
def dashboard_view(request):
    """Main dashboard view"""
    context = {
        'page_title': 'Дашборд',
    }
    return render(request, 'dashboard/main/dashboard.html', context)
