import uuid
from django.db.models import Sum, Count, Avg, Q, F
from django.utils import timezone
from datetime import timedelta
from django.core.cache import cache

from apps.accounts.models import User
from apps.wallet.models import Transaction, WithdrawalRequest
from apps.sports.models import Bet
from apps.casino.models import GameSession
from apps.predictions.models import Trade


class AnalyticsService:
    """Service for calculating platform analytics and metrics."""

    @staticmethod
    def get_financial_summary(days=7):
        """High-level financial metrics."""
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        cache_key = f'analytics_financial_summary_{days}'
        data = cache.get(cache_key)
        if data: return data

        # Deposits & Withdrawals
        deposits = Transaction.objects.filter(
            type='deposit', 
            status='completed',
            created_at__range=(start_date, end_date)
        ).aggregate(total=Sum('amount_usd'))['total'] or 0

        withdrawals = WithdrawalRequest.objects.filter(
            status='completed',
            created_at__range=(start_date, end_date)
        ).aggregate(total=Sum('amount_usd'))['total'] or 0

        # Casino GGR (Bets - Wins)
        casino_stats = GameSession.objects.filter(
            created_at__range=(start_date, end_date)
        ).aggregate(
            total_bets=Sum('bet_amount_usd'),
            total_wins=Sum('win_amount_usd')
        )
        casino_ggr = (casino_stats['total_bets'] or 0) - (casino_stats['total_wins'] or 0)

        # Sports GGR
        sports_stats = Bet.objects.filter(
            created_at__range=(start_date, end_date),
            status='settled'
        ).aggregate(
            total_bets=Sum('amount_usd'),
            total_payouts=Sum('payout_usd')
        )
        sports_ggr = (sports_stats['total_bets'] or 0) - (sports_stats['total_payouts'] or 0)

        # Total Revenue (approx GGR)
        total_ggr = casino_ggr + sports_ggr
        
        data = {
            'deposits': float(deposits),
            'withdrawals': float(withdrawals),
            'casino_ggr': float(casino_ggr),
            'sports_ggr': float(sports_ggr),
            'total_ggr': float(total_ggr),
            'net_flow': float(deposits - withdrawals)
        }
        
        cache.set(cache_key, data, 300) # 5 min cache
        return data

    @staticmethod
    def get_user_activity(days=30):
        """User registration and activity metrics."""
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)

        new_users = User.objects.filter(date_joined__range=(start_date, end_date)).count()
        total_users = User.objects.count()
        
        # Active users (last activity in last 24h)
        active_24h = User.objects.filter(last_login__gte=end_date - timedelta(days=1)).count()
        
        return {
            'new_users': new_users,
            'total_users': total_users,
            'dau': active_24h,
            'conversion_rate': 0 # Placeholder for Reg -> Deposit conversion
        }

    @staticmethod
    def get_revenue_chart_data(days=14):
        """Time-series data for GGR chart."""
        end_date = timezone.now().date()
        days_list = []
        ggr_values = []
        
        for i in range(days, -1, -1):
            target_date = end_date - timedelta(days=i)
            days_list.append(target_date.strftime('%d.%m'))
            
            # Simplified daily GGR calculation
            c_ggr = GameSession.objects.filter(created_at__date=target_date).aggregate(
                ggr=Sum(F('bet_amount_usd') - F('win_amount_usd'))
            )['ggr'] or 0
            
            s_ggr = Bet.objects.filter(created_at__date=target_date, status='settled').aggregate(
                ggr=Sum(F('amount_usd') - F('payout_usd'))
            )['ggr'] or 0
            
            ggr_values.append(float(c_ggr + s_ggr))
            
        return {
            'labels': days_list,
            'values': ggr_values
        }
