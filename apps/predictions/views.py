import json
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.http import require_POST
from django.views.generic import ListView, DetailView, TemplateView
from django.utils import timezone
from datetime import timedelta

from .models import (
    PredictionMarket, MarketCategory, MarketComment, MarketLike,
    Trade, Position, CommentLike
)
from .services.market_service import MarketService
from .services.trading_service import TradingService
from .services.analytics_service import AnalyticsService


# ════════════════════════════════════════════════════════════════════
# VIEW CLASSES
# ════════════════════════════════════════════════════════════════════

class IndexView(ListView):
    """Главная страница с категориями и маркетами."""
    model = PredictionMarket
    template_name = 'predictions/index.html'
    context_object_name = 'markets'
    paginate_by = 20

    def get_queryset(self):
        queryset = PredictionMarket.objects.filter(status='active').select_related('category')

        category = self.request.GET.get('category')
        if category:
            queryset = queryset.filter(category_id=category)

        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(
                Q(question__icontains=query) |
                Q(description__icontains=query) |
                Q(tags__contains=query)
            )

        filter_type = self.request.GET.get('filter')
        if filter_type == 'trending':
            queryset = queryset.filter(is_trending=True)
        elif filter_type == 'closing_soon':
            soon = timezone.now() + timedelta(hours=48)
            queryset = queryset.filter(close_date__lte=soon)
        elif filter_type == 'resolved':
            queryset = PredictionMarket.objects.filter(status='resolved')

        return queryset.order_by('-is_featured', '-volume_24h_usd', '-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = MarketCategory.objects.filter(is_active=True).order_by('sort_order')
        context['selected_category'] = self.request.GET.get('category')
        context['query'] = self.request.GET.get('q')
        context['filter_type'] = self.request.GET.get('filter')
        context['total_volume'] = PredictionMarket.objects.aggregate(
            total=Sum('volume_usd')
        )['total'] or 0
        return context


class MarketDetailView(DetailView):
    """Детальная страница маркета."""
    model = PredictionMarket
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

        # Позиция пользователя
        if user.is_authenticated:
            yes_position = Position.objects.filter(user=user, market=market, side='yes').first()
            no_position = Position.objects.filter(user=user, market=market, side='no').first()
            context['user_yes_position'] = yes_position
            context['user_no_position'] = no_position

        # Последние сделки
        context['recent_trades'] = market.trades.order_by('-created_at')[:20]

        # Комментарии
        context['comments'] = market.comments.filter(is_deleted=False).order_by('-is_pinned', '-created_at')[:50]

        # Chart data
        context['chart_data'] = json.dumps(AnalyticsService.get_market_chart_data(str(market.id), '24h'))

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
    paginate_by = 100

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
        
        categories = MarketCategory.objects.filter(is_active=True)
        return render(request, self.template_name, {'categories': categories})

    def post(self, request):
        if not request.user.is_staff:
            return redirect('predictions:index')

        try:
            market = MarketService.create_market(
                title=request.POST['title'],
                description=request.POST['description'],
                category_id=request.POST['category'],
                close_date=request.POST['close_date'],
                initial_liquidity=Decimal(request.POST.get('initial_liquidity', 10000)),
                created_by=request.user,
                resolution_source=request.POST.get('resolution_source'),
                tags=json.loads(request.POST.get('tags', '[]')),
                title_en=request.POST.get('title_en'),
                description_en=request.POST.get('description_en'),
            )
            return redirect('predictions:market_detail', pk=market.id)
        except Exception as e:
            return render(request, self.template_name, {
                'error': str(e),
                'categories': MarketCategory.objects.filter(is_active=True)
            })


# ════════════════════════════════════════════════════════════════════
# API VIEWS
# ════════════════════════════════════════════════════════════════════

@login_required
@require_POST
def preview_buy(request):
    """Предпросмотр покупки."""
    try:
        market_id = request.POST.get('market_id')
        side = request.POST.get('side')
        amount = Decimal(request.POST.get('amount', 0))

        result = TradingService.preview_buy(market_id, side, amount)
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_POST
def preview_sell(request):
    """Предпросмотр продажи."""
    try:
        market_id = request.POST.get('market_id')
        side = request.POST.get('side')
        shares = Decimal(request.POST.get('shares', 0))

        result = TradingService.preview_sell(market_id, side, shares)
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_POST
def trade(request):
    """Выполнить сделку."""
    try:
        action = request.POST.get('action', 'buy')
        market_id = request.POST.get('market_id')
        side = request.POST.get('side')
        amount = Decimal(request.POST.get('amount', 0)) if action == 'buy' else None
        shares = Decimal(request.POST.get('shares', 0)) if action == 'sell' else None
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
        market = get_object_or_404(PredictionMarket, id=market_id)
        text = request.POST.get('text', '').strip()
        
        if not text or len(text) < 3:
            return JsonResponse({'error': 'Комментарий слишком короткий'}, status=400)

        user_position = request.POST.get('user_position')

        comment = MarketComment.objects.create(
            market=market,
            user=request.user,
            text=text,
            side_prediction=user_position if user_position in ('yes', 'no') else None,
        )

        # Update market comments count
        market.comments_count = market.comments.filter(is_deleted=False).count()
        market.save(update_fields=['comments_count'])

        # Return rendered comment
        html = render_to_string('predictions/components/comment.html', {'comment': comment})
        return JsonResponse({'success': True, 'html': html})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


def chart_data(request, market_id):
    """Данные для графика."""
    try:
        period = request.GET.get('period', '24h')
        data = AnalyticsService.get_market_chart_data(str(market_id), period)
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


def get_prices(request, market_id):
    """Текущие цены маркета."""
    try:
        market = get_object_or_404(PredictionMarket, id=market_id)
        return JsonResponse({
            'yes_price': str(market.yes_price),
            'no_price': str(market.no_price),
            'volume_24h': str(market.volume_24h_usd),
            'updated_at': market.updated_at.isoformat()
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_POST
def like_comment(request, comment_id):
    """Лайк к комментарию."""
    try:
        comment = get_object_or_404(MarketComment, id=comment_id)
        
        like, created = CommentLike.objects.get_or_create(
            comment=comment,
            user=request.user
        )
        
        if not created:
            like.delete()
            liked = False
        else:
            liked = True

        comment.likes_count = comment.liked_by.count()
        comment.save(update_fields=['likes_count'])

        return JsonResponse({
            'success': True,
            'liked': liked,
            'likes_count': comment.likes_count
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
