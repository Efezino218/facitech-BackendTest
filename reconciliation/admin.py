from django.contrib import admin
from .models import ReconciliationRecord, PeriodSummary


@admin.register(ReconciliationRecord)
class ReconciliationRecordAdmin(admin.ModelAdmin):
    list_display    = (
        'bill', 'operator', 'shop',
        'billing_period', 'iscooa_amount',
        'operator_amount', 'variance',
        'match_status', 'reconciled_at'
    )
    list_filter     = ('match_status', 'billing_period')
    search_fields   = (
        'bill__invoice_id',
        'operator__email',
        'shop__shop_number'
    )
    readonly_fields = ('created_at', 'updated_at')


@admin.register(PeriodSummary)
class PeriodSummaryAdmin(admin.ModelAdmin):
    list_display    = (
        'billing_period', 'total_bills',
        'matched_count', 'unverified_count',
        'gap_count', 'settlement_percentage',
        'last_updated'
    )
    readonly_fields = ('last_updated',)