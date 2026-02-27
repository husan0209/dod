from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime
import uuid


User = get_user_model()


class TelegramUser(models.Model):
    """
    Связь аккаунта Telegram с пользователем DOD.
    Хранит данные из initData и настройки Mini App.
    Один Telegram аккаунт = один пользователь DOD.
    """

    # Связь с пользователем DOD
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='telegram_profile',
        null=True,
        blank=True,
        help_text='Связанный пользователь DOD'
    )

    # Telegram данные
    telegram_id = models.BigIntegerField(
        unique=True,
        help_text='ID пользователя в Telegram'
    )

    username = models.CharField(
        max_length=100,
        blank=True,
        help_text='Username в Telegram (@username)'
    )

    first_name = models.CharField(
        max_length=200,
        help_text='Имя в Telegram'
    )

    last_name = models.CharField(
        max_length=200,
        blank=True,
        help_text='Фамилия в Telegram'
    )

    photo_url = models.URLField(
        blank=True,
        help_text='Ссылка на аватар в Telegram'
    )

    language_code = models.CharField(
        max_length=10,
        blank=True,
        help_text='Язык Telegram клиента'
    )

    is_premium = models.BooleanField(
        default=False,
        help_text='Telegram Premium подписка'
    )

    # Авторизация
    auth_date = models.DateTimeField(
        help_text='Дата последней авторизации через initData'
    )

    auth_hash = models.CharField(
        max_length=64,
        help_text='Последний валидный hash initData'
    )

    # Настройки Mini App
    theme_params = models.JSONField(
        default=dict,
        help_text='Параметры темы Telegram клиента'
    )

    # Статистика
    app_opens_count = models.IntegerField(
        default=0,
        help_text='Сколько раз открывал Mini App'
    )

    last_app_open = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Последний раз открывал'
    )

    total_time_spent = models.IntegerField(
        default=0,
        help_text='Время в Mini App (секунды)'
    )

    # Привязка
    account_linked_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Когда привязан к аккаунту DOD'
    )

    link_method = models.CharField(
        max_length=20,
        blank=True,
        choices=(
            ('auto', 'Автоматически'),
            ('email', 'Через email'),
            ('phone', 'Через телефон'),
            ('existing', 'Через существующий аккаунт'),
            ('new', 'Новый аккаунт'),
        ),
        help_text='Метод привязки аккаунта'
    )

    # Уведомления через бота
    bot_notifications_enabled = models.BooleanField(
        default=True,
        help_text='Разрешил уведомления от бота'
    )

    notification_preferences = models.JSONField(
        default=dict,
        help_text='Настройки уведомлений'
    )

    # Реферал (deeplink)
    referred_by_deeplink = models.CharField(
        max_length=100,
        blank=True,
        help_text='Deeplink параметр при первом /start'
    )

    # Мета
    device_info = models.JSONField(
        default=dict,
        help_text='Информация об устройстве'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Telegram пользователь'
        verbose_name_plural = 'Telegram пользователи'
        indexes = [
            models.Index(fields=['telegram_id']),
            models.Index(fields=['user']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"TG:{self.telegram_id} → {self.user}"

    def get_display_name(self):
        """Имя для отображения."""
        if self.user:
            return self.user.username
        return self.first_name or f"TG-{self.telegram_id}"

    def is_linked(self):
        """Привязан ли к аккаунту DOD."""
        return self.user is not None

    def update_from_initdata(self, data):
        """Обновить данные из initData."""
        self.username = data.get('username', '')
        self.first_name = data.get('first_name', '')
        self.last_name = data.get('last_name', '')
        self.photo_url = data.get('photo_url', '')
        self.language_code = data.get('language_code', '')
        self.is_premium = data.get('is_premium', False)
        # Note: auth_date is set once during authentication, not updated
        self.save()


class MiniAppSession(models.Model):
    """
    Отслеживание сессий Mini App.
    Для аналитики и безопасности.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    telegram_user = models.ForeignKey(
        TelegramUser,
        on_delete=models.CASCADE,
        related_name='sessions'
    )

    # Данные сессии
    session_key = models.CharField(
        max_length=64,
        unique=True,
        help_text='Генерируется при каждом открытии'
    )

    init_data_hash = models.CharField(
        max_length=64,
        help_text='Hash для валидации'
    )

    # Платформа
    platform = models.CharField(
        max_length=20,
        choices=(
            ('android', 'Android'),
            ('ios', 'iOS'),
            ('tdesktop', 'Desktop'),
            ('web', 'Web Telegram'),
            ('macos', 'macOS'),
        ),
        help_text='Платформа Telegram клиента'
    )

    telegram_version = models.CharField(
        max_length=20,
        help_text='Версия Telegram клиента'
    )

    # Активность
    started_at = models.DateTimeField(auto_now_add=True)
    last_activity_at = models.DateTimeField(auto_now=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.IntegerField(default=0)

    # Навигация
    pages_visited = models.JSONField(
        default=list,
        help_text='Посещённые страницы'
    )

    actions_count = models.IntegerField(default=0)

    # Состояние
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Сессия Mini App'
        verbose_name_plural = 'Сессии Mini App'
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['telegram_user', 'is_active']),
            models.Index(fields=['started_at']),
        ]
