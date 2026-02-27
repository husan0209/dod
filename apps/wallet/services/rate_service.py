from decimal import Decimal
from typing import Optional

from django.core.cache import cache
from django.utils import timezone

from apps.wallet.models import Currency


class RateService:
    CACHE_TIMEOUT = 60 * 15  # 15 minutes

    @staticmethod
    def get_rate(from_code: str, to_code: str) -> Decimal:
        if from_code == to_code:
            return Decimal("1")
        cache_key = f"wallet_rate:{from_code}->{to_code}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached
        from_currency = Currency.objects.get(code=from_code)
        to_currency = Currency.objects.get(code=to_code)
        if to_currency.rate_to_usd == 0:
            raise ZeroDivisionError("Target currency rate is zero")
        rate = from_currency.rate_to_usd / to_currency.rate_to_usd
        cache.set(cache_key, rate, RateService.CACHE_TIMEOUT)
        return rate

    @staticmethod
    def update_all_rates(fiat_rates: Optional[dict] = None, crypto_rates: Optional[dict] = None) -> None:
        # Placeholder: real implementation should call external APIs (exchangerate-api, CoinGecko)
        now = timezone.now()
        updated_codes = set()
        if fiat_rates:
            for code, rate in fiat_rates.items():
                Currency.objects.filter(code=code).update(rate_to_usd=Decimal(str(rate)), rate_updated_at=now)
                updated_codes.add(code)
        if crypto_rates:
            for code, rate in crypto_rates.items():
                Currency.objects.filter(code=code).update(rate_to_usd=Decimal(str(rate)), rate_updated_at=now)
                updated_codes.add(code)
        # Invalidate cache for updated pairs
        if updated_codes:
            for code in updated_codes:
                cache.delete_pattern(f"wallet_rate:{code}->*")
                cache.delete_pattern(f"wallet_rate:*->{code}")
