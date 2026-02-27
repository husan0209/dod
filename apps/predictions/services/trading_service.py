import random
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.wallet.services.transaction_service import TransactionService

from .amm_service import AMMService
from ..models import Market, UserPosition, Trade


def generate_id(prefix):
    timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
    random6 = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=6))
    return f"{prefix}-{timestamp}-{random6}"


class TradingService:
    """
    Покупка и продажа акций.
    Связывает AMM с кошельком.
    """

    @staticmethod
    @transaction.atomic
    def buy_shares(user, market_id, side, amount, currency_code, ip_address):
        """
        Купить акции YES или NO.
        """
        # ВАЛИДАЦИЯ
        try:
            market = Market.objects.select_for_update().get(id=market_id)
        except Market.DoesNotExist:
            raise ValueError("Market not found")

        if not market.is_tradeable():
            raise ValueError("Market is not tradeable")

        settings = PredictionSettings.get_settings()
        if amount < settings.min_trade_amount_usd:
            raise ValueError(f"Minimum trade amount is ${settings.min_trade_amount_usd}")

        if amount > settings.max_trade_amount_usd:
            raise ValueError(f"Maximum trade amount is ${settings.max_trade_amount_usd}")

        if side not in ('yes', 'no'):
            raise ValueError("Invalid side")

        # Check balance
        if not user.wallet.has_sufficient_balance(currency_code, amount):
            raise ValueError("Insufficient balance")

        # Check position limit
        position, _ = Position.objects.get_or_create(
            user=user, market=market, side=side, defaults={'shares': Decimal('0'), 'avg_price': Decimal('0')}
        )
        if position.total_invested + amount > settings.max_position_usd:
            raise ValueError("Position would exceed maximum allowed")

        # РАССЧИТАТЬ КОМИССИЮ
        fee_percent = settings.trading_fee_percent
        fee = amount * fee_percent / 100
        net_amount = amount - fee

        # РАССЧИТАТЬ ПОКУПКУ (AMM)
        result = AMMService.execute_buy(market, side, net_amount)
        shares = Decimal(str(result['shares']))

        # СПИСАТЬ ДЕНЬГИ
        old_price = market.yes_price if side == 'yes' else market.no_price
        tx = TransactionService.withdraw(
            wallet=user.wallet,
            currency_code=currency_code,
            amount=amount,
            type='bet',
            description=f"Покупка {shares:.2f} {side.upper()} акций: {market.question[:50]}",
            reference_type='prediction_trade'
        )

        # ОБНОВИТЬ ПОЗИЦИЮ
        if position.shares == 0:
            position.avg_price = result['avg_price']
        else:
            total_shares = position.shares + shares
            position.avg_price = (
                (position.avg_price * position.shares + result['avg_price'] * shares) / total_shares
            )

        position.shares += shares
        position.total_invested += amount
        position.save()

        # СОЗДАТЬ TRADE
        trade = Trade.objects.create(
            trade_id=generate_id("TRD"),
            user=user,
            market=market,
            position=position,
            action='buy',
            side=side,
            shares=shares,
            price=result['avg_price'],
            total_cost=amount,
            fee_amount=fee,
            price_before=old_price,
            price_after=result[f'{side}_price_after'],
            yes_price_after=result['new_yes_price'],
            no_price_after=result['new_no_price'],
            transaction=tx,
            ip_address=ip_address
        )

        # ОБНОВИТЬ СТАТИСТИКУ
        market.volume_usd += amount
        market.trades_count += 1
        if user not in market.traders.all():  # Need to track unique traders
            market.unique_traders += 1
        market.save()

        # ЗАПИСАТЬ ИСТОРИЮ ЦЕН
        from ..models import PriceHistory
        PriceHistory.objects.create(
            market=market,
            yes_price=market.yes_price,
            no_price=market.no_price,
            volume=amount,
            source='trade'
        )

        return {
            "trade_id": trade.trade_id,
            "shares": shares,
            "avg_price": result['avg_price'],
            "total_cost": amount,
            "fee": fee,
            "new_yes_price": market.yes_price,
            "new_no_price": market.no_price,
            "position_shares": position.shares,
            "potential_payout": shares,
            "message": f"✅ Куплено {shares:.2f} {side.upper()} акций"
        }

    @staticmethod
    @transaction.atomic
    def sell_shares(user, market_id, side, shares, currency_code, ip_address):
        """
        Продать акции YES или NO.
        """
        try:
            market = PredictionMarket.objects.select_for_update().get(id=market_id)
        except PredictionMarket.DoesNotExist:
            raise ValueError("Market not found")

        if not market.is_tradeable():
            raise ValueError("Market is not tradeable")

        try:
            position = Position.objects.get(user=user, market=market, side=side)
        except Position.DoesNotExist:
            raise ValueError("No position found")

        if position.shares < shares:
            raise ValueError("Insufficient shares")

        # РАССЧИТАТЬ ПРОДАЖУ (AMM)
        result = AMMService.execute_sell(market, side, shares)
        payout = Decimal(str(result['payout']))

        # РАССЧИТАТЬ КОМИССИЮ
        settings = PredictionSettings.get_settings()
        fee_percent = settings.trading_fee_percent
        fee = payout * fee_percent / 100
        net_payout = payout - fee

        # ЗАЧИСЛИТЬ ДЕНЬГИ
        tx = TransactionService.deposit(
            wallet=user.wallet,
            currency_code=currency_code,
            amount=net_payout,
            type='win',
            description=f"Продажа {shares:.2f} {side.upper()} акций: {market.question[:50]}",
            reference_type='prediction_trade'
        )

        # ОБНОВИТЬ ПОЗИЦИЮ
        position.shares -= shares
        position.total_returned += net_payout
        
        # Реализованный PnL
        cost_basis = position.avg_price * shares
        position.realized_pnl += net_payout - cost_basis
        
        if position.shares <= 0:
            position.shares = 0
        
        position.save()

        # СОЗДАТЬ TRADE
        old_price = market.yes_price if side == 'yes' else market.no_price
        trade = Trade.objects.create(
            trade_id=generate_id("TRD"),
            user=user,
            market=market,
            position=position,
            action='sell',
            side=side,
            shares=shares,
            price=result['avg_price'],
            total_cost=-net_payout,  # Negative for sell
            fee_amount=fee,
            price_before=old_price,
            price_after=result[f'{side}_price_after'],
            yes_price_after=result['new_yes_price'],
            no_price_after=result['new_no_price'],
            transaction=tx,
            ip_address=ip_address
        )

        # ОБНОВИТЬ СТАТИСТИКУ
        market.volume_usd += payout  # Or net_payout?
        market.trades_count += 1
        market.save()

        # ЗАПИСАТЬ ИСТОРИЮ ЦЕН
        from ..models import PriceHistory
        PriceHistory.objects.create(
            market=market,
            yes_price=market.yes_price,
            no_price=market.no_price,
            volume=payout,
            source='trade'
        )

        return {
            "trade_id": trade.trade_id,
            "shares_sold": shares,
            "payout": net_payout,
            "avg_price": result['avg_price'],
            "fee": fee,
            "new_yes_price": market.yes_price,
            "new_no_price": market.no_price,
            "position_shares": position.shares,
            "message": f"✅ Продано {shares:.2f} {side.upper()} акций"
        }

    @staticmethod
    def preview_buy(market_id, side, amount):
        """
        Предпросмотр покупки (без выполнения).
        """
        try:
            market = PredictionMarket.objects.get(id=market_id)
            return AMMService.calculate_buy_price(market, side, amount)
        except PredictionMarket.DoesNotExist:
            raise ValueError("Market not found")

    @staticmethod
    def preview_sell(market_id, side, shares):
        """
        Предпросмотр продажи.
        """
        try:
            market = PredictionMarket.objects.get(id=market_id)
            return AMMService.calculate_sell_price(market, side, shares)
        except PredictionMarket.DoesNotExist:
            raise ValueError("Market not found")
