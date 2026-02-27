from django.contrib import admin
from .models import GameType, GameSession, CrashGame, CrashBet, UserSeed, CasinoSettings


@admin.register(GameType)
class GameTypeAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'house_edge', 'rtp', 'min_bet', 'max_bet', 'is_active', 'total_bets', 'total_wagered_usd']
    list_editable = ['house_edge', 'min_bet', 'max_bet', 'is_active']
    list_filter = ['is_active', 'is_popular', 'is_new']
    search_fields = ['code', 'name']


@admin.register(GameSession)
class GameSessionAdmin(admin.ModelAdmin):
    list_display = ['game_id', 'user', 'game_type', 'currency', 'bet_amount', 'win_multiplier', 'win_amount', 'status', 'started_at']
    list_filter = ['game_type', 'status', 'currency', 'started_at']
    search_fields = ['game_id', 'user__email']
    readonly_fields = ['game_data', 'server_seed', 'server_seed_hash', 'client_seed', 'nonce']
    date_hierarchy = 'started_at'


@admin.register(CrashGame)
class CrashGameAdmin(admin.ModelAdmin):
    list_display = ['round_id', 'crash_point', 'status', 'players_count', 'total_bet', 'total_payout', 'created_at']
    list_filter = ['status']
    readonly_fields = ['server_seed', 'crash_point']


@admin.register(CrashBet)
class CrashBetAdmin(admin.ModelAdmin):
    list_display = ['user', 'crash_game', 'bet_amount', 'currency', 'auto_cashout', 'cashout_at', 'win_amount', 'status']
    list_filter = ['status']
    search_fields = ['user__email']


@admin.register(UserSeed)
class UserSeedAdmin(admin.ModelAdmin):
    list_display = ['user', 'server_seed_hash', 'nonce', 'updated_at']
    search_fields = ['user__email']
    readonly_fields = ['server_seed']  # Masked for security


@admin.register(CasinoSettings)
class CasinoSettingsAdmin(admin.ModelAdmin):
    # Singleton admin
    def has_add_permission(self, request):
        return not CasinoSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
