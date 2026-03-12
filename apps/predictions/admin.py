from django.contrib import admin
from django.utils import timezone
from django.contrib import messages

from .models import (
    MarketCategory, PredictionMarket, Position, Trade,
    PriceHistory, MarketComment, MarketLike, CommentLike,
    MarketDispute, PredictionSettings
)


@admin.register(MarketCategory)
class MarketCategoryAdmin(admin.ModelAdmin):
    list_display = ('icon', 'name', 'markets_count', 'is_active', 'sort_order')
    list_editable = ('is_active', 'sort_order')
    search_fields = ('name', 'name_en')
    ordering = ('sort_order',)


@admin.register(PredictionMarket)
class PredictionMarketAdmin(admin.ModelAdmin):
    list_display = ('question_short', 'category', 'status', 'yes_price', 'no_price', 'volume_usd', 'trades_count', 'close_date', 'created_at')
    list_filter = ('status', 'category', 'is_featured', 'is_trending', 'close_date')
    search_fields = ('question', 'question_en', 'tags')
    readonly_fields = ('market_id', 'yes_pool', 'no_pool', 'constant_k', 'volume_usd', 'trades_count', 'unique_traders')
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Основное', {
            'fields': ('market_id', 'question', 'question_en', 'description', 'description_en', 'category', 'thumbnail')
        }),
        ('AMM & Цены', {
            'fields': ('yes_pool', 'no_pool', 'constant_k', 'yes_price', 'no_price', 'initial_liquidity'),
            'classes': ('collapse',)
        }),
        ('Временные рамки', {
            'fields': ('close_date', 'resolution_date')
        }),
        ('Статус и резолвинг', {
            'fields': ('status', 'resolution', 'resolved_by', 'resolved_at', 'resolution_evidence', 'resolution_evidence_url'),
            'classes':('collapse',)
        }),
        ('Статистика', {
            'fields': ('volume_usd', 'volume_24h_usd', 'trades_count', 'unique_traders', 'views_count', 'comments_count', 'likes_count'),
            'classes': ('collapse',)
        }),
        ('Позиции', {
            'fields': ('yes_holders', 'no_holders', 'total_yes_shares', 'total_no_shares', 'liquidity_usd'),
            'classes': ('collapse',)
        }),
        ('Настройки', {
            'fields': ('is_featured', 'is_trending', 'sort_order', 'source_url', 'resolution_source', 'tags', 'created_by'),
            'classes': ('collapse',)
        }),
    )

    actions = ['resolve_as_yes', 'resolve_as_no', 'void_market', 'close_trading']

    def question_short(self, obj):
        return obj.question[:60]
    question_short.short_description = 'Вопрос'

    def resolve_as_yes(self, request, queryset):
        """Разрешить как YES."""
        from .services.resolution_service import ResolutionService
        for market in queryset:
            try:
                ResolutionService.resolve_market(
                    market.id, 'yes', request.user,
                    'Разрешено админом через интерфейс'
                )
                self.message_user(request, f"✅ {market.question[:50]} разрешен как YES")
            except Exception as e:
                self.message_user(request, f"❌ Ошибка: {str(e)}", level=messages.ERROR)

    resolve_as_yes.short_description = "Разрешить как YES"

    def resolve_as_no(self, request, queryset):
        """Разрешить как NO."""
        from .services.resolution_service import ResolutionService
        for market in queryset:
            try:
                ResolutionService.resolve_market(
                    market.id, 'no', request.user,
                    'Разрешено админом через интерфейс'
                )
                self.message_user(request, f"✅ {market.question[:50]} разрешен как NO")
            except Exception as e:
                self.message_user(request, f"❌ Ошибка: {str(e)}", level=messages.ERROR)

    resolve_as_no.short_description = "Разрешить как NO"

    def void_market(self, request, queryset):
        """Аннулировать маркет."""
        from .services.resolution_service import ResolutionService
        for market in queryset:
            try:
                ResolutionService.void_market(
                    market.id, request.user,
                    'Аннулировано админом'
                )
                self.message_user(request, f"🚫 {market.question[:50]} аннулирован")
            except Exception as e:
                self.message_user(request, f"❌ Ошибка: {str(e)}", level=messages.ERROR)

    void_market.short_description = "Аннулировать маркет"

    def close_trading(self, request, queryset):
        """Закрыть торги."""
        updated = queryset.filter(status='active').update(status='trading_halted')
        self.message_user(request, f"⏸️ Торги закрыты на {updated} маркетах")

    close_trading.short_description = "Закрыть торги"


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ('user', 'market', 'side', 'shares', 'avg_price', 'total_invested', 'is_settled')
    list_filter = ('side', 'is_settled')
    search_fields = ('user__email', 'market__question')
    readonly_fields = ('settlement_amount',)
    raw_id_fields = ('user', 'market')
    date_hierarchy = 'created_at'


@admin.register(Trade)
class TradeAdmin(admin.ModelAdmin):
    list_display = ('trade_id', 'user', 'market', 'action', 'side', 'shares', 'price', 'total_cost', 'created_at')
    list_filter = ('action', 'side', 'created_at')
    search_fields = ('trade_id', 'user__email', 'market__question')
    readonly_fields = ('trade_id', 'user', 'market', 'position', 'action', 'side', 'shares', 'price', 'total_cost', 'fee_amount', 'price_before', 'price_after', 'created_at')
    date_hierarchy = 'created_at'
    raw_id_fields = ('user', 'market', 'position', 'transaction')


@admin.register(PriceHistory)
class PriceHistoryAdmin(admin.ModelAdmin):
    list_display = ('market', 'yes_price', 'no_price', 'volume', 'source', 'timestamp')
    list_filter = ('source', 'timestamp')
    search_fields = ('market__question',)
    raw_id_fields = ('market',)
    date_hierarchy = 'timestamp'


@admin.register(MarketComment)
class MarketCommentAdmin(admin.ModelAdmin):
    list_display = ('user', 'market', 'text_short', 'likes_count', 'is_pinned', 'is_deleted', 'created_at')
    list_filter = ('is_pinned', 'is_deleted', 'side_prediction', 'created_at')
    search_fields = ('text', 'user__email', 'market__question')
    raw_id_fields = ('market', 'user', 'parent')
    actions = ['pin_comment', 'unpin_comment', 'delete_comment']
    date_hierarchy = 'created_at'

    def text_short(self, obj):
        return obj.text[:60]
    text_short.short_description = 'Комментарий'

    def pin_comment(self, request, queryset):
        updated = queryset.update(is_pinned=True)
        self.message_user(request, f"📌 {updated} комментариев закреплено")

    pin_comment.short_description = "Закрепить комментарии"

    def unpin_comment(self, request, queryset):
        updated = queryset.update(is_pinned=False)
        self.message_user(request, f"📍 {updated} комментариев открепленоrelease")

    unpin_comment.short_description = "Открепить комментарии"

    def delete_comment(self, request, queryset):
        updated = queryset.update(is_deleted=True)
        self.message_user(request, f"🗑️ {updated} комментариев удалено")

    delete_comment.short_description = "Удалить комментарии"


@admin.register(MarketLike)
class MarketLikeAdmin(admin.ModelAdmin):
    list_display = ('market', 'user', 'created_at')
    search_fields = ('market__question', 'user__email')
    raw_id_fields = ('market', 'user')
    date_hierarchy = 'created_at'


@admin.register(CommentLike)
class CommentLikeAdmin(admin.ModelAdmin):
    list_display = ('comment', 'user', 'created_at')
    search_fields = ('comment__text', 'user__email')
    raw_id_fields = ('comment', 'user')
    date_hierarchy = 'created_at'


@admin.register(MarketDispute)
class MarketDisputeAdmin(admin.ModelAdmin):
    list_display = ('market', 'user', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('market__question', 'user__email', 'reason')
    raw_id_fields = ('market', 'user', 'reviewed_by')
    actions = ['accept_dispute', 'reject_dispute']
    date_hierarchy = 'created_at'

    def accept_dispute(self, request, queryset):
        updated = queryset.filter(status='pending').update(status='accepted', reviewed_by=request.user)
        self.message_user(request, f"✅ {updated} оспариваний принято")

    accept_dispute.short_description = "Принять оспаривание"

    def reject_dispute(self, request, queryset):
        updated = queryset.filter(status='pending').update(status='rejected', reviewed_by=request.user)
        self.message_user(request, f"❌ {updated} оспариваний отклонено")

    reject_dispute.short_description = "Отклонить оспаривание"


@admin.register(PredictionSettings)
class PredictionSettingsAdmin(admin.ModelAdmin):
    list_display = ('is_enabled', 'trading_fee_percent', 'min_trade_amount_usd', 'max_trade_amount_usd')
    fieldsets = (
        ('Общие', {
            'fields': ('is_enabled',)
        }),
        ('Торговля', {
            'fields': ('trading_fee_percent', 'min_trade_amount_usd', 'max_trade_amount_usd', 'max_position_usd')
        }),
        ('Маркеты', {
            'fields': ('default_initial_liquidity', 'min_market_duration_hours', 'auto_close_before_resolution_hours')
        }),
        ('Оспаривание', {
            'fields': ('resolution_dispute_window_hours',)
        }),
        ('Предложения', {
            'fields': ('allow_user_market_proposals',)
        }),
    )

    def has_add_permission(self, request):
        """Запретить добавление дополнительных объектов."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Запретить удаление объекта."""
        return False
