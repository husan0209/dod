from decimal import Decimal
from django.db import transaction

from ..models import PredictionMarket


class AMMService:
    """
    Automated Market Maker.
    Constant Product Market Maker formula: yes_pool × no_pool = K
    
    Как это работает:
      Пул начинается: yes=10000, no=10000, K=100000000
      Цена YES = no / (yes + no) = 0.5000 (50%)
      
      Кто-то покупает YES за $100:
      → $100 добавляется в no_pool
      → no_pool = 10100
      → yes_pool = K / no_pool = 100000000 / 10100 = 9900.99
      → shares = 10000 - 9900.99 = 99.01 акций YES
    """

    @staticmethod
    def calculate_buy_price(market, side, amount):
        """
        Рассчитать сколько акций получит покупатель.
        НЕ ИЗМЕНЯЕТ пулы (preview).
        
        Args:
            market: PredictionMarket
            side: 'yes' или 'no'
            amount: сумма покупки (USD)
        
        Returns:
            dict с информацией о сделке
        """
        amount_dec = Decimal(str(amount))
        
        if side == 'yes':
            # Добавляем деньги в no_pool
            new_no_pool = market.no_pool + amount_dec
            new_yes_pool = market.constant_k / new_no_pool
            shares = market.yes_pool - new_yes_pool
        else:  # 'no'
            new_yes_pool = market.yes_pool + amount_dec
            new_no_pool = market.constant_k / new_yes_pool
            shares = market.no_pool - new_no_pool

        avg_price = amount_dec / shares if shares > 0 else Decimal('0')
        
        # Новые цены после сделки
        total = new_yes_pool + new_no_pool
        new_yes_price = new_no_pool / total if total > 0 else Decimal('0.5')
        new_no_price = new_yes_pool / total if total > 0 else Decimal('0.5')

        # Price impact
        current_price = market.yes_price if side == 'yes' else market.no_price
        if current_price > 0:
            price_impact = (
                (new_yes_price - current_price) / current_price * 100
                if side == 'yes'
                else (new_no_price - current_price) / current_price * 100
            )
        else:
            price_impact = Decimal('0')

        potential_payout = shares
        potential_profit = shares - amount_dec
        potential_roi_percent = (
            (potential_profit / amount_dec * 100) if amount_dec > 0 else Decimal('0')
        )

        return {
            "shares": float(round(shares, 8)),
            "avg_price": float(round(avg_price, 4)),
            "total_cost": float(amount),
            "new_yes_price": float(round(new_yes_price, 4)),
            "new_no_price": float(round(new_no_price, 4)),
            "price_impact_percent": float(round(price_impact, 2)),
            "potential_payout": float(round(potential_payout, 2)),
            "potential_profit": float(round(potential_profit, 2)),
            "potential_roi_percent": float(round(potential_roi_percent, 2)),
        }

    @staticmethod
    def calculate_sell_price(market, side, shares):
        """
        Рассчитать сколько получит продавец.
        НЕ ИЗМЕНЯЕТ пулы (preview).
        """
        shares_dec = Decimal(str(shares))
        
        if side == 'yes':
            new_yes_pool = market.yes_pool + shares_dec
            new_no_pool = market.constant_k / new_yes_pool if new_yes_pool > 0 else Decimal('0')
            payout = market.no_pool - new_no_pool
        else:  # 'no'
            new_no_pool = market.no_pool + shares_dec
            new_yes_pool = market.constant_k / new_no_pool if new_no_pool > 0 else Decimal('0')
            payout = market.yes_pool - new_yes_pool

        avg_price = payout / shares_dec if shares_dec > 0 else Decimal('0')
        
        total = new_yes_pool + new_no_pool
        new_yes_price = new_no_pool / total if total > 0 else Decimal('0.5')
        new_no_price = new_yes_pool / total if total > 0 else Decimal('0.5')

        return {
            "shares_sold": float(shares),
            "payout": float(round(payout, 8)),
            "avg_price": float(round(avg_price, 4)),
            "new_yes_price": float(round(new_yes_price, 4)),
            "new_no_price": float(round(new_no_price, 4))
        }

    @staticmethod
    @transaction.atomic
    def execute_buy(market, side, amount):
        """
        Выполнить покупку. ИЗМЕНЯЕТ пулы.
        Вызывается ТОЛЬКО из TradingService (внутри atomic).
        
        Args:
            market: PredictionMarket (должна быть заблокирована select_for_update)
            side: 'yes' или 'no'
            amount: сумма в USD
        
        Returns:
            dict с результатом сделки
        """
        amount_dec = Decimal(str(amount))
        preview = AMMService.calculate_buy_price(market, side, amount)
        
        if side == 'yes':
            market.no_pool += amount_dec
            market.yes_pool = market.constant_k / market.no_pool if market.no_pool > 0 else Decimal('0')
        else:  # 'no'
            market.yes_pool += amount_dec
            market.no_pool = market.constant_k / market.yes_pool if market.yes_pool > 0 else Decimal('0')
        
        market.recalculate_prices()
        market.save(update_fields=['yes_pool', 'no_pool', 'yes_price', 'no_price'])
        
        return preview

    @staticmethod
    @transaction.atomic
    def execute_sell(market, side, shares):
        """
        Выполнить продажу. ИЗМЕНЯЕТ пулы.
        
        Args:
            market: PredictionMarket (должна быть заблокирована)
            side: 'yes' или 'no'
            shares: количество акций
        
        Returns:
            dict с результатом сделки
        """
        shares_dec = Decimal(str(shares))
        preview = AMMService.calculate_sell_price(market, side, shares)
        
        if side == 'yes':
            market.yes_pool += shares_dec
            market.no_pool = market.constant_k / market.yes_pool if market.yes_pool > 0 else Decimal('0')
        else:  # 'no'
            market.no_pool += shares_dec
            market.yes_pool = market.constant_k / market.no_pool if market.no_pool > 0 else Decimal('0')
        
        market.recalculate_prices()
        market.save(update_fields=['yes_pool', 'no_pool', 'yes_price', 'no_price'])
        
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
