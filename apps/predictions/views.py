import json
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.http import require_POST
from django.views.generic import ListView, DetailView, TemplateView

from .models import Market, Category, Comment, Trade
from .services import MarketService, AnalyticsService, TradingService


class IndexView(ListView):
    """Главная страница с категориями и маркетами."""
    model = Market
    template_name = 'predictions/index.html'
    context_object_name = 'markets'
    paginate_by = 20

    def get_queryset(self):
        queryset = Market.objects.filter(status='active').select_related('category')

        category = self.request.GET.get('category')
        if category:
            queryset = queryset.filter(category_id=category)

        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(
                Q(title__icontains=query) |
                Q(description__icontains=query) |
                Q(tags__icontains=query)
            )

        filter_type = self.request.GET.get('filter')
        if filter_type == 'trending':
            queryset = MarketService.get_trending_markets()
        elif filter_type == 'closing_soon':
            queryset = MarketService.get_closing_soon()
        elif filter_type == 'resolved':
            queryset = MarketService.get_recently_resolved()

        return queryset.order_by('-is_featured', '-total_volume', '-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.filter(is_active=True).order_by('sort_order')
        context['selected_category'] = self.request.GET.get('category')
        context['query'] = self.request.GET.get('q')
        context['filter_type'] = self.request.GET.get('filter')
        return context


class MarketDetailView(DetailView):
    """Детальная страница маркета."""
    model = Market
    template_name = 'predictions/market_detail.html'
    context_object_name = 'market'

    def get_object(self):
        market = super().get_object()
        market.views_count += 1
        market.save(update_fields=['views_count'])
        return market

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        market = self.object
        user = self.request.user

        # Позиция пользователя - TODO: update for new UserPosition model
        if user.is_authenticated:
            # Placeholder - need to update for Outcome-based positions
            pass

        # Последние сделки
        context['recent_trades'] = market.trades.order_by('-created_at')[:20]

        # Комментарии
        context['comments'] = market.comments.filter(is_hidden=False).order_by('-created_at')[:50]

        return context


@method_decorator(login_required, name='dispatch')
class PortfolioView(TemplateView):
    """Портфель пользователя."""
    template_name = 'predictions/portfolio.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['portfolio'] = AnalyticsService.get_user_portfolio(self.request.user)
        return context


class LeaderboardView(ListView):
    """Таблица лидеров."""
    template_name = 'predictions/leaderboard.html'
    context_object_name = 'leaderboard'

    def get_queryset(self):
        period = self.request.GET.get('period', 'all')
        return AnalyticsService.get_leaderboard(period=period)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['period'] = self.request.GET.get('period', 'all')
        return context


@method_decorator(login_required, name='dispatch')
class HistoryView(ListView):
    """История сделок пользователя."""
    model = Trade
    template_name = 'predictions/history.html'
    context_object_name = 'trades'
    paginate_by = 50

    def get_queryset(self):
        return Trade.objects.filter(
            user=self.request.user
        ).select_related('market').order_by('-created_at')


@method_decorator(login_required, name='dispatch')
class CreateMarketView(View):
    """Создание маркета (модератор)."""
    template_name = 'predictions/create_market.html'

    def get(self, request):
        if not request.user.is_staff:
            return redirect('predictions:index')
        
        categories = Category.objects.filter(is_active=True)
        return render(request, self.template_name, {'categories': categories})

    def post(self, request):
        if not request.user.is_staff:
            return redirect('predictions:index')

        # Parse form data and create market
        # This is a placeholder - implement form validation
        try:
            market = MarketService.create_market(
                title=request.POST['title'],
                description=request.POST['description'],
                category_id=request.POST['category'],
                closes_at=request.POST['closes_at'],
                initial_liquidity=Decimal(request.POST['initial_liquidity']),
                created_by=request.user,
                resolution_source=request.POST.get('resolution_source'),
                tags=json.loads(request.POST.get('tags', '[]')),
                title_en=request.POST.get('title_en'),
                description_en=request.POST.get('description_en'),
            )
            return redirect('predictions:market_detail', pk=market.id)
        except Exception as e:
            return render(request, self.template_name, {'error': str(e)})


# HTMX API Views

@login_required
@require_POST
def preview_buy(request, market_id):
    """Предпросмотр покупки."""
    try:
        side = request.POST['side']
        amount = Decimal(request.POST['amount'])
        result = TradingService.preview_buy(market_id, side, amount)
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_POST
def preview_sell(request, market_id):
    """Предпросмотр продажи."""
    try:
        side = request.POST['side']
        shares = Decimal(request.POST['shares'])
        result = TradingService.preview_sell(market_id, side, shares)
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_POST
def trade(request, market_id):
    """Выполнить сделку."""
    try:
        action = request.POST['action']  # 'buy' or 'sell'
        side = request.POST['side']
        amount = Decimal(request.POST.get('amount', '0'))
        shares = Decimal(request.POST.get('shares', '0'))
        currency_code = request.POST.get('currency', 'USD')

        if action == 'buy':
            result = TradingService.buy_shares(
                user=request.user,
                market_id=market_id,
                side=side,
                amount=amount,
                currency_code=currency_code,
                ip_address=request.META.get('REMOTE_ADDR')
            )
        else:
            result = TradingService.sell_shares(
                user=request.user,
                market_id=market_id,
                side=side,
                shares=shares,
                currency_code=currency_code,
                ip_address=request.META.get('REMOTE_ADDR')
            )

        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_POST
def add_comment(request, market_id):
    """Добавить комментарий."""
    try:
        market = get_object_or_404(Market, id=market_id)
        text = request.POST['text']
        user_position = request.POST.get('user_position')
        parent_id = request.POST.get('parent_id')

        comment = Comment.objects.create(
            market=market,
            user=request.user,
            text=text,
            user_position=user_position,
            parent_id=parent_id if parent_id else None
        )

        # Update market comments count
        market.comments_count = market.comments.filter(is_hidden=False).count()
        market.save()

        return render(request, 'predictions/components/comment.html', {'comment': comment})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


def chart_data(request, market_id):
    """Данные для графика."""
    period = request.GET.get('period', '7d')
    data = AnalyticsService.get_market_chart_data(market_id, period)
    return JsonResponse(data)
