from django.contrib import admin
from .models import (
    KYCApplication, KYCReviewNote, KYCPersonal, KYCBusiness,
    KYCShop, KYCIscooaStanding, KYCStaff, KYCNextOfKin,
    KYCGuarantor, KYCFinance, KYCEmergencyContact,
    KYCDocuments, KYCDeclaration
)


class KYCReviewNoteInline(admin.TabularInline):
    model = KYCReviewNote
    extra = 0
    readonly_fields = ('reviewed_by', 'note', 'created_at')


@admin.register(KYCApplication)
class KYCApplicationAdmin(admin.ModelAdmin):
    list_display  = ('kyc_id', 'operator', 'status', 'member_number', 'submitted_date')
    list_filter   = ('status',)
    search_fields = ('kyc_id', 'operator__email', 'member_number')
    readonly_fields = ('kyc_id', 'submitted_date', 'updated_at')
    inlines       = [KYCReviewNoteInline]


@admin.register(KYCShop)
class KYCShopAdmin(admin.ModelAdmin):
    list_display = ('shop_number', 'block', 'tenure', 'application')
    list_filter  = ('block', 'tenure')