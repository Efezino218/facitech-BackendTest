from django.contrib import admin
from .models import Subscription, SubscriptionPayment


class SubscriptionPaymentInline(admin.TabularInline):
    model         = SubscriptionPayment
    extra         = 0
    readonly_fields = (
        'period', 'cycle', 'shop_count',
        'amount', 'iscooa_cut', 'iprolance_cut',
        'status', 'payment_ref', 'paid_at', 'created_at'
    )


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display    = (
        'operator', 'status', 'cycle',
        'current_month', 'shop_count',
        'renewal_date', 'created_at'
    )
    list_filter     = ('status', 'cycle')
    search_fields   = ('operator__email', 'operator__member_number')
    readonly_fields = ('created_at', 'updated_at')
    inlines         = [SubscriptionPaymentInline]


@admin.register(SubscriptionPayment)
class SubscriptionPaymentAdmin(admin.ModelAdmin):
    list_display  = (
        'operator', 'period', 'cycle',
        'amount', 'iscooa_cut', 'iprolance_cut',
        'status', 'paid_at'
    )
    list_filter   = ('status', 'cycle')
    search_fields = ('operator__email', 'payment_ref')