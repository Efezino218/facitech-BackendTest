from django.contrib import admin
from .models import Penalty, ShutdownNotice


@admin.register(Penalty)
class PenaltyAdmin(admin.ModelAdmin):
    list_display    = (
        'penalty_ref', 'operator', 'shop',
        'penalty_type', 'amount', 'status',
        'issued_date', 'due_date'
    )
    list_filter     = ('status', 'penalty_type')
    search_fields   = (
        'penalty_ref', 'operator__email',
        'shop__shop_number'
    )
    readonly_fields = ('penalty_ref', 'created_at', 'updated_at')


@admin.register(ShutdownNotice)
class ShutdownNoticeAdmin(admin.ModelAdmin):
    list_display    = (
        'shutdown_ref', 'operator', 'shop',
        'reason', 'status', 'issued_date'
    )
    list_filter     = ('status', 'reason')
    search_fields   = (
        'shutdown_ref', 'operator__email',
        'shop__shop_number'
    )
    readonly_fields = ('shutdown_ref', 'created_at', 'updated_at')