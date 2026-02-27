from django.urls import path

from . import views

urlpatterns = [
    path('health/', views.health, name='accounts-health'),
    path('settings/telegram/', views.telegram_settings, name='telegram_settings'),
    path('api/link-telegram/', views.link_telegram, name='link_telegram'),
]
