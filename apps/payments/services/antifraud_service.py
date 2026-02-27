from __future__ import annotations

from decimal import Decimal
from typing import Dict

from apps.wallet.models import Currency


class AntiFraudService:
    @staticmethod
    def assess_deposit(user, amount: Decimal, currency: Currency) -> Dict:
        # Minimal placeholder: mark low risk always; hook for future rules.
        return {"risk": "low", "reasons": []}

    @staticmethod
    def is_deposit_blocked(user, amount: Decimal, currency: Currency) -> bool:
        assessment = AntiFraudService.assess_deposit(user, amount, currency)
        return assessment.get("risk") in {"high", "critical"}
