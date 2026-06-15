from rest_framework import serializers
from .models import Subscription, SubscriptionPayment


class SubscriptionPaymentSerializer(serializers.ModelSerializer):
    amount_naira        = serializers.ReadOnlyField()
    iscooa_cut_naira    = serializers.ReadOnlyField()
    iprolance_cut_naira = serializers.ReadOnlyField()

    class Meta:
        model  = SubscriptionPayment
        fields = [
            'id', 'period', 'cycle', 'shop_count',
            'amount', 'amount_naira',
            'iscooa_cut', 'iscooa_cut_naira',
            'iprolance_cut', 'iprolance_cut_naira',
            'status', 'payment_ref', 'paid_at', 'created_at',
        ]
        read_only_fields = fields


class SubscriptionSerializer(serializers.ModelSerializer):
    """
    Full subscription serializer for operator view.
    Shows the 20/80 split explicitly as required by the brief.
    """
    operator_email      = serializers.EmailField(source='operator.email', read_only=True)
    operator_name       = serializers.CharField(source='operator.full_name', read_only=True)
    monthly_fee         = serializers.ReadOnlyField()
    monthly_fee_naira   = serializers.ReadOnlyField()
    iscooa_cut          = serializers.ReadOnlyField()
    iscooa_cut_naira    = serializers.ReadOnlyField()
    iprolance_cut       = serializers.ReadOnlyField()
    iprolance_cut_naira = serializers.ReadOnlyField()
    cycle_total         = serializers.SerializerMethodField()
    cycle_total_naira   = serializers.SerializerMethodField()
    payments            = SubscriptionPaymentSerializer(many=True, read_only=True)

    class Meta:
        model  = Subscription
        fields = [
            'id', 'operator_email', 'operator_name',
            'status', 'cycle', 'current_month', 'shop_count',
            'rate_per_shop',
            'monthly_fee', 'monthly_fee_naira',
            'iscooa_cut', 'iscooa_cut_naira',
            'iprolance_cut', 'iprolance_cut_naira',
            'cycle_total', 'cycle_total_naira',
            'period_start', 'period_end', 'renewal_date',
            'created_at', 'updated_at',
            'payments',
        ]
        read_only_fields = [
            'id', 'operator_email', 'operator_name',
            'current_month', 'shop_count', 'rate_per_shop',
            'created_at', 'updated_at',
        ]

    def get_cycle_total(self, obj):
        return obj.cycle_total()

    def get_cycle_total_naira(self, obj):
        return obj.cycle_total_naira()


class SubscriptionListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for ISCOOA executive list view."""
    operator_email      = serializers.EmailField(source='operator.email', read_only=True)
    operator_name       = serializers.CharField(source='operator.full_name', read_only=True)
    monthly_fee_naira   = serializers.ReadOnlyField()
    iscooa_cut_naira    = serializers.ReadOnlyField()

    class Meta:
        model  = Subscription
        fields = [
            'id', 'operator_email', 'operator_name',
            'status', 'cycle', 'current_month', 'shop_count',
            'monthly_fee_naira', 'iscooa_cut_naira',
            'renewal_date',
        ]


class CycleSelectSerializer(serializers.Serializer):
    """Used when operator selects a payment cycle and pays."""
    cycle = serializers.ChoiceField(
        choices=Subscription.Cycle.choices
    )