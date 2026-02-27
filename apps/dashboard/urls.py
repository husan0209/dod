from django.urls import path
from .views import main, api, users, finance, sports, casino, predictions

app_name = 'dashboard'

urlpatterns = [
    path('', main.dashboard_view, name='dashboard'),
    path('api/stats/', api.stats_view, name='stats'),
    path('api/search/', api.global_search_view, name='global_search'),
    path('users/', users.user_list, name='users'),
    path('users/<int:user_id>/', users.user_detail, name='user_detail'),
    path('finance/', finance.finance_overview, name='finance'),
    path('finance/withdrawals/', finance.withdrawals_queue, name='finance_withdrawals'),
    path('finance/transactions/', finance.transactions_list, name='finance_transactions'),
    path('sports/', sports.sports_overview, name='sports'),
    path('casino/', casino.casino_overview, name='casino'),
    path('predictions/', predictions.predictions_overview, name='predictions'),
]
