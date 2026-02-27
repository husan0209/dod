import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.urls import reverse
from django.core.files.storage import default_storage
from django.conf import settings
from datetime import date, timedelta
from django.utils import timezone as tz

User = get_user_model()


class Ticket(models.Model):
    STATUS_CHOICES = [
        ('new', _('Новый')),
        ('open', _('Открыт')),
        ('in_progress', _('В работе')),
        ('waiting_user', _('Ожидание ответа пользователя')),
        ('waiting_admin', _('Ожидание ответа оператора')),
        ('on_hold', _('На удержании')),
        ('resolved', _('Решён')),
        ('closed', _('Закрыт')),
        ('reopened', _('Переоткрыт')),
    ]

    PRIORITY_CHOICES = [
        ('low', _('Низкий')),
        ('medium', _('Средний')),
        ('high', _('Высокий')),
        ('critical', _('Критический')),
    ]

    SOURCE_CHOICES = [
        ('form', _('Форма на сайте')),
        ('chat', _('Живой чат')),
        ('email', _('Email')),
        ('telegram', _('Telegram')),
        ('admin', _('Создан администратором')),
    ]

    CATEGORY_CHOICES = [
        ('finance', _('Финансы и платежи')),
        ('deposit', _('Проблема с депозитом')),
        ('withdrawal', _('Проблема с выводом')),
        ('account', _('Аккаунт и профиль')),
        ('verification', _('Верификация (KYC)')),
        ('sport_bet', _('Ставки на спорт')),
        ('casino', _('Казино')),
        ('prediction', _('Маркеты предсказаний')),
        ('referral', _('Партнёрская программа')),
        ('technical', _('Технические проблемы')),
        ('security', _('Безопасность')),
        ('complaint', _('Жалоба')),
        ('suggestion', _('Предложение')),
        ('other', _('Другое')),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket_number = models.CharField(max_length=20, unique=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tickets')
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    subject = models.CharField(max_length=200)
    description = models.TextField(max_length=5000)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='form')
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_tickets')
    assigned_at = models.DateTimeField(null=True, blank=True)
    assigned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    related_object_type = models.CharField(max_length=50, blank=True)
    related_object_id = models.UUIDField(null=True, blank=True)
    first_response_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    tags = models.JSONField(default=list)
    internal_notes = models.TextField(blank=True)
    rating = models.IntegerField(null=True, blank=True)
    rating_comment = models.TextField(blank=True, max_length=500)
    rated_at = models.DateTimeField(null=True, blank=True)
    is_escalated = models.BooleanField(default=False)
    escalated_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='escalated_tickets')
    escalated_at = models.DateTimeField(null=True, blank=True)
    escalation_reason = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Тикет')
        verbose_name_plural = _('Тикеты')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'priority', 'created_at']),
            models.Index(fields=['assigned_to', 'status']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['category', 'status']),
            models.Index(fields=['ticket_number']),
        ]

    def __str__(self):
        return f'{self.ticket_number}: {self.subject}'

    def save(self, *args, **kwargs):
        if not self.ticket_number:
            self.ticket_number = self.generate_ticket_number()
        super().save(*args, **kwargs)

    @staticmethod
    def generate_ticket_number():
        today = date.today().strftime('%Y%m%d')
        last = Ticket.objects.filter(ticket_number__startswith=f'DOD-{today}').count()
        return f'DOD-{today}-{last + 1:04d}'

    def time_since_creation(self):
        return tz.now() - self.created_at

    def time_to_first_response(self):
        if self.first_response_at:
            return self.first_response_at - self.created_at
        return None

    def time_to_resolution(self):
        if self.resolved_at:
            return self.resolved_at - self.created_at
        return None

    def is_sla_breached(self):
        sla = SLAConfig.get_for_priority(self.priority)
        if not self.first_response_at:
            return self.time_since_creation() > sla.first_response_time
        return False

    def can_reopen(self):
        if self.status != 'closed':
            return False
        return (tz.now() - self.closed_at).days <= 7


class Message(models.Model):
    SENDER_TYPE_CHOICES = [
        ('user', _('Пользователь')),
        ('operator', _('Оператор')),
        ('system', _('Система')),
        ('bot', _('Автоответ')),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    sender_type = models.CharField(max_length=20, choices=SENDER_TYPE_CHOICES)
    text = models.TextField(max_length=5000)
    is_system_message = models.BooleanField(default=False)
    system_action = models.CharField(max_length=50, blank=True)
    is_internal = models.BooleanField(default=False)
    is_read_by_user = models.BooleanField(default=False)
    is_read_by_operator = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    edited_at = models.DateTimeField(null=True, blank=True)
    is_edited = models.BooleanField(default=False)

    class Meta:
        verbose_name = _('Сообщение')
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['ticket', 'created_at']),
            models.Index(fields=['sender', 'created_at']),
        ]


class MessageAttachment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='support/attachments/{ticket_id}/')
    original_filename = models.CharField(max_length=255)
    file_size = models.IntegerField()
    file_type = models.CharField(max_length=50)
    is_image = models.BooleanField(default=False)
    thumbnail = models.ImageField(upload_to='support/attachments/thumbnails/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        if self.file_size > 10 * 1024 * 1024:  # 10MB
            raise ValidationError(_('Файл слишком большой (макс 10 МБ)'))
        allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain']
        if self.file_type not in allowed_types:
            raise ValidationError(_('Неподдерживаемый тип файла'))
        ticket_attachments = MessageAttachment.objects.filter(message__ticket=self.message.ticket).count()
        if ticket_attachments >= 20:
            raise ValidationError(_('Слишком много вложений в тикете (макс 20)'))


class ChatSession(models.Model):
    CHAT_STATUS_CHOICES = [
        ('waiting', _('Ожидание оператора')),
        ('active', _('Активный разговор')),
        ('idle', _('Неактивен')),
        ('ended', _('Завершён')),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket = models.OneToOneField(Ticket, on_delete=models.CASCADE, related_name='chat_session')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    operator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='chat_sessions')
    chat_status = models.CharField(max_length=20, choices=CHAT_STATUS_CHOICES, default='waiting')
    user_channel_name = models.CharField(max_length=255, blank=True)
    operator_channel_name = models.CharField(max_length=255, blank=True)
    queue_position = models.IntegerField(default=0)
    queue_entered_at = models.DateTimeField(null=True, blank=True)
    operator_joined_at = models.DateTimeField(null=True, blank=True)
    wait_time_seconds = models.IntegerField(default=0)
    messages_count = models.IntegerField(default=0)
    user_typing = models.BooleanField(default=False)
    operator_typing = models.BooleanField(default=False)
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    ended_by = models.CharField(max_length=20, blank=True)

    class Meta:
        verbose_name = _('Чат-сессия')
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['chat_status']),
            models.Index(fields=['operator', 'chat_status']),
        ]


class FAQCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    name_en = models.CharField(max_length=100, blank=True)
    slug = models.SlugField(unique=True)
    icon = models.CharField(max_length=10)
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    articles_count = models.IntegerField(default=0)

    class Meta:
        ordering = ['sort_order']

    def __str__(self):
        return self.name


class FAQArticle(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.ForeignKey(FAQCategory, on_delete=models.CASCADE, related_name='articles')
    question = models.CharField(max_length=300)
    question_en = models.CharField(max_length=300, blank=True)
    answer = models.TextField(max_length=10000)
    answer_en = models.TextField(blank=True)
    slug = models.SlugField(unique=True)
    meta_description = models.CharField(max_length=200, blank=True)
    views_count = models.IntegerField(default=0)
    helpful_yes = models.IntegerField(default=0)
    helpful_no = models.IntegerField(default=0)
    related_ticket_categories = models.JSONField(default=list)
    keywords = models.JSONField(default=list)
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    is_pinned = models.BooleanField(default=False)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('FAQ статья')
        ordering = ['-is_pinned', 'sort_order', '-views_count']
        indexes = [
            models.Index(fields=['category', 'is_active', 'sort_order']),
            models.Index(fields=['is_active', 'views_count']),
        ]

    def __str__(self):
        return self.question


class QuickReply(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=100)
    text = models.TextField(max_length=3000)
    category = models.CharField(max_length=50, blank=True)
    is_global = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    usage_count = models.IntegerField(default=0)
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Быстрый ответ')
        ordering = ['-usage_count']

    def __str__(self):
        return self.title


class SLAConfig(models.Model):
    priority = models.CharField(max_length=20, primary_key=True)
    first_response_minutes = models.IntegerField()
    resolution_minutes = models.IntegerField()
    chat_response_seconds = models.IntegerField()
    business_hours_only = models.BooleanField(default=True)

    class Meta:
        verbose_name = _('Настройки SLA')

    @classmethod
    def get_for_priority(cls, priority):
        config = cls.objects.filter(priority=priority).first()
        if not config:
            # Default values
            defaults = {
                'low': {'first_response_minutes': 480, 'resolution_minutes': 2880, 'chat_response_seconds': 300, 'business_hours_only': True},
                'medium': {'first_response_minutes': 240, 'resolution_minutes': 1440, 'chat_response_seconds': 120, 'business_hours_only': True},
                'high': {'first_response_minutes': 60, 'resolution_minutes': 480, 'chat_response_seconds': 60, 'business_hours_only': False},
                'critical': {'first_response_minutes': 15, 'resolution_minutes': 120, 'chat_response_seconds': 30, 'business_hours_only': False},
            }
            return cls(**defaults.get(priority, defaults['medium']))
        return config


class OperatorProfile(models.Model):
    STATUS_CHOICES = [
        ('online', _('На линии')),
        ('busy', _('Занят')),
        ('away', _('Отошёл')),
        ('offline', _('Оффлайн')),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='operator_profile')
    operator_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='offline')
    max_concurrent_chats = models.IntegerField(default=5)
    current_chats_count = models.IntegerField(default=0)
    current_tickets_count = models.IntegerField(default=0)
    categories = models.JSONField(default=list)
    can_handle_critical = models.BooleanField(default=False)
    can_escalate = models.BooleanField(default=True)
    can_close_tickets = models.BooleanField(default=True)
    can_transfer = models.BooleanField(default=True)
    total_tickets_handled = models.IntegerField(default=0)
    total_chats_handled = models.IntegerField(default=0)
    avg_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    total_ratings = models.IntegerField(default=0)
    avg_first_response_seconds = models.IntegerField(default=0)
    avg_resolution_seconds = models.IntegerField(default=0)
    shift_start = models.TimeField(null=True, blank=True)
    shift_end = models.TimeField(null=True, blank=True)
    last_status_change = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Профиль оператора')

    def is_available(self):
        return (
            self.operator_status == 'online'
            and self.current_chats_count < self.max_concurrent_chats
        )

    def accept_chat(self):
        self.current_chats_count += 1
        self.save(update_fields=['current_chats_count'])

    def release_chat(self):
        self.current_chats_count = max(0, self.current_chats_count - 1)
        self.save(update_fields=['current_chats_count'])


class AutoResponse(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    trigger_keywords = models.JSONField()
    trigger_categories = models.JSONField(default=list)
    response_text = models.TextField(max_length=3000)
    related_faq = models.ForeignKey(FAQArticle, on_delete=models.SET_NULL, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    priority = models.IntegerField(default=0)
    times_triggered = models.IntegerField(default=0)
    times_resolved = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Автоответ')
        ordering = ['-priority']
