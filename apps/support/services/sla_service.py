from django.utils import timezone
from django.db.models import Q, Sum, Avg, F, Count
from apps.support.models import Ticket, SLAConfig, OperatorProfile, ChatSession, FAQArticle
from apps.support.services.ticket_service import TicketService
# from apps.notifications.services import NotificationService


class SLAService:
    """
    Сервис для мониторинга SLA (Service Level Agreement).
    """

    @staticmethod
    def check_sla_violations():
        """
        Celery задача (каждые 5 минут).
        Проверяет нарушения SLA.
        """
        now = timezone.now()

        # 1. Нет первого ответа
        open_tickets = Ticket.objects.filter(
            status__in=['new', 'open', 'in_progress'],
            first_response_at__isnull=True,
        ).select_related('assigned_to')

        for ticket in open_tickets:
            sla_config = SLAConfig.get_for_priority(ticket.priority)
            if not sla_config:
                continue

            deadline = ticket.created_at + sla_config.first_response_time
            if now > deadline:
                if not ticket.is_escalated:
                    # SLA нарушен → эскалировать
                    TicketService.escalate_ticket(
                        ticket=ticket,
                        escalated_by=None,  # система
                        reason=f'SLA первого ответа нарушен ({sla_config.first_response_minutes} мин)',
                    )

                    # Уведомить всех операторов
                    SLAService.notify_operators_sla_breach(ticket)

        # 2. Нет решения
        in_progress = Ticket.objects.filter(
            status__in=['in_progress', 'waiting_user', 'waiting_admin'],
            resolved_at__isnull=True,
        ).select_related('assigned_to')

        for ticket in in_progress:
            sla_config = SLAConfig.get_for_priority(ticket.priority)
            if not sla_config:
                continue

            deadline = ticket.created_at + sla_config.resolution_time
            if now > deadline and not ticket.is_escalated:
                TicketService.escalate_ticket(
                    ticket=ticket,
                    escalated_by=None,
                    reason=f'SLA решения нарушен ({sla_config.resolution_minutes} мин)',
                )

    @staticmethod
    def notify_operators_sla_breach(ticket):
        """
        Уведомить операторов о нарушении SLA.
        """
        operators = OperatorProfile.objects.filter(
            operator_status__in=['online', 'busy']
        ).select_related('user')

        for op in operators:
            # NotificationService.create_notification(
            #     user=op.user,
            #     notification_type='sla_breach',
            #     title='⚠️ Нарушение SLA',
            #     message=f'Тикет #{ticket.ticket_number} ({ticket.category}) нарушает SLA. Требуется срочное вмешательство.',
            #     icon='⚠️',
            #     link=f'/operator/tickets/{ticket.id}/',
            # )
            pass

    @staticmethod
    def get_sla_stats():
        """
        Получить статистику SLA.
        """
        total_tickets = Ticket.objects.count()
        resolved_tickets = Ticket.objects.filter(status__in=['resolved', 'closed']).count()
        resolved_rate = (resolved_tickets / total_tickets * 100) if total_tickets > 0 else 0

        # Среднее время первого ответа
        first_response_stats = Ticket.objects.filter(
            first_response_at__isnull=False
        ).aggregate(avg=Avg(F('first_response_at') - F('created_at')))

        # Среднее время решения
        resolution_stats = Ticket.objects.filter(
            resolved_at__isnull=False
        ).aggregate(avg=Avg(F('resolved_at') - F('created_at')))

        # SLA процент
        sla_breached = Ticket.objects.filter(is_escalated=True).count()
        sla_compliant = resolved_tickets - sla_breached
        sla_percentage = (sla_compliant / resolved_tickets * 100) if resolved_tickets > 0 else 0

        return {
            'total_tickets': total_tickets,
            'resolved_rate': resolved_rate,
            'avg_first_response_hours': first_response_stats['avg'].total_seconds() / 3600 if first_response_stats['avg'] else 0,
            'avg_resolution_hours': resolution_stats['avg'].total_seconds() / 3600 if resolution_stats['avg'] else 0,
            'sla_percentage': sla_percentage,
            'sla_breaches': sla_breached,
        }

    @staticmethod
    def get_category_stats():
        """
        Статистика по категориям.
        """
        stats = Ticket.objects.values('category').annotate(
            ticket_count=Count('id'),
            avg_resolution_time=Avg(F('resolved_at') - F('created_at')),
            avg_rating=Avg('rating'),
        ).order_by('-ticket_count')

        return list(stats)

    @staticmethod
    def get_operator_stats():
        """
        Статистика по операторам.
        """
        stats = OperatorProfile.objects.select_related('user').annotate(
            total_tickets=Count('assigned_tickets'),
            avg_rating=Avg('assigned_tickets__rating'),
            avg_first_response=Avg(F('assigned_tickets__first_response_at') - F('assigned_tickets__created_at')),
            avg_resolution=Avg(F('assigned_tickets__resolved_at') - F('assigned_tickets__created_at')),
        ).values(
            'user__username',
            'total_tickets',
            'avg_rating',
            'avg_first_response',
            'avg_resolution',
        )

        return list(stats)

    @staticmethod
    def get_chat_stats():
        """
        Статистика живого чата.
        """
        total_chats = ChatSession.objects.count()
        avg_wait_time = ChatSession.objects.filter(
            wait_time_seconds__gt=0
        ).aggregate(avg=Avg('wait_time_seconds'))['avg'] or 0

        # Процент отказов (ушли из очереди)
        total_waiting = ChatSession.objects.filter(chat_status='waiting').count()
        abandoned = ChatSession.objects.filter(
            chat_status='ended',
            ended_by='timeout'
        ).count()
        abandonment_rate = (abandoned / total_waiting * 100) if total_waiting > 0 else 0

        return {
            'total_chats': total_chats,
            'avg_wait_seconds': avg_wait_time,
            'abandonment_rate': abandonment_rate,
        }

    @staticmethod
    def get_faq_stats():
        """
        Статистика FAQ.
        """
        total_views = FAQArticle.objects.aggregate(total=Sum('views_count'))['total'] or 0
        total_helpful_yes = FAQArticle.objects.aggregate(total=Sum('helpful_yes'))['total'] or 0
        total_helpful_no = FAQArticle.objects.aggregate(total=Sum('helpful_no'))['total'] or 0
        total_feedback = total_helpful_yes + total_helpful_no
        helpful_percentage = (total_helpful_yes / total_feedback * 100) if total_feedback > 0 else 0

        return {
            'total_views': total_views,
            'helpful_percentage': helpful_percentage,
            'total_feedback': total_feedback,
        }
