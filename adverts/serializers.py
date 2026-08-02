from rest_framework import serializers
from .models import Advert


class AdvertListSerializer(serializers.ModelSerializer):
    operator_name    = serializers.CharField(source='operator.full_name', read_only=True)
    shop_number      = serializers.CharField(source='shop.shop_number', read_only=True)
    association_name = serializers.CharField(source='association.name', read_only=True)
    fee_naira        = serializers.ReadOnlyField()
    is_expired       = serializers.ReadOnlyField()

    class Meta:
        model  = Advert
        fields = [
            'id', 'headline', 'description',
            'category', 'image_url',
            'contact_phone', 'contact_email',
            'contact_whatsapp', 'contact_instagram',
            'contact_facebook',
            'operator', 'operator_name',
            'shop', 'shop_number',
            'association', 'association_name',
            'fee', 'fee_naira',
            'status', 'is_live', 'is_expired',
            'live_from', 'expires_at',
            'approved_at', 'created_at',
        ]


class AdvertSerializer(serializers.ModelSerializer):
    operator_name    = serializers.CharField(source='operator.full_name', read_only=True)
    shop_number      = serializers.CharField(source='shop.shop_number', read_only=True)
    reviewed_by_name = serializers.CharField(source='reviewed_by.full_name', read_only=True)
    association_name = serializers.CharField(source='association.name', read_only=True)
    fee_naira        = serializers.ReadOnlyField()
    iscooa_cut_naira = serializers.ReadOnlyField()
    iprolance_cut_naira = serializers.ReadOnlyField()
    is_expired       = serializers.ReadOnlyField()

    class Meta:
        model  = Advert
        fields = [
            'id', 'headline', 'description',
            'category', 'image_url', 'duration_days',
            'contact_phone', 'contact_email',
            'contact_whatsapp', 'contact_instagram',
            'contact_facebook',
            'operator', 'operator_name',
            'shop', 'shop_number',
            'association', 'association_name',
            'fee', 'fee_naira',
            'iscooa_cut', 'iscooa_cut_naira',
            'iprolance_cut', 'iprolance_cut_naira',
            'status', 'is_live', 'is_expired',
            'reviewed_by', 'reviewed_by_name',
            'reviewed_at', 'reject_reason',
            'approved_at', 'live_from', 'expires_at',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'fee', 'iscooa_cut', 'iprolance_cut',
            'operator', 'association',
            'reviewed_by', 'reviewed_at',
            'approved_at', 'live_from', 'expires_at',
            'created_at', 'updated_at',
        ]


class AdvertCreateSerializer(serializers.ModelSerializer):
    """Used when operator submits a new advert."""

    class Meta:
        model  = Advert
        fields = [
            'shop', 'headline', 'description',
            'category', 'image_url',
            # Optional contact fields
            'contact_phone', 'contact_email',
            'contact_whatsapp', 'contact_instagram',
            'contact_facebook',
        ]

    def validate_shop(self, shop):
        request = self.context.get('request')
        if shop.operator != request.user:
            raise serializers.ValidationError(
                'This shop does not belong to you.'
            )
        return shop