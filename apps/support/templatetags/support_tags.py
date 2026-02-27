from django import template
from django.utils import timezone
from ..models import SLAConfig

register = template.Library()


@register.filter
def time_since(value):
    """Return time since the given datetime."""
    if not value:
        return ''
    now = timezone.now()
    diff = now - value
    if diff.days > 0:
        return f'{diff.days} days ago'
    elif diff.seconds // 3600 > 0:
        return f'{diff.seconds // 3600} hours ago'
    elif diff.seconds // 60 > 0:
        return f'{diff.seconds // 60} minutes ago'
    else:
        return 'Just now'


@register.filter
def sla_status(ticket):
    """Return SLA status for a ticket."""
    sla = SLAConfig.get_for_priority(ticket.priority)
    if ticket.first_response_at:
        return 'ok'
    time_since = timezone.now() - ticket.created_at
    if time_since > sla.first_response_time:
        return 'breached'
    return 'warning'
