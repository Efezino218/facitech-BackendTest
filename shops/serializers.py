from rest_framework import serializers
from .models import Shop, StaffMember


class StaffMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model  = StaffMember
        fields = [
            'id', 'full_name', 'role', 'shop',
            'phone', 'email', 'is_active', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class ShopSerializer(serializers.ModelSerializer):
    """Full shop serializer including nested staff."""
    staff           = StaffMemberSerializer(many=True, read_only=True)
    operator_name   = serializers.CharField(source='operator.full_name', read_only=True)
    operator_email  = serializers.EmailField(source='operator.email', read_only=True)

    class Meta:
        model  = Shop
        fields = [
            'id', 'shop_number', 'block', 'floor', 'size_sqm',
            'tenure', 'landlord', 'trading_name', 'nature',
            'description', 'electricity_type', 'iscooa_position',
            'shop_photo', 'is_active', 'created_at', 'updated_at',
            'operator_name', 'operator_email', 'staff',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ShopListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing shops."""
    operator_name = serializers.CharField(source='operator.full_name', read_only=True)

    class Meta:
        model  = Shop
        fields = [
            'id', 'shop_number', 'block', 'floor',
            'trading_name', 'nature', 'electricity_type',
            'tenure', 'iscooa_position', 'is_active', 'operator_name',
        ]


class ShopCreateSerializer(serializers.ModelSerializer):
    """Used when operator registers a new shop or updates an existing one."""
    class Meta:
        model  = Shop
        fields = [
            'shop_number', 'block', 'floor', 'size_sqm',
            'tenure', 'landlord', 'trading_name', 'nature',
            'description', 'electricity_type', 'shop_photo',
        ]

    def validate_shop_number(self, value):
        # Get the current shop instance if this is an update
        # self.instance is set by DRF when the serializer is used for update
        current_shop_id = self.instance.id if self.instance else None

        # Check uniqueness but exclude the current shop being edited
        qs = Shop.objects.filter(shop_number=value)
        if current_shop_id:
            qs = qs.exclude(id=current_shop_id)

        if qs.exists():
            raise serializers.ValidationError(
                f"Shop number '{value}' is already registered on the platform."
            )
        return value