from django.contrib import admin
from .models import Dispute, DisputeUpdate


class DisputeUpdateInline(admin.TabularInline):
    model         = DisputeUpdate
    extra         = 0
    readonly_fields = ('updated_by', 'old_status', 'new_status', 'note', 'created_at')


@admin.register(Dispute)
class DisputeAdmin(admin.ModelAdmin):
    list_display    = (
        'dispute_ref', 'operator', 'shop',
        'category', 'priority', 'status', 'created_at'
    )
    list_filter     = ('status', 'category', 'priority')
    search_fields   = (
        'dispute_ref', 'subject',
        'operator__email', 'shop__shop_number'
    )
    readonly_fields = ('dispute_ref', 'created_at', 'updated_at')
    inlines         = [DisputeUpdateInline]


@admin.register(DisputeUpdate)
class DisputeUpdateAdmin(admin.ModelAdmin):
    list_display  = ('dispute', 'updated_by', 'old_status', 'new_status', 'created_at')
    readonly_fields = ('created_at',)