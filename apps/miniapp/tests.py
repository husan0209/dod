import json
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from unittest.mock import patch, MagicMock

from apps.miniapp.models import TelegramUser, MiniAppSession
from apps.miniapp.services.auth_service import TelegramAuthService

User = get_user_model()


class TelegramUserModelTest(TestCase):
    """Тесты для модели TelegramUser."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com'
        )

    def test_telegram_user_creation(self):
        """Тест создания TelegramUser."""
        tg_user = TelegramUser.objects.create(
            telegram_id=123456789,
            first_name='Test',
            last_name='User',
            username='testuser',
            auth_date=timezone.now(),
            auth_hash='testhash123'
        )
        self.assertEqual(tg_user.telegram_id, 123456789)
        self.assertEqual(tg_user.first_name, 'Test')
        self.assertFalse(tg_user.is_linked())

    def test_telegram_user_linking(self):
        """Тест привязки аккаунта DOD."""
        tg_user = TelegramUser.objects.create(
            telegram_id=123456789,
            first_name='Test',
            auth_date=timezone.now(),
            auth_hash='testhash123'
        )

        # Привязываем пользователя
        tg_user.user = self.user
        tg_user.account_linked_at = timezone.now()
        tg_user.link_method = 'manual'
        tg_user.save()

        self.assertTrue(tg_user.is_linked())
        self.assertEqual(tg_user.get_display_name(), 'testuser')

    def test_update_from_initdata(self):
        """Тест обновления данных из initData."""
        tg_user = TelegramUser.objects.create(
            telegram_id=123456789,
            first_name='Old Name',
            auth_date=timezone.now(),
            auth_hash='oldhash'
        )

        init_data = {
            'first_name': 'New Name',
            'username': 'newuser',
            'photo_url': 'https://example.com/photo.jpg',
            'auth_date': 1234567890  # This will be converted in update_from_initdata
        }

        tg_user.update_from_initdata(init_data)

        tg_user.refresh_from_db()
        self.assertEqual(tg_user.first_name, 'New Name')
        self.assertEqual(tg_user.username, 'newuser')
        self.assertEqual(tg_user.photo_url, 'https://example.com/photo.jpg')


class MiniAppSessionModelTest(TestCase):
    """Тесты для модели MiniAppSession."""

    def setUp(self):
        self.user = User.objects.create_user(username='testuser')
        self.tg_user = TelegramUser.objects.create(
            telegram_id=123456789,
            user=self.user,
            auth_date=timezone.now(),
            auth_hash='testhash123'
        )

    def test_session_creation(self):
        """Тест создания сессии."""
        session = MiniAppSession.objects.create(
            telegram_user=self.tg_user,
            session_key='testkey123',
            init_data_hash='hash123',
            platform='android',
            telegram_version='7.8.0'
        )

        self.assertEqual(session.telegram_user, self.tg_user)
        self.assertEqual(session.platform, 'android')
        self.assertFalse(session.is_active)

    def test_session_ending(self):
        """Тест завершения сессии."""
        session = MiniAppSession.objects.create(
            telegram_user=self.tg_user,
            session_key='testkey123',
            init_data_hash='hash123',
            platform='ios'
        )

        # Имитируем завершение сессии
        session.is_active = False
        session.ended_at = timezone.now()
        session.duration_seconds = 300  # 5 минут
        session.save()

        session.refresh_from_db()
        self.assertFalse(session.is_active)
        self.assertIsNotNone(session.ended_at)
        self.assertEqual(session.duration_seconds, 300)


class TelegramAuthServiceTest(TestCase):
    """Тесты для TelegramAuthService."""

    def setUp(self):
        self.valid_init_data = (
            "query_id=AAHdF6IQAAAAAAN0Xog&user=%7B%22id%22%3A123456789%2C%22first_name%22%3A%22Test%22%2C%22username%22%3A%22testuser%22%7D&"
            "auth_date=1234567890&hash=abc123def456"
        )

    @patch('apps.miniapp.services.auth_service.settings')
    def test_validate_init_data_valid(self, mock_settings):
        """Тест валидации корректных initData."""
        mock_settings.TELEGRAM_BOT_TOKEN = 'test_token'

        with patch('apps.miniapp.services.auth_service.hmac.compare_digest', return_value=True):
            with patch('apps.miniapp.services.auth_service.time.time', return_value=1234567800):  # Не истекло
                result = TelegramAuthService.validate_init_data(self.valid_init_data)

                self.assertIn('user', result)
                self.assertIn('auth_date', result)
                self.assertEqual(result['user']['id'], 123456789)

    def test_validate_init_data_expired(self):
        """Тест валидации истекших initData."""
        expired_init_data = (
            "query_id=AAHdF6IQAAAAAAN0Xog&user=%7B%22id%22%3A123456789%7D&"
            "auth_date=1234567890&hash=abc123def456"
        )

        with patch('apps.miniapp.services.auth_service.hmac.compare_digest', return_value=True):
            with patch('apps.miniapp.services.auth_service.time.time', return_value=1234567890 + 7200):  # Истекло
                with self.assertRaises(ValueError) as context:
                    TelegramAuthService.validate_init_data(expired_init_data)

                self.assertIn('истекла', str(context.exception))

    def test_get_or_create_user_new(self):
        """Тест создания нового пользователя."""
        validated_data = {
            'user': {
                'id': 987654321,
                'first_name': 'New',
                'last_name': 'User',
                'username': 'newuser'
            },
            'auth_date': 1234567890,
            'hash': 'testhash'
        }

        user, tg_user, is_new = TelegramAuthService.get_or_create_user(validated_data)

        self.assertTrue(is_new)
        self.assertEqual(tg_user.telegram_id, 987654321)
        self.assertEqual(tg_user.first_name, 'New')
        self.assertEqual(user.username, 'tg_987654321')

    def test_link_existing_account(self):
        """Тест привязки существующего аккаунта."""
        user = User.objects.create_user(
            username='existing',
            email='existing@example.com',
            password='password123'
        )

        tg_user = TelegramUser.objects.create(
            telegram_id=123456789,
            auth_date=timezone.now(),
            auth_hash='testhash'
        )

        linked_user = TelegramAuthService.link_existing_account(
            tg_user, 'existing@example.com', 'password123'
        )

        tg_user.refresh_from_db()
        self.assertEqual(linked_user, user)
        self.assertEqual(tg_user.user, user)
        self.assertEqual(tg_user.link_method, 'existing')


class MiniAppViewsTest(TestCase):
    """Тесты для представлений Mini App."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser')
        self.tg_user = TelegramUser.objects.create(
            telegram_id=123456789,
            user=self.user,
            auth_date=timezone.now(),
            auth_hash='testhash'
        )

    def test_home_view_requires_auth(self):
        """Тест, что главная страница требует авторизации."""
        response = self.client.get('/tg/')
        # Должен быть редирект или ошибка, так как нет initData
        self.assertNotEqual(response.status_code, 200)

    def test_api_balance_requires_auth(self):
        """Тест, что API баланса требует авторизации."""
        response = self.client.get('/tg/api/balance/')
        self.assertEqual(response.status_code, 403)  # Forbidden

    @patch('apps.miniapp.views.render')
    def test_home_view_authenticated(self, mock_render):
        """Тест главной страницы с авторизацией."""
        mock_render.return_value = MagicMock()

        # Имитируем middleware авторизацию
        session = self.client.session
        session['_auth_user_id'] = self.user.id
        session.save()

        # Имитируем Telegram middleware
        with patch('apps.miniapp.middleware.TelegramMiniAppMiddleware') as mock_middleware:
            mock_middleware.return_value = None

            response = self.client.get('/tg/')
            # Проверяем, что render был вызван
            mock_render.assert_called_once()


class MiniAppMiddlewareTest(TestCase):
    """Тесты для middleware Mini App."""

    def setUp(self):
        self.client = Client()

    def test_middleware_ignores_non_tg_paths(self):
        """Тест, что middleware игнорирует пути вне /tg/."""
        response = self.client.get('/accounts/login/')
        # URL exists, so it returns 200, middleware doesn't interfere
        self.assertEqual(response.status_code, 200)

    @patch('apps.miniapp.services.auth_service.TelegramAuthService.validate_init_data')
    @patch('apps.miniapp.services.auth_service.TelegramAuthService.get_or_create_user')
    def test_middleware_with_initdata(self, mock_get_user, mock_validate):
        """Тест middleware с initData."""
        # Мокаем сервисы
        mock_validate.return_value = {'user': {'id': 123}, 'auth_date': 1234567890, 'hash': 'hash'}
        mock_get_user.return_value = (MagicMock(), MagicMock(), False)

        # Запрос с initData
        response = self.client.get('/tg/', {'initData': 'test_data'})

        # Проверяем, что сервисы были вызваны
        mock_validate.assert_called_once_with('test_data')
        mock_get_user.assert_called_once()


class NotificationServiceTest(TestCase):
    """Тесты для сервиса уведомлений."""

    def setUp(self):
        self.user = User.objects.create_user(username='testuser')
        self.tg_user = TelegramUser.objects.create(
            telegram_id=123456789,
            user=self.user,
            auth_date=timezone.now(),
            auth_hash='testhash',
            bot_notifications_enabled=True
        )

    @patch('apps.miniapp.services.notification_service.Bot')
    def test_send_notification(self, mock_bot_class):
        """Тест отправки уведомления."""
        mock_bot = MagicMock()
        mock_bot_class.return_value = mock_bot

        from apps.miniapp.services.notification_service import notification_service

        # Вызываем напрямую для тестирования
        import asyncio
        async def test_send():
            await notification_service.send_notification(
                self.tg_user,
                "Test message",
                reply_markup=None
            )

        asyncio.run(test_send())

        # Проверяем, что бот был вызван
        mock_bot.send_message.assert_called_once()
        args = mock_bot.send_message.call_args
        self.assertEqual(args[1]['chat_id'], 123456789)
        self.assertEqual(args[1]['text'], "Test message")

    def test_should_notify_enabled(self):
        """Тест проверки необходимости уведомления."""
        from apps.miniapp.services.notification_service import notification_service

        # Уведомления включены
        self.assertTrue(notification_service._should_notify(self.tg_user, 'bets_results'))

    def test_should_notify_disabled(self):
        """Тест проверки когда уведомления отключены."""
        from apps.miniapp.services.notification_service import notification_service

        # Отключаем уведомления
        self.tg_user.bot_notifications_enabled = False
        self.tg_user.save()

        self.assertFalse(notification_service._should_notify(self.tg_user, 'bets_results'))
