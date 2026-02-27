from django.db import models
from django.utils import timezone


class TicketManager(models.Manager):
    def active_tickets(self):
        return self.filter(status__in=['new', 'open', 'in_progress', 'waiting_user', 'waiting_admin'])

    def overdue_tickets(self):
        # Tickets that are overdue based on SLA
        return self.filter(status__in=['new', 'open', 'in_progress'])

    def assigned_to(self, operator):
        return self.filter(assigned_to=operator)


class MessageManager(models.Manager):
    def unread_for_user(self, user):
        return self.filter(ticket__user=user, is_read_by_user=False)

    def unread_for_operator(self, operator):
        return self.filter(ticket__assigned_to=operator, is_read_by_operator=False)
