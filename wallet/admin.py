from django.contrib import admin
from .models import Wallet, WalletTransaction


class WalletTransactionInline(admin.TabularInline):
    model         = WalletTransaction
    extra         = 0
    readonly_fields = (
        'type', 'amount', 'description',
        'method', 'reference', 'confirmed', 'created_at'
    )


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display    = (
        'operator', 'balance', 'balance_naira',
        'coolmfb_account_number', 'is_active', 'created_at'
    )
    list_filter     = ('is_active',)
    search_fields   = ('operator__email', 'coolmfb_account_number')
    readonly_fields = ('created_at', 'updated_at')
    inlines         = [WalletTransactionInline]


@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display  = (
        'operator', 'type', 'amount',
        'description', 'method', 'confirmed', 'created_at'
    )
    list_filter   = ('type', 'method', 'confirmed')
    search_fields = ('operator__email', 'reference', 'description')
    readonly_fields = ('created_at',)