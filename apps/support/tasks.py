"""
Celery задачи для системы поддержки.
"""

from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q
from .models import Ticket, ChatSession, MessageAttachment, FAQArticle, Message
from .services.chat_service import ChatService
from .services.sla_service import SLAService
from apps.notifications.services import NotificationService


@shared_task
def process_chat_queue():
    """
    Обработка очереди живого чата.
    Запускается каждые 10 секунд.
    """
    ChatService.process_queue()


@shared_task
def check_sla_violations():
    """
    Проверка нарушений SLA.
    Запускается каждые 5 минут.
    """
    SLAService.check_sla_violations()


@shared_task
def auto_close_idle_chats():
    """
    Автоматическое закрытие неактивных чатов.
    Запускается каждые 5 минут.
    """
    now = timezone.now()
    idle_threshold = now - timedelta(minutes=30)

    # Найти неактивные чаты
    idle_sessions = ChatSession.objects.filter(
        chat_status='active',
    )

    for session in idle_sessions:
        last_message = Message.objects.filter(
            ticket=session.ticket,
        ).order_by('-created_at').first()

        if last_message and (now - last_message.created_at).total_seconds() > 1800:
            session.chat_status = 'ended'
            session.ended_at = now
            session.ended_by = 'timeout'
            session.save()

            # Системное сообщение
            Message.objects.create(
                ticket=session.ticket,
                sender=None,
                sender_type='system',
                text='Чат завершён из-за неактивности (30 минут).',
                is_system_message=True,
            )

            # Освободить оператора
            if session.operator:
                session.operator.operator_profile.release_chat()


@shared_task
def auto_close_resolved_tickets():
    """
    Автоматическое закрытие resolved тикетов без ответа пользователя.
    Запускается ежедневно в 3:00 UTC.
    """
    threshold_date = timezone.now() - timedelta(days=3)

    tickets = Ticket.objects.filter(
        status='resolved',
        resolved_at__lt=threshold_date,
    )

    for ticket in tickets:
        Ticket.objects.filter(id=ticket.id).update(
            status='closed',
            closed_at=timezone.now(),
        )

        # Системное сообщение
        Message.objects.create(
            ticket=ticket,
            sender=None,
            sender_type='system',
            text='Тикет автоматически закрыт из-за отсутствия ответа пользователя (3 дня).',
            is_system_message=True,
            system_action='auto_closed',
        )


@shared_task
def update_operator_stats():
    """
    Обновление статистики операторов.
    Запускается каждые 5 минут.
    """
    # Статистика обновляется автоматически при изменениях,
    # но можно добавить периодические обновления если нужно
    pass


@shared_task
def update_faq_stats():
    """
    Обновление статистики FAQ.
    Запускается ежедневно.
    """
    # Статистика обновляется в реальном времени,
    # но можно добавить агрегацию если нужно
    pass


@shared_task
def cleanup_old_attachments():
    """
    Очистка старых вложений.
    Запускается ежедневно.
    Удаляет вложения из закрытых тикетов старше 90 дней.
    """
    threshold_date = timezone.now() - timedelta(days=90)

    old_attachments = MessageAttachment.objects.filter(
        message__ticket__status='closed',
        message__ticket__closed_at__lt=threshold_date,
    )

    count = old_attachments.count()
    # В продакшене нужно удалять файлы с диска
    old_attachments.delete()

    return f"Удалено {count} старых вложений"


@shared_task
def generate_support_daily_report():
    """
    Генерация ежедневного отчёта поддержки.
    Запускается ежедневно в 7:00 UTC.
    """
    # Получить статистику
    sla_stats = SLAService.get_sla_stats()
    chat_stats = SLAService.get_chat_stats()
    faq_stats = SLAService.get_faq_stats()

    # Сформировать отчёт
    report = f"""
📊 Ежедневный отчёт поддержки - {timezone.now().date()}

🎫 Тикеты:
- Всего: {sla_stats['total_tickets']}
- Решено: {sla_stats['resolved_rate']:.1f}%
- SLA соблюдено: {sla_stats['sla_percentage']:.1f}%
- Нарушений SLA: {sla_stats['sla_breaches']}

💬 Чат:
- Чатов: {chat_stats['total_chats']}
- Ср. ожидание: {chat_stats['avg_wait_seconds']:.1f} сек
- Отказы: {chat_stats['abandonment_rate']:.1f}%

❓ FAQ:
- Просмотров: {faq_stats['total_views']}
- Полезно: {faq_stats['helpful_percentage']:.1f}%
    """.strip()

    # Отправить админам
    from django.contrib.auth import get_user_model
    User = get_user_model()
    admins = User.objects.filter(is_staff=True, is_superuser=True)

    for admin in admins:
        NotificationService.create_notification(
            user=admin,
            notification_type='daily_report',
            title='📊 Ежедневный отчёт поддержки',
            message=report,
            icon='📊',
        )
