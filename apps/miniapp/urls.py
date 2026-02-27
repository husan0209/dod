from django.urls import path
from . import views

app_name = 'miniapp'

urlpatterns = [
    # Главная
    path('', views.home, name='home'),

    # Авторизация
    path('auth/link/', views.link_account, name='link-account'),
    path('auth/link/existing/', views.link_existing,
         name='link-existing'),
    path('auth/welcome/', views.welcome, name='welcome'),

    # Кошелёк
    path('wallet/', views.wallet_home, name='wallet'),
    path('wallet/deposit/', views.wallet_deposit,
         name='wallet-deposit'),
    path('wallet/withdraw/', views.wallet_withdraw,
         name='wallet-withdraw'),
    path('wallet/history/', views.wallet_history,
         name='wallet-history'),
    path('wallet/convert/', views.wallet_convert,
         name='wallet-convert'),

    # Спорт
    path('sports/', views.sports_home, name='sports'),
    path('sports/<slug:sport>/', views.sports_events,
         name='sports-events'),
    path('sports/event/<uuid:event_id>/', views.sports_event,
         name='sports-event'),
    path('sports/bet/', views.sports_place_bet,
         name='sports-bet'),
    path('sports/my-bets/', views.sports_my_bets,
         name='sports-my-bets'),

    # Казино
    path('casino/', views.casino_home, name='casino'),
    path('casino/<slug:game>/', views.casino_game,
         name='casino-game'),

    # Predictions
    path('predictions/', views.predictions_home,
         name='predictions'),
    path('predictions/<uuid:market_id>/',
         views.predictions_market, name='predictions-market'),
    path('predictions/trade/', views.predictions_trade,
         name='predictions-trade'),
    path('predictions/portfolio/', views.predictions_portfolio,
         name='predictions-portfolio'),

    # Профиль
    path('profile/', views.profile_home, name='profile'),
    path('profile/edit/', views.profile_edit,
         name='profile-edit'),
    path('profile/referral/', views.profile_referral,
         name='profile-referral'),
    path('profile/settings/', views.profile_settings,
         name='profile-settings'),

    # Поддержка
    path('support/', views.support_home, name='support'),
    path('support/new/', views.support_new_ticket,
         name='support-new'),
    path('support/faq/', views.support_faq,
         name='support-faq'),

    # API (JSON для HTMX и JS)
    path('api/balance/', views.api_balance,
         name='api-balance'),
    path('api/live-matches/', views.api_live_matches,
         name='api-live-matches'),
    path('api/notifications/', views.api_notifications,
         name='api-notifications'),
    path('api/theme/', views.api_theme, name='api-theme'),

    # Webhook бота
    path('bot/webhook/', views.bot_webhook,
         name='bot-webhook'),
]
