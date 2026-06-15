from django.contrib import admin
from .models import ToiletPricing, ToiletSubscription


@admin.register(ToiletPricing)
class ToiletPricingAdmin(admin.ModelAdmin):
    list_display  = (
        'daily_naira', 'monthly_naira',
        'quarterly_naira', 'annual_naira',
        'is_active', 'updated_at'
    )
    readonly_fields = ('updated_at', 'created_at')


@admin.register(ToiletSubscription)
class ToiletSubscriptionAdmin(admin.ModelAdmin):
    list_display  = (
        'access_ref', 'full_name', 'person_type',
        'shop', 'plan', 'amount',
        'start_date', 'expiry_date', 'status'
    )
    list_filter   = ('status', 'plan', 'person_type')
    search_fields = (
        'full_name', 'access_ref',
        'shop__shop_number',
        'registered_by__email'
    )
    readonly_fields = ('access_ref', 'created_at', 'updated_at')