"""
URL маршруты для модуля ставок на спорт.
"""
from django.urls import path
from apps.sports import views

app_name = 'sports'

urlpatterns = [
    # Основные страницы
    path('', views.SportsListView.as_view(), name='sports_list'),
    path('<slug:slug>/', views.SportDetailView.as_view(), name='sport_detail'),
    path('events/upcoming/', views.EventsUpcomingView.as_view(), name='upcoming_events'),

    # Событие
    path('events/<uuid:event_id>/', views.EventDetailView.as_view(), name='event_detail'),

    # Ставки пользователя
    path('bets/', views.UserBetsView.as_view(), name='user_bets'),
    path('bets/<uuid:bet_id>/', views.BetDetailView.as_view(), name='bet_detail'),

    # API endpoints
    path('api/bets/single/', views.place_single_bet_api, name='api_single_bet'),
    path('api/bets/combo/', views.place_combo_bet_api, name='api_combo_bet'),
    path('api/bets/<uuid:bet_id>/cashout/', views.cashout_bet_api, name='api_cashout'),
    path('api/bet-slip/validate/', views.validate_bet_slip_api, name='api_validate_slip'),
    path('api/events/<uuid:event_id>/markets/', views.event_markets_api, name='api_event_markets'),
]
