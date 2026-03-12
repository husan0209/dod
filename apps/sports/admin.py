from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from .models import (
    Sport, Country, League, Team, Event, Market, MarketType,
    Outcome, Bet, BetItem, BetSettings, OddHistory
)


@admin.register(Sport)
class SportAdmin(admin.ModelAdmin):
    list_display = ['icon', 'name', 'slug', 'events_count', 'is_active', 'is_popular', 'sort_order']
    list_editable = ['is_active', 'is_popular', 'sort_order']
    prepopulated_fields = {'slug': ('name_en',)}
    list_filter = ['is_active', 'is_popular']
    search_fields = ['name', 'name_en', 'slug']


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ['flag', 'name', 'code', 'sort_order', 'is_active']
    list_editable = ['is_active', 'sort_order']
    list_filter = ['is_active']
    search_fields = ['name', 'name_en', 'code']


@admin.register(League)
class LeagueAdmin(admin.ModelAdmin):
    list_display = ['name', 'sport', 'country', 'season', 'events_count', 'is_active', 'is_popular']
    list_filter = ['sport', 'country', 'is_active', 'is_popular', 'season']
    search_fields = ['name', 'name_en']
    list_editable = ['is_active', 'is_popular']


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ['name', 'sport', 'country', 'is_active']
    list_filter = ['sport', 'country']
    search_fields = ['name', 'name_en']


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = [
        'event_display', 'sport', 'league', 'start_time_display', 'status_badge',
        'score_display', 'markets_count',
        'bets_count', 'total_stake_display', 'is_featured'
    ]
    list_filter = ['sport', 'league', 'status', 'is_featured', 'data_source', 'start_time']
    search_fields = ['name', 'home_team__name', 'away_team__name']
    date_hierarchy = 'start_time'
    readonly_fields = ['bets_count', 'total_stake', 'views_count', 'id']
    list_editable = ['is_featured']

    fieldsets = (
        (_('Основная информация'), {
            'fields': ('id', 'sport', 'league', 'home_team', 'away_team', 'name', 'start_time', 'end_time')
        }),
        (_('Статус и результат'), {
            'fields': ('status', 'home_score', 'away_score', 'result_details', 'is_featured', 'is_boosted')
        }),
        (_('Источник данных'), {
            'fields': ('data_source', 'external_id', 'notes')
        }),
        (_('Статистика'), {
            'fields': ('views_count', 'bets_count', 'total_stake', 'markets_count'),
            'classes': ('collapse',)
        }),
        (_('Расчёт'), {
            'fields': ('settled_at', 'settled_by'),
            'classes': ('collapse',)
        }),
    )

    # Custom actions
    actions = ['open_prematch', 'suspend_bets', 'close_bets', 'mark_featured', 'cancel_event']

    def event_display(self, obj):
        """Отображение события с ссылкой"""
        return format_html(
            '<a href="{}">{}</a>',
            reverse('admin:sports_event_change', args=[obj.id]),
            str(obj)
        )
    event_display.short_description = _('Событие')

    def status_badge(self, obj):
        """Статус с цветной бейджем"""
        colors = {
            'scheduled': '#6c757d',
            'prematch': '#0066cc',
            'live': '#ff3333',
            'suspended': '#ffcc00',
            'finished': '#28a745',
            'cancelled': '#666',
            'postponed': '#ff6600',
        }
        icons = {
            'scheduled': '📅',
            'prematch': '📊',
            'live': '🔴',
            'suspended': '⏸',
            'finished': '✅',
            'cancelled': '❌',
            'postponed': '🔄',
        }
        return format_html(
            '<span style="background: {}; color: white; padding: 4px 10px; border-radius: 4px; font-weight: bold;">'
            '{} {}</span>',
            colors.get(obj.status, '#ccc'),
            icons.get(obj.status, ''),
            obj.get_status_display()
        )
    status_badge.short_description = _('Статус')

    def score_display(self, obj):
        """Отображение счёта"""
        if obj.status == 'finished' or obj.status == 'live':
            return format_html(
                '<strong style="font-size: 16px;">{} : {}</strong>',
                obj.home_score or 0,
                obj.away_score or 0
            )
        return '—'
    score_display.short_description = _('Счёт')

    def start_time_display(self, obj):
        """Отображение времени начала"""
        return obj.start_time.strftime('%d.%m.%Y\n%H:%M')
    start_time_display.short_description = _('Начало')

    def total_stake_display(self, obj):
        """Общая сумма ставок"""
        return format_html(
            '<strong style="color: #0066cc;">${:.2f}</strong>',
            obj.total_stake
        )
    total_stake_display.short_description = _('На сумму')

    def open_prematch(self, request, queryset):
        """Открыть ставки"""
        queryset.update(status='prematch')
        self.message_user(request, _("✅ События открыты для ставок"))
    open_prematch.short_description = _("🟢 Открыть ставки")

    def suspend_bets(self, request, queryset):
        """Приостановить ставки"""
        queryset.update(status='suspended')
        self.message_user(request, _("⏸ Ставки приостановлены"))
    suspend_bets.short_description = _("⏸ Приостановить ставки")

    def close_bets(self, request, queryset):
        """Закрыть ставки"""
        queryset.update(status='live')
        self.message_user(request, _("🔴 Ставки закрыты"))
    close_bets.short_description = _("🔴 Закрыть ставки")

    def mark_featured(self, request, queryset):
        """Отметить как избранное"""
        queryset.update(is_featured=True)
        self.message_user(request, _("⭐ События отмечены как избранные"))
    mark_featured.short_description = _("⭐ Отметить как избранное")

    def cancel_event(self, request, queryset):
        """Отменить событие (вернуть все ставки)"""
        from apps.sports.services.settlement_service import SettlementService
        for event in queryset:
            try:
                SettlementService.void_event(event.id, request.user, 'Событие отменено админом')
                self.message_user(request, _("✅ События отменены, ставки возвращены"))
            except Exception as e:
                self.message_user(request, _("❌ Ошибка: " + str(e)))
    cancel_event.short_description = _("❌ Отменить событие (вернуть ставки)")


@admin.register(Market)
class MarketAdmin(admin.ModelAdmin):
    list_display = ['name', 'event', 'market_type', 'status', 'parameter']
    list_filter = ['status', 'market_type']
    search_fields = ['name', 'event__name']


@admin.register(MarketType)
class MarketTypeAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'has_parameter', 'sport', 'is_active', 'is_popular', 'sort_order']
    list_editable = ['is_active', 'is_popular', 'sort_order']
    list_filter = ['has_parameter', 'sport', 'is_active', 'is_popular']
    search_fields = ['code', 'name', 'name_en']


@admin.register(Outcome)
class OutcomeAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'market', 'odd_display', 'odd_direction_badge', 'result_badge',
        'is_active', 'bets_count', 'total_stake_display'
    ]
    list_filter = ['result', 'is_active', 'odd_direction']
    list_editable = ['is_active']
    search_fields = ['name', 'market__name', 'code']
    readonly_fields = ['id', 'bets_count', 'total_stake']

    def odd_display(self, obj):
        """Отображение коэффициента"""
        return format_html(
            '<strong style="color: #0066cc; font-size: 14px;">{:.3f}</strong>',
            obj.odd
        )
    odd_display.short_description = _('Коэффициент')

    def odd_direction_badge(self, obj):
        """Направление изменения коэффициента"""
        colors = {'up': '#28a745', 'down': '#dc3545', 'same': '#ccc'}
        icons = {'up': '📈', 'down': '📉', 'same': '▯'}
        return format_html(
            '<span style="color: {}; font-weight: bold; font-size: 16px;">{}</span>',
            colors.get(obj.odd_direction, '#ccc'),
            icons.get(obj.odd_direction, '')
        )
    odd_direction_badge.short_description = _('Движение')

    def result_badge(self, obj):
        """Статус результата"""
        colors = {
            'pending': '#0066cc',
            'won': '#28a745',
            'lost': '#dc3545',
            'void': '#ffcc00',
            'half_won': '#17a2b8',
            'half_lost': '#ff6600',
        }
        icons = {
            'pending': '⏳',
            'won': '✅',
            'lost': '❌',
            'void': '↩️',
            'half_won': '👌',
            'half_lost': '👎',
        }
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; border-radius: 4px; font-weight: bold;">'
            '{} {}</span>',
            colors.get(obj.result, '#ccc'),
            icons.get(obj.result, ''),
            obj.get_result_display()
        )
    result_badge.short_description = _('Результат')

    def total_stake_display(self, obj):
        """Общая сумма ставок на исход"""
        return format_html(
            '<span style="color: #0066cc; font-weight: bold;">${:.2f}</span>',
            obj.total_stake
        )
    total_stake_display.short_description = _('На сумму')


@admin.register(Bet)
class BetAdmin(admin.ModelAdmin):
    list_display = [
        'bet_link', 'user_link', 'bet_type_badge', 'stake_display',
        'odd_display', 'potential_win_display', 'actual_win_display',
        'status_badge', 'items_count', 'created_at_display'
    ]
    list_filter = ['status', 'bet_type', 'currency', 'created_at']
    search_fields = ['bet_id', 'user__email', 'user__username']
    readonly_fields = ['bet_id', 'total_odd', 'potential_win', 'freeze_transaction', 'win_transaction', 'id']
    date_hierarchy = 'created_at'

    fieldsets = (
        (_('Базовая информация'), {
            'fields': ('id', 'bet_id', 'user', 'wallet', 'created_at')
        }),
        (_('Ставка'), {
            'fields': (
                'bet_type', 'currency', 'stake', 'stake_usd',
                'total_odd', 'potential_win', 'actual_win', 'profit'
            )
        }),
        (_('Статус'), {
            'fields': ('status', 'items_count', 'items_won', 'items_lost', 'items_void', 'items_pending')
        }),
        (_('Кэшаут'), {
            'fields': ('cashout_available', 'cashout_amount', 'cashout_used_at'),
            'classes': ('collapse',)
        }),
        (_('Платежи'), {
            'fields': ('freeze_transaction', 'win_transaction'),
            'classes': ('collapse',)
        }),
        (_('Расчёт'), {
            'fields': ('settled_at',),
            'classes': ('collapse',)
        }),
    )

    actions = ['cancel_bets']

    def bet_link(self, obj):
        """Ссылка на ставку"""
        return format_html(
            '<a href="{}"><strong>{}</strong></a>',
            reverse('admin:sports_bet_change', args=[obj.id]),
            obj.bet_id
        )
    bet_link.short_description = _('ID')

    def user_link(self, obj):
        """Ссылка на пользователя"""
        try:
            user_url = reverse('admin:accounts_customuser_change', args=[obj.user.id])
            return format_html(
                '<a href="{}">{}</a>',
                user_url,
                obj.user.email or obj.user.username
            )
        except:
            return obj.user.email or obj.user.username
    user_link.short_description = _('Пользователь')

    def bet_type_badge(self, obj):
        """Тип ставки с эмодзи"""
        icons = {'single': '1️⃣', 'combo': '#️⃣', 'system': '3️⃣'}
        return format_html(
            '{} <strong>{}</strong>',
            icons.get(obj.bet_type, ''),
            obj.get_bet_type_display()
        )
    bet_type_badge.short_description = _('Тип')

    def stake_display(self, obj):
        return format_html(
            '<strong>${:.2f}</strong> {}',
            obj.stake,
            obj.currency.code
        )
    stake_display.short_description = _('Ставка')

    def odd_display(self, obj):
        return format_html('<strong style="color: #0066cc;">{:.3f}</strong>', obj.total_odd)
    odd_display.short_description = _('Коэф')

    def potential_win_display(self, obj):
        return format_html(
            '<span style="color: #0066cc; font-weight: bold;">${:.2f}</span>',
            obj.potential_win
        )
    potential_win_display.short_description = _('Потенциально')

    def actual_win_display(self, obj):
        color = '#28a745' if obj.actual_win > 0 else '#dc3545' if obj.actual_win < 0 else '#ccc'
        return format_html(
            '<span style="color: {}; font-weight: bold;">${:.2f}</span>',
            color,
            obj.actual_win
        )
    actual_win_display.short_description = _('Выигрыш')

    def status_badge(self, obj):
        """Статус ставки"""
        colors = {
            'pending': '#0066cc',
            'won': '#28a745',
            'lost': '#dc3545',
            'void': '#ffcc00',
            'cashed_out': '#ff6600',
            'cancelled': '#666',
            'partial_won': '#17a2b8',
        }
        icons = {
            'pending': '⏳',
            'won': '✅',
            'lost': '❌',
            'void': '↩️',
            'cashed_out': '💰',
            'cancelled': '🚫',
            'partial_won': '👌',
        }
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; border-radius: 4px; font-weight: bold;">'
            '{} {}</span>',
            colors.get(obj.status, '#ccc'),
            icons.get(obj.status, ''),
            obj.get_status_display()
        )
    status_badge.short_description = _('Статус')

    def created_at_display(self, obj):
        return format_html(
            '{}',
            obj.created_at.strftime('%d.%m.%Y<br>%H:%M')
        )
    created_at_display.short_description = _('Создано')

    def cancel_bets(self, request, queryset):
        """Отменить ставку"""
        from apps.sports.services.betting_service import BettingService
        cancelled_count = 0
        for bet in queryset.filter(status='pending'):
            try:
                BettingService.cancel_bet(bet.id, request.user, 'Отмена админом')
                cancelled_count += 1
            except Exception as e:
                self.message_user(request, _("❌ Ошибка при отмене: " + str(e)))

        if cancelled_count > 0:
            self.message_user(request, _("✅ Отменено ставок: " + str(cancelled_count)))
    cancel_bets.short_description = _("🚫 Отменить выбранные ставки")


@admin.register(BetItem)
class BetItemAdmin(admin.ModelAdmin):
    list_display = ['bet', 'event_name', 'market_name', 'outcome_name', 'odd_at_placement', 'result']
    readonly_fields = ['event_name', 'market_name', 'outcome_name', 'odd_at_placement']
    search_fields = ['bet__bet_id', 'event_name', 'outcome_name']


@admin.register(BetSettings)
class BetSettingsAdmin(admin.ModelAdmin):
    list_display = ['min_stake_usd', 'max_stake_usd', 'cashout_enabled']

    def has_add_permission(self, request):
        return not BetSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(OddHistory)
class OddHistoryAdmin(admin.ModelAdmin):
    list_display = ['outcome', 'odd_before', 'odd_after', 'changed_by', 'changed_at']
    list_filter = ['changed_by', 'changed_at']
    search_fields = ['outcome__name']
    readonly_fields = ['outcome', 'odd_before', 'odd_after', 'changed_by', 'changed_at']
