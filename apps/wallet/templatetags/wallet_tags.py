from decimal import Decimal

from django import template
from django.utils.safestring import mark_safe

from apps.wallet.models import Currency, Wallet

register = template.Library()


@register.filter
def split(value, delimiter=","):
    """
    Разбивает строку по разделителю.
    Использование: {{ "10,25,50"|split:"," }}
    """
    if isinstance(value, str):
        return value.split(delimiter)
    return []


@register.simple_tag
def user_balance(user) -> str:
    """
    Возвращает форматированный баланс пользователя в его основной валюте кошелька.
    Если кошелька ещё нет или пользователь не аутентифицирован — "$0.00".
    """
    if not getattr(user, "is_authenticated", False):
        return "$0.00"
    wallet: Wallet | None = getattr(user, "wallet", None)
    if not wallet:
        return "$0.00"
    try:
        return wallet.get_primary_balance_display()
    except Exception:
        return "$0.00"


@register.simple_tag
def user_balance_raw(user) -> Decimal:
    """
    Возвращает числовое значение баланса в основной валюте.
    Удобно для JS / data-атрибутов.
    """
    if not getattr(user, "is_authenticated", False):
        return Decimal("0")
    wallet: Wallet | None = getattr(user, "wallet", None)
    if not wallet:
        return Decimal("0")
    return wallet.get_primary_balance()


@register.simple_tag
def format_currency(amount: Decimal | int | float, currency_code: str) -> str:
    """
    Форматирует произвольную сумму в указанной валюте:
    {% format_currency 1234.56 "USD" %} -> "$1,234.56"
    """
    try:
        amount_dec = Decimal(str(amount))
        currency = Currency.objects.get(code=currency_code)
        return currency.format_amount(amount_dec)
    except Exception:
        return str(amount)


@register.simple_tag
def currency_icon(currency_code: str) -> str:
    """
    Возвращает символ/иконку валюты.
    """
    try:
        currency = Currency.objects.get(code=currency_code)
        return currency.icon or currency.symbol or currency_code
    except Currency.DoesNotExist:
        return currency_code


@register.simple_tag
def format_transaction_amount(tx) -> str:
    """
    Форматированная сумма транзакции с цветом и знаком.
    """
    try:
        signed = tx.get_signed_amount()
        cls = "text-green-400" if signed >= 0 else "text-red-400"
        prefix = "+" if signed >= 0 else "−"
        formatted = tx.currency.format_amount(abs(signed))
        html = f'<span class="{cls}">{prefix}{formatted}</span>'
        return mark_safe(html)
    except Exception:
        return str(getattr(tx, "amount", ""))


@register.simple_tag
def conversion_rate(from_code: str, to_code: str) -> str:
    """
    Возвращает строку вида: "1 USD = 90.45 RUB".
    """
    try:
        from_currency = Currency.objects.get(code=from_code)
        to_currency = Currency.objects.get(code=to_code)
        if to_currency.rate_to_usd == 0:
            return f"1 {from_code} = ? {to_code}"
        rate = from_currency.rate_to_usd / to_currency.rate_to_usd
        rate_str = f"{rate.quantize(Decimal('0.0001'))}"
        return f"1 {from_code} = {rate_str} {to_code}"
    except Currency.DoesNotExist:
        return ""
@register.filter
def get_balance_by_code(wallet, code):
    """
    Возвращает баланс кошелька для конкретной валюты.
    Использование: {{ wallet|get_balance_by_code:currency_code }}
    """
    if not wallet or not code:
        return Decimal("0")
    try:
        return wallet.get_balance(code)
    except Exception:
        return Decimal("0")
