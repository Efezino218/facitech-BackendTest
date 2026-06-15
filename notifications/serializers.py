from rest_framework import serializers
from .models import Notification, NotificationPreference


class NotificationSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(
        source='get_category_display', read_only=True
    )
    channel_display  = serializers.CharField(
        source='get_channel_display', read_only=True
    )

    class Meta:
        model  = Notification
        fields = [
            'id', 'category', 'category_display',
            'channel', 'channel_display',
            'title', 'message', 'related_id',
            'is_read', 'read_at', 'sent_at',
        ]
        read_only_fields = fields


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model  = NotificationPreference
        fields = [
            'id',
            'email_bills',   'email_adverts',  'email_disputes',
            'email_polls',   'email_penalties', 'email_payments',
            'email_kyc',     'email_subscriptions',
            'email_toilet',  'email_general',
            'sms_bills',     'sms_adverts',    'sms_disputes',
            'sms_polls',     'sms_penalties',  'sms_payments',
            'sms_kyc',       'sms_subscriptions',
            'sms_toilet',    'sms_general',
            'updated_at',
        ]
        read_only_fields = ['id', 'updated_at']