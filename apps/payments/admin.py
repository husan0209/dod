from django.contrib import admin

from apps.payments.models import (
    PaymentProvider,
    PaymentMethod,
    DepositOrder,
    PayoutOrder,
    WebhookLog,
    SavedPaymentMethod,
    PaymentSettings,
)


@admin.register(PaymentProvider)
class PaymentProviderAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "type",
        "is_active",
        "is_deposit_enabled",
        "is_withdrawal_enabled",
    )
    list_editable = ("is_active", "is_deposit_enabled", "is_withdrawal_enabled")
    readonly_fields = ("api_key", "api_secret", "webhook_secret")


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "provider",
        "code",
        "currency",
        "type",
        "min_amount",
        "max_amount",
        "fee_percent",
        "is_active",
    )
    list_filter = ("provider", "type", "is_active", "currency")
    list_editable = ("is_active", "fee_percent", "min_amount", "max_amount")


@admin.register(DepositOrder)
class DepositOrderAdmin(admin.ModelAdmin):
    list_display = ("order_id", "user", "provider", "currency", "amount", "status", "created_at")
    list_filter = ("status", "provider", "currency", "created_at")
    search_fields = ("order_id", "user__email", "provider_order_id")
    readonly_fields = ("provider_response", "transaction")
    date_hierarchy = "created_at"

    actions = ["mark_completed", "mark_cancelled", "mark_refunded"]

    def mark_completed(self, request, queryset):
        queryset.update(status="completed")

    mark_completed.short_description = "Ручное подтверждение"

    def mark_cancelled(self, request, queryset):
        queryset.update(status="cancelled")

    mark_cancelled.short_description = "Отменить"

    def mark_refunded(self, request, queryset):
        queryset.update(status="refunded")

    mark_refunded.short_description = "Вернуть средства"


@admin.register(PayoutOrder)
class PayoutOrderAdmin(admin.ModelAdmin):
    list_display = (
        "payout_id",
        "user",
        "provider",
        "currency",
        "amount",
        "status",
        "retry_count",
        "created_at",
    )
    list_filter = ("status", "provider", "currency")
    search_fields = ("payout_id", "user__email")
    readonly_fields = ("provider_response", "payment_details")

    actions = ["retry_send", "cancel_payout"]

    def retry_send(self, request, queryset):
        updated = 0
        for payout in queryset:
            if payout.can_retry():
                payout.retry_count += 1
                payout.status = "processing"
                payout.save(update_fields=["retry_count", "status", "updated_at"])
                updated += 1
        self.message_user(request, f"Повторно отправлено: {updated}")

    retry_send.short_description = "Повторить отправку"

    def cancel_payout(self, request, queryset):
        count = queryset.update(status="cancelled")
        self.message_user(request, f"Отменено и вернуть средства: {count}")

    cancel_payout.short_description = "Отменить и вернуть"


@admin.register(WebhookLog)
class WebhookLogAdmin(admin.ModelAdmin):
    list_display = (
        "provider",
        "event_type",
        "is_valid_signature",
        "is_processed",
        "processing_result",
        "related_order_id",
        "created_at",
    )
    list_filter = ("provider", "is_valid_signature", "is_processed", "processing_result")
    search_fields = ("related_order_id",)
    readonly_fields = [f.name for f in WebhookLog._meta.fields]


@admin.register(SavedPaymentMethod)
class SavedPaymentMethodAdmin(admin.ModelAdmin):
    list_display = ("user", "type", "name", "currency", "is_verified", "is_default")
    list_filter = ("type", "currency", "is_verified")
    search_fields = ("user__email", "name")
    readonly_fields = ("details",)


@admin.register(PaymentSettings)
class PaymentSettingsAdmin(admin.ModelAdmin):
    list_display = (
        "deposit_enabled",
        "withdrawal_enabled",
        "auto_payout_enabled",
        "auto_payout_max_amount_usd",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(singleton_id=1)
