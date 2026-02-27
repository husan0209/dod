from django.urls import path

from apps.payments import views

app_name = "payments"

urlpatterns = [
    path("webhooks/rukassa/", views.rukassa_webhook, name="rukassa_webhook"),
    path("webhooks/nowpayments/", views.nowpayments_webhook, name="nowpayments_webhook"),
    path("webhooks/nowpayments/payout/", views.nowpayments_payout_webhook, name="nowpayments_payout_webhook"),
]
