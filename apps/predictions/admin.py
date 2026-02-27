from django.contrib import admin
from django.utils import timezone
from django.contrib import messages

from .models import (
    Category, Market, Outcome, AMMPool, UserPosition, Trade,
    PriceHistory, Comment, CommentLike, MarketActivity
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('icon', 'name', 'markets_count', 'is_active', 'sort_order')
    list_editable = ('is_active', 'sort_order')
    search_fields = ('name', 'name_en')
    ordering = ('sort_order',)


@admin.register(Market)
class MarketAdmin(admin.ModelAdmin):
    list_display = ('title_short', 'category', 'status', 'total_volume', 'total_traders', 'closes_at', 'created_at')
    list_filter = ('status', 'category', 'is_featured', 'is_hot', 'closes_at')
    search_fields = ('title', 'title_en', 'slug')
    readonly_fields = ('id', 'total_volume', 'total_traders', 'total_shares')
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Основное', {
            'fields': ('title', 'description', 'category', 'image')
        }),
        ('Английский', {
            'fields': ('title_en', 'description_en'),
            'classes': ('collapse',)
        }),
        ('Тип и статус', {
            'fields': ('market_type', 'status', 'resolution_source')
        }),
        ('Временные рамки', {
            'fields': ('opens_at', 'closes_at', 'resolved_at')
        }),
        ('Финансы', {
            'fields': ('initial_liquidity', 'fee_percent', 'total_volume')
        }),
        ('Статистика', {
            'fields': ('total_traders', 'total_shares', 'views_count', 'comments_count'),
            'classes': ('collapse',)
        }),
        ('Настройки', {
            'fields': ('is_featured', 'is_hot', 'comments_enabled', 'tags', 'created_by', 'resolved_by'),
            'classes': ('collapse',)
        }),
    )

    actions = ['resolve_market', 'close_market', 'cancel_market']

    def title_short(self, obj):
        return obj.title[:50]
    title_short.short_description = 'Title'

    def resolve_market(self, request, queryset):
        # Placeholder for resolution logic
        self.message_user(request, "Resolution logic not implemented yet")
    resolve_market.short_description = "Resolve selected markets"

    def close_market(self, request, queryset):
        updated = queryset.filter(status='active').update(status='closed')
        self.message_user(request, f"{updated} markets closed")
    close_market.short_description = "Close trading on selected markets"

    def cancel_market(self, request, queryset):
        updated = queryset.filter(status__in=['draft', 'pending', 'active']).update(status='cancelled')
        self.message_user(request, f"{updated} markets cancelled")
    cancel_market.short_description = "Cancel selected markets"


@admin.register(Outcome)
class OutcomeAdmin(admin.ModelAdmin):
    list_display = ('market', 'title', 'current_price', 'pool_shares', 'total_shares_sold', 'is_winner')
    list_filter = ('is_winner',)
    search_fields = ('title', 'market__title')
    raw_id_fields = ('market',)


@admin.register(AMMPool)
class AMMPoolAdmin(admin.ModelAdmin):
    list_display = ('market', 'liquidity', 'pool_yes', 'pool_no', 'constant_product')
    search_fields = ('market__title',)
    raw_id_fields = ('market',)


@admin.register(UserPosition)
class UserPositionAdmin(admin.ModelAdmin):
    list_display = ('user', 'market', 'outcome', 'shares', 'avg_buy_price', 'total_invested', 'is_settled')
    list_filter = ('is_settled',)
    search_fields = ('user__email', 'market__title')
    readonly_fields = ('settlement_amount',)
    raw_id_fields = ('user', 'market', 'outcome')


@admin.register(Trade)
class TradeAdmin(admin.ModelAdmin):
    list_display = ('user', 'market', 'outcome', 'trade_type', 'shares', 'price_per_share', 'total_amount', 'created_at')
    list_filter = ('trade_type',)
    search_fields = ('user__email', 'market__title')
    readonly_fields = ('id', 'user', 'market', 'outcome', 'trade_type', 'shares', 'price_per_share', 'total_cost', 'fee_amount', 'total_amount', 'price_before', 'price_after', 'ip_address', 'created_at')
    date_hierarchy = 'created_at'
    raw_id_fields = ('user', 'market', 'outcome')


@admin.register(PriceHistory)
class PriceHistoryAdmin(admin.ModelAdmin):
    list_display = ('outcome', 'price', 'volume', 'trades_count', 'interval', 'timestamp')
    list_filter = ('interval',)
    search_fields = ('outcome__title',)
    raw_id_fields = ('outcome',)
    date_hierarchy = 'timestamp'


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('user', 'market', 'text_short', 'likes_count', 'is_pinned', 'is_hidden', 'created_at')
    list_filter = ('is_pinned', 'is_hidden')
    search_fields = ('text', 'user__email', 'market__title')
    raw_id_fields = ('market', 'user', 'parent')
    actions = ['pin_comment', 'unpin_comment', 'hide_comment']

    def text_short(self, obj):
        return obj.text[:50]
    text_short.short_description = 'Comment'

    def pin_comment(self, request, queryset):
        updated = queryset.update(is_pinned=True)
        self.message_user(request, f"{updated} comments pinned")
    pin_comment.short_description = "Pin selected comments"

    def unpin_comment(self, request, queryset):
        updated = queryset.update(is_pinned=False)
        self.message_user(request, f"{updated} comments unpinned")
    unpin_comment.short_description = "Unpin selected comments"

    def hide_comment(self, request, queryset):
        updated = queryset.update(is_hidden=True)
        self.message_user(request, f"{updated} comments hidden")
    hide_comment.short_description = "Hide selected comments"


@admin.register(CommentLike)
class CommentLikeAdmin(admin.ModelAdmin):
    list_display = ('comment', 'user', 'created_at')
    search_fields = ('comment__text', 'user__email')
    raw_id_fields = ('comment', 'user')


@admin.register(MarketActivity)
class MarketActivityAdmin(admin.ModelAdmin):
    list_display = ('market', 'user', 'activity_type', 'description', 'created_at')
    list_filter = ('activity_type',)
    search_fields = ('market__title', 'user__email', 'description')
    raw_id_fields = ('market', 'user', 'trade', 'comment')
