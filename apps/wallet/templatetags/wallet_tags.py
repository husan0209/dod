from decimal import Decimal

from django import template
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from apps.wallet.models import Currency, Wallet

register = template.Library()

_CURRENCY_LOGOS = {
    "BTC": (
        "#F7931A",
        '<path d="M23.638 14.904c-1.602 6.43-8.113 10.34-14.542 8.736C2.67 22.05-1.244 15.525.362 9.105 1.962 2.67 8.475-1.243 14.9.358c6.43 1.605 10.342 8.115 8.738 14.548v-.002zm-6.35-4.613c.24-1.59-.974-2.45-2.64-3.03l.54-2.153-1.315-.33-.525 2.107c-.345-.087-.705-.167-1.064-.25l.526-2.127-1.32-.33-.54 2.165c-.285-.067-.565-.132-.84-.2l-1.815-.45-.35 1.407s.975.225.955.236c.535.136.63.486.615.766l-1.477 5.92c-.075.166-.24.406-.614.314.015.02-.96-.24-.96-.24l-.66 1.51 1.71.426.93.242-.54 2.19 1.32.327.54-2.17c.36.1.705.19 1.05.273l-.51 2.154 1.32.33.545-2.19c2.24.427 3.93.257 4.64-1.774.57-1.637-.03-2.58-1.217-3.196.854-.193 1.5-.76 1.68-1.93h.01zm-3.01 4.22c-.404 1.64-3.157.75-4.05.53l.72-2.9c.896.23 3.757.67 3.33 2.37zm.41-4.24c-.37 1.49-2.662.735-3.405.55l.654-2.64c.744.18 3.137.524 2.75 2.084v.006z"/>',
    ),
    "ETH": (
        "#627EEA",
        '<path d="M11.944 17.97 4.58 13.62 11.943 24l7.37-10.38-7.372 4.35h.003zM12.056 0 4.69 12.223l7.365 4.354 7.365-4.35L12.056 0z"/>',
    ),
    "USDT": (
        "#26A17B",
        '<path d="M18.7538 10.5176c0 .6251-2.2379 1.1483-5.2381 1.2812l.0028.0007c-.0848.0064-.5233.0325-1.5012.0325-.7778 0-1.33-.0233-1.5237-.0325-3.0059-.1322-5.2495-.6555-5.2495-1.2819s2.2436-1.149 5.2495-1.2834v2.0442c.1965.0142.7594.0474 1.5372.0474.9334 0 1.4008-.0389 1.4849-.0466V9.2356c2.9994.1337 5.2381.657 5.2381 1.282zm5.19.5466L12.1248 22.389a.1803.1803 0 0 1-.2496 0L.0562 11.0635a.1781.1781 0 0 1-.0382-.2079l4.3762-9.1921a.1767.1767 0 0 1 .1626-.1026h14.8878a.1768.1768 0 0 1 .1612.1032l4.3762 9.1922a.1782.1782 0 0 1-.0382.2079zm-4.478-.4038c0-.8068-2.5515-1.4799-5.9473-1.6369V7.195h4.186V4.4055H6.3076V7.195h4.1852v1.8286c-3.4018.1562-5.9601.83-5.9601 1.6376 0 .8075 2.5583 1.4806 5.9601 1.6376v5.8618h3.025v-5.8639c3.394-.1563 5.948-.8295 5.948-1.6363z"/>',
    ),
    "LTC": (
        "#345D9D",
        '<path d="M12 0a12 12 0 1 0 0 24 12 12 0 0 0 0-24zm-.2617 3.6777h2.584a.3425.3425 0 0 1 .33.4356l-2.0312 6.918 1.9062-.582-.4082 1.3847-1.9238.5605-1.248 4.213h6.6757a.3425.3425 0 0 1 .3282.4374l-.582 2a.4586.4586 0 0 1-.4395.3301H6.7324l1.7227-5.8223-1.9063.5801.42-1.3613 1.9101-.58 2.4219-8.1798a.4557.4557 0 0 1 .4375-.334Z"/>',
    ),
    "TRX": (
        "#EF0027",
        '<path d="M3 4.2 21 7l-7.5 14.8L3 4.2Zm3.5 2.7 6.7 11.2 5.1-10.1L6.5 6.9Zm1.1-1.5 8.8 1.4-4.1 2.7-4.7-4.1Z" fill="#fff"/>',
    ),
    "BNB": (
        "#F0B90B",
        '<path d="m16.624 13.9202 2.7175 2.7154-7.353 7.353-7.353-7.352 2.7175-2.7164 4.6355 4.6595 4.6356-4.6595zm4.6366-4.6366L24 12l-2.7154 2.7164L18.5682 12l2.6924-2.7164zm-9.272.001 2.7163 2.6914-2.7164 2.7174v-.001L9.2721 12l2.7164-2.7154zm-9.2722-.001L5.4088 12l-2.6914 2.6924L0 12l2.7164-2.7164zM11.9885.0115l7.353 7.329-2.7174 2.7154-4.6356-4.6356-4.6355 4.6595-2.7174-2.7154 7.353-7.353z"/>',
    ),
    "TON": (
        "#0098EA",
        '<path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zM7.902 6.697h8.196c1.505 0 2.462 1.628 1.705 2.94l-5.059 8.765a.86.86 0 0 1-1.488 0L6.199 9.637c-.758-1.314.197-2.94 1.703-2.94zm4.844 1.496v7.58l1.102-2.128 2.656-4.756a.465.465 0 0 0-.408-.696h-3.35zM7.9 8.195a.464.464 0 0 0-.408.694l2.658 4.754 1.102 2.13V8.195H7.9z"/>',
    ),
}

_CURRENCY_SYMBOLS = {
    "USD": "$",
    "EUR": "€",
    "RUB": "₽",
    "UAH": "₴",
    "KZT": "₸",
    "UZS": "сўм",
    "BYN": "Br",
    "BTC": "₿",
    "ETH": "Ξ",
    "USDT": "₮",
    "BNB": "BNB",
    "LTC": "Ł",
    "TON": "TON",
    "TRX": "TRX",
}


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
def currency_logo(currency_code: str, size: str = "w-6 h-6"):
    """Render a local brand mark for crypto or an ISO currency symbol for fiat."""
    code = str(currency_code or "").upper()
    logo = _CURRENCY_LOGOS.get(code)
    if logo:
        color, paths = logo
        return format_html(
            '<svg class="{}" viewBox="0 0 24 24" role="img" aria-label="{}" '
            'xmlns="http://www.w3.org/2000/svg" fill="currentColor" style="color:{}">{}</svg>',
            size,
            code,
            color,
            mark_safe(paths),
        )

    symbol = _CURRENCY_SYMBOLS.get(code, code or "?")
    return format_html(
        '<span class="{} inline-flex items-center justify-center rounded-full bg-white/10 '
        'text-white font-bold leading-none" aria-label="{}">{}</span>',
        size,
        code,
        symbol,
    )


@register.simple_tag
def currency_symbol(currency_code: str) -> str:
    """Return a standard text symbol without falling back to stored emoji icons."""
    code = str(currency_code or "").upper()
    return _CURRENCY_SYMBOLS.get(code, code or "?")


@register.simple_tag
def payment_method_logo(method_code: str, currency_code: str = "", size: str = "w-6 h-6"):
    """Render a payment-specific icon instead of the emoji stored in seed data."""
    method = str(method_code or "").lower()
    if method in _CURRENCY_LOGOS:
        return currency_logo(method, size)
    if currency_code and str(currency_code).upper() in _CURRENCY_LOGOS:
        return currency_logo(currency_code, size)

    if method in {"crypto", "coin", "cryptocurrency"} or method.startswith("nowpay_"):
        path = '<path d="m12 2 8 5v10l-8 5-8-5V7l8-5Z" fill="none" stroke="currentColor" stroke-width="2"/><path d="m4 7 8 5 8-5m-8 5v10" fill="none" stroke="currentColor" stroke-width="2"/>'
        label = "Криптовалюта"
        color = "#F0B90B"
    elif method in {"card", "bank_card", "visa", "mastercard"}:
        path = '<rect x="3" y="5" width="18" height="14" rx="2" fill="none" stroke="currentColor" stroke-width="2"/><path d="M3 10h18M7 15h3" fill="none" stroke="currentColor" stroke-width="2"/>'
        label = "Банковская карта"
        color = "#60A5FA"
    else:
        path = '<rect x="6" y="2" width="12" height="20" rx="2" fill="none" stroke="currentColor" stroke-width="2"/><path d="M9 5h6M10 18h4" fill="none" stroke="currentColor" stroke-width="2"/>'
        label = "Электронный платёж"
        color = "#34D399"
    return format_html(
        '<svg class="{}" viewBox="0 0 24 24" role="img" aria-label="{}" '
        'xmlns="http://www.w3.org/2000/svg" style="color:{}">{}</svg>',
        size,
        label,
        color,
        mark_safe(path),
    )


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
