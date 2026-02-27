from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import (
    Sport, Country, League, Team, Event, Market, MarketType,
    Outcome, Bet, BetItem, BetSettings, OddHistory
)

# Register your models here.


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
        'name', 'sport', 'league', 'start_time', 'status',
        'home_score', 'away_score', 'markets_count',
        'bets_count', 'total_stake', 'is_featured'
    ]
    list_filter = ['sport', 'league', 'status', 'is_featured', 'data_source', 'start_time']
    search_fields = ['name', 'home_team__name', 'away_team__name']
    date_hierarchy = 'start_time'
    readonly_fields = ['bets_count', 'total_stake', 'views_count']
    list_editable = ['status', 'is_featured']

    # Custom actions
    actions = ['open_prematch', 'suspend_bets', 'close_bets', 'settle_event', 'cancel_event', 'mark_featured']

    def open_prematch(self, request, queryset):
        queryset.update(status='prematch')
        self.message_user(request, _("События открыты для ставок"))
    open_prematch.short_description = _("Открыть ставки (prematch)")

    def suspend_bets(self, request, queryset):
        queryset.update(status='suspended')
        self.message_user(request, _("Ставки приостановлены"))
    suspend_bets.short_description = _("Приостановить ставки")

    def close_bets(self, request, queryset):
        queryset.update(status='live')
        self.message_user(request, _("Ставки закрыты"))
    close_bets.short_description = _("Закрыть ставки")

    def settle_event(self, request, queryset):
        # Placeholder for settlement
        self.message_user(request, _("Расчёт событий (placeholder)"))
    settle_event.short_description = _("Рассчитать событие")

    def cancel_event(self, request, queryset):
        queryset.update(status='cancelled')
        self.message_user(request, _("События отменены"))
    cancel_event.short_description = _("Отменить событие")

    def mark_featured(self, request, queryset):
        queryset.update(is_featured=True)
        self.message_user(request, _("События отмечены как избранные"))
    mark_featured.short_description = _("Отметить как featured")


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
    list_display = ['name', 'market', 'odd', 'odd_direction', 'result', 'is_active', 'bets_count', 'total_stake']
    list_filter = ['result', 'is_active']
    list_editable = ['odd', 'result', 'is_active']
    search_fields = ['name', 'market__name']


@admin.register(Bet)
class BetAdmin(admin.ModelAdmin):
    list_display = [
        'bet_id', 'user', 'bet_type', 'currency', 'stake',
        'total_odd', 'potential_win', 'actual_win',
        'status', 'items_count', 'created_at'
    ]
    list_filter = ['status', 'bet_type', 'currency', 'created_at']
    search_fields = ['bet_id', 'user__email', 'user__username']
    readonly_fields = ['bet_id', 'total_odd', 'potential_win', 'freeze_transaction', 'win_transaction']
    date_hierarchy = 'created_at'

    actions = ['cancel_bets']

    def cancel_bets(self, request, queryset):
        queryset.update(status='cancelled')
        self.message_user(request, _("Ставки отменены"))
    cancel_bets.short_description = _("Отменить ставки")


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
