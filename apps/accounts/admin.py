from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import (
    User,
    LoginHistory,
    ActiveSession,
    EmailVerification,
    PhoneVerification,
    BackupCode,
)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    model = User
    list_display = (
        'email', 'username', 'balance', 'preferred_currency', 'trust_level', 'kyc_status',
        'is_email_verified', 'is_2fa_enabled', 'is_online', 'registration_method', 'created_at'
    )
    list_filter = (
        'is_active', 'is_email_verified', 'is_phone_verified', 'is_2fa_enabled', 'kyc_status',
        'trust_level', 'registration_method', 'country', 'language', 'created_at'
    )
    search_fields = ('email', 'username', 'phone', 'first_name', 'last_name', 'referral_code')
    readonly_fields = ('id', 'created_at', 'updated_at', 'registration_ip', 'last_login_ip', 'registration_method', 'referral_code')
    fieldsets = (
        ('Основная информация', {'fields': ('email', 'username', 'password')}),
        ('Личные данные', {'fields': ('first_name', 'last_name', 'date_of_birth', 'country', 'language', 'timezone')}),
        ('Контакты', {'fields': ('phone', 'is_phone_verified', 'is_email_verified')}),
        ('Безопасность', {'fields': ('is_2fa_enabled', 'two_fa_method', 'kyc_status', 'trust_level', 'is_active', 'is_staff', 'is_superuser')}),
        ('Баланс', {'fields': ('balance', 'preferred_currency')}),
        ('Метаданные', {'fields': ('registration_ip', 'last_login_ip', 'registration_method', 'referral_code', 'notification_settings')}),
        ('Даты', {'fields': ('last_login', 'created_at', 'updated_at')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'password1', 'password2', 'is_staff', 'is_superuser', 'is_email_verified')
        }),
    )
    ordering = ('-created_at',)


@admin.register(LoginHistory)
class LoginHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'ip_address', 'country', 'device_type', 'login_method', 'is_successful', 'is_suspicious', 'created_at')
    list_filter = ('is_successful', 'is_suspicious', 'device_type', 'login_method', 'country')
    search_fields = ('user__email', 'ip_address', 'user_agent')
    readonly_fields = ('user', 'ip_address', 'country', 'city', 'device_type', 'browser', 'os', 'device_name', 'user_agent', 'login_method', 'is_successful', 'failure_reason', 'is_suspicious', 'session_key', 'created_at')


@admin.register(ActiveSession)
class ActiveSessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'session_key', 'ip_address', 'device_type', 'is_current', 'last_activity')
    list_filter = ('device_type', 'is_current')
    search_fields = ('user__email', 'session_key', 'ip_address')
    readonly_fields = ('user', 'session_key', 'ip_address', 'device_type', 'browser', 'os', 'device_name', 'country', 'is_current', 'last_activity', 'created_at')


@admin.register(EmailVerification)
class EmailVerificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'email', 'token', 'is_used', 'expires_at', 'created_at')
    list_filter = ('is_used',)
    search_fields = ('email', 'token', 'user__email')
    readonly_fields = ('user', 'email', 'token', 'is_used', 'expires_at', 'created_at')


@admin.register(PhoneVerification)
class PhoneVerificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'code', 'is_used', 'attempts', 'expires_at', 'created_at')
    list_filter = ('is_used',)
    search_fields = ('phone', 'user__email')
    readonly_fields = ('user', 'phone', 'code', 'is_used', 'attempts', 'expires_at', 'created_at')


@admin.register(BackupCode)
class BackupCodeAdmin(admin.ModelAdmin):
    list_display = ('user', 'is_used', 'created_at', 'used_at')
    list_filter = ('is_used',)
    search_fields = ('user__email',)
    readonly_fields = ('user', 'code', 'is_used', 'created_at', 'used_at')
