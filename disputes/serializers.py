from rest_framework import serializers
from .models import Dispute, DisputeUpdate


class DisputeUpdateSerializer(serializers.ModelSerializer):
    updated_by_name = serializers.CharField(
        source='updated_by.full_name', read_only=True
    )

    class Meta:
        model  = DisputeUpdate
        fields = [
            'id', 'updated_by_name',
            'old_status', 'new_status',
            'note', 'created_at',
        ]
        read_only_fields = fields


class DisputeSerializer(serializers.ModelSerializer):
    """Full dispute serializer."""
    operator_name           = serializers.CharField(source='operator.full_name', read_only=True)
    operator_email          = serializers.EmailField(source='operator.email', read_only=True)
    shop_number             = serializers.CharField(source='shop.shop_number', read_only=True)
    assigned_to_name        = serializers.CharField(source='assigned_to.full_name', read_only=True)
    amount_in_dispute_naira = serializers.ReadOnlyField()
    category_display        = serializers.CharField(source='get_category_display', read_only=True)
    status_display          = serializers.CharField(source='get_status_display', read_only=True)
    priority_display        = serializers.CharField(source='get_priority_display', read_only=True)
    updates                 = DisputeUpdateSerializer(many=True, read_only=True)

    class Meta:
        model  = Dispute
        fields = [
            'id', 'dispute_ref',
            'operator', 'operator_name', 'operator_email',
            'shop', 'shop_number',
            'bill_ref', 'category', 'category_display',
            'priority', 'priority_display',
            'subject', 'description',
            'amount_in_dispute', 'amount_in_dispute_naira',
            'status', 'status_display',
            'response', 'assigned_to', 'assigned_to_name',
            'resolved_at', 'created_at', 'updated_at',
            'updates',
        ]
        read_only_fields = [
            'id', 'dispute_ref', 'operator',
            'status', 'response', 'assigned_to',
            'resolved_at', 'created_at', 'updated_at',
        ]


class DisputeCreateSerializer(serializers.ModelSerializer):
    """Used by operator to raise a new dispute."""
    class Meta:
        model  = Dispute
        fields = [
            'shop', 'bill_ref', 'category',
            'priority', 'subject', 'description',
            'amount_in_dispute',
        ]

    def validate_shop(self, shop):
        request = self.context.get('request')
        if shop.operator != request.user:
            raise serializers.ValidationError(
                'This shop does not belong to you.'
            )
        return shop


class DisputeListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing disputes."""
    operator_name   = serializers.CharField(source='operator.full_name', read_only=True)
    shop_number     = serializers.CharField(source='shop.shop_number', read_only=True)

    class Meta:
        model  = Dispute
        fields = [
            'id', 'dispute_ref', 'operator_name',
            'shop_number', 'category', 'priority',
            'subject', 'status', 'created_at',
        ]


class DisputeRespondSerializer(serializers.Serializer):
    """Used by ISCOOA executive to update dispute status and add response."""
    new_status = serializers.ChoiceField(choices=Dispute.Status.choices)
    response   = serializers.CharField()
    note       = serializers.CharField(required=False, allow_blank=True)