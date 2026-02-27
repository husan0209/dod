from django.contrib import admin
from django.contrib.admin import ModelAdmin
from django.utils.translation import gettext_lazy as _
from .models import (
    Ticket, Message, MessageAttachment, ChatSession,
    FAQCategory, FAQArticle, QuickReply, SLAConfig,
    OperatorProfile, AutoResponse
)


@admin.register(Ticket)
class TicketAdmin(ModelAdmin):
    list_display = ['ticket_number', 'user', 'category', 'priority', 'status', 'assigned_to', 'created_at']
    list_filter = ['status', 'priority', 'category', 'source', 'is_escalated', 'created_at']
    search_fields = ['ticket_number', 'subject', 'user__username', 'user__email']
    readonly_fields = ['ticket_number', 'created_at', 'updated_at']
    ordering = ['-created_at']
    actions = ['assign_to_me', 'mark_resolved', 'mark_closed']

    def assign_to_me(self, request, queryset):
        queryset.update(assigned_to=request.user)
        self.message_user(request, _("Selected tickets assigned to you."))
    assign_to_me.short_description = _("Assign selected tickets to me")

    def mark_resolved(self, request, queryset):
        queryset.update(status='resolved', resolved_at=timezone.now())
        self.message_user(request, _("Selected tickets marked as resolved."))
    mark_resolved.short_description = _("Mark selected tickets as resolved")

    def mark_closed(self, request, queryset):
        queryset.update(status='closed', closed_at=timezone.now())
        self.message_user(request, _("Selected tickets marked as closed."))
    mark_closed.short_description = _("Mark selected tickets as closed")


@admin.register(Message)
class MessageAdmin(ModelAdmin):
    list_display = ['ticket', 'sender', 'sender_type', 'created_at', 'is_system_message', 'is_internal']
    list_filter = ['sender_type', 'is_system_message', 'is_internal', 'created_at']
    search_fields = ['text', 'sender__username', 'ticket__ticket_number']
    readonly_fields = ['created_at', 'edited_at']
    ordering = ['-created_at']


@admin.register(MessageAttachment)
class MessageAttachmentAdmin(ModelAdmin):
    list_display = ['message', 'original_filename', 'file_size', 'file_type', 'created_at']
    list_filter = ['file_type', 'is_image', 'created_at']
    search_fields = ['original_filename', 'message__ticket__ticket_number']
    readonly_fields = ['created_at']


@admin.register(ChatSession)
class ChatSessionAdmin(ModelAdmin):
    list_display = ['ticket', 'user', 'operator', 'chat_status', 'started_at', 'ended_at']
    list_filter = ['chat_status', 'started_at', 'ended_at']
    search_fields = ['ticket__ticket_number', 'user__username', 'operator__username']
    readonly_fields = ['started_at', 'ended_at']


@admin.register(FAQCategory)
class FAQCategoryAdmin(ModelAdmin):
    list_display = ['name', 'slug', 'sort_order', 'is_active', 'articles_count']
    list_filter = ['is_active']
    search_fields = ['name', 'name_en', 'slug']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(FAQArticle)
class FAQArticleAdmin(ModelAdmin):
    list_display = ['question', 'category', 'is_active', 'is_pinned', 'views_count', 'helpful_yes', 'helpful_no']
    list_filter = ['is_active', 'is_pinned', 'category', 'created_at']
    search_fields = ['question', 'question_en', 'answer', 'answer_en']
    prepopulated_fields = {'slug': ('question',)}
    readonly_fields = ['views_count', 'helpful_yes', 'helpful_no', 'created_at', 'updated_at']


@admin.register(QuickReply)
class QuickReplyAdmin(ModelAdmin):
    list_display = ['title', 'category', 'is_global', 'usage_count', 'is_active']
    list_filter = ['is_active', 'is_global', 'category', 'created_at']
    search_fields = ['title', 'text']
    readonly_fields = ['usage_count', 'created_at']


@admin.register(SLAConfig)
class SLAConfigAdmin(ModelAdmin):
    list_display = ['priority', 'first_response_minutes', 'resolution_minutes', 'chat_response_seconds', 'business_hours_only']
    list_editable = ['first_response_minutes', 'resolution_minutes', 'chat_response_seconds', 'business_hours_only']


@admin.register(OperatorProfile)
class OperatorProfileAdmin(ModelAdmin):
    list_display = ['user', 'operator_status', 'max_concurrent_chats', 'current_chats_count', 'current_tickets_count', 'avg_rating', 'can_handle_critical']
    list_filter = ['operator_status', 'can_handle_critical', 'last_status_change']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['total_tickets_handled', 'total_chats_handled', 'avg_rating', 'total_ratings', 'avg_first_response_seconds', 'avg_resolution_seconds', 'last_status_change']


@admin.register(AutoResponse)
class AutoResponseAdmin(ModelAdmin):
    list_display = ['name', 'is_active', 'priority', 'times_triggered', 'times_resolved']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'response_text']
    readonly_fields = ['times_triggered', 'times_resolved', 'created_at']
