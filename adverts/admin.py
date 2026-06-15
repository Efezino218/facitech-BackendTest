from django.contrib import admin
from .models import Advert


@admin.register(Advert)
class AdvertAdmin(admin.ModelAdmin):
    list_display    = (
        'headline', 'operator', 'shop', 'category',
        'fee', 'status', 'is_live', 'created_at'
    )
    list_filter     = ('status', 'category', 'is_live')
    search_fields   = ('headline', 'operator__email', 'shop__shop_number')
    readonly_fields = (
        'fee', 'iscooa_cut', 'iprolance_cut',
        'created_at', 'updated_at'
    )