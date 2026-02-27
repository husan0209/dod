from django.urls import path

from . import views

app_name = 'predictions'

urlpatterns = [
    # Main pages
    path('', views.IndexView.as_view(), name='index'),
    path('market/<uuid:pk>/', views.MarketDetailView.as_view(), name='market_detail'),
    path('portfolio/', views.PortfolioView.as_view(), name='portfolio'),
    path('leaderboard/', views.LeaderboardView.as_view(), name='leaderboard'),
    path('history/', views.HistoryView.as_view(), name='history'),
    path('create/', views.CreateMarketView.as_view(), name='create_market'),

    # HTMX API
    path('api/preview/buy/<uuid:market_id>/', views.preview_buy, name='preview_buy'),
    path('api/preview/sell/<uuid:market_id>/', views.preview_sell, name='preview_sell'),
    path('api/trade/<uuid:market_id>/', views.trade, name='trade'),
    path('api/comment/<uuid:market_id>/', views.add_comment, name='add_comment'),
    path('api/chart/<uuid:market_id>/', views.chart_data, name='chart_data'),
]
