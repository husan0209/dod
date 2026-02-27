from django import template
from decimal import Decimal

register = template.Library()


@register.filter
def format_currency(amount, currency='USD'):
    """Форматировать сумму с валютой."""
    if amount is None:
        return '0.00'
    return f"{amount:.2f} {currency}"


@register.filter
def multiply(value, arg):
    """Умножить значение на аргумент."""
    try:
        return Decimal(str(value)) * Decimal(str(arg))
    except:
        return 0


@register.filter
def subtract(value, arg):
    """Вычесть аргумент из значения."""
    try:
        return Decimal(str(value)) - Decimal(str(arg))
    except:
        return 0


@register.simple_tag
def get_game_icon(game_code):
    """Получить иконку игры."""
    icons = {
        'crash': '📈',
        'slots': '🎰',
        'roulette': '🎡',
        'mines': '💣',
        'dice': '🎲',
        'plinko': '📌',
    }
    return icons.get(game_code, '🎮')


@register.simple_tag
def get_game_name(game_code):
    """Получить название игры."""
    names = {
        'crash': 'Crash',
        'slots': 'Slots',
        'roulette': 'Roulette',
        'mines': 'Mines',
        'dice': 'Dice',
        'plinko': 'Plinko',
    }
    return names.get(game_code, game_code.title())
