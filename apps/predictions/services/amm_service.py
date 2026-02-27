from decimal import Decimal
from django.db import transaction

from ..models import Market, AMMPool


class AMMService:
    """
    Automated Market Maker.
    Constant Product Market Maker formula: yes_pool × no_pool = K
    """

    @staticmethod
    def calculate_buy_price(market, outcome, amount):
        """
        Рассчитать сколько акций получит покупатель.
        НЕ ИЗМЕНЯЕТ пулы (preview).
        """
        pool = market.amm_pool
        if outcome.title.lower() == 'да':  # yes
            # Добавляем деньги в no_pool
            new_no_pool = pool.pool_no + Decimal(str(amount))
            new_yes_pool = pool.constant_product / new_no_pool
            shares = pool.pool_yes - new_yes_pool
        else:  # no
            new_yes_pool = pool.pool_yes + Decimal(str(amount))
            new_no_pool = pool.constant_product / new_yes_pool
            shares = pool.pool_no - new_no_pool

        avg_price = amount / shares if shares > 0 else Decimal('0')
        
        # Новые цены после сделки
        total = new_yes_pool + new_no_pool
        new_yes_price = new_no_pool / total
        new_no_price = new_yes_pool / total

        # Price impact
        current_price = outcome.current_price
        if outcome.title.lower() == 'да':
            price_impact = (new_yes_price - float(current_price)) / float(current_price) * 100
        else:
            price_impact = (new_no_price - float(current_price)) / float(current_price) * 100

        potential_payout = shares
        potential_profit = shares - amount
        potential_roi_percent = (potential_profit / amount * 100) if amount > 0 else Decimal('0')

        return {
            "shares": round(shares, 8),
            "avg_price": round(avg_price, 4),
            "total_cost": amount,
            "new_price": round(new_yes_price if outcome.title.lower() == 'да' else new_no_price, 4),
            "price_impact_percent": round(price_impact, 2),
            "potential_payout": round(potential_payout, 2),
            "potential_profit": round(potential_profit, 2),
            "potential_roi_percent": round(potential_roi_percent, 2),
        }

    @staticmethod
    def calculate_sell_price(market, outcome, shares):
        """
        Рассчитать сколько получит продавец.
        НЕ ИЗМЕНЯЕТ пулы (preview).
        """
        pool = market.amm_pool
        if outcome.title.lower() == 'да':
            new_yes_pool = pool.pool_yes + Decimal(str(shares))
            new_no_pool = pool.constant_product / new_yes_pool
            payout = pool.pool_no - new_no_pool
        else:
            new_no_pool = pool.pool_no + Decimal(str(shares))
            new_yes_pool = pool.constant_product / new_no_pool
            payout = pool.pool_yes - new_yes_pool

        avg_price = payout / shares if shares > 0 else Decimal('0')
        
        total = new_yes_pool + new_no_pool
        new_yes_price = new_no_pool / total
        new_no_price = new_yes_pool / total

        return {
            "shares_sold": shares,
            "payout": round(payout, 8),
            "avg_price": round(avg_price, 4),
            "new_price": round(new_yes_price if outcome.title.lower() == 'да' else new_no_price, 4)
        }

    @staticmethod
    @transaction.atomic
    def execute_buy(market, outcome, amount):
        """
        Выполнить покупку. ИЗМЕНЯЕТ пулы.
        Вызывается ТОЛЬКО из TradingService (внутри atomic).
        """
        pool = market.amm_pool
        preview = AMMService.calculate_buy_price(market, outcome, amount)
        
        if outcome.title.lower() == 'да':
            pool.pool_no += Decimal(str(amount))
            pool.pool_yes = pool.constant_product / pool.pool_no
        else:
            pool.pool_yes += Decimal(str(amount))
            pool.pool_no = pool.constant_product / pool.pool_yes
        
        pool.save()
        
        # Update outcome prices
        total = pool.pool_yes + pool.pool_no
        for out in market.outcomes.all():
            if out.title.lower() == 'да':
                out.current_price = pool.pool_no / total
            else:
                out.current_price = pool.pool_yes / total
            out.save()
        
        return preview

    @staticmethod
    @transaction.atomic
    def execute_sell(market, outcome, shares):
        """
        Выполнить продажу. ИЗМЕНЯЕТ пулы.
        """
        pool = market.amm_pool
        preview = AMMService.calculate_sell_price(market, outcome, shares)
        
        if outcome.title.lower() == 'да':
            pool.pool_yes += Decimal(str(shares))
            pool.pool_no = pool.constant_product / pool.pool_yes
        else:
            pool.pool_no += Decimal(str(shares))
            pool.pool_yes = pool.constant_product / pool.pool_no
        
        pool.save()
        
        # Update outcome prices
        total = pool.pool_yes + pool.pool_no
        for out in market.outcomes.all():
            if out.title.lower() == 'да':
                out.current_price = pool.pool_no / total
            else:
                out.current_price = pool.pool_yes / total
            out.save()
        
        return preview
