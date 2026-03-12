"""
Views для модуля ставок на спорт.
"""
import logging
from datetime import timedelta

from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView, DetailView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.db.models import Q, Count, Sum
from django.utils.translation import gettext as _

from apps.sports.models import (
    Sport, Event, Market, Outcome, Bet, BetItem, League
)
from apps.sports.services.betting_service import BettingService, BettingError
from apps.sports.services.settlement_service import SettlementService
from apps.sports.services.cashout_service import CashoutService
from apps.sports.services.odds_service import OddsService

logger = logging.getLogger(__name__)


class SportsListView(ListView):
    """Список видов спорта с активными событиями"""
    model = Sport
    template_name = 'sports/sports_list.html'
    context_object_name = 'sports'
    paginate_by = 20

    def get_queryset(self):
        """Получить активные виды спорта с событиями"""
        return Sport.objects.filter(
            is_active=True
        ).annotate(
            active_events_count=Count(
                'events',
                filter=Q(events__status__in=['prematch', 'live'])
            )
        ).filter(
            active_events_count__gt=0
        ).order_by('-is_popular', 'sort_order')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Популярные события
        context['featured_events'] = Event.objects.filter(
            status='prematch',
            is_featured=True,
            start_time__gte=timezone.now()
        ).order_by('start_time')[:5]
        return context


class SportDetailView(DetailView):
    """Детальный вид спорта с лигами и событиями"""
    model = Sport
    template_name = 'sports/sport_detail.html'
    slug_field = 'slug'
    context_object_name = 'sport'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sport = self.object

        # Лиги этого спорта
        context['leagues'] = sport.leagues.filter(
            is_active=True
        ).annotate(
            upcoming_events=Count(
                'events',
                filter=Q(events__status__in=['scheduled', 'prematch'])
            )
        ).filter(
            upcoming_events__gt=0
        ).order_by('-is_popular', 'sort_order')

        # Ближайшие события
        context['upcoming_events'] = Event.objects.filter(
            sport=sport,
            status__in=['scheduled', 'prematch'],
            start_time__gte=timezone.now()
        ).order_by('start_time')[:20]

        # Топ события (по просмотрам и ставкам)
        context['featured_events'] = Event.objects.filter(
            sport=sport,
            status='prematch',
            is_featured=True,
            start_time__gte=timezone.now()
        ).order_by('start_time')

        return context


class EventDetailView(LoginRequiredMixin, DetailView):
    """Детальный вид события с маркетами, исходами и системой ставок"""
    model = Event
    template_name = 'sports/event_detail.html'
    pk_url_kwarg = 'event_id'
    context_object_name = 'event'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        event = self.object

        # Маркеты события
        context['markets'] = event.markets.filter(
            status__in=['open', 'suspended']
        ).select_related('market_type').prefetch_related('outcomes')

        # Главный маркет (обычно 1X2)
        context['main_market'] = event.markets.filter(
            status='open',
            is_main=True
        ).prefetch_related('outcomes').first()

        # Статистика события
        context['stats'] = {
            'bets_count': event.bets_count,
            'total_stake': float(event.total_stake),
            'markets_count': event.markets_count,
            'time_until_start': event.get_time_until_start(),
            'is_bettable': event.is_bettable(),
        }

        # История коэффициентов (для графиков)
        main_outcomes = context['main_market'].outcomes.all() if context['main_market'] else []
        for outcome in main_outcomes:
            outcome.odd_history = OddsService.get_odd_history(
                outcome.id, limit=10
            )

        # Пользовательские ставки на это событие
        if self.request.user.is_authenticated:
            context['user_bets'] = Bet.objects.filter(
                user=self.request.user,
                items__event=event,
                status='pending'
            ).distinct()

        return context


class EventsUpcomingView(ListView):
    """Список ближайших событий"""
    model = Event
    template_name = 'sports/events_upcoming.html'
    context_object_name = 'events'
    paginate_by = 50

    def get_queryset(self):
        """Получить ближайшие события"""
        now = timezone.now()
        return Event.objects.filter(
            status__in=['scheduled', 'prematch'],
            start_time__gte=now,
            start_time__lte=now + timedelta(days=7)
        ).select_related(
            'sport', 'league', 'home_team', 'away_team'
        ).order_by('start_time')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Группировать по датам
        events_by_date = {}
        for event in context['events']:
            date_key = event.start_time.date()
            if date_key not in events_by_date:
                events_by_date[date_key] = []
            events_by_date[date_key].append(event)
        context['events_by_date'] = events_by_date
        return context


class UserBetsView(LoginRequiredMixin, ListView):
    """Выводы пользователя"""
    model = Bet
    template_name = 'sports/user_bets.html'
    context_object_name = 'bets'
    paginate_by = 20

    def get_queryset(self):
        status = self.request.GET.get('status', '')
        queryset = Bet.objects.filter(user=self.request.user).prefetch_related(
            'items__event', 'items__market', 'items__outcome'
        ).order_by('-created_at')

        if status and status in ['pending', 'won', 'lost', 'void', 'cashed_out']:
            queryset = queryset.filter(status=status)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        bets = context['bets']

        # Статистика ставок
        context['stats'] = {
            'total_bets': Bet.objects.filter(user=self.request.user).count(),
            'pending_bets': Bet.objects.filter(
                user=self.request.user,
                status='pending'
            ).count(),
            'won_bets': Bet.objects.filter(
                user=self.request.user,
                status='won'
            ).count(),
            'lost_bets': Bet.objects.filter(
                user=self.request.user,
                status='lost'
            ).count(),
        }

        # Финансовая статистика
        stats = Bet.objects.filter(
            user=self.request.user,
            status__in=['won', 'lost', 'void']
        ).aggregate(
            total_stake=Sum('stake'),
            total_win=Sum('actual_win')
        )

        context['financial_stats'] = {
            'total_stake': stats['total_stake'] or 0,
            'total_win': stats['total_win'] or 0,
            'balance': (stats['total_win'] or 0) - (stats['total_stake'] or 0),
        }

        return context


class BetDetailView(LoginRequiredMixin, DetailView):
    """Детальный вид ставки"""
    model = Bet
    template_name = 'sports/bet_detail.html'
    pk_url_kwarg = 'bet_id'
    context_object_name = 'bet'

    def get_queryset(self):
        return Bet.objects.filter(user=self.request.user).prefetch_related(
            'items__event', 'items__market', 'items__outcome'
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        bet = self.object

        # Информация о кэшауте
        context['cashout_info'] = CashoutService.get_cashout_info(bet)

        return context


# =========================
# AJAX API ENDPOINTS
# =========================

@require_POST
def place_single_bet_api(request):
    """
    API для размещения одиночной ставки.
    POST /api/sports/bets/single/
    """
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Требуется авторизация'}, status=401)

    try:
        outcome_id = request.POST.get('outcome_id')
        stake = request.POST.get('stake')
        currency_code = request.POST.get('currency', 'USD')

        result = BettingService.place_single_bet(
            user=request.user,
            outcome_id=outcome_id,
            stake=stake,
            currency_code=currency_code,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )

        return JsonResponse(result)

    except BettingError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    except Exception as e:
        logger.error(f"Ошибка при размещении ставки: {str(e)}")
        return JsonResponse(
            {'success': False, 'error': 'Внутренняя ошибка сервера'},
            status=500
        )


@require_POST
def place_combo_bet_api(request):
    """
    API для размещения экспресс ставки.
    POST /api/sports/bets/combo/
    """
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Требуется авторизация'}, status=401)

    try:
        import json
        data = json.loads(request.body)

        items = data.get('items', [])
        stake = data.get('stake')
        currency_code = data.get('currency', 'USD')

        result = BettingService.place_combo_bet(
            user=request.user,
            items=items,
            stake=stake,
            currency_code=currency_code,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )

        return JsonResponse(result)

    except BettingError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    except Exception as e:
        logger.error(f"Ошибка при размещении экспресса: {str(e)}")
        return JsonResponse(
            {'success': False, 'error': 'Внутренняя ошибка сервера'},
            status=500
        )


@require_POST
def cashout_bet_api(request):
    """
    API для кэшаута ставки.
    POST /api/sports/bets/{bet_id}/cashout/
    """
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Требуется авторизация'}, status=401)

    try:
        bet_id = request.POST.get('bet_id')
        result = CashoutService.place_cashout(bet_id, request.user)
        return JsonResponse(result)

    except Exception as e:
        logger.error(f"Ошибка при кэшауте: {str(e)}")
        return JsonResponse(
            {'success': False, 'error': str(e)},
            status=400
        )


@require_GET
def validate_bet_slip_api(request):
    """
    API для валидации купона перед размещением.
    GET /api/sports/bet-slip/validate/
    """
    import json

    try:
        items_json = request.GET.get('items', '[]')
        items = json.loads(items_json)

        result = BettingService.validate_bet_slip(items)
        return JsonResponse(result)

    except Exception as e:
        logger.error(f"Ошибка при валидации купона: {str(e)}")
        return JsonResponse(
            {'success': False, 'error': 'Ошибка при валидации'},
            status=400
        )


@require_GET
def event_markets_api(request, event_id):
    """
    API получения маркетов события.
    GET /api/sports/events/{event_id}/markets/
    """
    try:
        event = get_object_or_404(Event, id=event_id)

        markets_data = []
        for market in event.markets.filter(status='open'):
            outcomes = []
            for outcome in market.outcomes.filter(is_active=True):
                outcomes.append({
                    'id': str(outcome.id),
                    'code': outcome.code,
                    'name': outcome.name,
                    'odd': float(outcome.odd),
                })

            markets_data.append({
                'id': str(market.id),
                'name': market.name,
                'type': market.market_type.code,
                'parameter': float(market.parameter) if market.parameter else None,
                'outcomes': outcomes,
            })

        return JsonResponse({
            'success': True,
            'event_id': str(event_id),
            'markets': markets_data,
        })

    except Exception as e:
        logger.error(f"Ошибка при получении маркетов: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

