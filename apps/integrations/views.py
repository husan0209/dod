from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.shortcuts import render

from .services import get_odds_feed, get_prediction_feed


@login_required
def demo_hub(request):
    force_refresh = False
    if request.GET.get('refresh') == '1':
        force_refresh = cache.add(
            f'integration_demo_refresh:{request.user.pk}', True, timeout=15
        )

    return render(request, 'integrations/demo_hub.html', {
        'odds_feed': get_odds_feed(force_refresh=force_refresh),
        'prediction_feed': get_prediction_feed(force_refresh=force_refresh),
    })
