from django.utils.timezone import now
from django.db.models import Q
from django.core.exceptions import ValidationError
from apps.support.models import Ticket, Message, AutoResponse, FAQArticle, SLAConfig, MessageAttachment
from apps.accounts.services.notification_service import NotificationService
from utils.helpers import get_client_ip
from apps.support.services.assignment_service import AssignmentService


class TicketService:
    """
    Сервис для управления тикетами поддержки.
    """

    @staticmethod
    def create_ticket(user, category, subject, description, attachments=None, request=None):
        """
        Создание нового тикета.
        """
        # 1. Валидация
        if len(subject) < 5:
            return None, 'Тема слишком короткая (минимум 5 символов)'
        if len(description) < 20:
            return None, 'Опишите проблему подробнее (минимум 20 символов)'

        # Rate limit: максимум 5 тикетов в день
        today_tickets = Ticket.objects.filter(
            user=user, created_at__date=now().date()
        ).count()
        if today_tickets >= 5:
            return None, 'Превышен лимит обращений (5 в день)'

        # 2. Автоопределение приоритета
        priority = TicketService.determine_priority(category, user)

        # 3. Создать тикет
        ticket = Ticket.objects.create(
            user=user,
            category=category,
            subject=subject,
            description=description,
            priority=priority,
            source='form',
            ip_address=get_client_ip(request) if request else None,
            user_agent=request.META.get('HTTP_USER_AGENT', '') if request else '',
        )

        # 4. Первое сообщение
        first_message = Message.objects.create(
            ticket=ticket,
            sender=user,
            sender_type='user',
            text=description,
            ip_address=ticket.ip_address,
        )

        # 5. Обработка вложений
        if attachments:
            for file in attachments[:5]:
                TicketService.process_attachment(first_message, file)

        # 6. Автоответ
        auto_response = TicketService.check_auto_response(ticket)
        if auto_response:
            Message.objects.create(
                ticket=ticket,
                sender=None,  # Бот
                sender_type='bot',
                text=auto_response.response_text,
                is_system_message=False,
            )
            auto_response.times_triggered += 1
            auto_response.save(update_fields=['times_triggered'])

        # 7. Предложить FAQ
        suggested_faqs = TicketService.suggest_faq_articles(category, subject, description)

        # 8. Назначить оператора
        AssignmentService.auto_assign(ticket)

        # 9. Уведомления
        # Пользователю:
        NotificationService.create_notification(
            user=user,
            notification_type='ticket_created',
            title=f'Тикет #{ticket.ticket_number} создан',
            message=f'Ваше обращение принято. Мы ответим в течение {SLAConfig.get_for_priority(priority).first_response_minutes // 60} часов.',
            icon='📋',
            link=f'/support/tickets/{ticket.id}/',
        )

        # Операторам (через WebSocket):
        # notify_operators_new_ticket(ticket)  # TODO: implement

        return ticket, None

    @staticmethod
    def add_reply(ticket, sender, text, attachments=None, is_internal=False):
        """
        Добавить ответ в тикет.
        sender может быть user или operator.
        """
        sender_type = 'operator' if sender.is_staff else 'user'

        message = Message.objects.create(
            ticket=ticket,
            sender=sender,
            sender_type=sender_type,
            text=text,
            is_internal=is_internal,
        )

        if attachments:
            for file in attachments[:5]:
                TicketService.process_attachment(message, file)

        # Обновить статус тикета
        if sender_type == 'operator' and not is_internal:
            # Оператор ответил
            if not ticket.first_response_at:
                ticket.first_response_at = now()
            ticket.status = 'waiting_user'
            ticket.save(update_fields=['first_response_at', 'status', 'updated_at'])

            # Уведомить пользователя
            NotificationService.create_notification(
                user=ticket.user,
                notification_type='ticket_reply',
                title=f'Ответ на тикет #{ticket.ticket_number}',
                message=text[:200] + ('...' if len(text) > 200 else ''),
                icon='💬',
                link=f'/support/tickets/{ticket.id}/',
            )

        elif sender_type == 'user':
            # Пользователь ответил
            ticket.status = 'waiting_admin'
            ticket.save(update_fields=['status', 'updated_at'])

        ticket.save(update_fields=['first_response_at', 'status', 'updated_at'])

        # TODO: Notifications

        return message

    @staticmethod
    def change_status(ticket, new_status, changed_by, reason=''):
        """Change ticket status."""
        old_status = ticket.status
        ticket.status = new_status

        if new_status == 'resolved':
            ticket.resolved_at = tz.now()
        elif new_status == 'closed':
            ticket.closed_at = tz.now()

        ticket.save()

        # System message
        Message.objects.create(
            ticket=ticket,
            sender=changed_by,
            sender_type='system',
            text=f'Статус изменён: {old_status} → {new_status}' + (f'. Причина: {reason}' if reason else ''),
            is_system_message=True,
            system_action='status_changed',
        )

        # TODO: Notifications

        return True

    @staticmethod
    def escalate_ticket(ticket, escalated_by, reason, escalate_to=None):
        """Эскалация тикета."""
        from apps.support.models import OperatorProfile

        ticket.is_escalated = True
        ticket.escalated_at = now()
        ticket.escalation_reason = reason
        ticket.priority = 'critical'

        if escalate_to:
            ticket.escalated_to = escalate_to
            ticket.assigned_to = escalate_to
        else:
            # Найти свободного старшего оператора
            senior = OperatorProfile.objects.filter(
                can_handle_critical=True,
                operator_status='online',
            ).order_by('current_tickets_count').first()
            if senior:
                ticket.escalated_to = senior.user
                ticket.assigned_to = senior.user

        ticket.save()

        Message.objects.create(
            ticket=ticket,
            sender=escalated_by,
            sender_type='system',
            text=f'Тикет эскалирован. Причина: {reason}',
            is_system_message=True,
            system_action='escalated',
        )

        # Уведомить эскалированному оператору
        # if ticket.escalated_to:
        #     notify_operator_escalation(ticket)

    @staticmethod
    def rate_ticket(ticket, user, rating, comment=''):
        """Оценка пользователем после решения."""
        if ticket.user != user:
            return False, 'Нельзя оценить чужой тикет'
        if ticket.status not in ('resolved', 'closed'):
            return False, 'Тикет ещё не решён'
        if ticket.rating is not None:
            return False, 'Вы уже оценили этот тикет'

        ticket.rating = rating  # 1-5
        ticket.rating_comment = comment
        ticket.rated_at = now()
        ticket.save(update_fields=['rating', 'rating_comment', 'rated_at'])

        # Обновить статистику оператора
        if ticket.assigned_to and hasattr(ticket.assigned_to, 'operator_profile'):
            op = ticket.assigned_to.operator_profile
            total_sum = op.avg_rating * op.total_ratings + rating
            op.total_ratings += 1
            op.avg_rating = total_sum / op.total_ratings
            op.save(update_fields=['avg_rating', 'total_ratings'])

        return True, None

    @staticmethod
    def determine_priority(category, user):
        """Автоопределение приоритета."""
        if category == 'security':
            return 'critical'
        if category in ('withdrawal', 'deposit'):
            return 'high'
        if category in ('complaint', 'verification'):
            return 'high'
        if category in ('suggestion',):
            return 'low'
        # VIP пользователь → повышаем
        if user.trust_level >= 4:
            return 'high'
        return 'medium'

    @staticmethod
    def check_auto_response(ticket):
        """Проверить есть ли подходящий автоответ."""
        text = f'{ticket.subject} {ticket.description}'.lower()

        responses = AutoResponse.objects.filter(is_active=True)
        for resp in responses:
            # Проверить категорию
            if resp.trigger_categories:
                if ticket.category not in resp.trigger_categories:
                    continue

            # Проверить ключевые слова
            for keyword in resp.trigger_keywords:
                if keyword.lower() in text:
                    return resp

        return None

    @staticmethod
    def suggest_faq_articles(category, subject, description):
        """Предложить FAQ статьи по теме."""
        text = f'{subject} {description}'.lower()
        words = set(text.split())

        articles = FAQArticle.objects.filter(
            is_active=True,
            related_ticket_categories__contains=[category],
        )

        scored = []
        for article in articles:
            score = 0
            for keyword in article.keywords:
                if keyword.lower() in text:
                    score += 1
            if score > 0:
                scored.append((article, score))

        scored.sort(key=lambda x: -x[1])
        return [a for a, s in scored[:3]]

    @staticmethod
    def process_attachment(message, file):
        """Обработать вложение к сообщению."""
        MessageAttachment.objects.create(
            message=message,
            file=file,
            original_filename=file.name,
            file_size=file.size,
            file_type=file.content_type,
            is_image=file.content_type.startswith('image/'),
        )
