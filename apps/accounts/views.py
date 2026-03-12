from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST, require_http_methods
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth.backends import ModelBackend

from apps.accounts.models import User
from apps.accounts.forms import (
    CustomUserCreationForm, 
    EmailAuthenticationForm, 
    ChangePasswordForm,
    PasswordResetForm,
    SetPasswordForm,
    Enable2FAForm,
    Disable2FAForm,
    Verify2FAForm,
    PhoneVerificationForm,
    PhoneVerificationCodeForm,
)
from apps.accounts.services.auth_service import AuthService
from apps.accounts.services.otp_service import OTPService
from apps.accounts.services.sms_service import SMSService
from apps.telegram_bot.services import TelegramBotService


@require_http_methods(["GET", "POST"])
@csrf_protect
def register(request):
    """
    Страница регистрации.
    """
    if request.user.is_authenticated:
        return redirect('dashboard:home')
    
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            username = form.cleaned_data['username']
            password = form.cleaned_data['password1']
            phone = form.cleaned_data.get('phone')
            language = form.cleaned_data.get('language', 'ru')
            
            # Получить IP адрес
            ip_address = request.META.get('REMOTE_ADDR', '')
            
            # Регистрируем пользователя
            user, error = AuthService.register_user(
                email=email,
                username=username,
                password=password,
                phone=phone,
                registration_ip=ip_address,
                registration_method='email'
            )
            
            if user:
                messages.success(request, 'Пожалуйста, подтвердите ваш email. Письмо отправлено на вашу почту.')
                return redirect('accounts:email_verification_pending', user_id=user.id)
            else:
                messages.error(request, error or 'Ошибка при регистрации')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'accounts/register.html', {'form': form})


@require_http_methods(["GET"])
def email_verification_pending(request, user_id):
    """
    Страница ожидания подтверждения email.
    """
    try:
        user = User.objects.get(id=user_id)
        return render(request, 'accounts/email_verification_pending.html', {'user': user})
    except User.DoesNotExist:
        messages.error(request, 'Пользователь не найден')
        return redirect('accounts:register')


@require_http_methods(["GET"])
def verify_email(request, token):
    """
    Подтверждение email по токену.
    """
    user, error = AuthService.verify_email_token(token)
    
    if user:
        messages.success(request, 'Email успешно подтвержден! Теперь вы можете войти.')
        return redirect('accounts:login')
    else:
        messages.error(request, error or 'Ошибка при подтверждении email')
        return redirect('accounts:register')


@require_http_methods(["GET", "POST"])
@csrf_protect
def login_view(request):
    """
    Страница входа.
    """
    if request.user.is_authenticated:
        return redirect('dashboard:dashboard')
    
    if request.method == 'POST':
        form = EmailAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            ip_address = request.META.get('REMOTE_ADDR', '')
            
            # Аутентифицируем пользователя
            if email and password:
                user, error = AuthService.authenticate_user(email, password, ip_address)
            else:
                user, error = None, 'Неверный email или пароль'
            
            if user:
                # Логируем пользователя без проверки 2FA
                login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                messages.success(request, 'Вы успешно вошли.')
                return redirect('dashboard:dashboard')
            else:
                messages.error(request, error or 'Неверный email или пароль')
    else:
        form = EmailAuthenticationForm()
    
    return render(request, 'accounts/login.html', {'form': form})


@require_http_methods(["GET", "POST"])
@csrf_protect
def verify_2fa(request):
    """
    Второй фактор аутентификации (TOTP или резервный код).
    """
    user_id = request.session.get('2fa_user_id')
    if not user_id:
        return redirect('accounts:login')
    
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return redirect('accounts:login')
    
    if request.method == 'POST':
        form = Verify2FAForm(request.POST)
        if form.is_valid():
            totp_code = form.cleaned_data.get('totp_code')
            backup_code = form.cleaned_data.get('backup_code')
            
            verified = False
            error = None
            
            # Проверяем TOTP код
            if totp_code:
                verified, error = OTPService.verify_totp_code(user, totp_code)
            
            # Проверяем резервный код
            elif backup_code:
                verified, error = OTPService.verify_backup_code(user, backup_code)
            
            if verified:
                del request.session['2fa_user_id']
                login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                messages.success(request, 'Вы успешно вошли.')
                return redirect('dashboard:dashboard')
            else:
                messages.error(request, error or 'Неверный код')
    else:
        form = Verify2FAForm()
    
    return render(request, 'accounts/verify_2fa.html', {'form': form, 'user': user})


@require_http_methods(["GET", "POST"])
@login_required
@csrf_protect
def logout_view(request):
    """
    Выход из аккаунта.
    """
    logout(request)
    messages.success(request, 'Вы успешно вышли.')
    return redirect('accounts:login')


@require_http_methods(["GET", "POST"])
@login_required
@csrf_protect
def change_password(request):
    """
    Смена пароля.
    """
    if request.method == 'POST':
        form = ChangePasswordForm(request.POST)
        if form.is_valid():
            old_password = form.cleaned_data['old_password']
            new_password = form.cleaned_data['new_password1']
            
            if not request.user.check_password(old_password):
                messages.error(request, 'Текущий пароль неверен')
            else:
                success, error = AuthService.change_password(request.user, old_password, new_password)
                if success:
                    messages.success(request, 'Пароль успешно изменен.')
                    return redirect('accounts:profile')
                else:
                    messages.error(request, error or 'Ошибка при изменении пароля')
    else:
        form = ChangePasswordForm()
    
    return render(request, 'accounts/change_password.html', {'form': form})


@require_http_methods(["GET", "POST"])
@csrf_protect
def password_reset(request):
    """
    Запрос на сброс пароля.
    """
    if request.user.is_authenticated:
        return redirect('dashboard:home')
    
    if request.method == 'POST':
        form = PasswordResetForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            verification, error = AuthService.request_password_reset(email)
            
            messages.success(request, 'Если этот email зарегистрирован, вы получите письмо для сброса пароля.')
            return redirect('accounts:login')
    else:
        form = PasswordResetForm()
    
    return render(request, 'accounts/password_reset.html', {'form': form})


@require_http_methods(["GET", "POST"])
@csrf_protect
def reset_password_confirm(request, token):
    """
    Подтверждение сброса пароля.
    """
    if request.user.is_authenticated:
        return redirect('dashboard:home')
    
    if request.method == 'POST':
        form = SetPasswordForm(request.POST)
        if form.is_valid():
            new_password = form.cleaned_data['new_password1']
            user, error = AuthService.reset_password(token, new_password)
            
            if user:
                messages.success(request, 'Пароль успешно сброшен. Войдите с новым пароль.')
                return redirect('accounts:login')
            else:
                messages.error(request, error or 'Ошибка при сбросе пароля')
    else:
        form = SetPasswordForm()
    
    return render(request, 'accounts/reset_password_confirm.html', {'form': form, 'token': token})


@require_http_methods(["GET", "POST"])
@login_required
@csrf_protect
def setup_2fa(request):
    """
    Настройка двухфакторной аутентификации.
    """
    # variables may be assigned in branches below; initialize for type checker
    secret = None
    backup_codes = []

    if request.method == 'POST':
        form = Enable2FAForm(request.POST)
        if form.is_valid():
            totp_code = form.cleaned_data['totp_code']
            
            # Берем secret из сессии
            secret = request.session.get('totp_secret')
            backup_codes = request.session.get('backup_codes', [])
            
            if not secret:
                messages.error(request, 'Пожалуйста, начните процесс настройки 2FA сначала.')
                return redirect('accounts:setup_2fa_start')
            
            # Проверяем TOTP код
            verified, error = OTPService.verify_totp_setup(request.user, secret, totp_code)
            
            if verified:
                # Включаем TOTP
                success, error = OTPService.enable_totp(request.user, secret, backup_codes)
                
                if success:
                    del request.session['totp_secret']
                    del request.session['backup_codes']
                    
                    messages.success(request, 'Двухфакторная аутентификация успешно включена!')
                    return redirect('accounts:security_settings')
                else:
                    messages.error(request, error or 'Ошибка при включении 2FA')
            else:
                messages.error(request, error or 'Неверный код')
    else:
        # Генерируем новый secret если его ещё нет
        secret = request.session.get('totp_secret')
        backup_codes = request.session.get('backup_codes')
        
        if not secret:
            otp_data, error = OTPService.setup_totp(request.user)
            if error:
                messages.error(request, error or 'Ошибка при настройке 2FA')
                return redirect('accounts:security_settings')
            
            secret = otp_data['secret']
            backup_codes = otp_data['backup_codes']
            
            request.session['totp_secret'] = secret
            request.session['backup_codes'] = backup_codes
        
        form = Enable2FAForm()
    
    qr_code = request.session.get('qr_code', '')
    if not qr_code:
        otp_data, _ = OTPService.setup_totp(request.user)
        qr_code = otp_data.get('qr_code', '')
        request.session['qr_code'] = qr_code
    
    return render(request, 'accounts/setup_2fa.html', {
        'form': form,
        'qr_code': qr_code,
        'secret': secret,
        'backup_codes': backup_codes,
    })


@require_http_methods(["GET", "POST"])
@login_required
@csrf_protect
def disable_2fa(request):
    """
    Отключение двухфакторной аутентификации.
    """
    if request.method == 'POST':
        form = Disable2FAForm(request.POST)
        if form.is_valid():
            password = form.cleaned_data['password']
            
            success, error = OTPService.disable_totp(request.user, password)
            
            if success:
                messages.success(request, 'Двухфакторная аутентификация отключена.')
                return redirect('accounts:security_settings')
            else:
                messages.error(request, error or 'Ошибка при отключении 2FA')
    else:
        form = Disable2FAForm()
    
    return render(request, 'accounts/disable_2fa.html', {'form': form})


@require_http_methods(["GET"])
@login_required
@csrf_protect
def security_settings(request):
    """
    Страница настроек безопасности.
    """
    # Получаем связанные аккаунты
    linked_accounts = request.user.linked_accounts.all()
    
    # Получаем последние входы
    login_history = request.user.login_history.all()[:10]
    
    # Получаем активные сессии
    active_sessions = request.user.active_sessions.all()
    
    # Количество оставшихся резервных кодов
    backup_codes_count = OTPService.get_backup_codes_count(request.user)
    
    context = {
        'is_2fa_enabled': request.user.is_2fa_enabled,
        'two_fa_method': request.user.two_fa_method,
        'linked_accounts': linked_accounts,
        'login_history': login_history,
        'active_sessions': active_sessions,
        'backup_codes_count': backup_codes_count,
    }
    
    return render(request, 'accounts/security_settings.html', context)


@require_http_methods(["GET", "POST"])
@login_required
@csrf_protect
def link_phone(request):
    """
    Привязка номера телефона.
    """
    if request.method == 'POST':
        form = PhoneVerificationForm(request.POST)
        if form.is_valid():
            phone = form.cleaned_data['phone']
            
            # Отправляем SMS код
            verification, error = SMSService.send_verification_code(phone, request.user)
            
            if verification:
                request.session['phone_for_verification'] = str(phone)
                messages.success(request, 'SMS код отправлен. Проверьте ваш телефон.')
                return redirect('accounts:verify_phone')
            else:
                messages.error(request, error or 'Ошибка при отправке SMS')
    else:
        form = PhoneVerificationForm()
    
    return render(request, 'accounts/link_phone.html', {'form': form})


@require_http_methods(["GET", "POST"])
@login_required
@csrf_protect
def verify_phone(request):
    """
    Подтверждение номера телефона.
    """
    phone = request.session.get('phone_for_verification')
    if not phone:
        return redirect('accounts:link_phone')
    
    if request.method == 'POST':
        form = PhoneVerificationCodeForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['code']
            
            # Проверяем код
            verified, error = SMSService.verify_code(phone, code, request.user)
            
            if verified:
                del request.session['phone_for_verification']
                messages.success(request, 'Номер телефона успешно подтвержден.')
                return redirect('accounts:profile')
            else:
                messages.error(request, error or 'Ошибка при проверке SMS кода')
    else:
        form = PhoneVerificationCodeForm()
    
    return render(request, 'accounts/verify_phone.html', {'form': form, 'phone': phone})


@require_http_methods(["GET"])
@login_required
def profile(request):
    """
    Страница профиля пользователя.
    """
    return render(request, 'accounts/profile.html')


@require_POST
@login_required
def regenerate_backup_codes(request):
    """
    Переоснащение резервных кодов.
    """
    password = request.POST.get('password', '')
    
    new_codes, error = OTPService.regenerate_backup_codes(request.user, password)
    
    if new_codes:
        messages.success(request, 'Резервные коды успешно обновлены.')
        return render(request, 'accounts/backup_codes.html', {'codes': new_codes})
    else:
        error_message = error if error else 'Ошибка при обновлении резервных кодов'
        messages.error(request, error_message)
        return redirect('accounts:security_settings')


@require_http_methods(["GET", "POST"])
@login_required
def unlink_account(request, provider):
    """
    Отвязать аккаунт провайдера.
    """
    if request.method == 'POST':
        success, error = AuthService.unlink_provider(request.user, provider)
        
        if success:
            messages.success(request, f'Аккаунт {provider} отвязан.')
        else:
            messages.error(request, error or f'Не удалось отвязать {provider}')
        
        return redirect('accounts:security_settings')
    
    return render(request, 'accounts/confirm_unlink.html', {'provider': provider})
