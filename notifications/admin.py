from django.contrib import admin
from .models import Notification, NotificationPreference


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display    = (
        'user', 'title', 'category',
        'channel', 'is_read', 'sent_at'
    )
    list_filter     = ('category', 'channel', 'is_read')
    search_fields   = ('user__email', 'title', 'message')
    readonly_fields = ('sent_at', 'read_at')


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display  = ('user', 'updated_at')
    search_fields = ('user__email',)
    readonly_fields = ('updated_at',)