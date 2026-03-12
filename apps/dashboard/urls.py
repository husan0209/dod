from django.urls import path
from .views import main, api, users, finance, sports, casino, predictions

app_name = 'dashboard'

urlpatterns = [
    path('', main.dashboard_view, name='dashboard'),
    path('verify-2fa/', main.verify_2fa_view, name='verify-2fa'),
    path('api/stats/', api.stats_view, name='stats'),
    path('api/search/', api.global_search_view, name='global_search'),
    path('users/', users.user_list, name='users'),
    path('users/bulk/', users.users_bulk_action, name='users_bulk_action'),
    path('users/<uuid:user_id>/', users.user_detail, name='user_detail'),
    path('users/<uuid:user_id>/action/', users.user_action, name='user_action'),
    path('finance/', finance.finance_overview, name='finance'),
    path('finance/withdrawals/', finance.withdrawals_queue, name='finance_withdrawals'),
    path('finance/transactions/', finance.transactions_list, name='finance_transactions'),
    path('sports/', sports.sports_overview, name='sports'),
    path('casino/', casino.casino_overview, name='casino'),
    path('predictions/', predictions.predictions_overview, name='predictions'),
    path('logs/', main.logs_view, name='logs'),
]
