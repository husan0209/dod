from django.urls import path

from . import views

app_name = 'accounts'

urlpatterns = [
    # Authentication
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Email verification
    path('verify-email/pending/<uuid:user_id>/', views.email_verification_pending, name='email_verification_pending'),
    path('verify-email/<str:token>/', views.verify_email, name='verify_email'),
    
    # 2FA
    path('2fa/', views.verify_2fa, name='verify_2fa'),
    path('2fa/setup/', views.setup_2fa, name='setup_2fa'),
    path('2fa/disable/', views.disable_2fa, name='disable_2fa'),
    path('2fa/backup-codes/regenerate/', views.regenerate_backup_codes, name='regenerate_backup_codes'),
    
    # Phone verification
    path('phone/link/', views.link_phone, name='link_phone'),
    path('phone/verify/', views.verify_phone, name='verify_phone'),
    
    # Password management
    path('password/change/', views.change_password, name='change_password'),
    path('password/reset/', views.password_reset, name='password_reset'),
    path('password/reset/<str:token>/', views.reset_password_confirm, name='reset_password_confirm'),
    
    # Profile
    path('profile/', views.profile, name='profile'),
    path('security/', views.security_settings, name='security_settings'),
    path('unlink/<str:provider>/', views.unlink_account, name='unlink_account'),
]
