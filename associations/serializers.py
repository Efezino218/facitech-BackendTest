from rest_framework import serializers
from .models import Association, AssociationConfig


class AssociationConfigSerializer(serializers.ModelSerializer):
    subscription_rate_naira = serializers.ReadOnlyField()
    bot_threshold_naira     = serializers.ReadOnlyField()

    class Meta:
        model  = AssociationConfig
        fields = [
            'id',
            'member_prefix',
            'subscription_rate', 'subscription_rate_naira',
            'bot_threshold', 'bot_threshold_naira',
            'association_share', 'platform_share',
            'logo_url', 'primary_color', 'secondary_color',
            'contact_email', 'contact_phone', 'website',
            'footer_text', 'wallet_provider',
            'wallet_provider_short',
            'toilet_association_share',
            'updated_at',
        ]
        read_only_fields = ['id', 'updated_at']


class AssociationSerializer(serializers.ModelSerializer):
    config = AssociationConfigSerializer(read_only=True)

    class Meta:
        model  = Association
        fields = [
            'id', 'name', 'slug', 'short_name',
            'location', 'is_active', 'launched_at',
            'config', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class AssociationCreateSerializer(serializers.ModelSerializer):
    """Used by Super Admin to create a new association."""

    # Config fields included at creation time
    member_prefix       = serializers.CharField(write_only=True)
    subscription_rate   = serializers.IntegerField(write_only=True, default=100000)
    bot_threshold       = serializers.IntegerField(write_only=True, default=500000000)
    association_share   = serializers.IntegerField(write_only=True, default=20)
    platform_share      = serializers.IntegerField(write_only=True, default=80)
    logo_url            = serializers.URLField(write_only=True, required=False, allow_blank=True)
    primary_color       = serializers.CharField(write_only=True, default='#1a3a5c')
    secondary_color     = serializers.CharField(write_only=True, default='#c9a84c')
    contact_email       = serializers.EmailField(write_only=True, required=False, allow_blank=True)
    contact_phone       = serializers.CharField(write_only=True, required=False, allow_blank=True)
    footer_text         = serializers.CharField(write_only=True, required=False)
    wallet_provider     = serializers.CharField(write_only=True, default='Cool Microfinance Bank')
    wallet_provider_short = serializers.CharField(write_only=True, default='Cool MFB')

    class Meta:
        model  = Association
        fields = [
            'name', 'slug', 'short_name', 'location',
            'launched_at',
            # Config fields
            'member_prefix', 'subscription_rate',
            'bot_threshold', 'association_share', 'platform_share',
            'logo_url', 'primary_color', 'secondary_color',
            'contact_email', 'contact_phone', 'footer_text',
            'wallet_provider', 'wallet_provider_short',
        ]

    def validate(self, data):
        # Revenue split must add up to 100
        assoc_share    = data.get('association_share', 20)
        platform_share = data.get('platform_share', 80)
        if assoc_share + platform_share != 100:
            raise serializers.ValidationError(
                'association_share and platform_share must add up to 100.'
            )
        return data

    def create(self, validated_data):
        # Extract config fields
        config_fields = [
            'member_prefix', 'subscription_rate', 'bot_threshold',
            'association_share', 'platform_share', 'logo_url',
            'primary_color', 'secondary_color', 'contact_email',
            'contact_phone', 'footer_text', 'wallet_provider',
            'wallet_provider_short',
        ]
        config_data = {}
        for field in config_fields:
            if field in validated_data:
                config_data[field] = validated_data.pop(field)

        # Create association
        association = Association.objects.create(**validated_data)

        # Create config
        AssociationConfig.objects.create(
            association=association,
            **config_data
        )
        return association


class PublicAssociationConfigSerializer(serializers.ModelSerializer):
    """
    Public config endpoint for the frontend.
    Returns only branding and display data.
    No sensitive financial details.
    """
    association_name     = serializers.CharField(source='association.name', read_only=True)
    association_slug     = serializers.CharField(source='association.slug', read_only=True)
    association_location = serializers.CharField(source='association.location', read_only=True)

    class Meta:
        model  = AssociationConfig
        fields = [
            'association_name', 'association_slug',
            'association_location',
            'logo_url', 'primary_color', 'secondary_color',
            'footer_text', 'wallet_provider',
            'wallet_provider_short',
            'contact_email', 'contact_phone', 'website',
        ]