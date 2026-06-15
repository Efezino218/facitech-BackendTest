from django.contrib import admin
from .models import Bill, ExternalPayment


@admin.register(Bill)
class BillAdmin(admin.ModelAdmin):
    list_display    = (
        'invoice_id', 'shop', 'operator', 'billing_period',
        'total', 'status', 'created_at'
    )
    list_filter     = ('status', 'billing_period')
    search_fields   = ('invoice_id', 'shop__shop_number', 'operator__email')
    readonly_fields = ('invoice_id', 'vat', 'total', 'created_at', 'updated_at')


@admin.register(ExternalPayment)
class ExternalPaymentAdmin(admin.ModelAdmin):
    list_display    = (
        'shop', 'operator', 'category', 'amount',
        'billing_period', 'status', 'created_at'
    )
    list_filter     = ('status', 'category')
    search_fields   = ('shop__shop_number', 'operator__email', 'reference')
    readonly_fields = ('created_at', 'updated_at')