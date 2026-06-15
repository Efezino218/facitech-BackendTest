from rest_framework import serializers
from .models import Advert


class AdvertSerializer(serializers.ModelSerializer):
    """Full advert serializer."""
    operator_name   = serializers.CharField(source='operator.full_name', read_only=True)
    operator_email  = serializers.EmailField(source='operator.email', read_only=True)
    shop_number     = serializers.CharField(source='shop.shop_number', read_only=True)
    reviewed_by_name = serializers.CharField(
        source='reviewed_by.full_name', read_only=True
    )
    fee_naira           = serializers.ReadOnlyField()
    iscooa_cut_naira    = serializers.ReadOnlyField()
    iprolance_cut_naira = serializers.ReadOnlyField()
    category_display    = serializers.CharField(
        source='get_category_display', read_only=True
    )

    class Meta:
        model  = Advert
        fields = [
            'id', 'operator', 'operator_name', 'operator_email',
            'shop', 'shop_number',
            'headline', 'category', 'category_display', 'description',
            'fee', 'fee_naira',
            'iscooa_cut', 'iscooa_cut_naira',
            'iprolance_cut', 'iprolance_cut_naira',
            'status', 'reject_reason',
            'reviewed_by', 'reviewed_by_name', 'reviewed_at',
            'is_live', 'live_from', 'expires_at',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'operator', 'fee', 'iscooa_cut', 'iprolance_cut',
            'status', 'reviewed_by', 'reviewed_at', 'reject_reason',
            'is_live', 'live_from', 'expires_at',
            'created_at', 'updated_at',
        ]


class AdvertCreateSerializer(serializers.ModelSerializer):
    """Used by operator to submit a new advert."""
    class Meta:
        model  = Advert
        fields = ['shop', 'headline', 'category', 'description']

    def validate_shop(self, shop):
        request = self.context.get('request')
        if shop.operator != request.user:
            raise serializers.ValidationError(
                'This shop does not belong to you.'
            )
        return shop


class AdvertListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing adverts."""
    operator_name   = serializers.CharField(source='operator.full_name', read_only=True)
    shop_number     = serializers.CharField(source='shop.shop_number', read_only=True)
    fee_naira       = serializers.ReadOnlyField()
    iscooa_cut_naira = serializers.ReadOnlyField()

    class Meta:
        model  = Advert
        fields = [
            'id', 'headline', 'category', 'operator_name',
            'shop_number', 'fee_naira', 'iscooa_cut_naira',
            'status', 'is_live', 'created_at',
        ]