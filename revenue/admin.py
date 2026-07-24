from django.contrib import admin
from django.utils import timezone
from .models import (
    RevenueWallet, RevenueTransaction,
    RevenueDistribution, WithdrawalRequest,
)


class RevenueTransactionInline(admin.TabularInline):
    model         = RevenueTransaction
    extra         = 0
    readonly_fields = (
        'transaction_type', 'amount', 'source_type',
        'source_ref', 'description', 'created_at'
    )


@admin.register(RevenueWallet)
class RevenueWalletAdmin(admin.ModelAdmin):
    list_display    = (
        'name', 'wallet_type', 'association',
        'balance_naira', 'total_earned_naira',
        'total_withdrawn_naira', 'updated_at'
    )
    list_filter     = ('wallet_type',)
    readonly_fields = (
        'balance', 'total_earned', 'total_withdrawn',
        'created_at', 'updated_at'
    )
    inlines         = [RevenueTransactionInline]


@admin.register(RevenueTransaction)
class RevenueTransactionAdmin(admin.ModelAdmin):
    list_display    = (
        'revenue_wallet', 'transaction_type', 'amount',
        'source_type', 'source_ref', 'created_at'
    )
    list_filter     = ('transaction_type', 'source_type')
    search_fields   = ('source_ref', 'description')
    readonly_fields = ('created_at',)


@admin.register(RevenueDistribution)
class RevenueDistributionAdmin(admin.ModelAdmin):
    list_display    = (
        'association', 'operator', 'payment_type',
        'total_amount', 'association_amount', 'platform_amount',
        'created_at'
    )
    list_filter     = ('payment_type', 'association')
    search_fields   = ('source_ref', 'operator__email')
    readonly_fields = ('created_at',)


@admin.register(WithdrawalRequest)
class WithdrawalRequestAdmin(admin.ModelAdmin):
    list_display = (
        'withdrawal_ref', 'revenue_wallet', 'amount', 'status',
        'requested_by', 'requested_at', 'processed_at'
    )
    list_filter = ('status',)
    search_fields = (
        'withdrawal_ref', 'requested_by__email', 'account_number', 'transfer_ref'
    )
    readonly_fields = (
        'withdrawal_ref', 'requested_at', 'updated_at'
    )

    def save_model(self, request, obj, form, change):
        # Figure out what the status was BEFORE this save, straight from the DB
        old_status = None
        if change:
            old_status = WithdrawalRequest.objects.get(pk=obj.pk).status

        is_becoming_processed = (
            obj.status == WithdrawalRequest.Status.PROCESSED
            and old_status != WithdrawalRequest.Status.PROCESSED
        )

        if is_becoming_processed:
            # Stamp who/when processed it, same as the API does
            obj.processed_by = request.user
            obj.processed_at = timezone.now()

            # This is the missing piece — actually move the money
            obj.revenue_wallet.debit(
                obj.amount,
                description=obj.processing_note,
                ref=obj.transfer_ref,
            )

        super().save_model(request, obj, form, change)