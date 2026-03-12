import random
from decimal import Decimal
from django.db import transaction
from django.utils import timezone

from apps.wallet.services.transaction_service import TransactionService
from .amm_service import AMMService
from ..models import PredictionMarket, Position, Trade, PriceHistory, PredictionSettings


def generate_id(prefix):
    """Генерировать уникальный ID."""
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
    def buy_shares(user, market_id, side, amount, currency_code='USD', ip_address=None):
        """
        Купить акции YES или NO.
        """
        try:
            market = PredictionMarket.objects.select_for_update().get(id=market_id)
        except PredictionMarket.DoesNotExist:
            raise ValueError("Маркет не найден")

        if not market.is_tradeable():
            raise ValueError("На этом маркете больше нельзя торговать")

        settings = PredictionSettings.get_settings()
        
        amount_dec = Decimal(str(amount))
        
        if amount_dec < settings.min_trade_amount_usd:
            raise ValueError(f"Минимальная сумма: ${settings.min_trade_amount_usd}")

        if amount_dec > settings.max_trade_amount_usd:
            raise ValueError(f"Максимальная сумма: ${settings.max_trade_amount_usd}")

        if side not in ('yes', 'no'):
            raise ValueError("Неверная сторона")

        # Проверить баланс
        try:
            wallet = user.wallet
        except:
            raise ValueError("У пользователя нет кошелька")

        wallet.refresh_from_db()
        if not wallet.has_sufficient_balance(currency_code, amount):
            raise ValueError("Недостаточно средств")

        # Проверить лимит позиции
        position, _ = Position.objects.get_or_create(
            user=user, market=market, side=side,
            defaults={'shares': Decimal('0'), 'avg_price': Decimal('0')}
        )
        
        if position.total_invested + amount_dec > settings.max_position_usd:
            raise ValueError("Позиция превышает максимально допустимый размер")

        # РАССЧИТАТЬ КОМИССИЮ
        fee_percent = settings.trading_fee_percent
        fee = (amount_dec * fee_percent / 100)
        net_amount = amount_dec - fee

        # РАССЧИТАТЬ ПОКУПКУ (AMM)
        old_yes_price = market.yes_price
        old_no_price = market.no_price
        old_price = old_yes_price if side == 'yes' else old_no_price
        
        result = AMMService.execute_buy(market, side, net_amount)
        shares = Decimal(str(result['shares']))

        # СПИСАТЬ ДЕНЬГИ
        try:
            tx = TransactionService.withdraw(
                wallet=wallet,
                currency_code=currency_code,
                amount=amount,
                type='bet',
                description=f"Покупка {shares:.2f} {side.upper()} акций: {market.question[:50]}",
                reference_type='prediction_trade'
            )
        except Exception as e:
            raise ValueError(f"Ошибка при списании средств: {str(e)}")

        # ОБНОВИТЬ ПОЗИЦИЮ
        if position.shares == Decimal('0'):
            position.avg_price = Decimal(str(result['avg_price']))
        else:
            total_shares = position.shares + shares
            position.avg_price = (
                (position.avg_price * position.shares + Decimal(str(result['avg_price'])) * shares) / total_shares
            )

        position.shares += shares
        position.total_invested += amount_dec
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
            price=Decimal(str(result['avg_price'])),
            total_cost=amount_dec,
            fee_amount=fee,
            price_before=old_price,
            price_after=Decimal(str(result['new_yes_price'])) if side == 'yes' else Decimal(str(result['new_no_price'])),
            yes_price_after=Decimal(str(result['new_yes_price'])),
            no_price_after=Decimal(str(result['new_no_price'])),
            transaction=tx,
            ip_address=ip_address
        )

        # ОБНОВИТЬ СТАТИСТИКУ МАРКЕТА
        market.volume_usd += amount_dec
        market.trades_count += 1
        market.save(update_fields=['volume_usd', 'trades_count'])

        # ЗАПИСАТЬ ИСТОРИЮ ЦЕН
        PriceHistory.objects.create(
            market=market,
            yes_price=market.yes_price,
            no_price=market.no_price,
            volume=amount_dec,
            source='trade'
        )

        return {
            "trade_id": trade.trade_id,
            "shares": float(round(shares, 2)),
            "avg_price": float(result['avg_price']),
            "total_cost": float(amount),
            "fee": float(round(fee, 2)),
            "new_yes_price": float(market.yes_price),
            "new_no_price": float(market.no_price),
            "position_shares": float(position.shares),
            "potential_payout": float(round(shares, 2)),
            "message": f"✅ Куплено {float(round(shares, 2)):.2f} {side.upper()} акций"
        }

    @staticmethod
    @transaction.atomic
    def sell_shares(user, market_id, side, shares, currency_code='USD', ip_address=None):
        """
        Продать акции YES или NO.
        """
        shares_dec = Decimal(str(shares))
        
        # ВАЛИДАЦИЯ
        try:
            market = PredictionMarket.objects.select_for_update().get(id=market_id)
        except PredictionMarket.DoesNotExist:
            raise ValueError("Маркет не найден")

        if not market.is_tradeable():
            raise ValueError("На этом маркете больше нельзя торговать")

        try:
            position = Position.objects.get(user=user, market=market, side=side)
        except Position.DoesNotExist:
            raise ValueError("У вас нет позиции на этом маркете")

        if position.shares < shares_dec or shares_dec <= 0:
            raise ValueError("Некорректное количество акций для продажи")

        settings = PredictionSettings.get_settings()

        # РАССЧИТАТЬ ПРОДАЖУ (AMM)
        old_yes_price = market.yes_price
        old_no_price = market.no_price
        old_price = old_yes_price if side == 'yes' else old_no_price
        
        result = AMMService.execute_sell(market, side, shares)
        payout = Decimal(str(result['payout']))

        # РАССЧИТАТЬ КОМИССИЮ
        fee_percent = settings.trading_fee_percent
        fee = (payout * fee_percent / 100)
        net_payout = payout - fee

        # ЗАЧИСЛИТЬ ДЕНЬГИ
        try:
            wallet = user.wallet
            tx = TransactionService.deposit(
                wallet=wallet,
                currency_code=currency_code,
                amount=float(net_payout),
                type='win',
                description=f"Продажа {shares_dec:.2f} {side.upper()} акций: {market.question[:50]}",
                reference_type='prediction_trade'
            )
        except Exception as e:
            raise ValueError(f"Ошибка при зачислении средств: {str(e)}")

        # ОБНОВИТЬ ПОЗИЦИЮ
        position.shares -= shares_dec
        position.total_returned += net_payout

        # Реализованный PnL
        cost_basis = position.avg_price * shares_dec
        position.realized_pnl += net_payout - cost_basis

        if position.shares <= 0:
            position.shares = Decimal('0')

        position.save()

        # СОЗДАТЬ TRADE (action='sell')
        trade = Trade.objects.create(
            trade_id=generate_id("TRD"),
            user=user,
            market=market,
            position=position,
            action='sell',
            side=side,
            shares=shares_dec,
            price=Decimal(str(result['avg_price'])),
            total_cost=payout,
            fee_amount=fee,
            price_before=old_price,
            price_after=Decimal(str(result['new_yes_price'])) if side == 'yes' else Decimal(str(result['new_no_price'])),
            yes_price_after=Decimal(str(result['new_yes_price'])),
            no_price_after=Decimal(str(result['new_no_price'])),
            transaction=tx,
            ip_address=ip_address
        )

        # ОБНОВИТЬ СТАТИСТИКУ МАРКЕТА
        market.volume_usd += payout
        market.trades_count += 1
        market.save(update_fields=['volume_usd', 'trades_count'])

        # ЗАПИСАТЬ ИСТОРИЮ ЦЕН
        PriceHistory.objects.create(
            market=market,
            yes_price=market.yes_price,
            no_price=market.no_price,
            volume=payout,
            source='trade'
        )

        return {
            "trade_id": trade.trade_id,
            "shares_sold": float(shares),
            "payout": float(round(payout, 2)),
            "fee": float(round(fee, 2)),
            "net_payout": float(round(net_payout, 2)),
            "new_yes_price": float(market.yes_price),
            "new_no_price": float(market.no_price),
            "position_shares": float(position.shares),
            "message": f"✅ Продано {float(shares):.2f} {side.upper()} акций. Получено: ${float(round(net_payout, 2)):.2f}"
        }

    @staticmethod
    def preview_buy(market_id, side, amount):
        """Предпросмотр покупки (без выполнения)."""
        try:
            market = PredictionMarket.objects.get(id=market_id)
        except PredictionMarket.DoesNotExist:
            raise ValueError("Маркет не найден")

        settings = PredictionSettings.get_settings()
        amount_dec = Decimal(str(amount))
        
        # Рассчитать комиссию
        fee = amount_dec * settings.trading_fee_percent / 100
        net_amount = amount_dec - fee
        
        preview = AMMService.calculate_buy_price(market, side, net_amount)
        preview['fee'] = float(fee)
        preview['total_with_fee'] = float(amount)
        
        return preview

    @staticmethod
    def preview_sell(market_id, side, shares):
        """Предпросмотр продажи (без выполнения)."""
        try:
            market = PredictionMarket.objects.get(id=market_id)
        except PredictionMarket.DoesNotExist:
            raise ValueError("Маркет не найден")

        settings = PredictionSettings.get_settings()
        
        preview = AMMService.calculate_sell_price(market, side, shares)
        
        payout = Decimal(str(preview['payout']))
        fee = payout * settings.trading_fee_percent / 100
        net_payout = payout - fee
        
        preview['fee'] = float(round(fee, 2))
        preview['net_payout'] = float(round(net_payout, 2))
        
        return preview

