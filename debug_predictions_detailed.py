#!/usr/bin/env python
"""Debug predictions index by testing each component"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from django.db.models import Sum
from apps.predictions.models import PredictionMarket

print("1. Checking PredictionMarket query...")
try:
    queryset = PredictionMarket.objects.filter(status='active').select_related('category')
    print(f"   ✅ Query works, found {queryset.count()} markets")
except Exception as e:
    print(f"   ❌ Error: {e}")

print("\n2. Checking aggregate (total_volume)...")
try:
    result = PredictionMarket.objects.aggregate(
        total=Sum('volume_usd')
    )
    print(f"   ✅ Aggregate works: total = {result['total']}")
except Exception as e:
    print(f"   ❌ Error: {e}")

print("\n3. Checking market methods...")
try:
    market = PredictionMarket.objects.filter(status='active').first()
    if market:
        print(f"   Testing market: {market.question[:50]}...")
        print(f"   - yes_probability: {market.get_yes_probability()}")
        print(f"   - no_probability: {market.get_no_probability()}")
        print(f"   - time_until_close: {market.get_time_until_close()}")
        print(f"   ✅ All methods work")
    else:
        print("   ℹ️ No active markets found")
except Exception as e:
    print(f"   ❌ Error: {e}")
    import traceback
    traceback.print_exc()
