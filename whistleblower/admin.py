from django.contrib import admin
from .models import WhistleblowerReport, WhistleblowerUpdate


class WhistleblowerUpdateInline(admin.TabularInline):
    model         = WhistleblowerUpdate
    extra         = 0
    readonly_fields = ('updated_by', 'old_status', 'new_status', 'note', 'created_at')


@admin.register(WhistleblowerReport)
class WhistleblowerReportAdmin(admin.ModelAdmin):
    list_display    = (
        'report_ref', 'category', 'status',
        'assigned_to', 'submitted_at'
    )
    list_filter     = ('status', 'category')
    search_fields   = ('report_ref',)
    readonly_fields = ('report_ref', 'submitted_at', 'updated_at')
    inlines         = [WhistleblowerUpdateInline]

    def get_queryset(self, request):
        # Extra caution — only superusers can see in admin
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.none()