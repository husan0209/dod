from django.contrib import admin
from .models import (
    PartnerTier, PartnerProfile, Referral, Commission,
    PartnerPayout, PromoLink, PromoLinkClick, NegativeCarryover,
    ReferralSettings
)


@admin.register(PartnerTier)
class PartnerTierAdmin(admin.ModelAdmin):
    list_display = ('icon', 'name', 'sort_order', 'min_referrals', 'min_monthly_ggr', 'commission_rate_month_1', 'is_active')
    list_editable = ('is_active', 'sort_order')
    search_fields = ('name', 'name_en')
    ordering = ('sort_order',)


@admin.register(PartnerProfile)
class PartnerProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'tier', 'balance', 'total_earned', 'total_referrals', 'is_partner_active')
    list_filter = ('tier', 'is_partner_active', 'is_suspended')
    search_fields = ('user__email', 'user__username')
    raw_id_fields = ('user', 'tier')


@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    list_display = ('partner', 'referral', 'status', 'total_deposits', 'total_ggr', 'total_commission_earned', 'registered_at')
    list_filter = ('status', 'level', 'is_qualified', 'is_suspicious')
    search_fields = ('partner__email', 'referral__email')
    raw_id_fields = ('partner', 'referral', 'promo_link')


@admin.register(Commission)
class CommissionAdmin(admin.ModelAdmin):
    list_display = ('partner', 'referral', 'commission_type', 'period_start', 'period_end', 'net_amount', 'status')
    list_filter = ('commission_type', 'status')
    search_fields = ('partner__email', 'referral__referral__email')
    raw_id_fields = ('partner', 'referral', 'payout')


@admin.register(PartnerPayout)
class PartnerPayoutAdmin(admin.ModelAdmin):
    list_display = ('partner', 'amount', 'payout_method', 'status', 'created_at')
    list_filter = ('payout_method', 'status')
    search_fields = ('partner__email',)
    raw_id_fields = ('partner', 'processed_by')


@admin.register(PromoLink)
class PromoLinkAdmin(admin.ModelAdmin):
    list_display = ('partner', 'name', 'slug', 'clicks', 'registrations', 'total_earned', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('partner__email', 'name', 'slug')
    raw_id_fields = ('partner',)


@admin.register(PromoLinkClick)
class PromoLinkClickAdmin(admin.ModelAdmin):
    list_display = ('promo_link', 'ip_address', 'is_unique', 'resulted_in_registration', 'created_at')
    list_filter = ('is_unique', 'resulted_in_registration')
    search_fields = ('promo_link__slug', 'ip_address')
    raw_id_fields = ('promo_link', 'user_registered')


@admin.register(NegativeCarryover)
class NegativeCarryoverAdmin(admin.ModelAdmin):
    list_display = ('partner', 'referral', 'amount')
    search_fields = ('partner__email', 'referral__referral__email')
    raw_id_fields = ('partner', 'referral')


@admin.register(ReferralSettings)
class ReferralSettingsAdmin(admin.ModelAdmin):
    list_display = ('commission_period', 'min_deposit_to_qualify', 'level2_enabled')

    def has_add_permission(self, request):
        return not ReferralSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
