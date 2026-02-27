from django.utils import timezone
from apps.support.models import Ticket, OperatorProfile


class AssignmentService:
    """
    Сервис для распределения тикетов операторам.
    """

    @staticmethod
    def auto_assign(ticket):
        """
        Автоматическое назначение тикета оператору.
        Алгоритм: Round-robin с учётом специализации
        и нагрузки.
        """

        # 1. Найти подходящих операторов
        operators = OperatorProfile.objects.filter(
            operator_status='online',
        )

        # Если критический — только с разрешением
        if ticket.priority == 'critical':
            operators = operators.filter(can_handle_critical=True)

        # Фильтр по специализации
        specialized = operators.filter(
            categories__contains=[ticket.category]
        )
        if specialized.exists():
            operators = specialized

        # 2. Сортировать по нагрузке (меньше тикетов → приоритет)
        operators = operators.order_by('current_tickets_count')

        operator_profile = operators.first()

        if operator_profile:
            ticket.assigned_to = operator_profile.user
            ticket.assigned_at = timezone.now()
            ticket.status = 'open'
            ticket.save(update_fields=['assigned_to', 'assigned_at', 'status'])

            operator_profile.current_tickets_count += 1
            operator_profile.save(update_fields=['current_tickets_count'])

            Message.objects.create(
                ticket=ticket,
                sender=operator_profile.user,
                sender_type='system',
                text='Тикет назначен оператору',
                is_system_message=True,
                system_action='assigned',
            )

        return operator_profile

    @staticmethod
    def transfer_ticket(ticket, from_operator, to_operator, reason=''):
        """Transfer ticket to another operator."""
        old = ticket.assigned_to
        ticket.assigned_to = to_operator
        ticket.assigned_at = timezone.now()
        ticket.save(update_fields=['assigned_to', 'assigned_at'])

        # Update load
        if old and hasattr(old, 'operator_profile'):
            old.operator_profile.current_tickets_count = max(0, old.operator_profile.current_tickets_count - 1)
            old.operator_profile.save(update_fields=['current_tickets_count'])

        to_operator.operator_profile.current_tickets_count += 1
        to_operator.operator_profile.save(update_fields=['current_tickets_count'])

    @staticmethod
    def assign_to_chat(session):
        """Назначить оператора для чата (из очереди)."""
        # Аналогично auto_assign, но для чатов
        operators = OperatorProfile.objects.filter(
            operator_status='online',
        )

        # Фильтр по специализации (если есть категории в сессии)
        # Для чатов специализация может быть по категориям тикета
        ticket_category = session.ticket.category
        specialized = operators.filter(
            categories__contains=[ticket_category]
        )
        if specialized.exists():
            operators = specialized

        # 2. Сортировать по нагрузке (меньше чатов → приоритет)
        operators = operators.order_by('current_chats_count')

        operator = operators.first()

        if operator and operator.is_available():
            session.operator = operator.user
            session.assigned_at = timezone.now()
            session.save(update_fields=['operator', 'assigned_at'])

            operator.current_chats_count += 1
            operator.save(update_fields=['current_chats_count'])

            return operator

        return None
