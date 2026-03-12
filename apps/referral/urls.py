from django.urls import path

from . import views

app_name = 'referral'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('referrals/', views.referrals, name='referrals'),
    path('referrals/<uuid:referral_id>/', views.referral_detail, name='referral_detail'),
    path('commissions/', views.commissions, name='commissions'),
    path('payouts/', views.payouts, name='payouts'),
    path('promo/', views.promo, name='promo'),
    path('stats/', views.stats, name='stats'),
    path('settings/', views.settings, name='settings'),
    
    # API Endpoints
    path('api/stats/', views.api_referral_stats, name='api_stats'),
    path('api/promo-links/', views.api_promo_links, name='api_promo_links'),
    path('api/referrals/', views.api_referrals_data, name='api_referrals'),
]