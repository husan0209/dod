from django.urls import path

from apps.payments import views

app_name = "payments"

urlpatterns = [
    # Deposit views
    path("deposit/", views.deposit_page, name="deposit_page"),
    path("deposit/create/", views.create_deposit, name="create_deposit"),
    path("deposit/crypto/<str:order_id>/", views.deposit_crypto, name="deposit_crypto"),
    path("deposit/status/<str:order_id>/", views.deposit_status, name="deposit_status"),
    path("deposit/success/", views.deposit_success, name="deposit_success"),
    path("deposit/failure/", views.deposit_failure, name="deposit_failure"),
    
    # Withdrawal views
    path("withdrawal/", views.withdrawal_page, name="withdrawal_page"),
    path("withdrawal/create/", views.create_withdrawal, name="create_withdrawal"),
    path("withdrawal/status/<str:request_id>/", views.withdrawal_status, name="withdrawal_status"),
    
    # Transaction history
    path("history/", views.transaction_history, name="transaction_history"),
    
    # Webhook endpoints
    path("webhooks/rukassa/", views.rukassa_webhook, name="rukassa_webhook"),
    path("webhooks/nowpayments/", views.nowpayments_webhook, name="nowpayments_webhook"),
    path("webhooks/nowpayments/payout/", views.nowpayments_payout_webhook, name="nowpayments_payout_webhook"),
]
