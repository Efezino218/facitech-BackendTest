from rest_framework import serializers
from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    action_display = serializers.CharField(
        source='get_action_display', read_only=True
    )

    class Meta:
        model  = AuditLog
        fields = [
            'id', 'user_email', 'user_role',
            'action', 'action_display',
            'table_name', 'record_id', 'record_ref',
            'description', 'old_value', 'new_value',
            'ip_address', 'timestamp',
        ]
        read_only_fields = fields