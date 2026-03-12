from django.contrib import admin
from django.utils.html import format_html
from .models import (
    PartnerTier, PartnerProfile, Referral, Commission,
    PartnerPayout, PromoLink, PromoLinkClick, NegativeCarryover,
    ReferralSettings
)


@admin.register(PartnerTier)
class PartnerTierAdmin(admin.ModelAdmin):
    list_display = ('icon_name', 'sort_order', 'commission_display', 'min_referrals', 'is_active')
    list_editable = ('is_active', 'sort_order')
    search_fields = ('name', 'name_en')
    ordering = ('sort_order',)
    
    def icon_name(self, obj):
        return format_html(f"{obj.icon} {obj.name}")
    icon_name.short_description = "Уровень"
    
    def commission_display(self, obj):
        return f"{obj.commission_rate_month_1}% → {obj.commission_rate_month_4_plus}%"
    commission_display.short_description = "Комиссия (мес1-4+)"


@admin.register(PartnerProfile)
class PartnerProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'tier_icon', 'balance_display', 'earned_display', 'referrals_display', 'status')
    list_filter = ('tier', 'is_partner_active', 'is_suspended', 'partner_since')
    search_fields = ('user__email', 'user__username')
    raw_id_fields = ('user', 'tier')
    readonly_fields = ('total_earned', 'total_withdrawn', 'partner_since', 'created_at', 'updated_at')
    fieldsets = (
        ('Профиль', {
            'fields': ('user', 'tier', 'custom_slug', 'is_partner_active', 'is_suspended', 'suspension_reason')
        }),
        ('Баланс', {
            'fields': ('balance', 'total_earned', 'total_withdrawn', 'last_payout_at'),
            'classes': ('collapse',)
        }),
        ('Статистика', {
            'fields': ('total_referrals', 'active_referrals', 'referrals_with_deposit', 
                      'monthly_ggr', 'monthly_earned', 'monthly_referrals', 'total_level2_referrals'),
            'classes': ('collapse',)
        }),
        ('О партнёре', {
            'fields': ('bio', 'website_url', 'telegram_channel'),
            'classes': ('collapse',)
        }),
        ('Даты', {
            'fields': ('partner_since', 'tier_changed_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def tier_icon(self, obj):
        return f"{obj.tier.icon} {obj.tier.name}"
    tier_icon.short_description = "Уровень"
    
    def balance_display(self, obj):
        return format_html(f"<b>${obj.balance:.2f}</b>")
    balance_display.short_description = "Баланс"
    
    def earned_display(self, obj):
        return f"${obj.total_earned:.2f}"
    earned_display.short_description = "Заработано"
    
    def referrals_display(self, obj):
        return f"{obj.total_referrals} ({obj.referrals_with_deposit} депозит)"
    referrals_display.short_description = "Рефералы"
    
    def status(self, obj):
        if obj.is_suspended:
            return format_html('<span style="color: red;">🔒 Приостановлен</span>')
        elif obj.is_partner_active:
            return format_html('<span style="color: green;">✅ Активен</span>')
        return format_html('<span style="color: gray;">❌ Неактивен</span>')
    status.short_description = "Статус"


@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    list_display = ('referral_name', 'partner_name', 'status_badge', 'deposits_display', 'ggr_display', 'commission_display', 'qualified_badge')
    list_filter = ('status', 'level', 'is_qualified', 'is_suspicious', 'registered_at')
    search_fields = ('partner__email', 'referral__email', 'referral__username')
    raw_id_fields = ('partner', 'referral', 'promo_link')
    readonly_fields = ('registered_at', 'created_at', 'updated_at', 'qualified_at')
    fieldsets = (
        ('Связь', {
            'fields': ('partner', 'referral', 'level')
        }),
        ('Регистрация', {
            'fields': ('referral_code_used', 'promo_link', 'registration_ip', 'registration_country', 'registration_device', 'registered_at')
        }),
        ('Финансы', {
            'fields': ('total_deposits', 'first_deposit_amount', 'first_deposit_at', 'total_bets', 'total_ggr', 'total_winnings', 'total_commission_earned')
        }),
        ('Статус', {
            'fields': ('status', 'is_active', 'last_active_at')
        }),
        ('Квалификация', {
            'fields': ('is_qualified', 'qualified_at'),
            'classes': ('collapse',)
        }),
        ('Антифрод', {
            'fields': ('is_suspicious', 'fraud_flags'),
            'classes': ('collapse',)
        }),
        ('Мета', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def referral_name(self, obj):
        return f"{obj.referral.username} ({obj.referral.email})"
    referral_name.short_description = "Реферал"
    
    def partner_name(self, obj):
        return f"{obj.partner.username}"
    partner_name.short_description = "Партнёр"
    
    def status_badge(self, obj):
        colors = {
            'active': 'green',
            'deposited': 'blue',
            'registered': 'gray',
            'churned': 'orange',
            'fraud': 'red',
            'blocked': 'red'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(f'<span style="color: {color};"><b>{obj.get_status_display()}</b></span>')
    status_badge.short_description = "Статус"
    
    def deposits_display(self, obj):
        if obj.total_deposits > 0:
            return format_html(f'<span style="color: green;">${obj.total_deposits:.2f}</span>')
        return "-"
    deposits_display.short_description = "Депозиты"
    
    def ggr_display(self, obj):
        return f"${obj.total_ggr:.2f}"
    ggr_display.short_description = "GGR"
    
    def commission_display(self, obj):
        return format_html(f'<b style="color: green;">${obj.total_commission_earned:.2f}</b>')
    commission_display.short_description = "Комиссия"
    
    def qualified_badge(self, obj):
        if obj.is_qualified:
            return format_html('<span style="background: green; color: white; padding: 3px 6px; border-radius: 3px;">✅ Квалифицирован</span>')
        return "-"
    qualified_badge.short_description = "Квалификация"


@admin.register(Commission)
class CommissionAdmin(admin.ModelAdmin):
    list_display = ('partner_display', 'referral_display', 'period_display', 'commission_type_badge', 'amount_display', 'status_badge')
    list_filter = ('commission_type', 'status', 'period_start')
    search_fields = ('partner__email', 'referral__referral__email')
    raw_id_fields = ('partner', 'referral', 'payout')
    readonly_fields = ('created_at', 'created_by')
    fieldsets = (
        ('Комиссия', {
            'fields': ('partner', 'referral', 'commission_type', 'period_start', 'period_end')
        }),
        ('Расчёт', {
            'fields': ('referral_ggr', 'commission_rate', 'gross_amount', 'adjustments', 'net_amount')
        }),
        ('Статус', {
            'fields': ('status', 'payout')
        }),
        ('Доп. информация', {
            'fields': ('notes', 'created_by', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    def partner_display(self, obj):
        return f"{obj.partner.username}"
    partner_display.short_description = "Партнёр"
    
    def referral_display(self, obj):
        return f"{obj.referral.referral.username}"
    referral_display.short_description = "Реферал"
    
    def period_display(self, obj):
        return f"{obj.period_start.strftime('%d.%m')} - {obj.period_end.strftime('%d.%m.%y')}"
    period_display.short_description = "Период"
    
    def commission_type_badge(self, obj):
        colors = {
            'ggr': 'purple',
            'signup_bonus': 'blue',
            'first_deposit': 'green',
            'level2_ggr': 'indigo',
            'manual': 'orange'
        }
        color = colors.get(obj.commission_type, 'gray')
        type_labels = {
            'ggr': 'GGR',
            'signup_bonus': 'Регистрация',
            'first_deposit': '1-й дн',
            'level2_ggr': '2-й уров',
            'manual': 'Ручной'
        }
        label = type_labels.get(obj.commission_type, obj.commission_type)
        return format_html(f'<span style="background: {color}; color: white; padding: 3px 6px; border-radius: 3px;">{label}</span>')
    commission_type_badge.short_description = "Тип"
    
    def amount_display(self, obj):
        color = 'green' if obj.net_amount > 0 else 'gray'
        return format_html(f'<span style="color: {color}; font-weight: bold;">${obj.net_amount:.2f}</span>')
    amount_display.short_description = "Сумма"
    
    def status_badge(self, obj):
        colors = {
            'approved': 'green',
            'pending': 'orange',
            'paid': 'blue',
            'cancelled': 'red',
            'held': 'purple'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(f'<span style="color: {color};"><b>{obj.get_status_display()}</b></span>')
    status_badge.short_description = "Статус"


@admin.register(PartnerPayout)
class PartnerPayoutAdmin(admin.ModelAdmin):
    list_display = ('partner_display', 'amount_display', 'method_badge', 'status_badge', 'created_display')
    list_filter = ('payout_method', 'status', 'created_at')
    search_fields = ('partner__email', 'partner__username')
    raw_id_fields = ('partner', 'processed_by')
    readonly_fields = ('created_at',)
    fieldsets = (
        ('Выплата', {
            'fields': ('partner', 'amount', 'fee', 'net_amount')
        }),
        ('Детали', {
            'fields': ('payout_method', 'payout_details', 'ip_address')
        }),
        ('Обработка', {
            'fields': ('status', 'processed_by', 'processed_at', 'rejection_reason'),
            'classes': ('collapse',)
        }),
        ('Мета', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def partner_display(self, obj):
        return f"{obj.partner.username} ({obj.partner.email})"
    partner_display.short_description = "Партнёр"
    
    def amount_display(self, obj):
        return format_html(f'<b>${obj.amount:.2f}</b>')
    amount_display.short_description = "Сумма"
    
    def method_badge(self, obj):
        colors = {
            'game_balance': 'blue',
            'wallet': 'purple',
            'usdt': 'orange',
            'bank_card': 'green'
        }
        methods = {
            'game_balance': '💳 Игра',
            'wallet': '🏦 Кошелёк',
            'usdt': '₿ USDT',
            'bank_card': '💰 Карта'
        }
        color = colors.get(obj.payout_method, 'gray')
        method = methods.get(obj.payout_method, obj.payout_method)
        return format_html(f'<span style="background: {color}; color: white; padding: 3px 6px; border-radius: 3px;">{method}</span>')
    method_badge.short_description = "Метод"
    
    def status_badge(self, obj):
        colors = {
            'completed': 'green',
            'processing': 'blue',
            'pending': 'orange',
            'rejected': 'red',
            'cancelled': 'gray'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(f'<span style="color: {color};"><b>{obj.get_status_display()}</b></span>')
    status_badge.short_description = "Статус"
    
    def created_display(self, obj):
        return obj.created_at.strftime('%d.%m.%y %H:%M')
    created_display.short_description = "Дата"


@admin.register(PromoLink)
class PromoLinkAdmin(admin.ModelAdmin):
    list_display = ('name_display', 'partner_display', 'stats_display', 'conversion_display', 'is_active_badge')
    list_filter = ('is_active', 'created_at')
    search_fields = ('partner__email', 'name', 'slug')
    raw_id_fields = ('partner',)
    readonly_fields = ('clicks', 'registrations', 'deposits', 'created_at', 'updated_at')
    fieldsets = (
        ('Ссылка', {
            'fields': ('partner', 'name', 'slug')
        }),
        ('UTM параметры', {
            'fields': ('utm_source', 'utm_medium', 'utm_campaign'),
            'classes': ('collapse',)
        }),
        ('Статистика', {
            'fields': ('clicks', 'registrations', 'deposits', 'conversion_rate', 'deposit_rate', 'total_deposit_amount', 'total_ggr', 'total_earned')
        }),
        ('Статус', {
            'fields': ('is_active',)
        }),
        ('Мета', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def name_display(self, obj):
        return format_html(f'<a href="{obj.get_full_url()}" target="_blank">{obj.name}</a>')
    name_display.short_description = "Ссылка"
    
    def partner_display(self, obj):
        return f"{obj.partner.username}"
    partner_display.short_description = "Партнёр"
    
    def stats_display(self, obj):
        return f"👀 {obj.clicks} | 📝 {obj.registrations} | 💰 {obj.deposits}"
    stats_display.short_description = "Статистика"
    
    def conversion_display(self, obj):
        if obj.clicks > 0:
            return f"{obj.conversion_rate:.1f}% → {obj.deposit_rate:.1f}%"
        return "-"
    conversion_display.short_description = "Конверсия"
    
    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html('<span style="color: green;">✅ Активна</span>')
        return format_html('<span style="color: red;">⛔ Отключена</span>')
    is_active_badge.short_description = "Статус"


@admin.register(PromoLinkClick)
class PromoLinkClickAdmin(admin.ModelAdmin):
    list_display = ('promo_link', 'ip_display', 'device_type_badge', 'unique_badge', 'registration_badge', 'created_display')
    list_filter = ('is_unique', 'resulted_in_registration', 'created_at')
    search_fields = ('promo_link__slug', 'ip_address')
    raw_id_fields = ('promo_link', 'user_registered')
    readonly_fields = ('created_at',)
    
    def ip_display(self, obj):
        return format_html(f'<code>{obj.ip_address}</code>')
    ip_display.short_description = "IP"
    
    def device_type_badge(self, obj):
        colors = {'desktop': 'blue', 'mobile': 'orange', 'tablet': 'green'}
        color = colors.get(obj.device_type, 'gray')
        return format_html(f'<span style="background: {color}; color: white; padding: 3px 6px; border-radius: 3px;">{obj.device_type}</span>')
    device_type_badge.short_description = "Устройство"
    
    def unique_badge(self, obj):
        if obj.is_unique:
            return format_html('<span style="color: green;">✅ Уникален</span>')
        return format_html('<span style="color: orange;">↩️ Повтор</span>')
    unique_badge.short_description = "Уникальность"
    
    def registration_badge(self, obj):
        if obj.resulted_in_registration:
            return format_html('<span style="color: green;">✅ Регистрация</span>')
        return "-"
    registration_badge.short_description = "Результат"
    
    def created_display(self, obj):
        return obj.created_at.strftime('%d.%m.%y %H:%M')
    created_display.short_description = "Дата"


@admin.register(NegativeCarryover)
class NegativeCarryoverAdmin(admin.ModelAdmin):
    list_display = ('partner_display', 'referral_display', 'amount_display')
    search_fields = ('partner__email', 'referral__referral__email')
    raw_id_fields = ('partner', 'referral')
    
    def partner_display(self, obj):
        return f"{obj.partner.username}"
    partner_display.short_description = "Партнёр"
    
    def referral_display(self, obj):
        return f"{obj.referral.referral.username}"
    referral_display.short_description = "Реферал"
    
    def amount_display(self, obj):
        return format_html(f'<span style="color: red;">${obj.amount:.2f}</span>')
    amount_display.short_description = "Перенос"


@admin.register(ReferralSettings)
class ReferralSettingsAdmin(admin.ModelAdmin):
    list_display = ('commission_period', 'min_deposit_to_qualify', 'level2_enabled')
    fieldsets = (
        ('Квалификация', {
            'fields': ('min_deposit_to_qualify', 'min_bets_to_qualify', 'min_wagered_to_qualify')
        }),
        ('Расчёт', {
            'fields': ('commission_period',)
        }),
        ('Ограничения', {
            'fields': ('max_referrals_per_ip', 'max_referrals_per_day', 'min_time_between_registrations'),
            'classes': ('collapse',)
        }),
        ('Антифрод', {
            'fields': ('suspicious_patterns_enabled', 'auto_block_on_fraud'),
            'classes': ('collapse',)
        }),
        ('Многоуровневость', {
            'fields': ('level2_enabled',),
            'classes': ('collapse',)
        }),
        ('Методы вывода', {
            'fields': ('payout_to_game_balance', 'payout_to_wallet', 'payout_direct_crypto'),
            'classes': ('collapse',)
        }),
    )
    def has_add_permission(self, request):
        return not ReferralSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
