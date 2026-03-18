from django.urls import path

from . import views

app_name = "wallet"

urlpatterns = [
    path("", views.wallet_overview, name="overview"),
    path("deposit/", views.deposit_view, name="deposit"),
    path("withdraw/", views.withdraw_view, name="withdraw"),
    path("convert/", views.conversion_view, name="convert"),
    path("transactions/", views.transactions_view, name="transactions"),
    path("transactions/export/csv/", views.transactions_export_csv, name="transactions_export_csv"),
    path("transactions/export/xls/", views.transactions_export_xls, name="transactions_export_xls"),
    path("transaction/<uuid:tx_id>/", views.transaction_detail_view, name="transaction_detail"),
    path("withdrawal/<uuid:request_id>/", views.withdrawal_status_view, name="withdrawal_status"),
    path("kyc/", views.kyc_start_view, name="kyc_start"),
    path("kyc/form/", views.kyc_form_view, name="kyc_form"),
    path("withdraw/confirm/", views.withdraw_confirm_view, name="withdraw_confirm"),
    # HTMX/API endpoints
    path("api/navbar-balance/", views.api_navbar_balance, name="api_navbar_balance"),
    path("api/balances/", views.api_balances, name="api_balances"),
    path("api/primary-currency/", views.api_primary_currency, name="api_primary_currency"),
    path("api/conversion-preview/", views.api_conversion_preview, name="api_conversion_preview"),
    path("api/withdrawal-fee/", views.api_withdrawal_fee, name="api_withdrawal_fee"),
]
