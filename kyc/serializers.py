from rest_framework import serializers
from .models import (
    KYCApplication, KYCReviewNote, KYCPersonal, KYCBusiness,
    KYCShop, KYCIscooaStanding, KYCStaff, KYCNextOfKin,
    KYCGuarantor, KYCFinance, KYCEmergencyContact,
    KYCDocuments, KYCDeclaration
)


class KYCPersonalSerializer(serializers.ModelSerializer):
    class Meta:
        model  = KYCPersonal
        exclude = ['application']


class KYCBusinessSerializer(serializers.ModelSerializer):
    class Meta:
        model  = KYCBusiness
        exclude = ['application']


class KYCShopSerializer(serializers.ModelSerializer):
    class Meta:
        model  = KYCShop
        exclude = ['application']


class KYCIscooaStandingSerializer(serializers.ModelSerializer):
    class Meta:
        model  = KYCIscooaStanding
        exclude = ['application']


class KYCStaffSerializer(serializers.ModelSerializer):
    class Meta:
        model  = KYCStaff
        exclude = ['application']


class KYCNextOfKinSerializer(serializers.ModelSerializer):
    class Meta:
        model  = KYCNextOfKin
        exclude = ['application']


class KYCGuarantorSerializer(serializers.ModelSerializer):
    class Meta:
        model  = KYCGuarantor
        exclude = ['application']


class KYCFinanceSerializer(serializers.ModelSerializer):
    class Meta:
        model  = KYCFinance
        exclude = ['application']


class KYCEmergencyContactSerializer(serializers.ModelSerializer):
    class Meta:
        model  = KYCEmergencyContact
        exclude = ['application']


class KYCDocumentsSerializer(serializers.ModelSerializer):
    class Meta:
        model  = KYCDocuments
        exclude = ['application']


class KYCDeclarationSerializer(serializers.ModelSerializer):
    class Meta:
        model  = KYCDeclaration
        exclude = ['application']


class KYCReviewNoteSerializer(serializers.ModelSerializer):
    reviewed_by_name = serializers.CharField(
        source='reviewed_by.full_name', read_only=True
    )

    class Meta:
        model  = KYCReviewNote
        fields = ['id', 'reviewed_by_name', 'note', 'created_at']


class KYCApplicationSerializer(serializers.ModelSerializer):
    """Full read serializer — used by ISCOOA executive to view complete record."""
    personal            = KYCPersonalSerializer(read_only=True)
    business            = KYCBusinessSerializer(read_only=True)
    kyc_shops           = KYCShopSerializer(many=True, read_only=True)
    iscooa_standing     = KYCIscooaStandingSerializer(read_only=True)
    staff_info          = KYCStaffSerializer(read_only=True)
    next_of_kin         = KYCNextOfKinSerializer(read_only=True)
    guarantor           = KYCGuarantorSerializer(read_only=True)
    finance             = KYCFinanceSerializer(read_only=True)
    emergency_contact   = KYCEmergencyContactSerializer(read_only=True)
    documents           = KYCDocumentsSerializer(read_only=True)
    declaration         = KYCDeclarationSerializer(read_only=True)
    review_notes        = KYCReviewNoteSerializer(many=True, read_only=True)
    operator_email      = serializers.EmailField(source='operator.email', read_only=True)
    operator_name       = serializers.CharField(source='operator.full_name', read_only=True)

    class Meta:
        model  = KYCApplication
        fields = [
            'id', 'kyc_id', 'operator_email', 'operator_name',
            'status', 'member_number', 'docs_note',
            'submitted_date', 'updated_at', 'approved_date',
            'personal', 'business', 'kyc_shops', 'iscooa_standing',
            'staff_info', 'next_of_kin', 'guarantor', 'finance',
            'emergency_contact', 'documents', 'declaration',
            'review_notes',
        ]


class KYCApplicationListSerializer(serializers.ModelSerializer):
    """Lightweight list serializer — used in the ISCOOA review queue."""
    operator_email  = serializers.EmailField(source='operator.email', read_only=True)
    operator_name   = serializers.CharField(source='operator.full_name', read_only=True)
    shop_count      = serializers.IntegerField(source='kyc_shops.count', read_only=True)

    class Meta:
        model  = KYCApplication
        fields = [
            'id', 'kyc_id', 'operator_email', 'operator_name',
            'status', 'member_number', 'shop_count', 'submitted_date',
        ]