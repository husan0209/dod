from django.contrib import admin
from django.contrib import messages
from django.http import HttpRequest
from import_export.admin import ImportExportModelAdmin

from .models import (
    ConversionOrder,
    Currency,
    KYCVerification,
    Transaction,
    Wallet,
    WalletBalance,
    WalletSettings,
    WithdrawalRequest,
)
from apps.wallet.services.withdrawal_service import WithdrawalService, WithdrawalValidationError


class WalletBalanceInline(admin.TabularInline):
    model = WalletBalance
    extra = 0
    readonly_fields = ("available", "frozen")


@admin.register(Currency)
class CurrencyAdmin(ImportExportModelAdmin):
    list_display = (
        "code",
        "name",
        "symbol",
        "type",
        "rate_to_usd",
        "min_deposit",
        "min_withdrawal",
        "is_active",
        "is_deposit_enabled",
        "is_withdrawal_enabled",
    )
    list_filter = ("type", "is_active")
    list_editable = (
        "rate_to_usd",
        "is_active",
        "is_deposit_enabled",
        "is_withdrawal_enabled",
        "min_deposit",
        "min_withdrawal",
    )
    search_fields = ("code", "name")


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "primary_currency",
        "total_deposited",
        "total_withdrawn",
        "is_frozen",
        "created_at",
    )
    list_filter = ("is_frozen", "primary_currency")
    search_fields = ("user__email", "user__username")
    readonly_fields = ("total_deposited", "total_withdrawn", "total_wagered", "total_won")
    inlines = [WalletBalanceInline]


@admin.register(Transaction)
class TransactionAdmin(ImportExportModelAdmin):
    list_display = ("transaction_id", "user", "type", "currency", "amount", "status", "created_at")
    list_filter = ("type", "status", "currency", "created_at")
    search_fields = ("transaction_id", "user__email", "description")
    readonly_fields = [field.name for field in Transaction._meta.fields]
    date_hierarchy = "created_at"

    def has_add_permission(self, request: HttpRequest) -> bool:  # noqa: D401
        """Запрет добавления транзакций вручную."""
        return False


@admin.register(WithdrawalRequest)
class WithdrawalRequestAdmin(admin.ModelAdmin):
    list_display = ("request_id", "user", "currency", "amount", "status", "risk_level", "created_at")
    list_filter = ("status", "risk_level", "currency", "created_at")
    search_fields = ("request_id", "user__email")
    readonly_fields = ("risk_factors", "ip_address", "user_agent")

    actions = ["bulk_approve", "bulk_reject"]

    def bulk_approve(self, request: HttpRequest, queryset):
        count = 0
        for req in queryset:
            if req.status not in {"pending", "manual_review"}:
                continue
            try:
                WithdrawalService.approve_withdrawal(str(req.id), request.user, comment="Approved via bulk")
                count += 1
            except WithdrawalValidationError:
                continue
        messages.success(request, f"Одобрено заявок: {count}")

    bulk_approve.short_description = "Одобрить выбранные"

    def bulk_reject(self, request: HttpRequest, queryset):
        count = 0
        for req in queryset:
            if req.status not in {"pending", "manual_review"}:
                continue
            try:
                WithdrawalService.reject_withdrawal(str(req.id), request.user, reason="bulk_reject", comment="Rejected via bulk")
                count += 1
            except WithdrawalValidationError:
                continue
        messages.success(request, f"Отклонено заявок: {count}")

    bulk_reject.short_description = "Отклонить выбранные"


@admin.register(KYCVerification)
class KYCVerificationAdmin(admin.ModelAdmin):
    list_display = ("user", "status", "document_type", "submitted_at", "reviewed_by")
    list_filter = ("status", "document_type", "country_of_issue")
    search_fields = ("user__email", "full_name")
    readonly_fields = (
        "document_front",
        "document_back",
        "selfie_with_document",
    )


@admin.register(WalletSettings)
class WalletSettingsAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        # Singleton: запрещаем создавать больше одной записи
        return not WalletSettings.objects.exists()


@admin.register(ConversionOrder)
class ConversionOrderAdmin(admin.ModelAdmin):
    list_display = ("wallet", "from_currency", "to_currency", "from_amount", "to_amount", "status", "created_at")
    list_filter = ("status", "from_currency", "to_currency")
    search_fields = ("wallet__user__email",)
