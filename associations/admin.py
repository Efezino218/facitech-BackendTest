from django.contrib import admin
from .models import Association, AssociationConfig


class AssociationConfigInline(admin.StackedInline):
    model   = AssociationConfig
    extra   = 0
    can_delete = False


@admin.register(Association)
class AssociationAdmin(admin.ModelAdmin):
    list_display    = (
        'name', 'slug', 'short_name',
        'location', 'is_active', 'created_at'
    )
    list_filter     = ('is_active',)
    search_fields   = ('name', 'slug', 'short_name')
    readonly_fields = ('created_at', 'updated_at')
    prepopulated_fields = {'slug': ('short_name',)}
    inlines         = [AssociationConfigInline]


@admin.register(AssociationConfig)
class AssociationConfigAdmin(admin.ModelAdmin):
    list_display    = (
        'association', 'member_prefix',
        'subscription_rate', 'bot_threshold',
        'association_share', 'platform_share',
        'updated_at'
    )
    readonly_fields = ('updated_at',)