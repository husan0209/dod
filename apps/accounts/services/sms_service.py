import os
from typing import Tuple, Optional
from django.utils import timezone
from django.core.cache import cache

from apps.accounts.models import PhoneVerification


class SMSService:
    """
    Сервис для отправки и проверки SMS кодов.
    Поддерживает различные SMS провайдеры.
    """

    # SMS провайдеры (будут실 настроены в settings)
    PROVIDERS = {
        'twilio': 'apps.accounts.services.sms_providers.TwilioProvider',
        'nexmo': 'apps.accounts.services.sms_providers.NexmoProvider',
        'custom': 'apps.accounts.services.sms_providers.CustomAPIProvider',
    }

    @staticmethod
    def get_provider():
        """
        Получить SMS провайдера из настроек.
        """
        provider_name = os.getenv('SMS_PROVIDER', 'custom').lower()
        
        if provider_name == 'twilio':
            from apps.accounts.services.sms_providers import TwilioProvider
            return TwilioProvider()
        elif provider_name == 'nexmo':
            from apps.accounts.services.sms_providers import NexmoProvider
            return NexmoProvider()
        else:
            from apps.accounts.services.sms_providers import CustomAPIProvider
            return CustomAPIProvider()

    @staticmethod
    def send_sms(phone_number: str, message: str) -> Tuple[bool, Optional[str]]:
        """
        Отправить SMS сообщение.
        """
        try:
            provider = SMSService.get_provider()
            success, error = provider.send(phone_number, message)
            return success, error
        
        except Exception as e:
            return False, f"Ошибка при отправке SMS: {str(e)}"

    @staticmethod
    def check_sms_rate_limit(phone_number: str) -> Tuple[bool, Optional[str]]:
        """
        Проверить лимит на отправку SMS для номера.
        
        Пределы:
        - 3 SMS за 10 минут
        - 10 SMS за 1 час
        - 20 SMS за 24 часа
        """
        cache_key_10m = f"sms_limit_10m_{phone_number}"
        cache_key_1h = f"sms_limit_1h_{phone_number}"
        cache_key_24h = f"sms_limit_24h_{phone_number}"
        
        count_10m = cache.get(cache_key_10m, 0)
        count_1h = cache.get(cache_key_1h, 0)
        count_24h = cache.get(cache_key_24h, 0)
        
        if count_10m >= 3:
            return False, "Слишком много SMS за короткое время. Попробуйте попозже (3 SMS за 10 минут)."
        
        if count_1h >= 10:
            return False, "Превышен лимит SMS за час (10 SMS за 1 час)."
        
        if count_24h >= 20:
            return False, "Превышен лимит SMS за день (20 SMS за 24 часа)."
        
        return True, None

    @staticmethod
    def send_verification_code(phone_number: str, user=None) -> Tuple[Optional[PhoneVerification], Optional[str]]:
        """
        Отправить SMS код подтверждения.
        """
        # Проверить рейт-лимит
        allowed, error = SMSService.check_sms_rate_limit(phone_number)
        if not allowed:
            return None, error
        
        # Генерируем код
        import secrets
        code = f"{secrets.randbelow(10)}{secrets.randbelow(10)}{secrets.randbelow(10)}{secrets.randbelow(10)}{secrets.randbelow(10)}{secrets.randbelow(10)}"
        
        # Сохраняем в БД
        verification = PhoneVerification.objects.create(
            user=user,
            phone=phone_number,
            code=code,
        )
        
        # Отправляем SMS
        message = f"DOD: Ваш код подтверждения: {code}\nЭтот код действителен 10 минут."
        success, sms_error = SMSService.send_sms(phone_number, message)
        
        if not success:
            verification.delete()
            return None, sms_error
        
        # Обновляем рейт-лимит в кэше
        cache_key_10m = f"sms_limit_10m_{phone_number}"
        cache_key_1h = f"sms_limit_1h_{phone_number}"
        cache_key_24h = f"sms_limit_24h_{phone_number}"
        
        cache.set(cache_key_10m, cache.get(cache_key_10m, 0) + 1, 600)  # 10 минут
        cache.set(cache_key_1h, cache.get(cache_key_1h, 0) + 1, 3600)  # 1 час
        cache.set(cache_key_24h, cache.get(cache_key_24h, 0) + 1, 86400)  # 24 часа
        
        return verification, None

    @staticmethod
    def resend_verification_code(phone_number: str, user=None) -> Tuple[Optional[PhoneVerification], Optional[str]]:
        """
        Переотправить SMS код.
        """
        # Удаляем старый код если он есть
        old_code = PhoneVerification.objects.filter(
            phone=phone_number,
            is_used=False,
            created_at__gte=timezone.now() - timezone.timedelta(minutes=10)
        ).first()
        
        if old_code:
            old_code.delete()
        
        # Отправляем новый
        return SMSService.send_verification_code(phone_number, user)

    @staticmethod
    def verify_code(phone_number: str, code: str, user=None) -> Tuple[bool, Optional[str]]:
        """
        Проверить SMS код.
        """
        try:
            verification = PhoneVerification.objects.filter(
                phone=phone_number,
                is_used=False,
                created_at__gte=timezone.now() - timezone.timedelta(minutes=10)
            ).latest('created_at')
            
            if verification.attempts >= 3:
                verification.is_used = True
                verification.save(update_fields=['is_used'])
                return False, "Превышено максимальное количество попыток (3)"
            
            if verification.code != code:
                verification.attempts += 1
                verification.save(update_fields=['attempts'])
                remaining = 3 - verification.attempts
                return False, f"Неверный код. Осталось {remaining} попыток."
            
            # Успешная проверка
            verification.is_used = True
            verification.save(update_fields=['is_used'])
            
            return True, None
        
        except PhoneVerification.DoesNotExist:
            return False, "Код подтверждения не найден или истек"
        except Exception as e:
            return False, f"Ошибка при проверке кода: {str(e)}"


class BaseSMSProvider:
    """
    Базовый класс для SMS провайдеров.
    """
    
    def send(self, phone_number: str, message: str) -> Tuple[bool, Optional[str]]:
        """
        Отправить SMS.
        """
        raise NotImplementedError


class TwilioProvider(BaseSMSProvider):
    """
    SMS провайдер Twilio.
    """
    
    def __init__(self):
        import os
        self.account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        self.auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        self.from_number = os.getenv('TWILIO_FROM_NUMBER')
    
    def send(self, phone_number: str, message: str) -> Tuple[bool, Optional[str]]:
        """
        Отправить SMS через Twilio.
        """
        try:
            from twilio.rest import Client
            
            client = Client(self.account_sid, self.auth_token)
            client.messages.create(
                body=message,
                from_=self.from_number,
                to=phone_number
            )
            
            return True, None
        
        except Exception as e:
            return False, f"Ошибка Twilio: {str(e)}"


class NexmoProvider(BaseSMSProvider):
    """
    SMS провайдер Nexmo (Vonage).
    """
    
    def __init__(self):
        import os
        self.api_key = os.getenv('NEXMO_API_KEY')
        self.api_secret = os.getenv('NEXMO_API_SECRET')
        self.from_number = os.getenv('NEXMO_FROM_NUMBER', 'DOD')
    
    def send(self, phone_number: str, message: str) -> Tuple[bool, Optional[str]]:
        """
        Отправить SMS через Nexmo.
        """
        try:
            import requests
            
            url = 'https://rest.nexmo.com/sms/json'
            params = {
                'api_key': self.api_key,
                'api_secret': self.api_secret,
                'to': phone_number,
                'from': self.from_number,
                'text': message,
            }
            
            response = requests.get(url, params=params, timeout=5)
            data = response.json()
            
            if data['messages'][0]['status'] == '0':
                return True, None
            else:
                return False, f"Nexmo ошибка: {data['messages'][0]['error-text']}"
        
        except Exception as e:
            return False, f"Ошибка Nexmo: {str(e)}"


class CustomAPIProvider(BaseSMSProvider):
    """
    SMS провайдер с использованием кастомного API.
    (Заглушка для тестирования)
    """
    
    def __init__(self):
        import os
        self.api_url = os.getenv('SMS_API_URL', 'http://localhost:8000/api/sms')
        self.api_key = os.getenv('SMS_API_KEY', '')
        self.api_secret = os.getenv('SMS_API_SECRET', '')
    
    def send(self, phone_number: str, message: str) -> Tuple[bool, Optional[str]]:
        """
        Отправить SMS через кастомный API.
        """
        try:
            import requests
            import hashlib
            
            # Создаем подпись (HMAC-SHA256)
            signature = hashlib.sha256(
                f"{phone_number}{message}{self.api_secret}".encode()
            ).hexdigest()
            
            payload = {
                'phone': phone_number,
                'message': message,
                'api_key': self.api_key,
                'signature': signature,
            }
            
            response = requests.post(self.api_url, json=payload, timeout=5)
            
            if response.status_code == 200:
                return True, None
            else:
                return False, f"API ошибка: {response.text}"
        
        except Exception as e:
            return False, f"Ошибка отправки SMS: {str(e)}"
