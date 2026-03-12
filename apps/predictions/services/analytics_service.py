from decimal import Decimal

from django.db.models import Sum, Count, F, Q, Case, When, DecimalField
from django.utils import timezone
from django.contrib.auth import get_user_model

from ..models import Position, Trade, PredictionMarket, PriceHistory

User = get_user_model()


class AnalyticsService:
    """
    Аналитика, портфель, графики, лидерборд.
    """

    @staticmethod
    def get_user_portfolio(user):
        """
        Портфель пользователя.
        """
        positions = Position.objects.filter(
            user=user
        ).select_related('market').order_by('-updated_at')

        active_positions = []
        settled_positions = []
        total_invested = Decimal('0')
        total_returned = Decimal('0')
        total_realized_pnl = Decimal('0')
        total_current_value = Decimal('0')

        for position in positions:
            invested = position.total_invested
            returned = position.total_returned
            realized_pnl = position.realized_pnl
            
            # Рассчитать текущую стоимость позиции
            if position.side == 'yes':
                current_price = position.market.yes_price
            else:
                current_price = position.market.no_price
                
            current_value = position.shares * current_price
            unrealized_pnl = current_value - invested + returned
            total_pnl = realized_pnl + unrealized_pnl
            
            if invested > 0:
                pnl_percent = (total_pnl / invested * 100)
            else:
                pnl_percent = Decimal('0')

            position_data = {
                "market": position.market.question[:50],
                "market_id": str(position.market.id),
                "side": position.side,
                "shares": float(position.shares),
                "avg_price": float(position.avg_price),
                "invested": float(invested),
                "returned": float(returned),
                "realized_pnl": float(realized_pnl),
                "current_value": float(current_value),
                "unrealized_pnl": float(unrealized_pnl),
                "total_pnl": float(total_pnl),
                "pnl_percent": float(pnl_percent),
                "potential_payout": float(position.shares),
                "is_settled": position.is_settled,
                "settlement_amount": float(position.settlement_amount) if position.settlement_amount else 0,
            }

            total_invested += invested
            total_returned += returned
            total_realized_pnl += realized_pnl

            if position.is_settled:
                settled_positions.append(position_data)
            else:
                active_positions.append(position_data)
                total_current_value += current_value

        total_pnl = total_realized_pnl + (total_current_value - total_invested + total_returned)
        if total_invested > 0:
            total_pnl_percent = (total_pnl / total_invested * 100)
        else:
            total_pnl_percent = Decimal('0')

        # Win rate from settled positions with positive pnl
        settled_positions_count = len(settled_positions)
        winning_positions = sum(1 for pos in settled_positions if pos['total_pnl'] > 0)
        win_rate = (winning_positions / settled_positions_count * 100) if settled_positions_count > 0 else 0

        # Total trades count
        total_trades = Trade.objects.filter(user=user).count()

        return {
            "total_invested": float(total_invested),
            "total_returned": float(total_returned),
            "current_value": float(total_current_value),
            "total_pnl": float(total_pnl),
            "total_pnl_percent": float(total_pnl_percent),
            "realized_pnl": float(total_realized_pnl),
            "unrealized_pnl": float(total_current_value - total_invested + total_returned),
            "active_positions": active_positions,
            "settled_positions": settled_positions,
            "total_trades": total_trades,
            "win_rate": float(win_rate),
        }

    @staticmethod
    def get_market_chart_data(market_id, period='7d'):
        """
        Данные для графика цены.
        """
        try:
            market = PredictionMarket.objects.get(id=market_id)
        except PredictionMarket.DoesNotExist:
            return {"error": "Market not found"}

        # Parse period
        if period == '1d':
            hours = 24
        elif period == '7d':
            hours = 168
        elif period == '30d':
            hours = 720
        elif period == '90d':
            hours = 2160
        else:  # 'all'
            hours = None

        queryset = PriceHistory.objects.filter(market=market)
        if hours:
            since = timezone.now() - timezone.timedelta(hours=hours)
            queryset = queryset.filter(timestamp__gte=since)

        data = queryset.order_by('timestamp').values_list(
            'timestamp', 'yes_price', 'no_price', 'volume'
        )

        timestamps = []
        yes_prices = []
        no_prices = []
        volumes = []

        for timestamp, yes_price, no_price, volume in data:
            timestamps.append(timestamp.isoformat())
            yes_prices.append(float(yes_price))
            no_prices.append(float(no_price))
            volumes.append(float(volume))

        return {
            "timestamps": timestamps,
            "yes_prices": yes_prices,
            "no_prices": no_prices,
            "volumes": volumes,
        }

    @staticmethod
    def get_leaderboard(period='all', limit=50):
        """
        Таблица лидеров.
        """
        users_with_pnl = []

        # Get all users with trades
        users = User.objects.filter(
            position__isnull=False
        ).distinct()

        for user in users:
            portfolio = AnalyticsService.get_user_portfolio(user)
            
            if portfolio['total_pnl'] != 0:
                roi = (portfolio['total_pnl_percent']) if portfolio['total_invested'] > 0 else 0
                
                users_with_pnl.append({
                    "user_id": str(user.id),
                    "username": user.username,
                    "avatar": user.profile.avatar.url if hasattr(user, 'profile') and user.profile.avatar else None,
                    "pnl": portfolio['total_pnl'],
                    "roi": roi,
                    "trades": portfolio['total_trades'],
                    "invested": portfolio['total_invested'],
                    "current": portfolio['current_value'],
                    "win_rate": portfolio['win_rate'],
                })

        # Sort by ROI desc
        users_with_pnl.sort(key=lambda x: x['roi'], reverse=True)

        leaderboard = []
        for i, user_data in enumerate(users_with_pnl[:limit], 1):
            leaderboard.append({
                "rank": i,
                "user_id": user_data['user_id'],
                "username": user_data['username'],
                "avatar": user_data['avatar'],
                "pnl": round(user_data['pnl'], 2),
                "roi": round(user_data['roi'], 2),
                "trades": user_data['trades'],
                "invested": round(user_data['invested'], 2),
                "current": round(user_data['current'], 2),
                "win_rate": round(user_data['win_rate'], 2),
            })

        return leaderboard

    @staticmethod
    def get_market_activity(market_id, limit=50):
        """
        Активность маркета: последние операции.
        """
        try:
            market = PredictionMarket.objects.get(id=market_id)
        except PredictionMarket.DoesNotExist:
            return []

        trades = Trade.objects.filter(
            market=market
        ).select_related('user').order_by('-created_at')[:limit]

        activity = []
        for trade in trades:
            activity.append({
                "type": "trade",
                "action": trade.action,
                "side": trade.side,
                "user": trade.user.username,
                "shares": float(trade.shares),
                "price": float(trade.price),
                "total": float(trade.total_cost),
                "timestamp": trade.created_at.isoformat()
            })

        return activity

    @staticmethod
    def get_user_trades(user, limit=50):
        """
        Все трейды пользователя.
        """
        trades = Trade.objects.filter(
            user=user
        ).select_related('market').order_by('-created_at')[:limit]

        result = []
        for trade in trades:
            result.append({
                "trade_id": trade.trade_id,
                "market": trade.market.question[:50],
                "market_id": str(trade.market.id),
                "action": trade.action,
                "side": trade.side,
                "shares": float(trade.shares),
                "price": float(trade.price),
                "total_cost": float(trade.total_cost),
                "fee_amount": float(trade.fee_amount),
                "timestamp": trade.created_at.isoformat()
            })

        return result

    @staticmethod
    def get_market_summary(market_id):
        """
        Краткая статистика маркета.
        """
        try:
            market = PredictionMarket.objects.get(id=market_id)
        except PredictionMarket.DoesNotExist:
            return None

        positions_count = Position.objects.filter(market=market, shares__gt=0).count()
        traders_count = Position.objects.filter(market=market, shares__gt=0).values('user').distinct().count()
        
        return {
            "market_id": str(market.id),
            "question": market.question,
            "yes_price": float(market.yes_price),
            "no_price": float(market.no_price),
            "volume_usd": float(market.volume_usd),
            "trades_count": market.trades_count,
            "positions_count": positions_count,
            "traders_count": traders_count,
            "status": market.status,
            "close_date": market.close_date.isoformat() if market.close_date else None,
        }
