from django.contrib import admin
from .models import ToiletPricing, ToiletSubscription


@admin.register(ToiletPricing)
class ToiletPricingAdmin(admin.ModelAdmin):
    list_display  = (
        'association',
        'daily_naira', 'monthly_naira',
        'quarterly_naira', 'annual_naira',
        'is_active', 'updated_by', 'updated_at'
    )
    list_filter   = ('is_active', 'association')
    search_fields = ('association__name', 'association__slug')
    readonly_fields = ('updated_at', 'created_at')


@admin.register(ToiletSubscription)
class ToiletSubscriptionAdmin(admin.ModelAdmin):
    list_display  = (
        'access_ref', 'full_name', 'person_type',
        'association', 'shop', 'plan', 'amount',
        'start_date', 'expiry_date', 'status'
    )
    list_filter   = ('status', 'plan', 'person_type', 'association')
    search_fields = (
        'full_name', 'access_ref',
        'shop__shop_number',
        'registered_by__email',
        'association__name',
    )
    readonly_fields = ('access_ref', 'created_at', 'updated_at')