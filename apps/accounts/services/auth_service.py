import secrets
from typing import Tuple, Optional
from django.contrib.auth import authenticate
from django.db import transaction
from django.utils import timezone
from phonenumber_field.phonenumber import PhoneNumber

from apps.accounts.models import User, EmailVerification, PhoneVerification, LoginHistory, LinkedAccount
from apps.accounts.services.notification_service import NotificationService


class AuthService:
    """
    Сервис для управления авторизацией, регистрацией и верификацией.
    """

    @staticmethod
    def register_user(
        email: str,
        username: str,
        password: Optional[str] = None,
        phone: Optional[str] = None,
        registration_ip: Optional[str] = None,
        registration_method: str = 'email',
    ) -> Tuple[Optional[User], Optional[str]]:
        """
        Регистрация нового пользователя.
        
        Args:
            email: Email пользователя
            username: Имя пользователя
            password: Пароль (опционально, для OAuth может быть None)
            phone: Номер телефона (опционально)
            registration_ip: IP адрес при регистрации
            registration_method: Способ регистрации (email, google, telegram, phone)
        
        Returns:
            (user, error) - кортеж пользователя и ошибки (если она есть)
        """
        # Проверка уникальности email
        if User.objects.filter(email__iexact=email).exists():
            return None, "Этот email уже зарегистрирован"
        
        # Проверка уникальности username
        if User.objects.filter(username__iexact=username).exists():
            return None, "Это имя пользователя уже занято"
        
        # Проверка уникальности телефона
        if phone and User.objects.filter(phone=phone).exists():
            return None, "Этот номер телефона уже зарегистрирован"
        
        try:
            with transaction.atomic():
                # Создание пользователя
                user = User.objects.create_user(
                    email=email.lower(),
                    username=username.lower(),
                    password=password,
                    phone=phone,
                    registration_ip=registration_ip,
                    registration_method=registration_method,
                )
                
                # Если регистрация по email, отправить письмо подтверждения
                if registration_method == 'email':
                    AuthService.send_email_verification(user)
                
                # Создать уведомление о регистрации
                NotificationService.create_notification(
                    user=user,
                    notification_type='general',
                    title='Добро пожаловать на DOD!',
                    message='Спасибо за регистрацию. Пожалуйста, подтвердите ваш email.',
                    icon='👋'
                )
                
                return user, None
        
        except Exception as e:
            return None, f"Ошибка при регистрации: {str(e)}"

    @staticmethod
    def send_email_verification(user: User) -> EmailVerification:
        """
        Отправить письмо подтверждения email.
        """
        token = secrets.token_urlsafe(32)
        
        verification = EmailVerification.objects.create(
            user=user,
            email=user.email,
            token=token,
        )
        
        # TODO: Отправить email с ссылкой потверждения
        # Ссылка должна быть: /accounts/verify-email/{token}
        
        return verification

    @staticmethod
    def verify_email_token(token: str) -> Tuple[Optional[User], Optional[str]]:
        """
        Проверить токен подтверждения email.
        """
        try:
            verification = EmailVerification.objects.get(token=token)
            
            if not verification.is_valid():
                if verification.is_used:
                    return None, "Этот токен уже использован"
            
            user = verification.user
            user.is_email_verified = True
            user.save(update_fields=['is_email_verified'])
            
            verification.is_used = True
            verification.save(update_fields=['is_used'])
            
            # Уведомление
            NotificationService.create_notification(
                user=user,
                notification_type='general',
                title='Email подтвержден',
                message='Ваш email успешно подтвержден.',
                icon='✅'
            )
            
            return user, None
        
        except EmailVerification.DoesNotExist:
            return None, "Токен подтверждения не найден"
        except Exception as e:
            return None, f"Ошибка при проверке токена: {str(e)}"

    @staticmethod
    def send_phone_verification(phone: Optional[PhoneNumber], user: Optional[User] = None) -> Tuple[Optional[PhoneVerification], Optional[str]]:
        """
        Отправить SMS код для подтверждения телефона.
        """
        if not phone:
            return None, "Номер телефона не указан"
        
        # Проверить лимит на количество SMS
        recent_codes = PhoneVerification.objects.filter(
            phone=phone,
            created_at__gte=timezone.now() - timezone.timedelta(minutes=10)
        )
        
        if recent_codes.count() >= 3:
            return None, "Слишком много попыток отправки кода. Попробуйте позже."
        
        code = f"{secrets.randbelow(10)}{secrets.randbelow(10)}{secrets.randbelow(10)}{secrets.randbelow(10)}{secrets.randbelow(10)}{secrets.randbelow(10)}"
        
        verification = PhoneVerification.objects.create(
            user=user,
            phone=phone,
            code=code,
        )
        
        # TODO: Отправить SMS код через провайдера
        
        return verification, None

    @staticmethod
    def verify_phone_code(phone: PhoneNumber, code: str, user: Optional[User] = None) -> Tuple[Optional[User], Optional[str]]:
        """
        Проверить SMS код подтверждения телефона.
        """
        try:
            verification = PhoneVerification.objects.filter(
                phone=phone,
                is_used=False,
            ).latest('created_at')
            
            if timezone.now() - verification.created_at > timezone.timedelta(minutes=10):
                return None, "Код подтверждения истек"
            
            if verification.attempts >= 3:
                verification.is_used = True
                verification.save(update_fields=['is_used'])
                return None, "Превышено максимальное количество попыток"
            
            if verification.code != code:
                verification.attempts += 1
                verification.save(update_fields=['attempts'])
                return None, "Неверный код подтверждения"
            
            # Успешная проверка
            if user:
                user.is_phone_verified = True
                user.phone = str(phone)
                user.save(update_fields=['is_phone_verified', 'phone'])
                
                NotificationService.create_notification(
                    user=user,
                    notification_type='general',
                    title='Телефон подтвержден',
                    message='Ваш номер телефона успешно подтвержден.',
                    icon='✅'
                )
            
            verification.is_used = True
            verification.save(update_fields=['is_used'])
            
            return user, None
        
        except PhoneVerification.DoesNotExist:
            return None, "Код подтверждения не найден"
        except Exception as e:
            return None, f"Ошибка при проверке кода: {str(e)}"

    @staticmethod
    def authenticate_user(email: str, password: str, ip_address: str = '') -> Tuple[Optional[User], Optional[str]]:
        """
        Аутентификация пользователя по email и пароль.
        """
        try:
            user = User.objects.get(email__iexact=email)
            
            if not user.is_active:
                return None, "Ваш аккаунт заблокирован. Свяжитесь с поддержкой."
            
            if user.check_password(password):
                # Логирование входа
                AuthService.log_login_attempt(
                    user=user,
                    ip_address=ip_address,
                    is_successful=True,
                    login_method='email'
                )
                return user, None
            else:
                # Логирование неудачного входа
                AuthService.log_login_attempt(
                    user=user,
                    ip_address=ip_address,
                    is_successful=False,
                    login_method='email',
                    failure_reason='wrong_password'
                )
                return None, "Неверный пароль"
        
        except User.DoesNotExist:
            return None, "Пользователь с таким email не найден"
        except Exception as e:
            return None, f"Ошибка при аутентификации: {str(e)}"

    @staticmethod
    def log_login_attempt(
        user: User,
        ip_address: str = '',
        is_successful: bool = True,
        login_method: str = 'email',
        failure_reason: Optional[str] = None,
        device_info: Optional[dict] = None,
    ) -> LoginHistory:
        """
        Логирование попытки входа.
        """
        device_info = device_info or {}
        
        login_history = LoginHistory.objects.create(
            user=user,
            ip_address=ip_address,
            is_successful=is_successful,
            login_method=login_method,
            failure_reason=failure_reason,
            device_type=device_info.get('device_type', 'unknown'),
            browser=device_info.get('browser', ''),
            os=device_info.get('os', ''),
            device_name=device_info.get('device_name', ''),
            user_agent=device_info.get('user_agent', ''),
            country=device_info.get('country', ''),
            city=device_info.get('city', ''),
        )
        
        if is_successful:
            user.last_login_ip = ip_address
            user.last_activity = timezone.now()
            user.save(update_fields=['last_login_ip', 'last_activity'])
        
        return login_history

    @staticmethod
    def link_provider(
        user: User,
        provider: str,
        provider_id: str,
        provider_email: Optional[str] = None,
        provider_username: Optional[str] = None,
        provider_avatar: Optional[str] = None,
    ) -> Tuple[Optional[LinkedAccount], Optional[str]]:
        """
        Привязать аккаунт провайдера (Google, Telegram, телефон).
        """
        try:
            with transaction.atomic():
                # Проверить что провайдер не привязан к другому аккаунту
                existing_account = LinkedAccount.objects.filter(
                    provider=provider,
                    provider_id=provider_id
                ).first()
                
                if existing_account and existing_account.user != user:
                    return None, "Этот аккаунт уже привязан к другому пользователю"
                
                linked_account, created = LinkedAccount.objects.update_or_create(
                    user=user,
                    provider=provider,
                    defaults={
                        'provider_id': provider_id,
                        'provider_email': provider_email,
                        'provider_username': provider_username,
                        'provider_avatar': provider_avatar,
                        'is_primary': False,
                    }
                )
                
                NotificationService.create_notification(
                    user=user,
                    notification_type='security',
                    title=f'{provider.capitalize()} привязан',
                    message=f'Ваш аккаунт {provider} успешно привязан.',
                    icon='🔗'
                )
                
                return linked_account, None
        
        except Exception as e:
            return None, f"Ошибка при привязке аккаунта: {str(e)}"

    @staticmethod
    def unlink_provider(user: User, provider: str) -> Tuple[bool, Optional[str]]:
        """
        Отвязать аккаунт провайдера.
        """
        try:
            LinkedAccount.objects.filter(user=user, provider=provider).delete()
            
            NotificationService.create_notification(
                user=user,
                notification_type='security',
                title=f'{provider.capitalize()} отвязан',
                message=f'Аккаунт {provider} отвязан от вашего профиля.',
                icon='🔓'
            )
            
            return True, None
        
        except Exception as e:
            return False, f"Ошибка при отвязке аккаунта: {str(e)}"

    @staticmethod
    def change_password(user: User, old_password: str, new_password: str) -> Tuple[bool, Optional[str]]:
        """
        Изменить пароль пользователя.
        """
        if not user.check_password(old_password):
            return False, "Текущий пароль неверен"
        
        user.set_password(new_password)
        user.save(update_fields=['password'])
        
        NotificationService.create_notification(
            user=user,
            notification_type='security',
            title='Пароль изменен',
            message='Ваш пароль был успешно изменен.',
            icon='✅'
        )
        
        return True, None

    @staticmethod
    def request_password_reset(email: str) -> Tuple[Optional[EmailVerification], Optional[str]]:
        """
        Запросить сброс пароля (отправить письмо с ссылкой).
        """
        try:
            user = User.objects.get(email__iexact=email)
            
            token = secrets.token_urlsafe(32)
            verification = EmailVerification.objects.create(
                user=user,
                email=user.email,
                token=token,
            )
            
            # TODO: Отправить email с ссылкой сброса пароля
            # Ссылка: /accounts/reset-password/{token}
            
            return verification, None
        
        except User.DoesNotExist:
            # В целях безопасности не сообщаем что email не найден
            return None, "Если этот email зарегистрирован, вы получите письмо для сброса пароля"
        except Exception as e:
            return None, f"Ошибка при запросе сброса пароля: {str(e)}"

    @staticmethod
    def reset_password(token: str, new_password: str) -> Tuple[Optional[User], Optional[str]]:
        """
        Сбросить пароль по токену.
        """
        try:
            verification = EmailVerification.objects.get(token=token)
            
            if not verification.is_valid():
                if verification.is_used:
                    return None, "Эта ссылка уже была использована"
            
            user = verification.user
            user.set_password(new_password)
            user.save(update_fields=['password'])
            
            verification.is_used = True
            verification.save(update_fields=['is_used'])
            
            NotificationService.create_notification(
                user=user,
                notification_type='security',
                title='Пароль сброшен',
                message='Ваш пароль был успешно изменен.',
                icon='✅'
            )
            
            return user, None
        
        except EmailVerification.DoesNotExist:
            return None, "Токен сброса пароля не найден"
        except Exception as e:
            return None, f"Ошибка при сбросе пароля: {str(e)}"
