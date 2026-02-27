from django.urls import path

from . import views

app_name = "wallet"

urlpatterns = [
    path("", views.wallet_overview, name="overview"),
    path("deposit/", views.deposit_view, name="deposit"),
    path("withdraw/", views.withdraw_view, name="withdraw"),
    path("conversion/", views.conversion_view, name="conversion"),
    path("transactions/", views.transactions_view, name="transactions"),
    path("transaction/<uuid:tx_id>/", views.transaction_detail_view, name="transaction_detail"),
    path("withdrawal/<uuid:request_id>/", views.withdrawal_status_view, name="withdrawal_status"),
    path("kyc/", views.kyc_start_view, name="kyc_start"),
]
