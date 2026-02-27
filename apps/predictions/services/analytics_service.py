from decimal import Decimal

from django.db.models import Sum, Count, F, Q, Case, When, DecimalField
from django.utils import timezone

from ..models import UserPosition, Trade, Market, PriceHistory


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
            current_value = position.current_value()
            unrealized_pnl = position.unrealized_pnl()
            total_pnl = position.total_pnl()
            pnl_percent = position.pnl_percent()

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
                "potential_payout": float(position.potential_payout()),
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
        total_pnl_percent = (total_pnl / total_invested * 100) if total_invested > 0 else 0

        # Win rate from trades
        trades = Trade.objects.filter(user=user)
        win_trades = trades.filter(action='sell', total_cost__lt=0).count()  # Sell with positive pnl
        total_trades = trades.count()
        win_rate = (win_trades / total_trades * 100) if total_trades > 0 else 0

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
        elif period == '1M':
            hours = 720
        elif period == '3M':
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
        # This is complex - need to aggregate pnl per user
        # For simplicity, use total pnl from positions and trades
        # In real implementation, might need a cached table

        users_with_pnl = []

        # Get all users with positions
        users = Position.objects.values('user').distinct()

        for user_dict in users:
            user_id = user_dict['user']
            portfolio = AnalyticsService.get_user_portfolio_by_id(user_id)
            
            if portfolio['total_pnl'] != 0:
                users_with_pnl.append({
                    "user_id": user_id,
                    "pnl": portfolio['total_pnl'],
                    "trades": portfolio['total_trades'],
                    "win_rate": portfolio['win_rate'],
                })

        # Sort by pnl desc
        users_with_pnl.sort(key=lambda x: x['pnl'], reverse=True)

        leaderboard = []
        for i, user_data in enumerate(users_with_pnl[:limit], 1):
            leaderboard.append({
                "rank": i,
                "user_id": user_data['user_id'],
                "pnl": round(user_data['pnl'], 2),
                "trades": user_data['trades'],
                "win_rate": round(user_data['win_rate'], 2),
            })

        return leaderboard

    @staticmethod
    def get_user_portfolio_by_id(user_id):
        """
        Helper to get portfolio by user id.
        """
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            user = User.objects.get(id=user_id)
            return AnalyticsService.get_user_portfolio(user)
        except User.DoesNotExist:
            return {
                "total_invested": 0,
                "total_returned": 0,
                "current_value": 0,
                "total_pnl": 0,
                "total_pnl_percent": 0,
                "realized_pnl": 0,
                "unrealized_pnl": 0,
                "active_positions": [],
                "settled_positions": [],
                "total_trades": 0,
                "win_rate": 0,
            }
