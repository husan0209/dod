from django.utils import timezone
from django.db.models import Avg
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .models import ChatSession, Ticket, OperatorProfile
from .services.ticket_service import TicketService
from .services.assignment_service import AssignmentService


class ChatService:
    """
    Сервис для управления живым чатом.
    """

    @staticmethod
    def start_chat(user, category, initial_message, request=None):
        """
        Начать живой чат.
        Создаёт тикет + ChatSession + ставит в очередь.
        """
        # Проверить: есть ли уже активный чат
        active = ChatSession.objects.filter(
            user=user,
            chat_status__in=['waiting', 'active'],
        ).first()
        if active:
            return active.ticket, None  # Вернуть существующий

        # Создать тикет
        ticket, error = TicketService.create_ticket(
            user=user,
            category=category,
            subject=f'Чат: {initial_message[:50]}',
            description=initial_message,
            request=request,
        )
        if error:
            return None, error

        ticket.source = 'chat'
        ticket.save(update_fields=['source'])

        # Создать ChatSession
        session = ChatSession.objects.create(
            ticket=ticket,
            user=user,
            chat_status='waiting',
            queue_entered_at=timezone.now(),
        )

        # Попробовать назначить оператора сразу
        operator = AssignmentService.assign_to_chat(session)

        if operator:
            session.chat_status = 'active'
            session.operator = operator.user
            session.operator_joined_at = timezone.now()
            session.wait_time_seconds = 0
            session.save()
        else:
            # Поставить в очередь
            position = ChatSession.objects.filter(
                chat_status='waiting',
                queue_entered_at__lt=session.queue_entered_at,
            ).count() + 1
            session.queue_position = position
            session.save(update_fields=['queue_position'])

        return ticket, None

    @staticmethod
    def get_queue_status():
        """Получить состояние очереди."""
        waiting = ChatSession.objects.filter(
            chat_status='waiting',
        ).count()

        avg_wait = ChatSession.objects.filter(
            chat_status='active',
            wait_time_seconds__gt=0,
        ).aggregate(avg=Avg('wait_time_seconds'))['avg'] or 0

        online_operators = OperatorProfile.objects.filter(
            operator_status='online',
        ).count()

        return {
            'waiting': waiting,
            'avg_wait_seconds': int(avg_wait),
            'online_operators': online_operators,
            'estimated_wait': ChatService.estimate_wait_time(waiting, online_operators),
        }

    @staticmethod
    def process_queue():
        """
        Celery задача (каждые 10 секунд).
        Обрабатывает очередь: назначает операторов.
        """
        waiting_sessions = ChatSession.objects.filter(
            chat_status='waiting',
        ).order_by('queue_entered_at')

        for session in waiting_sessions:
            operator = AssignmentService.assign_to_chat(session)
            if operator:
                session.chat_status = 'active'
                session.operator = operator.user
                session.operator_joined_at = timezone.now()
                session.wait_time_seconds = (
                    timezone.now() - session.queue_entered_at
                ).total_seconds()
                session.save()

                # Уведомить пользователя через WebSocket
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    f'chat_{session.ticket_id}',
                    {
                        'type': 'operator_joined_event',
                        'operator': {
                            'name': operator.user.username,
                        },
                    }
                )
            else:
                # Обновить позицию в очереди
                new_position = ChatSession.objects.filter(
                    chat_status='waiting',
                    queue_entered_at__lt=session.queue_entered_at,
                ).count() + 1

                if new_position != session.queue_position:
                    session.queue_position = new_position
                    session.save(update_fields=['queue_position'])

                    # Отправить обновление через WebSocket
                    channel_layer = get_channel_layer()
                    async_to_sync(channel_layer.group_send)(
                        f'chat_{session.ticket_id}',
                        {
                            'type': 'queue_update_event',
                            'position': new_position,
                            'wait_time': ChatService.estimate_wait_time(new_position, 0),
                        }
                    )

    @staticmethod
    def estimate_wait_time(queue_position, online_operators):
        """Оценить время ожидания в минутах."""
        if online_operators == 0:
            return "~30 мин"

        # Простая оценка: позиция / операторы * среднее время
        avg_time_per_chat = 5  # минут
        estimated_minutes = (queue_position / online_operators) * avg_time_per_chat

        if estimated_minutes < 1:
            return "<1 мин"
        elif estimated_minutes < 5:
            return f"~{int(estimated_minutes)} мин"
        else:
            return f"~{int(estimated_minutes)} мин"
