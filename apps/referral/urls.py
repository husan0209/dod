from django.urls import path

from . import views

app_name = 'referral'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('referrals/', views.referrals, name='referrals'),
    path('commissions/', views.commissions, name='commissions'),
    path('payouts/', views.payouts, name='payouts'),
    path('promo/', views.promo, name='promo'),
    path('stats/', views.stats, name='stats'),
    path('settings/', views.settings, name='settings'),
]