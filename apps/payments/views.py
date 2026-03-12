from __future__ import annotations

import logging
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods

from apps.payments.models import DepositOrder, PaymentProvider, PaymentMethod
from apps.payments.services.payment_service import PaymentService
from apps.payments.webhooks.handler import webhook_handler
from apps.wallet.models import Currency

logger = logging.getLogger(__name__)


def rukassa_webhook(request: HttpRequest):
    """RUkassa deposit webhook endpoint."""
    return webhook_handler.handle_deposit_webhook(request, "rukassa")


def nowpayments_webhook(request: HttpRequest):
    """NOWpayments deposit webhook endpoint."""
    return webhook_handler.handle_deposit_webhook(request, "nowpayments")


def nowpayments_payout_webhook(request: HttpRequest):
    """NOWpayments payout webhook endpoint."""
    return webhook_handler.handle_payout_webhook(request, "nowpayments")


@login_required
@require_http_methods(["GET"])
def deposit_page(request: HttpRequest) -> HttpResponse:
    """
    Display deposit page with available providers and payment methods.
    
    Requirements: 14.1, 14.2
    """
    # Get active providers grouped by type
    providers = PaymentProvider.objects.filter(
        is_active=True,
        is_deposit_enabled=True
    ).prefetch_related('methods').order_by('sort_order')
    
    # Group providers by type (fiat, crypto)
    fiat_providers = []
    crypto_providers = []
    
    for provider in providers:
        # Get active deposit methods for this provider
        methods = provider.methods.filter(
            is_active=True,
            type__in=['deposit', 'both']
        ).select_related('currency').order_by('sort_order')
        
        if methods.exists():
            provider_data = {
                'provider': provider,
                'methods': methods
            }
            
            if provider.type == 'fiat':
                fiat_providers.append(provider_data)
            elif provider.type == 'crypto':
                crypto_providers.append(provider_data)
            else:  # mixed
                fiat_providers.append(provider_data)
                crypto_providers.append(provider_data)
    
    context = {
        'fiat_providers': fiat_providers,
        'crypto_providers': crypto_providers,
    }
    
    return render(request, 'payments/deposit.html', context)


@login_required
@require_http_methods(["POST"])
def create_deposit(request: HttpRequest) -> HttpResponse:
    """
    Create a new deposit order and redirect to payment page.
    
    Requirements: 14.2, 14.3
    """
    try:
        # Extract form data
        payment_method_id = request.POST.get('payment_method_id')
        amount_str = request.POST.get('amount')
        currency_code = request.POST.get('currency')
        
        # Validate inputs
        if not all([payment_method_id, amount_str, currency_code]):
            return render(request, 'payments/deposit.html', {
                'error': 'Пожалуйста, заполните все поля'
            })
        
        try:
            amount = Decimal(amount_str)
        except (ValueError, TypeError):
            return render(request, 'payments/deposit.html', {
                'error': 'Неверная сумма'
            })
        
        # Get payment method and extract provider/method codes
        payment_method = get_object_or_404(PaymentMethod, id=payment_method_id, is_active=True)
        provider_code = payment_method.provider.code
        method_code = payment_method.code
        
        # Get client IP and user agent
        ip_address = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip() or \
                     request.META.get('REMOTE_ADDR', '127.0.0.1')
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Create deposit via service
        result = PaymentService.create_deposit(
            user=request.user,
            currency_code=currency_code,
            amount=amount,
            provider_code=provider_code,
            method_code=method_code,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        # Check if deposit was created successfully
        if result['status'] == 'failed':
            return render(request, 'payments/deposit.html', {
                'error': 'Не удалось создать заказ на пополнение. Попробуйте позже.'
            })
        
        # Redirect based on payment type
        if result.get('crypto_address'):
            # Crypto payment - show payment page with address and QR code
            return redirect('payments:deposit_crypto', order_id=result['deposit_id'])
        elif result.get('payment_url'):
            # Fiat payment - redirect to provider's payment page
            return redirect(result['payment_url'])
        else:
            return render(request, 'payments/deposit.html', {
                'error': 'Не удалось получить платёжные данные'
            })
            
    except ValueError as e:
        logger.error(f"Deposit creation error: {e}")
        return render(request, 'payments/deposit.html', {
            'error': str(e)
        })
    except Exception as e:
        logger.error(f"Unexpected error creating deposit: {e}", exc_info=True)
        return render(request, 'payments/deposit.html', {
            'error': 'Произошла ошибка. Попробуйте позже.'
        })


@login_required
@require_http_methods(["GET"])
def deposit_crypto(request: HttpRequest, order_id: str) -> HttpResponse:
    """
    Display crypto payment page with address and QR code.
    
    Requirements: 14.3, 14.4
    """
    # Get deposit order
    deposit = get_object_or_404(
        DepositOrder,
        order_id=order_id,
        user=request.user
    )
    
    # Ensure it's a crypto deposit
    if not deposit.crypto_address:
        return redirect('payments:deposit_failure', order_id=order_id)
    
    context = {
        'deposit': deposit,
    }
    
    return render(request, 'payments/deposit_crypto.html', context)


@login_required
@require_http_methods(["GET"])
def deposit_status(request: HttpRequest, order_id: str) -> JsonResponse:
    """
    Check deposit order status (AJAX endpoint for polling).
    
    Requirements: 14.3
    """
    try:
        deposit = get_object_or_404(
            DepositOrder,
            order_id=order_id,
            user=request.user
        )
        
        return JsonResponse({
            'status': deposit.status,
            'amount': str(deposit.amount),
            'amount_received': str(deposit.amount_received) if deposit.amount_received else None,
            'currency': deposit.currency.code,
            'completed_at': deposit.completed_at.isoformat() if deposit.completed_at else None,
            'expires_at': deposit.expires_at.isoformat(),
        })
    except Exception as e:
        logger.error(f"Error checking deposit status: {e}", exc_info=True)
        return JsonResponse({'error': 'Не удалось проверить статус'}, status=500)


@login_required
@require_http_methods(["GET"])
def deposit_success(request: HttpRequest) -> HttpResponse:
    """
    Display deposit success page.
    
    Requirements: 14.6
    """
    order_id = request.GET.get('order')
    
    deposit = None
    if order_id:
        try:
            deposit = DepositOrder.objects.get(
                order_id=order_id,
                user=request.user
            )
        except DepositOrder.DoesNotExist:
            pass
    
    context = {
        'deposit': deposit,
    }
    
    return render(request, 'payments/deposit_success.html', context)


@login_required
@require_http_methods(["GET"])
def deposit_failure(request: HttpRequest) -> HttpResponse:
    """
    Display deposit failure page.
    
    Requirements: 14.7
    """
    order_id = request.GET.get('order')
    
    deposit = None
    if order_id:
        try:
            deposit = DepositOrder.objects.get(
                order_id=order_id,
                user=request.user
            )
        except DepositOrder.DoesNotExist:
            pass
    
    context = {
        'deposit': deposit,
    }
    
    return render(request, 'payments/deposit_failure.html', context)


@login_required
@require_http_methods(["GET"])
def withdrawal_page(request: HttpRequest) -> HttpResponse:
    """
    Display withdrawal page with saved payment methods and form.
    
    Requirements: 14.8, 14.9
    """
    from apps.payments.models import SavedPaymentMethod
    from apps.wallet.services.wallet_service import WalletService
    
    # Get user's wallet and balances
    wallet = WalletService.create_wallet(request.user)
    balances = WalletService.get_all_balances(wallet)
    
    # Filter currencies with available balance > 0
    available_currencies = [b for b in balances if b["available"] > 0]
    
    # Get selected currency (default to first available or primary)
    if available_currencies:
        default_code = available_currencies[0]["currency"]
    else:
        default_code = wallet.primary_currency_id or "USD"
    
    selected_code = request.GET.get("currency", default_code)
    selected_currency = get_object_or_404(Currency, code=selected_code)
    
    # Get saved payment methods for the user
    saved_methods = SavedPaymentMethod.objects.filter(
        user=request.user
    ).select_related('currency').order_by('-is_default', '-last_used_at')
    
    # Get active payment providers and methods for withdrawals
    providers = PaymentProvider.objects.filter(
        is_active=True,
        is_withdrawal_enabled=True
    ).prefetch_related('methods').order_by('sort_order')
    
    # Group providers by type
    fiat_providers = []
    crypto_providers = []
    
    for provider in providers:
        # Get active withdrawal methods for this provider
        methods = provider.methods.filter(
            is_active=True,
            type__in=['withdrawal', 'both']
        ).select_related('currency').order_by('sort_order')
        
        if methods.exists():
            provider_data = {
                'provider': provider,
                'methods': methods
            }
            
            if provider.type == 'fiat':
                fiat_providers.append(provider_data)
            elif provider.type == 'crypto':
                crypto_providers.append(provider_data)
            else:  # mixed
                fiat_providers.append(provider_data)
                crypto_providers.append(provider_data)
    
    context = {
        'wallet': wallet,
        'balances': balances,
        'available_currencies': available_currencies,
        'selected_currency': selected_currency,
        'saved_methods': saved_methods,
        'fiat_providers': fiat_providers,
        'crypto_providers': crypto_providers,
    }
    
    return render(request, 'payments/withdrawal.html', context)


@login_required
@require_http_methods(["POST"])
def create_withdrawal(request: HttpRequest) -> HttpResponse:
    """
    Create a withdrawal request and initiate payout via PayoutService.
    
    Requirements: 14.8, 14.9, 5.1
    """
    from apps.wallet.services.wallet_service import WalletService
    from apps.wallet.services.withdrawal_service import WithdrawalService
    from apps.wallet.exceptions import WithdrawalValidationError
    from apps.payments.services.payout_service import PayoutService
    
    try:
        # Extract form data
        currency_code = request.POST.get('currency')
        amount_str = request.POST.get('amount')
        payment_method = request.POST.get('payment_method')
        provider_code = request.POST.get('provider_code')
        method_code = request.POST.get('method_code')
        
        # Payment details based on method type
        payment_details = {}
        if payment_method == 'card':
            payment_details = {
                'method': 'card',
                'card_number': request.POST.get('card_number', ''),
                'card_holder': request.POST.get('card_holder', ''),
            }
        elif payment_method == 'crypto':
            payment_details = {
                'method': 'crypto',
                'crypto_address': request.POST.get('crypto_address', ''),
                'network': request.POST.get('network', ''),
            }
        elif payment_method == 'ewallet':
            payment_details = {
                'method': 'ewallet',
                'account': request.POST.get('ewallet_account', ''),
                'account_type': request.POST.get('ewallet_type', ''),
            }
        
        # Validate inputs
        if not all([currency_code, amount_str, payment_method, provider_code, method_code]):
            return render(request, 'payments/withdrawal.html', {
                'error': 'Пожалуйста, заполните все поля'
            })
        
        try:
            amount = Decimal(amount_str)
        except (ValueError, TypeError):
            return render(request, 'payments/withdrawal.html', {
                'error': 'Неверная сумма'
            })
        
        # Get wallet
        wallet = WalletService.create_wallet(request.user)
        
        # Get client IP and user agent
        ip_address = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip() or \
                     request.META.get('REMOTE_ADDR', '127.0.0.1')
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Step 1: Create WithdrawalRequest via WithdrawalService
        withdrawal_request = WithdrawalService.create_withdrawal_request(
            wallet=wallet,
            currency_code=currency_code,
            amount=amount,
            payment_method=payment_method,
            payment_details=payment_details,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        # Step 2: If auto-approved, create payout via PayoutService
        if withdrawal_request.status in ['auto_approved', 'approved']:
            try:
                payout = PayoutService.create_payout(
                    withdrawal_request=withdrawal_request,
                    provider_code=provider_code,
                    method_code=method_code
                )
                
                # Redirect to withdrawal status page
                return redirect('payments:withdrawal_status', request_id=withdrawal_request.request_id)
                
            except Exception as e:
                logger.error(f"Error creating payout: {e}", exc_info=True)
                # Withdrawal request created but payout failed
                return render(request, 'payments/withdrawal.html', {
                    'error': f'Заявка создана, но не удалось инициировать выплату: {str(e)}'
                })
        else:
            # Manual review required
            return redirect('payments:withdrawal_status', request_id=withdrawal_request.request_id)
            
    except WithdrawalValidationError as e:
        logger.error(f"Withdrawal validation error: {e}")
        return render(request, 'payments/withdrawal.html', {
            'error': str(e)
        })
    except ValueError as e:
        logger.error(f"Withdrawal creation error: {e}")
        return render(request, 'payments/withdrawal.html', {
            'error': str(e)
        })
    except Exception as e:
        logger.error(f"Unexpected error creating withdrawal: {e}", exc_info=True)
        return render(request, 'payments/withdrawal.html', {
            'error': 'Произошла ошибка. Попробуйте позже.'
        })


@login_required
@require_http_methods(["GET"])
def withdrawal_status(request: HttpRequest, request_id: str) -> HttpResponse:
    """
    Display withdrawal request status.
    
    Requirements: 14.9
    """
    from apps.wallet.models import WithdrawalRequest
    from apps.payments.models import PayoutOrder
    
    # Get withdrawal request
    withdrawal = get_object_or_404(
        WithdrawalRequest,
        request_id=request_id,
        user=request.user
    )
    
    # Try to get associated payout order
    payout = None
    try:
        payout = PayoutOrder.objects.get(withdrawal_request=withdrawal)
    except PayoutOrder.DoesNotExist:
        pass
    
    context = {
        'withdrawal': withdrawal,
        'payout': payout,
    }
    
    return render(request, 'payments/withdrawal_status.html', context)


@login_required
@require_http_methods(["GET"])
def transaction_history(request: HttpRequest) -> HttpResponse:
    """
    Display transaction history page showing all deposits and withdrawals.
    
    Requirements: 14.10
    """
    from apps.wallet.models import WithdrawalRequest
    
    # Get filter parameters
    status_filter = request.GET.get('status', 'all')
    type_filter = request.GET.get('type', 'all')
    
    # Get deposits
    deposits = DepositOrder.objects.filter(
        user=request.user
    ).select_related('currency', 'provider', 'payment_method').order_by('-created_at')
    
    # Get withdrawals
    withdrawals = WithdrawalRequest.objects.filter(
        user=request.user
    ).select_related('currency').order_by('-created_at')
    
    # Apply status filter
    if status_filter != 'all':
        deposits = deposits.filter(status=status_filter)
        withdrawals = withdrawals.filter(status=status_filter)
    
    # Apply type filter
    if type_filter == 'deposits':
        withdrawals = WithdrawalRequest.objects.none()
    elif type_filter == 'withdrawals':
        deposits = DepositOrder.objects.none()
    
    # Combine and sort by date
    transactions = []
    
    for deposit in deposits:
        transactions.append({
            'type': 'deposit',
            'id': deposit.order_id,
            'amount': deposit.amount,
            'currency': deposit.currency,
            'status': deposit.status,
            'provider': deposit.provider.name if deposit.provider else None,
            'payment_method': deposit.payment_method.name if deposit.payment_method else None,
            'created_at': deposit.created_at,
            'completed_at': deposit.completed_at,
            'object': deposit,
        })
    
    for withdrawal in withdrawals:
        transactions.append({
            'type': 'withdrawal',
            'id': withdrawal.request_id,
            'amount': withdrawal.amount,
            'currency': withdrawal.currency,
            'status': withdrawal.status,
            'provider': None,
            'payment_method': withdrawal.payment_method,
            'created_at': withdrawal.created_at,
            'completed_at': withdrawal.completed_at,
            'object': withdrawal,
        })
    
    # Sort by created_at descending
    transactions.sort(key=lambda x: x['created_at'], reverse=True)
    
    # Get unique statuses for filter dropdown
    deposit_statuses = DepositOrder.objects.filter(user=request.user).values_list('status', flat=True).distinct()
    withdrawal_statuses = WithdrawalRequest.objects.filter(user=request.user).values_list('status', flat=True).distinct()
    all_statuses = sorted(set(list(deposit_statuses) + list(withdrawal_statuses)))
    
    context = {
        'transactions': transactions,
        'status_filter': status_filter,
        'type_filter': type_filter,
        'all_statuses': all_statuses,
    }
    
    return render(request, 'payments/transaction_history.html', context)
