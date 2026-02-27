from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def probability_color(value):
    """Return color class based on probability value."""
    try:
        prob = float(value)
        if prob > 60:
            return 'text-green-600'
        elif prob > 40:
            return 'text-yellow-600'
        else:
            return 'text-red-600'
    except (ValueError, TypeError):
        return 'text-gray-600'


@register.filter
def pnl_color(value):
    """Return color class for PnL values."""
    try:
        pnl = float(value)
        if pnl > 0:
            return 'text-green-600'
        elif pnl < 0:
            return 'text-red-600'
        else:
            return 'text-gray-600'
    except (ValueError, TypeError):
        return 'text-gray-600'


@register.filter
def format_shares(value):
    """Format shares with appropriate precision."""
    try:
        shares = float(value)
        if shares >= 1:
            return f"{shares:.2f}"
        else:
            return f"{shares:.8f}"
    except (ValueError, TypeError):
        return str(value)


@register.simple_tag
def market_status_badge(status):
    """Return a colored badge for market status."""
    status_map = {
        'draft': ('badge-neutral', 'Draft'),
        'pending_review': ('badge-warning', 'Pending Review'),
        'active': ('badge-success', 'Active'),
        'trading_halted': ('badge-error', 'Trading Halted'),
        'pending_resolution': ('badge-info', 'Pending Resolution'),
        'resolved': ('badge-primary', 'Resolved'),
        'voided': ('badge-error', 'Voided'),
        'disputed': ('badge-warning', 'Disputed'),
    }
    
    css_class, label = status_map.get(status, ('badge-neutral', status))
    return mark_safe(f'<span class="badge {css_class}">{label}</span>')
