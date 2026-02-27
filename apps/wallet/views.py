from django.http import HttpResponse


def wallet_overview(request):
    return HttpResponse("wallet overview placeholder")


def deposit_view(request):
    return HttpResponse("deposit placeholder")


def withdraw_view(request):
    return HttpResponse("withdraw placeholder")


def conversion_view(request):
    return HttpResponse("conversion placeholder")


def transactions_view(request):
    return HttpResponse("transactions placeholder")


def transaction_detail_view(request, tx_id):
    return HttpResponse(f"transaction {tx_id} placeholder")


def withdrawal_status_view(request, request_id):
    return HttpResponse(f"withdrawal {request_id} placeholder")


def kyc_start_view(request):
    return HttpResponse("kyc start placeholder")
