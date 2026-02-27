from django import template

register = template.Library()


@register.filter
def format_currency(amount, currency):
    try:
        return currency.format_amount(amount)
    except Exception:
        return amount
