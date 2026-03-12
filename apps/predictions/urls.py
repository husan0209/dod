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

    # Trading API
    path('preview_buy/', views.preview_buy, name='preview_buy'),
    path('preview_sell/', views.preview_sell, name='preview_sell'),
    path('trade/', views.trade, name='trade'),
    path('add_comment/<uuid:market_id>/', views.add_comment, name='add_comment'),
    path('chart/<uuid:market_id>/', views.chart_data, name='chart_data'),
    
    # API endpoints for real-time data
    path('api/market/<uuid:market_id>/prices/', views.get_prices, name='get_prices'),
    path('api/comment/<uuid:comment_id>/like/', views.like_comment, name='like_comment'),
]
