from rest_framework import serializers
from .models import ToiletPricing, ToiletSubscription


class ToiletPricingSerializer(serializers.ModelSerializer):
    """Shows current toilet pricing in both kobo and naira."""
    daily_naira     = serializers.ReadOnlyField()
    monthly_naira   = serializers.ReadOnlyField()
    quarterly_naira = serializers.ReadOnlyField()
    annual_naira    = serializers.ReadOnlyField()

    class Meta:
        model  = ToiletPricing
        fields = [
            'id',
            'daily_kobo',     'daily_naira',
            'monthly_kobo',   'monthly_naira',
            'quarterly_kobo', 'quarterly_naira',
            'annual_kobo',    'annual_naira',
            'is_active', 'updated_at',
        ]
        read_only_fields = ['id', 'updated_at']


class ToiletSubscriptionSerializer(serializers.ModelSerializer):
    """Full toilet subscription serializer."""
    registered_by_name  = serializers.CharField(
        source='registered_by.full_name', read_only=True
    )
    shop_number         = serializers.CharField(
        source='shop.shop_number', read_only=True
    )
    amount_naira        = serializers.ReadOnlyField()
    is_expired          = serializers.ReadOnlyField()
    plan_display        = serializers.CharField(
        source='get_plan_display', read_only=True
    )
    person_type_display = serializers.CharField(
        source='get_person_type_display', read_only=True
    )

    class Meta:
        model  = ToiletSubscription
        fields = [
            'id', 'access_ref',
            'registered_by', 'registered_by_name',
            'shop', 'shop_number',
            'full_name', 'person_type', 'person_type_display',
            'plan', 'plan_display',
            'amount', 'amount_naira',
            'start_date', 'expiry_date',
            'status', 'is_expired',
            'payment_ref', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'access_ref', 'registered_by',
            'amount', 'payment_ref',
            'status', 'created_at', 'updated_at',
        ]


class ToiletRegisterSerializer(serializers.ModelSerializer):
    """Used by operator to register a person for toilet access."""

    class Meta:
        model  = ToiletSubscription
        fields = [
            'shop', 'full_name',
            'person_type', 'plan',
            'start_date',
        ]

    def validate_shop(self, shop):
        request = self.context.get('request')
        if shop.operator != request.user:
            raise serializers.ValidationError(
                'This shop does not belong to you.'
            )
        return shop

    def validate(self, data):
        from .models import ToiletPricing
        # Confirm active pricing exists
        if not ToiletPricing.objects.filter(is_active=True).exists():
            raise serializers.ValidationError(
                'No active toilet pricing found. '
                'Please contact ISCOOA Treasurer.'
            )
        return data


class ToiletRenewSerializer(serializers.Serializer):
    """Used when renewing a toilet subscription."""
    plan       = serializers.ChoiceField(choices=ToiletSubscription.Plan.choices)
    start_date = serializers.DateField()