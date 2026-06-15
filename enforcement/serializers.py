from rest_framework import serializers
from .models import Penalty, ShutdownNotice


class PenaltySerializer(serializers.ModelSerializer):
    """Full penalty serializer."""
    operator_name       = serializers.CharField(source='operator.full_name', read_only=True)
    operator_email      = serializers.EmailField(source='operator.email', read_only=True)
    shop_number         = serializers.CharField(source='shop.shop_number', read_only=True)
    issued_by_name      = serializers.CharField(source='issued_by.full_name', read_only=True)
    waived_by_name      = serializers.CharField(source='waived_by.full_name', read_only=True)
    amount_naira        = serializers.ReadOnlyField()
    is_overdue          = serializers.ReadOnlyField()
    penalty_type_display = serializers.CharField(
        source='get_penalty_type_display', read_only=True
    )
    status_display      = serializers.CharField(
        source='get_status_display', read_only=True
    )

    class Meta:
        model  = Penalty
        fields = [
            'id', 'penalty_ref',
            'operator', 'operator_name', 'operator_email',
            'shop', 'shop_number',
            'penalty_type', 'penalty_type_display',
            'description', 'amount', 'amount_naira',
            'issued_date', 'due_date',
            'status', 'status_display', 'is_overdue',
            'issued_by', 'issued_by_name',
            'paid_at', 'paid_ref',
            'waived_by', 'waived_by_name', 'waiver_reason',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'penalty_ref', 'operator',
            'status', 'issued_by',
            'paid_at', 'paid_ref',
            'waived_by', 'waiver_reason',
            'created_at', 'updated_at',
        ]


class PenaltyCreateSerializer(serializers.ModelSerializer):
    """Used by ISCOOA Executive to issue a penalty."""
    class Meta:
        model  = Penalty
        fields = [
            'operator', 'shop', 'penalty_type',
            'description', 'amount',
            'issued_date', 'due_date',
        ]

    def validate_shop(self, shop):
        operator = self.initial_data.get('operator')
        if operator and str(shop.operator.id) != str(operator):
            raise serializers.ValidationError(
                'This shop does not belong to the specified operator.'
            )
        return shop


class ShutdownNoticeSerializer(serializers.ModelSerializer):
    """Full shutdown notice serializer."""
    operator_name   = serializers.CharField(source='operator.full_name', read_only=True)
    operator_email  = serializers.EmailField(source='operator.email', read_only=True)
    shop_number     = serializers.CharField(source='shop.shop_number', read_only=True)
    issued_by_name  = serializers.CharField(source='issued_by.full_name', read_only=True)
    lifted_by_name  = serializers.CharField(source='lifted_by.full_name', read_only=True)
    reason_display  = serializers.CharField(source='get_reason_display', read_only=True)
    status_display  = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model  = ShutdownNotice
        fields = [
            'id', 'shutdown_ref',
            'operator', 'operator_name', 'operator_email',
            'shop', 'shop_number',
            'reason', 'reason_display',
            'description', 'issued_date',
            'status', 'status_display',
            'issued_by', 'issued_by_name',
            'lifted_at', 'lifted_by', 'lifted_by_name',
            'lift_reason', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'shutdown_ref', 'operator',
            'status', 'issued_by',
            'lifted_at', 'lifted_by', 'lift_reason',
            'created_at', 'updated_at',
        ]


class ShutdownCreateSerializer(serializers.ModelSerializer):
    """Used by ISCOOA Executive to issue a shutdown notice."""
    class Meta:
        model  = ShutdownNotice
        fields = [
            'operator', 'shop',
            'reason', 'description', 'issued_date',
        ]

    def validate_shop(self, shop):
        operator = self.initial_data.get('operator')
        if operator and str(shop.operator.id) != str(operator):
            raise serializers.ValidationError(
                'This shop does not belong to the specified operator.'
            )
        return shop