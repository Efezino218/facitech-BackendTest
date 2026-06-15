from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display    = (
        'user_email', 'user_role', 'action',
        'table_name', 'record_ref',
        'ip_address', 'timestamp'
    )
    list_filter     = ('action', 'user_role', 'table_name')
    search_fields   = (
        'user_email', 'record_ref',
        'record_id', 'description'
    )
    readonly_fields = (
        'user', 'user_email', 'user_role',
        'action', 'table_name', 'record_id', 'record_ref',
        'description', 'old_value', 'new_value',
        'ip_address', 'user_agent', 'timestamp'
    )

    # Prevent any modification
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False