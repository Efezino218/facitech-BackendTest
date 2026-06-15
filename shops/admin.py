from django.contrib import admin
from .models import Shop, StaffMember


class StaffMemberInline(admin.TabularInline):
    model   = StaffMember
    extra   = 0
    fields  = ('full_name', 'role', 'shop', 'phone', 'is_active')


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    list_display    = ('shop_number', 'block', 'floor', 'operator', 'tenure', 'electricity_type', 'is_active')
    list_filter     = ('block', 'tenure', 'electricity_type', 'is_active')
    search_fields   = ('shop_number', 'operator__email', 'trading_name')
    readonly_fields = ('created_at', 'updated_at')
    inlines         = [StaffMemberInline]


@admin.register(StaffMember)
class StaffMemberAdmin(admin.ModelAdmin):
    list_display  = ('full_name', 'role', 'shop', 'operator', 'is_active')
    list_filter   = ('role', 'is_active')
    search_fields = ('full_name', 'operator__email', 'shop__shop_number')