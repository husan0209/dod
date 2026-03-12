import qrcode
import io
import base64
from typing import Tuple, Optional
from django.utils import timezone
import pyotp

from apps.accounts.models import User, BackupCode, TOTPDevice
from apps.accounts.services.notification_service import NotificationService


class OTPService:
    """
    Сервис для управления двухфакторной аутентификацией (2FA) через TOTP.
    """

    @staticmethod
    def setup_totp(user: User) -> Tuple[dict, Optional[str]]:
        """
        Настроить TOTP (Google Authenticator / Яндекс.Ключ).
        
        Возвращает:
            {
                'secret': 'JBSWY3DPEBLW64TMMQ======',  # Base32 secret
                'qr_code': 'data:image/png;base64,...',  # QR код в base64
                'backup_codes': ['XXXX-XXXX', ...]
            }
        """
        try:
            # Генерируем новый secret
            secret = pyotp.random_base32()
            totp = pyotp.TOTP(secret)
            
            # Генерируем URL для QR кода
            provisioning_uri = totp.provisioning_uri(
                name=user.email,
                issuer_name='DOD'
            )
            
            # Генерируем QR код
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(provisioning_uri)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            qr_code_base64 = base64.b64encode(buffer.getvalue()).decode()
            qr_code_data = f"data:image/png;base64,{qr_code_base64}"
            
            # Генерируем резервные коды
            backup_codes = OTPService.generate_backup_codes()
            
            return {
                'secret': secret,
                'qr_code': qr_code_data,
                'provisioning_uri': provisioning_uri,
                'backup_codes': backup_codes,
            }, None
        
        except Exception as e:
            return {}, f"Ошибка при настройке TOTP: {str(e)}"

    @staticmethod
    def verify_totp_setup(user: User, secret: str, totp_code: str) -> Tuple[bool, Optional[str]]:
        """
        Проверить TOTP код перед сохранением.
        """
        try:
            totp = pyotp.TOTP(secret)
            
            # Проверяем текущий код и предыдущий (в случае временного расхождения)
            if not (totp.verify(totp_code) or totp.verify(totp_code, valid_window=1)):
                return False, "Неверный код верификации"
            
            return True, None
        
        except Exception as e:
            return False, f"Ошибка при проверке TOTP: {str(e)}"

    @staticmethod
    def enable_totp(user: User, secret: str, backup_codes: list) -> Tuple[bool, Optional[str]]:
        """
        Включить TOTP для пользователя и сохранить резервные коды.
        """
        try:
            # Сохраняем TOTP secret в TOTPDevice
            device = TOTPDevice.objects.create(
                user=user,
                name='TOTP',
                secret=secret,
                confirmed=True
            )
            
            # Сохраняем резервные коды
            from django.contrib.auth.hashers import make_password
            for code in backup_codes:
                BackupCode.objects.create(
                    user=user,
                    code=make_password(code)
                )
            
            # Обновляем пользователя
            user.is_2fa_enabled = True
            user.two_fa_method = 'totp'
            user.save(update_fields=['is_2fa_enabled', 'two_fa_method'])
            
            NotificationService.create_notification(
                user=user,
                notification_type='security',
                title='2FA включена',
                message='Двухфакторная аутентификация успешно включена.',
                icon='🔒'
            )
            
            return True, None
        
        except Exception as e:
            return False, f"Ошибка при включении TOTP: {str(e)}"

    @staticmethod
    def disable_totp(user: User, password: str) -> Tuple[bool, Optional[str]]:
        """
        Отключить TOTP для пользователя.
        """
        try:
            if not user.check_password(password):
                return False, "Неверный пароль"
            
            # Удаляем TOTP устройство
            TOTPDevice.objects.filter(user=user, name='TOTP').delete()
            
            # Удаляем резервные коды
            BackupCode.objects.filter(user=user).delete()
            
            # Обновляем пользователя
            user.is_2fa_enabled = False
            user.two_fa_method = None
            user.save(update_fields=['is_2fa_enabled', 'two_fa_method'])
            
            NotificationService.create_notification(
                user=user,
                notification_type='security',
                title='2FA отключена',
                message='Двухфакторная аутентификация была отключена.',
                icon='🔓'
            )
            
            return True, None
        
        except Exception as e:
            return False, f"Ошибка при отключении TOTP: {str(e)}"

    @staticmethod
    def verify_totp_code(user: User, totp_code: str) -> Tuple[bool, Optional[str]]:
        """
        Проверить TOTP код при входе.
        """
        try:
            # Получаем TOTP устройство пользователя
            device = TOTPDevice.objects.filter(user=user, confirmed=True).first()
            if not device:
                return False, "TOTP не настроена"
            
            # Проверяем код с помощью pyotp
            totp = pyotp.TOTP(device.secret)
            if not totp.verify(totp_code):
                return False, "Неверный TOTP код"
            
            return True, None
        
        except Exception as e:
            return False, f"Ошибка при проверке TOTP: {str(e)}"

    @staticmethod
    def verify_backup_code(user: User, code: str) -> Tuple[bool, Optional[str]]:
        """
        Проверить резервный код и пометить его как использованный.
        """
        try:
            from django.contrib.auth.hashers import check_password
            
            backup_codes = BackupCode.objects.filter(user=user, is_used=False)
            
            for backup_code in backup_codes:
                if check_password(code, backup_code.code):
                    backup_code.is_used = True
                    backup_code.used_at = timezone.now()
                    backup_code.save(update_fields=['is_used', 'used_at'])
                    
                    NotificationService.create_notification(
                        user=user,
                        notification_type='security',
                        title='Резервный код использован',
                        message='Один из ваших резервных кодов был использован.',
                        icon='⚠️'
                    )
                    
                    return True, None
            
            return False, "Неверный резервный код"
        
        except Exception as e:
            return False, f"Ошибка при проверке резервного кода: {str(e)}"

    @staticmethod
    def generate_backup_codes(count: int = 10) -> list:
        """
        Генерировать резервные коды (10 кодов).
        """
        import secrets
        codes = []
        for _ in range(count):
            # Генерируем код в формате XXXX-XXXX
            code = '-'.join([
                secrets.token_hex(2).upper(),
                secrets.token_hex(2).upper()
            ])
            codes.append(code)
        
        return codes

    @staticmethod
    def get_backup_codes_count(user: User) -> int:
        """
        Получить количество оставшихся неиспользованных резервных кодов.
        """
        return BackupCode.objects.filter(user=user, is_used=False).count()

    @staticmethod
    def regenerate_backup_codes(user: User, password: str) -> Tuple[Optional[list], Optional[str]]:
        """
        Переоснастить резервные коды.
        """
        try:
            if not user.check_password(password):
                return None, "Неверный пароль"
            
            from django.contrib.auth.hashers import make_password
            
            # Удаляем старые коды
            BackupCode.objects.filter(user=user).delete()
            
            # Генерируем новые
            new_codes = OTPService.generate_backup_codes()
            
            for code in new_codes:
                BackupCode.objects.create(
                    user=user,
                    code=make_password(code)
                )
            
            NotificationService.create_notification(
                user=user,
                notification_type='security',
                title='Резервные коды обновлены',
                message='Новые резервные коды были сгенерированы.',
                icon='🔄'
            )
            
            return new_codes, None
        
        except Exception as e:
            return None, f"Ошибка при переоснащении кодов: {str(e)}"
