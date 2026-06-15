from rest_framework import serializers
from .models import Bill, ExternalPayment
from validators import validate_billing_period


class BillSerializer(serializers.ModelSerializer):
    """
    Full bill serializer.
    Converts kobo amounts to Naira for display.
    """
    shop_number         = serializers.CharField(source='shop.shop_number', read_only=True)
    operator_name       = serializers.CharField(source='operator.full_name', read_only=True)
    verified_by_name    = serializers.CharField(source='verified_by.full_name', read_only=True)

    # Naira display fields (read only)
    management_fee_naira    = serializers.SerializerMethodField()
    maintenance_levy_naira  = serializers.SerializerMethodField()
    electricity_naira       = serializers.SerializerMethodField()
    water_naira             = serializers.SerializerMethodField()
    vat_naira               = serializers.SerializerMethodField()
    total_naira             = serializers.SerializerMethodField()

    class Meta:
        model  = Bill
        fields = [
            'id', 'invoice_id', 'shop', 'shop_number',
            'operator', 'operator_name', 'billing_period',
            'management_fee', 'management_fee_naira',
            'maintenance_levy', 'maintenance_levy_naira',
            'electricity', 'electricity_naira',
            'water', 'water_naira',
            'vat', 'vat_naira',
            'total', 'total_naira',
            'status', 'paid_at', 'paid_ref',
            'verified_by', 'verified_by_name', 'verified_at',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'invoice_id', 'vat', 'total',
            'paid_at', 'paid_ref',
            'verified_by', 'verified_at',
            'created_at', 'updated_at',
        ]

    def get_management_fee_naira(self, obj):
        return obj.management_fee / 100

    def get_maintenance_levy_naira(self, obj):
        return obj.maintenance_levy / 100

    def get_electricity_naira(self, obj):
        return obj.electricity / 100

    def get_water_naira(self, obj):
        return obj.water / 100

    def get_vat_naira(self, obj):
        return obj.vat / 100

    def get_total_naira(self, obj):
        return obj.total / 100


class BillCreateSerializer(serializers.ModelSerializer):
    """
    Used by ISCOOA Treasurer to raise a new bill.
    Accepts amounts in kobo.
    """
    class Meta:
        model  = Bill
        fields = [
            'shop', 'billing_period',
            'management_fee', 'maintenance_levy',
            'electricity', 'water',
        ]

    def validate_billing_period(self, value):
        from django.core.exceptions import ValidationError as DjangoValidationError
        try:
            validate_billing_period(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(str(e.message) if hasattr(e, 'message') else str(e))
        return value

    def validate(self, data):
        # Prevent duplicate bill for same shop + period
        from .models import Bill
        if Bill.objects.filter(
            shop=data['shop'],
            billing_period=data['billing_period']
        ).exists():
            raise serializers.ValidationError(
                f"A bill already exists for shop "
                f"{data['shop'].shop_number} "
                f"in period {data['billing_period']}."
            )
        return data


class ExternalPaymentSerializer(serializers.ModelSerializer):
    """Full external payment serializer."""
    shop_number         = serializers.CharField(source='shop.shop_number', read_only=True)
    operator_name       = serializers.CharField(source='operator.full_name', read_only=True)
    verified_by_name    = serializers.CharField(source='verified_by.full_name', read_only=True)
    amount_naira        = serializers.SerializerMethodField()
    verified_amount_naira = serializers.SerializerMethodField()

    class Meta:
        model  = ExternalPayment
        fields = [
            'id', 'operator', 'operator_name',
            'shop', 'shop_number',
            'category', 'amount', 'amount_naira',
            'payment_date', 'billing_period',
            'channel', 'reference', 'note', 'evidence',
            'status',
            'verified_by', 'verified_by_name',
            'verified_at', 'verified_amount',
            'verified_amount_naira', 'rejection_note',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'operator', 'status',
            'verified_by', 'verified_at',
            'verified_amount', 'rejection_note',
            'created_at', 'updated_at',
        ]

    def get_amount_naira(self, obj):
        return obj.amount / 100

    def get_verified_amount_naira(self, obj):
        if obj.verified_amount:
            return obj.verified_amount / 100
        return None


class ExternalPaymentCreateSerializer(serializers.ModelSerializer):
    """Used by operator to register an external payment."""
    class Meta:
        model  = ExternalPayment
        fields = [
            'shop', 'category', 'amount',
            'payment_date', 'billing_period',
            'channel', 'reference', 'note', 'evidence',
        ]

    def validate_billing_period(self, value):
        from django.core.exceptions import ValidationError as DjangoValidationError
        try:
            validate_billing_period(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(str(e.message) if hasattr(e, 'message') else str(e))
        return value

    def validate_shop(self, shop):
        request = self.context.get('request')
        if shop.operator != request.user:
            raise serializers.ValidationError(
                "This shop does not belong to you."
            )
        return shop