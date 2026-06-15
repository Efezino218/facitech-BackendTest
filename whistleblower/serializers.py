from rest_framework import serializers
from .models import WhistleblowerReport, WhistleblowerUpdate


class WhistleblowerUpdateSerializer(serializers.ModelSerializer):
    updated_by_name = serializers.CharField(
        source='updated_by.full_name', read_only=True
    )

    class Meta:
        model  = WhistleblowerUpdate
        fields = [
            'id', 'updated_by_name',
            'old_status', 'new_status',
            'note', 'created_at',
        ]
        read_only_fields = fields


class WhistleblowerReportSerializer(serializers.ModelSerializer):
    """
    Full report serializer.
    Used by President and Legal Adviser only.
    Never exposes submitter identity.
    """
    assigned_to_name    = serializers.CharField(
        source='assigned_to.full_name', read_only=True
    )
    category_display    = serializers.CharField(
        source='get_category_display', read_only=True
    )
    status_display      = serializers.CharField(
        source='get_status_display', read_only=True
    )
    updates             = WhistleblowerUpdateSerializer(many=True, read_only=True)

    class Meta:
        model  = WhistleblowerReport
        fields = [
            'id', 'report_ref',
            'category', 'category_display',
            'narrative', 'status', 'status_display',
            'response', 'assigned_to', 'assigned_to_name',
            'resolved_at', 'submitted_at', 'updated_at',
            'updates',
        ]
        read_only_fields = [
            'id', 'report_ref', 'status',
            'response', 'assigned_to',
            'resolved_at', 'submitted_at', 'updated_at',
        ]


class WhistleblowerSubmitSerializer(serializers.ModelSerializer):
    """
    Used by operator to submit an anonymous report.
    Only category and narrative are accepted.
    No user data is stored.
    """
    class Meta:
        model  = WhistleblowerReport
        fields = ['category', 'narrative']


class WhistleblowerListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing reports."""
    category_display = serializers.CharField(
        source='get_category_display', read_only=True
    )
    status_display   = serializers.CharField(
        source='get_status_display', read_only=True
    )

    class Meta:
        model  = WhistleblowerReport
        fields = [
            'id', 'report_ref',
            'category', 'category_display',
            'status', 'status_display',
            'submitted_at',
        ]


class WhistleblowerRespondSerializer(serializers.Serializer):
    """Used by President or Legal Adviser to update a report."""
    new_status = serializers.ChoiceField(
        choices=WhistleblowerReport.Status.choices
    )
    response   = serializers.CharField()
    note       = serializers.CharField(required=False, allow_blank=True)