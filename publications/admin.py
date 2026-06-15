from django.contrib import admin
from .models import Publication, Announcement


@admin.register(Publication)
class PublicationAdmin(admin.ModelAdmin):
    list_display    = (
        'pub_ref', 'pub_type', 'subject',
        'target_group', 'status',
        'recipient_count', 'sent_at', 'created_at'
    )
    list_filter     = ('pub_type', 'status', 'target_group')
    search_fields   = ('pub_ref', 'subject', 'content')
    readonly_fields = ('pub_ref', 'created_at', 'updated_at')


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display    = (
        'ann_ref', 'title', 'priority',
        'category', 'status',
        'send_email', 'send_sms',
        'publish_date', 'expiry_date'
    )
    list_filter     = ('priority', 'category', 'status')
    search_fields   = ('ann_ref', 'title', 'content')
    readonly_fields = ('ann_ref', 'created_at', 'updated_at')