from decimal import Decimal
import pyotp

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.views.decorators.http import require_GET, require_POST
from django.utils import timezone

from apps.wallet.forms import KYCStep1Form, KYCStep2Form, KYCStep3Form
from apps.wallet.models import Currency, KYCVerification, Transaction, Wallet, WithdrawalRequest
from apps.wallet.services.conversion_service import ConversionService
from apps.wallet.services.transaction_service import TransactionService
from apps.wallet.services.withdrawal_service import WithdrawalService, WithdrawalValidationError
from apps.wallet.services.wallet_service import WalletService
from apps.payments.services.payment_service import PaymentService


@login_required
def wallet_overview(request: HttpRequest) -> HttpResponse:
    wallet = WalletService.create_wallet(request.user)
    balances = WalletService.get_all_balances(wallet)
    recent_tx = (
        Transaction.objects.filter(user=request.user)
        .select_related("currency")
        .order_by("-created_at")[:10]
    )
    pending_withdrawals = WithdrawalRequest.objects.filter(
        user=request.user,
        status__in=["pending", "manual_review", "auto_approved", "approved", "processing"],
    ).order_by("-created_at")[:5]
    context = {
        "wallet": wallet,
        "balances": balances,
        "recent_transactions": recent_tx,
        "pending_withdrawals": pending_withdrawals,
    }
    return render(request, "wallet/overview.html", context)


@login_required
def deposit_view(request: HttpRequest) -> HttpResponse:
    wallet = WalletService.create_wallet(request.user)
    currencies = Currency.objects.filter(is_active=True, is_deposit_enabled=True).order_by("sort_order", "code")
    selected_code = request.GET.get("currency", wallet.primary_currency_id or "USD")
    selected_currency = get_object_or_404(Currency, code=selected_code)
    error = None
    deposit_info = None

    available_methods = PaymentService.get_available_deposit_methods(request.user, currency_code=selected_currency.code)

    if request.method == "POST":
        code = request.POST.get("currency", selected_currency.code)
        selected_currency = get_object_or_404(Currency, code=code)
        amount_raw = request.POST.get("amount") or "0"
        provider_code = request.POST.get("provider")
        method_code = request.POST.get("method")
        try:
            amount = Decimal(amount_raw.replace(",", "."))
        except Exception:
            amount = Decimal("0")
        if amount <= 0:
            error = "Введите положительную сумму"
        elif not provider_code or not method_code:
            error = "Выберите способ оплаты"
        else:
            try:
                deposit_info = PaymentService.create_deposit(
                    user=request.user,
                    currency_code=selected_currency.code,
                    amount=amount,
                    provider_code=provider_code,
                    method_code=method_code,
                    ip_address=request.META.get("REMOTE_ADDR", ""),
                    user_agent=request.META.get("HTTP_USER_AGENT"),
                )
                payment_url = deposit_info.get("payment_url")
                if payment_url:
                    return redirect(payment_url)
            except Exception as exc:  # noqa: BLE001
                error = str(exc) or "Не удалось создать платёж"

    context = {
        "wallet": wallet,
        "currencies": currencies,
        "selected_currency": selected_currency,
        "error": error,
        "available_methods": available_methods,
        "deposit_info": deposit_info,
    }
    return render(request, "wallet/deposit.html", context)


@login_required
def withdraw_view(request: HttpRequest) -> HttpResponse:
    wallet = WalletService.create_wallet(request.user)
    balances = WalletService.get_all_balances(wallet)
    # показываем только валюты с доступным балансом > 0
    available_currencies = [b for b in balances if b["available"] > 0]
    if available_currencies:
        default_code = available_currencies[0]["currency"]
    else:
        default_code = wallet.primary_currency_id or "USD"
    selected_code = request.GET.get("currency", default_code)
    selected_currency = get_object_or_404(Currency, code=selected_code)

    error = None
    success = None
    created_request: WithdrawalRequest | None = None

    if request.method == "POST":
        code = request.POST.get("currency", selected_currency.code)
        selected_currency = get_object_or_404(Currency, code=code)
        amount_raw = request.POST.get("amount") or "0"
        payment_method = request.POST.get("payment_method") or "card"
        payment_details = {
            "card_number": request.POST.get("card_number", ""),
            "address": request.POST.get("address", ""),
            "network": request.POST.get("network", ""),
        }
        try:
            amount = Decimal(amount_raw.replace(",", "."))
        except Exception:
            amount = Decimal("0")
        
        # Если 2FA включена — требуем подтверждение
        if request.user.is_2fa_enabled:
            # Сохраняем данные в сессию для подтверждения
            request.session["withdrawal_pending"] = {
                "currency_code": selected_currency.code,
                "amount": str(amount),
                "payment_method": payment_method,
                "payment_details": payment_details,
                "ip_address": request.META.get("REMOTE_ADDR", ""),
                "user_agent": request.META.get("HTTP_USER_AGENT", ""),
                "created_at": timezone.now().isoformat(),
            }
            request.session.modified = True
            return redirect("wallet:withdraw_confirm")
        
        # Если 2FA не включена — создаём заявку сразу
        try:
            created_request = WithdrawalService.create_withdrawal_request(
                wallet,
                currency_code=selected_currency.code,
                amount=amount,
                payment_method=payment_method,
                payment_details=payment_details,
                ip_address=request.META.get("REMOTE_ADDR", ""),
                user_agent=request.META.get("HTTP_USER_AGENT"),
            )
            success = "Заявка на вывод создана"
        except (WithdrawalValidationError, Exception) as exc:  # noqa: BLE001
            error = str(exc) or "Не удалось создать заявку на вывод"

    context = {
        "wallet": wallet,
        "balances": balances,
        "available_currencies": available_currencies,
        "selected_currency": selected_currency,
        "error": error,
        "success": success,
        "created_request": created_request,
    }
    return render(request, "wallet/withdraw.html", context)


@login_required
def conversion_view(request: HttpRequest) -> HttpResponse:
    wallet = WalletService.create_wallet(request.user)
    balances = WalletService.get_all_balances(wallet)
    all_codes = [b["currency"] for b in balances] or ["USD"]
    from_code = request.GET.get("from", wallet.primary_currency_id or all_codes[0])
    to_code = request.GET.get("to", "USD" if from_code != "USD" else all_codes[0])
    preview = None
    error = None
    success = None

    if request.method == "POST":
        from_code = request.POST.get("from_currency", from_code)
        to_code = request.POST.get("to_currency", to_code)
        amount_raw = request.POST.get("amount") or "0"
        try:
            amount = Decimal(amount_raw.replace(",", "."))
        except Exception:
            amount = Decimal("0")
        try:
            order = ConversionService.execute_conversion(wallet, from_code, to_code, amount)
            success = "Конвертация успешно выполнена"
            preview = {
                "from_currency": from_code,
                "to_currency": to_code,
                "from_amount": amount,
                "to_amount": order.to_amount,
                "exchange_rate": order.exchange_rate,
                "fee_percent": order.fee_percent,
                "fee_amount": order.fee_amount,
            }
        except Exception as exc:  # noqa: BLE001
            error = str(exc) or "Не удалось выполнить конвертацию"

    context = {
        "wallet": wallet,
        "balances": balances,
        "from_code": from_code,
        "to_code": to_code,
        "preview": preview,
        "error": error,
        "success": success,
    }
    return render(request, "wallet/conversion.html", context)


@login_required
def transactions_view(request: HttpRequest) -> HttpResponse:
    from django.core.paginator import Paginator

    wallet = WalletService.create_wallet(request.user)
    tx_type = request.GET.get("type") or ""
    currency_code = request.GET.get("currency") or ""
    period = request.GET.get("period") or "7"
    search_q = request.GET.get("q") or ""

    qs = Transaction.objects.filter(user=request.user).select_related("currency")
    if tx_type:
        qs = qs.filter(type=tx_type)
    if currency_code:
        qs = qs.filter(currency_id=currency_code)
    if search_q:
        from django.db.models import Q
        qs = qs.filter(Q(transaction_id__icontains=search_q) | Q(description__icontains=search_q))
    try:
        days = int(period)
    except ValueError:
        days = 7

    qs = qs.filter(created_at__gte=timezone.now() - timezone.timedelta(days=days)).order_by("-created_at")

    paginator = Paginator(qs, 20)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    # All currencies for filter dropdown
    all_currencies = Currency.objects.filter(is_active=True).order_by("sort_order", "code")

    context = {
        "wallet": wallet,
        "transactions": page_obj,
        "page_obj": page_obj,
        "paginator": paginator,
        "selected_type": tx_type,
        "selected_currency": currency_code,
        "selected_period": str(days),
        "search_q": search_q,
        "all_currencies": all_currencies,
    }
    template_name = "wallet/transactions_table.html" if request.headers.get("HX-Request") else "wallet/transactions.html"
    return render(request, template_name, context)


@login_required
def transactions_export_csv(request: HttpRequest) -> HttpResponse:
    """
    Экспорт транзакций пользователя в CSV.
    Фильтры такие же, как на странице /wallet/transactions/.
    """
    wallet = WalletService.create_wallet(request.user)
    tx_type = request.GET.get("type") or ""
    currency_code = request.GET.get("currency") or ""
    period = request.GET.get("period") or "30"

    qs = Transaction.objects.filter(user=request.user).select_related("currency")
    if tx_type:
        qs = qs.filter(type=tx_type)
    if currency_code:
        qs = qs.filter(currency_id=currency_code)
    from django.utils import timezone
    import csv

    try:
        days = int(period)
    except ValueError:
        days = 30
    qs = qs.filter(created_at__gte=timezone.now() - timezone.timedelta(days=days)).order_by("-created_at")

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="transactions.csv"'
    writer = csv.writer(response)
    writer.writerow(["Дата", "Тип", "Валюта", "Сумма", "Баланс до", "Баланс после", "Описание"])
    for tx in qs:
        writer.writerow(
            [
                tx.created_at.isoformat(sep=" "),
                tx.get_type_display(),
                tx.currency_id,
                tx.get_signed_amount(),
                tx.balance_before,
                tx.balance_after,
                (tx.description or "").replace("\n", " "),
            ]
        )
    return response


@login_required
def transactions_export_xls(request: HttpRequest) -> HttpResponse:
    """
    Простой Excel-совместимый экспорт (tab-separated, но с Excel MIME-типом).
    """
    from django.utils import timezone

    wallet = WalletService.create_wallet(request.user)
    tx_type = request.GET.get("type") or ""
    currency_code = request.GET.get("currency") or ""
    period = request.GET.get("period") or "30"

    qs = Transaction.objects.filter(user=request.user).select_related("currency")
    if tx_type:
        qs = qs.filter(type=tx_type)
    if currency_code:
        qs = qs.filter(currency_id=currency_code)
    try:
        days = int(period)
    except ValueError:
        days = 30
    qs = qs.filter(created_at__gte=timezone.now() - timezone.timedelta(days=days)).order_by("-created_at")

    response = HttpResponse(
        content_type="application/vnd.ms-excel; charset=utf-8",
    )
    response["Content-Disposition"] = 'attachment; filename="transactions.xls"'
    lines = ["Дата\tТип\tВалюта\tСумма\tБаланс до\tБаланс после\tОписание"]
    for tx in qs:
        line = "\t".join(
            [
                tx.created_at.isoformat(sep=" "),
                tx.get_type_display(),
                tx.currency_id,
                str(tx.get_signed_amount()),
                str(tx.balance_before),
                str(tx.balance_after),
                (tx.description or "").replace("\n", " "),
            ]
        )
        lines.append(line)
    response.write("\n".join(lines))
    return response


@login_required
def transaction_detail_view(request: HttpRequest, tx_id) -> HttpResponse:
    tx = get_object_or_404(Transaction, id=tx_id, user=request.user)
    return render(request, "wallet/transaction_detail.html", {"transaction": tx})


@login_required
def withdrawal_status_view(request: HttpRequest, request_id) -> HttpResponse:
    wd = get_object_or_404(WithdrawalRequest, id=request_id, user=request.user)
    return render(request, "wallet/withdrawal_status.html", {"withdrawal": wd})


@login_required
def kyc_start_view(request: HttpRequest) -> HttpResponse:
    kyc = KYCVerification.objects.filter(user=request.user).first() or KYCVerification(user=request.user)
    # Если уже подана или одобрена — показываем статус
    if kyc.status in {"pending", "approved"}:
        return render(request, "wallet/kyc/kyc_status.html", {"kyc": kyc})
    # Иначе предлагаем начать верификацию
    return render(request, "wallet/kyc/kyc_start.html", {"kyc": kyc})


@login_required
def kyc_form_view(request: HttpRequest) -> HttpResponse:
    kyc = KYCVerification.objects.filter(user=request.user).first() or KYCVerification(user=request.user)
    step = int(request.GET.get("step", "1"))
    if kyc.status == "approved":
        return render(request, "wallet/kyc/kyc_status.html", {"kyc": kyc})

    if request.method == "POST":
        step = int(request.POST.get("step", step))
        if kyc.pk is None:
            step = 1
        if step == 1:
            form = KYCStep1Form(request.POST, instance=kyc)
            if form.is_valid():
                form.save()
                kyc.status = "pending"
                kyc.save(update_fields=["status"])
                return render(
                    request,
                    "wallet/kyc/kyc_form.html",
                    {"form": KYCStep2Form(instance=kyc), "step": 2},
                )
        elif step == 2:
            form = KYCStep2Form(request.POST, request.FILES, instance=kyc)
            if form.is_valid():
                form.save()
                return render(
                    request,
                    "wallet/kyc/kyc_form.html",
                    {"form": KYCStep3Form(instance=kyc), "step": 3},
                )
        else:
            form = KYCStep3Form(request.POST, request.FILES, instance=kyc)
            if form.is_valid():
                form.save()
                kyc.status = "pending"
                kyc.submitted_at = kyc.submitted_at or kyc.created_at
                kyc.attempts += 1
                kyc.save(update_fields=["status", "submitted_at", "attempts"])
                return render(request, "wallet/kyc/kyc_status.html", {"kyc": kyc})
    else:
        # GET шаг 1
        form = KYCStep1Form(instance=kyc)
        step = 1

    return render(request, "wallet/kyc/kyc_form.html", {"form": form, "step": step})


@login_required
def withdraw_confirm_view(request: HttpRequest) -> HttpResponse:
    """
    Страница подтверждения 2FA перед выводом средств.
    Пользователь вводит OTP код из приложения аутентификации или email.
    """
    withdrawal_pending = request.session.get("withdrawal_pending")
    if not withdrawal_pending:
        return redirect("wallet:withdraw")

    error = None
    success = None

    if request.method == "POST":
        otp_code = request.POST.get("otp_code", "").strip()

        if not otp_code:
            error = "Введите код подтверждения"
        else:
            is_valid = False

            if request.user.two_fa_method == "totp":
                totp_device = request.user.totp_devices.filter(confirmed=True).first()
                if totp_device:
                    totp = pyotp.TOTP(totp_device.secret)
                    is_valid = totp.verify(otp_code)
            elif request.user.two_fa_method == "email":
                is_valid = len(otp_code) == 6 and otp_code.isdigit()

            if is_valid:
                wallet = WalletService.create_wallet(request.user)
                try:
                    created_request = WithdrawalService.create_withdrawal_request(
                        wallet,
                        currency_code=withdrawal_pending["currency_code"],
                        amount=Decimal(withdrawal_pending["amount"]),
                        payment_method=withdrawal_pending["payment_method"],
                        payment_details=withdrawal_pending["payment_details"],
                        ip_address=withdrawal_pending["ip_address"],
                        user_agent=withdrawal_pending["user_agent"],
                    )
                    if "withdrawal_pending" in request.session:
                        del request.session["withdrawal_pending"]
                        request.session.modified = True
                    return redirect("wallet:withdrawal_status", request_id=created_request.id)
                except (WithdrawalValidationError, Exception) as exc:
                    error = str(exc) or "Не удалось создать заявку на вывод"
            else:
                error = "Неверный код подтверждения. Попробуйте ещё раз."

    currency = get_object_or_404(Currency, code=withdrawal_pending["currency_code"])
    amount = Decimal(withdrawal_pending["amount"])

    context = {
        "error": error,
        "success": success,
        "currency": currency,
        "amount": amount,
        "two_fa_method": request.user.two_fa_method,
    }
    return render(request, "wallet/withdraw_confirm.html", context)


# === HTMX / API endpoints ===


@login_required
@require_GET
def api_navbar_balance(request: HttpRequest) -> HttpResponse:
    try:
        wallet = WalletService.create_wallet(request.user)
    except Exception:
        wallet = None
    return render(request, "wallet/components/navbar_balance.html", {"wallet": wallet})


@login_required
@require_GET
def api_balances(request: HttpRequest) -> HttpResponse:
    wallet = WalletService.create_wallet(request.user)
    balances = WalletService.get_all_balances(wallet)
    return render(request, "wallet/components/balances_list.html", {"wallet": wallet, "balances": balances})


@login_required
@require_POST
def api_primary_currency(request: HttpRequest) -> HttpResponse:
    wallet = WalletService.create_wallet(request.user)
    code = request.POST.get("currency_code") or wallet.primary_currency_id or "USD"
    WalletService.change_primary_currency(wallet, code)
    # возвращаем обновлённый navbar-баланс
    return render(request, "wallet/components/navbar_balance.html", {"wallet": wallet})


@login_required
@require_GET
def api_conversion_preview(request: HttpRequest) -> HttpResponse:
    wallet = WalletService.create_wallet(request.user)
    from_code = request.GET.get("from") or wallet.primary_currency_id or "USD"
    to_code = request.GET.get("to") or "USD"
    amount_raw = request.GET.get("amount") or "0"
    try:
        amount = Decimal(amount_raw.replace(",", "."))
    except Exception:
        amount = Decimal("0")
    context: dict = {}
    if amount > 0:
        try:
            preview = ConversionService.preview_conversion(wallet, from_code, to_code, amount)
            context["preview"] = preview
        except Exception as exc:  # noqa: BLE001
            context["error"] = str(exc)
    else:
        context["error"] = "Введите сумму больше нуля"
    return render(request, "wallet/components/conversion_preview.html", context)


@login_required
@require_GET
def api_withdrawal_fee(request: HttpRequest) -> HttpResponse:
    wallet = WalletService.create_wallet(request.user)
    code = request.GET.get("currency") or wallet.primary_currency_id or "USD"
    amount_raw = request.GET.get("amount") or "0"
    currency = get_object_or_404(Currency, code=code)
    try:
        amount = Decimal(amount_raw.replace(",", "."))
    except Exception:
        amount = Decimal("0")
    fee_amount = (amount * currency.withdrawal_fee_percent / Decimal("100")) + currency.withdrawal_fee_fixed
    net_amount = amount - fee_amount
    context = {
        "currency": currency,
        "amount": amount,
        "fee_amount": fee_amount,
        "net_amount": net_amount,
    }
    return render(request, "wallet/components/withdrawal_fee.html", context)
