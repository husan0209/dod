from django.utils import timezone
from apps.accounts.models import Notification


class NotificationService:
    """
    Сервис для управления уведомлениями.
    """

    @staticmethod
    def create_notification(user, notification_type, title, message, icon='', link=''):
        """
        Создать уведомление для пользователя.
        """
        notification = Notification.objects.create(
            user=user,
            notification_type=notification_type,
            title=title,
            message=message,
            icon=icon,
            link=link,
        )

        # Здесь можно добавить отправку email или telegram
        # if user.notification_settings.get('email_notifications', True):
        #     send_email_notification(user, notification)
        # if user.notification_settings.get('telegram_notifications', False):
        #     send_telegram_notification(user, notification)

        return notification

    @staticmethod
    def mark_as_read(notification):
        """
        Отметить уведомление как прочитанное.
        """
        notification.mark_as_read()

    @staticmethod
    def get_unread_count(user):
        """
        Получить количество непрочитанных уведомлений.
        """
        return Notification.objects.filter(user=user, is_read=False).count()

    @staticmethod
    def get_recent_notifications(user, limit=10):
        """
        Получить последние уведомления пользователя.
        """
        return Notification.objects.filter(user=user).order_by('-created_at')[:limit]
