from django.urls import path
from . import views, api

app_name = 'casino'

urlpatterns = [
    path('', views.index, name='index'),
    
    # Internal API for External Engines
    path('api/v1/sso-verify/', api.verify_sso, name='api_sso_verify'),
    path('api/v1/balance/', api.get_balance, name='api_balance'),
    path('api/v1/bet/', api.place_bet, name='api_bet'),
    path('api/v1/win/', api.record_win, name='api_win'),
    
    path('crash/', views.crash, name='crash'),
    path('crash/play/', views.crash_play, name='crash_play'),
    path('slots/', views.slots, name='slots'),
    path('slots/play/', views.slots_play, name='slots_play'),
    path('roulette/', views.roulette, name='roulette'),
    path('roulette/play/', views.roulette_play, name='roulette_play'),
    path('mines/', views.mines, name='mines'),
    path('mines/start/', views.mines_start, name='mines_start'),
    path('mines/reveal/', views.mines_reveal, name='mines_reveal'),
    path('mines/cashout/', views.mines_cashout, name='mines_cashout'),
    path('dice/', views.dice, name='dice'),
    path('dice/play/', views.dice_play, name='dice_play'),
    path('dice/calculate/', views.dice_calculate, name='dice_calculate'),
    path('plinko/', views.plinko, name='plinko'),
    path('plinko/play/', views.plinko_play, name='plinko_play'),
    path('fairness/', views.fairness, name='fairness'),
    path('fairness/verify/', views.fairness_verify, name='fairness_verify'),
    path('fairness/change-seed/', views.fairness_change_seed, name='fairness_change_seed'),
    path('fairness/change-client-seed/', views.fairness_change_client_seed, name='fairness_change_client_seed'),
    path('history/', views.history, name='history'),
    path('game/<str:game>/server', views.game_proxy, name='game_proxy'),
    path('<str:game_id>/', views.local_game_play, name='local_game_play'),
]
