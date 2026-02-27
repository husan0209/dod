import hmac
import hashlib
import json
import time
from urllib.parse import unquote, parse_qs
from django.conf import settings
from django.utils import timezone
from datetime import datetime

from apps.miniapp.models import TelegramUser, MiniAppSession


class TelegramAuthService:
    """
    Сервис авторизации через Telegram initData.

    initData — строка, которую Telegram передаёт
    в WebApp при открытии Mini App.
    Содержит данные пользователя, подписанные
    токеном бота. ОБЯЗАТЕЛЬНО валидировать на сервере.

    Формат initData:
      query_id=AAHdF6IQAAAAAAN0Xog...
      &user={"id":123456,"first_name":"John",...}
      &auth_date=1234567890
      &hash=abc123def456...

    Алгоритм валидации:
      1. Разобрать initData на пары ключ=значение
      2. Убрать hash из набора
      3. Отсортировать пары по ключу
      4. Собрать строку "key=value\n..."
      5. Создать HMAC-SHA256:
         secret = HMAC-SHA256("WebAppData", BOT_TOKEN)
         hash = HMAC-SHA256(secret, data_check_string)
      6. Сравнить с полученным hash
      7. Проверить auth_date (не старше 1 часа)
    """

    MAX_AUTH_AGE_SECONDS = 3600  # 1 час

    @staticmethod
    def validate_init_data(init_data_raw: str) -> dict:
        """
        Валидация initData от Telegram.

        Args:
            init_data_raw: Строка initData из WebApp

        Returns:
            dict с данными пользователя

        Raises:
            ValueError: Если данные невалидны
        """
        if not init_data_raw:
            raise ValueError('initData пуста')

        # 1. Парсинг
        parsed = dict(
            pair.split('=', 1)
            for pair in unquote(init_data_raw).split('&')
        )

        # 2. Извлечь hash
        received_hash = parsed.pop('hash', None)
        if not received_hash:
            raise ValueError('hash отсутствует в initData')

        # 3. Сортировать и собрать строку
        data_check_pairs = sorted(parsed.items())
        data_check_string = '\n'.join(
            f'{k}={v}' for k, v in data_check_pairs
        )

        # 4. Вычислить HMAC
        secret_key = hmac.new(
            b'WebAppData',
            settings.TELEGRAM_BOT_TOKEN.encode(),
            hashlib.sha256
        ).digest()

        computed_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()

        # 5. Сравнить
        if not hmac.compare_digest(computed_hash, received_hash):
            raise ValueError('Невалидная подпись initData')

        # 6. Проверить auth_date
        auth_date = int(parsed.get('auth_date', 0))
        current_time = int(time.time())
        if current_time - auth_date > TelegramAuthService.MAX_AUTH_AGE_SECONDS:
            raise ValueError(
                'initData истекла '
                f'(возраст: {current_time - auth_date}s)'
            )

        # 7. Извлечь user
        user_data = json.loads(parsed.get('user', '{}'))
        if not user_data.get('id'):
            raise ValueError('ID пользователя отсутствует')

        return {
            'user': user_data,
            'query_id': parsed.get('query_id'),
            'auth_date': auth_date,
            'hash': received_hash,
        }

    @staticmethod
    def get_or_create_user(validated_data: dict):
        """
        Получить или создать пользователя DOD
        по данным из Telegram.

        Логика:
          1. Ищем TelegramUser по telegram_id
          2. Если найден и привязан → возвращаем User
          3. Если найден но НЕ привязан → пробуем привязать
          4. Если НЕ найден → создаём TelegramUser
             + автосоздаём User

        Автосоздание User:
          username = tg_{telegram_id}
          (можно поменять позже)
          email = не задан (потребуется позже для KYC)
          is_email_verified = False
          источник_регистрации = 'telegram'
        """
        tg_data = validated_data['user']
        telegram_id = tg_data['id']

        tg_user, created = TelegramUser.objects.get_or_create(
            telegram_id=telegram_id,
            defaults={
                'first_name': tg_data.get('first_name', ''),
                'last_name': tg_data.get('last_name', ''),
                'username': tg_data.get('username', ''),
                'photo_url': tg_data.get('photo_url', ''),
                'language_code': tg_data.get('language_code', ''),
                'is_premium': tg_data.get('is_premium', False),
                'auth_date': timezone.make_aware(
                    datetime.fromtimestamp(validated_data['auth_date'])
                ),
                'auth_hash': validated_data['hash'],
            }
        )

        if not created:
            # Обновить данные
            tg_user.update_from_initdata(tg_data)

        if tg_user.is_linked():
            # Уже привязан → вернуть пользователя
            return tg_user.user, tg_user, False

        # Автосоздание нового User
        from apps.accounts.models import User
        user = User.objects.create(
            username=f'tg_{telegram_id}',
            first_name=tg_data.get('first_name', ''),
            last_name=tg_data.get('last_name', ''),
            registration_method='telegram',
            preferred_language=(
                'ru' if tg_data.get('language_code') == 'ru'
                else 'en'
            ),
        )

        # Привязать
        tg_user.user = user
        tg_user.account_linked_at = timezone.now()
        tg_user.link_method = 'new'
        tg_user.save()

        # Создать кошелёк, партнёрский профиль и т.д.
        # (сигналы post_save User уже сделают это)

        # Обработать deeplink (реферальный код)
        if tg_user.referred_by_deeplink:
            process_referral_deeplink(
                user, tg_user.referred_by_deeplink
            )

        return user, tg_user, True  # True = новый

    @staticmethod
    def link_existing_account(tg_user, email, password):
        """
        Привязать Telegram к существующему аккаунту.
        Пользователь вводит email + пароль своего аккаунта.
        """
        from apps.accounts.models import User
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise ValueError('Аккаунт не найден')

        if not user.check_password(password):
            raise ValueError('Неверный пароль')

        if hasattr(user, 'telegram_profile'):
            raise ValueError(
                'К этому аккаунту уже привязан Telegram'
            )

        tg_user.user = user
        tg_user.account_linked_at = timezone.now()
        tg_user.link_method = 'existing'
        tg_user.save()

        return user


# Вспомогательные функции

def process_referral_deeplink(user, deeplink):
    """
    Обработать реферальный deeplink.
    Пример: ref_DOD-X7K9M2
    """
    # Реализация зависит от реферальной системы
    # Пока заглушка
    pass


def generate_session_key():
    """Генерировать уникальный ключ сессии."""
    import secrets
    return secrets.token_hex(32)


def extract_platform(request):
    """Определить платформу из User-Agent или initData."""
    # Заглушка, реализовать по необходимости
    return 'android'
