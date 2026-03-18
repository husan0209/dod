from django.urls import path
from .views import main, api, users, finance, sports, casino, predictions, settings, analytics

app_name = 'dashboard'

urlpatterns = [
    # Main
    path('', main.dashboard_view, name='dashboard'),
    path('verify-2fa/', main.verify_2fa_view, name='verify-2fa'),
    path('logs/', main.logs_view, name='logs'),
    path('logs/<int:log_id>/', main.log_detail, name='log_detail'),

    # API
    path('api/stats/', api.stats_view, name='stats'),
    path('api/search/', api.global_search_view, name='global_search'),

    # Users
    path('users/', users.user_list, name='users'),
    path('users/bulk/', users.users_bulk_action, name='users_bulk_action'),
    path('users/<uuid:user_id>/', users.user_detail, name='user_detail'),
    path('users/<uuid:user_id>/action/', users.user_action, name='user_action'),

    # Finance
    path('finance/', finance.finance_overview, name='finance'),
    path('finance/withdrawals/', finance.withdrawals_queue, name='finance_withdrawals'),
    path('finance/withdrawals/<uuid:withdrawal_id>/action/', finance.withdrawal_action, name='finance_withdrawal_action'),
    path('finance/transactions/', finance.transactions_list, name='finance_transactions'),
    path('finance/transactions/export/', finance.transactions_export, name='finance_transactions_export'),

    # Sports
    path('sports/', sports.sports_overview, name='sports'),
    path('sports/events/', sports.events_list, name='sports_events'),
    path('sports/events/<uuid:event_id>/', sports.event_detail, name='sports_event_detail'),
    path('sports/events/<uuid:event_id>/settle/', sports.event_settle, name='sports_event_settle'),
    path('sports/bets/', sports.bets_list, name='sports_bets'),

    # Casino
    path('casino/', casino.casino_overview, name='casino'),
    path('casino/rounds/', casino.rounds_list, name='casino_rounds'),
    path('casino/crash/', casino.crash_history, name='casino_crash'),

    # Predictions
    path('predictions/', predictions.predictions_overview, name='predictions'),
    path('predictions/markets/', predictions.markets_list, name='predictions_markets'),
    path('predictions/markets/<uuid:market_id>/', predictions.market_detail, name='predictions_market_detail'),
    path('predictions/markets/<uuid:market_id>/resolve/', predictions.market_resolve, name='predictions_market_resolve'),

    # Content
    path('content/banners/', settings.banners_list, name='banners_list'),
    path('content/banners/create/', settings.banner_create, name='banner_create'),
    path('content/promotions/', settings.promotions_list, name='promotions_list'),
    path('content/pages/', settings.static_pages_list, name='static_pages_list'),
    path('content/pages/<uuid:page_id>/edit/', settings.static_page_edit, name='static_page_edit'),

    # Settings
    path('settings/platform/', settings.platform_settings, name='platform_settings'),
    path('settings/roles/', settings.roles_list, name='roles_list'),
    path('settings/roles/<uuid:role_id>/', settings.role_detail, name='role_detail'),

    # Analytics
    path('analytics/', analytics.analytics_overview, name='analytics_overview'),
    path('analytics/financial/', analytics.financial_report, name='analytics_financial'),
    path('analytics/users/', analytics.user_analytics, name='analytics_users'),
]
