from rest_framework import serializers
from .models import Publication, Announcement


class PublicationSerializer(serializers.ModelSerializer):
    """Full publication serializer."""
    created_by_name     = serializers.CharField(
        source='created_by.full_name', read_only=True
    )
    pub_type_display    = serializers.CharField(
        source='get_pub_type_display', read_only=True
    )
    target_group_display = serializers.CharField(
        source='get_target_group_display', read_only=True
    )
    status_display      = serializers.CharField(
        source='get_status_display', read_only=True
    )

    class Meta:
        model  = Publication
        fields = [
            'id', 'pub_ref',
            'pub_type', 'pub_type_display',
            'subject', 'content',
            'target_group', 'target_group_display',
            'status', 'status_display',
            'created_by', 'created_by_name',
            'attachment',
            'scheduled_for', 'sent_at',
            'recipient_count', 'open_rate',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'pub_ref', 'created_by',
            'sent_at', 'recipient_count', 'open_rate',
            'created_at', 'updated_at',
        ]


class PublicationCreateSerializer(serializers.ModelSerializer):
    """Used by Secretary General to create a publication."""
    class Meta:
        model  = Publication
        fields = [
            'pub_type', 'subject', 'content',
            'target_group', 'status',
            'attachment', 'scheduled_for',
        ]


class PublicationListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing publications."""
    pub_type_display    = serializers.CharField(
        source='get_pub_type_display', read_only=True
    )
    status_display      = serializers.CharField(
        source='get_status_display', read_only=True
    )

    class Meta:
        model  = Publication
        fields = [
            'id', 'pub_ref', 'pub_type', 'pub_type_display',
            'subject', 'target_group', 'status', 'status_display',
            'recipient_count', 'sent_at', 'created_at',
        ]


class AnnouncementSerializer(serializers.ModelSerializer):
    """Full announcement serializer."""
    created_by_name     = serializers.CharField(
        source='created_by.full_name', read_only=True
    )
    priority_display    = serializers.CharField(
        source='get_priority_display', read_only=True
    )
    category_display    = serializers.CharField(
        source='get_category_display', read_only=True
    )
    status_display      = serializers.CharField(
        source='get_status_display', read_only=True
    )

    class Meta:
        model  = Announcement
        fields = [
            'id', 'ann_ref',
            'title', 'content',
            'priority', 'priority_display',
            'category', 'category_display',
            'status', 'status_display',
            'created_by', 'created_by_name',
            'send_email', 'send_sms',
            'publish_date', 'expiry_date',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'ann_ref', 'created_by',
            'created_at', 'updated_at',
        ]


class AnnouncementCreateSerializer(serializers.ModelSerializer):
    """Used by Secretary General to create an announcement."""
    class Meta:
        model  = Announcement
        fields = [
            'title', 'content',
            'priority', 'category',
            'send_email', 'send_sms',
            'publish_date', 'expiry_date',
        ]